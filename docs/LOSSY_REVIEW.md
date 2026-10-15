---
native_review: independent_ai_review
human_linguist_signoff: recommended, not yet done (founder action; sign below and in tests/fixtures/REVIEW.md)
reviewed: 2026-10-15
---

# Review of the lossy substitutions (pilot policies)

This is an independent Arabic linguistic review of every change that the pilot policies flag as lossy: the 24 conformance fixtures with a lossy flag and the 31 context classes in which lossy changes occurred in the Arabic Wikipedia stress run ([stress/report.md](stress/report.md)). For each case it asks two questions:

1. Is the substitution correct, that is, is the output the form the rule promises (bare alef, yeh, heh)?
2. Is the lossy flag justified, that is, can the change make two different words identical?

Reviewer: an AI reviewer in a separate agent session (TL-003, oracles and stress part) that did not write the engine or the fixtures. Arabic is Modern Standard Arabic. This review does not replace the human native linguist sign-off that the brief requires; that sign-off is recommended and listed for the founder.

Verdicts: **correct**: the substitution is right and the flag marks a possible merge. **correct, flag conservative**: the substitution is right, but in this instance it restores the standard spelling, so the flag over-reports (the safe direction). **error**: wrong output or wrong flag.

## Result

| Set | Cases | correct | correct, flag conservative | error |
|---|---|---|---|---|
| Lossy fixtures | 24 | 21 | 3 | 0 |
| Stress context classes | 31 | 27 | 4 | 0 |

Errors found: 0. No engine or fixture change was needed. Two documentation gaps were closed (findings L-2 and L-3) and four recommendations are recorded for later policy versions.

## Findings

| Id | Finding | Action |
|---|---|---|
| L-1 | No substitution error. All lossy fixtures and all stress classes give the output their rule specifies, and every lossy flag marks a change that can merge two different words. Some flags are conservative (the change restores the standard spelling in that instance); over-flagging is the safe direction. | None. |
| L-2 | Uthmani (Quranic) spelling. Removing the superscript alef leaves the consonantal skeleton (ٱلْكِتَٰبُ → الكتب), which can coincide with another word (الكتب, the books). It is not flagged, because the superscript alef is classed with the vowel marks (DECISIONS D-04) and counted in diacritization_ratio. The classification is consistent for modern text, where the superscript alef appears in words such as هٰذا and لٰكن and its removal gives the standard spelling. In Uthmani text a hamza written on a tatweel (يَسْـَٔلُونَ) also stays as a combining hamza on the preceding letter (يسٔلون). | Limitation added to the bayanat-norm-v1 and asr-eval-v1 cards (English and Arabic). No engine change: the policies are frozen, and a Quranic-text policy is the right place for a fix (recommendation R-2). |
| L-3 | ى → ي assumes Arabic-language text. In some other languages written in Arabic script (for example Uyghur) ى and ي are different letters. The change is already flagged as lossy. | Limitation added to the bayanat-norm-v1 and asr-eval-v1 cards (English and Arabic). |
| L-4 | One rule id, alef_variants.map, covers four letters with different effects: ٱ → ا restores standard spelling, while أ، إ، آ → ا delete a hamza that distinguishes words. | No change in v1 (frozen policies). Recommendation R-1. |
| L-5 | Outside the lossy rules: U+FDFC (rial sign) is in the honorific set of SPEC 4.4, so a price written with ﷼ raises ligatures_honorific.flag. The text is unchanged; only the flag name is inaccurate. | No change in v1. Recommendation R-3. |

## Recommendations for later policy versions

- **R-1.** In the next policy versions, split alef_variants.map into separate rule ids for ٱ (not lossy or separately flagged) and for أ، إ، آ, so lossy counts in dataset cards count only hamza deletions.
- **R-2.** Add a Quranic-text policy (for example quran-skeleton-v1 or quran-modern-v1) that states how it treats the superscript alef, hamza on tatweel and alef wasla, with fixtures taken from a licensed Uthmani text.
- **R-3.** Take U+FDFC out of the honorific set, or rename the flag to arabic_word_ligature, in the next spec version.
- **R-4.** Report non-final ة and ى as an anomaly flag in a later version; the stress classes show they are rare but real.

## Lossy fixtures

