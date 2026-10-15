// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Every value shown in README.md is what the code returns, and every count comes from conformance.json.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { loadPolicy, normalize, normalizeDetailed } from '../src/index.js';
import { JS } from './helpers.mjs';

const README = readFileSync(join(JS, 'README.md'), 'utf8');
const COUNTS = JSON.parse(readFileSync(join(JS, 'conformance.json'), 'utf8'));
const show = (v) => (typeof v === 'string' ? `'${v}'` : Array.isArray(v) ? `[${v.map(show).join(', ')}]` : String(v));

test('worked example in README.md matches the code', () => {
  const text = 'إِلَى المَدْرَسَةِ الجَدِيدَةِ ١٢٣';
  assert.ok(README.includes(`const text = '${text}';`));
  for (const [call, value] of [
    ['normalize(text);', normalize(text)],
    ["normalize(text, 'asr-eval-v1');", normalize(text, 'asr-eval-v1')],
    ["normalize(text, 'raw-safe-v1');", normalize(text, 'raw-safe-v1')],
  ]) {
    assert.match(README, new RegExp(`${call.replace(/[()'.]/g, '\\$&')}\\s+// ${show(value).replace(/[.]/g, '\\.')}`), call);
  }
  const r = normalizeDetailed(text);
  assert.ok(README.includes(`r.lossy_flags;                    // ${show(r.lossy_flags)}`));
  assert.ok(README.includes(`r.flags;                          // ${show(r.flags)}`));
  assert.ok(README.includes(`r.diacritization_ratio;           // ${r.diacritization_ratio}`));
  assert.ok(README.includes(`r.policy_hash;                    // '${r.policy_hash}'`));
  const c = r.changes.find((x) => x.rule_id === 'alef_maqsura.to_yeh');
  assert.ok(README.includes(`src_start: ${c.src_start}, src_end: ${c.src_end}`));
});

test('policy table and conformance counts in README.md come from the code and conformance.json', () => {
  for (const pid of ['bayanat-norm-v1', 'asr-eval-v1', 'raw-safe-v1']) {
    assert.ok(README.includes(`| \`${pid}\` | \`${loadPolicy(pid).policy_hash}\` |`), pid);
  }
  const ref = COUNTS.python_reference;
  const nFix = Object.values(COUNTS.by_split).reduce((a, v) => a + v.fixtures, 0);
  assert.ok(README.includes(`the ${nFix} fixtures under ${ref.policies} policies (${ref.cases} cases) and ${ref.diffs} policy comparisons are identical`));
  assert.equal(ref.cases_identical, ref.cases);
  assert.equal(ref.diffs_identical, ref.diffs);
});
