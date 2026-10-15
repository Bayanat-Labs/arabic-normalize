# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""The arabic-normalize engine: stages of docs/SPEC.md applied in a fixed order.

Every stage produces edits on the current string. In detailed mode the edits are composed into an offset
map (output code point -> input span) and a change log; in plain mode only the string is built. Both modes
run the same edit-finding code, so they always give the same text.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import namedtuple

from . import _ucd as U
from ._version import __version__
from .errors import InputRejected
from .policy import load_policy

MAX_TEXT_BYTES = 10 * 1024 * 1024
MAX_RECORDS = 10000
DEFAULT_POLICY = "bayanat-norm-v1"

LOSSY_RULES = frozenset({
    "alef_variants.map", "alef_maqsura.to_yeh", "taa_marbuta.to_heh", "hamza_carriers.fold",
    "persian_urdu_letters.map", "latin_case.lower", "canonical_order.nfkc",
})

Change = namedtuple("Change", "stage rule_id src_start src_end before after lossy")


def _cps(*ranges):
    out = set()
    for r in ranges:
        if isinstance(r, tuple):
            out.update(range(r[0], r[1] + 1))
        else:
            out.add(r)
    return frozenset(out)


def _re(cps):
    return U.CharMatcher(cps)


# --- Character sets (docs/SPEC.md section 4) -----------------------------------------------------------
SURROGATES = _cps((0xD800, 0xDFFF))
ALLOWED_CONTROLS = frozenset(U.CONTROLS & U.WHITE_SPACE)
REJECT_CONTROLS = frozenset(U.CONTROLS - ALLOWED_CONTROLS)
REJECT_RE = _re(SURROGATES | REJECT_CONTROLS | U.NONCHARACTERS)

FORMAT_CONTROLS = _cps(0x00AD, 0x2060, (0x2061, 0x2064), (0x206A, 0x206F), (0xFFF9, 0xFFFB))
BOM = 0xFEFF

HONORIFIC = _cps((0x0610, 0x0614), (0xFD40, 0xFD4F), 0xFDCF, (0xFDF0, 0xFDFF), (0x10ED1, 0x10ED8))
PF = frozenset(c for c in _cps((0xFB50, 0xFDFF), (0xFE70, 0xFEFF))
               if c in U.COMPAT_DECOMPOSABLE and c not in HONORIFIC)
PF_MAP = {c: U.normalize_form(chr(c), "NFKC") for c in sorted(PF)}
H_EXPAND = {c: U.normalize_form(chr(c), "NFKC") for c in sorted(HONORIFIC) if c in U.COMPAT_DECOMPOSABLE}

ZWSP, ZWNJ, ZWJ = 0x200B, 0x200C, 0x200D
BIDI = U.BIDI_CONTROLS
BIDI_ZW_RE = _re(BIDI | {ZWSP, ZWNJ, ZWJ})
EMOJI_SKIP = frozenset(U.EMOJI_MODIFIER | {0xFE0E, 0xFE0F} | set(range(0xE0020, 0xE0080)))

TATWEEL = 0x0640
HARAKAT = _cps((0x064B, 0x0652))
SHADDA = 0x0651
QURANIC = _cps((0x0615, 0x061A), 0x0653, (0x0656, 0x0658), (0x06D6, 0x06ED), (0x0898, 0x089F),
               (0x08CA, 0x08E2), (0x08E3, 0x08E9), (0x08F0, 0x08F3), 0x08FF, (0x10EFD, 0x10EFF))
SUPERSCRIPT_ALEF = 0x0670
ALEF = 0x0627
ALEF_VARIANTS = _cps(0x0622, 0x0623, 0x0625, 0x0671)
HAMZA_MARKS = _cps(0x0653, 0x0654, 0x0655)
HAMZA_ABOVE = 0x0654
HAMZA_CARRIERS = {0x0624: 0x0648, 0x0626: 0x064A}
HAMZA_BASES = _cps(0x0648, 0x064A, 0x0649, 0x0624, 0x0626)
ALEF_MAQSURA, YEH = 0x0649, 0x064A
TAA_MARBUTA, HEH = 0x0629, 0x0647
PERSIAN_URDU = {0x06CC: 0x064A, 0x06A9: 0x0643, 0x06C1: 0x0647, 0x06C2: 0x0647, 0x06BE: 0x0647,
                0x06D5: 0x0647, 0x06C0: 0x0647}
