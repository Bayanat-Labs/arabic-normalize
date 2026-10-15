# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Exceptions. Every rejection carries a machine-readable ``reason`` (see docs/SPEC.md section 6)."""
from __future__ import annotations


class ArabicNormalizeError(ValueError):
    """Base class: ``reason`` is a stable identifier, ``detail`` a human-readable message."""

    def __init__(self, reason: str, detail: str = "", span=None):
        self.reason = reason
        self.detail = detail
        self.span = span
        super().__init__("%s: %s" % (reason, detail) if detail else reason)


class InputRejected(ArabicNormalizeError):
    """The input text, bytes or request does not meet the input contract."""


class PolicyError(ArabicNormalizeError):
    """The policy id is unknown or the policy object is invalid."""
