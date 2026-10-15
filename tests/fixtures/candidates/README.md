# Acceptance-b candidates (blind, second session)

Licence: CC BY 4.0, Bayanat Labs. Every record is labelled `synthetic/illustrative, authored by Bayanat Labs`; no corpus text, no personal data.

| File | Records | Status |
|---|---|---|
| acceptance-b.jsonl | 16 | Candidates. Not part of the 80 pilot fixtures, the published counts or the Hugging Face dataset |

**Why.** The pilot acceptance fixtures were written by the same agent session as the dev fixtures (docs/DECISIONS.md D-14). The brief asks for acceptance cases written by a second session or a human without seeing the engine.

**How.** A separate agent session wrote these 16 cases on 15 Oct 2026, working only from docs/SPEC.md, the three policy files and the raw UCD 18.0.0 files in ucd/18.0.0/. It did not read or run the engine or the JavaScript port before the cases were committed (commit "Add a blind acceptance-b candidate set written from the spec without engine access"; the engine was first run on them afterwards). The source is `scripts/author_acceptance_b.py`. Every family is new: none occurs in the dev split (checked by `tests/test_acceptance_b.py`).

**First run against the engine (15 Oct 2026).** 16 of 16 pass in Python and 16 of 16 in JavaScript: output text, rule ids, lossy flags, flags, rejected spans, and the offset map and diacritization ratio where asserted. No spec ambiguity or engine change came out of the run. No expected value was edited after the engine was run.

| Family | Policy | What it checks |
|---|---|---|
| quranic_maddah_unbound | asr-eval-v1 | Maddah above on waw (no precomposed form) is removed as a Quranic mark |
| quranic_symbols | bayanat-norm-v1 | Rub el hizb (So) and end of ayah (Cf) are in set Q; ayah digits become ASCII |
| uthmani_small_letters | asr-eval-v1 | Small waw U+06E5 (Lm) removed with the harakat; hamza-below alef folded |
| noncharacter_in_pf_block | bayanat-norm-v1 | U+FDD0 dropped as a noncharacter before presentation-form mapping |
| virama_zero_width | bayanat-norm-v1 | ZWNJ and ZWJ after a Devanagari virama kept; ZWNJ between Latin letters removed |
| zwnj_tatweel_edge | raw-safe-v1 | The known ZWNJ-before-tatweel edge of spec 4.5 |
| emoji_keycap_digits | bayanat-norm-v1 | Keycap sequences on Arabic-Indic digits |
| unicode_whitespace | asr-eval-v1 | Line separator, ideographic and Ogham spaces collapsed; trailing tab removed |
| arabic_punctuation_extended | asr-eval-v1 | U+061D, U+066D, U+06D4 stripped; poetic verse sign (So) kept |
| honorific_extended | bayanat-norm-v1 | Bismillah, Extended-C honorific and rial sign flagged; U+10EFD removed |
| nfc_compose_across_mark | raw-safe-v1 | Alef + hamza below composed across a kasra; union offset span |
| latin_compat_nfc | bayanat-norm-v1 | NFC, not NFKC: fi ligature, fullwidth A and superscript two kept |
| alef_wavy_hamza | bayanat-norm-v1 | Alef wasla folded; U+0672 and U+0673 kept |
| hamza_presentation_forms | asr-eval-v1 | Isolated hamza and yeh-hamza medial forms mapped; carriers kept |
| ansi_escape_controls | raw-safe-v1 | ESC and DEL dropped as three rejected spans |
| marks_outside_harakat | bayanat-norm-v1 | U+0656 removed; U+065F and hamza below after yeh kept |

**Next step.** The brief's pilot gate keeps the fixture count at 80 until a native linguist has reviewed the lossy cases. After that review, these cases get an Arabic rationale and a review verdict and move into the acceptance split, and the dataset, the JavaScript reference and every published count are regenerated.
