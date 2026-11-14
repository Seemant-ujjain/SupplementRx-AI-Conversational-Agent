# SupplementRx AI

- Conversational-agent POC for supplement information and source-attributed retrieval.
- **Current phase:** audits, schema/rule design, bounded preprocessing and a local KG pilot are implemented.
- All six sources are represented in the pilot; full-dataset processing and a general answering system remain unfinished.

## Supplement categories

Magnesium, Vitamin D, Ashwagandha, Melatonin, Omega-3, Vitamin B12, Iron, Turmeric, Probiotics and Creatine.

## Collected datasets

| Source | Saved collection | Role |
|---|---|---|
| [DSLD](data/raw/dsld/collection_manifest.json) | 400 product labels; 40 per category | Products, brands, ingredients, quantities and servings |
| [PubChem](data/raw/pubchem/runs/20261028T035149634190Z/collection_manifest.json) | 239 compounds | Chemical structures, identifiers and synonyms |
| [RxNorm](data/raw/rxnorm/runs/20261028T060819025094Z/collection_manifest.json) | 287 concepts | Standardized ingredient names and forms |
| [MeSH](data/raw/mesh/runs/20261028T062833838481Z/collection_manifest.json) | 247 matched records | Biomedical concepts, substance classes and hierarchy |
| [NatMed Pro](data/raw/natmedpro/collection_manifest.json) | 10 monographs; 1,269 pending annotations | Source-attributed clinical-reference content |
| [Reddit](data/raw/reddit/collection_manifest.json) | 287 posts and 4,593 comments | User discussion, opinions and thread context |

- DSLD: individual files in `labels/`, combined `collection.json`, and a collection manifest.
- Terminology: 753 distinct ingredient/form names grouped into 739 queries; original occurrences retained. Other-ingredient/excipient names were excluded from collection queries.
- PubChem, RxNorm and MeSH were queried separately; these are not a downloaded UMLS Metathesaurus. Search results are candidates, not automatic identity matches.
- NatMed/Reddit use `records.jsonl`; manifests record source commits and hashes. Supplied passages and graphs remain in `upstream_derived/`, separate from our local KG.

## Import and provenance

