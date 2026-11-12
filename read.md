# SupplementRx AI

SupplementRx AI is a conversational-agent project exploring supplement information, evidence retrieval, and a knowledge graph. The current proof of concept focuses on collecting raw data for ten supplement categories.

**Current phase: data collection. Preprocessing will begin after all planned source data has been received.** Candidate identities have not been accepted, and source datasets have not been merged into a normalized knowledge base.

## Supplement categories

Magnesium, Vitamin D, Ashwagandha, Melatonin, Omega-3, Vitamin B12, Iron, Turmeric, Probiotics, and Creatine.

## Collection approach

```text
Ten supplement search categories
    └── DSLD product labels
        └── Ingredient rows, nested ingredients, and chemical forms
            ├── PubChem candidate records
            ├── RxNorm candidate concepts
            └── MeSH candidate records and RDF statements

NatMed Pro and Reddit exports — imported separately
```

The DSLD collection contains 40 labels per search category, totaling 400 unique labels. Recursive ingredient discovery produces 753 distinct names, grouped into 739 queries by case and whitespace to avoid repeated requests. All original names and their source occurrences are retained.

The query inventory includes co-ingredients in the selected products, not only the ten category names. The terminology collectors exclude the DSLD `otheringredients` field containing excipients. Search-category membership records how a label was found; it does not establish ingredient identity.

## Repository structure

```text
.
├── read.md
├── Proposal.pdf
├── notebooks/
│   ├── DSLD_Data_collection.ipynb
│   ├── DSLD_Data_exploration.ipynb
│   ├── PubChem_Data_Collection.ipynb
│   ├── RxNorm_Data_Collection.ipynb
│   └── MeSH_Data_Collection.ipynb
├── data/raw/
│   ├── dsld/
│   │   ├── labels/                 # Individual label_*.json files
│   │   ├── collection.json         # Combined raw collection
│   │   ├── collection_manifest.json
│   │   └── search_results.json
│   ├── pubchem/
│   │   └── runs/<UTC timestamp>/
│   ├── rxnorm/
│   │   └── runs/<UTC timestamp>/
│   ├── mesh/
│   │   └── runs/<UTC timestamp>/
│   ├── natmedpro/
│   │   ├── records.jsonl
│   │   ├── collection_manifest.json
│   │   └── upstream_derived/
│   ├── reddit/
│   │   ├── records.jsonl
│   │   ├── collection_manifest.json
│   │   └── upstream_derived/
│   ├── imports/cse573/<source commit>/
│   └── umls/
├── scripts/import_cse573_datasets.py
├── supplementsrx_env/
└── merged_supplements.csv
```



## Notebooks

| Notebook | Purpose |
|---|---|
| [DSLD collection](notebooks/DSLD_Data_collection.ipynb) | Search the ten categories and download complete label JSON and collection metadata. |
| [DSLD exploration](notebooks/DSLD_Data_exploration.ipynb) | exploratory notebook. |
| [PubChem collection](notebooks/PubChem_Data_Collection.ipynb) | Search ingredient names and collect chemical properties, structures, identifiers, and synonyms. |
| [RxNorm collection](notebooks/RxNorm_Data_Collection.ipynb) | Search exact names, then normalized names on no match; collect names, term types, attributes, and source codes. |
| [MeSH collection](notebooks/MeSH_Data_Collection.ipynb) | Search exact entry terms and collect linked descriptors, supplementary records, concepts, terms, and RDF statements. |
| [Data audit and preprocessing](notebooks/Data_Audit_and_Preprocessing.ipynb) | Read-only audit of all six sources, followed by the first DSLD preprocessing step: preserve labels, flag market status, and group repeated brand/product names for review. Other transformations remain pending. |

Each terminology notebook builds its inventory directly from DSLD. None requires running another terminology notebook first.

The notebook runs locally without network access and fingerprints the raw files before and after execution. Sections 1–6 audit without writing data files; section 8 writes versioned derived files under `data/processed/dsld/`. No raw dataset is overwritten or cleaned.

### Preprocessing step 1: DSLD label inventory

The [DSLD preprocessing script](scripts/preprocess_dsld.py) preserves all **400 labels**, adds stable source-label IDs and provenance, and flags **231 off-market** versus **169 on-market-in-source** records. These statuses describe the saved source, not independently verified present availability. **70 repeated brand/product-name groups**, covering **206 labels**, are flagged for review; no records are deleted or merged.