ARABIC_INDIC = _cps((0x0660, 0x0669))
EXT_ARABIC_INDIC = _cps((0x06F0, 0x06F9))
PUNCT_ASCII = {0x060C: ",", 0x061B: ";", 0x061F: "?", 0x066A: "%", 0x066B: ".", 0x066C: ",", 0x06D4: ".",
               0x066D: "*", 0x00AB: '"', 0x00BB: '"'}
WS_RUN_RE = re.compile(U.char_class(U.WHITE_SPACE) + "+")

PF_RE = _re(PF)
HONORIFIC_RE = _re(HONORIFIC)
H_REMAIN_RE = _re(HONORIFIC - set(H_EXPAND))
ARABIC_LETTER_RE = _re(U.ARABIC_LETTERS)
PF_TRANS = {c: v for c, v in PF_MAP.items()}


class _MapStage(object):
    """A context-free per-code-point mapping with one rule id per code point."""

    __slots__ = ("stage", "rules", "reps", "regex", "trans")

    def __init__(self, stage, mapping):
        # mapping: {cp: (replacement_str, rule_id)}
        self.stage = stage
        self.reps = {c: v[0] for c, v in mapping.items()}
        self.rules = {c: v[1] for c, v in mapping.items()}
        self.regex = _re(mapping) if mapping else None
        self.trans = {c: (v if v else None) for c, v in self.reps.items()}

    def run(self, ctx, s):
        if not self.reps:
            return s
        if not ctx.detailed:
            if self.regex.search(s) is None:
                return s
            return s.translate(self.trans)
        edits = []
        for m in self.regex.finditer(s):
            c = ord(m.group())
            edits.append((m.start(), m.end(), self.reps[c], self.rules[c], None))
        return ctx.apply(s, edits, self.stage)


def _map(stage, cps, rep, rule):
    return _MapStage(stage, {c: (rep(c) if callable(rep) else rep, rule) for c in cps})


_STAGES = {
    ("strip_controls", "strip"): _MapStage("strip_controls", dict(
        [(c, ("", "strip_controls.format")) for c in FORMAT_CONTROLS] + [(BOM, ("", "strip_controls.bom"))])),
    ("presentation_forms", "map"): _map("presentation_forms", PF, lambda c: PF_MAP[c], "presentation_forms.map"),
    ("ligatures_honorific", "expand"): _map("ligatures_honorific", H_EXPAND, lambda c: H_EXPAND[c],
                                            "ligatures_honorific.expand"),
    ("tatweel", "strip"): _map("tatweel", [TATWEEL], "", "tatweel.strip"),
    ("diacritics", "strip"): _map("diacritics", HARAKAT, "", "diacritics.strip"),
    ("diacritics", "strip-except-shadda"): _map("diacritics", HARAKAT - {SHADDA}, "", "diacritics.strip"),
    ("quranic_marks", "strip"): _map("quranic_marks", QURANIC, "", "quranic_marks.strip"),
    ("superscript_alef", "strip"): _map("superscript_alef", [SUPERSCRIPT_ALEF], "", "superscript_alef.strip"),
    ("superscript_alef", "to-alef"): _map("superscript_alef", [SUPERSCRIPT_ALEF], chr(ALEF), "superscript_alef.to_alef"),
    ("alef_maqsura", "to-yeh"): _map("alef_maqsura", [ALEF_MAQSURA], chr(YEH), "alef_maqsura.to_yeh"),
    ("taa_marbuta", "to-heh"): _map("taa_marbuta", [TAA_MARBUTA], chr(HEH), "taa_marbuta.to_heh"),
    ("persian_urdu_letters", "map"): _map("persian_urdu_letters", PERSIAN_URDU, lambda c: chr(PERSIAN_URDU[c]),
                                          "persian_urdu_letters.map"),
    ("digits", "ascii"): _map("digits", ARABIC_INDIC | EXT_ARABIC_INDIC, lambda c: chr(0x30 + (c & 0xF)),
                              "digits.to_ascii"),
    ("digits", "arabic-indic"): _map("digits", _cps((0x30, 0x39)) | EXT_ARABIC_INDIC,
                                     lambda c: chr(0x0660 + (c - 0x30 if c <= 0x39 else c - 0x06F0)),
                                     "digits.to_arabic_indic"),
    ("punctuation", "strip"): _map("punctuation", U.PUNCTUATION, " ", "punctuation.strip"),
    ("punctuation", "ascii"): _map("punctuation", PUNCT_ASCII, lambda c: PUNCT_ASCII[c], "punctuation.to_ascii"),
    ("latin_case", "lower"): _map("latin_case", U.LATIN_LOWER, lambda c: chr(U.LATIN_LOWER[c]), "latin_case.lower"),
}


