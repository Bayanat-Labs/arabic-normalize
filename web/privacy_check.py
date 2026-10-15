#!/usr/bin/env python3
# Copyright 2026 Bayanat Labs
# SPDX-License-Identifier: Apache-2.0
"""Privacy check of the built web page (Hugging Face Space) in headless Chromium with Playwright.

Usage:
  node web/build.mjs --out DIR
  python web/privacy_check.py DIR [--json OUT.json]

The script serves DIR on 127.0.0.1 (no Content-Security-Policy header, as on Hugging Face static hosting),
opens the page and checks:
  1. the worked example is normalised and the processing runs in a Web Worker started from a blob: URL;
  2. fetch() and XMLHttpRequest fail inside that worker (the page's CSP, connect-src 'none', applies there),
     and fetch() fails in the page itself, while the same URL is reachable from outside the page;
  3. after load, typing a marker text causes no network request and nothing with the marker is written to
     localStorage, sessionStorage, IndexedDB or cookies.
Exit code 0 when every check passes. Needs `pip install playwright` and `python -m playwright install chromium`.
"""
import argparse
import functools
import http.server
import json
import sys
import threading
import time
import urllib.request

from playwright.sync_api import sync_playwright

MARKER = "كلمهسريه7f3a"  # unchanged by every built-in policy, so the output can be matched
WORKED_OUT = "الي المدرسة الجديدة 123"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(QuietHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:%d/" % httpd.server_address[1]


def wait_output(page, pred, timeout=20.0):
    """Poll the output box (the page's CSP forbids the eval that wait_for_function needs)."""
    end = time.time() + timeout
    while time.time() < end:
        v = page.input_value("#output")
        if pred(v):
            return v
        time.sleep(0.1)
    raise TimeoutError("output did not match; last value %r" % page.input_value("#output"))


PROBE_FETCH = """async (url) => {
  try { const r = await fetch(url, {cache: 'no-store'}); return 'allowed:' + r.status; }
  catch (e) { return 'blocked:' + e.name; }
}"""
PROBE_XHR = """(url) => new Promise((resolve) => {
  try {
    const x = new XMLHttpRequest();
    x.onload = () => resolve('allowed:' + x.status);
    x.onerror = () => resolve('blocked:error');
    x.open('GET', url);
    x.send();
  } catch (e) { resolve('blocked:' + e.name); }
})"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("space_dir")
    ap.add_argument("--json")
    args = ap.parse_args()
    httpd, base = serve(args.space_dir)
    probe_url = base + "README.md"
    checks = {}
    after = []
    try:
        with urllib.request.urlopen(probe_url) as r:
            checks["probe_url_reachable_outside_page"] = r.status == 200
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            requests, csp_reports = [], []
            page.on("request", lambda r: requests.append(r.url))
            page.on("console", lambda m: csp_reports.append(m.text) if "Content Security Policy" in m.text else None)
            page.goto(base + "?lang=en")
            out = wait_output(page, lambda v: len(v) > 0)
            checks["worked_example_output"] = out == WORKED_OUT
            workers = page.workers
            checks["processing_worker_from_blob_url"] = len(workers) == 1 and workers[0].url.startswith("blob:")
            if workers:
                w = workers[0]
                checks["worker_fetch_blocked"] = w.evaluate(PROBE_FETCH, probe_url).startswith("blocked:")
                checks["worker_xhr_blocked"] = w.evaluate(PROBE_XHR, probe_url).startswith("blocked:")
            else:
                checks["worker_fetch_blocked"] = checks["worker_xhr_blocked"] = False
            checks["page_fetch_blocked"] = page.evaluate(PROBE_FETCH, probe_url).startswith("blocked:")
            checks["csp_violation_reported"] = len(csp_reports) > 0
            # After load: type a marker text and normalise it; nothing may go to the network or to storage.
            n_before = len(requests)
            page.fill("#input", MARKER + " إِلَى")
            wait_output(page, lambda v: v.startswith(MARKER))
            page.select_option("#policy", "asr-eval-v1")
            wait_output(page, lambda v: v.startswith(MARKER) and v.endswith("الي"))
            time.sleep(0.5)
            after = requests[n_before:]
            checks["no_request_after_load"] = not after
            checks["no_request_carries_marker"] = not any(MARKER in u for u in requests)
            storage = page.evaluate("""async () => ({
              local: JSON.stringify(Object.entries(localStorage)),
              session: JSON.stringify(Object.entries(sessionStorage)),
              idb: indexedDB.databases ? JSON.stringify(await indexedDB.databases()) : '[]',
              cookie: document.cookie,
            })""")
            checks["no_storage_of_input"] = all(MARKER not in v for v in storage.values())
            checks["no_indexeddb"] = storage["idb"] == "[]"
            checks["no_cookies"] = storage["cookie"] == "" and not ctx.cookies()
            ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    ok = all(checks.values())
    result = {"base": "local static server (no CSP header)", "ok": ok, "checks": checks,
              "requests_after_load": len(after)}
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
