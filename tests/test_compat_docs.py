# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""The oracle agreement tables match the fixture files. No GPL tool is imported anywhere in this repository, and
the MIT-licensed oracle tools are imported only by their harnesses in scripts/compat/harness/, which run as
subprocesses in their own virtual environments."""
import json
import os
import re

from conftest import ROOT, fixtures

GPL_MODULES = ("pyarabic", "mishkal", "qalsadi")
MIT_ORACLE_MODULES = ("camel_tools", "tnkeeh", "whisper_normalizer", "whisper", "farasa")
ORACLE_MODULES = GPL_MODULES + MIT_ORACLE_MODULES
HARNESS_DIR = os.path.join("scripts", "compat", "harness")
_IMPORT = re.compile(r"^\s*(?:import|from)\s+(%s)\b" % "|".join(ORACLE_MODULES), re.M)
_GPL_IMPORT = re.compile(r"^\s*(?:import|from)\s+(%s)\b" % "|".join(GPL_MODULES), re.M)


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


def _python_files():
    for top in ("src", "tests", "scripts", "web", "js"):
        for dirpath, _, files in os.walk(os.path.join(ROOT, top)):
            for name in files:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def test_no_oracle_module_is_imported_outside_the_harnesses():
    hits = []
    for path in _python_files():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if _GPL_IMPORT.search(text) or (_IMPORT.search(text) and os.path.dirname(rel) != HARNESS_DIR):
            hits.append(rel)
    assert hits == []


def test_harnesses_are_mit_tools_only():
    names = sorted(n for n in os.listdir(os.path.join(ROOT, HARNESS_DIR)) if n.endswith(".py"))
    assert names == ["_common.py", "camel_harness.py", "tnkeeh_harness.py", "whisper_harness.py"]


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


def test_other_stress_corpora_records():
    """Every extra stress corpus (docs/stress/<name>.json other than stats.json) is crash-free and consistent."""
    found = []
    stress = os.path.join(ROOT, "docs", "stress")
    for name in sorted(n[:-5] for n in os.listdir(stress) if n.endswith(".json") and n != "stats.json"):
        path = os.path.join(stress, name + ".json")
        found.append(name)
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        assert rec["runs"]
        for run in rec["runs"]:
            assert run["texts"] > 0
            assert run["crashes"] == {} and run["consistency_failures"] == {}
            assert run["not_idempotent"] == {} and run["not_nfc"] == {} and run["plain_detailed_mismatch"] == {}
            assert all(len(f["sha256"]) == 64 for f in run["source"]["files"])
    assert "fleurs" in found
