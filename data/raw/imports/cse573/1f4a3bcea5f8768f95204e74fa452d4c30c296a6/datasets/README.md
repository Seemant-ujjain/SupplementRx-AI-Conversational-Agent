# Collected prototype dataset

This private repository includes 4,890 source records: 287 Reddit posts,
4,593 Reddit comments, and 10 NatMed professional monographs. There are
6,250 derived passages (5,071 Reddit, 1,179 NatMed), plus source/mention graph
exports and a SQLite snapshot.

Rule-based extraction also supplies **1,269 pending clinical annotations** from
the ten monographs. These are source-backed candidates for human review, not
approved medical facts. Start with [clinical_claims.sample.json](clinical_claims.sample.json)
for readable values; [clinical_extraction_report.json](clinical_extraction_report.json)
shows per-source/type/field coverage and the 49 unresolved extraction issues.

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

`manifest.json` records source/archive destinations, sizes and SHA-256 hashes.
`clinical_claims_manifest.json` independently fingerprints the source records,
claim schema and three clinical-output archives. The restore command processes
both manifests; `--manifest datasets/clinical_claims_manifest.json` selects only
clinical outputs. Existing differing local files remain protected unless
`--overwrite` is explicitly supplied. The SQLite file is a consistent source backup.

**October 28 NatMed recapture.** The ten NatMed records were recaptured from an
authenticated, user-controlled Edge session and re-imported through the real batch
importer. About two-thirds of each monograph had been hidden in collapsed
`.custom-details-content` blocks behind 300+ "more" toggles, which the earlier
capture never saved (Magnesium grew from 52.6k to 146.0k characters; monographs
are now about 55k-228k characters). The hidden blocks are now revealed in place
and the rendered text is saved. The 4,880 Reddit records are byte-identical to the
October 27 snapshot, the knowledge-graph edges are identical (7,992 `MENTIONS`),
and only the ten NatMed records changed. Passages rose from 5,538 to 6,250.
Passages retain the clinical source title, Reddit mention scope and parent
context, capture-quality and normalization metadata, batch identity when available,
source hash and exact section/word-window metadata. Citation links are limited to
numeric labels cited in that passage, not the full page inventory or verified
study support. `reference_documents_sha256` now holds the hash of each monograph's
captured bibliography. "Nutrient Depletions" is its own section for Magnesium,
Vitamin D, Vitamin B12 and Iron; no claims are extracted from it.
Hashes in `manifest.json` describe the updated archives. `collection_summary.json`
(restored to `data/collection_summary.json`) is the original October 27 completion
record and still lists 5,538 passages.
If you already restored an older copy, preserve any local collection changes
before deliberately using `--overwrite`; do not overwrite a newer local corpus
just to refresh its derived passages. Use `python3 -m supplementsrx export`
to regenerate passages from your own current database instead.

**Raw HTML and bibliographies.** `natmed_source_html.jsonl.gz` (restores to
`data/natmed_source_html.jsonl`) holds the raw monograph HTML, one row per record,
bound to its record by `source_html_sha256`. All `<script>` and `<noscript>` elements
were removed before saving (they embed account, session and IP identifiers) and
session parameters were stripped; the monograph text is unchanged
(`natmed.scrub_source_html`). Each monograph's bibliography is the authenticated
server HTML of its References page, because the rendered page is DataTables-paginated
and shows only 10 rows. Parsed rows equal the site's "of N entries" totals for all
ten monographs and are stored in the source record's `reference_documents`.

| Monograph | Bibliography entries | Inline citation refs absent from bibliography |
| --- | ---: | ---: |
| Creatine | 544 | 6 |
| Magnesium | 965 | 0 |
| Vitamin D | 628 | 30 |
| Ashwagandha | 137 | 0 |
| Melatonin | 1,022 | 1 |
| Fish Oil | 1,062 | 10 |
| Vitamin B12 | 534 | 1 |
| Iron | 666 | 3 |
| Turmeric | 586 | 4 |
| Lactobacillus acidophilus | 291 | 0 |
| **Total** | **6,435** | **55** |

The 55 missing reference numbers are a publisher-side gap; they are reported, not
corrected.

NatMed is licensed content; keep this dataset private. The Omega-3 source is
Fish Oil, and the Probiotics source is Lactobacillus acidophilus. Evidence in
those monographs must retain its ingredient, formulation, population, and strain
limits. Reddit content remains labeled `user_report`; it is not clinical evidence.
Capture of the ten monographs is now structurally complete (no collapsed content
or missing bibliography), but `capture_quality.complete` stays false and
`requires_clinical_review` stays true. Qualified human source/claim review, UMLS
mapping, DSLD collection and QA relevance judgments remain outstanding. See
[READINESS_AUDIT.md](../READINESS_AUDIT.md).

## Clinical outputs

| Checked-in artifact | Restored output |
| --- | --- |
| `clinical_claims.jsonl.gz` | `exports/clinical_claims.jsonl` |
| `clinical_claims.sample.json.gz` | `exports/clinical_claims.sample.json` |
| `clinical_extraction_report.json.gz` | `exports/clinical_extraction_report.json` |

The sample and report are also checked in uncompressed for GitHub inspection.
Regenerate from saved sources with `python3 -m supplementsrx extract-clinical`
(it reads the raw HTML in `datasets/natmed_source_html.jsonl.gz`, or `--html PATH`,
and requires each row's hash to match the record's `source_html_sha256`);
validate with `python3 -m supplementsrx validate-claims datasets/clinical_claims.jsonl.gz`.
No source record is modified, and the command cannot approve a claim.

Current counts (1,269 pending, 0 approved): 85 dose (71 with numeric quantities),
809 effectiveness, 107 safety, 120 adverse-effect and 148 interaction claims.
Safety claims include Interactions-with-Conditions entries, identifiable by
`source.section_heading == "interactions with conditions"`, with the condition in
`population`; they describe caution in that condition, not an indication. Each
excerpt holds one entry with its detail paragraphs. Known gaps: Ashwagandha
warnings embedded in its overview are not parsed (`section_not_in_html`), and two
entries with inline condition headings (Magnesium PXE, Fish Oil heart transplant)
yield issues, not claims.

## PubMed metadata

`python3 -m supplementsrx pubmed-enrich` reads the captured bibliographies and
fetches public NCBI E-utilities esummary metadata only (title, journal, year,
publication types, DOI) into `pubmed_metadata.jsonl.gz` and `pubmed_report.json`.
These two files are checked in directly and are not part of the restore manifests.

- 5,990 distinct PMIDs; 5,988 found in PubMed.
- Publication types, counted per source bibliography (a PMID cited by two
  monographs counts twice): 2,456 Randomized Controlled Trials, 773 Meta-Analyses
  and 653 Systematic Reviews.
- 23 citation-year vs PubMed-year mismatches are flagged as possible wrong
  publisher links; none is corrected.

Publication type and year describe the cited study, not whether it supports a claim.