The [versioned outputs](data/processed/dsld/dsld-label-inventory-v1-b1689b0c095fb6ed/) contain `label_inventory.jsonl`, `on_market_label_index.csv`, `repeated_name_groups.json`, `validation_report.json`, and `manifest.json`. Each inventory record retains the original label under `raw_label`; ingredient quantities, forms and serving context are unchanged. Source fingerprints and a rules version identify each run. An identical rerun reuses the output; differing existing output is protected from overwrite.

This step does not perform ingredient normalization, cross-source entity matching, Reddit filtering, or clinical-claim approval. Those decisions remain pending review of the audit findings.

## Saved collection snapshot

The following figures describe the current local collections. The original collections were saved on October 28, 2026 UTC; the NatMed Pro and Reddit imports were refreshed on November 9, 2026. Reddit source records remain from October 27, while NatMed monographs were recaptured upstream on October 28. Sizes refer to each source's main data file: `collection.json` for DSLD and the terminology sources, or `records.jsonl` for NatMed Pro and Reddit. They exclude manifests, individual DSLD label copies, archived originals, and upstream-derived passages and graphs.

| Source | Queries with candidates | No-match queries | Collected records | Main data file size |
|---|---:|---:|---:|---:|
| DSLD | Not applicable | Not applicable | 400 product labels | 6.94 MiB |
| PubChem | 228 / 739 | 511 | 239 compounds | 9.01 MiB |
| RxNorm | 313 / 739 | 426 | 287 concepts | 69.12 MiB |
| MeSH | 270 / 739 | 469 | 247 records | 36.45 MiB |
| NatMed Pro | Not applicable | Not applicable | 10 recaptured monographs | 6.20 MiB |
| Reddit | Not applicable | Not applicable | 4,880 records: 287 posts and 4,593 comments | 5.79 MiB |

The three terminology runs completed without failed requests. Their manifests report completeness for the selected collection policy, not comprehensive coverage of supplements or clinical evidence. NatMed Pro and Reddit were imported from verified upstream archives rather than queried through those terminology APIs. Different sources and search policies make these counts unsuitable as direct measures of source quality.

- **PubChem:** 46,426 synonym entries; seven queries returned multiple candidate CIDs. Three compounds lack an IUPAC name, although property and synonym responses were retrieved for all 239 compounds.
- **RxNorm:** 282 exact-match queries and 31 normalized-match queries. The 287 concepts comprise 256 ingredients (`IN`), 30 precise ingredients (`PIN`), and one multiple-ingredient concept (`MIN`). Separately, 31 queries returned multiple candidates. Most saved property entries are source-code references. The API reported release `05-Oct-2026` throughout the run.
- **MeSH:** 195 topical descriptors, 49 supplementary chemical records, and three supplementary organism records. The collection contains 24,792 unique RDF statements across 2,360 resources, including scope notes on 206 concepts. Six queries link to multiple records. There were no unresolved matched terms, incomplete record batches, or lookup-limit warnings. MeSH uses a current endpoint; available-year metadata is not a fixed-release checksum.
- **NatMed Pro:** 10 recaptured monographs and 1,179 upstream-generated passages, plus captured bibliographies and HTML. The supplied graph remains at 20 nodes and 10 `MENTIONS` edges. An additional 1,269 clinical annotations are stored separately with pending status; none is approved. Capture-quality and clinical-review flags are preserved.
- **Reddit:** 287 posts and 4,593 comments, with 5,071 upstream-generated passages. The supplied graph has 4,890 nodes and 7,982 `MENTIONS` edges. Records remain labeled as user reports, not clinical evidence.

### Collections and manifests

| Source | Main collection | Manifest |
|---|---|---|
| DSLD | [collection.json](data/raw/dsld/collection.json) · [Individual labels](data/raw/dsld/labels/) | [Collection manifest](data/raw/dsld/collection_manifest.json) |
| PubChem | [collection.json](data/raw/pubchem/runs/20261028T035149634190Z/collection.json) | [Run manifest](data/raw/pubchem/runs/20261028T035149634190Z/collection_manifest.json) |
| RxNorm | [collection.json](data/raw/rxnorm/runs/20261028T060819025094Z/collection.json) | [Run manifest](data/raw/rxnorm/runs/20261028T060819025094Z/collection_manifest.json) |
| MeSH | [collection.json](data/raw/mesh/runs/20261028T062833838481Z/collection.json) | [Run manifest](data/raw/mesh/runs/20261028T062833838481Z/collection_manifest.json) |
| NatMed Pro | [records.jsonl](data/raw/natmedpro/records.jsonl) | [Collection manifest](data/raw/natmedpro/collection_manifest.json) |
| Reddit | [records.jsonl](data/raw/reddit/records.jsonl) | [Collection manifest](data/raw/reddit/collection_manifest.json) |

