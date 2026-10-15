# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Public API behaviour beyond the fixtures."""
import pytest

import arabic_normalize as an


def test_public_names():
    for name in an.__all__:
        assert hasattr(an, name), name
    assert an.__version__ == "0.1.0"
    assert an.DEFAULT_POLICY == "bayanat-norm-v1"


def test_worked_example():
    text = "إِلَى المَدْرَسَةِ ١٢"
    r = an.normalize_detailed(text)
    assert r.text_norm == "الي المدرسة 12"
    assert r.lossy_flags == ("alef_maqsura.to_yeh", "alef_variants.map")
    assert r.flags == ("taa_marbuta.flag",)
    assert r.stats["rules"]["diacritics.strip"] == 7
    assert r.stats["classes"]["arabic_letters"] == 10
    assert r.diacritization_ratio == pytest.approx(0.7)
    assert an.normalize(text, "asr-eval-v1") == "الي المدرسه 12"
    assert an.normalize(text, "raw-safe-v1") == text


def test_result_is_immutable_and_serialisable():
    r = an.normalize_detailed("على")
    with pytest.raises(AttributeError):
        r.text_norm = "x"
    d = r.to_dict(text_raw="على", record_id="r1")
    assert d["record_id"] == "r1" and d["text_raw"] == "على"
    assert d["changes"][0]["rule_id"] == "alef_maqsura.to_yeh" and d["changes"][0]["lossy"] is True
    assert d["text_diac"] is None


def test_text_diac():
    assert an.text_diac("كَتَبَ‏") == "كَتَبَ"
    assert an.text_diac("كتب") is None


def test_request_contract():
    assert an.normalize_request({"text": "على"}) == ["علي"]
    out = an.normalize_request({"texts": ["ة", "ى"], "policy": "asr-eval-v1", "detailed": True})
    assert [o["text_norm"] for o in out] == ["ه", "ي"]
    for bad, reason in [({}, "invalid_request"), ({"text": "a", "texts": ["b"]}, "invalid_request"),
                        ({"text": "a", "extra": 1}, "unknown_member"), ({"text": 5}, "text_not_string"),
                        ({"texts": "abc"}, "invalid_request")]:
        with pytest.raises(an.InputRejected) as ei:
            an.normalize_request(bad)
        assert ei.value.reason == reason
    assert an.normalize_request({"text": "x" * an.MAX_TEXT_BYTES}) == ["x" * an.MAX_TEXT_BYTES]


def test_bytes_bom_and_decoding():
    assert an.normalize_bytes(b"\xef\xbb\xbf" + "نص".encode("utf-8")) == "نص"
    with pytest.raises(an.InputRejected) as ei:
        an.normalize_bytes(b"\xd8")
    assert ei.value.reason == "invalid_utf8"


def test_diff_policies_and_explain():
    d = an.diff_policies("مدرسة", "bayanat-norm-v1", "asr-eval-v1")
    assert not d["identical"]
    assert d["regions"] == [{"src_start": 4, "src_end": 5, "source": "ة", "a": "ة", "b": "ه"}]
    e = an.explain("ـا")
    assert e["rows"][0]["rules"] == ["tatweel.strip"] and e["rows"][0]["output"] == ""
    assert e["rows"][1]["rules"] == [] and e["rows"][1]["output"] == "ا"


def test_nfkc_custom_policy():
    data = an.load_policy("bayanat-norm-v1").data
    data.update({"policy_id": "custom-nfkc"})
    data["unicode_form"] = "NFKC"
    data["stages"]["ligatures_honorific"] = "expand"
    r = an.normalize_detailed("ﷺ x²", data)
    assert r.text_norm == "صلي الله عليه وسلم x2"
    assert "canonical_order.nfkc" in r.lossy_flags
    assert "ligatures_honorific.expand" in r.rules
