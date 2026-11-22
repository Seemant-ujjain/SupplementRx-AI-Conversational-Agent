# SupplementRx AI

- Conversational-agent POC for supplement information and source-attributed retrieval.
- **Current phase:** collection-wide preparation and an evidence-preserving KG export are complete for the saved POC data.
- **Latest KG:** 35,998 nodes, 74,122 relationships and 33 relationship types across all six sources.
- Neo4j import, embeddings and the conversational answering system are next; no GNN/RGCN has been trained.

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

- **Design sequence:** dataset audits and provisional field selection → 10 representative POC questions → question-to-field coverage review → shared schema and source mappings → implementation and validation. Lower/upper bounds were formalized afterward.
- The **10 design questions** covered amounts/composition, product comparison, effectiveness, safety/interactions, dose context, terminology identity, Reddit experiences and provenance/conflicts. Examples: comparing 1,500 mg with 1.5 g, and distinguishing Creatine HCl from other creatine forms.
- **Design rules:** retain the fields and relationships each question needs; distinguish source roles and ingredient forms; preserve serving/clinical context, provenance, unknowns and conflicts; avoid unsupported identity merges or product-level clinical inference.
- Full questions, source-field coverage and acceptance criteria are in **Step 1** of [Schema_Design_and_Mapping.ipynb](notebooks/Schema_Design_and_Mapping.ipynb); subsequent steps define the schema and mappings.
- Kept product labels, ingredient occurrences, terminology targets, clinical claims, Reddit records and source evidence distinct.
- Reviewed PubChem/RxNorm/MeSH together as a terminology layer, retaining separate source IDs.
- Defined identity, normalization, deduplication, reference-resolution and version-history rules; [contract 0.1.0](schemas/poc_preprocessing_contract_v0.1.json) provides the base record conventions, extended by collection-wide specifications.
- Graph navigation topics are not chemical identities, and general ingredient claims do not automatically apply to branded products. The current export retains source-specific records and qualified claim nodes.

## Retrospective schema bounds

- Formalized the audit-driven, POC-guided design retrospectively; no KG records were changed.
- **Lower bound:** 14 node types and 20 relationship types needed for the chosen POC question families, with required properties, source links and scoped cardinalities. Unknown values remain valid; no mandatory identity match or invented clinical value.
- **Upper bound:** the current 16 node types and 33 relationship types, permitted endpoints and top-level properties. Extensions require schema versioning; nested source structures retain their existing contracts.
- Current graph passes these checks. This confirms structural conformance, not clinical approval or complete answer coverage; all 1,269 claims remain pending review.
- [Specification](schemas/kg_schema_bounds_v1.json) · [Findings](reports/Schema_Bounds_Review.md) · [Validation result](reports/schema_bounds_validation_v1.json). Recheck with `python3 scripts/validate_schema_bounds.py`.

## 3. Mapping confidence and decisions

- **High:** supported relationship with compatible scope → eligible for use at that relationship level.
- **Medium:** missing qualifiers or unresolved scope → pending review.
- **Low:** conflicting form, preparation or entity type → excluded from exact matching.
- The latest graph contains **3,073 mapping relationships**, including terminology and NatMed subject links.
- Context-based discovery considered related saved queries using explicit label qualifiers. A subsequent general-concept rule added **34 DENOTES_CONCEPT links**: 21 from the original review pool and 13 additional candidates.
- Matching ingredient identity, plant part and preparation can support a general concept link. Standardization percentages and branded preparations remain on the source occurrence; they do not imply exact material equivalence.
- A concept link never becomes an exact-material match automatically. High technical confidence is not clinical approval or a statistical probability.
- Answer selection also requires relevance: a reliable packaging discussion does not answer an effectiveness question.

## 4. Normalization and issue handling

