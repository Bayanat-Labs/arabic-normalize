// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Every rejected-input fixture is rejected with its documented reason, as in tests/test_rejected.py.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  ArabicNormalizeError, loadPolicy, normalize, normalizeBytes, normalizeRequest, parseRecord,
} from '../src/index.js';
import { fixtures } from './helpers.mjs';

const REJ = fixtures('rejected');

function patched(base, patch) {
  const data = loadPolicy(base).data;
  for (const [key, value] of Object.entries(patch)) {
    if (key.startsWith('stages.')) data.stages[key.split('.', 2)[1]] = value;
    else data[key] = value;
  }
  return data;
}

function hexBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

function run(fx) {
  switch (fx.kind) {
    case 'bytes': return normalizeBytes(hexBytes(fx.input_hex));
    case 'text_strict': return normalize(fx.input, fx.policy_id, { strict: true });
    case 'generated_text': return normalizeRequest({ text: fx.generate.repeat.repeat(fx.generate.count), policy: fx.policy_id });
    case 'generated_records': return normalizeRequest({ texts: Array(fx.generate.count).fill(fx.generate.text), policy: fx.policy_id });
    case 'policy_id': return normalize('نص', fx.policy_id);
    case 'policy': return normalizeRequest({ text: 'نص', policy: fx.policy });
    case 'policy_patch': return normalize('نص', patched(fx.base, fx.patch));
    case 'jsonl_line': {
      const [, text] = parseRecord(fx.line, fx.field);
      return normalize(text, fx.policy_id);
    }
    default: throw new Error(`unknown fixture kind ${fx.kind}`);
  }
}

test('at least ten rejected examples', () => assert.ok(REJ.length >= 10));

for (const fx of REJ) {
  test(`rejected ${fx.fixture_id}: ${fx.expected_reason}`, () => {
    assert.throws(() => run(fx), (e) => e instanceof ArabicNormalizeError && e.reason === fx.expected_reason);
  });
}

test('invalid UTF-8 reports the same byte offsets and reasons as CPython', () => {
  // [hex, start, end, reason] as printed by CPython 3.12 bytes.decode('utf-8')
  const cases = [['d8a7ff', 2, 3, 'invalid start byte'], ['d8a7d8', 2, 3, 'unexpected end of data'],
    ['c0af', 0, 1, 'invalid start byte'], ['eda080', 0, 1, 'invalid continuation byte'],
    ['e180', 0, 2, 'unexpected end of data'], ['e18041', 0, 2, 'invalid continuation byte'],
    ['f4908080', 0, 1, 'invalid continuation byte'], ['41f0', 1, 2, 'unexpected end of data'],
    ['f0808080', 0, 1, 'invalid continuation byte'], ['e0a0', 0, 2, 'unexpected end of data'],
    ['edbfbf', 0, 1, 'invalid continuation byte'], ['f5', 0, 1, 'invalid start byte'], ['80', 0, 1, 'invalid start byte']];
  for (const [hex, start, end, reason] of cases) {
    assert.throws(() => normalizeBytes(hexBytes(hex)), (e) => e.reason === 'invalid_utf8'
      && e.span[0] === start && e.span[1] === end && e.detail === `byte offset ${start}: ${reason}`, hex);
  }
  assert.equal(normalizeBytes(hexBytes('efbbbfd8a7')), 'ا', 'a BOM is decoded, then removed by strip_controls');
});

test('strict mode names the first rejected code point', () => {
  assert.throws(() => normalize('نص\u0007', 'bayanat-norm-v1', { strict: true }),
    (e) => e.reason === 'control' && e.detail === 'U+0007 at index 2' && e.span[0] === 2);
});
