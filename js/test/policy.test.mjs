// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import {
  LIB_VERSION, Policy, PolicyError, canonicalJson, listPolicies, loadPolicy, normalize, policyHash, sha256Hex,
} from '../src/index.js';
import { loadPolicyFile } from '../src/node.js';
import { POLICY_FILE_SHA256 } from '../src/generated/policies.js';
import { JS, ROOT } from './helpers.mjs';

const PY_POLICIES = join(ROOT, 'src', 'arabic_normalize', 'policies');
const EXPECTED = {
  'asr-eval-v1': '5d866146536a23b90c0882044dae5f55f2484f0635e206828246eabeb69668de',
  'bayanat-norm-v1': 'ebdb82000d0762a65120ffa9311bc6f01b481b19d4348ea5bedb3ab23d759321',
  'raw-safe-v1': '57c3d9f03fb9b6854f2527cd1e8a47cadc266f47f02dda94652306dacea03bb5',
};

test('generated files are up to date with the Python package (build --check)', () => {
  execFileSync(process.execPath, [join(JS, 'scripts', 'build.mjs'), '--check'], { stdio: 'pipe' });
});

test('built-in policies are the Python package files, byte for byte', () => {
  const files = readdirSync(PY_POLICIES).filter((f) => f.endsWith('.json'));
  for (const f of files) {
    const a = readFileSync(join(PY_POLICIES, f));
    assert.ok(a.equals(readFileSync(join(JS, 'policies', f))), f);
  }
  assert.deepEqual(listPolicies(), files.filter((f) => f !== 'schema.json').map((f) => f.slice(0, -5)).sort());
  for (const pid of listPolicies()) {
    const bytes = readFileSync(join(PY_POLICIES, `${pid}.json`));
    assert.equal(POLICY_FILE_SHA256[pid], createHash('sha256').update(bytes).digest('hex'));
    assert.equal(loadPolicyFile(join(JS, 'policies', `${pid}.json`)).policy_hash, EXPECTED[pid]);
  }
});

test('published policy hashes are stable', () => {
  for (const [pid, h] of Object.entries(EXPECTED)) {
    assert.equal(loadPolicy(pid).policy_hash, h);
    assert.equal(policyHash(loadPolicy(pid).data), h);
    assert.equal(sha256Hex(new TextEncoder().encode(loadPolicy(pid).canonical())), h);
  }
});

test('meta does not change the hash; any stage change does', () => {
  const data = loadPolicy('bayanat-norm-v1').data;
  data.meta.title_en = 'something else';
  assert.equal(policyHash(data), EXPECTED['bayanat-norm-v1']);
  data.stages.tatweel = 'keep';
  data.policy_id = 'custom-test';
  assert.notEqual(policyHash(data), EXPECTED['bayanat-norm-v1']);
  assert.equal(new Policy(data).policy_hash, policyHash(data));
});

test('canonical JSON sorts keys by code point and keeps non-ASCII characters', () => {
  assert.equal(canonicalJson({ b: 1, a: [true, null, 'ي'], 'é': { z: 0, y: 'x' } }),
    '{"a":[true,null,"ي"],"b":1,"é":{"y":"x","z":0}}');
});

test('policies are immutable and package version matches the Python package', () => {
  const p = loadPolicy('raw-safe-v1');
  assert.throws(() => { p.policy_id = 'x'; });
  assert.throws(() => { p.stages.tatweel = 'strip'; });
  const pkg = JSON.parse(readFileSync(join(JS, 'package.json'), 'utf8'));
  assert.equal(pkg.version, LIB_VERSION);
  assert.equal(pkg.name, '@bayanat-labs/arabic-normalize');
});

test('policy errors carry the Python reasons', () => {
  const reason = (fn) => { try { fn(); } catch (e) { assert.ok(e instanceof PolicyError); return e.reason; } return null; };
  const base = () => loadPolicy('bayanat-norm-v1').data;
  assert.equal(reason(() => loadPolicy('nope-v1')), 'unknown_policy');
  assert.equal(reason(() => loadPolicy(42)), 'invalid_policy');
  assert.equal(reason(() => loadPolicy({ ...base(), policy_id: 'Bad_ID' })), 'invalid_policy_id');
  assert.equal(reason(() => loadPolicy({ ...base(), version: 0 })), 'invalid_member');
  assert.equal(reason(() => loadPolicy({ ...base(), spec: 'x' })), 'unsupported_spec');
  assert.equal(reason(() => { const d = base(); delete d.stages.digits; return loadPolicy(d); }), 'missing_stage');
  assert.equal(reason(() => { const d = base(); delete d.version; return loadPolicy(d); }), 'missing_member');
  assert.equal(reason(() => loadPolicy({ ...base(), meta: { colour: 'x' } })), 'unknown_member');
  assert.equal(reason(() => loadPolicy({ ...base(), stages: { ...base().stages, $ref: 'x' } })), 'remote_ref_not_allowed');
  assert.equal(normalize('ـا', { ...base(), policy_id: 'custom-test' }), 'ا');
});
