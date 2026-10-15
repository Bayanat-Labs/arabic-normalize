// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// One normalisation request, shared by the Web Worker and the main-thread fallback.
// Input {text, policy, compare, full}; output {result, diff, compareSkipped, inMark, outMark} or {error}.
import { diffPolicies, normalizeDetailed } from './lib/index.js';

export const DISPLAY_LIMIT = 20000; // code points highlighted in the before/after view
const MAX_MAP = 50000; // offset-map entries returned for display (the download asks for the full result)
const MAX_CHANGES = 5000; // change-log rows returned for display
const MAX_COMPARE_LENGTH = 200000; // code points; longer texts are not compared

/**
 * Highlight data for the before/after view.
 * inMark[i] for the first DISPLAY_LIMIT input code points: bits 0-1 = 0 unchanged, 1 changed, 2 lossy;
 * bit 2 (value 4) = some output code point comes from this position (unset means removed).
 * outMark[j] for the first DISPLAY_LIMIT output code points: 0, 1 or 2 from the input positions it comes from.
 */
function marks(result, inputLength) {
  const chg = new Uint8Array(inputLength);
  for (const c of result.changes) {
    const v = c.lossy ? 2 : 1;
    for (let i = c.src_start; i < c.src_end; i++) if (chg[i] < v) chg[i] = v;
  }
  const covered = new Uint8Array(inputLength);
  const outMark = new Uint8Array(Math.min(result.offset_map.length, DISPLAY_LIMIT));
  result.offset_map.forEach(([lo, hi], j) => {
    let m = 0;
    for (let i = lo; i < hi; i++) {
      covered[i] = 1;
      if (chg[i] > m) m = chg[i];
    }
    if (j < outMark.length) outMark[j] = m;
  });
  const inMark = new Uint8Array(Math.min(inputLength, DISPLAY_LIMIT));
  for (let i = 0; i < inMark.length; i++) inMark[i] = chg[i] | (covered[i] ? 4 : 0);
  return { inMark, outMark };
}

export function compute({ text, policy, compare, full }) {
  try {
    const result = normalizeDetailed(text, policy);
    if (full) return { result, diff: null };
    let inputLength = 0;
    for (const ch of text) if (ch) inputLength += 1; // code points (a lone surrogate counts as one)
    const { inMark, outMark } = marks(result, inputLength);
    let lossyTotal = 0;
    for (const c of result.changes) if (c.lossy) lossyTotal += 1;
    const slim = {
      ...result,
      changes: result.changes.slice(0, MAX_CHANGES),
      offset_map: result.offset_map.slice(0, MAX_MAP),
      changes_total: result.changes.length,
      lossy_total: lossyTotal,
      offset_map_total: result.offset_map.length,
      input_length: inputLength,
    };
    let diff = null;
    let compareSkipped = false;
    if (compare && compare !== policy) {
      if (inputLength <= MAX_COMPARE_LENGTH) diff = diffPolicies(text, policy, compare);
      else compareSkipped = true;
    }
    return { result: slim, diff, compareSkipped, inMark, outMark };
  } catch (e) {
    return { error: { reason: e && e.reason ? e.reason : 'error', message: String(e && e.message ? e.message : e) } };
  }
}
