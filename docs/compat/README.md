# Agreement with other Arabic normalisers on the pilot fixtures

Generated 2026-10-15 from the 80 pilot fixtures (64 dev, 16 acceptance) and arabic-normalize 0.1.0 (UCD 18.0.0) by `scripts/compat/compare.py`. The CAMeL Tools, tnkeeh and Whisper harnesses are in `scripts/compat/harness/`; the PyArabic harness is kept outside this repository so that no file here imports a GPL module, and is passed to the driver with `--harness pyarabic=PATH`. Every number below is computed by the driver; the machine-readable result is [agreement.json](agreement.json) and the per-fixture table is [fixtures.md](fixtures.md).

This is a pilot comparison on synthetic fixtures, not the brief's compatibility target (paragraph-level exact match on 10,000 stress paragraphs for each future `compat-*` policy). The pilot ships no compat policy; these tables show how far each tool's closest pipeline is from the three pilot policies, and where, so that compat policies can be designed later.

## How the oracles were run

- Each tool is installed in its own virtual environment outside this repository and is called as a subprocess that exchanges JSON lines. No oracle code is imported by, copied into or shipped with arabic-normalize. PyArabic is GPL and is used only this way.
- Only each tool's public functions are called, in the compositions below. Nothing is re-implemented.
- The tools use the Unicode data of their interpreter; arabic-normalize uses its pinned UCD 18.0.0 tables.

| Oracle | Licence | Python | Interpreter Unicode | Installed packages |
|---|---|---|---|---|
| CAMeL Tools 1.6.0 | MIT | 3.12.14 | 15.0.0 | camel-tools==1.6.0, emoji==2.16.0, six==1.17.0 |
| tnkeeh 0.0.9 | MIT | 3.12.14 | 15.0.0 | numpy==2.5.4, pandas==3.0.6, python-dateutil==2.9.0.post0, six==1.17.0, tnkeeh==0.0.9 |
| Whisper BasicTextNormalizer (whisper-normalizer 0.1.15) | MIT | 3.12.14 | 15.0.0 | indic-numtowords==1.1.0, more-itertools==11.2.1, regex==2026.9.29, text2num==3.1.0, whisper-normalizer==0.1.15 |
| PyArabic 0.6.15 (subprocess only) | GPL | 3.12.14 | 15.0.0 | pyarabic==0.6.15, six==1.17.0 |

Installation notes: camel-tools was installed without its declared dependencies (torch, transformers, kenlm and others are not needed by `camel_tools.utils`); only `emoji` and `six`, which the utility modules import, were added. tnkeeh imports `farasa.segmenter` at load time but uses it only for segmentation, which is not used here, so farasapy (which downloads a Java archive on first use) is not installed and an inert module stands in for it.

### Pipelines

| Pipeline | Calls | Compared with |
|---|---|---|
| `camel-nfc` | `normalize_unicode(s, compatibility=False)` (NFC) | `raw-safe-v1` |
| `camel-norm` | `normalize_unicode(s)` (NFKC plus two ligature fixes) → `dediac_ar` → `normalize_alef_ar` → `normalize_alef_maksura_ar` | `bayanat-norm-v1` |
| `camel-asr` | camel-norm → `normalize_teh_marbuta_ar` | `asr-eval-v1` |
| `tnkeeh-default` | `Tnkeeh().clean_raw_text(s)` with every option off (the tool still pads non-letters with spaces and squeezes runs of spaces) | `raw-safe-v1` |
| `tnkeeh-norm` | `Tnkeeh(normalize=True, remove_diacritics=True, remove_tatweel=True).clean_raw_text(s)` | `bayanat-norm-v1` |
| `tnkeeh-asr` | tnkeeh-norm options plus `remove_special_chars=True` | `asr-eval-v1` |
| `whisper-basic` | `BasicTextNormalizer()(s)` (the default Whisper basic normaliser) | `asr-eval-v1` |
| `whisper-basic-rd` | `BasicTextNormalizer(remove_diacritics=True)(s)` | matrix only |
| `pyarabic-brief` | `strip_tashkeel` → `strip_tatweel` → `normalize_hamza` (default method) → `normalize_ligature` (the composition the TL-003 brief names for compat-pyarabic-v1) | matrix only |
| `pyarabic-norm` | `normalize_ligature` → `strip_diacritics` → `strip_tatweel` → `normalize_alef` | `bayanat-norm-v1` |
| `pyarabic-asr` | pyarabic-norm → `normalize_teh` | `asr-eval-v1` |

