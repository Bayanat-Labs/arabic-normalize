# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""The oracle agreement tables match the fixture files, and no oracle package is imported by this repository."""
import json
import os
import re

from conftest import ROOT, fixtures

ORACLE_MODULES = ("pyarabic", "camel_tools", "tnkeeh", "whisper_normalizer", "whisper", "farasa", "mishkal")
_IMPORT = re.compile(r"^\s*(?:import|from)\s+(%s)\b" % "|".join(ORACLE_MODULES), re.M)


def test_agreement_tables_cover_the_fixtures():
    with open(os.path.join(ROOT, "docs", "compat", "agreement.json"), encoding="utf-8") as f:
        data = json.load(f)
    fx = {f["fixture_id"]: f for f in fixtures("dev") + fixtures("acceptance")}
    rows = {r["fixture_id"]: r for r in data["fixtures"]}
    assert set(rows) == set(fx)
    for fid, r in rows.items():
        assert r["policy_id"] == fx[fid]["policy_id"]
        assert r["input_escaped"] == fx[fid]["input_escaped"]
    for s in data["summary"]:
        assert 0 <= s["exact"] <= s["ws"] <= s["ws_punct"] <= s["n"]
    assert all(v == 0 for v in (o["harness_errors"] for o in data["oracles"].values()))


def test_no_oracle_module_is_imported():
    hits = []
    for top in ("src", "tests", "scripts"):
        for dirpath, _, files in os.walk(os.path.join(ROOT, top)):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8") as f:
                        if _IMPORT.search(f.read()):
                            hits.append(os.path.relpath(path, ROOT))
    assert hits == []


def test_stress_run_record_meets_the_pilot_gate():
    with open(os.path.join(ROOT, "docs", "stress", "stats.json"), encoding="utf-8") as f:
        st = json.load(f)
    assert st["articles"] >= 50000
    assert st["crashes"] == {}
    assert st["consistency_failures"] == {}
    assert st["not_idempotent"] == {} and st["not_nfc"] == {} and st["plain_detailed_mismatch"] == {}
    assert len(st["dump"]["sha256"]) == 64 and st["dump"]["deleted_at"]


def test_lossy_review_up_to_date():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_lossy_review.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
