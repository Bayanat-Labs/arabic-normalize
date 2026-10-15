# arabic-normalize specification: arabic-normalize-spec-1

Status: pilot (library v0.1.0). Unicode data: UCD 18.0.0, pinned. Every policy names this spec in its `spec` member.

This file defines what each stage and mode does, so that any implementation (Python today, TypeScript later) gives the same output, offset map and change log. Decisions behind the choices are in [DECISIONS.md](DECISIONS.md).

## 1. Units and terms

- **Text** is a sequence of Unicode code points. All offsets are code-point indices into the caller's input string (`text_raw`), zero-based, end-exclusive. They are not UTF-8 byte offsets and not UTF-16 code units.
- **Mark**: a code point whose General_Category is Mn, Mc or Me (UCD 18.0.0).
- **Mark sequence after X**: the maximal run of marks that directly follows code point X.
- **Arabic letter**: General_Category Lo and Script=Arabic (Scripts.txt).
- **Joining type**: from ArabicShaping.txt; code points not listed have type T if their General_Category is Mn, Me or Cf, and type U otherwise.
- **Character classes** come only from the pinned UCD files, never from the interpreter's `unicodedata` module.

## 2. Policy object and hash

A policy has `policy_id`, `version`, `spec`, `unicode_version`, `unicode_form` (NFC, NFKC or none), `idempotent` and `stages` (one mode per stage, all 18 stages present), plus an optional `meta` object (titles, description, licence). The schema is `src/arabic_normalize/policies/schema.json`.

**Policy hash** = SHA-256 (lowercase hex) of the canonical JSON of the policy object with the top-level `meta` member removed. Canonical JSON: object keys sorted by code point at every level, UTF-8, separators `,` and `:` with no whitespace, no escaping of non-ASCII characters, integers without exponent. Released policies are immutable: any change in behaviour ships as a new `policy_id` (for example `bayanat-norm-v2`).

Policies are rejected when they contain unknown members, unknown stage names, invalid stage values, any member whose name starts with `$` (no `$ref`, `$id` or `$schema`; nothing is ever fetched), a `unicode_version` other than 18.0.0, or `unicode_form: NFKC` without `presentation_forms: map` and `ligatures_honorific: expand` (NFKC already performs both).

## 3. Pipeline order

Stages always run in this order. A stage whose mode is `keep` does nothing.

| # | Stage | Modes |
|---|---|---|
| 1 | reject_invalid | drop, error |
| 2 | strip_controls | strip, keep |
| 3 | presentation_forms | map, keep, flag |
| 4 | ligatures_honorific | keep, flag, expand |
| 5 | bidi_zw | keep, strip, strip-except-zwnj, strip-except-emoji-zwj, strip-except-meaningful |
| 6 | canonical_order | applies `unicode_form` (NFC, NFKC or none) |
| 7 | tatweel | strip, keep |
| 8 | diacritics | keep, strip, strip-except-shadda |
| 9 | quranic_marks | strip, keep |
| 10 | superscript_alef | keep, strip, to-alef |
| 11 | alef_variants | map, keep |
| 12 | alef_maqsura | to-yeh, keep, flag |
| 13 | taa_marbuta | keep, flag, to-heh |
| 14 | hamza_carriers | keep, fold |
| 15 | persian_urdu_letters | map, keep |
| 16 | digits | keep, ascii, arabic-indic |
| 17 | punctuation | keep, ascii, strip |
| 18 | whitespace | collapse, keep |
| 19 | latin_case | keep, lower |
| 20 | canonical_order (final pass) | NFC again when `unicode_form` is not none |

## 4. Stages

Each change is logged as `{stage, rule_id, src_start, src_end, before, after, lossy}`. `before` and `after` are the stage-local strings (what the stage saw and what it wrote); `text_raw[src_start:src_end]` is the original input that the changed code points came from. One log entry is written per changed code point, per changed normalisation chunk (stage 6 and 20) or per changed whitespace run (stage 18).

### 4.1 reject_invalid
Rejected code points: lone surrogates U+D800..U+DFFF (reason `lone_surrogate`); General_Category Cc except the Cc code points with White_Space=Yes, that is U+0009..U+000D and U+0085 (reason `control`); Noncharacter_Code_Point (reason `noncharacter`). Mode `drop` removes them, logs rule `reject_invalid.<reason>` and adds `{start, end, reason}` to `rejected_spans` (adjacent code points with the same reason are merged into one span). Mode `error` raises `InputRejected` naming the first span. Callers can force `error` behaviour with `strict=True` (CLI `--strict`); this is a call option, not part of the policy.

### 4.2 strip_controls
Removes invisible format characters that carry no text: U+00AD SOFT HYPHEN, U+2060 WORD JOINER, U+2061..U+2064 invisible operators, U+206A..U+206F deprecated format characters, U+FFF9..U+FFFB interlinear annotation characters (rule `strip_controls.format`) and U+FEFF ZERO WIDTH NO-BREAK SPACE / BOM at any position (rule `strip_controls.bom`). Variation selectors, tag characters and U+034F COMBINING GRAPHEME JOINER are kept.