class _Ctx(object):
    __slots__ = ("detailed", "strict", "policy", "spans", "changes", "flags", "rejected")

    def __init__(self, detailed, strict, policy, n):
        self.detailed = detailed
        self.strict = strict
        self.policy = policy
        self.spans = [(i, i + 1) for i in range(n)] if detailed else None
        self.changes = []
        self.flags = set()
        self.rejected = []

    def apply(self, s, edits, stage):
        """Apply sorted, non-overlapping edits (start, end, replacement, rule_id, sub_spans)."""
        if not edits:
            return s
        out = []
        pos = 0
        if not self.detailed:
            for e in edits:
                out.append(s[pos:e[0]])
                out.append(e[2])
                pos = e[1]
            out.append(s[pos:])
            return "".join(out)
        spans = self.spans
        new_spans = []
        changes = self.changes
        for i, j, rep, rule, sub in edits:
            out.append(s[pos:i])
            new_spans.extend(spans[pos:i])
            seg = spans[i:j]
            lo = min(x[0] for x in seg)
            hi = max(x[1] for x in seg)
            if sub is None:
                new_spans.extend([(lo, hi)] * len(rep))
            else:
                for a, b in sub:
                    ss = spans[a:b]
                    new_spans.append((min(x[0] for x in ss), max(x[1] for x in ss)))
            out.append(rep)
            changes.append(Change(stage, rule, lo, hi, s[i:j], rep, rule in LOSSY_RULES))
            pos = j
        out.append(s[pos:])
        new_spans.extend(spans[pos:])
        self.spans = new_spans
        return "".join(out)


# --- Context-sensitive stages ---------------------------------------------------------------------------
def _reject_reason(cp):
    if 0xD800 <= cp <= 0xDFFF:
        return "lone_surrogate"
    if cp in REJECT_CONTROLS:
        return "control"
    return "noncharacter"


def _stage_reject(ctx, s, mode):
    m = REJECT_RE.search(s)
    if m is None:
        return s
    if mode == "error" or ctx.strict:
        cp = ord(m.group())
        raise InputRejected(_reject_reason(cp), "U+%04X at index %d" % (cp, m.start()), span=(m.start(), m.end()))
    edits = []
    rejected = ctx.rejected
    for m in REJECT_RE.finditer(s):
        reason = _reject_reason(ord(m.group()))
        i = m.start()
        edits.append((i, i + 1, "", "reject_invalid." + reason, None))
        if rejected and rejected[-1]["reason"] == reason and rejected[-1]["end"] == i:
            rejected[-1]["end"] = i + 1
        else:
            rejected.append({"start": i, "end": i + 1, "reason": reason})
    return ctx.apply(s, edits, "reject_invalid")


# Code points skipped when looking for the letters around a ZWNJ: transparent (joining type T), the zero-width
# characters themselves, tatweel and Quranic marks (docs/SPEC.md 4.5). The set does not depend on the policy, so a
# ZWNJ gets the same decision under every policy and every policy stays idempotent.
_CTX_SKIP_BASE = frozenset(c for c, t in U.JOINING.items() if t == "T") | {ZWSP, ZWNJ, ZWJ, TATWEEL} | QURANIC
# A presentation form that maps only to skipped code points (for example U+FE7D, shadda medial form, maps to
# tatweel + shadda) is skipped too.
CTX_SKIP = _CTX_SKIP_BASE | frozenset(c for c, m in PF_MAP.items() if all(ord(x) in _CTX_SKIP_BASE for x in m))
# Presentation forms take the joining behaviour of the letters they map to (first letter on their right side,
# last letter on their left side), so mapping them first or keeping them gives the same ZWNJ decision.
_JT_PREV = {}
_JT_NEXT = {}
for _c, _m in PF_MAP.items():
    _letters = [x for x in _m if ord(x) not in CTX_SKIP]
    _JT_PREV[_c] = U.JOINING.get(ord(_letters[-1]), "U") if _letters else "U"
    _JT_NEXT[_c] = U.JOINING.get(ord(_letters[0]), "U") if _letters else "U"


