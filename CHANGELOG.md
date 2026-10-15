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
