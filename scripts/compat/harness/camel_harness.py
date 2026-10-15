# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""CAMeL Tools 1.6.0 (MIT) oracle. Calls only public functions of camel_tools.utils (normalize, dediac)."""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import run  # noqa: E402

from camel_tools.utils.dediac import dediac_ar  # noqa: E402
from camel_tools.utils.normalize import (  # noqa: E402
    normalize_alef_ar, normalize_alef_maksura_ar, normalize_teh_marbuta_ar, normalize_unicode)


def nfc(s):
    return normalize_unicode(s, compatibility=False)


def norm(s):
    return normalize_alef_maksura_ar(normalize_alef_ar(dediac_ar(normalize_unicode(s))))


def asr(s):
    return normalize_teh_marbuta_ar(norm(s))


if __name__ == "__main__":
    if sys.argv[1:] == ["--version"]:
        import camel_tools
        print(camel_tools.__version__ if hasattr(camel_tools, "__version__") else "1.6.0", unicodedata.unidata_version)
        sys.exit(0)
    run({"camel-nfc": nfc, "camel-norm": norm, "camel-asr": asr})
