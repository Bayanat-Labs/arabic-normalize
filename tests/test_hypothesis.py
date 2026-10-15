# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Hypothesis property tests (optional: skipped when hypothesis is not installed).

ARNORM_HYPOTHESIS_N sets max_examples per policy (default 500; the release check runs 100,000).
"""
import os

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from arabic_normalize import normalize, normalize_detailed  # noqa: E402
from arabic_normalize import _ucd as U  # noqa: E402

N = int(os.environ.get("ARNORM_HYPOTHESIS_N", "500"))

ARABIC_HEAVY = st.one_of(
    st.characters(min_codepoint=0x0600, max_codepoint=0x06FF),
    st.characters(min_codepoint=0x0750, max_codepoint=0x08FF),
    st.characters(min_codepoint=0xFB50, max_codepoint=0xFEFF),
    st.sampled_from(["‌", "‍", "​", "‎", "‏", "⁦", "⁩", "﻿", "­",
                     " ", "\t", "\n", " ", "️", "\U0001f468", "\U0001f469", "\U0001f3fd", "्"]),
    st.characters(codec=None, blacklist_categories=()),
)
TEXTS = st.lists(ARABIC_HEAVY, max_size=40).map("".join)


@pytest.mark.parametrize("pid", ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"])
def test_hypothesis_properties(pid):
    @settings(max_examples=N, deadline=None, suppress_health_check=list(HealthCheck), database=None)
    @given(TEXTS)
    def check(s):
        res = normalize_detailed(s, pid)
        out = res.text_norm
        assert normalize(s, pid) == out
        assert normalize(out, pid) == out
        assert U.normalize_form(out, "NFC") == out
        assert len(res.offset_map) == len(out)
        for lo, hi in res.offset_map:
            assert 0 <= lo < hi <= len(s)

    check()
