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
- QA records: agreement tables against CAMeL Tools, tnkeeh, Whisper's basic normaliser and PyArabic on the fixtures (`docs/compat/`, tables only), a statistics-only stress run on one Arabic Wikipedia dump part (`docs/stress/`), and an independent review of every lossy fixture and lossy context class (`docs/LOSSY_REVIEW.md`). Two limitations found by the review (Uthmani spelling; ى in other Arabic-script languages) were added to the bayanat-norm-v1 and asr-eval-v1 cards. No policy or engine behaviour changed.
- JavaScript port `js/` (npm `@bayanat-labs/arabic-normalize`, ES module, no runtime dependencies): same policies and pinned UCD 18.0.0 tables, generated from the Python package files by `js/scripts/build.mjs`; `normalize`, `normalizeDetailed`, `diffPolicies`, `normalizeBytes`, `normalizeRequest`, policy loading and hashing. Cross-implementation conformance against the Python engine (`js/test/reference/python-reference.json`, `js/conformance.json`) and a random-string and paragraph parity run (`js/parity.json`).

### Changed after the independent review (15 Oct 2026, still unreleased)
- CLI: the CSV output of `arnorm normalize --csv` adds `lib_version` and `unicode_version` columns, like the JSONL output.
- JavaScript: Node 20 or later (Node 18 has been end of life since April 2025 and was never tested); CI runs the JavaScript tests on Node 20, 22 and 24.
- Web page: the processing Web Worker is started from a `blob:` URL so that the page's Content-Security-Policy (`connect-src 'none'`) applies inside it too; `web/privacy_check.py` (Playwright, Chromium) tests this and runs in CI. The bundled font is now IBM's unmodified IBM Plex Sans Arabic 1.005 (Regular and SemiBold) instead of Google Fonts subsets, with provenance rows and a NOTICE entry.
- Reproducibility: the stress and oracle-comparison scripts are now in the repository (`scripts/stress/`, `scripts/compat/` with the CAMeL Tools, tnkeeh and Whisper harnesses; the PyArabic harness stays outside because PyArabic is GPL). Re-running them reproduced `docs/stress/stats.json` and `docs/compat/agreement.json` exactly. CLAIMS.md lists the scripts and the SHA-256 of each QA record.
- Stress: a statistics-only run on the FLEURS ar_eg transcripts (`docs/stress/fleurs.md`). The Tanzil run waits for the text file (its download page asks users to accept terms).
- Fixtures: 16 blind acceptance-b candidates written by a second session without engine access (`tests/fixtures/candidates/`); 16 of 16 pass in Python and JavaScript. They are not part of the 80 pilot fixtures until the linguist review. The fixture README's dev family count is corrected to 17.
- Arabic text: an independent AI review by an agent session separate from the authors, of the Arabic policy cards, the web page's Arabic interface strings and the Arabic fixture rationales (one wording fix, dev-026; no expected value changed). Recorded as `native_review: independent_ai_review`; a human native review is still recommended.
