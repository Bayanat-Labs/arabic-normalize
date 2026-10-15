// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// The JavaScript tables decode to exactly the Python package's tables, and the span-tracking UAX #15
// implementation passes every line of the pinned Unicode 18.0.0 NormalizationTest.txt.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { gunzipSync } from 'node:zlib';
import { decodedTables, normalizeForm, toCodePoints, fromCodePoints } from '../src/ucd.js';
import { ROOT } from './helpers.mjs';

const sortRows = (rows) => [...rows].sort((a, b) => a[0] - b[0] || (a[1] ?? 0) - (b[1] ?? 0));

test('decoded tables equal src/arabic_normalize/tables/ucd_tables.json (names omitted)', () => {
  const py = JSON.parse(readFileSync(join(ROOT, 'src', 'arabic_normalize', 'tables', 'ucd_tables.json'), 'utf8'));
  const js = decodedTables();
  const keys = Object.keys(py).filter((k) => k !== 'names').sort();
  assert.deepEqual(Object.keys(js).sort(), keys);
  for (const k of keys) {
    if (['unicode_version', 'source', 'license', 'source_sha256'].includes(k)) {
      assert.deepEqual(js[k], py[k], k);
    } else if (k === 'joining_type') {
      assert.deepEqual(Object.keys(js[k]).sort(), Object.keys(py[k]).sort());
      for (const t of Object.keys(py[k])) assert.deepEqual(sortRows(js[k][t]), sortRows(py[k][t]), `${k}.${t}`);
    } else if (k === 'compat_decomposable') {
      assert.deepEqual(js[k], [...py[k]].sort((a, b) => a - b), k);
    } else {
      assert.deepEqual(sortRows(js[k]), sortRows(py[k]), k);
    }
  }
});

test('code point conversion keeps lone surrogates and pairs proper ones', () => {
  assert.deepEqual(toCodePoints('a😀b\uD800'), [0x61, 0x1F600, 0x62, 0xD800]);
  assert.equal(fromCodePoints([0x61, 0x1F600, 0xDFFF]), 'a😀\uDFFF');
});

const NT = join(ROOT, 'ucd', '18.0.0', 'NormalizationTest.txt.gz');

function parseNT() {
  const rows = [];
  for (const line of gunzipSync(readFileSync(NT)).toString('utf8').split('\n')) {
    const body = line.split('#')[0].trim();
    if (!body || body.startsWith('@')) continue;
    const cols = body.split(';').slice(0, 5).map((c) => fromCodePoints(c.trim().split(/\s+/).map((h) => parseInt(h, 16))));
    rows.push(cols);
  }
  return rows;
}

test('NormalizationTest.txt (UCD 18.0.0): every line, all four forms', () => {
  const rows = parseNT();
  assert.ok(rows.length > 19000, `only ${rows.length} rows`);
  let checked = 0;
  for (const [c1, c2, c3, c4, c5] of rows) {
    // UAX #15 conformance invariants
    for (const x of [c1, c2, c3]) assert.equal(normalizeForm(x, 'NFC'), c2);
    for (const x of [c4, c5]) assert.equal(normalizeForm(x, 'NFC'), c4);
    for (const x of [c1, c2, c3]) assert.equal(normalizeForm(x, 'NFD'), c3);
    for (const x of [c4, c5]) assert.equal(normalizeForm(x, 'NFD'), c5);
    for (const x of [c1, c2, c3, c4, c5]) assert.equal(normalizeForm(x, 'NFKC'), c4);
    for (const x of [c1, c2, c3, c4, c5]) assert.equal(normalizeForm(x, 'NFKD'), c5);
    checked += 1;
  }
  assert.equal(checked, rows.length);
});

test('information: how far the engine\'s own String.prototype.normalize is from UCD 18.0.0', (t) => {
  const rows = parseNT();
  let differ = 0;
  for (const [c1, c2] of rows) if (c1.normalize('NFC') !== c2) differ += 1;
  t.diagnostic(`node ${process.versions.node}, ICU ${process.versions.icu}, ICU Unicode ${process.versions.unicode}: `
    + `${differ} of ${rows.length} NormalizationTest lines differ under native NFC (the port never uses it)`);
});
