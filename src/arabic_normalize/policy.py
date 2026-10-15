# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Named, immutable normalisation policies and their SHA-256 identity (docs/SPEC.md section 2)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import types

from ._ucd import UNICODE_VERSION
from .errors import PolicyError

POLICY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policies")
SPEC_ID = "arabic-normalize-spec-1"

STAGE_ORDER = (
    "reject_invalid", "strip_controls", "presentation_forms", "ligatures_honorific", "bidi_zw",
    "tatweel", "diacritics", "quranic_marks", "superscript_alef", "alef_variants", "alef_maqsura",
    "taa_marbuta", "hamza_carriers", "persian_urdu_letters", "digits", "punctuation", "whitespace", "latin_case",
)
STAGE_MODES = {
    "reject_invalid": ("drop", "error"),
    "strip_controls": ("strip", "keep"),
    "presentation_forms": ("map", "keep", "flag"),
    "ligatures_honorific": ("keep", "flag", "expand"),
    "bidi_zw": ("keep", "strip", "strip-except-zwnj", "strip-except-emoji-zwj", "strip-except-meaningful"),
    "tatweel": ("strip", "keep"),
    "diacritics": ("keep", "strip", "strip-except-shadda"),
    "quranic_marks": ("strip", "keep"),
    "superscript_alef": ("keep", "strip", "to-alef"),
    "alef_variants": ("map", "keep"),
    "alef_maqsura": ("to-yeh", "keep", "flag"),
    "taa_marbuta": ("keep", "flag", "to-heh"),
    "hamza_carriers": ("keep", "fold"),
    "persian_urdu_letters": ("map", "keep"),
    "digits": ("keep", "ascii", "arabic-indic"),
    "punctuation": ("keep", "ascii", "strip"),
    "whitespace": ("collapse", "keep"),
    "latin_case": ("keep", "lower"),
}
TOP_MEMBERS = ("policy_id", "version", "spec", "unicode_version", "unicode_form", "idempotent", "stages", "meta")
META_MEMBERS = ("title_en", "title_ar", "description_en", "license", "attribution", "created", "status")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


