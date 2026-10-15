#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Write docs/LOSSY_REVIEW.md: the review of every lossy fixture and every lossy context class of the stress run.

The verdicts and notes below are the review (written out, not computed). Every count in the output is computed here from the
fixture files, the engine's change log and docs/stress/stats.json. The script refuses to run when a lossy
fixture or a stress class has no verdict, so new cases cannot slip through unreviewed.

Run: python scripts/make_lossy_review.py [--check]
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import arabic_normalize as an  # noqa: E402

REVIEW_DATE = "2026-10-15"
OK, CONS = "correct", "correct, flag conservative"

# --- Review of the lossy fixtures ------------------------------------------------------------------------------
FIXTURE_REVIEW = {
    "dev-010": (OK, "أمس، إلى، آخر become the bare forms the rules promise. Real merges: إلى and إليّ (to me) both "
                    "become الي; آخر (other) and أخّر (he delayed) both become اخر."),
    "dev-011": (CONS, "Standard unvocalised spelling writes alef wasla as plain ا, so ٱلكتاب → الكتاب restores the "
                      "standard form and merges nothing new. The flag comes from the shared rule id (finding L-4)."),
    "dev-012": (OK, "Alef + combining hamza is the decomposed form of أ. The hamza is lost: أمر and إمر (a grievous "
                    "thing) both become امر."),
    "dev-014": (OK, "إنّ → ان. Removing the shadda is a haraka change, measured by diacritization_ratio, not a lossy "
                    "change."),
    "dev-015": (OK, "The standard case: إنّ and أنّ become identical."),
    "dev-016": (OK, "In مآذن the madda carries a hamza (ma'ādhin); ماذن loses it. The hamza on the line in سماء is "
                    "kept, as specified."),
    "dev-017": (OK, "على (preposition) and علي (the name; also عليّ, high) both become علي."),
    "dev-018": (OK, "The spelling of the name changes in text_norm; text_raw keeps it. Names are where the ى/ي "
                    "distinction matters most: يحيى (the name) and يُحيي (he revives) both become يحيي."),
    "dev-020": (OK, "مبنى (building) and مبنيّ (built) both become مبني; معنى (meaning) and معنيّ (concerned) both "
                    "become معني."),
    "dev-022": (OK, "ة → ه in scoring only. جميلة (beautiful) and جميله (his favour) both become جميله."),
    "dev-035": (OK, "ﻷ is lam + أ. After mapping, لأنّ (because) becomes لان, the spelling of لانَ (it softened)."),
    "dev-038": (OK, "ﻣﺪﺭﺳﺔ is مدرسة in presentation forms; the letters are mapped (not lossy), then ة → ه (lossy) "
                    "under asr-eval-v1."),
    "dev-050": (OK, "الساعة → الساعه under asr-eval-v1 (scoring only)."),
    "dev-051": (OK, "أنت → انت. أنت (you) and أنّت (she groaned) both become انت."),
    "dev-052": (OK, "As dev-051, under asr-eval-v1."),
    "dev-054": (OK, "إلى → الي inside quotation marks, as in dev-010."),
    "dev-060": (CONS, "The only flagged change is ٱ → ا, conservative as in dev-011. The real merge in this fixture "
                      "comes from removing the superscript alef: Uthmani ٱلْكِتَٰبُ (al-kitāb, the book) becomes "
                      "الكتب, the spelling of al-kutub (the books). That change is not flagged, because the superscript "
                      "alef is counted as a vowel mark (docs/DECISIONS.md, section 4). Documented as a limitation (finding L-2)."),
    "dev-062": (OK, "كلمة → كلمه (ة → ه) and أخرى → اخري (أ → ا, ى → ي) under asr-eval-v1."),
    "acc-002": (OK, "مبرمجة → مبرمجه under asr-eval-v1."),
    "acc-006": (OK, "ى → ي applies whatever the neighbouring letters; the Arabic Supplement and Extended-A letters "
                    "are kept. The string is a code-point test, not a word. In some other languages written in Arabic "
                    "script (for example Uyghur) ى and ي are different letters, so the flag is justified (finding L-3)."),
    "acc-012": (OK, "آخر → اخر, the same merge as in dev-010."),
    "acc-013": (OK, "Once the tatweel is removed the hamza sits on the alef, the decomposed form of أ; reading it so "
                    "gives the word أمل (hope). The output امل is also the normalised form of آمل (I hope)."),
    "acc-014": (CONS, "ى followed by a combining hamza above is how ئ is drawn (the seat of ئ has no dots); after "
                      "ى → ي the final NFC pass composes ئ. The output letter is the one the writer meant, so the flag "
                      "is conservative."),
    "acc-016": (OK, "ليرة → ليره under asr-eval-v1."),
}