### 4.3 presentation_forms
Set PF: code points in U+FB50..U+FDFF and U+FE70..U+FEFF that have a compatibility decomposition in UnicodeData.txt, minus the honorific set H (4.4). Mode `map` replaces each with its NFKC form (rule `presentation_forms.map`); for example U+FEFB ﻻ becomes U+0644 U+0627 and U+FE70 (fathatan isolated form) becomes U+0020 U+064B, exactly as NFKC does. Mode `flag` keeps them and sets flag `presentation_forms.flag`. Other compatibility characters (Latin ligatures, fullwidth forms, superscripts, Arabic letters such as U+0675, Arabic Mathematical Alphabetic Symbols) are not touched by this stage.

### 4.4 ligatures_honorific
Set H: U+0610..U+0614 (combining honorific signs), U+FD40..U+FD4F, U+FDCF, U+FDF0..U+FDFF, U+10ED1..U+10ED8. Mode `flag` keeps them and sets flag `ligatures_honorific.flag`. Mode `expand` replaces each member that has a compatibility decomposition (U+FDF0..U+FDFC) with its NFKC form (rule `ligatures_honorific.expand`) and flags the rest. The stage runs before the letter rules so that expanded text is normalised like any other text.

### 4.5 bidi_zw
BIDI = Bidi_Control code points (U+061C, U+200E, U+200F, U+202A..U+202E, U+2066..U+2069). ZW = U+200B ZWSP, U+200C ZWNJ, U+200D ZWJ.
- `keep`: nothing. `strip`: remove all BIDI and ZW.
- `strip-except-zwnj`: remove BIDI, ZWSP, ZWJ and every ZWNJ that is not meaningful.
- `strip-except-emoji-zwj`: remove BIDI, ZWSP, ZWNJ and every ZWJ that is not meaningful.
- `strip-except-meaningful`: remove BIDI, ZWSP and every ZWNJ or ZWJ that is not meaningful.

**Context.** For a ZWNJ at position i, *prev* is the nearest code point before i and *next* the nearest after i, skipping the context-skip set: code points of joining type T, U+200B, U+200C, U+200D, U+0640 tatweel and the Quranic set Q (4.9). The skip set is the same for every policy, so a ZWNJ gets the same decision whatever the policy deletes later, and every policy stays idempotent. A presentation form (4.3) takes the joining type of the letters it maps to: its first non-skipped code point when it is *next*, its last when it is *prev*; a presentation form that maps only to skipped code points (for example U+FE7D, which maps to tatweel + shadda) is itself skipped.
- A ZWNJ is **meaningful** when prev has joining type D, L or C and next has joining type D, R or C (the ZWNJ really prevents a cursive join), or when the run of marks directly before it contains a virama (canonical combining class 9).
- A ZWJ is **meaningful** when it is part of an emoji ZWJ sequence: the nearest code point before it, skipping U+FE0E, U+FE0F, Emoji_Modifier code points and tag characters U+E0020..U+E007F, is Extended_Pictographic, and the code point after it is Extended_Pictographic; or when the run of marks directly before it contains a virama.
- Known edge: a ZWNJ directly before a tatweel that is followed by a non-joining character is removed even by policies that keep tatweel.

Rules: `bidi_zw.bidi_control`, `bidi_zw.zwsp`, `bidi_zw.zwnj`, `bidi_zw.zwj`.

### 4.6 canonical_order
Applies `unicode_form` per UAX #15 with the pinned tables. The text is split into chunks that start at a code point with canonical combining class 0 and Quick_Check=Yes for the form; each chunk that changes is logged once with rule `canonical_order.nfc`, or `canonical_order.nfkc` (lossy) when the NFKC result differs from the NFC result. Offsets follow each code point through decomposition, reordering and composition: a composed code point maps to the union of the spans it was composed from.

### 4.7 tatweel
U+0640 removed (rule `tatweel.strip`).

### 4.8 diacritics
Harakat = U+064B..U+0652 (fathatan, dammatan, kasratan, fatha, damma, kasra, shadda, sukun). `strip` removes them; `strip-except-shadda` keeps U+0651. Rule `diacritics.strip`.

### 4.9 quranic_marks
Set Q: U+0615..U+061A, U+0653 (maddah above when not composed), U+0656..U+0658, U+06D6..U+06ED, U+0898..U+089F, U+08CA..U+08E2, U+08E3..U+08E9, U+08F0..U+08F3, U+08FF, U+10EFD..U+10EFF. `strip` removes them (rule `quranic_marks.strip`). Language-specific vowel signs and tone marks (U+0659..U+065F, U+0897, U+08EA..U+08EF, U+08F4..U+08FE) are not in Q and are kept.

### 4.10 superscript_alef
U+0670. `strip` removes it (rule `superscript_alef.strip`); `to-alef` replaces it with U+0627 (rule `superscript_alef.to_alef`).

