# Croissant metadata for the conformance dataset

`croissant.json` in this folder is the [Croissant](https://mlcommons.org/croissant/) metadata that Hugging Face generates for the dataset [Bayanat-Labs/arabic-normalization-conformance](https://huggingface.co/datasets/Bayanat-Labs/arabic-normalization-conformance). It is kept byte for byte as the Hub returned it. `scripts/build_conformance_dataset.py` copies it into the dataset as `croissant.json` and lists it in `MANIFEST.json` and `SHA256SUMS`.

| Item | Value |
|---|---|
| Source | https://huggingface.co/api/datasets/Bayanat-Labs/arabic-normalization-conformance/croissant |
| Fetched | 2026-10-15, 13:27 UTC (dataset repository commit `777a97ac2b41`) |
| SHA-256 | `0b0e32812aaf58cc824db83009c852ef8572909ccaac37cee8763b0fcd29f9f8` (20,249 bytes) |
| Croissant version | 1.1 (`conformsTo`) |
| Validation | `mlcroissant validate --jsonld croissant.json` with mlcroissant 1.1.1: no errors, 4 warnings (below) |
| Record check | mlcroissant reads 64 records from `dev` and 16 from `acceptance`, using the Hub's converted Parquet files (`refs/convert/parquet`). Their fixture ids and expected outputs equal the released Parquet files |

Warnings, as mlcroissant 1.1.1 reports them:

- `citeAs`, `datePublished` and `version` are recommended but absent. The citation is in the dataset's `CITATION.cff` and card; the version is v0.1 (2026-10-15).
- "`source` has cardinality `ONE`, but got a list". The dataset has a column named `split`, and the Hub also names its split field `<config>/split`, so two fields share one `@id`. Read through Croissant, `<config>/split` gives the Hub split name (`test`). The column's own value (`dev` or `acceptance`, the same as the config name) is unchanged in the Parquet and JSONL files.
- mlcroissant also notes that the Hub's JSON-LD `@context` differs from the reference context (the keys `equivalentProperty`, `rai`, `examples` and `samplingRate`).

To refresh it after a new dataset version is public:

```sh
curl -sS -o docs/dataset/croissant.json https://huggingface.co/api/datasets/Bayanat-Labs/arabic-normalization-conformance/croissant
mlcroissant validate --jsonld docs/dataset/croissant.json
python -I scripts/build_conformance_dataset.py --out <dataset folder>
```

Then update this table.
