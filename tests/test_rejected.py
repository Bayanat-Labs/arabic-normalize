# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Every explicit rejected-input example is rejected with its documented reason."""
import copy
import json

import pytest

from arabic_normalize import (ArabicNormalizeError, load_policy, normalize, normalize_bytes, normalize_request,
                              parse_record)

from conftest import fixtures

REJ = fixtures("rejected")


def _patched_policy(base, patch):
    data = copy.deepcopy(load_policy(base).data)
    for key, value in patch.items():
        if key.startswith("stages."):
            data["stages"][key.split(".", 1)[1]] = value
        else:
            data[key] = value
    return data


def _run(fx):
    kind = fx["kind"]
    if kind == "bytes":
        normalize_bytes(bytes.fromhex(fx["input_hex"]))
    elif kind == "text_strict":
        normalize(fx["input"], fx["policy_id"], strict=True)
    elif kind == "generated_text":
        g = fx["generate"]
        normalize_request({"text": g["repeat"] * g["count"], "policy": fx["policy_id"]})
    elif kind == "generated_records":
        g = fx["generate"]
        normalize_request({"texts": [g["text"]] * g["count"], "policy": fx["policy_id"]})
    elif kind == "policy_id":
        normalize("نص", fx["policy_id"])
    elif kind == "policy":
        normalize_request({"text": "نص", "policy": fx["policy"]})
    elif kind == "policy_patch":
        normalize("نص", _patched_policy(fx["base"], fx["patch"]))
    elif kind == "jsonl_line":
        _, text = parse_record(fx["line"], fx["field"])
        normalize(text, fx["policy_id"])
    else:
        raise AssertionError("unknown fixture kind %r" % kind)


def test_at_least_ten_rejected_examples():
    assert len(REJ) >= 10


@pytest.mark.parametrize("fx", REJ, ids=[f["fixture_id"] for f in REJ])
def test_rejected(fx):
    with pytest.raises(ArabicNormalizeError) as ei:
        _run(fx)
    assert ei.value.reason == fx["expected_reason"]


def test_same_inputs_without_strict_are_dropped_not_rejected():
    for fx in REJ:
        if fx["kind"] == "text_strict":
            out = normalize(fx["input"], fx["policy_id"])
            assert out == "نص"
