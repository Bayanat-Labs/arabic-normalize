#!/usr/bin/env node
// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// JavaScript side of the cross-language parity run: reads the gzipped JSONL written by parity_make.py,
// recomputes every record with this package and compares text_norm (plain and detailed), the offset map,
// the change log, flags, ratio, rejected spans, statistics and hashes. Also measures JavaScript throughput
// on the synthetic paragraphs.
//
// Usage: node scripts/parity_check.mjs PARITY.jsonl.gz [--summary OUT.json]
import { createReadStream, writeFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { createGunzip } from 'node:zlib';
import { performance } from 'node:perf_hooks';
import { loadPolicy, normalize, normalizeDetailed, sha256Hex } from '../src/index.js';
import { LIB_VERSION } from '../src/generated/version.js';
import { toCodePoints } from '../src/ucd.js';
import { encodeCodePoints } from '../src/utf8.js';

const args = process.argv.slice(2);
const input = args[0];
const summaryPath = args.includes('--summary') ? args[args.indexOf('--summary') + 1] : null;

const sha = (s) => sha256Hex(encodeCodePoints(toCodePoints(s)));
const hexcps = (s) => toCodePoints(s).map((c) => c.toString(16).toUpperCase()).join(' ');

function digest(res) {
  return {
    text_norm_sha256: sha(res.text_norm),
    offsets_sha256: sha(res.offset_map.map(([lo, hi]) => `${lo},${hi}`).join('\n')),
    changes_sha256: sha(res.changes.map((c) => [c.stage, c.rule_id, String(c.src_start), String(c.src_end),
      hexcps(c.before), hexcps(c.after), c.lossy ? '1' : '0'].join('\t')).join('\n')),
    n_changes: res.changes.length,
    lossy_flags: res.lossy_flags,
    flags: res.flags,
    ratio: res.diacritization_ratio,
    rejected_spans: res.rejected_spans,
    stats: res.stats,
    original_hash: res.original_hash,
    text_diac_sha256: res.text_diac === null ? null : sha(res.text_diac),
    policy_hash: res.policy_hash,
  };
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

const policies = new Map();
const counts = {};
const mismatches = [];
const paragraphs = [];
let meta = null;

const rl = createInterface({ input: createReadStream(input).pipe(createGunzip()), crlfDelay: Infinity });
for await (const line of rl) {
  if (!line) continue;
  const rec = JSON.parse(line);
  if (rec.kind === 'meta') {
    meta = rec;
    if (rec.lib_version !== LIB_VERSION) throw new Error(`Python ${rec.lib_version} vs JS ${LIB_VERSION}`);
    for (const d of rec.custom_policies) policies.set(d.policy_id, loadPolicy(d));
    continue;
  }
  if (!policies.has(rec.policy_id)) policies.set(rec.policy_id, loadPolicy(rec.policy_id));
  const p = policies.get(rec.policy_id);
  const key = `${rec.kind}/${rec.kind === 'paragraph' ? `${rec.set}/` : ''}${rec.policy_id}`;
  const c = counts[key] || (counts[key] = { records: 0, identical: 0 });
  c.records += 1;
  const plain = normalize(rec.input, p);
  const d = digest(normalizeDetailed(rec.input, p));
  const py = rec.detailed;
  const problems = [];
  if (plain !== rec.plain) problems.push('plain text_norm');
  for (const k of Object.keys(py)) {
    if (k === 'ratio') {
      if (Number(py.ratio) !== d.ratio) problems.push('diacritization_ratio');
    } else if (!same(py[k], d[k])) {
      problems.push(k);
    }
  }
  if (problems.length === 0) c.identical += 1;
  else if (mismatches.length < 20) mismatches.push({ key, input: rec.input, problems });
  if (rec.kind === 'paragraph') paragraphs.push(rec);
}

// Throughput on the synthetic paragraphs (one core; UTF-8 bytes in / seconds).
const throughput = {};
for (const set of ['undiacritised', 'diacritised']) {
  for (const pid of ['bayanat-norm-v1', 'asr-eval-v1', 'raw-safe-v1']) {
    const recs = paragraphs.filter((r) => r.set === set && r.policy_id === pid).map((r) => r.input);
    if (!recs.length) continue;
    const bytes = recs.reduce((a, s) => a + Buffer.byteLength(s, 'utf8'), 0);
    for (const r of recs.slice(0, 50)) normalize(r, pid); // warm-up
    let t = performance.now();
    for (const r of recs) normalize(r, pid);
    const plain = bytes / ((performance.now() - t) / 1000) / 1e6;
    const quarter = recs.slice(0, Math.floor(recs.length / 4));
    const qbytes = quarter.reduce((a, s) => a + Buffer.byteLength(s, 'utf8'), 0);
    t = performance.now();
    for (const r of quarter) normalizeDetailed(r, pid);
    const det = qbytes / ((performance.now() - t) / 1000) / 1e6;
    throughput[`${set}/${pid}`] = { bytes, normalize_MBps: Math.round(plain * 100) / 100, detailed_MBps: Math.round(det * 100) / 100 };
  }
}

const total = Object.values(counts).reduce((a, c) => a + c.records, 0);
const identical = Object.values(counts).reduce((a, c) => a + c.identical, 0);
const summary = {
  generated_by: 'js/scripts/parity_check.mjs',
  date: new Date().toISOString().slice(0, 10),
  lib_version: LIB_VERSION,
  python: meta && meta.python,
  node: process.versions.node,
  n_per_policy_random: meta && meta.n_per_policy,
  seed: meta && meta.seed,
  records: total,
  identical,
  by_group: counts,
  mismatches,
  throughput_js: { machine: 'one core', results: throughput },
};
console.log(JSON.stringify({ records: total, identical, mismatches: mismatches.length }, null, 1));
console.log(JSON.stringify(throughput, null, 1));
if (summaryPath) writeFileSync(summaryPath, `${JSON.stringify(summary, null, 1)}\n`);
process.exit(identical === total ? 0 : 1);
