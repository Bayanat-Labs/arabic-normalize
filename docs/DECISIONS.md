# Decisions for arabic-normalize v0.1 (pilot)

Date: 15 Oct 2026. Scope: the three pilot policies (`bayanat-norm-v1`, `asr-eval-v1`, `raw-safe-v1`), the engine and the fixtures. Each decision names the sources it reconciles. "RULES" means the Bayanat Labs open-data programme rules (RULES.md); "the brief" means the TL-003 brief; "the manual" means the BR-009 operating manual; "normref" means the reference implementation used in BR-009 calibration (`work/br009/scripts/calib/normref.py`).

A released policy never changes. If a decision below is reversed, the new behaviour ships as a new policy id (for example `bayanat-norm-v2`) and `bayanat-norm-v1` keeps its hash.

## D-01. Unicode form of bayanat-norm-v1: NFC plus Arabic presentation-form mapping (NFKC scoped to Arabic presentation forms)

**Sources.** RULES §5.1 (founder default) says "NFKC (this maps presentation forms U+FB50–FDFF and U+FE70–FEFF)". Claude-research P-TXT says NFC plus presentation-form mapping. Claude-max stage 3 says NFKC. RULES appendix A-10 picked NFKC with ة kept and flagged. The brief resolves to "NFC + explicit mapping of Arabic presentation forms only (equivalent to NFKC for Arabic letters, without folding non-Arabic compatibility characters or expanding ﷺ)". The manual (T3.recipe) keeps the RULES wording and records the difference as its conflict C-03; its stage-3 action text says "presentation forms mapped". normref implements the brief's version.

**Decision.** bayanat-norm-v1 uses `unicode_form: NFC` with `presentation_forms: map`, which applies the NFKC mapping to every Arabic presentation form (U+FB50–U+FDFF, U+FE70–U+FEFF) except the honorific word ligatures, and `ligatures_honorific: flag`.

**Why this is the stricter reading of the founder default.** For Arabic presentation forms the output is the NFKC output, which is the purpose RULES gives for NFKC. Full NFKC would in addition (a) expand U+FDFA ﷺ into an 18-code-point, four-word phrase and U+FDF2 ﷲ into a word, changing word counts and tokenisation, and (b) silently fold non-Arabic compatibility characters: ² to 2, ½ to 1⁄2, ﬁ to fi, fullwidth Ａ to A, … to ..., ① to 1, ㎏ to kg, NBSP to space, Arabic mathematical letters and the Kazakh high-hamza letters U+0675–U+0678. RULES §1 item 8 forbids destructive normalisation applied silently, and A-10 records astra's rule "do not erase task-relevant distinctions". Scoping the compatibility mapping to Arabic presentation forms is the more cautious choice, and the brief gives it as an explicit pitfall. The difference from full NFKC is limited to the cases above; acceptance fixture acc-007 and dev fixture dev-039 pin it.

**Consequence for the manual.** A dataset that records `normalisation_version: bayanat-norm-v1` follows the RULES §5.1 recipe with this scoping. The manual's T3.recipe line can cite `bayanat-norm-v1` and its hash (see CHANGELOG) as the implementation of RULES §5.1 (founder note filed with the TL-003 engine report). Full NFKC stays available as `unicode_form: NFKC` in a custom policy.

## D-02. Taa marbuta: kept and flagged in bayanat-norm-v1, folded only for scoring and search

**Sources.** RULES §5.1 and A-10: keep ة and flag it; fold ة→ه only in `text_search`. Claude-max stage 3 unifies it in text_norm. The brief, the manual and normref agree with RULES.

**Decision.** bayanat-norm-v1 has `taa_marbuta: flag`: ة is kept and the result carries the flag `taa_marbuta.flag` (and `stats.classes.taa_marbuta` counts it). asr-eval-v1 folds ة→ه (`taa_marbuta: to-heh`, lossy) because WER scoring needs it; the future `search-v1` policy will fold it for `text_search`. raw-safe-v1 keeps it with no flag.

## D-03. Alef maqsura and alef variants are folded in bayanat-norm-v1 and flagged as lossy

RULES §5.1 maps أ إ آ ٱ → ا and ى → ي in text_norm. Both can merge different words (إنّ/أنّ; على/علي; names such as مصطفى). They stay in bayanat-norm-v1 as RULES requires, but every such change is logged with `lossy: true`, and the rule ids appear in `lossy_flags`, so a dataset card can say how many records were affected. `text_raw` always keeps the original (RULES §1 item 8). Only the four alef letters named in RULES are mapped; U+0672, U+0673, U+0675, U+0773 and U+0774 are kept. A combining hamza or madda that ends up on a bare alef (for example after a tatweel between them is removed) is removed by the same rule, so the output is the same whether the input was precomposed or decomposed.