### 4.11 alef_variants (lossy)
`map`: U+0622 آ, U+0623 أ, U+0625 إ, U+0671 ٱ become U+0627 ا, and any U+0653, U+0654 or U+0655 in the mark sequence after U+0627 is removed. Rule `alef_variants.map`. Other alef letters (U+0672, U+0673, U+0675, U+0773, U+0774) are kept.

### 4.12 alef_maqsura (lossy)
`to-yeh`: U+0649 ى becomes U+064A ي (rule `alef_maqsura.to_yeh`). `flag`: kept, flag `alef_maqsura.flag`. U+06CC (Farsi yeh) is handled only by stage 15.

### 4.13 taa_marbuta (lossy)
`to-heh`: U+0629 ة becomes U+0647 ه (rule `taa_marbuta.to_heh`). `flag`: kept, flag `taa_marbuta.flag`.

### 4.14 hamza_carriers (lossy)
`fold`: U+0624 ؤ becomes U+0648 و, U+0626 ئ becomes U+064A ي, and U+0654 in the mark sequence after U+0648, U+064A or U+0649 is removed. Rule `hamza_carriers.fold`. U+0621 ء is kept.

### 4.15 persian_urdu_letters (lossy)
`map`: U+06CC ی → U+064A ي; U+06A9 ک → U+0643 ك; U+06C1 ہ, U+06C2 ۂ, U+06BE ھ, U+06D5 ە, U+06C0 ۀ → U+0647 ه. Rule `persian_urdu_letters.map`.

### 4.16 digits
`ascii`: U+0660..U+0669 and U+06F0..U+06F9 become 0..9 (rule `digits.to_ascii`). `arabic-indic`: 0..9 and U+06F0..U+06F9 become U+0660..U+0669 (rule `digits.to_arabic_indic`). Separators U+066B and U+066C are punctuation (stage 17), not digits.

### 4.17 punctuation
Punctuation = General_Category Pc, Pd, Ps, Pe, Pi, Pf, Po. `strip` replaces each with U+0020 (rule `punctuation.strip`), so that words on both sides stay apart. `ascii` maps ، ؛ ؟ ٪ ٫ ٬ ۔ ٭ « » to , ; ? % . , . * " " (rule `punctuation.to_ascii`) and keeps other punctuation.

### 4.18 whitespace
Whitespace = White_Space=Yes. `collapse` replaces every maximal run of whitespace that is not exactly one U+0020 with one U+0020, and removes leading and trailing whitespace. Rule `whitespace.collapse`, one entry per changed run.

### 4.19 latin_case (lossy)
`lower`: Script=Latin code points with a simple lowercase mapping in UnicodeData.txt are lowercased (rule `latin_case.lower`).

### 4.20 final canonical_order pass
When `unicode_form` is NFC or NFKC, NFC is applied once more, because removing tatweel or mapping letters can leave a base letter next to a combining hamza or a mark run out of canonical order. Changes are logged as `canonical_order.final`.

## 5. Result

| Field | Meaning |
|---|---|
| text_norm | Output string |
| offset_map | For each output code point, `[src_start, src_end]` in `text_raw`. Several output code points can share one span (for example ﻻ → لا). Entries are non-decreasing except where canonical reordering moved a mark |
| changes | Change log, in pipeline order |
| lossy_flags | Sorted unique rule ids of lossy changes (alef_variants.map, alef_maqsura.to_yeh, taa_marbuta.to_heh, hamza_carriers.fold, persian_urdu_letters.map, latin_case.lower, canonical_order.nfkc) |
| flags | Sorted unique informational flags (`taa_marbuta.flag`, `alef_maqsura.flag`, `presentation_forms.flag`, `ligatures_honorific.flag`) |
| diacritization_ratio | count(U+064B..U+0652, U+0670) / count(Arabic letters), counted on the input after presentation-form mapping (independent of the policy); 0.0 when there is no Arabic letter |
| rejected_spans | `{start, end, reason}` for code points removed by stage 1 |
| stats | `rules`: number of change entries per rule id; `classes`: input counts of arabic_letters, harakat, superscript_alef, taa_marbuta, alef_maqsura, presentation_forms, honorific_ligatures, rejected |
| policy_id, policy_hash, lib_version, unicode_version | Identify exactly how the output was produced |

## 6. Input contract

Accepted input: UTF-8 text (invalid UTF-8 is rejected as `invalid_utf8`), or JSONL records with a string field (default `text`), and a policy id or an inline policy object. One request is capped at 10 MiB of UTF-8 per text (`over_cap_bytes`) and 10,000 records (`over_cap_records`); the CLI applies the 10 MiB cap per record and streams files of any length. Other rejection reasons: `unknown_policy`, `remote_ref_not_allowed`, `unknown_stage`, `invalid_stage_value`, `unknown_member`, `inconsistent_policy`, `unsupported_unicode_version`, `missing_text_field`, `text_not_string`, `invalid_json`, plus the span reasons of stage 1 under `strict=True`. The JSON Schema is `schemas/input.schema.json`.