NatMed Pro and Reddit use JSONL: each line is one complete source record. Their manifests include upstream repository and commit provenance, record counts, and file hashes. Supplied passages and graph files are kept separately in each source's `upstream_derived/` folder; the detailed source sections below link to those folders.

Each terminology run contains:

- `collection.json`: original query occurrences, DSLD provenance and hashes, raw API responses, request metadata, candidate links, and a coverage report.
- `collection_manifest.json`: file size, SHA-256 checksum, completeness status, and report.

MeSH record data is stored as raw SPARQL JSON bindings, preserving source literals, language tags, datatypes, and relationship URIs. It is not stored as a flattened table.

## Running a collection

1. Open the desired notebook in a Jupyter-compatible editor with a Python kernel containing its imports. The existing `supplementsrx_env` was used for the recorded runs. The terminology notebooks use `requests` and Python's standard library; the DSLD notebook also uses `pandas`.
2. Use the project root or `notebooks/` as the working directory. Confirm `data/raw/dsld/labels/` contains the source labels and `data/raw/dsld/collection_manifest.json` exists before running a terminology collector.
3. Start with a fresh kernel and run cells in order. Public API access is required. Full runs can take several minutes; retries and request pacing are built in.
4. Inspect the preview report: matches, no matches, errors, ambiguous candidates, incomplete records, and payload size. **New raw responses remain in memory before this step.**
5. After reviewing the results, set `SAVE_DATA = True` in the final save code cell and run that cell. It writes a new timestamped directory without overwriting earlier runs.

`SAVE_DATA` defaults to `False` in the PubChem, RxNorm, and MeSH notebooks. The DSLD notebook has its own existing save workflow and does not use that preview flag. A kernel restart loses unsaved in-memory responses. The current collectors do not automatically resume a previous saved run from disk.

## Interpretation and pending work

Candidate matches are raw collection results, not approved equivalences. In particular, RxNorm normalized searches can return different salt or chemical forms. No-match results are distinct from request failures and do not establish that an ingredient is absent from a source under every possible search strategy.

DSLD supplies label information; the three terminology sources supply identifiers, names, properties, and source relationships. These collections do not by themselves establish effectiveness, recommended dosage, or safety.

After all planned data has been collected, the next phase can review candidate identities, handle unresolved terms, normalize the schema, and prepare evidence and graph inputs. Those preprocessing tasks have not been performed in the current collection workflow.

## Imported NatMed Pro and Reddit datasets

