# arabic-normalize conformance fixtures (pilot)

Licence: CC BY 4.0, Bayanat Labs. Every record is labelled `synthetic/illustrative, authored by Bayanat Labs`: the text was written for these fixtures, contains no corpus text and no personal data. Common first names (for example مصطفى) appear only as spelling examples.

| Split | File | Records | Purpose |
|---|---|---|---|
| dev | dev/dev.jsonl | 64 | Development cases across 17 families |
| acceptance | acceptance/acceptance.jsonl | 16 | Held-back cases with code-point families and rule combinations that do not occur in dev |
| rejected | rejected/rejected.jsonl | 20 | Inputs and policies that must be rejected, with the expected reason |

Fields of a dev or acceptance record (schema: `schemas/fixture.schema.json`): `fixture_id`, `split`, `family`, `policy_id`, `input` and `input_escaped` (the same text as `\u` escapes), `expected_output`, `expected_rules` (sorted unique rule ids in the change log), `expected_lossy_flags`, `expected_flags`, `expected_offset_map` (null when not asserted), `expected_rejected_spans`, `expected_diacritization_ratio` (null when not asserted), `rationale_en` (the note), `rationale_ar`, `author`, `created`, `label`, `synthetic`, `reviewed_by`, `review_verdict`.

The records are generated from the hand-written definitions in `scripts/author_fixtures.py`, which never calls the engine. `PROVENANCE.jsonl` holds one row per fixture with its SHA-256. Native review status: see `REVIEW.md`. A further 16 blind acceptance cases written by a second session are kept apart as candidates in `candidates/` (see `candidates/README.md`).
