// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Cross-implementation conformance: every dev and acceptance fixture gives the Python engine's exact output
// (text_norm, offset map, change log, lossy flags, flags, ratio, statistics, hashes) in JavaScript.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  LIB_VERSION, UNICODE_VERSION, diffPolicies, loadPolicy, normalize, normalizeDetailed, ruleIds,
} from '../src/index.js';
import { fixtures, keyOrder, reference } from './helpers.mjs';

const DEV = fixtures('dev');
const ACC = fixtures('acceptance');
const ALL = [...DEV, ...ACC];
const REF = reference();

test('fixture counts', () => {
  assert.equal(DEV.length, 64);
  assert.equal(ACC.length, 16);
  assert.equal(new Set(ALL.map((f) => f.fixture_id)).size, 80);
  assert.equal(REF.fixture_count, 80);
});

test('reference was made by the same library and Unicode version', () => {
  assert.equal(REF.lib_version, LIB_VERSION);
  assert.equal(REF.unicode_version, UNICODE_VERSION);
});

for (const fx of ALL) {
  test(`fixture ${fx.fixture_id} (${fx.policy_id}) meets its expectations`, () => {
    const res = normalizeDetailed(fx.input, fx.policy_id);
    assert.equal(res.text_norm, fx.expected_output);
    assert.equal(normalize(fx.input, fx.policy_id), res.text_norm, 'plain and detailed modes disagree');
    assert.deepEqual(ruleIds(res), fx.expected_rules);
    assert.deepEqual(res.lossy_flags, fx.expected_lossy_flags);
    assert.deepEqual(res.flags, fx.expected_flags);
    assert.deepEqual(res.rejected_spans, fx.expected_rejected_spans);
    if (fx.expected_offset_map !== null) assert.deepEqual(res.offset_map, fx.expected_offset_map);
    if (fx.expected_diacritization_ratio !== null) {
      assert.ok(Math.abs(res.diacritization_ratio - fx.expected_diacritization_ratio) <= 1e-12);
    }
    assert.equal(res.offset_map.length, [...res.text_norm].length);
  });
}

function customPolicies() {
  const out = {};
  for (const [pid, p] of Object.entries(REF.policies)) out[pid] = p.builtin ? pid : loadPolicy(p.data);
  return out;
}

test('policy hashes and canonical JSON match Python', () => {
  const pols = customPolicies();
  for (const [pid, p] of Object.entries(REF.policies)) {
    const js = loadPolicy(pols[pid]);
    assert.equal(js.policy_hash, p.policy_hash, pid);
    assert.equal(js.canonical(), p.canonical, pid);
  }
});

test('every reference case is identical to the Python engine', () => {
  const pols = customPolicies();
  let n = 0;
  for (const c of REF.cases) {
    const policy = pols[c.policy_id];
    const res = normalizeDetailed(c.input, policy);
    const label = `${c.fixture_id} / ${c.policy_id}`;
    assert.deepStrictEqual(res, c.detailed, label);
    assert.deepStrictEqual(keyOrder(res), keyOrder(c.detailed), `${label}: key order`);
    assert.equal(normalize(c.input, policy), c.text_norm_plain, `${label}: plain mode`);
    assert.deepEqual(ruleIds(res), c.rules, `${label}: rule ids`);
    n += 1;
  }
  assert.equal(n, 560);
});

test('diffPolicies is identical to Python diff_policies', () => {
  for (const d of REF.diffs) {
    const res = diffPolicies(d.input, d.policy_a, d.policy_b);
    assert.deepStrictEqual(res, d.result, d.fixture_id);
  }
});
