# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""arabic-normalize by Bayanat Labs: Arabic text normalisation with named, immutable, hash-identified policies.

    >>> from arabic_normalize import normalize
    >>> normalize("إِلَى المَدْرَسَةِ")
    'الي المدرسة'

Pure Python, no runtime dependencies. Unicode data: UCD 18.0.0 (pinned). See docs/SPEC.md.
"""
from ._ucd import UNICODE_VERSION
from ._version import __version__
from .engine import (Change, DEFAULT_POLICY, MAX_RECORDS, MAX_TEXT_BYTES, Result, decode_utf8, diff_policies,
                     explain, input_stats, normalize, normalize_bytes, normalize_detailed, normalize_request,
                     parse_record, text_diac)
from .errors import ArabicNormalizeError, InputRejected, PolicyError
from .policy import Policy, canonical_json, list_policies, load_policy, policy_hash

__all__ = [
    "__version__", "UNICODE_VERSION", "DEFAULT_POLICY", "MAX_TEXT_BYTES", "MAX_RECORDS",
    "normalize", "normalize_detailed", "normalize_bytes", "normalize_request", "diff_policies", "explain",
    "text_diac", "input_stats", "decode_utf8", "parse_record",
    "Result", "Change", "Policy", "load_policy", "list_policies", "policy_hash", "canonical_json",
    "ArabicNormalizeError", "InputRejected", "PolicyError",
]
