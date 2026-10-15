# Per-fixture agreement with other normalisers

Generated 2026-10-15 by `scripts/compat/compare.py` (see [README.md](README.md)). Each cell compares the oracle's closest pipeline for the fixture's policy (see [README.md](README.md)) with the fixture's expected output, which arabic-normalize reproduces. `=` exact match; `≈ws` equal after squeezing spaces; `≈p` equal after also dropping punctuation; `≠` different, followed by the character classes that differ. n/a: the tool has no counterpart of that policy. Oracle outputs, as escapes, are in [agreement.json](agreement.json).

| Fixture | Family | Policy | CAMeL Tools | tnkeeh | Whisper basic | PyArabic |
|---|---|---|---|---|---|---|
| dev-001 | diacritics | `bayanat-norm-v1` | = | = | n/a | = |
| dev-002 | diacritics | `bayanat-norm-v1` | = | = | n/a | = |
| dev-003 | diacritics | `bayanat-norm-v1` | = | = | n/a | = |
| dev-004 | diacritics | `raw-safe-v1` | = | ≠ whitespace, harakat | n/a | n/a |
| dev-005 | diacritics | `bayanat-norm-v1` | = | = | n/a | = |
| dev-006 | diacritics | `asr-eval-v1` | = | = | ≠ whitespace | = |
| dev-007 | tatweel | `bayanat-norm-v1` | ≠ tatweel | = | n/a | = |
| dev-008 | tatweel | `bayanat-norm-v1` | ≠ tatweel | = | n/a | = |
| dev-009 | tatweel | `raw-safe-v1` | = | = | n/a | n/a |
| dev-010 | alef_hamza | `bayanat-norm-v1` | = | ≠ alef, alef_maqsura_yeh | n/a | ≠ alef, alef_maqsura_yeh |
| dev-011 | alef_hamza | `bayanat-norm-v1` | = | = | n/a | = |
| dev-012 | alef_hamza | `bayanat-norm-v1` | = | ≠ whitespace, hamza | n/a | = |
| dev-013 | alef_hamza | `raw-safe-v1` | = | ≠ whitespace, alef, hamza | n/a | n/a |
| dev-014 | alef_hamza | `asr-eval-v1` | = | ≠ alef | ≠ whitespace, alef | = |
| dev-015 | alef_hamza | `bayanat-norm-v1` | = | ≠ alef | n/a | = |
| dev-016 | alef_hamza | `bayanat-norm-v1` | = | ≠ alef | n/a | = |
| dev-017 | alef_maqsura | `bayanat-norm-v1` | = | ≠ alef_maqsura_yeh | n/a | ≠ alef, alef_maqsura_yeh |
| dev-018 | alef_maqsura | `bayanat-norm-v1` | = | ≠ alef_maqsura_yeh | n/a | ≠ alef, alef_maqsura_yeh |
| dev-019 | alef_maqsura | `raw-safe-v1` | = | = | n/a | n/a |
| dev-020 | alef_maqsura | `asr-eval-v1` | = | ≠ alef_maqsura_yeh | ≠ alef_maqsura_yeh | ≠ alef, alef_maqsura_yeh |
| dev-021 | taa_marbuta | `bayanat-norm-v1` | = | = | n/a | = |
| dev-022 | taa_marbuta | `asr-eval-v1` | = | ≠ taa_marbuta_heh | ≠ taa_marbuta_heh | = |
| dev-023 | taa_marbuta | `raw-safe-v1` | = | = | n/a | n/a |
| dev-024 | taa_marbuta | `bayanat-norm-v1` | = | = | n/a | = |
| dev-025 | hamza_carriers | `bayanat-norm-v1` | = | = | n/a | = |
| dev-026 | hamza_carriers | `asr-eval-v1` | = | = | = | = |
| dev-027 | persian_urdu | `bayanat-norm-v1` | = | ≠ whitespace | n/a | = |
| dev-028 | persian_urdu | `bayanat-norm-v1` | = | ≠ alef_maqsura_yeh, other_arabic | n/a | = |
| dev-029 | persian_urdu | `bayanat-norm-v1` | = | ≠ whitespace | n/a | = |
| dev-030 | digits | `bayanat-norm-v1` | ≠ digits | ≠ whitespace, digits | n/a | ≠ digits |
| dev-031 | digits | `bayanat-norm-v1` | ≠ digits | ≠ whitespace, digits | n/a | ≠ digits |
| dev-032 | digits | `raw-safe-v1` | = | ≠ whitespace | n/a | n/a |
| dev-033 | digits | `bayanat-norm-v1` | ≠ digits | ≠ whitespace, digits | n/a | ≠ digits |
| dev-034 | presentation_forms | `bayanat-norm-v1` | = | = | n/a | = |
| dev-035 | presentation_forms | `bayanat-norm-v1` | = | ≠ alef | n/a | = |
| dev-036 | presentation_forms | `bayanat-norm-v1` | = | = | n/a | ≠ alef_maqsura_yeh, presentation_forms, other_arabic |
| dev-037 | presentation_forms | `raw-safe-v1` | = | ≈ws | n/a | n/a |
| dev-038 | presentation_forms | `asr-eval-v1` | = | ≠ taa_marbuta_heh | ≠ taa_marbuta_heh | ≠ taa_marbuta_heh, presentation_forms, other_arabic |
| dev-039 | ligatures_honorific | `bayanat-norm-v1` | ≠ whitespace, alef, alef_maqsura_yeh, taa_marbuta_heh, honorific, other_arabic | ≈ws | n/a | = |
| dev-040 | ligatures_honorific | `bayanat-norm-v1` | ≠ alef, taa_marbuta_heh, honorific, other_arabic | ≈ws | n/a | = |
| dev-041 | ligatures_honorific | `raw-safe-v1` | = | ≈ws | n/a | n/a |
| dev-042 | zero_width | `bayanat-norm-v1` | = | ≠ whitespace, alef_maqsura_yeh, other_arabic | n/a | = |
| dev-043 | zero_width | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| dev-044 | zero_width | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| dev-045 | zero_width | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| dev-046 | zero_width | `bayanat-norm-v1` | = | ≠ whitespace | n/a | = |
| dev-047 | bidi_bom | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| dev-048 | bidi_bom | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| dev-049 | bidi_bom | `raw-safe-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | n/a |
| dev-050 | bidi_bom | `asr-eval-v1` | ≠ whitespace, punctuation, digits, invisible_controls | ≠ whitespace, taa_marbuta_heh, digits | ≠ taa_marbuta_heh, digits, invisible_controls | ≠ whitespace, punctuation, digits, invisible_controls |
| dev-051 | punctuation | `bayanat-norm-v1` | = | ≠ whitespace, alef | n/a | = |
| dev-052 | punctuation | `asr-eval-v1` | ≈p | ≠ whitespace, alef | ≠ whitespace, alef | ≈p |
| dev-053 | punctuation | `asr-eval-v1` | ≠ punctuation, digits | ≠ whitespace, digits | ≠ whitespace, digits | ≠ punctuation, digits |
| dev-054 | punctuation | `bayanat-norm-v1` | = | ≠ whitespace, alef, alef_maqsura_yeh | n/a | ≠ alef, alef_maqsura_yeh |
| dev-055 | mixed_latin | `bayanat-norm-v1` | = | ≈p | n/a | = |
| dev-056 | mixed_latin | `asr-eval-v1` | ≈p | ≈ws | ≠ whitespace, latin | ≈p |
| dev-057 | mixed_latin | `raw-safe-v1` | = | ≠ whitespace, latin, other_marks | n/a | n/a |
| dev-058 | quranic_superscript | `bayanat-norm-v1` | = | ≠ whitespace, superscript_alef | n/a | = |
| dev-059 | quranic_superscript | `bayanat-norm-v1` | ≠ quranic_marks | ≠ whitespace, quranic_marks | n/a | = |
| dev-060 | quranic_superscript | `asr-eval-v1` | = | ≠ whitespace | ≠ whitespace, alef | = |
| dev-061 | quranic_superscript | `raw-safe-v1` | = | ≠ whitespace | n/a | n/a |
| dev-062 | whitespace | `asr-eval-v1` | ≈ws | ≠ whitespace, alef, alef_maqsura_yeh, taa_marbuta_heh | ≠ whitespace, alef, alef_maqsura_yeh, taa_marbuta_heh | ≠ whitespace, alef, alef_maqsura_yeh |
| dev-063 | whitespace | `bayanat-norm-v1` | = | ≈ws | n/a | = |
| dev-064 | rejected_span | `bayanat-norm-v1` | ≠ rejected_code_points | ≠ whitespace, rejected_code_points | n/a | ≠ rejected_code_points |
| acc-001 | emoji_zwj | `bayanat-norm-v1` | = | ≠ whitespace | n/a | = |
| acc-002 | emoji_zwj | `asr-eval-v1` | = | ≠ taa_marbuta_heh, invisible_controls, symbols | ≠ whitespace, taa_marbuta_heh, symbols | = |
| acc-003 | bidi_isolates | `bayanat-norm-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | ≠ invisible_controls |
| acc-004 | pf_marks | `bayanat-norm-v1` | ≠ tatweel | ≠ whitespace, presentation_forms | n/a | ≠ presentation_forms |
| acc-005 | pf_marks | `bayanat-norm-v1` | = | ≠ whitespace, presentation_forms | n/a | ≠ whitespace, presentation_forms |
| acc-006 | arabic_extended_letters | `bayanat-norm-v1` | = | ≠ whitespace, alef_maqsura_yeh | n/a | ≠ alef, alef_maqsura_yeh |
| acc-007 | arabic_compat_outside_pf | `bayanat-norm-v1` | ≠ alef, other_arabic | ≈ws | n/a | = |
| acc-008 | format_controls | `raw-safe-v1` | ≠ invisible_controls | ≠ whitespace, invisible_controls | n/a | n/a |
| acc-009 | c1_controls | `bayanat-norm-v1` | ≠ rejected_code_points | ≠ whitespace, rejected_code_points | n/a | ≠ rejected_code_points |
| acc-010 | surrogates_nonchars | `bayanat-norm-v1` | ≠ rejected_code_points | ≠ whitespace, rejected_code_points | n/a | ≠ rejected_code_points |
| acc-011 | honorific_signs_extended_marks | `bayanat-norm-v1` | ≠ quranic_marks | ≠ whitespace, quranic_marks | n/a | ≠ quranic_marks, honorific |
| acc-012 | nbsp_ornate | `asr-eval-v1` | ≈p | ≠ whitespace, alef | ≠ whitespace, alef | ≈p |
| acc-013 | decomposed_residue | `bayanat-norm-v1` | ≠ tatweel, hamza | ≠ whitespace, hamza | n/a | = |
| acc-014 | final_nfc | `bayanat-norm-v1` | ≠ hamza, alef_maqsura_yeh | ≠ whitespace, hamza, alef_maqsura_yeh | n/a | ≠ alef, hamza |
| acc-015 | nfc_compose_reorder | `raw-safe-v1` | = | ≠ whitespace, hamza, latin, other_marks, other_arabic | n/a | n/a |
| acc-016 | digits_separators | `asr-eval-v1` | ≠ whitespace, punctuation, digits, invisible_controls | ≠ whitespace, taa_marbuta_heh, digits | ≠ taa_marbuta_heh, digits, invisible_controls | ≠ whitespace, punctuation, digits, invisible_controls |
