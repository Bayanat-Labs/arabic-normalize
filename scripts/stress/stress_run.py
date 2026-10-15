#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Statistics-only stress run of arabic-normalize on a real corpus.

Sources:
  * one Arabic Wikipedia pages-articles-multistream part (.bz2, streamed, never decompressed to disk): main-namespace
    pages that are not redirects, one text per article;
  * a TSV file set, one text per row taken from a named column (for example the FLEURS ar_eg transcripts),
    optionally deduplicated by another column and sampled;
  * a delimited text file, one text per line in the last of its fields (for example id|id|text with
    --delimiter "|"); lines starting with "#" are skipped; optionally sampled.

Every text goes through each pilot policy, in plain and detailed mode. The run records throughput, crashes,
offset-map and other consistency failures, rule and lossy-flag rates, lossy context classes and word-type merge
counts. It writes numbers only: no corpus text leaves this process, and no corpus file is added to the repository.

    python -I scripts/stress/stress_run.py --wikipedia-dump DUMP.bz2 --sha256 HEX --out-json PATH [--workers 8]
    python -I scripts/stress/stress_run.py --tsv A.tsv B.tsv --column 3 --unique-by 0 --unit sentence \
        --sample 2000 --seed 20261013 --out-json PATH
    python -I scripts/stress/stress_run.py --delimited TEXT.txt --delimiter "|" --unit line --sample 2000 \
        --seed 20261013 --out-json PATH