- NatMed and Reddit came from [ARYN26/CSE573](https://github.com/ARYN26/CSE573), imported commit `1f4a3bcea5f8768f95204e74fa452d4c30c296a6` (November 9, 2026 refresh).
- [Archived imports](data/raw/imports/cse573/) preserve upstream files, prior snapshots and validation reports; raw files are not overwritten by preprocessing.
- NatMed includes captured HTML, bibliographies and 1,179 supplied passages; Reddit includes 5,071 supplied passages. Upstream-derived data is not clinical approval.
- NatMed is licensed material to keep private. Its Fish Oil and Lactobacillus acidophilus monographs must not be generalized to all Omega-3 or probiotic products.

## 1. Audit and POC field selection

- Audited all six sources and selected provisional fields in [Data_Audit_and_Preprocessing.ipynb](notebooks/Data_Audit_and_Preprocessing.ipynb).
- **Structure/completeness:** record meaning, missing fields, nulls and placeholders.
- **Identifiers:** uniqueness, reuse and links to original DSLD queries.
- **Duplicates/ambiguity:** repeated records, shared identifiers and multiple candidates.
- **Mapping quality:** intended ingredient versus a specific form or broader concept.
- **Provenance:** source hashes, query methods, source responses, excerpts and unresolved references.
- DSLD: retained all 400 labels; reviewed 70 repeated-name groups and quantity/serving differences. Similar names or equal amounts did not justify merging.
- NatMed: checked schema, excerpt offsets and field-support spans; structural validity remained separate from clinical review. Reddit: distinguished direct text from inherited thread topics.

## 2. Schema and source mappings

- Designed the shared model and source-field mappings in [Schema_Design_and_Mapping.ipynb](notebooks/Schema_Design_and_Mapping.ipynb).
- Kept product labels, ingredient occurrences, terminology targets, clinical claims, Reddit records and source evidence distinct.
- Reviewed PubChem/RxNorm/MeSH together as a terminology layer, retaining separate source IDs.
- Defined identity, normalization, deduplication, reference-resolution and version-history rules; [contract 0.1.0](schemas/poc_preprocessing_contract_v0.1.json) governs the bounded preprocessing pilot.
- The broader schema is still evolving. Graph navigation topics are not chemical identities, and general ingredient claims do not automatically apply to branded products.

## 3. Mapping confidence and decisions

- **High:** supported relationship with compatible scope → eligible for use at that relationship level.
- **Medium:** missing qualifiers or unresolved scope → pending review.
- **Low:** conflicting form, preparation or entity type → excluded from exact matching.
- Reviewed 40 pilot candidates: **24 High, 8 Medium, 8 Low**. High links comprise **18 concept mappings and 6 exact named-form mappings**.
- A concept link never becomes an exact-material match automatically. High technical confidence is not clinical approval or a statistical probability.
- Answer selection also requires relevance: a reliable packaging discussion does not answer an effectiveness question.

## 4. Normalization and issue handling

- Preserved original values, source IDs, unknown fields and evidence pointers; derived results are versioned separately.
- **BPI creatine:** 1,500 mg and 1.5 g per two capsules compare equally; differing other ingredients mean the labels remain separate.
- **BetterYou iron:** numeric 52 mL conflicts with the note's 0.52 ml; retained the conflict and blocked affected dose calculations.
- **Wrong candidate scope:** excluded Creatine HCl → monohydrate, Acacia Gum → allergenic extract and fructooligosaccharides → fructose from exact matching.
- **Class/component roles:** Withanolides and Alkaloids remain standardization classes; corrected eight nested-ingredient edges from “form” to “component.”
- **Unknown quantities/context:** NP values, absent populations and unresolved formulations are not filled with guesses. No product/ingredient canonical merges or clinical approvals were made.

## 5. Current knowledge graph

- Implemented and inspected in [Preprocessing_Pilot.ipynb](notebooks/Preprocessing_Pilot.ipynb).
- [Current graph build](data/graph/creatine-natmed-v1-f174e5e28b21603a/): **249 nodes and 418 relationships**; all six sources represented in a bounded sample.
- DSLD/terminology: seven labels, their occurrences/assertions/servings and the 24 High-confidence mapping links.
- NatMed: one Ashwagandha safety annotation plus ten Creatine annotations—seven safety, one effectiveness and two dosing-context annotations. All remain **pending clinical review**.
- Reddit: three comments; one verified direct topic mention and four inherited topic associations. Missing parent posts remain references, not fabricated content.
- Separate node/relationship CSVs form one logical graph through stable IDs; JSON/JSONL sidecars preserve evidence, review decisions and manifests.
- Previous builds are retained. No Neo4j import, embedding generation or GNN/RGCN training has occurred.

## 6. Validation and sample answers

- Checked graph endpoints, unique IDs, source hashes, evidence references, excerpt/field spans and repeatable output; retained the original source records.
- Tested product → ingredient → concept paths and source-separated DSLD/NatMed/Reddit retrieval.
- Reviewed four fixed answer examples: effectiveness/label composition, label comparison, qualified safety retrieval and an insufficient-evidence response.
- [Effectiveness answer review](data/graph/creatine-answer-review-v1-d8909281d959c7c8/report.json) and [contrasting answer checks](data/graph/contrasting-answer-review-v1-e2c229e10e5ccb52/report.json) record selected/excluded evidence and limitations.
- Negative checks reject unsupported equivalence, false clinical approval, invented recommendations and missing citations. These are curated checks, not measured precision/recall or clinical validation.

## Remaining work

- Resolve Medium mappings, serving conflicts and outstanding upstream extraction/reference gaps; do not silently correct sources.
- Expand question-relevant coverage beyond the pilot. Creatine's remaining annotations and most collected records are not yet in the graph.
- Review sample answers, then build and evaluate a general retrieval/answering layer; decide on graph-database import separately.

## Workspace and entry points

```text
notebooks/       Collection, audit, schema design and preprocessing pilot
schemas/         Versioned preprocessing contract
scripts/         Collect/import, audit, review and graph-export workflows
tests/          Implementation checks
data/raw/       Preserved source collections and imported artifacts
data/processed/ Audits, identity reviews and preprocessing outputs
data/graph/     Versioned graph exports and answer-review reports
```

- Activate locally: `source supplementsrx_env/bin/activate`.
- Collection notebooks: [DSLD](notebooks/DSLD_Data_collection.ipynb), [PubChem](notebooks/PubChem_Data_Collection.ipynb), [RxNorm](notebooks/RxNorm_Data_Collection.ipynb), [MeSH](notebooks/MeSH_Data_Collection.ipynb). Inspect collection previews before saving; terminology collectors default to `SAVE_DATA = False`.
- The pilot notebook records executed stages and reproduction commands. Source references: [DSLD](https://dsld.od.nih.gov/), [PubChem](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest), [RxNorm](https://www.lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html), [MeSH](https://id.nlm.nih.gov/mesh/).
- `merged_supplements.csv` is an obsolete file and is not an input to this workflow.