## D-04. What counts as a diacritic, a Quranic mark and a lossy change

- Harakat (`diacritics` stage) are exactly U+064B–U+0652. The superscript alef U+0670 has its own stage (strip in bayanat-norm-v1 and asr-eval-v1, giving the standard spelling هذا). Quranic marks are an explicit list (SPEC §4.9) that includes the small high signs, small vowels, the standalone maddah and the Unicode 14–16 Quranic additions. Vowel signs and tone marks used by other languages written in Arabic script (U+0659–U+065F, U+0897, U+08EA–U+08EF, U+08F4–U+08FE) are kept, because removing them would damage those languages.
- A change is **lossy** when it can make two words that are spelled differently in standard unvocalised writing identical: alef variants, alef maqsura, taa marbuta, hamza carriers, Persian/Urdu letter mapping, Latin lower-casing and NFKC compatibility folding. Removing harakat, Quranic marks, tatweel or invisible controls, mapping presentation forms and changing digits or punctuation are not lossy in this sense; harakat removal is measured separately by `diacritization_ratio`. This follows the brief's examples (ة→ه, ى→ي, أ→ا, ؤ→و).

## D-05. Zero-width joiners: keep them only where they change rendering

RULES and the brief say "strip zero-width and bidi controls except a meaningful ZWNJ" and warn that stripping ZWJ breaks emoji sequences. Mode `strip-except-meaningful` keeps a ZWNJ only when it really prevents a cursive join (the letter before can join forward and the letter after can join backward, by ArabicShaping.txt joining types, skipping marks, tatweel and Quranic marks), or when it follows a virama; it keeps a ZWJ only inside an emoji ZWJ sequence (Extended_Pictographic on both sides, skipping variation selectors and skin-tone modifiers) or after a virama. The skip set is the same for all policies, and presentation forms take the joining type of the letters they map to, so raw-safe-v1 and bayanat-norm-v1 make the same decision for every ZWNJ (normalising `text_diac` with bayanat-norm-v1 gives `text_norm`; tested on random strings). The property tests found three problems in earlier versions of this rule (a virama check made before canonical reordering, a policy-dependent skip set, and a presentation form that maps only to tatweel and shadda); all three were fixed before release and have regression tests. Every RGI emoji ZWJ sequence of Unicode 18.0 survives all three pilot policies unchanged (tested).

## D-06. Stage order differs from the brief's list in two places

The brief lists `bidi_zw` before `presentation_forms`, and `ligatures_honorific` after the letter rules. Here `presentation_forms` and `ligatures_honorific` run before `bidi_zw`: (1) the ZWNJ test must see real letters, not presentation forms, which ArabicShaping.txt does not list; (2) when a policy expands ﷺ, the expansion contains ى and must pass through the alef maqsura rule like any other text. A final NFC pass (`canonical_order.final`) runs after the letter rules, because mapping ى→ي next to a combining hamza, or removing a tatweel between a letter and a mark, can leave a sequence that NFC composes. With this order every pilot policy is idempotent (tested on all fixtures and on random strings).

## D-07. Policy hash covers behaviour, not prose

The brief binds a policy id to "the SHA-256 of its canonical JSON". The hash here covers the canonical JSON of the whole policy object except the top-level `meta` member (titles in English and Arabic, description, licence, status). Reason: the Arabic titles still need native review, and a wording fix must not change the identity of a policy whose behaviour is unchanged. Everything that affects output is inside the hash: `policy_id`, `version`, `spec`, `unicode_version`, `unicode_form`, `idempotent` and every stage mode. The canonical form is defined in SPEC §2 so the TypeScript port can compute the same hash.

## D-08. Unicode data is pinned and bound to the policy

Character classes, decompositions and combining classes come from UCD 18.0.0 (the newest final UCD on 15 Oct 2026; ReadMe archived), generated into `src/arabic_normalize/tables/ucd_tables.json` by `scripts/build_tables.py`. The engine never calls the interpreter's `unicodedata`, so Python 3.9 (Unicode 13) and Python 3.14 (Unicode 16) give identical output. Each policy records `unicode_version: 18.0.0`; a later library that moves to UCD 19 must keep the 18.0.0 tables for these policies or publish new policy ids. The implementation passes all of NormalizationTest.txt 18.0.0 for NFC, NFD, NFKC and NFKD.

## D-09. Offsets are code-point spans

Offsets are zero-based code-point indices into the input string, end-exclusive. Each output code point maps to a span `[start, end]`, because one input code point can produce several output code points (ﻻ → لا) and composition can merge several into one. Byte or UTF-16 offsets are left to the caller (the TypeScript port will convert).

