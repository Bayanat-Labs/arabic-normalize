# Stress runs (statistics only)

`stress_run.py` runs every text of a real corpus through the three pilot policies, in plain and detailed mode, and records crashes, offset-map and change-log consistency, idempotence, NFC, rule and lossy-flag rates, lossy context classes and word-type merges. `stress_report.py` turns its JSON into `docs/stress/`. No corpus text is written anywhere, and no corpus file is added to the repository: download the corpus files separately.

| Corpus | Command | Output |
|---|---|---|
| Arabic Wikipedia, one dump part | `python -I scripts/stress/stress_run.py --wikipedia-dump arwiki-latest-pages-articles-multistream5.xml-p5545108p6060732.bz2 --sha256 HEX --out-json wiki.json` then `python -I scripts/stress/stress_report.py --stats wiki.json --deletion deletion.json --sha1sums arwiki-latest-sha1sums.txt` | `docs/stress/report.md`, `stats.json` |
| FLEURS ar_eg transcripts | `python -I scripts/stress/stress_run.py --tsv ar_eg_train.tsv ar_eg_dev.tsv ar_eg_test.tsv --column 3 --unique-by 0 --unit sentence --sample 2000 --seed 20261013 --out-json fleurs3.json` (and `--column 2` for raw_transcription), then `stress_report.py --corpus fleurs ...` | `docs/stress/fleurs.md`, `fleurs.json` |
| Any delimited text file, one text per line | `python -I scripts/stress/stress_run.py --delimited FILE --delimiter "\|" --fields 3 --unit line --sample 2000 --seed 20261013 --out-json NAME.json`, then `stress_report.py --corpus NAME ...` | `docs/stress/NAME.md`, `NAME.json` |

`deletion.json` records the dump's SHA-1 and when it was deleted (`{"sha1", "deleted_at", "absent_after", "fetch": {...}}`); the report checks the SHA-1 against Wikimedia's published `arwiki-latest-sha1sums.txt`.

Reproducibility check, 15 Oct 2026: the same dump part (SHA-256 `88f45948…`) was downloaded again and run with this script; every count in `docs/stress/stats.json` came out identical (only timings differ).

An optional third stress corpus is not run yet.
