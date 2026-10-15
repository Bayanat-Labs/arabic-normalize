#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Write the Python engine's outputs for the conformance fixtures, for the JavaScript conformance test.

Output: js/test/reference/python-reference.json with
  - every dev and acceptance fixture under its own policy, under the two other built-in policies and under
    four custom policies that exercise the stage modes no built-in policy uses (NFKC, ligature expansion,
    hamza folding, Persian/Urdu letters, Arabic-Indic digits, ASCII punctuation, lower-casing, flags, ...);
  - normalize() and normalize_detailed().to_dict() for each case, diff_policies() for each fixture;
  - the canonical JSON and SHA-256 of every policy used.

Usage (from the repository root): python -I js/scripts/make_reference.py
"""
import json
import os
import sys

JS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(JS)
sys.path.insert(0, os.path.join(ROOT, "src"))

import arabic_normalize as an  # noqa: E402
from arabic_normalize.policy import STAGE_ORDER  # noqa: E402

BUILTIN = an.list_policies()


def custom(base, policy_id, unicode_form=None, **stages):
    data = an.load_policy(base).data
    data["policy_id"] = policy_id
    data.pop("meta", None)
    if unicode_form:
        data["unicode_form"] = unicode_form
    for k, v in stages.items():
        assert k in STAGE_ORDER, k
        data["stages"][k] = v
    an.load_policy(data)  # validate
    return data


CUSTOM = [
    custom("asr-eval-v1", "test-search-like", hamza_carriers="fold", persian_urdu_letters="map",
           latin_case="lower", punctuation="ascii"),
    custom("bayanat-norm-v1", "test-nfkc-expand", unicode_form="NFKC", ligatures_honorific="expand",
           diacritics="strip-except-shadda", superscript_alef="to-alef", digits="arabic-indic", bidi_zw="strip",
           quranic_marks="keep"),
    custom("raw-safe-v1", "test-form-none", unicode_form="none", presentation_forms="flag",
           ligatures_honorific="flag", bidi_zw="strip-except-zwnj", alef_maqsura="flag", taa_marbuta="flag",
           whitespace="collapse", strip_controls="keep", punctuation="strip"),
    custom("bayanat-norm-v1", "test-emoji-zwj", bidi_zw="strip-except-emoji-zwj", ligatures_honorific="expand",
           tatweel="keep", alef_variants="keep", alef_maqsura="flag", taa_marbuta="to-heh", digits="keep",
           whitespace="collapse"),
]


def load(split):
    path = os.path.join(ROOT, "tests", "fixtures", split, split + ".jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    fixtures = load("dev") + load("acceptance")
    policies = {pid: an.load_policy(pid) for pid in BUILTIN}
    for data in CUSTOM:
        policies[data["policy_id"]] = an.load_policy(data)
    cases = []
    diffs = []
    for fx in fixtures:
        order = [fx["policy_id"]] + [p for p in BUILTIN if p != fx["policy_id"]] + [d["policy_id"] for d in CUSTOM]
        for pid in order:
            p = policies[pid]
            res = an.normalize_detailed(fx["input"], p)
            cases.append({
                "fixture_id": fx["fixture_id"],
                "split": fx["split"],
                "policy_id": pid,
                "own_policy": pid == fx["policy_id"],
                "input": fx["input"],
                "text_norm_plain": an.normalize(fx["input"], p),
                "rules": list(res.rules),
                "detailed": res.to_dict(),
            })
        other = "raw-safe-v1" if fx["policy_id"] != "raw-safe-v1" else "bayanat-norm-v1"
        diffs.append({
            "fixture_id": fx["fixture_id"], "input": fx["input"], "policy_a": other, "policy_b": fx["policy_id"],
            "result": an.diff_policies(fx["input"], other, fx["policy_id"]),
        })
    out = {
        "generator": "js/scripts/make_reference.py",
        "lib_version": an.__version__,
        "unicode_version": an.UNICODE_VERSION,
        "fixture_count": len(fixtures),
        "policies": {pid: {"policy_hash": p.policy_hash, "canonical": p.canonical(), "builtin": p.builtin,
                           "data": None if p.builtin else p.data}
                     for pid, p in sorted(policies.items())},
        "cases": cases,
        "diffs": diffs,
    }
    path = os.path.join(JS, "test", "reference", "python-reference.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=None, separators=(",", ":"))
        f.write("\n")
    print("wrote %s: %d fixtures, %d cases, %d diffs, %d policies"
          % (os.path.relpath(path, ROOT), len(fixtures), len(cases), len(diffs), len(policies)))


if __name__ == "__main__":
    main()
