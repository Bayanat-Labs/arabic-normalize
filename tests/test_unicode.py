# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Pinned Unicode data: UAX #15 conformance, table freshness and emoji ZWJ sequences."""
import gzip
import os
import subprocess
import sys

import pytest

from arabic_normalize import UNICODE_VERSION, normalize, normalize_detailed
from arabic_normalize import _ucd as U

from conftest import ROOT, UCD_DIR


def _read(name):
    with open(os.path.join(UCD_DIR, name + ".gz"), "rb") as f:
        return gzip.decompress(f.read()).decode("utf-8")


def test_unicode_version():
    assert UNICODE_VERSION == "18.0.0"


def test_tables_match_pinned_ucd():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_tables.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def _seq(field):
    return "".join(chr(int(x, 16)) for x in field.split())


def test_normalization_test_all_lines():
    nfc = lambda x: U.normalize_form(x, "NFC")  # noqa: E731
    nfd = lambda x: U.normalize_form(x, "NFD")  # noqa: E731
    nfkc = lambda x: U.normalize_form(x, "NFKC")  # noqa: E731
    nfkd = lambda x: U.normalize_form(x, "NFKD")  # noqa: E731
    part = None
    listed = set()
    lines = 0
    for raw in _read("NormalizationTest.txt").splitlines():
        if raw.startswith("@Part"):
            part = raw.split()[0]
            continue
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        c1, c2, c3, c4, c5 = [_seq(f) for f in line.split(";")[:5]]
        if part == "@Part1":
            listed.add(ord(c1))
        assert c2 == nfc(c1) == nfc(c2) == nfc(c3), raw
        assert c4 == nfc(c4) == nfc(c5), raw
        assert c3 == nfd(c1) == nfd(c2) == nfd(c3), raw
        assert c5 == nfd(c4) == nfd(c5), raw
        assert c4 == nfkc(c1) == nfkc(c2) == nfkc(c3) == nfkc(c4) == nfkc(c5), raw
        assert c5 == nfkd(c1) == nfkd(c2) == nfkd(c3) == nfkd(c4) == nfkd(c5), raw
        lines += 1
    assert lines > 20000
    # Part 1 invariant: every code point not listed is unchanged by all four forms.
    for cp in range(0x110000):
        if cp in listed or 0xD800 <= cp <= 0xDFFF:
            continue
        x = chr(cp)
        assert nfc(x) == x and nfd(x) == x and nfkc(x) == x and nfkd(x) == x, hex(cp)


def _zwj_sequences():
    seqs = []
    for raw in _read("emoji-zwj-sequences.txt").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            seqs.append(_seq(line.split(";")[0]))
    return seqs


@pytest.mark.parametrize("policy", ["bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"])
def test_every_rgi_emoji_zwj_sequence_survives(policy):
    seqs = _zwj_sequences()
    assert len(seqs) > 1000
    for s in seqs:
        text = "نص " + s + " نص"
        assert normalize(text, policy) == text, ascii(s)


def test_output_independent_of_interpreter_unicodedata():
    # U+1EE01 has a <font> decomposition in every Python version; the engine must not apply it (UCD tables only).
    assert normalize("\U0001ee01") == "\U0001ee01"
    # A character new in recent Unicode versions is handled from the pinned tables, not unicodedata.
    r = normalize_detailed("ࢗ")  # ARABIC PEPET (Unicode 16): a mark, not in the Quranic set
    assert r.text_norm == "ࢗ"
