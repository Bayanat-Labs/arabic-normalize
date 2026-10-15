# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Whisper BasicTextNormalizer oracle via whisper-normalizer 0.1.15 (MIT), which packages OpenAI Whisper's
basic normaliser. Calls only BasicTextNormalizer(...)(text)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import run  # noqa: E402

from whisper_normalizer.basic import BasicTextNormalizer  # noqa: E402

if __name__ == "__main__":
    run({"whisper-basic": BasicTextNormalizer(),
         "whisper-basic-rd": BasicTextNormalizer(remove_diacritics=True)})