Then scripts/stress/stress_report.py turns the JSON into docs/stress/*.md and *.json.
"""
import argparse
import bz2
import collections
import csv
import hashlib
import json
import multiprocessing as mp
import os
import platform
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))

from arabic_normalize import load_policy, normalize, normalize_detailed, __version__  # noqa: E402
from arabic_normalize import _ucd as U  # noqa: E402
from arabic_normalize import engine as E  # noqa: E402

POLICIES = ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]
CHUNK = 64

# Characters that do not interrupt a word when deciding a letter's position (marks, tatweel, ZWNJ/ZWJ).
_WORD_SKIP = frozenset(U.MARKS | {0x0640, 0x200C, 0x200D})
_ARABIC_LETTER = U.ARABIC_LETTERS


def _neighbour(s, i, step):
    j = i + step
    while 0 <= j < len(s) and ord(s[j]) in _WORD_SKIP:
        j += step
    if 0 <= j < len(s):
        return s[j]
    return None


def _position(s, start, end):
    """Position of the code point(s) s[start:end] in its Arabic word: initial, medial, final or alone."""
    prev = _neighbour(s, start, -1)
    nxt = _neighbour(s, end - 1, +1)
    p = prev is not None and ord(prev) in _ARABIC_LETTER
    n = nxt is not None and ord(nxt) in _ARABIC_LETTER
    return {(False, False): "alone", (False, True): "initial", (True, True): "medial", (True, False): "final"}[(p, n)]


# Common proclitic letter strings written before a stem (definite article, conjunctions, prepositions).
PROCLITICS = frozenset(["\u0627\u0644", "\u0648\u0627\u0644", "\u0641\u0627\u0644", "\u0628\u0627\u0644",
                        "\u0643\u0627\u0644", "\u0644\u0644", "\u0648", "\u0641", "\u0628", "\u0643",
                        "\u0644", "\u0633", "\u0648\u0644", "\u0641\u0644", "\u0648\u0628", "\u0641\u0628"])


def _word_prefix(s, i):
    """Letters of the same Arabic word before position i (marks and tatweel skipped)."""
    out = []
    j = i - 1
    while j >= 0:
        cp = ord(s[j])
        if cp in _WORD_SKIP:
            j -= 1
            continue
        if cp not in _ARABIC_LETTER:
            break
        out.append(s[j])
        j -= 1
    return "".join(reversed(out))


def _lossy_class(s, c):
    """A context class for one lossy change, from the input text around it (counts only, no text kept)."""
    src = s[c.src_start:c.src_end]
    if any(ord(ch) in E.PF for ch in src):
        origin = "presentation_form"
    elif len(src) > 1:
        origin = "sequence_" + "+".join("%04X" % ord(ch) for ch in src)
    else:
        origin = "U+%04X" % ord(src)
    pos = _position(s, c.src_start, c.src_end)
    if pos in ("medial", "final") and _word_prefix(s, c.src_start) in PROCLITICS:
        pos = "stem_initial_after_prefix" if pos == "medial" else "after_prefix_word_final"
    after = s[c.src_end] if c.src_end < len(s) else ""
    extra = []
    if after and ord(after) in (0x0654, 0x0655, 0x0653):
        extra.append("followed_by_hamza_or_madda_mark_U+%04X" % ord(after))
    if after and ord(after) == 0x0670:
        extra.append("followed_by_superscript_alef")
    nxt = _neighbour(s, c.src_end - 1, +1)
    if nxt is not None and ord(nxt) not in _ARABIC_LETTER and ord(nxt) in U.SCRIPT_ARABIC and not U.general_category(
            ord(nxt)).startswith(("P", "Z", "N")):
        extra.append("next_is_other_arabic_U+%04X" % ord(nxt))
    return "|".join([c.rule_id, origin, pos] + extra)


def _word_tokens(s):
    """Arabic-letter tokens of a raw-safe-normalised text, split at anything that is not a letter or a mark."""
    tok = []
    for ch in s:
        cp = ord(ch)
        if cp in _ARABIC_LETTER or (tok and (cp in U.MARKS or cp in (0x0640, 0x200C))):
            tok.append(ch)
        else:
            if tok:
                yield "".join(tok)
                tok = []
    if tok:
        yield "".join(tok)


def check_detailed(s, res, policy):
    """Consistency checks (same as tests/test_properties.py). Returns a list of failure names."""
    out = res.text_norm
    fails = []
    if len(res.offset_map) != len(out):
        fails.append("offset_map_length")
    for lo, hi in res.offset_map:
        if not (0 <= lo < hi <= len(s)):
            fails.append("offset_span_out_of_range")
            break
    if not any(c.rule_id.startswith("canonical_order") for c in res.changes):
        starts = [lo for lo, _ in res.offset_map]
        if starts != sorted(starts):
            fails.append("offset_starts_not_monotone")
    covered = bytearray(len(s))
    for c in res.changes:
        if not (0 <= c.src_start < c.src_end <= len(s)):
            fails.append("change_span_out_of_range")
            break
        for k in range(c.src_start, c.src_end):
            covered[k] = 1
    copies = {}
    for i, (lo, hi) in enumerate(res.offset_map):
        if hi == lo + 1 and 0 <= lo < len(s) and not covered[lo]:
            copies.setdefault(lo, []).append(out[i])
    for k in range(len(s)):
        if not covered[k] and copies.get(k) != [s[k]]:
            fails.append("silent_change_outside_change_log")
            break
    if list(res.lossy_flags) != sorted({c.rule_id for c in res.changes if c.lossy}):
        fails.append("lossy_flags_mismatch")
    return fails


def process_chunk(args):
    idx0, texts = args
    acc = {"articles": 0, "code_points": 0, "utf8_bytes": 0, "arabic_letters": 0, "crashes": collections.Counter(),
           "fails": collections.Counter(), "plain_s": collections.Counter(), "detailed_s": collections.Counter(),
           "rules": {p: collections.Counter() for p in POLICIES},
           "articles_with_rule": {p: collections.Counter() for p in POLICIES},
           "articles_with_any_lossy": collections.Counter(),
           "flags": {p: collections.Counter() for p in POLICIES},
           "rejected": collections.Counter(), "lossy_classes": collections.Counter(),
           "not_idempotent": collections.Counter(), "not_nfc": collections.Counter(),
           "plain_detailed_mismatch": collections.Counter(), "types": collections.Counter(),
           "crash_articles": []}
    for j, s in enumerate(texts):
        acc["articles"] += 1
        acc["code_points"] += len(s)
        acc["utf8_bytes"] += len(s.encode("utf-8", "surrogatepass"))
        classes, _ = E.input_stats(s)
        acc["arabic_letters"] += classes["arabic_letters"]
        raw_safe_out = None
        for p in POLICIES:
            try:
                t0 = time.perf_counter()
                plain = normalize(s, p)
                t1 = time.perf_counter()
                res = normalize_detailed(s, p)
                t2 = time.perf_counter()
            except Exception as exc:  # counted, never fatal
                acc["crashes"][p + ":" + type(exc).__name__] += 1
                acc["crash_articles"].append(idx0 + j)
                continue
            acc["plain_s"][p] += t1 - t0
            acc["detailed_s"][p] += t2 - t1
            if plain != res.text_norm:
                acc["plain_detailed_mismatch"][p] += 1
            for f in check_detailed(s, res, p):
                acc["fails"][p + ":" + f] += 1
            if normalize(res.text_norm, p) != res.text_norm:
                acc["not_idempotent"][p] += 1
            if U.normalize_form(res.text_norm, "NFC") != res.text_norm:
                acc["not_nfc"][p] += 1
            seen = set()
            for c in res.changes:
                acc["rules"][p][c.rule_id] += 1
                seen.add(c.rule_id)
                if c.lossy and (p == "bayanat-norm-v1" or (p == "asr-eval-v1" and c.rule_id == "taa_marbuta.to_heh")):
                    acc["lossy_classes"][_lossy_class(s, c)] += 1
            for r in seen:
                acc["articles_with_rule"][p][r] += 1
            if res.lossy_flags:
                acc["articles_with_any_lossy"][p] += 1
            for fl in res.flags:
                acc["flags"][p][fl] += 1
            if p == "raw-safe-v1":
                raw_safe_out = res.text_norm
                for sp in res.rejected_spans:
                    acc["rejected"][sp["reason"]] += 1
        if raw_safe_out is not None:
            for tok in _word_tokens(raw_safe_out):
                acc["types"][tok] += 1
    return acc


def merge(total, acc):
    for k, v in acc.items():
        if k == "crash_articles":
            total[k].extend(v)
        elif isinstance(v, dict) and not isinstance(v, collections.Counter):
            for p, c in v.items():
                total[k][p].update(c)
        elif isinstance(v, collections.Counter):
            total[k].update(v)
        else:
            total[k] += v


def iter_articles(path, ns_counts):
    from lxml import etree
    with bz2.open(path, "rb") as f:
        ctx = etree.iterparse(f, events=("end",), resolve_entities=False, no_network=True, huge_tree=True,
                              load_dtd=False)
        ns = None
        for _, el in ctx:
            tag = el.tag
            if ns is None and tag.startswith("{"):
                ns = tag[:tag.index("}") + 1]
            if tag != (ns or "") + "page":
                continue
            page_ns = el.findtext((ns or "") + "ns")
            redirect = el.find((ns or "") + "redirect") is not None
            text = el.findtext("%srevision/%stext" % (ns or "", ns or ""))
            ns_counts["pages"] += 1
            if page_ns == "0" and not redirect and text:
                ns_counts["articles"] += 1
                yield text
            elif page_ns == "0" and redirect:
                ns_counts["redirects"] += 1
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]


def read_tsv_texts(paths, column, unique_by):
    """Texts from one column of TSV files (no quoting), in file order; first occurrence per unique_by value."""
    out, seen = [], set()
    for path in paths:
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if unique_by is not None:
                    if row[unique_by] in seen:
                        continue
                    seen.add(row[unique_by])
                out.append(row[column])
    return out


def read_delimited_texts(path, delimiter, fields):
    """One text per line: the last of `fields` fields split on `delimiter`; empty lines and '#' lines are skipped."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            out.append(line.split(delimiter, fields - 1)[-1] if delimiter else line)
    return out


def sample(texts, n, seed):
    if not n or n >= len(texts):
        return list(texts)
    idx = sorted(random.Random(seed).sample(range(len(texts)), n))
    return [texts[i] for i in idx]


def file_record(path):
    with open(path, "rb") as f:
        b = f.read()
    return {"file": os.path.basename(path), "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def chunks(it, n):
    buf, i0, i = [], 0, 0
    for x in it:
        buf.append(x)
        i += 1
        if len(buf) == n:
            yield (i0, buf)
            i0, buf = i, []
    if buf:
        yield (i0, buf)


def single_core_throughput(path, n_articles, texts=None):
    """Throughput on one core, main process, first n_articles: plain and detailed modes per policy."""
    if texts is not None:
        texts = texts[:n_articles]
    else:
        counts = collections.Counter()
        texts = []
        for t in iter_articles(path, counts):
            texts.append(t)
            if len(texts) >= n_articles:
                break
    nbytes = sum(len(t.encode("utf-8", "surrogatepass")) for t in texts)
    out = {"articles": len(texts), "utf8_bytes": nbytes, "policies": {}}
    for p in POLICIES:
        pol = load_policy(p)
        normalize("", pol)
        t0 = time.process_time()
        for t in texts:
            normalize(t, pol)
        t1 = time.process_time()
        for t in texts:
            normalize_detailed(t, pol)
        t2 = time.process_time()
        out["policies"][p] = {"plain_cpu_s": round(t1 - t0, 3), "detailed_cpu_s": round(t2 - t1, 3),
                              "plain_MBps": round(nbytes / 1e6 / (t1 - t0), 2),
                              "detailed_MBps": round(nbytes / 1e6 / (t2 - t1), 2)}
    return out


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--wikipedia-dump", metavar="DUMP.bz2")
    src.add_argument("--tsv", nargs="+", metavar="FILE")
    src.add_argument("--delimited", metavar="FILE", help="text file, one text per line (see --delimiter, --fields)")
    ap.add_argument("--sha256", help="expected SHA-256 of the Wikipedia dump (checked against the file)")
    ap.add_argument("--column", type=int, default=3, help="TSV column holding the text (0-based)")
    ap.add_argument("--unique-by", type=int, default=None, help="TSV column used to keep one row per value")
    ap.add_argument("--delimiter", default="", help="field separator of a --delimited file (default: none, whole line)")
    ap.add_argument("--fields", type=int, default=3, help="fields per line of a --delimited file; the text is the last")
    ap.add_argument("--unit", default="article", help="what one text is: article, sentence, line")
    ap.add_argument("--sample", type=int, default=0, help="sample this many texts (0 = all)")
    ap.add_argument("--seed", type=int, default=20261013)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-articles", type=int, default=None)
    ap.add_argument("--single-core-articles", type=int, default=5000)
    ap.add_argument("--limit", type=int, default=0, help="stop after this many articles (0 = all)")
    a = ap.parse_args()

    started = time.time()
    texts, source = None, None
    if a.wikipedia_dump:
        if a.sha256 and file_record(a.wikipedia_dump)["sha256"] != a.sha256:
            raise SystemExit("dump SHA-256 does not match --sha256")
        min_articles = 50000 if a.min_articles is None else a.min_articles
    else:
        if a.tsv:
            pool_texts = read_tsv_texts(a.tsv, a.column, a.unique_by)
            files = [file_record(p) for p in a.tsv]
            kind = "tsv"
        else:
            pool_texts = read_delimited_texts(a.delimited, a.delimiter, a.fields)
            files = [file_record(a.delimited)]
            kind = "delimited"
        texts = sample(pool_texts, a.sample, a.seed)
        source = {"kind": kind, "files": files, "column": a.column if a.tsv else None,
                  "unique_by": a.unique_by if a.tsv else None, "unit": a.unit, "texts_available": len(pool_texts),
                  "sample_requested": a.sample, "seed": a.seed, "texts_selected": len(texts)}
        min_articles = 0 if a.min_articles is None else a.min_articles
    single = single_core_throughput(a.wikipedia_dump, a.single_core_articles, texts)
    print("single-core:", json.dumps(single), flush=True)

    total = None
    ns_counts = collections.Counter()
    t0 = time.time()

    def gen():
        it = iter_articles(a.wikipedia_dump, ns_counts) if texts is None else iter(texts)
        for k, t in enumerate(it):
            if a.limit and k >= a.limit:
                break
            yield t

    with mp.get_context("fork").Pool(a.workers) as pool:
        for acc in pool.imap_unordered(process_chunk, chunks(gen(), CHUNK), chunksize=1):
            if total is None:
                total = acc
            else:
                merge(total, acc)
            if total["articles"] % (CHUNK * 100) == 0:
                print("articles", total["articles"], "elapsed", round(time.time() - t0, 1), flush=True)
    wall = time.time() - t0

    # Word-type merges caused by lossy rules: distinct Arabic word types (after raw-safe-v1) whose
    # bayanat-norm-v1 / asr-eval-v1 form is shared with another type that differs in more than harakat, tatweel,
    # Quranic marks or superscript alef.
    types = total.pop("types")
    nonlossy = load_policy({**json.loads(json.dumps(_policy_dict("bayanat-norm-v1"))),
                            "policy_id": "stress-nonlossy-reference",
                            "stages": {**_policy_dict("bayanat-norm-v1")["stages"], "alef_variants": "keep",
                                       "alef_maqsura": "keep", "digits": "keep"}})
    merges = {}
    for p in ("bayanat-norm-v1", "asr-eval-v1"):
        pol = load_policy(p)
        groups = collections.defaultdict(set)
        tok_by_base = collections.Counter()
        for t, n in types.items():
            base = normalize(t, nonlossy)
            tok_by_base[base] += n
            groups[normalize(t, pol)].add(base)
        merged_bases = {b for g in groups.values() if len(g) > 1 for b in g}
        merges[p] = {"distinct_base_types": len(tok_by_base),
                     "base_types_merged_with_another": len(merged_bases),
                     "share_of_base_types_merged": round(len(merged_bases) / max(1, len(tok_by_base)), 4),
                     "tokens": sum(tok_by_base.values()),
                     "tokens_of_merged_types": sum(tok_by_base[b] for b in merged_bases),
                     "share_of_tokens_merged": round(sum(tok_by_base[b] for b in merged_bases)
                                                     / max(1, sum(tok_by_base.values())), 4),
                     "output_types": len(groups)}

    result = {
        "machine": {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
                    "workers": a.workers},
        "lib_version": __version__, "unicode_version": U.UNICODE_VERSION,
        "pages_seen": ns_counts["pages"], "main_namespace_redirects_skipped": ns_counts["redirects"],
        "articles": total["articles"], "code_points": total["code_points"], "utf8_bytes": total["utf8_bytes"],
        "arabic_letters": total["arabic_letters"],
        "wall_seconds_parallel": round(wall, 1), "single_core": single,
        "parallel_worker_seconds": {p: {"plain": round(total["plain_s"][p], 2),
                                        "detailed": round(total["detailed_s"][p], 2)} for p in POLICIES},
        "crashes": dict(total["crashes"]), "crash_article_indices": sorted(total["crash_articles"])[:50],
        "consistency_failures": dict(total["fails"]),
        "plain_detailed_mismatch": dict(total["plain_detailed_mismatch"]),
        "not_idempotent": dict(total["not_idempotent"]), "not_nfc": dict(total["not_nfc"]),
        "rules": {p: dict(total["rules"][p].most_common()) for p in POLICIES},
        "articles_with_rule": {p: dict(total["articles_with_rule"][p].most_common()) for p in POLICIES},
        "articles_with_any_lossy": dict(total["articles_with_any_lossy"]),
        "flags": {p: dict(total["flags"][p]) for p in POLICIES},
        "rejected_spans_by_reason": dict(total["rejected"]),
        "lossy_classes": dict(total["lossy_classes"].most_common()),
        "word_type_merges": merges,
        "elapsed_total_seconds": round(time.time() - started, 1),
    }
    if texts is None:
        result = {"dump": {"file": os.path.basename(a.wikipedia_dump), "bytes": os.path.getsize(a.wikipedia_dump),
                           "sha256": file_record(a.wikipedia_dump)["sha256"]}, **result}
    else:
        result = {"source": source, **result}
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=True)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ("articles", "crashes", "consistency_failures", "not_idempotent",
                                              "not_nfc", "wall_seconds_parallel")}, indent=1))
    if result["articles"] < min_articles:
        print("WARNING: fewer than %d articles" % min_articles, file=sys.stderr)
        return 1
    return 0


def _policy_dict(pid):
    path = os.path.join(REPO, "src", "arabic_normalize", "policies", pid + ".json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    d.pop("meta", None)
    return d


if __name__ == "__main__":
    sys.exit(main())
