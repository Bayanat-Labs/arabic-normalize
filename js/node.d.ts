// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
export * from './index.js';
import type { Policy } from './index.js';
/** Read a policy JSON file and return a validated Policy (Node only). */
export function loadPolicyFile(path: string): Policy;