- **Normalization rules:** standardize search-name formatting and supported mass representations for comparison; preserve original names, units, operators and serving basis. Unsupported conversions and conflicting quantities stay blocked.
- **Deduplication rules:** retain source IDs and snapshots; group similar records for review rather than merging entities. Equal quantities or repeated text do not establish identical products or independent corroboration. See the [identity/deduplication policy](schemas/identity_deduplication_decisions_v1.json) and [DSLD normalization specification](schemas/dsld_normalization_batch_v1.json).
- Preserved original values, source IDs, unknown fields and evidence pointers; derived results are versioned separately.
- **BPI creatine:** 1,500 mg and 1.5 g per two capsules compare equally; differing other ingredients mean the labels remain separate.
- **BetterYou iron:** numeric 52 mL conflicts with the note's 0.52 ml; retained the conflict and blocked affected dose calculations.
- **Wrong candidate scope:** excluded Creatine HCl → monohydrate, Acacia Gum → allergenic extract and fructooligosaccharides → fructose from exact matching.
- **Class/component roles:** Withanolides and Alkaloids remain standardization classes; corrected eight nested-ingredient edges from “form” to “component.”
- **Unknown quantities/context:** NP values, absent populations and unresolved formulations are not filled with guesses. No product/ingredient canonical merges or clinical approvals were made.

## 5. Current knowledge graph

**Use [full-graph-concepts-v1-08c99550a0fa0f86aca9](data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9/).** It is a complete snapshot, not an addition to combine with older folders.

| Contents | Purpose |
|---|---|
| `nodes/*.csv` | 16 node types: labels, ingredient occurrences, servings, assertions, terminology/chemical concepts, NatMed records/claims, Reddit records, topics and references |
| `relationships/relationships.csv` | 74,122 directed relationships connecting stable node IDs |
| `provenance/evidence.jsonl` | 64,312 source/decision evidence records |
| `review/` | Mapping decisions, exclusions, unresolved cases and source issues |
| `manifest.json`, `input_manifest.json`, `validation_report.json` | File hashes, build lineage and validation results |

- **Graph model:** a property-graph export with typed, directed relationships, nested properties and provenance. It is not an RDF/OWL implementation; source–relationship–target triples alone do not make it RDF. Semantics come from the schema, terminology identifiers, qualified relationship types and mapping rules.
- Node CSV columns: `id`, `type`, `properties_json`, `evidence_ids`. Relationship CSVs additionally identify endpoints, mapping IDs and confidence. Nested source properties remain JSON inside CSV cells.
- Includes all 400 saved DSLD labels and **6,462 captured label statements**; marketing/disclaimers are preserved as attributed text, not clinical facts.
- Includes 10 NatMed monographs, all **1,269 pending annotations**, 287 Reddit posts and 4,593 comments. Missing references remain explicit.
- Example: an Ashwagandha occurrence with explicit root context links to RxNorm **Withania somnifera root extract (1309279)** through `DENOTES_CONCEPT`; KSM-66/withanolide details remain on the occurrence.
- [Freeze/validation records](data/graph/poc-concepts-release-v1-9250419f3c2fc93805f9/) identify this graph; they are not another complete graph copy.
- Workflows: [Full_KG_Construction.ipynb](notebooks/Full_KG_Construction.ipynb) and the later mapping revisions in [Schema_Design_and_Mapping.ipynb](notebooks/Schema_Design_and_Mapping.ipynb).

## 6. Validation and limitations

- Verified unique IDs, valid endpoints, source hashes, evidence references and preservation of earlier nodes/edges. The final mapping revision passed validation; **233 tests passed** at that revision.
- The preceding graph review verified 64,278 evidence pointers, 1,269 NatMed excerpts and 2,923 field-support anchors. The final revision preserved that evidence and separately verified 34 additional mapping-decision pointers.
- **Original mapping pool:** 4,145 rows remain pending; 48 remain excluded. **Additional contextual pool:** 282 pending and 21 excluded. Counts represent candidate/occurrence rows, not unique ingredients or broken graph connections.
- **4,207 historical no-candidate lookup rows** remain recorded. Later candidate discovery does not rewrite the original query result.
- NatMed extraction/source support is technically checked; all 1,269 annotations retain pending review and `clinical_approval=false`. Source attribution is not clinical approval.
- Preserve quantity discrepancies, unknowns, product distinctions and Reddit direct-versus-inherited context. No automatic canonical product merge or product-level effectiveness inference.
- Coverage is limited to saved sources. Unresolved mappings can reduce retrieval recall; missing links do not establish absence of a real-world relationship.

## 7. Retrieval evaluation completed