def _jt_prev(cp):
    t = _JT_PREV.get(cp)
    return t if t is not None else U.JOINING.get(cp, "U")


def _jt_next(cp):
    t = _JT_NEXT.get(cp)
    return t if t is not None else U.JOINING.get(cp, "U")


def _virama_before(s, i):
    """True when the run of marks directly before position i contains a virama (combining class 9)."""
    k = i - 1
    while k >= 0 and ord(s[k]) in U.MARKS:
        if U.CCC.get(ord(s[k]), 0) == 9:
            return True
        k -= 1
    return False


def _context(s, positions):
    """For each position (sorted), the joining types of the nearest non-skipped code points before and after.

    Runs of skipped code points between consecutive positions are scanned once, so the cost is linear.
    """
    before = {}
    last, last_val = -1, None
    for i in positions:
        k = i - 1
        val = None
        while k > last:
            cp = ord(s[k])
            if cp not in CTX_SKIP:
                val = _jt_prev(cp)
                break
            k -= 1
        else:
            val = last_val if last >= 0 else None
        before[i] = val
        last, last_val = i, val
    after = {}
    n = len(s)
    last, last_val = n, None
    for i in reversed(positions):
        k = i + 1
        val = None
        while k < last:
            cp = ord(s[k])
            if cp not in CTX_SKIP:
                val = _jt_next(cp)
                break
            k += 1
        else:
            val = last_val if last < n else None
        after[i] = val
        last, last_val = i, val
    return before, after


def _zwj_meaningful(s, i):
    if _virama_before(s, i):
        return True
    k = i - 1
    while k >= 0 and ord(s[k]) in EMOJI_SKIP:
        k -= 1
    if k < 0 or ord(s[k]) not in U.EXT_PICT:
        return False
    return i + 1 < len(s) and ord(s[i + 1]) in U.EXT_PICT


def _stage_bidi_zw(ctx, s, mode):
    if mode == "keep" or BIDI_ZW_RE.search(s) is None:
        return s
    keep_zwnj = mode in ("strip-except-zwnj", "strip-except-meaningful")
    keep_zwj = mode in ("strip-except-emoji-zwj", "strip-except-meaningful")
    matches = [(m.start(), ord(m.group())) for m in BIDI_ZW_RE.finditer(s)]
    before = after = {}
    if keep_zwnj:
        zwnj = [i for i, c in matches if c == ZWNJ]
        if zwnj:
            before, after = _context(s, zwnj)
    edits = []
    for i, c in matches:
        if c == ZWNJ:
            if keep_zwnj and (_virama_before(s, i) or (before[i] in ("D", "L", "C") and after[i] in ("D", "R", "C"))):
                continue
            rule = "bidi_zw.zwnj"
        elif c == ZWJ:
            if keep_zwj and _zwj_meaningful(s, i):
                continue
            rule = "bidi_zw.zwj"
        elif c == ZWSP:
            rule = "bidi_zw.zwsp"
        else:
            rule = "bidi_zw.bidi_control"
        edits.append((i, i + 1, "", rule, None))
    return ctx.apply(s, edits, "bidi_zw")


def _stage_canonical(ctx, s, form, final):
    if form == "none":
        return s
    edits = []
    for a, b, rep, sub in U.normalization_edits(s, form):
        if final:
            rule = "canonical_order.final"
        elif form == "NFKC" and U.normalize_form(s[a:b], "NFC") != rep:
            rule = "canonical_order.nfkc"
        else:
            rule = "canonical_order.nfc"
        edits.append((a, b, rep, rule, sub))
    return ctx.apply(s, edits, "canonical_order")


_ALEF_RE = _re(ALEF_VARIANTS | HAMZA_MARKS)
_HAMZA_RE = _re(set(HAMZA_CARRIERS) | {HAMZA_ABOVE})