# --- Review of the stress-run context classes (keys as in docs/stress/stats.json) --------------------------------
ODD = ("Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by "
       "markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and "
       "gives the output it promises.")
CLASS_REVIEW = {
    "taa_marbuta.to_heh|U+0629|final": (OK, "The normal place of ة. Merges كرة (ball) / كره (hatred) and حياة (life) "
                                            "/ حيّاه (he greeted him)."),
    "taa_marbuta.to_heh|U+0629|alone": (OK, ODD),
    "taa_marbuta.to_heh|U+0629|medial": (OK, "ة is written only at the end of a word. " + ODD),
    "taa_marbuta.to_heh|U+0629|initial": (OK, "ة is written only at the end of a word. " + ODD),
    "taa_marbuta.to_heh|U+0629|after_prefix_word_final": (OK, "A proclitic followed only by ة. " + ODD),
    "alef_variants.map|U+0623|initial": (OK, "Word-initial hamza on alef, the largest class. Merges such as أنت / "
                                             "أنّت and أمر / إمر."),
    "alef_variants.map|U+0623|stem_initial_after_prefix": (OK, "As word-initial, after ال، و، ف، ب، ك، ل or لل "
                                                               "(for example الأول, وأن)."),
    "alef_variants.map|U+0623|medial": (OK, "Stem-medial hamza on alef (سأل، رأس، مسألة) and stem-initial أ after a "
                                            "longer prefix chain. The clearest merges: سأل (he asked) / سال (it "
                                            "flowed)."),
    "alef_variants.map|U+0623|final": (OK, "Final hamza on alef (بدأ، مبدأ، ملجأ): بدأ (he began) / بدا (it "
                                           "appeared)."),
    "alef_variants.map|U+0623|alone": (OK, ODD),
    "alef_variants.map|U+0623|after_prefix_word_final": (OK, "A proclitic followed only by أ. " + ODD),
    "alef_variants.map|U+0625|initial": (OK, "Word-initial hamza under alef: إنّ / أنّ, إلى / إليّ."),
    "alef_variants.map|U+0625|stem_initial_after_prefix": (OK, "As word-initial, after a proclitic (بإمكان، والإسلام)."),
    "alef_variants.map|U+0625|medial": (OK, "Stem-initial إ after a prefix chain the classifier does not list (such "
                                            "as وبال), and misspellings. إ belongs at the start of a stem."),
    "alef_variants.map|U+0625|final": (OK, ODD),
    "alef_variants.map|U+0625|alone": (OK, ODD),
    "alef_variants.map|U+0625|after_prefix_word_final": (OK, "A proclitic followed only by إ. " + ODD),
    "alef_variants.map|U+0622|initial": (OK, "آ = hamza + long a: آمن (he believed), أمن (security) and امن all become "
                                             "امن."),
    "alef_variants.map|U+0622|stem_initial_after_prefix": (OK, "As word-initial, after a proclitic (الآن، والآخر)."),
    "alef_variants.map|U+0622|medial": (OK, "Medial آ (مآذن، القرآن): the hamza is lost, as in dev-016."),
    "alef_variants.map|U+0622|final": (OK, ODD),
    "alef_variants.map|U+0622|alone": (OK, ODD),
    "alef_variants.map|U+0671|initial": (CONS, "Alef wasla appears in vocalised Quranic or classical quotations; "
                                               "standard spelling writes ا, so the output is the standard form "
                                               "(finding L-4)."),
    "alef_variants.map|U+0671|medial": (CONS, "As above (finding L-4)."),
    "alef_variants.map|U+0671|stem_initial_after_prefix": (CONS, "As above (finding L-4)."),
    "alef_maqsura.to_yeh|U+0649|final": (OK, "The normal place of ى. على / علي, يحيى / يُحيي."),
    "alef_maqsura.to_yeh|U+0649|after_prefix_word_final": (
        OK, "A proclitic plus final ى: short words such as الى (إلى written without hamza), فى and لى (spellings of "
            "في and لي) or ولّى (he turned away). For الى، فى، لى the output equals the normalised standard "
            "spelling (conservative); for ولّى / وليّ (guardian) the merge is real."),
    "alef_maqsura.to_yeh|U+0649|medial": (OK, "ى is written only at the end of an Arabic word; inside a word it is a "
                                              "misspelling or a letter of another language (finding L-3)."),
    "alef_maqsura.to_yeh|U+0649|alone": (OK, ODD),
    "alef_maqsura.to_yeh|U+0649|final|followed_by_superscript_alef": (
        OK, "Quranic spelling such as عَلَىٰ: the superscript alef (a vowel mark) is removed and ى → ي, giving علي "
            "like the unvocalised على."),
    "alef_maqsura.to_yeh|U+0649|final|followed_by_hamza_or_madda_mark_U+0654": (
        CONS, "ى + combining hamza is how ئ is drawn; the final NFC pass composes ئ (as acc-014)."),
}

