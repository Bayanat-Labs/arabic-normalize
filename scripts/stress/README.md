# Stress runs (statistics only)

`stress_run.py` runs every text of a real corpus through the three pilot policies, in plain and detailed mode, and records crashes, offset-map and change-log consistency, idempotence, NFC, rule and lossy-flag rates, lossy context classes and word-type merges. `stress_report.py` turns its JSON into `docs/stress/`. No corpus text is written anywhere; keep the corpus files outside the repository.

| Corpus | Command (corpus files outside the repository) | Output |
|---|---|---|
| Arabic Wikipedia, one dump part | `python -I scripts/stress/stress_run.py --wikipedia-dump arwiki-latest-pages-articles-multistream5.xml-p5545108p6060732.bz2 --sha256 HEX --out-json wiki.json` then `python -I scripts/stress/stress_report.py --stats wiki.json --deletion deletion.json --sha1sums arwiki-latest-sha1sums.txt` | `docs/stress/report.md`, `stats.json` |
| FLEURS ar_eg transcripts | `python -I scripts/stress/stress_run.py --tsv ar_eg_train.tsv ar_eg_dev.tsv ar_eg_test.tsv --column 3 --unique-by 0 --unit sentence --sample 2000 --seed 20261013 --out-json fleurs3.json` (and `--column 2` for raw_transcription), then `stress_report.py --corpus fleurs ...` | `docs/stress/fleurs.md`, `fleurs.json` |
| Tanzil Quran text, Uthmani | `python -I scripts/stress/stress_run.py --tanzil quran-uthmani.txt --unit verse --sample 2000 --seed 20261013 --out-json tanzil.json`, then `stress_report.py --corpus tanzil ...` | `docs/stress/tanzil.md`, `tanzil.json` (not run yet) |

`deletion.json` records the dump's SHA-1 and when it was deleted (`{"sha1", "deleted_at", "absent_after", "fetch": {...}}`); the report checks the SHA-1 against Wikimedia's published `arwiki-latest-sha1sums.txt`.

Reproducibility check, 15 Oct 2026: the same dump part (SHA-256 `88f45948…`) was downloaded again and run with this script; every count in `docs/stress/stats.json` came out identical (only timings differ).

The Tanzil text is distributed under terms that must be accepted on its download page (https://tanzil.net/download/). Bayanat Labs agents do not accept terms, so the Tanzil run waits for the file.
