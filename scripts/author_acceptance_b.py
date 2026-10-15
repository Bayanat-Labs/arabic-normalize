#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Blind acceptance-b candidate set: 16 further acceptance cases written by a second agent session.

Why: the 16 pilot acceptance fixtures were written by the same session as the dev fixtures (DECISIONS
D-14). The brief asks for acceptance cases written by a second session or a human without seeing the
engine. These 16 cases were written on 15 Oct 2026 by a separate agent session (the TL-003 fixes
session). The author worked only from docs/SPEC.md, the three policy JSON files and the raw UCD 18.0.0
data files in ucd/18.0.0/. It did not read or run src/arabic_normalize/engine.py, policy.py or _ucd.py,
or the JavaScript port, before this file was committed. Every expected value below was worked out by
hand from the spec.

Each case uses a family (and, where possible, a policy and rule combination) that does not occur in the
dev split. The set is a candidate set: it is not part of the 80 pilot fixtures, the published counts or
the Hugging Face conformance dataset. The brief's pilot gate keeps the fixture count at 80 until a native
linguist has reviewed the lossy cases; the set is merged into the acceptance split after that review.
Results of the first run against the engine are in tests/fixtures/candidates/README.md.

Text is original synthetic text written for these cases: no corpus text and no personal data.
Fixture data (tests/fixtures/**) is licensed CC BY 4.0 (Bayanat Labs); this script is Apache-2.0.

Run: python scripts/author_acceptance_b.py   (writes tests/fixtures/candidates/acceptance-b.jsonl)
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tests", "fixtures", "candidates")
AUTHOR = "Bayanat Labs (second agent session, written from docs/SPEC.md without engine access)"
CREATED = "2026-10-15"
LABEL = "synthetic/illustrative, authored by Bayanat Labs"

B, A, R = "bayanat-norm-v1", "asr-eval-v1", "raw-safe-v1"
AV, DS, DIG = "alef_variants.map", "diacritics.strip", "digits.to_ascii"
QM, PFM, NFC = "quranic_marks.strip", "presentation_forms.map", "canonical_order.nfc"
PS, WC, TM = "punctuation.strip", "whitespace.collapse", "taa_marbuta.to_heh"
ZWNJ, CTRL, NONCH, LHF = "bidi_zw.zwnj", "reject_invalid.control", "reject_invalid.noncharacter", "ligatures_honorific.flag"


def fx(fid, family, policy, inp, out, rules=(), lossy=(), flags=(), offsets=None, rejected=None, ratio=None, en=""):
    return {
        "fixture_id": fid, "split": "acceptance-b", "family": family, "policy_id": policy,
        "input": inp, "expected_output": out,
        "expected_rules": sorted(set(rules)), "expected_lossy_flags": sorted(set(lossy)),
        "expected_flags": sorted(set(flags)), "expected_offset_map": offsets,
        "expected_rejected_spans": rejected if rejected is not None else [],
        "expected_diacritization_ratio": ratio,
        "rationale_en": en,
        "rationale_ar": None,  # written when the set is merged, with the linguist review
        "author": AUTHOR, "created": CREATED, "label": LABEL, "synthetic": True,
        "reviewed_by": None, "review_verdict": "pending",
    }


CASES = [
    fx("accb-001", "quranic_maddah_unbound", A, "سوٓء", "سوء", [QM],
       offsets=[[0, 1], [1, 2], [3, 4]], ratio=0.0,
       en="Maddah above on waw has no precomposed form, so NFC leaves it and the Quranic-mark stage removes it "
          "(spec 4.9: U+0653 when not composed). U+0653 is not a haraka, so the ratio is 0."),
    fx("accb-002", "quranic_symbols", B, "۞ قال ۝١٢", " قال 12",
       [QM, DIG], offsets=[[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [7, 8], [8, 9]], ratio=0.0,
       en="Set Q is a code-point range, so the rub el hizb sign (So) and the end-of-ayah sign (Cf) are removed by "
          "stage 9, not by strip_controls; the ayah number becomes ASCII. Whitespace is kept, so the leading "
          "space stays."),
    fx("accb-003", "uthmani_small_letters", A,
       "إِنَّهُۥ", "انه", [DS, QM, AV], lossy=[AV],
       offsets=[[0, 1], [2, 3], [5, 6]],
       en="Uthmani spelling: small waw U+06E5 (General_Category Lm, inside set Q) is removed with the harakat, and "
          "hamza-below alef folds to bare alef. The marks are already in canonical order, so NFC changes nothing."),
    fx("accb-004", "noncharacter_in_pf_block", B, "ل﷐ﺎ", "لا", [NONCH, PFM],
       offsets=[[0, 1], [2, 3]], rejected=[{"start": 1, "end": 2, "reason": "noncharacter"}], ratio=0.0,
       en="U+FDD0 lies inside the presentation-forms block but is a noncharacter: stage 1 drops it and records a "
          "rejected span; the alef final form is then mapped."),
    fx("accb-005", "virama_zero_width", B,
       "क्‌ष क्‍ष a‌b",
       "क्‌ष क्‍ष ab", [ZWNJ],
       offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [12, 13]],
       ratio=0.0,
       en="Code-switching with Devanagari: a ZWNJ or ZWJ after a virama (ccc 9) is meaningful and kept; a ZWNJ "
          "between two Latin letters prevents no join and is removed."),
    fx("accb-006", "zwnj_tatweel_edge", R, "ب‌ـ ن", "بـ ن", [ZWNJ],
       offsets=[[0, 1], [2, 3], [3, 4], [4, 5]], ratio=0.0,
       en="The known edge in spec 4.5: the ZWNJ context skips tatweel, the next code point is a space "
          "(non-joining), so the ZWNJ is removed even though raw-safe-v1 keeps the tatweel."),
    fx("accb-007", "emoji_keycap_digits", B, "١️⃣ ٢️⃣", "1️⃣ 2️⃣",
       [DIG], offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]], ratio=0.0,
       en="Keycap sequences built on Arabic-Indic digits: the digits become ASCII; the variation selector and the "
          "enclosing keycap mark are kept."),
    fx("accb-008", "unicode_whitespace", A, "نص نص　 نص\t",
       "نص نص نص", [WC],
       offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 7], [7, 8], [8, 9]], ratio=0.0,
       en="Line separator, ideographic space and Ogham space mark are White_Space: each run becomes one space and "
          "the trailing tab is removed. NFC does not apply the wide compatibility mapping of U+3000."),
    fx("accb-009", "arabic_punctuation_extended", A,
       "نهاية؝ ٭نص۔ ؎بيت",
       "نهايه نص ؎بيت", [PS, TM, WC], lossy=[TM],
       en="End of text mark, five pointed star and Arabic full stop are punctuation (Po): each becomes a space and "
          "the runs collapse. The poetic verse sign is a symbol (So) and is kept. Taa marbuta becomes heh."),
    fx("accb-010", "honorific_extended", B,
       "﷽ قال\U00010efd \U00010ed1 ﷼", "﷽ قال \U00010ed1 ﷼",
       [QM], flags=[LHF], ratio=0.0,
       en="Bismillah ligature, an Arabic Extended-C honorific ligature and the rial sign are in set H: kept and "
          "flagged (the rial sign is not mapped because H is excluded from the presentation-form set). The small "
          "low word sakta U+10EFD is in set Q and is removed."),
    fx("accb-011", "nfc_compose_across_mark", R, "إِ", "إِ", [NFC],
       offsets=[[0, 3], [1, 2]], ratio=1.0,
       en="Kasra (ccc 32) does not block hamza below (ccc 220), so NFC composes alef + hamza below into U+0625 "
          "across the kasra; the composed letter maps to the union of its source spans."),
    fx("accb-012", "latin_compat_nfc", B, "É ﬁ Ａ² عدد",
       "É ﬁ Ａ² عدد", [NFC],
       offsets=[[0, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11]], ratio=0.0,
       en="bayanat-norm-v1 applies NFC, not NFKC: E + acute composes, but the fi ligature, fullwidth A and "
          "superscript two are kept, and the superscript is not a digit for stage 16."),
    fx("accb-013", "alef_wavy_hamza", B, "ٱسم ٲ ٳ", "اسم ٲ ٳ",
       [AV], lossy=[AV], offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]], ratio=0.0,
       en="Alef wasla maps to bare alef; alef with wavy hamza above and below (U+0672, U+0673) are outside the "
          "alef_variants set and are kept."),
    fx("accb-014", "hamza_presentation_forms", A, "ﺷﻲﺀ ﺑﺌﺮ",
       "شيء بئر", [PFM],
       offsets=[[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]], ratio=0.0,
       en="Isolated hamza and yeh-with-hamza medial forms map to U+0621 and U+0626; asr-eval-v1 keeps hamza "
          "carriers, so no letter is folded."),
    fx("accb-015", "ansi_escape_controls", R, "\u001b[31mنص\u001b[0m\u007f", "[31mنص[0m",
       [CTRL], offsets=[[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [8, 9], [9, 10], [10, 11]],
       rejected=[{"start": 0, "end": 1, "reason": "control"}, {"start": 7, "end": 8, "reason": "control"},
                 {"start": 11, "end": 12, "reason": "control"}], ratio=0.0,
       en="Terminal colour codes: ESC and DEL are C0/C1-class controls without White_Space, so raw-safe-v1 drops "
          "them as three separate rejected spans; the printable rest of the escape sequence stays."),
    fx("accb-016", "marks_outside_harakat", B,
       "بٖ بٟ بيٕر", "ب بٟ بيٕر", [QM],
       offsets=[[0, 1], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10]], ratio=0.0,
       en="Subscript alef U+0656 is in set Q and is removed. Wavy hamza below U+065F (a language-specific mark) and "
          "hamza below after yeh (no precomposed form; only removed after alef) are kept."),
]


def escaped(s):
    return "".join(c if 0x20 <= ord(c) < 0x7F and c != "\\" else
                   ("\\u%04x" % ord(c) if ord(c) <= 0xFFFF else "\\U%08x" % ord(c)) for c in s)


def main():
    os.makedirs(OUT, exist_ok=True)
    ids = [c["fixture_id"] for c in CASES]
    assert len(ids) == len(set(ids)) == 16
    lines = []
    for c in CASES:
        c = dict(c)
        c["input_escaped"] = escaped(c["input"])
        lines.append(json.dumps(c, ensure_ascii=False, sort_keys=True))
    path = os.path.join(OUT, "acceptance-b.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(path, "rb") as f:
        print("wrote %s: %d cases, sha256 %s" % (os.path.relpath(path, ROOT), len(lines),
                                                 hashlib.sha256(f.read()).hexdigest()))


if __name__ == "__main__":
    main()