FINDINGS = [
    ("L-1", "No substitution error. All lossy fixtures and all stress classes give the output their rule specifies, "
            "and every lossy flag marks a change that can merge two different words. Some flags are conservative "
            "(the change restores the standard spelling in that instance); over-flagging is the safe direction.",
     "None."),
    ("L-2", "Uthmani (Quranic) spelling. Removing the superscript alef leaves the consonantal skeleton (ٱلْكِتَٰبُ → "
            "الكتب), which can coincide with another word (الكتب, the books). It is not flagged, because the "
            "superscript alef is classed with the vowel marks (docs/DECISIONS.md, section 4) and counted in diacritization_ratio. "
            "The classification is consistent for modern text, where the superscript alef appears in words such as "
            "هٰذا and لٰكن and its removal gives the standard spelling. In Uthmani text a hamza written on a tatweel "
            "(يَسْـَٔلُونَ) also stays as a combining hamza on the preceding letter (يسٔلون).",
     "Limitation added to the bayanat-norm-v1 and asr-eval-v1 cards (English and Arabic). No engine change: the "
     "policies are frozen, and a Quranic-text policy is the right place for a fix (recommendation R-2)."),
    ("L-3", "ى → ي assumes Arabic-language text. In some other languages written in Arabic script (for example "
            "Uyghur) ى and ي are different letters. The change is already flagged as lossy.",
     "Limitation added to the bayanat-norm-v1 and asr-eval-v1 cards (English and Arabic)."),
    ("L-4", "One rule id, alef_variants.map, covers four letters with different effects: ٱ → ا restores standard "
            "spelling, while أ، إ، آ → ا delete a hamza that distinguishes words.",
     "No change in v1 (frozen policies). Recommendation R-1."),
    ("L-5", "Outside the lossy rules: U+FDFC (rial sign) is in the honorific set of SPEC 4.4, so a price written "
            "with ﷼ raises ligatures_honorific.flag. The text is unchanged; only the flag name is inaccurate.",
     "No change in v1. Recommendation R-3."),
]
RECOMMENDATIONS = [
    ("R-1", "In the next policy versions, split alef_variants.map into separate rule ids for ٱ (not lossy or "
            "separately flagged) and for أ، إ، آ, so lossy counts in dataset cards count only hamza deletions."),
    ("R-2", "Add a Quranic-text policy (for example quran-skeleton-v1 or quran-modern-v1) that states how it treats "
            "the superscript alef, hamza on tatweel and alef wasla, with fixtures taken from a licensed Uthmani text."),
    ("R-3", "Take U+FDFC out of the honorific set, or rename the flag to arabic_word_ligature, in the next spec "
            "version."),
    ("R-4", "Report non-final ة and ى as an anomaly flag in a later version; the stress classes show they are rare "
            "but real."),
]


