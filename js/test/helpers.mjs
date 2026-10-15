// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const JS = dirname(dirname(fileURLToPath(import.meta.url)));
export const ROOT = dirname(JS);
export const FIXTURES = join(ROOT, 'tests', 'fixtures');

export function loadJsonl(path) {
  return readFileSync(path, 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
}

export function fixtures(split) {
  return loadJsonl(join(FIXTURES, split, `${split}.jsonl`));
}

export function reference() {
  return JSON.parse(readFileSync(join(JS, 'test', 'reference', 'python-reference.json'), 'utf8'));
}

/** Keys in insertion order at every level, so two objects can be compared for identical JSON layout. */
export function keyOrder(v) {
  if (Array.isArray(v)) return v.map(keyOrder);
  if (v && typeof v === 'object') return Object.keys(v).map((k) => [k, keyOrder(v[k])]);
  return null;
}