def _mark_bases(s, positions):
    """Base code point (nearest non-mark before) for each mark position; linear over runs of marks."""
    bases = {}
    prev, prev_base = -1, None
    for i in positions:
        k = i - 1
        while k > prev and ord(s[k]) in U.MARKS:
            k -= 1
        if k == prev and prev >= 0:
            base = prev_base
        else:
            base = ord(s[k]) if k >= 0 else None
        bases[i] = base
        prev, prev_base = i, base
    return bases


def _stage_alef(ctx, s):
    if _ALEF_RE.search(s) is None:
        return s
    matches = [(m.start(), ord(m.group())) for m in _ALEF_RE.finditer(s)]
    bases = _mark_bases(s, [i for i, c in matches if c in HAMZA_MARKS])
    edits = []
    for i, c in matches:
        if c in ALEF_VARIANTS:
            edits.append((i, i + 1, chr(ALEF), "alef_variants.map", None))
        else:
            base = bases[i]
            if base == ALEF or base in ALEF_VARIANTS:
                edits.append((i, i + 1, "", "alef_variants.map", None))
    return ctx.apply(s, edits, "alef_variants")


def _stage_hamza(ctx, s):
    if _HAMZA_RE.search(s) is None:
        return s
    matches = [(m.start(), ord(m.group())) for m in _HAMZA_RE.finditer(s)]
    bases = _mark_bases(s, [i for i, c in matches if c == HAMZA_ABOVE])
    edits = []
    for i, c in matches:
        if c in HAMZA_CARRIERS:
            edits.append((i, i + 1, chr(HAMZA_CARRIERS[c]), "hamza_carriers.fold", None))
        elif bases[i] in HAMZA_BASES:
            edits.append((i, i + 1, "", "hamza_carriers.fold", None))
    return ctx.apply(s, edits, "hamza_carriers")


def _stage_whitespace(ctx, s):
    edits = []
    n = len(s)
    for m in WS_RUN_RE.finditer(s):
        i, j = m.span()
        if i == 0 or j == n:
            rep = ""
        elif m.group() == " ":
            continue
        else:
            rep = " "
        edits.append((i, j, rep, "whitespace.collapse", None))
    return ctx.apply(s, edits, "whitespace")


def _flag_step(flag, test):
    def step(ctx, s):
        if ctx.detailed and test(s):
            ctx.flags.add(flag)
        return s
    return step


def _compose(a, b):
    """One _MapStage equal to applying ``a`` then ``b`` (both per-code-point maps)."""
    mapping = {}
    for c in set(a.reps) | set(b.reps):
        first = a.reps.get(c, chr(c))
        out = "".join(b.reps.get(ord(x), x) for x in first)
        if out != chr(c):
            mapping[c] = (out, "composed")
    return _MapStage("composed", mapping)


_PLANS = {}