Lossy substitutions are read from the engine's change log for each fixture (count in brackets when more than one). Runs of whitespace in the input column are shown as one space; the exact inputs are in `tests/fixtures/`.

| Fixture | Policy | Input | Output | Lossy substitutions | Verdict | Note |
|---|---|---|---|---|---|---|
| dev-010 | `bayanat-norm-v1` | أمس إلى آخر | امس الي اخر | آ → ا; أ → ا; إ → ا; ى → ي | correct | أمس، إلى، آخر become the bare forms the rules promise. Real merges: إلى and إليّ (to me) both become الي; آخر (other) and أخّر (he delayed) both become اخر. |
| dev-011 | `bayanat-norm-v1` | ٱلكتاب | الكتاب | ٱ → ا | correct, flag conservative | Standard unvocalised spelling writes alef wasla as plain ا, so ٱلكتاب → الكتاب restores the standard form and merges nothing new. The flag comes from the shared rule id (finding L-4). |
| dev-012 | `bayanat-norm-v1` | أمر | امر | أ → ا | correct | Alef + combining hamza is the decomposed form of أ. The hamza is lost: أمر and إمر (a grievous thing) both become امر. |
| dev-014 | `asr-eval-v1` | إنّ | ان | إ → ا | correct | إنّ → ان. Removing the shadda is a haraka change, measured by diacritization_ratio, not a lossy change. |
| dev-015 | `bayanat-norm-v1` | إِنَّ أَنَّ | ان ان | أ → ا; إ → ا | correct | The standard case: إنّ and أنّ become identical. |
| dev-016 | `bayanat-norm-v1` | سماء مآذن | سماء ماذن | آ → ا | correct | In مآذن the madda carries a hamza (ma'ādhin); ماذن loses it. The hamza on the line in سماء is kept, as specified. |
| dev-017 | `bayanat-norm-v1` | على | علي | ى → ي | correct | على (preposition) and علي (the name; also عليّ, high) both become علي. |
| dev-018 | `bayanat-norm-v1` | مصطفى | مصطفي | ى → ي | correct | The spelling of the name changes in text_norm; text_raw keeps it. Names are where the ى/ي distinction matters most: يحيى (the name) and يُحيي (he revives) both become يحيي. |
| dev-020 | `asr-eval-v1` | مبنى ومعنى | مبني ومعني | ى → ي (2) | correct | مبنى (building) and مبنيّ (built) both become مبني; معنى (meaning) and معنيّ (concerned) both become معني. |
| dev-022 | `asr-eval-v1` | مدرسة جميلة | مدرسه جميله | ة → ه (2) | correct | ة → ه in scoring only. جميلة (beautiful) and جميله (his favour) both become جميله. |
| dev-035 | `bayanat-norm-v1` | ﻷ | لا | أ → ا | correct | ﻷ is lam + أ. After mapping, لأنّ (because) becomes لان, the spelling of لانَ (it softened). |
| dev-038 | `asr-eval-v1` | ﻣﺪﺭﺳﺔ | مدرسه | ة → ه | correct | ﻣﺪﺭﺳﺔ is مدرسة in presentation forms; the letters are mapped (not lossy), then ة → ه (lossy) under asr-eval-v1. |
| dev-050 | `asr-eval-v1` | الساعة ٣‎:٣٠ | الساعه 3 30 | ة → ه | correct | الساعة → الساعه under asr-eval-v1 (scoring only). |
| dev-051 | `bayanat-norm-v1` | نعم، شكرا؛ هل أنت بخير؟ | نعم، شكرا؛ هل انت بخير؟ | أ → ا | correct | أنت → انت. أنت (you) and أنّت (she groaned) both become انت. |
| dev-052 | `asr-eval-v1` | نعم، شكرا؛ هل أنت بخير؟ | نعم شكرا هل انت بخير | أ → ا | correct | As dev-051, under asr-eval-v1. |
| dev-054 | `bayanat-norm-v1` | قال: «إلى اللقاء» | قال: «الي اللقاء» | إ → ا; ى → ي | correct | إلى → الي inside quotation marks, as in dev-010. |
| dev-060 | `asr-eval-v1` | ٱلْكِتَٰبُ | الكتب | ٱ → ا | correct, flag conservative | The only flagged change is ٱ → ا, conservative as in dev-011. The real merge in this fixture comes from removing the superscript alef: Uthmani ٱلْكِتَٰبُ (al-kitāb, the book) becomes الكتب, the spelling of al-kutub (the books). That change is not flagged, because the superscript alef is counted as a vowel mark (DECISIONS D-04). Documented as a limitation (finding L-2). |
| dev-062 | `asr-eval-v1` | كلمة أخرى | كلمه اخري | أ → ا; ة → ه; ى → ي | correct | كلمة → كلمه (ة → ه) and أخرى → اخري (أ → ا, ى → ي) under asr-eval-v1. |
| acc-002 | `asr-eval-v1` | 👩🏽‍💻 مبرمجة | 👩🏽‍💻 مبرمجه | ة → ه | correct | مبرمجة → مبرمجه under asr-eval-v1. |
| acc-006 | `bayanat-norm-v1` | ݐࢠى | ݐࢠي | ى → ي | correct | ى → ي applies whatever the neighbouring letters; the Arabic Supplement and Extended-A letters are kept. The string is a code-point test, not a word. In some other languages written in Arabic script (for example Uyghur) ى and ي are different letters, so the flag is justified (finding L-3). |
| acc-012 | `asr-eval-v1` | ﴿نص﴾ آخر | نص اخر | آ → ا | correct | آخر → اخر, the same merge as in dev-010. |
| acc-013 | `bayanat-norm-v1` | اـٔمل | امل | ٔ →  | correct | Once the tatweel is removed the hamza sits on the alef, the decomposed form of أ; reading it so gives the word أمل (hope). The output امل is also the normalised form of آمل (I hope). |
| acc-014 | `bayanat-norm-v1` | شىٔ | شئ | ى → ي | correct, flag conservative | ى followed by a combining hamza above is how ئ is drawn (the seat of ئ has no dots); after ى → ي the final NFC pass composes ئ. The output letter is the one the writer meant, so the flag is conservative. |
| acc-016 | `asr-eval-v1` | ؜۱٬۲۵۰٫۵ ليرة | 1 250 5 ليره | ة → ه | correct | ليرة → ليره under asr-eval-v1. |

## Stress-run context classes

Counts are lossy changes in 113752 Arabic Wikipedia articles (bayanat-norm-v1 for alef variants and alef maqsura; asr-eval-v1 for taa marbuta), from [stress/stats.json](stress/stats.json). No corpus text was kept; the examples in the notes are standard dictionary words chosen by the reviewer.

| Rule | Source | Position | Extra context | Changes | Share of rule | Verdict | Note |
|---|---|---|---|---|---|---|---|
| taa_marbuta.to_heh | U+0629 | final |  | 3438196 | 99.91% | correct | The normal place of ة. Merges كرة (ball) / كره (hatred) and حياة (life) / حيّاه (he greeted him). |
| alef_variants.map | U+0623 | initial |  | 1875663 | 64.32% | correct | Word-initial hamza on alef, the largest class. Merges such as أنت / أنّت and أمر / إمر. |
| alef_variants.map | U+0623 | stem_initial_after_prefix |  | 480065 | 16.46% | correct | As word-initial, after ال، و، ف، ب، ك، ل or لل (for example الأول, وأن). |
| alef_variants.map | U+0625 | initial |  | 287105 | 9.85% | correct | Word-initial hamza under alef: إنّ / أنّ, إلى / إليّ. |
| alef_maqsura.to_yeh | U+0649 | final |  | 223450 | 99.85% | correct | The normal place of ى. على / علي, يحيى / يُحيي. |
| alef_variants.map | U+0625 | stem_initial_after_prefix |  | 165398 | 5.67% | correct | As word-initial, after a proclitic (بإمكان، والإسلام). |
| alef_variants.map | U+0623 | medial |  | 55236 | 1.89% | correct | Stem-medial hamza on alef (سأل، رأس، مسألة) and stem-initial أ after a longer prefix chain. The clearest merges: سأل (he asked) / سال (it flowed). |
| alef_variants.map | U+0622 | initial |  | 30810 | 1.06% | correct | آ = hamza + long a: آمن (he believed), أمن (security) and امن all become امن. |
| alef_variants.map | U+0622 | stem_initial_after_prefix |  | 12608 | 0.43% | correct | As word-initial, after a proclitic (الآن، والآخر). |
| alef_variants.map | U+0623 | final |  | 4917 | 0.17% | correct | Final hamza on alef (بدأ، مبدأ، ملجأ): بدأ (he began) / بدا (it appeared). |
| taa_marbuta.to_heh | U+0629 | alone |  | 2901 | 0.08% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0622 | medial |  | 2236 | 0.08% | correct | Medial آ (مآذن، القرآن): the hamza is lost, as in dev-016. |
| alef_variants.map | U+0623 | alone |  | 1102 | 0.04% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0625 | medial |  | 816 | 0.03% | correct | Stem-initial إ after a prefix chain the classifier does not list (such as وبال), and misspellings. إ belongs at the start of a stem. |
| alef_maqsura.to_yeh | U+0649 | after_prefix_word_final |  | 304 | 0.14% | correct | A proclitic plus final ى: short words such as الى (إلى written without hamza), فى and لى (spellings of في and لي) or ولّى (he turned away). For الى، فى، لى the output equals the normalised standard spelling (conservative); for ولّى / وليّ (guardian) the merge is real. |
| alef_variants.map | U+0625 | alone |  | 136 | 0.00% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| taa_marbuta.to_heh | U+0629 | medial |  | 46 | 0.00% | correct | ة is written only at the end of a word. Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0622 | final |  | 30 | 0.00% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0622 | alone |  | 21 | 0.00% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| taa_marbuta.to_heh | U+0629 | after_prefix_word_final |  | 20 | 0.00% | correct | A proclitic followed only by ة. Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_maqsura.to_yeh | U+0649 | medial |  | 18 | 0.01% | correct | ى is written only at the end of an Arabic word; inside a word it is a misspelling or a letter of another language (finding L-3). |
| alef_maqsura.to_yeh | U+0649 | alone |  | 18 | 0.01% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0623 | after_prefix_word_final |  | 14 | 0.00% | correct | A proclitic followed only by أ. Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0625 | final |  | 5 | 0.00% | correct | Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_maqsura.to_yeh | U+0649 | final | followed_by_superscript_alef | 4 | 0.00% | correct | Quranic spelling such as عَلَىٰ: the superscript alef (a vowel mark) is removed and ى → ي, giving علي like the unvocalised على. |
| alef_variants.map | U+0671 | initial |  | 3 | 0.00% | correct, flag conservative | Alef wasla appears in vocalised Quranic or classical quotations; standard spelling writes ا, so the output is the standard form (finding L-4). |
| taa_marbuta.to_heh | U+0629 | initial |  | 2 | 0.00% | correct | ة is written only at the end of a word. Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_variants.map | U+0625 | after_prefix_word_final |  | 2 | 0.00% | correct | A proclitic followed only by إ. Not a position this letter takes in a well-formed Arabic word: a letter cited on its own, a word split by markup, a misspelling, or a prefix chain the classifier does not list. The rule applies mechanically and gives the output it promises. |
| alef_maqsura.to_yeh | U+0649 | final | followed_by_hamza_or_madda_mark_U+0654 | 1 | 0.00% | correct, flag conservative | ى + combining hamza is how ئ is drawn; the final NFC pass composes ئ (as acc-014). |
| alef_variants.map | U+0671 | medial |  | 1 | 0.00% | correct, flag conservative | As above (finding L-4). |
| alef_variants.map | U+0671 | stem_initial_after_prefix |  | 1 | 0.00% | correct, flag conservative | As above (finding L-4). |

## Lossy wording in the policy cards

The lossy-rule lines and limitations of the six policy cards (`docs/policies/*.md`, English and Arabic) were read against the rules. The descriptions of alef_variants.map, alef_maqsura.to_yeh and taa_marbuta.to_heh are accurate in both languages. Two limitation lines were added to bayanat-norm-v1 and asr-eval-v1 (L-2, L-3) through `scripts/make_docs.py`. The Arabic of those new lines was written in this session and is covered by the cards' own pending native review.

## Human linguist sign-off (recommended)

Scope for the linguist: the 24 lossy fixtures above, the 31 stress classes, findings L-1 to L-5 and the lossy lines of the six policy cards.

| Reviewer (name) | Date | Fixtures and classes reviewed | Verdict | Notes |
|---|---|---|---|---|
| | | | | |