## D-10. Invalid input: dropped and reported by default, rejected under strict mode

Lone surrogates, C0/C1 controls other than whitespace controls, and noncharacters are removed by every pilot policy (`reject_invalid: drop`) and reported in `rejected_spans`; `strict=True` (CLI `--strict`) rejects the input instead. Whole-input problems (invalid UTF-8, over-cap input, unknown or malformed policy) always raise. TAB, LF, VT, FF, CR and NEL are allowed (they are whitespace).

## D-11. asr-eval-v1 details and coordination with TL-001

asr-eval-v1 = bayanat-norm-v1 + ة→ه + punctuation replaced by a space + whitespace collapsed and trimmed, as the brief defines it. Punctuation becomes a space rather than being deleted so that "كتاب،قلم" stays two words. Latin case is kept because the brief does not list lower-casing; TL-001's draft rule R12 casefolds Latin tokens, so ArabicWER should either add lower-casing in its own policy or adopt asr-eval-v1 as is and say so. Known limitation: Arabic decimal and thousands separators are punctuation, so `١٬٢٥٠٫٥` scores as three tokens (acceptance fixture acc-016). TL-001 computes its `diacritization_ratio` as the share of letters that carry a haraka; this library uses the brief's definition, count(U+064B–U+0652, U+0670) / count(Arabic letters), which can exceed 1. The two must not be mixed in one table.

## D-12. Differences from the BR-009 calibration reference implementation (normref)

normref was written to time the text stage, not as the specification. The library differs from it as follows, each for the reason given:

| Topic | normref | arabic-normalize | Reason |
|---|---|---|---|
| Diacritic set | strips U+064B–U+065F and U+0670 | strips U+064B–U+0652 (harakat), U+0670 and the explicit Quranic list | U+0659–U+065F are vowel signs of other languages; U+0654/U+0655 are hamza, handled by the alef and hamza rules |
| Quranic marks | U+06D6–U+06ED | U+06D6–U+06ED plus small vowels, standalone maddah and the Unicode 14–16 Quranic additions | Same intent, complete list |
| C0/C1 controls | silently removed (TAB, LF, CR kept) | removed and reported in `rejected_spans`; VT, FF and NEL also kept as whitespace | No silent normalisation (RULES §1 item 8) |
| ZWNJ | kept only between two Arabic letters that are immediate neighbours | kept when it prevents a join (joining types), skipping marks | normref drops a ZWNJ that follows a haraka, and keeps one that prevents nothing |
| ZWJ | kept next to any code point ≥ U+2600 | kept only inside emoji ZWJ sequences (Extended_Pictographic) or after a virama | Exact emoji rule; tested on every RGI sequence |
| Unicode data | interpreter `unicodedata` | pinned UCD 18.0.0 tables | Reproducibility across Python versions |
| Ratio | raw input, letters U+0621–U+063A, U+0641–U+064A, U+0671–U+06D3 | input after presentation-form mapping, letters = Lo and Script=Arabic | Counts letters in ligatures and all Arabic-script letters |
| Final NFC | none | final NFC pass | Output is always NFC; idempotence |

On ordinary Arabic text (letters, harakat, tatweel, alef variants, ى, ة, Arabic-Indic digits, spaces, ، ؛ ؟) the two give the same `text_norm` and the same diacritization ratio: identical results on 20,000 random strings for each of bayanat-norm-v1 and asr-eval-v1 (check run on 15 Oct 2026 with normref as written by the BR-009 agent).

## D-13. Licences

Code is Apache-2.0 (brief; claude-research Bucket B rule). Policy JSON files and the conformance fixtures are CC BY 4.0 (Bayanat Labs), because they are data (RULES §1 item 10 forbids Apache or MIT for data). The generated tables are derived from the Unicode Character Database and keep the Unicode License V3 notice (NOTICE-unicode.txt). There are no runtime dependencies. GPL tools (PyArabic, Mishkal) are not imported, vendored or consulted for code.

## D-14. Fixture authorship (deviation from the brief)

The brief asks for acceptance fixtures "written by a second agent session or a human without seeing the engine". The 16 acceptance fixtures were written by the same agent session as the dev fixtures, but before any engine code existed (they are in an earlier commit than `engine.py`), using code-point families and rule combinations that do not occur in the dev split. Independence of authorship is therefore partial. A second reviewer, ideally the native linguist named in the brief's founder action, should review both splits and sign `tests/fixtures/REVIEW.md`. No acceptance fixture was edited after the engine was written without being listed in the QA notes.

## D-15. Counsel

The brief marks this item green and says counsel review is not needed (no Medium or High risk source). Per the 15 Oct 2026 amendment to RULES §0, no counsel document was prepared.