def _plan(policy, detailed):
    """The ordered steps for a policy. In plain mode adjacent per-code-point maps are merged into one table;
    flags are not computed. Both plans give the same text (tested)."""
    key = (policy.policy_hash, detailed)
    plan = _PLANS.get(key)
    if plan is not None:
        return plan
    st = policy.stages
    steps = [lambda ctx, s: _stage_reject(ctx, s, st["reject_invalid"])]
    if st["strip_controls"] == "strip":
        steps.append(_STAGES[("strip_controls", "strip")])
    if st["presentation_forms"] == "map":
        steps.append(_STAGES[("presentation_forms", "map")])
    elif st["presentation_forms"] == "flag":
        steps.append(_flag_step("presentation_forms.flag", lambda x: PF_RE.search(x) is not None))
    if st["ligatures_honorific"] == "expand":
        steps.append(_STAGES[("ligatures_honorific", "expand")])
        steps.append(_flag_step("ligatures_honorific.flag", lambda x: H_REMAIN_RE.search(x) is not None))
    elif st["ligatures_honorific"] == "flag":
        steps.append(_flag_step("ligatures_honorific.flag", lambda x: HONORIFIC_RE.search(x) is not None))
    steps.append(lambda ctx, s: _stage_bidi_zw(ctx, s, st["bidi_zw"]))
    form = policy.unicode_form
    steps.append(lambda ctx, s: _stage_canonical(ctx, s, form, final=False))
    for stage in ("tatweel", "diacritics", "quranic_marks", "superscript_alef"):
        if (stage, st[stage]) in _STAGES:
            steps.append(_STAGES[(stage, st[stage])])
    if st["alef_variants"] == "map":
        steps.append(_stage_alef)
    if st["alef_maqsura"] == "to-yeh":
        steps.append(_STAGES[("alef_maqsura", "to-yeh")])
    elif st["alef_maqsura"] == "flag":
        steps.append(_flag_step("alef_maqsura.flag", lambda x: chr(ALEF_MAQSURA) in x))
    if st["taa_marbuta"] == "to-heh":
        steps.append(_STAGES[("taa_marbuta", "to-heh")])
    elif st["taa_marbuta"] == "flag":
        steps.append(_flag_step("taa_marbuta.flag", lambda x: chr(TAA_MARBUTA) in x))
    if st["hamza_carriers"] == "fold":
        steps.append(_stage_hamza)
    for stage in ("persian_urdu_letters", "digits", "punctuation"):
        if (stage, st[stage]) in _STAGES:
            steps.append(_STAGES[(stage, st[stage])])
    if st["whitespace"] == "collapse":
        steps.append(_stage_whitespace)
    if st["latin_case"] == "lower":
        steps.append(_STAGES[("latin_case", "lower")])
    if form != "none":
        steps.append(lambda ctx, s: _stage_canonical(ctx, s, "NFC", final=True))
    if not detailed:
        merged = []
        for step in steps:
            if getattr(step, "__name__", "") == "step":  # flag checks do nothing in plain mode
                continue
            if isinstance(step, _MapStage) and merged and isinstance(merged[-1], _MapStage):
                merged[-1] = _compose(merged[-1], step)
            else:
                merged.append(step)
        steps = merged
    plan = [step.run if isinstance(step, _MapStage) else step for step in steps]
    _PLANS[key] = plan
    return plan


def _run(text, policy, detailed, strict):
    ctx = _Ctx(detailed, strict, policy, len(text))
    s = text
    for step in _plan(policy, detailed):
        s = step(ctx, s)
    return s, ctx


# --- Public API ------------------------------------------------------------------------------------------
class Result(object):
    """Detailed result of one normalisation (docs/SPEC.md section 5). Immutable."""

    __slots__ = ("text_norm", "offset_map", "changes", "lossy_flags", "flags", "diacritization_ratio",
                 "rejected_spans", "stats", "policy_id", "policy_hash", "lib_version", "unicode_version",
                 "original_hash", "text_diac")

    def __init__(self, **kw):
        for k in self.__slots__:
            object.__setattr__(self, k, kw[k])

    def __setattr__(self, k, v):
        raise AttributeError("Result objects are immutable")

    def __repr__(self):
        return "Result(text_norm=%r, policy_id=%r, changes=%d, lossy_flags=%r)" % (
            self.text_norm, self.policy_id, len(self.changes), list(self.lossy_flags))

    @property
    def rules(self):
        """Sorted unique rule ids in the change log."""
        return tuple(sorted({c.rule_id for c in self.changes}))

    def to_dict(self, text_raw=None, record_id=None):
        """JSON-ready dict matching schemas/output.schema.json."""
        d = {}
        if record_id is not None:
            d["record_id"] = record_id
        d["original_hash"] = self.original_hash
        if text_raw is not None:
            d["text_raw"] = text_raw
        d.update({
            "text_norm": self.text_norm,
            "text_diac": self.text_diac,
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "lib_version": self.lib_version,
            "unicode_version": self.unicode_version,
            "changes": [c._asdict() for c in self.changes],
            "offset_map": [list(x) if x is not None else None for x in self.offset_map],
            "lossy_flags": list(self.lossy_flags),
            "flags": list(self.flags),
            "diacritization_ratio": self.diacritization_ratio,
            "stats": {"rules": dict(self.stats["rules"]), "classes": dict(self.stats["classes"])},
            "rejected_spans": [dict(x) for x in self.rejected_spans],
        })
        return d


