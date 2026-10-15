// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
// Type declarations for @bayanat-labs/arabic-normalize (ES module).

export type StageName =
  | 'reject_invalid' | 'strip_controls' | 'presentation_forms' | 'ligatures_honorific' | 'bidi_zw'
  | 'tatweel' | 'diacritics' | 'quranic_marks' | 'superscript_alef' | 'alef_variants' | 'alef_maqsura'
  | 'taa_marbuta' | 'hamza_carriers' | 'persian_urdu_letters' | 'digits' | 'punctuation' | 'whitespace'
  | 'latin_case';

export interface PolicyData {
  policy_id: string;
  version: number;
  spec: 'arabic-normalize-spec-1';
  unicode_version: string;
  unicode_form: 'NFC' | 'NFKC' | 'none';
  idempotent: boolean;
  stages: Record<StageName, string>;
  meta?: {
    title_en?: string; title_ar?: string; description_en?: string; license?: string;
    attribution?: string; created?: string; status?: string;
  };
}

/** A validated, immutable policy. `policy_hash` identifies its behaviour. */
export class Policy {
  constructor(data: PolicyData, builtin?: boolean);
  readonly policy_id: string;
  readonly policy_hash: string;
  readonly stages: Readonly<Record<StageName, string>>;
  readonly unicode_form: 'NFC' | 'NFKC' | 'none';
  readonly idempotent: boolean;
  readonly builtin: boolean;
  /** A deep copy of the full policy object (including meta). */
  readonly data: PolicyData;
  /** Pretty JSON of the full policy, stages in pipeline order. */
  toJSONString(indent?: number): string;
  /** The exact canonical JSON string that is hashed. */
  canonical(): string;
}

export type PolicyLike = string | PolicyData | Policy;

export interface Change {
  stage: string;
  rule_id: string;
  src_start: number;
  src_end: number;
  before: string;
  after: string;
  lossy: boolean;
}

export interface RejectedSpan {
  start: number;
  end: number;
  reason: 'lone_surrogate' | 'control' | 'noncharacter';
}

export interface InputClasses {
  arabic_letters: number;
  harakat: number;
  superscript_alef: number;
  taa_marbuta: number;
  alef_maqsura: number;
  presentation_forms: number;
  honorific_ligatures: number;
  rejected: number;
}

/** The detailed result; the same object as Result.to_dict() in Python (schemas/output.schema.json). */
export interface DetailedResult {
  original_hash: string;
  text_norm: string;
  text_diac: string | null;
  policy_id: string;
  policy_hash: string;
  lib_version: string;
  unicode_version: string;
  changes: Change[];
  /** For each output code point, [src_start, src_end] in the input, in code points. */
  offset_map: [number, number][];
  lossy_flags: string[];
  flags: string[];
  diacritization_ratio: number;
  stats: { rules: Record<string, number>; classes: InputClasses };
  rejected_spans: RejectedSpan[];
}

export interface PolicyDiff {
  policy_a: string; policy_hash_a: string; text_a: string;
  policy_b: string; policy_hash_b: string; text_b: string;
  identical: boolean;
  rules_only_a: string[]; rules_only_b: string[];
  lossy_flags_a: string[]; lossy_flags_b: string[];
  regions: { src_start: number; src_end: number; source: string; a: string; b: string }[];
}

export interface NormalizeOptions { strict?: boolean }

export const LIB_VERSION: string;
export const UNICODE_VERSION: string;
export const DEFAULT_POLICY: 'bayanat-norm-v1';
export const LOSSY_RULES: ReadonlySet<string>;
export const MAX_TEXT_BYTES: number;
export const MAX_RECORDS: number;
export const SPEC_ID: 'arabic-normalize-spec-1';
export const STAGE_ORDER: readonly StageName[];
export const STAGE_MODES: Readonly<Record<StageName, readonly string[]>>;

/** Normalise `text` with `policy` (default bayanat-norm-v1) and return the string. */
export function normalize(text: string, policy?: PolicyLike, options?: NormalizeOptions): string;
/** Normalise and return the offset map, change log, flags and statistics. */
export function normalizeDetailed(text: string, policy?: PolicyLike, options?: NormalizeOptions): DetailedResult;
export function normalizeBytes(bytes: Uint8Array, policy?: PolicyLike, options?: NormalizeOptions & { detailed?: false }): string;
export function normalizeBytes(bytes: Uint8Array, policy: PolicyLike | undefined, options: NormalizeOptions & { detailed: true }): DetailedResult;
export function normalizeRequest(request: {
  text?: string; texts?: string[]; policy?: string | PolicyData; detailed?: boolean; strict?: boolean;
}): (string | DetailedResult)[];
export function diffPolicies(text: string, policyA: PolicyLike, policyB: PolicyLike): PolicyDiff;
export function inputStats(text: string): [InputClasses, number];
export function textDiac(text: string): string | null;
export function ruleIds(result: DetailedResult): string[];
export function decodeUtf8(bytes: Uint8Array): string;
export function parseRecord(line: string, field?: string): [Record<string, unknown>, string];
/** Plain NFC, NFD, NFKC or NFKD with the pinned UCD 18.0.0 tables (never String.prototype.normalize). */
export function normalizeForm(text: string, form: 'NFC' | 'NFD' | 'NFKC' | 'NFKD'): string;

export function loadPolicy(policy: PolicyLike): Policy;
export function listPolicies(): string[];
export function policyHash(policy: PolicyData | Policy): string;
export function canonicalJson(value: unknown): string;
export function validatePolicy(value: unknown): void;
export function sha256Hex(bytes: Uint8Array): string;

export class ArabicNormalizeError extends Error {
  constructor(reason: string, detail?: string, span?: [number, number] | null);
  readonly reason: string;
  readonly detail: string;
  readonly span: [number, number] | null;
}
export class InputRejected extends ArabicNormalizeError {}
export class PolicyError extends ArabicNormalizeError {}
