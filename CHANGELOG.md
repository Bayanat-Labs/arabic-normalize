# Changelog

All notable changes to arabic-normalize (Bayanat Labs). The library follows semantic versioning. Policies are versioned separately and never change once released: a new behaviour gets a new policy id.

## 0.1.0 (pilot, unreleased)

### Added
- Engine: pure Python, no runtime dependencies, stages and modes of `docs/SPEC.md` (spec `arabic-normalize-spec-1`), span-tracking UAX #15 normalisation generated from the pinned Unicode Character Database 18.0.0.
- Policies (policy id and SHA-256 of the canonical policy JSON without `meta`):
<!-- BEGIN:hashes -->
- `asr-eval-v1`: sha256 `5d866146536a23b90c0882044dae5f55f2484f0635e206828246eabeb69668de`
- `bayanat-norm-v1`: sha256 `ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321`
- `raw-safe-v1`: sha256 `57c3d9f03fb9b6854f2527cd1e8a47cadc266f47f02dda94652306dacea03bb5`
<!-- END:hashes -->
- API: `normalize`, `normalize_detailed` (offset map, change log, lossy flags, flags, diacritization ratio, rejected spans, statistics), `diff_policies`, `explain`, `normalize_bytes`, `normalize_request`, `load_policy`, `list_policies`, `policy_hash`.
- CLI `arnorm`: `normalize` (text, JSONL, CSV; streaming; `--detailed`, `--strict`, `--resume`, `--on-error`), `diff`, `explain`, `policy list|show|export|hash`, `version`.
- Conformance fixtures: 64 dev, 16 acceptance and 20 rejected-input cases (CC BY 4.0), JSON schemas for input, output, fixtures and policies.
- Documentation: SPEC, DECISIONS, policy cards in English and Arabic.
- QA records: agreement tables against CAMeL Tools, tnkeeh, Whisper's basic normaliser and PyArabic on the fixtures (`docs/compat/`, tables only), a statistics-only stress run on one Arabic Wikipedia dump part (`docs/stress/`), and a review of every lossy fixture and lossy context class (`docs/LOSSY_REVIEW.md`). Two limitations found by the review (Uthmani spelling; ى in other Arabic-script languages) were added to the bayanat-norm-v1 and asr-eval-v1 cards. No policy or engine behaviour changed.
- JavaScript port `js/` (package `@bayanat-labs/arabic-normalize`, ES module, no runtime dependencies): same policies and pinned UCD 18.0.0 tables, generated from the Python package files by `js/scripts/build.mjs`; `normalize`, `normalizeDetailed`, `diffPolicies`, `normalizeBytes`, `normalizeRequest`, policy loading and hashing. Cross-implementation conformance against the Python engine (`js/test/reference/python-reference.json`, `js/conformance.json`) and a random-string and paragraph parity run (`js/parity.json`).

### Changed after review (15 Oct 2026, still unreleased)
- CLI: the CSV output of `arnorm normalize --csv` adds `lib_version` and `unicode_version` columns, like the JSONL output.
- JavaScript: Node 20 or later (Node 18 has been end of life since April 2025 and was never tested); CI runs the JavaScript tests on Node 20, 22 and 24.
- Web page: the processing Web Worker is started from a `blob:` URL so that the page's Content-Security-Policy (`connect-src 'none'`) applies inside it too; `web/privacy_check.py` (Playwright, Chromium) tests this and runs in CI. The bundled font is now IBM's unmodified IBM Plex Sans Arabic 1.005 (Regular and SemiBold) instead of Google Fonts subsets, with provenance rows and a NOTICE entry.
- Reproducibility: the stress and oracle-comparison scripts are now in the repository (`scripts/stress/`, `scripts/compat/` with the CAMeL Tools, tnkeeh and Whisper harnesses; no PyArabic harness is included because PyArabic is GPL). Re-running them reproduced `docs/stress/stats.json` and `docs/compat/agreement.json` exactly. CLAIMS.md lists the scripts and the SHA-256 of each QA record.
- Stress: a statistics-only run on the FLEURS ar_eg transcripts (`docs/stress/fleurs.md`). An optional third stress corpus is not run yet.
- Fixtures: 16 blind acceptance-b candidates written separately, without engine access (`tests/fixtures/candidates/`); 16 of 16 pass in Python and JavaScript. They are not part of the 80 pilot fixtures until the linguist review. The fixture README's dev family count is corrected to 17.
- Arabic text: the Arabic policy cards, the web page's Arabic interface strings and the Arabic fixture rationales were checked again (one wording fix, dev-026; no expected value changed). The Arabic text has not yet been reviewed by a native Arabic writer; the English governs.
- Conformance dataset: `docs/dataset/croissant.json` keeps the Croissant metadata that Hugging Face generates for the published dataset (validated with mlcroissant 1.1.1; see `docs/dataset/README.md`). `scripts/build_conformance_dataset.py` adds it to the dataset as `croissant.json`, listed in `MANIFEST.json` and `SHA256SUMS`, and its new `--source-commit` option rebuilds a released version after commits that do not touch the dataset inputs. The fixtures and the other dataset files are unchanged.
- Install instructions (`README.md`, `js/README.md`): until the first PyPI and npm releases, they install from GitHub, pinned to commit `da128047f20b`: `pip install "git+https://github.com/Bayanat-Labs/arabic-normalize@da128047f20b802489adcd765c6e8c412ee44d48"`, and for JavaScript the `js/` folder of a clone checked out at that commit (`npm install ./arabic-normalize/js`).
- Public text: the contact and takedown address is hello@bayanatlabs.com everywhere (READMEs, npm package metadata, web page, Space and dataset cards). The policy `meta` descriptions of `bayanat-norm-v1` and `asr-eval-v1` now describe the policy only; `meta` is outside the policy hash, so every policy hash is unchanged. `docs/DECISIONS.md` gives each design choice with its reason only, and its sections are numbered 1 to 14. Claim IDs in CLAIMS.md are plain names. The English rationale of dev-021 is reworded (no input or expected value changed). The web page, the Space and the dataset card no longer link a tool page on bayanatlabs.com, which is not online yet. `docs/LOSSY_REVIEW.md` and the Arabic cards record `native_review: pending`.
- Stress scripts: `stress_run.py --delimited FILE` reads any delimited text file, one text per line, in place of an option for one named corpus.
- Oracle comparison: the PyArabic pipeline `strip_tashkeel` → `strip_tatweel` → `normalize_hamza` → `normalize_ligature` is named `pyarabic-hamza` (numbers unchanged).
- Records: `PROVENANCE.jsonl` drops the `licence_evidence_id` column (the licence URL and quote of every row are kept). `evidence/census_2026-10-15.json` keeps the User-Agent product token without the contact comment of that day, and no longer keeps the free-text descriptions of GitHub search results (the feature columns computed from them are kept).
- Conformance dataset: `docs/dataset/croissant.json` is removed until the Croissant metadata of the revised dataset card is fetched from the Hub (`docs/dataset/README.md`); the dataset card's changelog records the revision.