Whisper has no counterpart of `bayanat-norm-v1` or `raw-safe-v1`, and PyArabic none of `raw-safe-v1`; those cells are n/a in the per-fixture table.

## Agreement with the closest pipeline, per fixture policy

Exact: identical output. Spacing: identical after squeezing whitespace runs and trimming both outputs. Spacing+punct.: identical after also turning every punctuation character into a space on both sides.

| Oracle | Policy | Fixtures | Exact | Spacing | Spacing+punct. |
|---|---|---|---|---|---|
| CAMeL Tools 1.6.0 | `bayanat-norm-v1` | 52 | 30 | 30 | 30 |
| tnkeeh 0.0.9 | `bayanat-norm-v1` | 52 | 12 | 16 | 17 |
| PyArabic 0.6.15 (subprocess only) | `bayanat-norm-v1` | 52 | 30 | 30 | 30 |
| CAMeL Tools 1.6.0 | `raw-safe-v1` | 13 | 11 | 11 | 11 |
| tnkeeh 0.0.9 | `raw-safe-v1` | 13 | 3 | 5 | 5 |
| CAMeL Tools 1.6.0 | `asr-eval-v1` | 15 | 8 | 9 | 12 |
| tnkeeh 0.0.9 | `asr-eval-v1` | 15 | 2 | 3 | 3 |
| Whisper BasicTextNormalizer (whisper-normalizer 0.1.15) | `asr-eval-v1` | 15 | 1 | 1 | 1 |
| PyArabic 0.6.15 (subprocess only) | `asr-eval-v1` | 15 | 6 | 6 | 9 |

## Matrix: every pipeline against every pilot policy (all 80 inputs, exact match)

| Pipeline | bayanat-norm-v1 | asr-eval-v1 | raw-safe-v1 |
|---|---|---|---|
| `camel-nfc` | 20 (20 / 20) | 12 (12 / 14) | 67 (67 / 67) |
| `camel-norm` | 48 (49 / 49) | 33 (34 / 40) | 26 (26 / 26) |
| `camel-asr` | 39 (40 / 40) | 40 (43 / 49) | 20 (20 / 20) |
| `tnkeeh-default` | 5 (10 / 12) | 2 (6 / 8) | 13 (22 / 29) |
| `tnkeeh-norm` | 20 (25 / 27) | 15 (19 / 21) | 11 (17 / 24) |
| `tnkeeh-asr` | 23 (31 / 33) | 18 (26 / 26) | 13 (20 / 26) |
| `whisper-basic` | 16 (20 / 20) | 11 (14 / 14) | 26 (28 / 34) |
| `whisper-basic-rd` | 29 (30 / 33) | 23 (27 / 27) | 18 (19 / 21) |
| `pyarabic-brief` | 29 (29 / 29) | 21 (21 / 23) | 33 (33 / 33) |
| `pyarabic-norm` | 46 (46 / 46) | 34 (34 / 39) | 27 (27 / 27) |
| `pyarabic-asr` | 39 (39 / 39) | 40 (41 / 46) | 21 (21 / 21) |

Cells: exact matches out of 80, then (spacing / spacing+punct.) matches.

## Where they diverge

Character classes involved in the differing segments, counted over the fixtures compared with each oracle's closest pipeline (one fixture can count in several classes).

