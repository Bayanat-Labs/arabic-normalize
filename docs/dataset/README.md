# Croissant metadata for the conformance dataset

Hugging Face generates [Croissant](https://mlcommons.org/croissant/) metadata for the dataset [Bayanat-Labs/arabic-normalization-conformance](https://huggingface.co/datasets/Bayanat-Labs/arabic-normalization-conformance) from the published files and the dataset card, at https://huggingface.co/api/datasets/Bayanat-Labs/arabic-normalization-conformance/croissant. A copy is kept in this folder as `croissant.json`, byte for byte as the Hub returned it; `scripts/build_conformance_dataset.py` copies it into the dataset as `croissant.json` and lists it in `MANIFEST.json` and `SHA256SUMS`.

Because the metadata repeats the opening of the dataset card, the copy is fetched again after each upload of a new card. The card was revised on 15 Oct 2026; the copy for the revised card has not been fetched yet, so `croissant.json` is not in this folder and the dataset is built without it until then.

Validation notes from the first copy (fetched 15 Oct 2026, dataset repository commit `777a97ac2b41`; mlcroissant 1.1.1, no errors, 4 warnings):

- `citeAs`, `datePublished` and `version` are recommended but absent. The citation is in the dataset's `CITATION.cff` and card; the version is v0.1 (2026-10-15).
- "`source` has cardinality `ONE`, but got a list". The dataset has a column named `split`, and the Hub also names its split field `<config>/split`, so two fields share one `@id`. Read through Croissant, `<config>/split` gives the Hub split name (`test`). The column's own value (`dev` or `acceptance`, the same as the config name) is unchanged in the Parquet and JSONL files.
- mlcroissant also notes that the Hub's JSON-LD `@context` differs from the reference context (the keys `equivalentProperty`, `rai`, `examples` and `samplingRate`).
- mlcroissant read 64 records from `dev` and 16 from `acceptance`, using the Hub's converted Parquet files (`refs/convert/parquet`); their fixture ids and expected outputs equal the released Parquet files.

To refresh it after a new card or dataset version is public:

```sh
curl -sS -o docs/dataset/croissant.json https://huggingface.co/api/datasets/Bayanat-Labs/arabic-normalization-conformance/croissant
mlcroissant validate --jsonld docs/dataset/croissant.json
python -I scripts/build_conformance_dataset.py --out <dataset folder> --source-commit <commit of the dataset inputs>
```

Then record the fetch date, the dataset repository commit, the SHA-256 and the validation result here.