- [KG_Retrieval_and_Evaluation.ipynb](notebooks/KG_Retrieval_and_Evaluation.ipynb) records a Python evidence-retrieval baseline using supplied categories and IDs, not free-form LLM question answering.
- **Role in schema design:** these were post-construction checks of evidence retrieval and intended schema distinctions, not the original 10 design questions. A failure can indicate a schema gap, missing data/link or a retrieval-rule error; retrieval scores alone do not establish schema completeness.
- **42 development cases = 30 original + 12 additional:** the original set contained 10 label-warning cases, 10 NatMed evidence cases and 10 interpretation/boundary cases (for example, serving basis, identity scope, unknown values and Reddit context). The additional set contained 10 label-warning and two NatMed cases. Once used to improve retrieval rules, those 12 diagnostic cases became development data.
- Each case specifies a structured request, expected evidence IDs and behavior checks. Full records: [original 30 cases](data/evaluation/evaluation_cases_v1.json) and [additional 12 cases](data/evaluation/additional_evaluation_cases_v1.json). The [evaluation notebook](notebooks/KG_Retrieval_and_Evaluation.ipynb) explains the workflow; [revision comparison](data/evaluation/retrieval_v3_comparison/comparison.json) records detailed scores and errors.
- Revision v3 scored 100% macro precision/recall where defined on the 42 development cases; [six further diagnostic cases](data/evaluation/additional_evaluation_cases_v2.json) scored 100% precision and 89.3% recall, with two missed adult-use statements.
- These are small, assistant-reviewed relevance sets, not an independent clinical benchmark. Empty-evidence cases have undefined metric denominators where appropriate.
- Evaluations remain pinned to the earlier **statements** graph. They have not been rerun against the latest concept-link revision. Rule tuning is paused; preserve these cases and limitations for future comparison.

### Existing-text audit before indexing

- Checked NatMed/Reddit passage coverage and boundaries, and DSLD statement lengths. No missing words or nonempty sections were found relative to the captured NatMed/Reddit source text; this does not prove website-capture completeness.
- With the pinned MedCPT tokenizer and special tokens, **two NatMed passages and one Reddit passage exceeded 512 tokens**; all DSLD statements fit. Recheck after final context templates are selected.
- Some clinical excerpts/qualifiers span passages, and short Reddit comments need thread context. Preserve graph links and fetch supporting context; no chunks or KG records were changed.
- PubChem/RxNorm/MeSH primarily need searchable concept fields, not blanket passage chunking. [Full audit and examples](reports/retrieval_chunk_audit/Review.md) · [Measurements](reports/retrieval_chunk_audit/summary.json). The report's originally proposed saved corpus is optional under the current indexing plan below.

## 8. Which folders to use

| Location | Current role |
|---|---|
| `data/raw/` | Preserved collected inputs; do not overwrite during processing |
| `data/processed/` | Source preparation plus cumulative mapping/review stages; there is no single latest folder for every source |
| `data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9/` | Latest complete KG export |
| Other `data/graph/full-graph-*` and `pilot-*` | Historical snapshots; navigation added topic links, statements preserved all DSLD text, concepts added 34 mappings |
| `schemas/` | Versioned record contracts, preparation rules and graph extensions; older names can still be active dependencies |
| `reports/` | Supporting reviews and handoff inventories; read their graph version before interpreting findings |

Principal processed inputs/decision layers:

- DSLD: `data/processed/dsld/dsld-normalized-v1-66adbe28c3b0344457fb/`.
- PubChem/RxNorm/MeSH: `data/processed/terminology/terminology-prepared-v1-f8afbddf6af7037ac98e/`.
- NatMed/Reddit: `data/processed/imported/natmed-reddit-prepared-v1-b85118347d2f8de1a1ea/`.
- Identity review: `data/processed/identity/identity-duplicates-v1-3aa86ab20b94fd928b6b/`.
- Base mappings: `data/processed/identity/ingredient-decisions-v1-1e02682e87ad7456218b/`.
- Context candidates: `data/processed/identity/contextual-candidates-v1-04577ddde5348c406ee2/`.
- Latest mapping decisions: `data/processed/identity/general-concept-decisions-v1-8613b59b7b926ebc30c0/`.

The latest decision layer supplements the base mappings. Do not delete/move historical files without checking provenance dependencies and pinned hashes.

## 9. Team handoff

