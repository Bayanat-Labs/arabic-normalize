// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Blind acceptance-b candidates (16 cases written separately, without engine access).
// Not part of the 80 pilot fixtures; see tests/fixtures/candidates/README.md.
import assert from 'node:assert/strict';
import { join } from 'node:path';
import { test } from 'node:test';
import { normalize, normalizeDetailed, ruleIds } from '../src/index.js';
import { FIXTURES, loadJsonl } from './helpers.mjs';

const CANDIDATES = loadJsonl(join(FIXTURES, 'candidates', 'acceptance-b.jsonl'));

test('candidate count', () => {
  assert.equal(CANDIDATES.length, 16);
});

for (const fx of CANDIDATES) {
  test(`candidate ${fx.fixture_id} (${fx.policy_id}) meets its expectations`, () => {
    const res = normalizeDetailed(fx.input, fx.policy_id);
    assert.equal(res.text_norm, fx.expected_output);
    assert.equal(normalize(fx.input, fx.policy_id), res.text_norm);
    assert.deepEqual(ruleIds(res), fx.expected_rules);
    assert.deepEqual(res.lossy_flags, fx.expected_lossy_flags);
    assert.deepEqual(res.flags, fx.expected_flags);
    assert.deepEqual(res.rejected_spans, fx.expected_rejected_spans);
    if (fx.expected_offset_map !== null) assert.deepEqual(res.offset_map, fx.expected_offset_map);
    if (fx.expected_diacritization_ratio !== null) {
      assert.ok(Math.abs(res.diacritization_ratio - fx.expected_diacritization_ratio) <= 1e-12);
    }
  });
}
