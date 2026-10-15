// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { test } from 'node:test';
import { sha256Hex } from '../src/sha256.js';
import { encodeCodePoints } from '../src/utf8.js';
import { normalizeDetailed } from '../src/index.js';

test('sha256Hex equals node:crypto for lengths 0..300 and a 1 MB buffer', () => {
  for (let n = 0; n <= 300; n++) {
    const b = randomBytes(n);
    assert.equal(sha256Hex(new Uint8Array(b)), createHash('sha256').update(b).digest('hex'), `length ${n}`);
  }
  const big = randomBytes(1 << 20);
  assert.equal(sha256Hex(new Uint8Array(big)), createHash('sha256').update(big).digest('hex'));
});

test('original_hash encodes lone surrogates like Python surrogatepass', () => {
  assert.deepEqual([...encodeCodePoints([0xD800])], [0xED, 0xA0, 0x80]);
  const r = normalizeDetailed('ن\uD800');
  const bytes = Buffer.from([0xD9, 0x86, 0xED, 0xA0, 0x80]);
  assert.equal(r.original_hash, createHash('sha256').update(bytes).digest('hex'));
});
