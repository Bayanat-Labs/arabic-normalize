// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Node-only helpers: load a policy from a JSON file (like passing a path to load_policy in Python).
import { readFileSync } from 'node:fs';
import { PolicyError } from './errors.js';
import { Policy } from './policy.js';

export * from './index.js';

/** Read a policy JSON file and return a validated Policy. Nothing is fetched from the network. */
export function loadPolicyFile(path) {
  let data;
  try {
    data = JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    if (e && e.code === 'ENOENT') throw new PolicyError('unknown_policy', `no policy file named '${path}'`);
    throw new PolicyError('invalid_json', `policy file ${path}: ${e.message}`);
  }
  return new Policy(data);
}
