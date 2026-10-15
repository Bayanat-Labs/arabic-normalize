# arabic-normalize

**Arabic text normalisation with named, versioned, hash-identified policies. By Bayanat Labs.**

arabic-normalize applies a *named policy* such as `bayanat-norm-v1` to Arabic text and tells you exactly what it changed: the normalised text, an offset map from every output character back to the input, a per-rule change log, the lossy changes (for example ى → ي), a diacritization ratio and the SHA-256 of the policy. A paper, a WER score or a dataset card can then say "normalised with bayanat-norm-v1 (sha256 ebdb8200…, arabic-normalize 0.1.0)" and anyone can reproduce the text byte for byte.

- Pure Python, no runtime dependencies, Python 3.9 to 3.14.
- Unicode data pinned to UCD 18.0.0 and shipped with the package, so output does not depend on your Python version.
- Policies are immutable: a change in behaviour ships as a new policy id, never as an edit.
- Licence: Apache-2.0 (code); policies and conformance fixtures CC BY 4.0.

Status: v0.1.0 pilot (three policies, 80 conformance fixtures, Python and JavaScript). The web page in `web/` runs in the browser as the Hugging Face Space [Bayanat-Labs/arabic-normalizer](https://huggingface.co/spaces/Bayanat-Labs/arabic-normalizer); more policies (compatibility policies, a search policy) are planned.

## Install

PyPI and npm releases are coming. Until then, install from GitHub:

```bash
pip install "git+https://github.com/Bayanat-Labs/arabic-normalize"
```

From a clone of this repository, `pip install .` does the same.

JavaScript (ES module, no runtime dependencies, same output as Python; see [js/README.md](js/README.md)): install the `js/` folder of a clone. npm links the package to that folder, so keep it.

```bash
git clone https://github.com/Bayanat-Labs/arabic-normalize.git
npm install ./arabic-normalize/js
```

```js
import { normalize, normalizeDetailed } from '@bayanat-labs/arabic-normalize';
normalize('إِلَى المَدْرَسَةِ');  // 'الي المدرسة'
```

## Worked example

<!-- BEGIN:example -->
```python
>>> from arabic_normalize import normalize, normalize_detailed
>>> text = "إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣"
>>> normalize(text)                        # bayanat-norm-v1, the default
'الي المدرسة الجديدة 123'
>>> normalize(text, "asr-eval-v1")         # for WER/CER scoring
'الي المدرسه الجديده 123'
>>> normalize(text, "raw-safe-v1")         # cleaning only, letters untouched
'إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣'
>>> r = normalize_detailed(text)
>>> r.lossy_flags
('alef_maqsura.to_yeh', 'alef_variants.map')
>>> r.flags
('taa_marbuta.flag',)
>>> round(r.diacritization_ratio, 3)
0.647
>>> r.policy_hash
'ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321'
>>> [c for c in r.changes if c.rule_id == "alef_maqsura.to_yeh"]
[Change(stage='alef_maqsura', rule_id='alef_maqsura.to_yeh', src_start=4, src_end=5, before='ى', after='ي', lossy=True)]
```

```console
$ echo "إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣" | arnorm normalize
الي المدرسة الجديدة 123
$ echo "إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣" | arnorm normalize --policy asr-eval-v1
الي المدرسه الجديده 123
```
<!-- END:example -->

In this example the hamza under the alef of إلى and the final ى are folded (both lossy, both logged), the harakat are removed (counted in the diacritization ratio), the Arabic-Indic digits become ASCII, and the taa marbuta is kept and flagged. Only `asr-eval-v1` folds ة to ه.

## Policies

<!-- BEGIN:policies -->
| Policy | SHA-256 | Use | Lossy rules | Card |
|---|---|---|---|---|
| `bayanat-norm-v1` | `ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321` | Default for text_norm columns in Bayanat Labs datasets, deduplication and statistics. | alef_maqsura.to_yeh, alef_variants.map | [EN](docs/policies/bayanat-norm-v1.md) · [AR](docs/policies/bayanat-norm-v1.ar.md) |
| `asr-eval-v1` | `5d866146536a23b90c0882044dae5f55f2484f0635e206828246eabeb69668de` | Scoring only: WER and CER for Arabic speech recognition. | alef_maqsura.to_yeh, alef_variants.map, taa_marbuta.to_heh | [EN](docs/policies/asr-eval-v1.md) · [AR](docs/policies/asr-eval-v1.ar.md) |
| `raw-safe-v1` | `57c3d9f03fb9b6854f2527cd1e8a47cadc266f47f02dda94652306dacea03bb5` | Cleaning without changing any letter, mark, digit or punctuation. | none | [EN](docs/policies/raw-safe-v1.md) · [AR](docs/policies/raw-safe-v1.ar.md) |
<!-- END:policies -->

The hash covers everything that affects output (every stage mode, the Unicode form and the Unicode version) and nothing else; see [docs/SPEC.md](docs/SPEC.md) section 2. `arnorm policy export bayanat-norm-v1 --canonical` prints the exact bytes that are hashed. The design choices, including why bayanat-norm-v1 maps Arabic presentation forms rather than applying full NFKC and why it keeps ة, are in [docs/DECISIONS.md](docs/DECISIONS.md).

## Python API

| Function | Returns |
|---|---|
| `normalize(text, policy="bayanat-norm-v1", strict=False)` | the normalised string |
| `normalize_detailed(text, policy, strict=False)` | a `Result`: `text_norm`, `offset_map`, `changes`, `lossy_flags`, `flags`, `diacritization_ratio`, `rejected_spans`, `stats`, `policy_id`, `policy_hash`, `lib_version`, `unicode_version`, `original_hash`, `text_diac`; `Result.to_dict()` matches `schemas/output.schema.json` |
| `diff_policies(text, a, b)` | both outputs, the rules only one policy applies, and the input regions where they differ |
| `explain(text, policy)` | one row per input code point: name, category, combining class, joining type, rules applied, output |
| `load_policy(id_or_path_or_dict)`, `list_policies()`, `policy_hash(policy)` | policy objects and their identity |
| `normalize_bytes(data, ...)`, `normalize_request(request)` | strict UTF-8 decoding and the input contract (10 MiB per text, 10,000 texts per request) |

`policy` can be a built-in id, a path to a policy JSON file, a dict or a `Policy`. Custom policies get their own hash; nothing is fetched from the network. Invalid code points (lone surrogates, control characters other than whitespace, noncharacters) are removed and reported in `rejected_spans`; with `strict=True` they raise `InputRejected` instead.

## Command line

```console
arnorm normalize [--policy ID|FILE] [--jsonl|--csv] [--field text] [--detailed] [--strict] [--out FILE] [--resume] [FILE ...]
arnorm diff "نص" --a bayanat-norm-v1 --b asr-eval-v1
arnorm explain "ﻷنّ"
arnorm policy list | show ID | export ID [--canonical] | hash ID_OR_FILE
arnorm version
```

Files are streamed record by record. `--jsonl` adds `text_norm`, `policy_id`, `policy_hash`, `lib_version` and `unicode_version` to each record (`--detailed` adds the offset map, change log and flags). `--csv` adds the same five columns (`--detailed` adds lossy flags, flags, the diacritization ratio and change and rejection counts). `--resume` continues an interrupted text or JSONL run from `OUT.checkpoint`. A rejected record stops the run with exit code 2 unless `--on-error skip` or `--on-error record` is given.

## Tests and conformance

<!-- BEGIN:counts -->
| Split | Fixtures | Passing (Python) | Passing (JavaScript) |
|---|---|---|---|
| dev | 64 | 64 | 64 |
| acceptance | 16 | 16 | 16 |
| rejected inputs | 20 | 20 | 20 |

By policy (dev + acceptance): asr-eval-v1 15/15, bayanat-norm-v1 52/52, raw-safe-v1 13/13. Computed by `scripts/make_docs.py` from the fixture files on 2026-10-15.

JavaScript port (`js/`): 560 of 560 reference cases (the 80 fixtures under 7 policies) and 80 of 80 policy comparisons are identical to the Python engine, including the offset map and change log; counts from `js/conformance.json` (`js/scripts/conformance_counts.mjs`).
<!-- END:counts -->

The test suite also checks every line of the Unicode 18.0.0 NormalizationTest.txt for NFC, NFD, NFKC and NFKD, every RGI emoji ZWJ sequence, policy hash stability, and properties on random Arabic-heavy strings (idempotence, offset-map consistency, no silent changes). Fixtures are original text written by Bayanat Labs, labelled synthetic/illustrative, and contain no personal data. An independent AI review of every lossy fixture and of the lossy cases met in the stress run is in [docs/LOSSY_REVIEW.md](docs/LOSSY_REVIEW.md); the native-speaker sign-off is pending (`tests/fixtures/REVIEW.md`).

- Stress run on one Arabic Wikipedia dump part (crashes, offset-map checks, throughput, lossy-flag rates; statistics only): [docs/stress/report.md](docs/stress/report.md).
- Agreement of CAMeL Tools, tnkeeh, Whisper's basic normaliser and PyArabic with the pilot policies on the fixtures (tables only; the tools run outside this repository): [docs/compat/README.md](docs/compat/README.md).

```bash
pip install -e ".[test]" && pytest
```

## How it compares

Other open tools normalise Arabic too: CAMeL Tools (MIT), PyArabic (GPL), tnkeeh (MIT), the Lucene/Elasticsearch `arabic_normalization` filter (Apache-2.0), Whisper's text normaliser (MIT) and an unrelated npm package also named `arabic-normalize` (MIT). arabic-normalize does not replace them; it adds named, immutable policies with a published hash, an offset map, a change log with lossy flags, and pinned Unicode data. A dated census of package registries and repository search results is in [CLAIMS.md](CLAIMS.md) and `evidence/census_2026-10-15.json`. This project is not affiliated with the npm package of the same name.

## Licence, citation, contact

Code: Apache-2.0 ([LICENSE](LICENSE)). Policy files and conformance fixtures: CC BY 4.0 ([LICENSE-data](LICENSE-data)). Generated Unicode tables: Unicode License V3 ([NOTICE-unicode.txt](NOTICE-unicode.txt)). To cite, use [CITATION.cff](CITATION.cff) and name the policy id and hash you used.

Questions, corrections and takedown requests: open@bayanatlabs.com.

**Need production-grade, rights-cleared Arabic data with documented normalisation?** See [Bayanat Labs Knowledge](https://bayanatlabs.com/products/knowledge).
