# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""ARBML tnkeeh 0.0.9 (MIT) oracle. Calls only Tnkeeh(...).clean_raw_text.

tnkeeh imports farasa.segmenter (farasapy) at module load but uses it only when segment=True, which is never
set here. farasapy downloads a Java jar on first use, so it is not installed; an inert module stands in for it."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import run  # noqa: E402


class _NoSegmenter:
    def __init__(self, *a, **k):
        raise RuntimeError("segmentation is not used by this harness")


_farasa = types.ModuleType("farasa")
_seg = types.ModuleType("farasa.segmenter")
_seg.FarasaSegmenter = _NoSegmenter
sys.modules.setdefault("farasa", _farasa)
sys.modules.setdefault("farasa.segmenter", _seg)

import tnkeeh  # noqa: E402

_T = {
    "tnkeeh-default": tnkeeh.Tnkeeh(),
    "tnkeeh-norm": tnkeeh.Tnkeeh(normalize=True, remove_diacritics=True, remove_tatweel=True),
    "tnkeeh-asr": tnkeeh.Tnkeeh(normalize=True, remove_diacritics=True, remove_tatweel=True, remove_special_chars=True),
}


def _mk(t):
    return lambda s: t.clean_raw_text(s)[0]  # clean_raw_text returns a 1-tuple


if __name__ == "__main__":
    run({k: _mk(v) for k, v in _T.items()})
