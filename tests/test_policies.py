# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Policy identity: hashes are stable, cover behaviour only, and policies are immutable."""
import copy
import hashlib
import json
import os

import pytest

from arabic_normalize import Policy, PolicyError, canonical_json, list_policies, load_policy, normalize, policy_hash
from arabic_normalize.policy import POLICY_DIR, STAGE_MODES, STAGE_ORDER

from conftest import ROOT

# Released hashes. Changing any of these is a breaking change: ship a new policy id instead.
EXPECTED = {
    "asr-eval-v1": "5d866146536a23b90c0882044dae5f55f2484f0635e206828246eabeb69668de",
    "bayanat-norm-v1": "ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321",
    "raw-safe-v1": "57c3d9f03fb9b6854f2527cd1e8a47cadc266f47f02dda94652306dacea03bb5",
}


def test_builtin_policies():
    assert list_policies() == sorted(EXPECTED)


@pytest.mark.parametrize("pid", sorted(EXPECTED))
def test_policy_hash_stable(pid):
    p = load_policy(pid)
    assert p.policy_hash == EXPECTED[pid]
    # Independent computation from the file, following docs/SPEC.md section 2.
    with open(os.path.join(POLICY_DIR, pid + ".json"), encoding="utf-8") as f:
        data = json.load(f)
    body = {k: v for k, v in data.items() if k != "meta"}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    assert hashlib.sha256(blob).hexdigest() == EXPECTED[pid]
    assert hashlib.sha256(p.canonical().encode("utf-8")).hexdigest() == EXPECTED[pid]


@pytest.mark.parametrize("pid", sorted(EXPECTED))
def test_meta_does_not_change_hash_but_stages_do(pid):
    data = copy.deepcopy(load_policy(pid).data)
    data["meta"]["title_ar"] = data["meta"]["title_ar"] + " (مراجعة)"
    assert policy_hash(data) == EXPECTED[pid]
    data["stages"]["latin_case"] = "lower" if data["stages"]["latin_case"] == "keep" else "keep"
    assert policy_hash(data) != EXPECTED[pid]


@pytest.mark.parametrize("pid", sorted(EXPECTED))
def test_policy_matches_schema(pid, jsonschema_mod):
    with open(os.path.join(POLICY_DIR, "schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema_mod.validate(load_policy(pid).data, schema)


def test_schema_and_code_agree_on_stages():
    with open(os.path.join(POLICY_DIR, "schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    props = schema["properties"]["stages"]["properties"]
    assert set(props) == set(STAGE_MODES) == set(STAGE_ORDER)
    for k, modes in STAGE_MODES.items():
        assert set(props[k]["enum"]) == set(modes)


def test_policy_is_immutable():
    p = load_policy("bayanat-norm-v1")
    with pytest.raises(AttributeError):
        p.policy_id = "x"
    with pytest.raises(TypeError):
        p.stages["tatweel"] = "keep"
    d = p.data
    d["stages"]["tatweel"] = "keep"  # a deep copy: does not affect the policy
    assert load_policy("bayanat-norm-v1").stages["tatweel"] == "strip"
    assert normalize("جمـيل") == "جميل"


def test_inline_custom_policy_and_file(tmp_path):
    data = copy.deepcopy(load_policy("bayanat-norm-v1").data)
    data["policy_id"] = "custom-diacritics-kept"
    data["stages"]["diacritics"] = "keep"
    data.pop("meta")
    p = Policy(data)
    assert normalize("كَتَبَ", p) == "كَتَبَ"
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_policy(str(path)).policy_hash == p.policy_hash


def test_canonical_json_is_ascii_for_builtins():
    for pid in EXPECTED:
        assert all(ord(c) < 128 for c in load_policy(pid).canonical())


def test_nested_dollar_member_rejected():
    data = copy.deepcopy(load_policy("raw-safe-v1").data)
    data["meta"]["$ref"] = "https://example.org/x"
    with pytest.raises(PolicyError) as ei:
        Policy(data)
    assert ei.value.reason == "remote_ref_not_allowed"


def test_changelog_records_policy_hashes():
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    for pid, h in EXPECTED.items():
        assert pid in text and h in text
