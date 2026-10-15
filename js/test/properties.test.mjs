// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Properties on seeded random Arabic-heavy strings (same pools as tests/test_properties.py).
// ARNORM_PROPERTY_N sets the number of strings per policy (default 2,000).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { loadPolicy, normalize, normalizeDetailed } from '../src/index.js';
import { normalizeFormCps, toCodePoints, fromCodePoints } from '../src/ucd.js';
import { randomText, mulberry32 } from './random-text.mjs';

const N = Number(process.env.ARNORM_PROPERTY_N || 2000);

for (const pid of ['bayanat-norm-v1', 'asr-eval-v1', 'raw-safe-v1']) {
  test(`properties hold for ${pid} on ${N} random strings`, () => {
    const policy = loadPolicy(pid);
    const rng = mulberry32(20261015 + pid.length);
    for (let k = 0; k < N; k++) {
      const s = randomText(rng);
      const res = normalizeDetailed(s, policy);
      const out = res.text_norm;
      assert.equal(normalize(s, policy), out, 'plain and detailed modes agree');
      if (policy.idempotent) assert.equal(normalize(out, policy), out, 'idempotent');
      const oc = toCodePoints(out);
      assert.equal(fromCodePoints(normalizeFormCps(oc, 'NFC')), out, 'output is NFC');
      assert.equal(res.offset_map.length, oc.length);
      const n = toCodePoints(s).length;
      for (const [lo, hi] of res.offset_map) assert.ok(lo >= 0 && lo < hi && hi <= n);
    }
  });
}