- **Completed:** a selective KG handoff was pushed to GitHub's `main`; the development branch was not merged wholesale. The published package supports consuming/validating the KG; rebuilding its history requires development inputs.
- The [published inventory on main](https://github.com/Seemant-ujjain/SupplementRx-AI-Conversational-Agent/blob/main/reports/kg_handoff_file_list.json) lists **479 data/schema files, about 500.5 MB**. Documentation and the validator are additional support files. The local 484-file [proposal](reports/kg_handoff_file_list.json) is historical, not the final published inventory.
- `main` contains a concise schema reference and a standalone handoff validator. The `preprocessing-kg-schema` branch retains construction notebooks, historical specifications, audits and experiments. Relative evidence paths must remain intact.
- This local development README and the concise [main README](https://github.com/Seemant-ujjain/SupplementRx-AI-Conversational-Agent/blob/main/read.md) serve different audiences. The schema-bounds and design/evaluation explanations are maintained on `preprocessing-kg-schema`; publishing development updates does not automatically update main.
- Reports are supporting history: `KG_Readiness_Review` describes the earlier statements graph; `Contextual_Mapping_Review` describes candidate discovery; `General_Concept_Mapping_Update` describes the latest 34 links. Check the graph version before interpreting results.

## 10. Next work — aligned with the proposal

1. **Prepare indexing inputs directly from the current KG:** choose source-specific text fields/templates, attach identifying context, handle token limits without silent truncation, and retain index-entry-to-KG/source mappings. Reuse existing preprocessing and passages; keep the frozen graph unchanged. Saving prepared text as a separate retrieval dataset is **optional**.
2. **Build entity lookup and BM25:** use identifiers, preferred names, synonyms and accepted mappings, preserving ambiguous matches. BM25 is keyword search and does not require embeddings.
3. **Generate MedCPT embeddings and build FAISS indexes:** encode evidence with the article encoder and questions with the query encoder. Pin model/KG versions and record text preparation and index mappings. See the [official implementation](https://github.com/ncbi/MedCPT).
4. **Combine and rerank:** use Reciprocal Rank Fusion for keyword/semantic results; evaluate cross-encoder reranking and retrieval of linked supporting context.
5. **Connect Neo4j and an open-source LLM:** validate imported counts/IDs, add bounded graph queries, and generate answers with citations, source distinctions, uncertainty and abstention.
6. **Evaluate the baseline:** prepare independently reviewed tuning/test question/evidence splits; keep the test set held out. Compare keyword-only, semantic-only and hybrid retrieval using precision/recall, identity errors, citation support, qualifications and latency. Historical rule-baseline results are not results for this pipeline.
7. **Later experiments:** test Louvain communities for graph analysis/optional retrieval expansion; it is not required for initial search. Consider supervised RGCN ranking only after defining the task and obtaining checked training examples, then compare it with the text/evidence baseline.

The proposal's UMLS/MetaMap workflow has not been implemented. Document the actual PubChem/RxNorm/MeSH approach rather than claiming full UMLS normalization. Retain unresolved mappings for targeted follow-up when evaluation exposes consequential gaps.

## Local entry points

- **Handoff users on `main`:** run `python3 scripts/validate_kg_handoff.py` from the repository root. That branch's validator uses Python's standard library; the original developer environment is not required. It is not included in this development checkout.
- **Existing development environment:** `source supplementsrx_env/bin/activate` works only if that local environment already exists. It is not distributed through GitHub.
- **New development environment:** create one with `python3 -m venv supplementsrx_env`, activate it, then install dependencies for the workflow you will run. `python -m pip install -r requirements-audit.txt` installs the pinned JSON-schema audit dependency only; it is not a complete environment specification for all notebooks or future embedding work.
- **Schema-bounds check on this branch:** `python3 scripts/validate_schema_bounds.py` uses the standard library and writes its validation report without changing the KG.
- Tests: `python -m unittest discover -s tests -q`.
- Latest mapping/export revision: `python scripts/apply_general_concept_mappings.py` (requires the development inputs, not merely the reduced handoff).
- Collection notebooks: [DSLD](notebooks/DSLD_Data_collection.ipynb), [PubChem](notebooks/PubChem_Data_Collection.ipynb), [RxNorm](notebooks/RxNorm_Data_Collection.ipynb), [MeSH](notebooks/MeSH_Data_Collection.ipynb). Inspect previews before saving; terminology collectors default to `SAVE_DATA = False`.
- `merged_supplements.csv` is obsolete and is not an input to this workflow.
