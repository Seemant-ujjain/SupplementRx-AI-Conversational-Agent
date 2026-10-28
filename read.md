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

Each terminology notebook builds its inventory directly from DSLD. None requires running another terminology notebook first.

## Saved collection snapshot

The following figures describe the local collections and imports saved on October 28, 2026 UTC. NatMed Pro and Reddit were collected upstream on October 27. Sizes refer to each source's main data file: `collection.json` for DSLD and the terminology sources, or `records.jsonl` for NatMed Pro and Reddit. They exclude manifests, individual DSLD label copies, archived originals, and upstream-derived passages and graphs.

| Source | Queries with candidates | No-match queries | Collected records | Main data file size |
|---|---:|---:|---:|---:|
| DSLD | Not applicable | Not applicable | 400 product labels | 6.94 MiB |
| PubChem | 228 / 739 | 511 | 239 compounds | 9.01 MiB |
| RxNorm | 313 / 739 | 426 | 287 concepts | 69.12 MiB |
| MeSH | 270 / 739 | 469 | 247 records | 36.45 MiB |
| NatMed Pro | Not applicable | Not applicable | 10 monographs | 2.21 MiB |
| Reddit | Not applicable | Not applicable | 4,880 records: 287 posts and 4,593 comments | 5.79 MiB |

The three terminology runs completed without failed requests. Their manifests report completeness for the selected collection policy, not comprehensive coverage of supplements or clinical evidence. NatMed Pro and Reddit were imported from verified upstream archives rather than queried through those terminology APIs. Different sources and search policies make these counts unsuitable as direct measures of source quality.

- **PubChem:** 46,426 synonym entries; seven queries returned multiple candidate CIDs. Three compounds lack an IUPAC name, although property and synonym responses were retrieved for all 239 compounds.
- **RxNorm:** 282 exact-match queries and 31 normalized-match queries. The 287 concepts comprise 256 ingredients (`IN`), 30 precise ingredients (`PIN`), and one multiple-ingredient concept (`MIN`). Separately, 31 queries returned multiple candidates. Most saved property entries are source-code references. The API reported release `05-Oct-2026` throughout the run.
- **MeSH:** 195 topical descriptors, 49 supplementary chemical records, and three supplementary organism records. The collection contains 24,792 unique RDF statements across 2,360 resources, including scope notes on 206 concepts. Six queries link to multiple records. There were no unresolved matched terms, incomplete record batches, or lookup-limit warnings. MeSH uses a current endpoint; available-year metadata is not a fixed-release checksum.
- **NatMed Pro:** 10 monographs and 467 upstream-generated passages. The supplied graph has 20 nodes and 10 `MENTIONS` edges. Capture-quality and clinical-review flags are preserved; these are imported reference records, not approved medical claims.
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

Source: [ARYN26/CSE573](https://github.com/ARYN26/CSE573), commit `39a48197905de2641d04a9adb8ae25100c57e4e7`, imported from its `datasets/` directory. Exact import timestamps, file sizes, and SHA-256 checksums are recorded in the local manifests.

The upstream repository combines both sources in compressed exports. Local import separates records using the existing `source` field, preserving each JSONL line byte-for-byte. These are **already normalized upstream exports**, not original browser captures. No additional text cleaning, entity resolution, or clinical relationship extraction was performed during import.

### NatMed Pro

- [Source records](data/raw/natmedpro/records.jsonl): **10 monographs** across the ten project topics.
- [Manifest](data/raw/natmedpro/collection_manifest.json): origin, counts, integrity hashes, and import details.
- [Upstream-derived files](data/raw/natmedpro/upstream_derived/): **467 passages**, **20 graph nodes**, and **10 `MENTIONS` edges**, supplied by the teammate.

The Omega-3 monograph is **Fish Oil**; the Probiotics monograph is **Lactobacillus acidophilus**. Their evidence must retain those source limits. The upstream specification flags expandable-content markers and incomplete bibliography capture in all ten monographs; source comparison and clinical review remain pending. The source repository identifies NatMed material as licensed content to keep private.

### Reddit

- [Source records](data/raw/reddit/records.jsonl): **4,880 records**, comprising **287 posts** and **4,593 comments**.
- [Manifest](data/raw/reddit/collection_manifest.json): origin, counts, integrity hashes, and import details.
- [Upstream-derived files](data/raw/reddit/upstream_derived/): **5,071 passages**, **4,890 graph nodes**, and **7,982 `MENTIONS` edges**, supplied by the teammate.

The upstream documentation describes a bounded sample from r/Supplements and r/herbalism. Reddit records retain their `user_report` evidence role and available thread/parent context. They are not clinical evidence.

### Preserved upstream artifacts

The [original import snapshot](data/raw/imports/cse573/39a48197905de2641d04a9adb8ae25100c57e4e7/) preserves every file from `datasets/`, including compressed source records, passages, sample records, the shared graph, coverage reports, and the SQLite snapshot. Repository documentation is also preserved. All eight archives and their decompressed payloads passed the upstream manifest's byte-size and SHA-256 checks before import.

Each source's `upstream_derived/` directory contains an unchanged subset of the supplied passages and graph. 


## Source documentation

- [NIH Dietary Supplement Label Database](https://dsld.od.nih.gov/)
- [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest)
- [RxNorm API](https://www.lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html)
- [MeSH RDF](https://id.nlm.nih.gov/mesh/)
