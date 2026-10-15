# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""All pilot conformance fixtures (64 dev + 16 acceptance) must pass exactly."""
import json
import os
import re

import pytest

from arabic_normalize import normalize, normalize_detailed

from conftest import ROOT, fixtures

DEV = fixtures("dev")
ACC = fixtures("acceptance")
ALL = DEV + ACC


def test_fixture_counts():
    assert len(DEV) == 64
    assert len(ACC) == 16
    assert len({f["fixture_id"] for f in ALL}) == 80
    assert all(f["synthetic"] is True and f["label"] == "synthetic/illustrative, authored by Bayanat Labs" for f in ALL)


@pytest.mark.parametrize("fx", ALL, ids=[f["fixture_id"] for f in ALL])
def test_fixture(fx):
    res = normalize_detailed(fx["input"], fx["policy_id"])
    assert res.text_norm == fx["expected_output"]
    assert normalize(fx["input"], fx["policy_id"]) == res.text_norm, "plain and detailed modes disagree"
    assert list(res.rules) == fx["expected_rules"]
    assert list(res.lossy_flags) == fx["expected_lossy_flags"]
    assert list(res.flags) == fx["expected_flags"]
    assert [dict(x) for x in res.rejected_spans] == fx["expected_rejected_spans"]
    if fx["expected_offset_map"] is not None:
        assert [list(x) for x in res.offset_map] == fx["expected_offset_map"]
    if fx["expected_diacritization_ratio"] is not None:
        assert res.diacritization_ratio == pytest.approx(fx["expected_diacritization_ratio"], abs=1e-12)
    assert len(res.offset_map) == len(res.text_norm)


_ESC = re.compile(r"\\u([0-9a-f]{4})|\\U([0-9a-f]{8})")


@pytest.mark.parametrize("fx", ALL, ids=[f["fixture_id"] for f in ALL])
def test_fixture_input_escaped_matches(fx):
    unescaped = _ESC.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), fx["input_escaped"])
    assert unescaped == fx["input"]


def test_fixtures_match_schema(jsonschema_mod):
    with open(os.path.join(ROOT, "schemas", "fixture.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    for fx in ALL:
        jsonschema_mod.validate(fx, schema)


def test_provenance_rows_cover_every_fixture():
    from conftest import FIXTURES, load_jsonl
    prov = load_jsonl(os.path.join(FIXTURES, "PROVENANCE.jsonl"))
    ids = {p["fixture_id"] for p in prov}
    assert ids == {f["fixture_id"] for f in ALL + fixtures("rejected")}
    assert all(p["license"] == "CC-BY-4.0" and len(p["sha256"]) == 64 for p in prov)