| Oracle | Classes (fixtures) |
|---|---|
| CAMeL Tools 1.6.0 | invisible_controls (10), digits (6), punctuation (6), whitespace (5), tatweel (4), alef (3), other_arabic (3), rejected_code_points (3), alef_maqsura_yeh (2), taa_marbuta_heh (2), honorific (2), quranic_marks (2), hamza (2) |
| tnkeeh 0.0.9 | whitespace (51), alef (11), alef_maqsura_yeh (10), invisible_controls (9), taa_marbuta_heh (6), digits (6), hamza (5), other_arabic (3), rejected_code_points (3), latin (2), other_marks (2), quranic_marks (2), presentation_forms (2), harakat (1), superscript_alef (1), symbols (1) |
| Whisper BasicTextNormalizer (whisper-normalizer 0.1.15) | whitespace (9), taa_marbuta_heh (6), alef (5), digits (3), alef_maqsura_yeh (2), invisible_controls (2), latin (1), symbols (1) |
| PyArabic 0.6.15 (subprocess only) | alef (8), alef_maqsura_yeh (8), invisible_controls (8), digits (6), punctuation (6), whitespace (5), presentation_forms (4), rejected_code_points (3), other_arabic (2), taa_marbuta_heh (1), quranic_marks (1), honorific (1), hamza (1) |

Behaviour checks computed from the same runs:

- Whisper basic normaliser: on 10 of the 13 fixtures that contain harakat, its output has more space-separated tokens than `asr-eval-v1`, because it replaces every combining mark with a space and so splits vocalised words.
- CAMeL Tools `normalize_unicode` (NFKC): on 3 of the 3 fixtures with U+FDFA or U+FDF2, the honorific ligature was expanded into words; `bayanat-norm-v1` keeps it and flags it (DECISIONS D-01).

### Behaviour fingerprint

Short probe strings, each isolating one feature, run through every pipeline. Inputs and outputs are shown as escapes, with a space written as `\u0020`; (empty) means the output is empty.

