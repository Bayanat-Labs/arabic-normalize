#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Python side of the cross-language parity run (beyond the fixtures).

Writes a gzipped JSONL file with, per record, the input and a compact, language-neutral digest of the Python
engine's detailed result. js/scripts/parity_check.mjs recomputes the same digest in JavaScript and compares.

Inputs (no corpus text; nothing here is redistributed):
  random:     seeded random Arabic-heavy strings (the pools of tests/test_properties.py, including lone
              surrogates, noncharacters, emoji, presentation forms and arbitrary code points), N per policy,
              under the 3 built-in policies and the 4 custom test policies of make_reference.py. Strings in
              which a high surrogate is directly followed by a low surrogate are skipped, because a JavaScript
              string cannot keep those two apart (they are one code point there);
  paragraphs: the synthetic paragraphs of work/tl003/scripts/throughput.py (words from the dev fixtures,
              about 4 MB undiacritised and 4 MB diacritised, 2,000-character records), plain and detailed,
              under the 3 built-in policies.

Usage (from the repository root): python -I js/scripts/parity_make.py --n 20000 --out /tmp/parity.jsonl.gz
"""
import argparse
import gzip
import hashlib
import json
import os
import random
import sys

JS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(JS)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(JS, "scripts"))

import arabic_normalize as an  # noqa: E402
from arabic_normalize import engine as E  # noqa: E402
from make_reference import CUSTOM  # noqa: E402

BUILTIN = ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]

_POOLS = [
    (40, list(range(0x0621, 0x063B)) + list(range(0x0641, 0x064B))),
    (12, list(range(0x064B, 0x0656)) + [0x0670]),
    (6, [0x0640, 0x0622, 0x0623, 0x0625, 0x0671, 0x0649, 0x0629, 0x0624, 0x0626, 0x0621]),
    (4, [0x06CC, 0x06A9, 0x06C1, 0x06BE, 0x06D5, 0x06C0, 0x067E, 0x0686, 0x06AF, 0x06D2, 0x0675]),
    (5, list(range(0x0660, 0x066E)) + list(range(0x06F0, 0x06FA)) + list(range(0x30, 0x3A))),
    (6, [0x20, 0x20, 0x20, 0x09, 0x0A, 0x0D, 0xA0, 0x202F, 0x0085, 0x0B, 0x0C]),
    (5, [0x060C, 0x061B, 0x061F, 0x2E, 0x2C, 0x21, 0x3A, 0xAB, 0xBB, 0x2D, 0xFD3E, 0xFD3F, 0x22]),
    (5, sorted(E.PF)),
    (2, sorted(E.HONORIFIC)),
    (5, [0x200B, 0x200C, 0x200C, 0x200D, 0x200D, 0x200E, 0x200F, 0x061C, 0x202A, 0x202B, 0x202C, 0x202D,
         0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0xFEFF, 0x00AD, 0x2060, 0xFE0F, 0x1F3FD, 0x094D]),
    (4, sorted(E.QURANIC) + list(range(0x0659, 0x0660)) + list(range(0x08EA, 0x08F0))),
    (3, [0x1F468, 0x1F469, 0x1F467, 0x1F4BB, 0x1F3F3, 0x1F308, 0x2764, 0x1F525, 0x0915]),
    (5, list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + [0x300, 0x301, 0x302, 0x323, 0xC9, 0xE9, 0x130]),
    (2, [0x07, 0x00, 0x1F, 0x7F, 0x80, 0x9B, 0xD800, 0xDFFF, 0xFFFE, 0xFDD0, 0x10FFFF]),
    (1, None),
]
_WEIGHTS = [w for w, _ in _POOLS]


def rand_text(rng):
    out = []
    for _ in range(rng.randint(0, 40)):
        pool = rng.choices(_POOLS, weights=_WEIGHTS)[0][1]
        out.append(chr(rng.randrange(0x110000)) if pool is None else chr(rng.choice(pool)))
    return "".join(out)


def has_split_pair(s):
    return any(0xD800 <= ord(a) <= 0xDBFF and 0xDC00 <= ord(b) <= 0xDFFF for a, b in zip(s, s[1:]))


def hexcps(s):
    return " ".join("%X" % ord(c) for c in s)


def sha(text):
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def digest(res):
    """Language-neutral digest of a detailed result (recomputed identically in parity_check.mjs)."""
    return {
        "text_norm_sha256": sha(res.text_norm),
        "offsets_sha256": sha("\n".join("%d,%d" % (lo, hi) for lo, hi in res.offset_map)),
        "changes_sha256": sha("\n".join("\t".join([c.stage, c.rule_id, str(c.src_start), str(c.src_end), hexcps(c.before),
                                                   hexcps(c.after), "1" if c.lossy else "0"]) for c in res.changes)),
        "n_changes": len(res.changes),
        "lossy_flags": list(res.lossy_flags),
        "flags": list(res.flags),
        "ratio": repr(res.diacritization_ratio),
        "rejected_spans": [dict(x) for x in res.rejected_spans],
        "stats": res.stats,
        "original_hash": res.original_hash,
        "text_diac_sha256": None if res.text_diac is None else sha(res.text_diac),
        "policy_hash": res.policy_hash,
    }


def paragraphs():
    """The synthetic paragraphs of work/tl003/scripts/throughput.py, rebuilt with the same seed and code."""
    rng = random.Random(5)
    words = []
    with open(os.path.join(ROOT, "tests", "fixtures", "dev", "dev.jsonl"), encoding="utf-8") as f:
        for line in f:
            fx = json.loads(line)
            if fx["policy_id"] == "bayanat-norm-v1":
                words += [w for w in fx["expected_output"].split() if w]
    plain_words = [w for w in words if all("ء" <= c <= "ي" for c in w)]
    harakat = [chr(c) for c in range(0x064B, 0x0651)]

    def build(diac, target=4_000_000):
        out, n = [], 0
        while n < target:
            w = rng.choice(plain_words)
            if diac:
                w = "".join(c + rng.choice(harakat) for c in w)
            out.append(w)
            n += len(w.encode("utf-8")) + 1
            if rng.random() < 0.08:
                out.append(rng.choice(["،", ".", "؟", "١٢", "أن", "إلى"]))
        text = " ".join(out)
        return [text[i:i + 2000] for i in range(0, len(text), 2000)]

    return {"undiacritised": build(False), "diacritised": build(True)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000, help="random strings per policy")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261015)
    args = ap.parse_args()
    policies = [(pid, an.load_policy(pid)) for pid in BUILTIN] + [(d["policy_id"], an.load_policy(d)) for d in CUSTOM]
    skipped = 0
    written = 0
    with gzip.open(args.out, "wt", encoding="utf-8") as f:
        meta = {"kind": "meta", "lib_version": an.__version__, "unicode_version": an.UNICODE_VERSION,
                "python": sys.version.split()[0], "n_per_policy": args.n, "seed": args.seed,
                "custom_policies": CUSTOM}
        f.write(json.dumps(meta, ensure_ascii=True) + "\n")
        for k, (pid, p) in enumerate(policies):
            rng = random.Random(args.seed + k)
            n = 0
            while n < args.n:
                s = rand_text(rng)
                if has_split_pair(s):
                    skipped += 1
                    continue
                rec = {"kind": "random", "policy_id": pid, "input": s, "plain": an.normalize(s, p),
                       "detailed": digest(an.normalize_detailed(s, p))}
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")
                n += 1
                written += 1
        for label, recs in paragraphs().items():
            for pid in BUILTIN:
                for i, s in enumerate(recs):
                    rec = {"kind": "paragraph", "set": label, "index": i, "policy_id": pid, "input": s,
                           "plain": an.normalize(s, pid), "detailed": digest(an.normalize_detailed(s, pid))}
                    f.write(json.dumps(rec, ensure_ascii=True) + "\n")
                    written += 1
    print(json.dumps({"written": written, "skipped_split_surrogate_pairs": skipped, "out": args.out}))


if __name__ == "__main__":
    main()
