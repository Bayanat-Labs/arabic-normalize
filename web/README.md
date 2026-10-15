# web/: the Arabic Text Normalizer page

A static page that runs the JavaScript port (`js/`) in the browser, in Arabic (right to left, the default) and English: paste text, choose a policy, and see the text before and after, the change log, the lossy flags, the diacritization ratio, the policy SHA-256 and a comparison with a second policy. It is deployed as the Hugging Face Space [Bayanat-Labs/arabic-normalizer](https://huggingface.co/spaces/Bayanat-Labs/arabic-normalizer) and is the tool behind https://www.bayanatlabs.com/tools/arabic-normalizer.

```bash
node web/build.mjs --out /tmp/arabic-normalizer   # assemble the page, the library, policies, fonts and the Space README
python3 -m http.server 8765 --bind 127.0.0.1 --directory /tmp/arabic-normalizer
```

Privacy: all processing happens in the browser tab, in a Web Worker when available. The page loads nothing from other hosts and its Content-Security-Policy forbids network connections (`connect-src 'none'`), so it keeps working offline once loaded. The text is never put in the URL or in browser storage; only the chosen interface language is remembered.

Files: `index.html`, `app.js` (interface and strings), `compute.js` (one normalisation request), `worker.js`, `style.css`, `fonts/` (IBM Plex Sans Arabic, SIL OFL 1.1, see `fonts/OFL.txt`). Code: Apache-2.0.
