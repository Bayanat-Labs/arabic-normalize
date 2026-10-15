# web/: the Arabic Text Normalizer page

A static page that runs the JavaScript port (`js/`) in the browser, in Arabic (right to left, the default) and English: paste text, choose a policy, and see the text before and after, the change log, the lossy flags, the diacritization ratio, the policy SHA-256 and a comparison with a second policy. It is deployed as the Hugging Face Space [Bayanat-Labs/arabic-normalizer](https://huggingface.co/spaces/Bayanat-Labs/arabic-normalizer) and is the tool behind https://www.bayanatlabs.com/tools/arabic-normalizer.

```bash
node web/build.mjs --out /tmp/arabic-normalizer   # assemble the page, the library, policies, fonts and the Space README
python3 -m http.server 8765 --bind 127.0.0.1 --directory /tmp/arabic-normalizer
```

Privacy: all processing happens in the browser tab, in a Web Worker when available. The page loads nothing from other hosts and its Content-Security-Policy forbids network connections (`connect-src 'none'`), so it keeps working offline once loaded. The worker is started from a `blob:` URL, so it inherits the page's policy: the code that processes the text cannot open a network connection either (a worker loaded from its own URL would take its policy from the HTTP response, and static hosts such as Hugging Face send none). The text is never put in the URL or in browser storage; only the chosen interface language is remembered.

Privacy check (Playwright, headless Chromium; also run in CI):

```bash
node web/build.mjs --out /tmp/arabic-normalizer
python web/privacy_check.py /tmp/arabic-normalizer
```

It checks that the worker runs from a `blob:` URL, that `fetch` and `XMLHttpRequest` fail inside the worker and in the page while the same URL is reachable from outside, and that typing text after load makes no network request and writes nothing to localStorage, sessionStorage, IndexedDB or cookies.

Files: `index.html`, `app.js` (interface and strings), `compute.js` (one normalisation request), `worker.js`, `privacy_check.py`, `style.css`, `fonts/` (IBM Plex Sans Arabic 1.005, the unmodified complete WOFF2 files from IBM's `@ibm/plex-sans-arabic` 1.1.0, SIL OFL 1.1 with Reserved Font Name "Plex", see `fonts/OFL.txt`; provenance rows in `PROVENANCE.jsonl`). Code: Apache-2.0.