def canonical_json(obj) -> str:
    """Canonical JSON: keys sorted at every level, separators ',' and ':', no whitespace, UTF-8 (no escaping)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def policy_hash(obj) -> str:
    """SHA-256 of the canonical JSON of the policy without its top-level ``meta`` member."""
    if isinstance(obj, Policy):
        return obj.policy_hash
    body = {k: v for k, v in obj.items() if k != "meta"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _check_no_dollar(obj, path="policy"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("$"):
                raise PolicyError("remote_ref_not_allowed",
                                  "%s.%s: members starting with '$' are not allowed; nothing is fetched" % (path, k))
            _check_no_dollar(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_no_dollar(v, "%s[%d]" % (path, i))


def validate_policy(obj) -> None:
    """Raise PolicyError with a reason if ``obj`` is not a valid policy (no network access, ever)."""
    if not isinstance(obj, dict):
        raise PolicyError("invalid_policy", "a policy must be a JSON object")
    _check_no_dollar(obj)
    for k in obj:
        if k not in TOP_MEMBERS:
            raise PolicyError("unknown_member", "unknown policy member %r" % k)
    for k in TOP_MEMBERS[:-1]:
        if k not in obj:
            raise PolicyError("missing_member", "policy member %r is required" % k)
    pid = obj["policy_id"]
    if not isinstance(pid, str) or not _ID_RE.match(pid):
        raise PolicyError("invalid_policy_id", "policy_id must match %s" % _ID_RE.pattern)
    if not isinstance(obj["version"], int) or isinstance(obj["version"], bool) or obj["version"] < 1:
        raise PolicyError("invalid_member", "version must be a positive integer")
    if obj["spec"] != SPEC_ID:
        raise PolicyError("unsupported_spec", "spec must be %r" % SPEC_ID)
    if obj["unicode_version"] != UNICODE_VERSION:
        raise PolicyError("unsupported_unicode_version",
                          "this release ships UCD %s tables only (got %r)" % (UNICODE_VERSION, obj["unicode_version"]))
    if obj["unicode_form"] not in ("NFC", "NFKC", "none"):
        raise PolicyError("invalid_member", "unicode_form must be NFC, NFKC or none")
    if not isinstance(obj["idempotent"], bool):
        raise PolicyError("invalid_member", "idempotent must be true or false")
    stages = obj["stages"]
    if not isinstance(stages, dict):
        raise PolicyError("invalid_member", "stages must be an object")
    for k in stages:
        if k not in STAGE_MODES:
            raise PolicyError("unknown_stage", "unknown stage %r" % k)
    for k, modes in STAGE_MODES.items():
        if k not in stages:
            raise PolicyError("missing_stage", "stage %r is required" % k)
        if stages[k] not in modes:
            raise PolicyError("invalid_stage_value", "stage %r has no mode %r (allowed: %s)" % (k, stages[k], ", ".join(modes)))
    if obj["unicode_form"] == "NFKC" and (stages["presentation_forms"] != "map" or stages["ligatures_honorific"] != "expand"):
        raise PolicyError("inconsistent_policy",
                          "unicode_form NFKC already maps presentation forms and expands ligatures; "
                          "set presentation_forms: map and ligatures_honorific: expand")
    meta = obj.get("meta")
    if meta is not None:
        if not isinstance(meta, dict):
            raise PolicyError("invalid_member", "meta must be an object")
        for k, v in meta.items():
            if k not in META_MEMBERS:
                raise PolicyError("unknown_member", "unknown meta member %r" % k)
            if not isinstance(v, str):
                raise PolicyError("invalid_member", "meta.%s must be a string" % k)


class Policy(object):
    """A validated, immutable policy. ``policy_hash`` identifies its behaviour."""

    __slots__ = ("_data", "policy_id", "policy_hash", "stages", "unicode_form", "idempotent", "builtin")

    def __init__(self, data, builtin=False):
        validate_policy(data)
        object.__setattr__(self, "_data", copy.deepcopy(data))
        object.__setattr__(self, "policy_id", data["policy_id"])
        object.__setattr__(self, "policy_hash", policy_hash(data))
        object.__setattr__(self, "stages", types.MappingProxyType(dict(data["stages"])))
        object.__setattr__(self, "unicode_form", data["unicode_form"])
        object.__setattr__(self, "idempotent", data["idempotent"])
        object.__setattr__(self, "builtin", builtin)

    def __setattr__(self, k, v):
        raise AttributeError("Policy objects are immutable")

    @property
    def data(self):
        """A deep copy of the full policy object (including meta)."""
        return copy.deepcopy(self._data)

    def __repr__(self):
        return "Policy(%r, sha256=%s)" % (self.policy_id, self.policy_hash[:12])

    def __eq__(self, other):
        return isinstance(other, Policy) and other.policy_hash == self.policy_hash

    def __hash__(self):
        return hash(self.policy_hash)

    def to_json(self, indent=2) -> str:
        """Pretty JSON of the full policy (with meta), stages in pipeline order."""
        d = {k: self._data[k] for k in TOP_MEMBERS if k in self._data}
        d["stages"] = {k: self._data["stages"][k] for k in STAGE_ORDER}
        return json.dumps(d, ensure_ascii=False, indent=indent)

    def canonical(self) -> str:
        return canonical_json({k: v for k, v in self._data.items() if k != "meta"})


_BUILTIN = {}


def list_policies():
    """Ids of the built-in policies, sorted."""
    return sorted(f[:-5] for f in os.listdir(POLICY_DIR) if f.endswith(".json") and f != "schema.json")


def _load_builtin(pid):
    p = _BUILTIN.get(pid)
    if p is None:
        if pid not in list_policies():
            raise PolicyError("unknown_policy", "no built-in policy %r (available: %s)" % (pid, ", ".join(list_policies())))
        with open(os.path.join(POLICY_DIR, pid + ".json"), encoding="utf-8") as f:
            data = json.load(f)
        if data.get("policy_id") != pid:
            raise PolicyError("invalid_policy", "built-in file %s.json has policy_id %r" % (pid, data.get("policy_id")))
        p = _BUILTIN[pid] = Policy(data, builtin=True)
    return p


def load_policy(policy) -> Policy:
    """Return a Policy from a built-in id, a path to a JSON file, a dict, or a Policy."""
    if isinstance(policy, Policy):
        return policy
    if isinstance(policy, dict):
        return Policy(policy)
    if isinstance(policy, str):
        if policy in _BUILTIN or _ID_RE.match(policy) and not policy.endswith(".json"):
            return _load_builtin(policy)
        if os.path.isfile(policy):
            with open(policy, encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except ValueError as e:
                    raise PolicyError("invalid_json", "policy file %s: %s" % (policy, e))
            return Policy(data)
        raise PolicyError("unknown_policy", "no built-in policy or file named %r" % policy)
    raise PolicyError("invalid_policy", "policy must be an id, a path, a dict or a Policy")