def _check_text(text):
    if not isinstance(text, str):
        raise InputRejected("text_not_string", "expected str, got %s" % type(text).__name__)
    if len(text) * 4 > MAX_TEXT_BYTES:
        nbytes = len(text.encode("utf-8", "surrogatepass"))
        if nbytes > MAX_TEXT_BYTES:
            raise InputRejected("over_cap_bytes", "%d UTF-8 bytes; the cap is %d" % (nbytes, MAX_TEXT_BYTES))


def normalize(text: str, policy=DEFAULT_POLICY, *, strict: bool = False) -> str:
    """Normalise ``text`` with ``policy`` (built-in id, path, dict or Policy) and return the string."""
    _check_text(text)
    p = load_policy(policy)
    return _run(text, p, False, strict)[0]


def input_stats(text: str):
    """Policy-independent input counts and the diacritization ratio (docs/SPEC.md section 5)."""
    expanded = text.translate(PF_TRANS)
    letters = sum(1 for _ in ARABIC_LETTER_RE.finditer(expanded))
    harakat = sum(expanded.count(chr(c)) for c in HARAKAT)
    sup = expanded.count(chr(SUPERSCRIPT_ALEF))
    classes = {
        "arabic_letters": letters,
        "harakat": harakat,
        "superscript_alef": sup,
        "taa_marbuta": expanded.count(chr(TAA_MARBUTA)),
        "alef_maqsura": expanded.count(chr(ALEF_MAQSURA)),
        "presentation_forms": sum(1 for _ in PF_RE.finditer(text)),
        "honorific_ligatures": sum(1 for _ in HONORIFIC_RE.finditer(text)),
        "rejected": sum(1 for _ in REJECT_RE.finditer(text)),
    }
    ratio = (harakat + sup) / letters if letters else 0.0
    return classes, ratio


def normalize_detailed(text: str, policy=DEFAULT_POLICY, *, strict: bool = False) -> Result:
    """Normalise ``text`` and return a Result with offset map, change log, flags and statistics."""
    _check_text(text)
    p = load_policy(policy)
    out, ctx = _run(text, p, True, strict)
    classes, ratio = input_stats(text)
    rule_counts = {}
    for c in ctx.changes:
        rule_counts[c.rule_id] = rule_counts.get(c.rule_id, 0) + 1
    text_diac = None
    if classes["harakat"] or classes["superscript_alef"]:
        text_diac = _run(text, load_policy("raw-safe-v1"), False, False)[0]
    return Result(
        text_norm=out,
        offset_map=tuple(ctx.spans),
        changes=tuple(ctx.changes),
        lossy_flags=tuple(sorted({c.rule_id for c in ctx.changes if c.lossy})),
        flags=tuple(sorted(ctx.flags)),
        diacritization_ratio=ratio,
        rejected_spans=tuple(ctx.rejected),
        stats={"rules": dict(sorted(rule_counts.items())), "classes": classes},
        policy_id=p.policy_id,
        policy_hash=p.policy_hash,
        lib_version=__version__,
        unicode_version=U.UNICODE_VERSION,
        original_hash=hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest(),
        text_diac=text_diac,
    )


def decode_utf8(data: bytes) -> str:
    """Strict UTF-8 decoding; raises InputRejected('invalid_utf8') with the byte offset."""
    if len(data) > MAX_TEXT_BYTES:
        raise InputRejected("over_cap_bytes", "%d bytes; the cap is %d" % (len(data), MAX_TEXT_BYTES))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise InputRejected("invalid_utf8", "byte offset %d: %s" % (e.start, e.reason), span=(e.start, e.end))


def normalize_bytes(data: bytes, policy=DEFAULT_POLICY, *, strict: bool = False, detailed: bool = False):
    """Decode strict UTF-8 (BOM handled by strip_controls), then normalise."""
    text = decode_utf8(data)
    return normalize_detailed(text, policy, strict=strict) if detailed else normalize(text, policy, strict=strict)


def parse_record(line, field="text"):
    """Parse one JSONL line and return (record_dict, text). Raises InputRejected with a contract reason."""
    try:
        rec = json.loads(line)
    except ValueError as e:
        raise InputRejected("invalid_json", str(e))
    if not isinstance(rec, dict):
        raise InputRejected("invalid_json", "a JSONL record must be a JSON object")
    if field not in rec:
        raise InputRejected("missing_text_field", "record has no %r field" % field)
    text = rec[field]
    if not isinstance(text, str):
        raise InputRejected("text_not_string", "field %r is %s, not a string" % (field, type(text).__name__))
    return rec, text