| Probe | Input | `bayanat-norm-v1` | `asr-eval-v1` | `raw-safe-v1` | `camel-nfc` | `camel-norm` | `camel-asr` | `tnkeeh-default` | `tnkeeh-norm` | `tnkeeh-asr` | `whisper-basic` | `whisper-basic-rd` | `pyarabic-brief` | `pyarabic-norm` | `pyarabic-asr` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| alef maqsura | \u0649 | \u064a | \u064a | \u0649 | \u0649 | \u064a | \u064a | \u0649 | \u0649 | \u0649 | \u0649 | \u0649 | \u0649 | \u0627 | \u0627 |
| alef variants | \u0623\u0625\u0622\u0671 | \u0627\u0627\u0627\u0627 | \u0627\u0627\u0627\u0627 | \u0623\u0625\u0622\u0671 | \u0623\u0625\u0622\u0671 | \u0627\u0627\u0627\u0627 | \u0627\u0627\u0627\u0627 | \u0623\u0625\u0622\u0020\u0671\u0020 | \u0623\u0625\u0622\u0627 | \u0623\u0625\u0622\u0627 | \u0623\u0625\u0622\u0671 | \u0627\u0627\u0627\u0671 | \u0621\u0621\u0621\u0621\u0671 | \u0627\u0627\u0627\u0627 | \u0627\u0627\u0627\u0627 |
| taa marbuta | \u0629 | \u0629 | \u0647 | \u0629 | \u0629 | \u0629 | \u0647 | \u0629 | \u0629 | \u0629 | \u0629 | \u0629 | \u0629 | \u0629 | \u0647 |
| hamza carriers | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0624\u0626 | \u0648\u064a | \u0621\u0621 | \u0624\u0626 | \u0624\u0626 |
| fatha on a letter | \u0643\u064e\u062a | \u0643\u062a | \u0643\u062a | \u0643\u064e\u062a | \u0643\u064e\u062a | \u0643\u062a | \u0643\u062a | \u0643\u0020\u064e\u0020\u062a | \u0643\u062a | \u0643\u062a | \u0643\u0020\u062a | \u0643\u062a | \u0643\u062a | \u0643\u062a | \u0643\u062a |
| superscript alef | \u0647\u0670\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0670\u0630\u0627 | \u0647\u0670\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0020\u0670\u0020\u0630\u0627 | \u0647\u0020\u0670\u0020\u0630\u0627 | \u0647\u0020\u0630\u0627 | \u0647\u0020\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0670\u0630\u0627 | \u0647\u0630\u0627 | \u0647\u0630\u0627 |
| tatweel | \u0628\u0640\u0628 | \u0628\u0628 | \u0628\u0628 | \u0628\u0640\u0628 | \u0628\u0640\u0628 | \u0628\u0640\u0628 | \u0628\u0640\u0628 | \u0628\u0640\u0628 | \u0628\u0628 | \u0628\u0628 | \u0628\u0640\u0628 | \u0628\u0640\u0628 | \u0628\u0628 | \u0628\u0628 | \u0628\u0628 |
| Arabic-Indic digits | \u0661\u0662 | 12 | 12 | \u0661\u0662 | \u0661\u0662 | \u0661\u0662 | \u0661\u0662 | \u0020\u0661\u0020\u0662\u0020 | \u0020\u0661\u0020\u0662\u0020 | \u0020 | \u0661\u0662 | \u0661\u0662 | \u0661\u0662 | \u0661\u0662 | \u0661\u0662 |
| lam-alef ligature | \ufefb | \u0644\u0627 | \u0644\u0627 | \ufefb | \ufefb | \u0644\u0627 | \u0644\u0627 | \u0020\ufefb\u0020 | \u0644\u0627 | \u0644\u0627 | \u0644\u0627 | \u0644\u0627 | \u0644\u0627 | \u0644\u0627 | \u0644\u0627 |
| U+FDFA | \ufdfa | \ufdfa | \ufdfa | \ufdfa | \ufdfa | \u0635\u0644\u064a\u0020\u0627\u0644\u0644\u0647\u0020\u0639\u0644\u064a\u0647\u0020\u0648\u0633\u0644\u0645 | \u0635\u0644\u064a\u0020\u0627\u0644\u0644\u0647\u0020\u0639\u0644\u064a\u0647\u0020\u0648\u0633\u0644\u0645 | \u0020\ufdfa\u0020 | \u0020\ufdfa\u0020 | \u0020 | \u0635\u0644\u0649\u0020\u0627\u0644\u0644\u0647\u0020\u0639\u0644\u064a\u0647\u0020\u0648\u0633\u0644\u0645 | \u0635\u0644\u0649\u0020\u0627\u0644\u0644\u0647\u0020\u0639\u0644\u064a\u0647\u0020\u0648\u0633\u0644\u0645 | \ufdfa | \ufdfa | \ufdfa |
| ZWNJ between joiners | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u0020\u200c\u0020\u0628 | \u0628\u0020\u200c\u0020\u0628 | \u0628\u0020\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 | \u0628\u200c\u0628 |
| Arabic comma | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u0020\u060c\u0020\u0628 | \u0628\u0020\u060c\u0020\u0628 | \u0628\u0020\u0628 | \u0628\u0020\u0628 | \u0628\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 | \u0628\u060c\u0020\u0628 |
| Latin capital | AB | AB | AB | AB | AB | AB | AB | AB | AB | AB | ab | ab | AB | AB | AB |

## What this means for compat policies

None of the four tools is a drop-in match for a pilot policy, which is expected: the pilot policies keep punctuation and spacing (bayanat-norm-v1), remove invisible controls and invalid code points, and pin Unicode data. The `compat-camel-v1`, `compat-whisper-basic-v1` and `compat-pyarabic-v1` policies planned for v1.0 must be designed from these divergence classes and then verified on the stress corpus, as the brief requires. Lucene was not run in this pass (no Java harness yet).