def lossy_fixture_rows():
    rows = []
    for split, rel in (("dev", "tests/fixtures/dev/dev.jsonl"), ("acceptance", "tests/fixtures/acceptance/acceptance.jsonl")):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            for line in f:
                fx = json.loads(line)
                if not fx["expected_lossy_flags"]:
                    continue
                r = an.normalize_detailed(fx["input"], fx["policy_id"])
                assert r.text_norm == fx["expected_output"], fx["fixture_id"]
                subs = collections.Counter("%s → %s" % (c.before, c.after) for c in r.changes if c.lossy)
                rows.append((fx, subs))
    return rows


def md(s):
    return s.replace("|", "\\|")


def build():
    rows = lossy_fixture_rows()
    missing = [fx["fixture_id"] for fx, _ in rows if fx["fixture_id"] not in FIXTURE_REVIEW]
    extra = sorted(set(FIXTURE_REVIEW) - {fx["fixture_id"] for fx, _ in rows})
    if missing or extra:
        raise SystemExit("fixture review out of date: missing %s, no longer lossy %s" % (missing, extra))
    with open(os.path.join(ROOT, "docs", "stress", "stats.json"), encoding="utf-8") as f:
        stats = json.load(f)
    classes = stats["lossy_classes"]
    missing = [k for k in classes if k not in CLASS_REVIEW]
    if missing:
        raise SystemExit("stress classes without a verdict: %s" % missing)
    by_rule = collections.Counter()
    for k, c in classes.items():
        by_rule[k.split("|")[0]] += c
    verdicts = collections.Counter(FIXTURE_REVIEW[fx["fixture_id"]][0] for fx, _ in rows)
    cverdicts = collections.Counter(CLASS_REVIEW[k][0] for k in classes)
    errors = sum(1 for v in list(FIXTURE_REVIEW.values()) + list(CLASS_REVIEW.values()) if v[0] not in (OK, CONS))

    L = []
    w = L.append
    w("---")
    w("native_review: pending")
    w("human_linguist_signoff: recommended, not yet done (sign below and in tests/fixtures/REVIEW.md)")
    w("reviewed: %s" % REVIEW_DATE)
    w("---")
    w("")
    w("# Review of the lossy substitutions (pilot policies)")
    w("")
    w("This is a review of every change that the pilot policies flag as lossy: the "
      "%d conformance fixtures with a lossy flag and the %d context classes in which lossy changes occurred in the "
      "Arabic Wikipedia stress run ([stress/report.md](stress/report.md)). For each case it asks two questions:"
      % (len(rows), len(classes)))
    w("")
    w("1. Is the substitution correct, that is, is the output the form the rule promises (bare alef, yeh, heh)?")
    w("2. Is the lossy flag justified, that is, can the change make two different words identical?")
    w("")
    w("The review was made by Bayanat Labs separately from the writing of the engine and the fixtures. Arabic is "
      "Modern Standard Arabic. It is not a native-speaker review and does not replace the human native linguist "
      "sign-off at the end of this page, which is still recommended. The Arabic text has not yet been reviewed by "
      "a native Arabic writer; the English governs.")
    w("")
    w("Verdicts: **%s**: the substitution is right and the flag marks a possible merge. **%s**: the substitution "
      "is right, but in this instance it restores the standard spelling, so the flag over-reports (the safe "
      "direction). **error**: wrong output or wrong flag." % (OK, CONS))
    w("")
    w("## Result")
    w("")
    w("| Set | Cases | %s | %s | error |" % (OK, CONS))
    w("|---|---|---|---|---|")
    w("| Lossy fixtures | %d | %d | %d | %d |" % (len(rows), verdicts[OK], verdicts[CONS],
                                               len(rows) - verdicts[OK] - verdicts[CONS]))
    w("| Stress context classes | %d | %d | %d | %d |" % (len(classes), cverdicts[OK], cverdicts[CONS],
                                                       len(classes) - cverdicts[OK] - cverdicts[CONS]))
    w("")
    w("Errors found: %d. No engine or fixture change was needed. Two documentation gaps were closed (findings L-2 "
      "and L-3) and four recommendations are recorded for later policy versions." % errors)
    w("")
    w("## Findings")
    w("")
    w("| Id | Finding | Action |")
    w("|---|---|---|")
    for fid, text, action in FINDINGS:
        w("| %s | %s | %s |" % (fid, md(text), md(action)))
    w("")
    w("## Recommendations for later policy versions")
    w("")
    for rid, text in RECOMMENDATIONS:
        w("- **%s.** %s" % (rid, text))
    w("")
    w("## Lossy fixtures")
    w("")
    w("Lossy substitutions are read from the engine's change log for each fixture (count in brackets when more "
      "than one). Runs of whitespace in the input column are shown as one space; the exact inputs are in "
      "`tests/fixtures/`.")
    w("")
    w("| Fixture | Policy | Input | Output | Lossy substitutions | Verdict | Note |")
    w("|---|---|---|---|---|---|---|")
    for fx, subs in rows:
        v, note = FIXTURE_REVIEW[fx["fixture_id"]]
        sub = "; ".join("%s (%d)" % (k, n) if n > 1 else k for k, n in sorted(subs.items()))
        inp = " ".join(fx["input"].split()) or fx["input_escaped"]
        w("| %s | `%s` | %s | %s | %s | %s | %s |" % (fx["fixture_id"], fx["policy_id"], md(inp),
                                                     md(fx["expected_output"]), md(sub), v, md(note)))
    w("")
    w("## Stress-run context classes")
    w("")
    w("Counts are lossy changes in %d Arabic Wikipedia articles (bayanat-norm-v1 for alef variants and alef "
      "maqsura; asr-eval-v1 for taa marbuta), from [stress/stats.json](stress/stats.json). No corpus text was kept; "
      "the examples in the notes are standard dictionary words chosen by the reviewer." % stats["articles"])
    w("")
    w("| Rule | Source | Position | Extra context | Changes | Share of rule | Verdict | Note |")
    w("|---|---|---|---|---|---|---|---|")
    for k, c in classes.items():
        parts = k.split("|")
        v, note = CLASS_REVIEW[k]
        w("| %s | %s | %s | %s | %d | %.2f%% | %s | %s |" % (parts[0], parts[1], parts[2], ", ".join(parts[3:]),
                                                            c, 100.0 * c / by_rule[parts[0]], v, md(note)))
    w("")
    w("## Lossy wording in the policy cards")
    w("")
    w("The lossy-rule lines and limitations of the six policy cards (`docs/policies/*.md`, English and Arabic) were "
      "read against the rules. The descriptions of alef_variants.map, alef_maqsura.to_yeh and taa_marbuta.to_heh "
      "are accurate in both languages. Two limitation lines were added to bayanat-norm-v1 and asr-eval-v1 (L-2, "
      "L-3) through `scripts/make_docs.py`. The Arabic of those new lines is covered by the cards' own pending "
      "native review.")
    w("")
    w("## Human linguist sign-off (recommended)")
    w("")
    w("Scope for the linguist: the %d lossy fixtures above, the %d stress classes, findings L-1 to L-5 and the "
      "lossy lines of the six policy cards." % (len(rows), len(classes)))
    w("")
    w("| Reviewer (name) | Date | Fixtures and classes reviewed | Verdict | Notes |")
    w("|---|---|---|---|---|")
    w("| | | | | |")
    w("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = build()
    path = os.path.join(ROOT, "docs", "LOSSY_REVIEW.md")
    cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    if a.check:
        if cur != text:
            raise SystemExit("docs/LOSSY_REVIEW.md is stale (run scripts/make_lossy_review.py)")
        print("LOSSY_REVIEW.md is up to date")
        return
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote docs/LOSSY_REVIEW.md")


if __name__ == "__main__":
    main()