def normalize_request(request: dict):
    """Apply the input contract (schemas/input.schema.json) to one request and return a list of results.

    request: {"text": str} or {"texts": [str, ...]}, optional "policy" (id or inline object),
    "detailed" (bool) and "strict" (bool). Returns strings, or dicts (to_dict) when detailed.
    """
    if not isinstance(request, dict):
        raise InputRejected("invalid_request", "a request must be a JSON object")
    unknown = set(request) - {"text", "texts", "policy", "detailed", "strict"}
    if unknown:
        raise InputRejected("unknown_member", "unknown request member(s): %s" % ", ".join(sorted(unknown)))
    if ("text" in request) == ("texts" in request):
        raise InputRejected("invalid_request", "give exactly one of 'text' or 'texts'")
    texts = [request["text"]] if "text" in request else request["texts"]
    if not isinstance(texts, list):
        raise InputRejected("invalid_request", "'texts' must be a list")
    if len(texts) > MAX_RECORDS:
        raise InputRejected("over_cap_records", "%d records; the cap is %d" % (len(texts), MAX_RECORDS))
    p = load_policy(request.get("policy", DEFAULT_POLICY))
    strict = bool(request.get("strict", False))
    for t in texts:
        _check_text(t)
    if request.get("detailed"):
        return [normalize_detailed(t, p, strict=strict).to_dict() for t in texts]
    return [normalize(t, p, strict=strict) for t in texts]


def diff_policies(text: str, policy_a, policy_b):
    """Compare two policies on one text: outputs, rules only one of them applies, and differing source regions."""
    ra = normalize_detailed(text, policy_a)
    rb = normalize_detailed(text, policy_b)
    regions = []
    for c in list(ra.changes) + list(rb.changes):
        regions.append([c.src_start, c.src_end])
    regions.sort()
    merged = []
    for lo, hi in regions:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])

    def piece(res, lo, hi):
        return "".join(ch for ch, sp in zip(res.text_norm, res.offset_map)
                       if sp is not None and sp[0] < hi and sp[1] > lo)

    diffs = []
    for lo, hi in merged:
        a, b = piece(ra, lo, hi), piece(rb, lo, hi)
        if a != b:
            diffs.append({"src_start": lo, "src_end": hi, "source": text[lo:hi], "a": a, "b": b})
    rules_a, rules_b = set(ra.rules), set(rb.rules)
    return {
        "policy_a": ra.policy_id, "policy_hash_a": ra.policy_hash, "text_a": ra.text_norm,
        "policy_b": rb.policy_id, "policy_hash_b": rb.policy_hash, "text_b": rb.text_norm,
        "identical": ra.text_norm == rb.text_norm,
        "rules_only_a": sorted(rules_a - rules_b), "rules_only_b": sorted(rules_b - rules_a),
        "lossy_flags_a": list(ra.lossy_flags), "lossy_flags_b": list(rb.lossy_flags),
        "regions": diffs,
    }


def explain(text: str, policy=DEFAULT_POLICY):
    """One row per input code point: code point, name, class data, the rules that touched it and its output."""
    res = normalize_detailed(text, policy)
    rows = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        rules = sorted({c.rule_id for c in res.changes if c.src_start <= i < c.src_end})
        out = "".join(o for o, sp in zip(res.text_norm, res.offset_map) if sp is not None and sp[0] <= i < sp[1])
        rows.append({
            "index": i, "char": ch, "codepoint": "U+%04X" % cp, "name": U.name(cp),
            "general_category": U.general_category(cp), "ccc": U.CCC.get(cp, 0),
            "joining_type": U.joining_type(cp), "rules": rules, "output": out,
        })
    return {"policy_id": res.policy_id, "policy_hash": res.policy_hash, "text_norm": res.text_norm, "rows": rows,
            "lossy_flags": list(res.lossy_flags), "flags": list(res.flags)}


def text_diac(text: str):
    """The text_diac field: raw-safe-v1 output when the input carries harakat or superscript alef, else None."""
    classes, _ = input_stats(text)
    if classes["harakat"] or classes["superscript_alef"]:
        return normalize(text, "raw-safe-v1")
    return None
