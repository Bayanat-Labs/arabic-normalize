# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Property tests on random Arabic-heavy strings (seeded, stdlib only).

ARNORM_PROPERTY_N sets the number of strings per policy (default 3,000; the release check runs 100,000).
"""
import os
import random

import pytest

from arabic_normalize import load_policy, normalize, normalize_detailed
from arabic_normalize import _ucd as U
from arabic_normalize import engine as E

N = int(os.environ.get("ARNORM_PROPERTY_N", "3000"))
POLICIES = ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"]

_POOLS = [
    (40, list(range(0x0621, 0x063B)) + list(range(0x0641, 0x064B))),  # Arabic letters
    (12, list(range(0x064B, 0x0656)) + [0x0670]),                     # harakat, hamza marks, superscript alef
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
    (1, None),  # any code point
]
_WEIGHTS = [w for w, _ in _POOLS]


def _rand_text(rng):
    n = rng.randint(0, 40)
    out = []
    for _ in range(n):
        pool = rng.choices(_POOLS, weights=_WEIGHTS)[0][1]
        out.append(chr(rng.randrange(0x110000)) if pool is None else chr(rng.choice(pool)))
    return "".join(out)


def _strings(seed):
    rng = random.Random(seed)
    return [_rand_text(rng) for _ in range(N)]


INVISIBLE = frozenset(E.BIDI | {E.ZWSP, E.ZWNJ, E.ZWJ, E.BOM} | E.FORMAT_CONTROLS)


def _strip_invisible(s):
    return "".join(c for c in s if ord(c) not in INVISIBLE and not E.REJECT_RE.match(c))


@pytest.mark.parametrize("pid", POLICIES)
def test_properties(pid):
    policy = load_policy(pid)
    for s in _strings(20261015 + POLICIES.index(pid)):
        res = normalize_detailed(s, policy)
        out = res.text_norm
        # Plain and detailed modes agree.
        assert normalize(s, policy) == out, ascii(s)
        # Idempotence (declared by every pilot policy).
        if policy.idempotent:
            assert normalize(out, policy) == out, ascii(s)
        # Output is NFC and contains no rejected code point.
        assert U.normalize_form(out, "NFC") == out, ascii(s)
        assert E.REJECT_RE.search(out) is None, ascii(s)
        # Offset map: one in-range span per output code point.
        assert len(res.offset_map) == len(out)
        for lo, hi in res.offset_map:
            assert 0 <= lo < hi <= len(s), ascii(s)
        # Starts are non-decreasing unless canonical reordering moved a mark.
        if not any(c.rule_id.startswith("canonical_order") for c in res.changes):
            starts = [lo for lo, _ in res.offset_map]
            assert starts == sorted(starts), ascii(s)
        # No silent normalisation: every input code point outside all change spans is copied unchanged.
        covered = [False] * len(s)
        for c in res.changes:
            assert 0 <= c.src_start < c.src_end <= len(s)
            for k in range(c.src_start, c.src_end):
                covered[k] = True
        copies = {}
        for i, (lo, hi) in enumerate(res.offset_map):
            if hi == lo + 1 and not covered[lo]:
                copies.setdefault(lo, []).append(out[i])
        for k in range(len(s)):
            if not covered[k]:
                assert copies.get(k) == [s[k]], (ascii(s), k)
        # Lossy flags are exactly the lossy rules in the change log.
        assert list(res.lossy_flags) == sorted({c.rule_id for c in res.changes if c.lossy})


def test_raw_safe_changes_only_nfc_and_invisible_controls():
    for s in _strings(7):
        out = normalize(s, "raw-safe-v1")
        assert U.normalize_form(_strip_invisible(out), "NFC") == U.normalize_form(_strip_invisible(s), "NFC"), ascii(s)


def test_bayanat_norm_equals_raw_safe_then_bayanat_norm():
    # Normalising text_diac (raw-safe-v1 output) with bayanat-norm-v1 gives the same text_norm.
    for s in _strings(11):
        assert normalize(normalize(s, "raw-safe-v1"), "bayanat-norm-v1") == normalize(s, "bayanat-norm-v1"), ascii(s)


def test_no_super_linear_runtime():
    import time
    for chunk in ("ـ", "َ", "‌", " ", "أ", "ﻻ"):
        small = chunk * 2000
        big = chunk * 40000
        t0 = time.perf_counter()
        normalize_detailed(small)
        t1 = time.perf_counter()
        normalize_detailed(big)
        t2 = time.perf_counter()
        # 20x the input must take well under 20^2 = 400x the time (allow generous noise).
        assert (t2 - t1) < max(0.05, (t1 - t0) * 80), chunk
