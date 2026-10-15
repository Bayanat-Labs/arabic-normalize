#!/usr/bin/env node
// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Computes the JavaScript conformance counts that scripts/make_docs.py puts into README.md and CLAIMS.md:
// fixtures passing every assertion in JavaScript (per split and per policy), rejected inputs rejected with
// the documented reason, and reference cases identical to the Python engine. Writes js/conformance.json.
//
// Usage: node scripts/conformance_counts.mjs [--check]
import { isDeepStrictEqual } from 'node:util';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  ArabicNormalizeError, LIB_VERSION, diffPolicies, loadPolicy, normalize, normalizeBytes, normalizeDetailed,
  normalizeRequest, parseRecord, ruleIds,
} from '../src/index.js';
import { JS, fixtures, reference } from '../test/helpers.mjs';

const CHECK = process.argv.includes('--check');
const same = (a, b) => isDeepStrictEqual(a, b);

function passes(fx) {
  const r = normalizeDetailed(fx.input, fx.policy_id);
  return r.text_norm === fx.expected_output
    && normalize(fx.input, fx.policy_id) === r.text_norm
    && same(ruleIds(r), fx.expected_rules)
    && same(r.lossy_flags, fx.expected_lossy_flags)
    && same(r.flags, fx.expected_flags)
    && same(r.rejected_spans, fx.expected_rejected_spans)
    && (fx.expected_offset_map === null || same(r.offset_map, fx.expected_offset_map))
    && (fx.expected_diacritization_ratio === null
      || Math.abs(r.diacritization_ratio - fx.expected_diacritization_ratio) <= 1e-12);
}

function rejectedOk(fx) {
  const hex = (h) => Uint8Array.from(h.match(/../g).map((x) => parseInt(x, 16)));
  const patched = () => {
    const d = loadPolicy(fx.base).data;
    for (const [k, v] of Object.entries(fx.patch)) {
      if (k.startsWith('stages.')) d.stages[k.split('.', 2)[1]] = v;
      else d[k] = v;
    }
    return d;
  };
  try {
    switch (fx.kind) {
      case 'bytes': normalizeBytes(hex(fx.input_hex)); break;
      case 'text_strict': normalize(fx.input, fx.policy_id, { strict: true }); break;
      case 'generated_text': normalizeRequest({ text: fx.generate.repeat.repeat(fx.generate.count), policy: fx.policy_id }); break;
      case 'generated_records': normalizeRequest({ texts: Array(fx.generate.count).fill(fx.generate.text), policy: fx.policy_id }); break;
      case 'policy_id': normalize('نص', fx.policy_id); break;
      case 'policy': normalizeRequest({ text: 'نص', policy: fx.policy }); break;
      case 'policy_patch': normalize('نص', patched()); break;
      case 'jsonl_line': normalize(parseRecord(fx.line, fx.field)[1], fx.policy_id); break;
      default: return false;
    }
  } catch (e) {
    return e instanceof ArabicNormalizeError && e.reason === fx.expected_reason;
  }
  return false;
}

const bySplit = {};
const byPolicy = {};
for (const fx of [...fixtures('dev'), ...fixtures('acceptance')]) {
  const ok = passes(fx) ? 1 : 0;
  const s = bySplit[fx.split] || (bySplit[fx.split] = [0, 0]);
  s[0] += 1;
  s[1] += ok;
  const p = byPolicy[fx.policy_id] || (byPolicy[fx.policy_id] = [0, 0]);
  p[0] += 1;
  p[1] += ok;
}
const rej = fixtures('rejected');
const rejOk = rej.filter(rejectedOk).length;

const REF = reference();
const pols = {};
for (const [pid, p] of Object.entries(REF.policies)) pols[pid] = p.builtin ? pid : loadPolicy(p.data);
let refSame = 0;
for (const c of REF.cases) {
  const r = normalizeDetailed(c.input, pols[c.policy_id]);
  if (same(r, c.detailed) && normalize(c.input, pols[c.policy_id]) === c.text_norm_plain) refSame += 1;
}
let diffSame = 0;
for (const d of REF.diffs) if (same(diffPolicies(d.input, d.policy_a, d.policy_b), d.result)) diffSame += 1;
let hashSame = 0;
for (const [pid, p] of Object.entries(REF.policies)) if (loadPolicy(pols[pid]).policy_hash === p.policy_hash) hashSame += 1;

const out = {
  generated_by: 'js/scripts/conformance_counts.mjs',
  package: '@bayanat-labs/arabic-normalize',
  lib_version: LIB_VERSION,
  by_split: Object.fromEntries(Object.keys(bySplit).sort().map((k) => [k, { fixtures: bySplit[k][0], passing_js: bySplit[k][1] }])),
  by_policy: Object.fromEntries(Object.keys(byPolicy).sort().map((k) => [k, { fixtures: byPolicy[k][0], passing_js: byPolicy[k][1] }])),
  rejected: { fixtures: rej.length, rejected_with_documented_reason: rejOk },
  python_reference: {
    file: 'js/test/reference/python-reference.json',
    policies: Object.keys(REF.policies).length,
    policy_hashes_identical: hashSame,
    cases: REF.cases.length,
    cases_identical: refSame,
    diffs: REF.diffs.length,
    diffs_identical: diffSame,
  },
};
const text = `${JSON.stringify(out, null, 2)}\n`;
const path = join(JS, 'conformance.json');
if (CHECK) {
  if (!existsSync(path) || readFileSync(path, 'utf8') !== text) {
    console.error('js/conformance.json is out of date (run node scripts/conformance_counts.mjs)');
    process.exit(1);
  }
  console.log('js/conformance.json is up to date');
} else {
  writeFileSync(path, text);
  console.log(text);
}
const allPass = Object.values(bySplit).every(([n, ok]) => n === ok) && rejOk === rej.length
  && refSame === REF.cases.length && diffSame === REF.diffs.length;
process.exit(allPass ? 0 : 1);
