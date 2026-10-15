# @bayanat-labs/arabic-normalize

**Arabic text normalisation with named, versioned, hash-identified policies. By Bayanat Labs.**

This is the JavaScript port of the Python package [arabic-normalize](https://github.com/Bayanat-Labs/arabic-normalize). It reads the same policy files and the same pinned Unicode tables, and gives the same output as the Python engine: the normalised text, an offset map from every output character back to the input, a per-rule change log, lossy flags (for example ى → ي), a diacritization ratio and the SHA-256 of the policy.

- ES module, no runtime dependencies. Node 20 or later (the CI matrix runs Node 20, 22 and 24), and current browsers.
- Unicode data pinned to UCD 18.0.0 and shipped with the package. `String.prototype.normalize` is never used, so the output does not depend on the ICU version of the JavaScript engine.
- Same output as Python on every conformance fixture: the 80 fixtures under 7 policies (560 cases) and 80 policy comparisons are identical, including the offset map and change log (`conformance.json`, `test/conformance.test.mjs`).
- Licence: Apache-2.0 (code). Policy files: CC BY 4.0. Generated Unicode tables: Unicode License V3.

Not affiliated with the unrelated npm package `arabic-normalize` (unscoped).

## Install

The npm package has not been released yet. Until it is, install the `js/` folder of a clone of the repository, pinned to a commit. npm links the package to that folder, so keep it.

```bash
git clone https://github.com/Bayanat-Labs/arabic-normalize.git
git -C arabic-normalize checkout da128047f20b802489adcd765c6e8c412ee44d48
npm install ./arabic-normalize/js
```

`npm install @bayanat-labs/arabic-normalize` will work once it is published.

To install a copy instead of a link, run `npm pack` in `arabic-normalize/js` and install the `.tgz` file it writes.

## Worked example

```js
import { normalize, normalizeDetailed } from '@bayanat-labs/arabic-normalize';

const text = 'إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣';
normalize(text);                  // 'الي المدرسة الجديدة 123'   (bayanat-norm-v1, the default)
normalize(text, 'asr-eval-v1');   // 'الي المدرسه الجديده 123'   (for WER/CER scoring)
normalize(text, 'raw-safe-v1');   // 'إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣' (cleaning only)

const r = normalizeDetailed(text);
r.lossy_flags;                    // ['alef_maqsura.to_yeh', 'alef_variants.map']
r.flags;                          // ['taa_marbuta.flag']
r.diacritization_ratio;           // 0.6470588235294118
r.policy_hash;                    // 'ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321'
r.changes.find((c) => c.rule_id === 'alef_maqsura.to_yeh');
// { stage: 'alef_maqsura', rule_id: 'alef_maqsura.to_yeh', src_start: 4, src_end: 5,
//   before: 'ى', after: 'ي', lossy: true }
```

In a browser, import `src/index.js` from the package as an ES module; it has no imports outside the package and fetches nothing.

## API

| Function | Returns |
|---|---|
| `normalize(text, policy = 'bayanat-norm-v1', { strict })` | the normalised string |
| `normalizeDetailed(text, policy, { strict })` | the detailed result: the same object as Python's `Result.to_dict()` (`text_norm`, `offset_map`, `changes`, `lossy_flags`, `flags`, `diacritization_ratio`, `rejected_spans`, `stats`, `policy_id`, `policy_hash`, `lib_version`, `unicode_version`, `original_hash`, `text_diac`) |
| `diffPolicies(text, a, b)` | both outputs, the rules only one policy applies, and the input regions where they differ |
| `loadPolicy(idOrObject)`, `listPolicies()`, `policyHash(policy)`, `canonicalJson(value)` | policy objects and their identity |
| `normalizeBytes(uint8array, ...)`, `normalizeRequest(request)`, `parseRecord(line, field)` | strict UTF-8 decoding and the input contract (10 MiB per text, 10,000 texts per request) |
| `normalizeForm(text, 'NFC' \| 'NFD' \| 'NFKC' \| 'NFKD')` | Unicode normalisation with the pinned tables |
| `loadPolicyFile(path)` from `@bayanat-labs/arabic-normalize/node` | a policy read from a JSON file (Node only) |

Offsets are code-point indices into the input, as in Python (not UTF-16 code units): use `[...text]` to index the input the same way. Errors are `InputRejected` or `PolicyError` with a machine-readable `reason`, the same reasons as in Python. Policy files are also exported as `@bayanat-labs/arabic-normalize/policies/<id>.json`.

| Policy | SHA-256 |
|---|---|
| `bayanat-norm-v1` | `ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321` |
| `asr-eval-v1` | `5d866146536a23b90c0882044dae5f55f2484f0635e206828246eabeb69668de` |
| `raw-safe-v1` | `57c3d9f03fb9b6854f2527cd1e8a47cadc266f47f02dda94652306dacea03bb5` |

What each policy does is in the policy cards of the main repository (`docs/policies/`, English and Arabic) and in `docs/SPEC.md`.

## Known differences from the Python package

- A JavaScript string cannot hold a high surrogate directly followed by a low surrogate as two separate code points: they always form one code point. A Python string built with `chr()` can keep them apart; Python then rejects both as lone surrogates. JSON input behaves the same in both languages.
- `loadPolicy` takes a built-in id, a policy object or a `Policy`, not a file path; use `loadPolicyFile` from `/node` for files.
- In a policy object read with `JSON.parse`, `1.0` and `1` are the same number, so a `version` of `1.0` is accepted (Python rejects the float).

## Development

```bash
node scripts/build.mjs               # regenerate src/generated/* and policies/ from the Python package files
node --test test/*.test.mjs          # conformance (fixtures and Python reference), rejected inputs, UCD tables,
                                     # NormalizationTest.txt, policies, SHA-256, properties
python3 -I scripts/make_reference.py # regenerate test/reference/python-reference.json from the Python engine
node scripts/conformance_counts.mjs  # write conformance.json (counts used in the main README and CLAIMS.md)
python3 -I scripts/parity_make.py --n 20000 --out /tmp/parity.jsonl.gz && node scripts/parity_check.mjs /tmp/parity.jsonl.gz
```

The parity run compares the full detailed result on seeded random strings (lone surrogates, noncharacters, emoji, presentation forms, any code point) and on 2,000-character synthetic paragraphs. The summary of the last run, with JavaScript throughput, is in `parity.json`.

## Licence and contact

Code: Apache-2.0 (`LICENSE`). Policy files: CC BY 4.0 (`LICENSE-data`). Generated Unicode tables: Unicode License V3 (`NOTICE-unicode.txt`). Questions, corrections and takedown requests: hello@bayanatlabs.com.

**Need production-grade, rights-cleared Arabic data with documented normalisation?** See [Bayanat Knowledge](https://www.bayanatlabs.com/products/knowledge).
