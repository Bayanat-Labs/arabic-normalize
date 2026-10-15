# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Blind acceptance-b candidates (16 cases written by a second session without engine access).

They are not part of the 80 pilot fixtures; see tests/fixtures/candidates/README.md.
"""
import os

import pytest

from arabic_normalize import normalize, normalize_detailed

from conftest import FIXTURES, load_jsonl

CANDIDATES = load_jsonl(os.path.join(FIXTURES, "candidates", "acceptance-b.jsonl"))


def test_candidate_count_and_labels():
    assert len(CANDIDATES) == 16
    assert len({c["fixture_id"] for c in CANDIDATES}) == 16
    assert all(c["synthetic"] is True and c["label"] == "synthetic/illustrative, authored by Bayanat Labs"
               and c["split"] == "acceptance-b" for c in CANDIDATES)


def test_candidate_families_do_not_occur_in_dev():
    from conftest import fixtures
    dev_families = {f["family"] for f in fixtures("dev")}
    assert not dev_families & {c["family"] for c in CANDIDATES}


@pytest.mark.parametrize("fx", CANDIDATES, ids=[c["fixture_id"] for c in CANDIDATES])
def test_candidate(fx):
    res = normalize_detailed(fx["input"], fx["policy_id"])
    assert res.text_norm == fx["expected_output"]
    assert normalize(fx["input"], fx["policy_id"]) == res.text_norm
    assert list(res.rules) == fx["expected_rules"]
    assert list(res.lossy_flags) == fx["expected_lossy_flags"]
    assert list(res.flags) == fx["expected_flags"]
    assert [dict(x) for x in res.rejected_spans] == fx["expected_rejected_spans"]
    if fx["expected_offset_map"] is not None:
        assert [list(x) for x in res.offset_map] == fx["expected_offset_map"]
    if fx["expected_diacritization_ratio"] is not None:
        assert res.diacritization_ratio == pytest.approx(fx["expected_diacritization_ratio"], abs=1e-12)


def test_candidate_provenance_rows():
    import hashlib
    prov = load_jsonl(os.path.join(FIXTURES, "candidates", "PROVENANCE.jsonl"))
    with open(os.path.join(FIXTURES, "candidates", "acceptance-b.jsonl"), encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]
    assert [p["fixture_id"] for p in prov] == [c["fixture_id"] for c in CANDIDATES]
    assert [p["sha256"] for p in prov] == [hashlib.sha256(line.encode("utf-8")).hexdigest() for line in lines]
    assert all(p["license"] == "CC-BY-4.0" for p in prov)
