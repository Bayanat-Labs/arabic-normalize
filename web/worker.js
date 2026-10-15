// Copyright 2026 Bayanat Labs
// SPDX-License-Identifier: Apache-2.0
//
// Runs the normaliser off the main thread. Nothing leaves the browser: the page forbids network
// connections (Content-Security-Policy connect-src 'none') and this worker keeps no state between messages.
import { compute } from './compute.js';

self.onmessage = (event) => {
  self.postMessage({ id: event.data.id, ...compute(event.data) });
};
