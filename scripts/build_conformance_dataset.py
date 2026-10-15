#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Build the Hugging Face dataset Bayanat-Labs/arabic-normalization-conformance from this repository.

Reads the 80 conformance fixtures (dev 64, acceptance 16) from the staged arabic-normalize repository, adds
the policy hash and the reference output of arabic-normalize (offset map and change log; the Python and
JavaScript implementations give identical output, see js/conformance.json), and writes:

  data/{dev,acceptance}/test-00000-of-00001.parquet   typed columns, zstd
  jsonl/{dev,acceptance}.jsonl                        the same rows as JSON Lines
  README.md, README.ar.md                             bilingual card; every number below is computed here
  CITATION.cff, LICENSE, CHANGELOG.md, CLAIMS.md, PROVENANCE.parquet, MANIFEST.json, SHA256SUMS

Needs pyarrow (development only). Run from anywhere:
    python -I scripts/build_conformance_dataset.py --out DIR [--stats FILE]
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys

import pyarrow as pa
import pyarrow.parquet as pq

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = None  # set from --out
sys.path.insert(0, os.path.join(REPO, "src"))

import arabic_normalize as an  # noqa: E402

HF_REPO = "Bayanat-Labs/arabic-normalization-conformance"
GITHUB = "https://github.com/Bayanat-Labs/arabic-normalize"
SPACE = "https://huggingface.co/spaces/Bayanat-Labs/arabic-normalizer"
TOOL_PAGE = "https://www.bayanatlabs.com/tools/arabic-normalizer"
TOOL_PAGE_AR = "https://www.bayanatlabs.com/ar/tools/arabic-normalizer"
VERSION = "v0.1"
DATE = "2026-10-15"
CONFIGS = ["dev", "acceptance"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cps(s):
    return " ".join("U+%04X" % ord(c) for c in s)


def utf8_ok(s):
    """False when the string holds a lone surrogate, which Parquet (UTF-8) and UTF-8 JSONL cannot store."""
    try:
        s.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def safe(s):
    return s if utf8_ok(s) else None


def load(split):
    path = os.path.join(REPO, "tests", "fixtures", split, split + ".jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()], path


CHANGE = pa.struct([("stage", pa.string()), ("rule_id", pa.string()), ("src_start", pa.int32()),
                    ("src_end", pa.int32()), ("before", pa.string()), ("after", pa.string()),
                    ("before_codepoints", pa.string()), ("after_codepoints", pa.string()), ("lossy", pa.bool_())])
SPAN = pa.struct([("start", pa.int32()), ("end", pa.int32()), ("reason", pa.string())])
SCHEMA = pa.schema([
    ("fixture_id", pa.string()), ("split", pa.string()), ("family", pa.string()),
    ("policy_id", pa.string()), ("policy_sha256", pa.string()),
    ("input", pa.string()), ("input_has_lone_surrogate", pa.bool_()), ("input_escaped", pa.string()),
    ("input_codepoints", pa.string()),
    ("expected_output", pa.string()), ("expected_output_codepoints", pa.string()),
    ("expected_rules", pa.list_(pa.string())), ("expected_lossy_flags", pa.list_(pa.string())),
    ("expected_flags", pa.list_(pa.string())),
    ("expected_offset_map", pa.list_(pa.list_(pa.int32()))),
    ("expected_rejected_spans", pa.list_(SPAN)),
    ("expected_diacritization_ratio", pa.float64()),
    ("reference_offset_map", pa.list_(pa.list_(pa.int32()))),
    ("reference_changes", pa.list_(CHANGE)),
    ("reference_library", pa.string()), ("unicode_version", pa.string()),
    ("rationale_en", pa.string()), ("rationale_ar", pa.string()),
    ("author", pa.string()), ("created", pa.string()), ("label", pa.string()), ("synthetic", pa.bool_()),
    ("reviewed_by", pa.string()), ("review_verdict", pa.string()),
])


def rows_for(fixtures):
    rows = []
    for fx in fixtures:
        p = an.load_policy(fx["policy_id"])
        res = an.normalize_detailed(fx["input"], p)
        # The reference must agree with every hand-written expectation, or the fixture would fail in CI.
        assert res.text_norm == fx["expected_output"], fx["fixture_id"]
        assert list(res.rules) == fx["expected_rules"], fx["fixture_id"]
        if fx["expected_offset_map"] is not None:
            assert [list(x) for x in res.offset_map] == fx["expected_offset_map"], fx["fixture_id"]
        rows.append({
            "fixture_id": fx["fixture_id"], "split": fx["split"], "family": fx["family"],
            "policy_id": fx["policy_id"], "policy_sha256": p.policy_hash,
            "input": safe(fx["input"]), "input_has_lone_surrogate": not utf8_ok(fx["input"]),
            "input_escaped": fx["input_escaped"], "input_codepoints": cps(fx["input"]),
            "expected_output": fx["expected_output"], "expected_output_codepoints": cps(fx["expected_output"]),
            "expected_rules": fx["expected_rules"], "expected_lossy_flags": fx["expected_lossy_flags"],
            "expected_flags": fx["expected_flags"], "expected_offset_map": fx["expected_offset_map"],
            "expected_rejected_spans": fx["expected_rejected_spans"],
            "expected_diacritization_ratio": fx["expected_diacritization_ratio"],
            "reference_offset_map": [list(x) for x in res.offset_map],
            "reference_changes": [{"stage": c.stage, "rule_id": c.rule_id, "src_start": c.src_start, "src_end": c.src_end,
                                   "before": safe(c.before), "after": safe(c.after), "before_codepoints": cps(c.before),
                                   "after_codepoints": cps(c.after), "lossy": c.lossy} for c in res.changes],
            "reference_library": "arabic-normalize %s" % an.__version__, "unicode_version": an.UNICODE_VERSION,
            "rationale_en": fx["rationale_en"], "rationale_ar": fx["rationale_ar"],
            "author": fx["author"], "created": fx["created"], "label": fx["label"], "synthetic": fx["synthetic"],
            "reviewed_by": fx["reviewed_by"], "review_verdict": fx["review_verdict"],
        })
    return rows


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, check=True).stdout.strip()


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory (the dataset repository)")
    ap.add_argument("--stats", help="also write the statistics JSON here")
    a = ap.parse_args()
    OUT = os.path.abspath(a.out)
    os.makedirs(OUT, exist_ok=True)
    commit = git("rev-parse", "HEAD")
    data, sources, stats = {}, {}, {}
    for cfg in CONFIGS:
        fixtures, path = load(cfg)
        rel = os.path.relpath(path, REPO)
        if git("status", "--porcelain", rel):
            raise SystemExit("%s has uncommitted changes; commit it first" % rel)
        sources[cfg] = {"path": rel, "sha256": sha256_file(path), "commit": commit}
        data[cfg] = rows_for(fixtures)
    # --- files ---------------------------------------------------------------------------------------
    for cfg, rows in data.items():
        d = os.path.join(OUT, "data", cfg)
        os.makedirs(d, exist_ok=True)
        table = pa.Table.from_pylist(rows, schema=SCHEMA)
        pq.write_table(table, os.path.join(d, "test-00000-of-00001.parquet"), compression="zstd")
        os.makedirs(os.path.join(OUT, "jsonl"), exist_ok=True)
        with open(os.path.join(OUT, "jsonl", cfg + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")
    # --- statistics (every number in the card comes from here) ----------------------------------------
    allrows = data["dev"] + data["acceptance"]
    by_policy = collections.Counter(r["policy_id"] for r in allrows)
    by_cfg_policy = {cfg: collections.Counter(r["policy_id"] for r in rows) for cfg, rows in data.items()}
    families = {cfg: sorted({r["family"] for r in rows}) for cfg, rows in data.items()}
    fam_counts = collections.Counter(r["family"] for r in allrows)
    lossy = sum(1 for r in allrows if r["expected_lossy_flags"])
    flagged = sum(1 for r in allrows if r["expected_flags"])
    with_map = sum(1 for r in allrows if r["expected_offset_map"] is not None)
    with_ratio = sum(1 for r in allrows if r["expected_diacritization_ratio"] is not None)
    with_rej = sum(1 for r in allrows if r["expected_rejected_spans"])
    rules = sorted({x for r in allrows for x in r["expected_rules"]})
    in_cps = sum(len(r["input_codepoints"].split()) for r in allrows)
    surrogate_inputs = [r["fixture_id"] for r in allrows if r["input_has_lone_surrogate"]]
    out_cps = sum(len(r["expected_output"]) for r in allrows)
    n_changes = sum(len(r["reference_changes"]) for r in allrows)
    unchanged = sum(1 for r in allrows if not r["reference_changes"])
    js = json.load(open(os.path.join(REPO, "js", "conformance.json"), encoding="utf-8"))
    js_pass = sum(v["passing_js"] for v in js["by_split"].values())
    py_pass = len(allrows)  # rows_for asserted every expectation against the Python engine
    stats = {
        "records": {cfg: len(rows) for cfg, rows in data.items()}, "total": len(allrows),
        "by_policy": dict(sorted(by_policy.items())),
        "by_config_policy": {cfg: dict(sorted(c.items())) for cfg, c in by_cfg_policy.items()},
        "families": families, "family_counts": dict(sorted(fam_counts.items())),
        "acceptance_only_families": sorted(set(families["acceptance"]) - set(families["dev"])),
        "lossy_fixtures": lossy, "flagged_fixtures": flagged, "with_offset_map": with_map,
        "with_ratio": with_ratio, "with_rejected_spans": with_rej, "rule_ids": rules,
        "input_codepoints": in_cps, "output_codepoints": out_cps, "reference_changes": n_changes,
        "unchanged_fixtures": unchanged, "lone_surrogate_inputs": surrogate_inputs, "python_passing": py_pass, "js_passing": js_pass,
        "js_reference_cases": js["python_reference"]["cases"],
        "js_reference_identical": js["python_reference"]["cases_identical"],
        "policies": {pid: an.load_policy(pid).policy_hash for pid in sorted(by_policy)},
    }
    write_text("README.md", card_en(stats))
    write_text("README.ar.md", card_ar(stats))
    write_text("CITATION.cff", citation())
    write_text("CHANGELOG.md", "# Changelog\n\n| Version | Date | Change |\n|---|---|---|\n| %s | %s | First release: %d fixtures (dev %d, acceptance %d) from arabic-normalize %s, repository commit %s. |\n" % (
        VERSION, DATE, stats["total"], stats["records"]["dev"], stats["records"]["acceptance"], an.__version__, commit[:12]))
    write_text("CLAIMS.md", claims(stats))
    with open(os.path.join(REPO, "LICENSE-data"), encoding="utf-8") as f:
        write_text("LICENSE", f.read())
    # Provenance ledger: one row per fixture (all Bayanat-authored; no external source).
    prov = {}
    with open(os.path.join(REPO, "tests", "fixtures", "PROVENANCE.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                prov[p["fixture_id"]] = p
    ledger = [{"fixture_id": r["fixture_id"], "config": r["split"], "source": "authored by Bayanat Labs in scripts/author_fixtures.py (never calls the engine)",
               "source_url": "%s/blob/main/tests/fixtures/%s/%s.jsonl" % (GITHUB, r["split"], r["split"]),
               "source_commit": commit, "license": "CC-BY-4.0", "fixture_sha256": prov[r["fixture_id"]]["sha256"],
               "created": r["created"], "synthetic": True, "personal_data": False} for r in allrows]
    pq.write_table(pa.Table.from_pylist(ledger), os.path.join(OUT, "PROVENANCE.parquet"), compression="zstd")
    # Manifest and checksums.
    files = []
    for root, _, names in os.walk(OUT):
        for n in sorted(names):
            p = os.path.join(root, n)
            rel = os.path.relpath(p, OUT)
            if rel in ("MANIFEST.json", "SHA256SUMS") or rel.startswith(".") or n == ".DS_Store":
                continue
            entry = {"path": rel, "bytes": os.path.getsize(p), "sha256": sha256_file(p), "license": "CC-BY-4.0", "version": VERSION}
            if rel.startswith("data/"):
                cfg = rel.split("/")[1]
                entry.update({"rows": pq.ParquetFile(p).metadata.num_rows, "config": cfg, "split": "test"})
            elif rel.startswith("jsonl/"):
                entry.update({"rows": len(data[rel.split("/")[1][:-6]]), "config": rel.split("/")[1][:-6]})
            files.append(entry)
    files.sort(key=lambda e: e["path"])
    manifest = {"dataset": HF_REPO, "version": VERSION, "date": DATE, "license": "CC-BY-4.0",
                "source_repository": GITHUB, "source_commit": commit, "source_files": sources,
                "library": "arabic-normalize %s" % an.__version__, "unicode_version": an.UNICODE_VERSION,
                "stats": stats, "files": files}
    write_text("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    sums = []
    for root, _, names in os.walk(OUT):
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(root, n), OUT)
            if rel == "SHA256SUMS" or rel.startswith(".") or n == ".DS_Store":
                continue
            sums.append("%s  %s" % (sha256_file(os.path.join(OUT, rel)), rel))
    write_text("SHA256SUMS", "\n".join(sorted(sums, key=lambda x: x.split("  ", 1)[1])) + "\n")
    if a.stats:
        with open(a.stats, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: stats[k] for k in ("records", "total", "by_policy", "lossy_fixtures", "python_passing", "js_passing")}, ensure_ascii=False))


def write_text(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def policy_table(s, lang):
    head = "| Policy | SHA-256 | Fixtures |\n|---|---|---|\n" if lang == "en" else "| السياسة | بصمة SHA-256 | عدد الحالات |\n|---|---|---|\n"
    return head + "\n".join("| `%s` | `%s` | %d |" % (pid, h, s["by_policy"][pid]) for pid, h in s["policies"].items())


def family_table(s, lang):
    head = "| Family | Fixtures |\n|---|---|\n" if lang == "en" else "| الفئة | عدد الحالات |\n|---|---|\n"
    return head + "\n".join("| `%s` | %d |" % (k, v) for k, v in s["family_counts"].items())


YAML = """---
pretty_name: "Bayanat Labs Arabic Normalization Conformance Fixtures"
license:
  - cc-by-4.0
language:
  - ar
  - fa
  - ur
size_categories:
  - n<1K
tags:
  - arabic
  - arabic-nlp
  - text-normalization
  - unicode
  - conformance-tests
  - test-suite
  - synthetic
  - bayanat-labs
configs:
  - config_name: dev
    default: true
    data_files:
      - split: test
        path: data/dev/test-00000-of-00001.parquet
  - config_name: acceptance
    data_files:
      - split: test
        path: data/acceptance/test-00000-of-00001.parquet
---
"""


def card_en(s):
    r = s["records"]
    return YAML + f"""
# Bayanat Labs Arabic Normalization Conformance Fixtures · حالات اختبار المطابقة لتوحيد النص العربي

> {s['total']} hand-written test cases (dev {r['dev']}, acceptance {r['acceptance']}) that pin down exactly what a named Arabic normalisation policy must output: the text, the rules applied, the lossy flags and the offset map.
> Version `{VERSION}` ({DATE}) · Library: [arabic-normalize]({GITHUB}) {an.__version__} · Demo: [Arabic Text Normalizer]({SPACE}) · Tool page: {TOOL_PAGE} · Arabic card: [README.ar.md](README.ar.md)
> Published by **Bayanat Labs** (bayanatlabs.com), which is not affiliated with bayanat.ae, Space42 or the ARBML `bayanat` library.

**بالعربية:** {s['total']} حالة اختبار كتبتها بيانات لابز يدويًا (حالات التطوير {r['dev']}، وحالات القبول {r['acceptance']})، تحدد بدقة ما يجب أن تخرجه سياسة مسمّاة لتوحيد النص العربي: النص الناتج، والقواعد المطبّقة، وتنبيهات فقد المعلومات، وخريطة الإزاحات. البطاقة الكاملة بالعربية في [README.ar.md](README.ar.md).

## 1. What is it

Arabic text normalisation (removing harakat and tatweel, folding alef variants, mapping presentation forms, handling zero-width characters) is done differently by every tool, and papers rarely say exactly what they did. These fixtures turn three named, hash-identified policies of the open-source library arabic-normalize into testable cases, so that any implementation, in any language, can check that it gives the same output. They are the conformance suite of arabic-normalize; the Python package and its JavaScript port both pass all of them.

**Intended uses:** testing an Arabic normaliser against a named policy; porting arabic-normalize to another language; documenting the edge cases of Arabic Unicode (presentation forms, combining hamza, ZWNJ, emoji ZWJ sequences, bidi controls, lone surrogates).
**Out-of-scope uses:** training or evaluating language models (the set is tiny and synthetic); linguistic statistics about Arabic; any claim about how often a phenomenon occurs in real text.

## 2. What is being released

| Config | Split | Content | Licence | Records |
|---|---|---|---|---|
| `dev` | `test` | development fixtures across {len(s['families']['dev'])} families | CC BY 4.0 | {r['dev']} |
| `acceptance` | `test` | held-back fixtures with code-point families and rule combinations not in dev | CC BY 4.0 | {r['acceptance']} |

The same rows are in `jsonl/dev.jsonl` and `jsonl/acceptance.jsonl`. Every record was written by Bayanat Labs for this suite (`synthetic: true`); none is taken from a corpus. The 20 rejected-input cases (invalid UTF-8, over-cap requests, invalid policies) stay in the GitHub repository (`tests/fixtures/rejected/`), because they are not text-to-text cases.

## 3. Changelog

| Version | Date | Change |
|---|---|---|
| {VERSION} | {DATE} | First release, from arabic-normalize {an.__version__} |

## 4. How to load

```python
from datasets import load_dataset
dev = load_dataset("{HF_REPO}", "dev", split="test")
acc = load_dataset("{HF_REPO}", "acceptance", split="test")

# check an implementation
from arabic_normalize import normalize_detailed   # or your own normaliser
for fx in dev:
    # exact input, lone surrogates included, rebuilt from the code points
    text = "".join(chr(int(c[2:], 16)) for c in fx["input_codepoints"].split())
    r = normalize_detailed(text, fx["policy_id"])
    assert r.text_norm == fx["expected_output"], fx["fixture_id"]
```

## 5. Breakdown

{policy_table(s, 'en')}

{family_table(s, 'en')}

- Fixtures whose expected output is lossy (non-empty `expected_lossy_flags`): {s['lossy_fixtures']}. Fixtures with an informational flag: {s['flagged_fixtures']}. Fixtures with removed invalid code points (`expected_rejected_spans`): {s['with_rejected_spans']}.
- Fixtures that assert the full offset map: {s['with_offset_map']}; that assert the diacritization ratio: {s['with_ratio']}. The `reference_offset_map` column gives the offset map for every fixture.
- Rule ids covered by `expected_rules`: {len(s['rule_ids'])} ({', '.join('`%s`' % x for x in s['rule_ids'])}).
- Families that occur only in acceptance: {', '.join('`%s`' % x for x in s['acceptance_only_families'])}.
- Input code points: {s['input_codepoints']}; expected output code points: {s['output_codepoints']}; reference change-log entries: {s['reference_changes']}; fixtures whose text the policy leaves unchanged: {s['unchanged_fixtures']}.

All numbers above are computed by `scripts/build_conformance_dataset.py` (GitHub repository) from the released files.

## 6. Baseline

| Implementation | Fixtures passing every assertion |
|---|---|
| arabic-normalize {an.__version__} (Python) | {s['python_passing']} of {s['total']} |
| @bayanat-labs/arabic-normalize {an.__version__} (JavaScript) | {s['js_passing']} of {s['total']} |

The JavaScript port also gives output identical to the Python package in {s['js_reference_identical']} of {s['js_reference_cases']} reference cases (these fixtures under 7 policies), including the offset map and change log (`js/conformance.json` in the GitHub repository).

## 7. Structure

| Field | Type | Description |
|---|---|---|
| `fixture_id` | string | Stable id (`dev-001`, `acc-001`, ...) |
| `split`, `family` | string | Source split and the phenomenon the case tests |
| `policy_id`, `policy_sha256` | string | Policy the case is written for, and its SHA-256 (canonical policy JSON without `meta`) |
| `input` | string, nullable | Input text (may contain invisible characters and noncharacters). Null when the input holds a lone surrogate, which UTF-8 cannot store: rebuild it from `input_codepoints` |
| `input_has_lone_surrogate` | bool | True for those inputs ({', '.join('`%s`' % x for x in s['lone_surrogate_inputs'])}) |
| `input_escaped`, `input_codepoints` | string | The same input as Python-style escapes (`\\uXXXX`, `\\UXXXXXXXX`) and as space-separated `U+XXXX` code points (always exact) |
| `expected_output`, `expected_output_codepoints` | string | Required output |
| `expected_rules` | list of string | Sorted unique rule ids that must appear in the change log |
| `expected_lossy_flags`, `expected_flags` | list of string | Required lossy and informational flags |
| `expected_offset_map` | list of [int, int], nullable | Required offset map (output code point to input span); null when not asserted |
| `expected_rejected_spans` | list of {{start, end, reason}} | Invalid code points that must be removed and reported |
| `expected_diacritization_ratio` | float, nullable | Required ratio; null when not asserted |
| `reference_offset_map`, `reference_changes` | list | Full offset map and change log of arabic-normalize {an.__version__} (informative; not hand-written). Each change has `before`/`after` text (null for a lone surrogate) and `before_codepoints`/`after_codepoints` |
| `reference_library`, `unicode_version` | string | `arabic-normalize {an.__version__}`, `{an.UNICODE_VERSION}` |
| `rationale_en`, `rationale_ar` | string | Why the output is what it is |
| `author`, `created`, `label`, `synthetic` | string, bool | Authorship and the `synthetic/illustrative` label |
| `reviewed_by`, `review_verdict` | string, nullable | Human native review; null until signed |

Offsets are code-point indices into `input`, zero-based and end-exclusive (not UTF-8 bytes, not UTF-16 units).

## 8. Creation

- Written by hand in `scripts/author_fixtures.py` of {GITHUB} (commit recorded in `MANIFEST.json`); the authoring script never calls the engine. The `expected_*` fields are the hand-written expectations; `reference_*` fields were added by `scripts/build_conformance_dataset.py`, which also checks that the reference output meets every expectation.
- Unicode data: UCD {an.UNICODE_VERSION}. Specification: `docs/SPEC.md` (arabic-normalize-spec-1).
- No web collection, no crawler, no third-party text.

## 9. Quality and human review

Every fixture passes in both implementations (section 6). An independent AI Arabic review of the lossy fixtures and policy cards was done on 15 Oct 2026 (`docs/LOSSY_REVIEW.md` in the GitHub repository). A named human native linguist has not yet signed `tests/fixtures/REVIEW.md`; until then `reviewed_by` and `review_verdict` are null. The Arabic rationales were written by the authors and have not had a human native review.

## 10. Considerations

- **Personal data:** none. Common first names (for example مصطفى) appear only as spelling examples.
- **Limitations:** the pilot set is small ({s['total']} cases) and covers three policies; it shows behaviour, not frequency. Persian and Urdu words appear only to test that their letters are kept.
- **Sensitive content:** none known. Some fixtures contain Quranic-style spelling and the honorific ligature ﷺ to test how marks and ligatures are handled.

## 11. Licensing

| Right | Status |
|---|---|
| Use in software tests, documentation and research | Allowed with attribution (CC BY 4.0) |
| Model training | Allowed with attribution; not a training set |
| Redistribution and modification | Allowed with attribution |

Attribute as: "Arabic Normalization Conformance Fixtures, Bayanat Labs, CC BY 4.0". The arabic-normalize code is Apache-2.0; this dataset is data and is CC BY 4.0.

## 12. Citation

```bibtex
@misc{{bayanatlabs_arabic_normalization_conformance_2026,
  title  = {{Bayanat Labs Arabic Normalization Conformance Fixtures}},
  author = {{{{Bayanat Labs}}}},
  year   = {{2026}},
  note   = {{Version {VERSION}, arabic-normalize {an.__version__}}},
  url    = {{https://huggingface.co/datasets/{HF_REPO}}}
}}
```

Also see `CITATION.cff`. To cite a normalisation, name the policy id and its SHA-256.

## 13. Provenance

| Source | URL | Licence | Basis | Date |
|---|---|---|---|---|
| Bayanat Labs, authored for this suite | {GITHUB} | CC BY 4.0 | own work | {DATE} |

Per-record ledger: `PROVENANCE.parquet` (fixture id, source commit, fixture SHA-256, licence). Checksums: `SHA256SUMS`; file list: `MANIFEST.json`.

## 14. Claims

No comparative claims. See `CLAIMS.md`.

## 15. Takedown and contact

Email `open@bayanatlabs.com`. We act on removal requests within 30 days and on platform requests within 24 hours.

## Need production-grade, rights-cleared data?

This free release covers normalisation test cases. For licensed Arabic text and knowledge datasets with documented normalisation, see **Bayanat Labs Knowledge** → https://www.bayanatlabs.com/products/knowledge
"""


def card_ar(s):
    r = s["records"]
    return f"""---
lang: ar
dir: rtl
native_review: independent_ai_review
human_native_review: recommended
---

<div dir="rtl" lang="ar">

# حالات اختبار المطابقة لتوحيد النص العربي من بيانات لابز

> {s['total']} حالة اختبار مكتوبة يدويًا (حالات التطوير {r['dev']}، وحالات القبول {r['acceptance']}) تحدد بدقة ما يجب أن تخرجه سياسة مسمّاة لتوحيد النص العربي: النص الناتج، والقواعد المطبّقة، وتنبيهات فقد المعلومات، وخريطة الإزاحات.
> الإصدار `{VERSION}` ({DATE}). المكتبة: [arabic-normalize]({GITHUB}) {an.__version__}. العرض التجريبي: [{SPACE}]({SPACE}). صفحة الأداة: {TOOL_PAGE_AR}. البطاقة الإنجليزية: [README.md](README.md).
> تنشرها **بيانات لابز** (bayanatlabs.com)، ولا صلة لها بموقع bayanat.ae ولا بشركة Space42 ولا بمكتبة `bayanat` من ARBML.

## 1. ما هذه المجموعة

تختلف أدوات توحيد النص العربي في طريقة حذف الحركات والتطويل، وتوحيد صور الألف، وتحويل أشكال العرض، ومعالجة المحارف الصفرية العرض، ونادرًا ما تذكر الأبحاث ما فعلته بالضبط. تحوّل هذه الحالات ثلاث سياسات مسمّاة ذات بصمة من مكتبة arabic-normalize مفتوحة المصدر إلى اختبارات، فتستطيع أي مكتبة أو أداة، بأي لغة برمجة، أن تتحقق من أنها تعطي الناتج نفسه. وهي مجموعة اختبارات المطابقة لمكتبة arabic-normalize، وتجتازها كلها مكتبة Python ونسختها بلغة JavaScript.

**الاستخدامات المقصودة:** اختبار أداة توحيد عربية وفق سياسة مسمّاة، ونقل arabic-normalize إلى لغة برمجة أخرى، وتوثيق الحالات الحدّية في ترميز يونيكود للنص العربي.
**استخدامات خارج النطاق:** تدريب النماذج اللغوية أو تقييمها (المجموعة صغيرة ومصطنعة)، واستخراج إحصاءات لغوية عن العربية، وأي ادعاء عن مدى شيوع ظاهرة في النصوص الحقيقية.

## 2. محتوى الإصدار

| الإعداد | القسم | المحتوى | الترخيص | عدد السجلات |
|---|---|---|---|---|
| `dev` | `test` | حالات التطوير | CC BY 4.0 | {r['dev']} |
| `acceptance` | `test` | حالات قبول محجوزة تضم فئات ومجموعات قواعد لا ترد في حالات التطوير | CC BY 4.0 | {r['acceptance']} |

السجلات نفسها متاحة أيضًا بصيغة JSON Lines في المجلد `jsonl/`. كتبت بيانات لابز كل سجل لهذه المجموعة (`synthetic: true`)، ولم يُؤخذ أي سجل من مدوّنة نصية. أما حالات المدخلات المرفوضة العشرون فتبقى في مستودع GitHub.

## 3. طريقة التحميل

```python
from datasets import load_dataset
dev = load_dataset("{HF_REPO}", "dev", split="test")
```

## 4. التوزيع

{policy_table(s, 'ar')}

{family_table(s, 'ar')}

- الحالات التي يكون ناتجها المتوقع فاقدًا للمعلومات: {s['lossy_fixtures']}. والحالات التي تحمل تنبيهًا لا يغيّر النص: {s['flagged_fixtures']}.
- الحالات التي تحدد خريطة الإزاحات كاملة: {s['with_offset_map']}. ويعطي العمود `reference_offset_map` خريطة الإزاحات لكل حالة.
- معرّفات القواعد التي تغطيها الحالات: {len(s['rule_ids'])}.

حُسبت جميع الأرقام السابقة بالبرنامج `scripts/build_conformance_dataset.py` في مستودع GitHub من الملفات المنشورة.

## 5. خط الأساس

| المكتبة | الحالات المجتازة |
|---|---|
| arabic-normalize {an.__version__} (Python) | {s['python_passing']} من {s['total']} |
| ‎@bayanat-labs/arabic-normalize {an.__version__} (JavaScript) | {s['js_passing']} من {s['total']} |

## 6. المراجعة

اجتازت كل الحالات في المكتبتين. أُجريت مراجعة عربية مستقلة بالذكاء الاصطناعي للحالات الفاقدة للمعلومات في 15 أكتوبر 2026، ولم يوقّع بعدُ مراجع لغوي بشري من الناطقين بالعربية، ولذلك يبقى الحقلان `reviewed_by` و`review_verdict` فارغين.

## 7. الترخيص والاستشهاد

الترخيص: CC BY 4.0. يُنسب العمل هكذا: "Arabic Normalization Conformance Fixtures, Bayanat Labs, CC BY 4.0". انظر الملف `CITATION.cff`. وعند الإشارة إلى عملية توحيد، اذكر معرّف السياسة وبصمة SHA-256 الخاصة بها.

لا تتضمن المجموعة بيانات شخصية. وترد بعض الأسماء الشائعة مثل مصطفى أمثلةً إملائية فقط.

## 8. الحذف والتواصل

راسلنا على `open@bayanatlabs.com`. نستجيب لطلبات الحذف خلال 30 يومًا، ولطلبات المنصات خلال 24 ساعة.

## هل تحتاج إلى بيانات جاهزة للإنتاج وواضحة الحقوق؟

يغطي هذا الإصدار المجاني حالات اختبار التوحيد. أما مجموعات البيانات النصية العربية المرخّصة ذات التوحيد الموثّق فتجدها في صفحة [مجموعات البيانات النصية العربية المرخّصة](https://www.bayanatlabs.com/ar/products/knowledge) من بيانات لابز.

</div>
"""


def citation():
    return f"""cff-version: 1.2.0
message: "If you use these fixtures, please cite them as below."
type: dataset
title: "Bayanat Labs Arabic Normalization Conformance Fixtures"
version: "{VERSION}"
date-released: "{DATE}"
license: CC-BY-4.0
url: "https://huggingface.co/datasets/{HF_REPO}"
repository-code: "{GITHUB}"
authors:
  - name: "Bayanat Labs"
keywords:
  - arabic
  - text-normalization
  - unicode
  - conformance-tests
abstract: "Hand-written conformance test cases for named Arabic normalisation policies (bayanat-norm-v1, asr-eval-v1, raw-safe-v1) of the arabic-normalize library, with expected output, rule ids, lossy flags and offset maps."
"""


def claims(s):
    return f"""# CLAIMS.md: Bayanat Labs Arabic Normalization Conformance Fixtures {VERSION}

Status: `draft`. Rules: RULES.md section 10.

| Claim ID | Allowed wording (exact) | Unit and counting rule | Count | Licence class | As of | Count script |
|---|---|---|---|---|---|---|
| TL-003-conformance-size | "{s['total']} hand-written conformance cases (dev {s['records']['dev']}, acceptance {s['records']['acceptance']}) for three named Arabic normalisation policies, CC BY 4.0, as of {DATE}." | records in data/dev and data/acceptance | {s['total']} | openly licensed (CC BY 4.0), Bayanat-authored, synthetic | {DATE} | scripts/build_conformance_dataset.py |
| TL-003-conformance-baseline | "arabic-normalize {an.__version__} passes {s['python_passing']} of {s['total']} cases in Python and {s['js_passing']} of {s['total']} in JavaScript, as of {DATE}." | cases passing every assertion | {s['python_passing']} / {s['js_passing']} | as above | {DATE} | scripts/build_conformance_dataset.py, js/scripts/conformance_counts.mjs |

No "first", "only", "largest" or "best" wording is used. No comparison with other datasets is made.
"""


if __name__ == "__main__":
    main()