Source: [ARYN26/CSE573](https://github.com/ARYN26/CSE573), current imported commit `1f4a3bcea5f8768f95204e74fa452d4c30c296a6`, from its `datasets/` directory. This supersedes the October 28 local import of `39a48197905de2641d04a9adb8ae25100c57e4e7`. Exact import timestamps, file sizes, and SHA-256 checksums are recorded in the local manifests. The prior snapshot and prior local source folders are preserved.

The upstream repository combines both sources in compressed exports. Local import separates records using the existing `source` field, preserving each JSONL line byte-for-byte. These are **already normalized upstream exports**, not original browser captures. No additional text cleaning, entity resolution, or clinical relationship extraction was performed during import.

### NatMed Pro

- [Source records](data/raw/natmedpro/records.jsonl): **10 monographs** across the ten project topics.
- [Manifest](data/raw/natmedpro/collection_manifest.json): origin, counts, integrity hashes, and import details.
- [Upstream-derived files](data/raw/natmedpro/upstream_derived/): **1,179 passages**, **20 graph nodes**, and **10 `MENTIONS` edges**, supplied by the teammate.
- [Captured HTML](data/raw/natmedpro/source_html.jsonl): ten source captures, hash-linked to their monographs. Bibliographies are retained in each record's `reference_documents` field.
- [Pending clinical annotations](data/raw/natmedpro/upstream_derived/pending_clinical/): **1,269 pending annotations**, their upstream schema, sample, extraction report, and manifest. These have not been approved or added to our graph as clinical facts.
- [PubMed metadata](data/raw/natmedpro/upstream_derived/pubmed_metadata.jsonl) and [report](data/raw/natmedpro/upstream_derived/pubmed_report.json): metadata for **5,990 PMIDs**, of which 5,988 were found upstream. This is study metadata, not validation that a citation supports a claim.

The Omega-3 monograph is **Fish Oil**; the Probiotics monograph is **Lactobacillus acidophilus**. Their evidence must retain those source limits. The October 28 upstream recapture addressed the previously collapsed content and missing bibliography capture. Human source comparison and clinical review remain pending, and the upstream review flags remain unapproved. Upstream reports 55 inline reference numbers absent from the captured bibliographies; they are reported rather than corrected. The source repository identifies NatMed material as licensed content to keep private.

### Reddit

- [Source records](data/raw/reddit/records.jsonl): **4,880 records**, comprising **287 posts** and **4,593 comments**.
- [Manifest](data/raw/reddit/collection_manifest.json): origin, counts, integrity hashes, and import details.
- [Upstream-derived files](data/raw/reddit/upstream_derived/): **5,071 passages**, **4,890 graph nodes**, and **7,982 `MENTIONS` edges**, supplied by the teammate.

The upstream documentation describes a bounded sample from r/Supplements and r/herbalism. Reddit records retain their `user_report` evidence role and available thread/parent context. They are not clinical evidence.

The November 9 update verified all 4,880 Reddit source records were byte-for-byte unchanged. The 5,071 supplied passages retain their text and IDs but now include updated source hashes, section/word-window positions, and citation-scope metadata.

### Preserved upstream artifacts

The [original import snapshot](data/raw/imports/cse573/39a48197905de2641d04a9adb8ae25100c57e4e7/) preserves every file from `datasets/`, including compressed source records, passages, sample records, the shared graph, coverage reports, and the SQLite snapshot. Repository documentation is also preserved. All eight archives and their decompressed payloads passed the upstream manifest's byte-size and SHA-256 checks before import.

The [current import snapshot](data/raw/imports/cse573/1f4a3bcea5f8768f95204e74fa452d4c30c296a6/) preserves the updated exports, documentation, clinical schema, and upstream evaluation metadata. All **12 archives** covered by the source and clinical manifests passed compressed and decompressed hash checks. PubMed files are outside those upstream manifests and have locally recorded hashes. The upstream `collection_summary.json` is historical and still lists 5,538 passages; the current dataset manifest correctly reports **6,250**.

The [previous local source folders](data/raw/imports/cse573/1f4a3bcea5f8768f95204e74fa452d4c30c296a6/previous_local/) preserve the exact pre-update NatMed Pro and Reddit files. The [update validation report](data/raw/imports/cse573/1f4a3bcea5f8768f95204e74fa452d4c30c296a6/update_validation.json) records checks on source hashes, all 6,250 passage-to-source bindings, clinical excerpt offsets, unchanged graph exports, and unchanged Reddit source records.

The import script now supports `--update`: it checks existing file hashes, stages new files, preserves previous source folders, and then activates the new snapshot. Existing snapshots and locally modified imported files are protected. No upstream code is executed, and no further preprocessing or clinical approval is performed.

Each source's `upstream_derived/` directory contains an unchanged subset of the supplied passages and graph. 


## Source documentation

- [NIH Dietary Supplement Label Database](https://dsld.od.nih.gov/)
- [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest)
- [RxNorm API](https://www.lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html)
- [MeSH RDF](https://id.nlm.nih.gov/mesh/)

## Shared audit categories and criteria

Apply these categories consistently across datasets, using source-specific checks where appropriate. For terminology sources, retain links back to the originating DSLD ingredient queries.

- **Structure and completeness:** what each record represents and which fields are missing.
- **Identifiers:** uniqueness, reuse, and links back to DSLD queries.
- **Duplicates and ambiguity:** multiple queries reaching one identifier, or one query returning several candidates.
- **Mapping quality:** whether a result represents the intended ingredient, a specific form, or something broader.
- **Provenance:** query method, source response, and unresolved matches.

Audits document findings and unresolved decisions; they do not automatically approve mappings, merge records, or correct source values. Preserve raw data and record derived findings separately.

### DSLD repeated-name review

Notebook section 9 runs `scripts/review_dsld_name_groups.py`. The report is at `data/processed/dsld/dsld-name-review-v1-0baa34b90a1fe69e/review.md`, with detailed comparisons in `review.json` and input/output hashes in `manifest.json`.

All 70 groups (206 labels, 304 pairs) were compared. Source annotations include image differences in 51 groups, package-size differences in 31, and flavor differences in 2 (overlapping counts); 8 groups have no within-group relationship annotation. Ingredient-row JSON differs in 54 groups, serving-size JSON in 23, and package contents in 40. These are exact stored-field comparisons, not verified formulation changes. Sixteen groups contain multiple labels marked on-market in the source snapshot. No pair is identical across all fields after excluding only `id` and `src`.

Retain every label ID and source relationship. Do not infer product identity from names, UPC/SKU, or DSLD entry dates alone. All raw files remain unchanged; no records were merged or deleted.

### DSLD ingredient and serving review

Notebook section 10 and `scripts/review_dsld_ingredients.py` compare all 304 pairs within the 70 repeated-name groups. Detailed outputs are in `data/processed/dsld/dsld-ingredient-review-v1-0baa34b90a1fe69e/` (`review.md`, `review.json`, `manifest.json`). Source hashes and comparison rules are retained.

Twenty-seven groups match across all pairs on the compared ingredient names, forms, quantities/basis and serving definitions; 43 have at least one difference. This is not an identity or formulation-equivalence decision. Other ingredients, notes, daily values and source metadata require separate consideration. No unit conversion, synonym mapping or merging is performed.

A notable source inconsistency is BetterYou Iron Daily Oral Spray label 257287: numeric serving fields say 52 mL, but its serving note states 0.52 ml. Verify the original label before correcting this value or calculating normalized doses. Section 10 also discusses equivalent mass-unit representations, differing tablet counts and differing recorded EPA/DHA amounts. All raw records remain unchanged.

### DSLD quantity and serving audit

Notebook section 12 runs `scripts/audit_dsld_quantities.py` across all 400 labels (2,339 ingredient rows and 2,392 quantity entries). Reports are in `data/processed/dsld/dsld-quantity-audit-v1-ae1a24aa4a66389a/`: `audit.md`, detailed `audit.json`, filterable `findings.csv`, and a provenance/checksum manifest. Notebook outputs include a raw-data example for every finding category.

Findings include 705 NP-unit zero entries on 74 labels, 8 missing serving-basis values on 2 labels, 35 incomplete daily-serving ranges, and 67 quantity bases outside the stated per-serving range on 9 labels. Of those 67, 52 fall within a computed daily-total range; this remains a review clue, not an automatic correction. BetterYou label 257287 has a numeric serving/notes conflict. Another 32 named-unit zeros and 24 inequality amounts are informational. Categories overlap.

No ingredient row lacks quantity entries, no amount is nonnumeric/nonfinite/negative, and all serving references resolve with matching serving-unit text. These checks do not validate source accuracy. NP semantics and ambiguous quantities remain unresolved; no units, quantities, raw labels or product identities were changed. Free-text checks are limited to explicit mL values in mL serving notes.

### DSLD baseline audit completion

Notebook section 13 runs `scripts/audit_dsld_baseline.py` and saves executable examples. Outputs: `data/processed/dsld/dsld-baseline-audit-v1-1487bf52f8e90a1f/` (`audit.json`, `audit.md`, `field_profiles.json`, `manifest.json`). All 213 field profiles across 31 object paths distinguish missing keys, null, empty strings/containers, candidate placeholder tokens and populated values. Child-field denominators are existing child objects, not all 400 labels.

Additional candidate checks found 4 normalized-name groups crossing exact-name boundaries and 10 shared whitespace-compacted UPC/SKU groups crossing exact names. These are not approved merges. Across 5,438 ingredient/form occurrences, 291 normalized names map to multiple DSLD ingredient IDs; 382 UNII fields contain 0 or 1. No external identifier registry validation was performed.

Of 1,739 label relationship entries, 1,720 are distinct directed typed links; 916 entries reference 451 labels outside the sample. Entry dates span 2011-10-26 through 2025-09-25. Directions occur on 398 labels, precautions on 366, and other-ingredient lists on 387. Absence of text does not establish absence of risk or ingredients. Source claim codes are not clinical evidence.

Together with earlier sections, the DSLD baseline is sufficiently documented for shared-schema design. Source vocabulary interpretation, external identifier verification, label-image accuracy, semantic merging and clinical review remain pending. No raw data, quantities or identities were changed.

### PubChem baseline audit

Notebook section 15 runs `scripts/audit_pubchem.py` against the saved 2026-10-28 snapshot. Outputs are in `data/processed/pubchem/pubchem-baseline-audit-v1-ee86973dbcbcc97b/` (`audit.json`, `audit.md`, `field_profiles.json`, `manifest.json`). Saved notebook outputs show source queries, DSLD occurrences, properties and ambiguity examples.

All 3,391 DSLD ingredient/form occurrences and source hashes were verified. Of 739 queries, 221 returned one CID, 7 returned multiple CIDs and 511 returned no match. There are 239 compound records and 272 candidate links. Thirty CIDs are reached by multiple queries; 74 normalized synonyms span multiple CIDs; 8 groups share InChIKey. These are review findings, not approved equivalences. Three records lack IUPACName. Collection and batch-response consistency checks pass; six derived candidate lists differ only in ordering due to the collector's sorting.

The audit is offline. Single results, shared synonyms and matching structures do not automatically approve ingredient mappings. Category associations include co-ingredients and are not clinical indications. No raw data was changed, no mappings were approved and no records were merged.

### RxNorm baseline audit

Notebook section 16 runs `scripts/audit_rxnorm.py` against the saved 2026-10-28 snapshot. Outputs: `data/processed/rxnorm/rxnorm-baseline-audit-v1-bb5c0ce9a6faee14/` (`audit.json`, `audit.md`, `field_profiles.json`, `manifest.json`). Notebook outputs include source search parameters, responses, concept properties and ambiguity examples.

All 3,391 DSLD ingredient/form occurrences across 400 labels were verified. Of 739 queries, 282 matched by exact search, 31 by normalized search and 426 returned no match. There are 31 ambiguous queries (21 exact and 10 normalized), 287 concepts (256 IN, 30 PIN, 1 MIN), and 347 candidate links. Forty-six concepts are reached by multiple query names. There are 31 shared external-code groups excluding SPL_SET_ID; these are not approved equivalences.

Creatine HCl returns creatine and creatine monohydrate via normalized search, illustrating why candidate mappings require identity review. Turmeric returns turmeric extract via exact search; exact does not guarantee equivalent preparation or scope. The 180,747 property entries are dominated by 175,552 SPL_SET_ID values. All 287 basic umlscui fields are blank; no UMLS CUIs are supplied here.

Hashes, source paths, search-policy traces and concept responses pass integrity checks. The saved vocabulary/API versions are stable across collection. The audit is offline; no mappings were approved, records merged or raw files changed.

### NatMed baseline audit and annotation validation

Notebook section 17 runs `scripts/audit_natmed.py` with `supplementsrx_env/bin/python`. Install its validator with `supplementsrx_env/bin/python -m pip install -r requirements-audit.txt`. Outputs: `data/processed/natmedpro/natmed-baseline-audit-v1-b548c344b8c0a9b7/` (`audit.json`, `audit.md`, `field_profiles.json`, `manifest.json`). Saved notebook outputs show claim-type completeness, source scope, example claims and supporting source spans.

All 1,269 claims pass the supplied contract 1.1 JSON Schema (Draft 2020-12 with format checking). Independent source checks pass for excerpts, hashes, source identity, dose-range ordering and 2,923 field-support anchors. Of those anchors, 769 effectiveness ratings refer to earlier section headings; the check for intervening headings is limited to known ratings. This is not the upstream custom validator or a clinical review. All 1,269 claims remain pending.

Source/capture hashes and 1,179 passage bindings pass. There are 5 repeated passage-text groups, 13 repeated claim-text groups and 12 shared source-span/type groups, but no duplicate full claim payloads after excluding ID. Population/dose distinctions prevent automatic merging. The upstream 49 extraction issues and 55 missing bibliography reference numbers remain unresolved. Dose indication/formulation/strain fields remain unpopulated; 71 of 85 dose claims have structured numeric values.

The audit covers the locally imported snapshot, not current upstream/publisher content. No source corrections, normalized doses, clinical approvals or record merges were made. Raw data remains unchanged.
