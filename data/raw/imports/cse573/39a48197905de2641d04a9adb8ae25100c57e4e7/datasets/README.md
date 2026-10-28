# Collected prototype dataset

This private repository includes 4,890 source records: 287 Reddit posts,
4,593 Reddit comments, and 10 NatMed professional monographs. There are
5,538 derived passages, plus source/mention graph exports and a SQLite snapshot.

The archives preserve the collected records and their citations. Restore the
standard project layout using Python 3.10 or later:

```sh
python3 scripts/restore_dataset.py
python3 -m supplementsrx status
```

To check all archive and extracted-content hashes without restoring files:

```sh
python3 scripts/restore_dataset.py --verify-only
```

`manifest.json` records the destination, byte size, and SHA-256 hashes of each
file. Existing differing local files are protected unless `--overwrite` is
explicitly supplied. The SQLite database is a consistent backup of the collection.

The October 27 correctness update regenerated passage metadata and coverage,
without changing source text or collection counts. Passages now retain the
clinical source title, Reddit mention scope and parent context, capture-quality
and normalization metadata, and batch identity when present in the source
record. Hashes in `manifest.json` describe the updated archives.
If you already restored an older copy, preserve any local collection changes
before deliberately using `--overwrite`; do not overwrite a newer local corpus
just to refresh its derived passages. Use `python3 -m supplementsrx export`
to regenerate passages from your own current database instead.

NatMed is licensed content; keep this dataset private. The Omega-3 source is
Fish Oil, and the Probiotics source is Lactobacillus acidophilus. Evidence in
those monographs must retain its ingredient, formulation, population, and strain
limits. Reddit content remains labeled `user_report`; it is not clinical evidence.
Collection and section extraction are complete for this bounded prototype;
medical claim review and UMLS mapping are later project stages.
