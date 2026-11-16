# SupplementRx AI — KG handoff

The POC graph is constructed for the ten supplement categories: Magnesium, Vitamin D, Ashwagandha, Melatonin, Omega-3, Vitamin B12, Iron, Turmeric, Probiotics and Creatine. It combines DSLD, PubChem, RxNorm, MeSH, NatMed and Reddit.

**Latest graph: [full-graph-concepts-v1-08c99550a0fa0f86aca9](data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9/).** It contains **35,998 nodes, 74,122 relationships, 16 node types and 33 relationship types**. It has not yet been imported into Neo4j; embeddings and the conversational answering system remain future work.

## Files to use

| File/folder | Purpose |
|---|---|
| Latest graph `nodes/*.csv` | One file per node type |
| Latest graph `relationships/relationships.csv` | Directed links between stable node IDs |
| Latest graph `provenance/evidence.jsonl` | Source/decision evidence and file pointers |
| Latest graph `review/` | Mapping decisions, exclusions and unresolved issues |
| Latest graph manifests and validation report | Version, file integrity, lineage and validation |
| [Release records](data/graph/poc-concepts-release-v1-9250419f3c2fc93805f9/) | Freeze reference for this graph |
| [Current schema reference](schemas/current_kg_reference.json) | All node/relationship types, CSV columns, observed endpoint types and semantics |
| [Package inventory](reports/kg_handoff_file_list.json) / [path list](reports/kg_handoff_file_list.txt) | 484 data/schema files, about 500.5 MB, needed for the evidence-preserving handoff |
| Referenced `data/raw/` and `data/processed/` files | Resolve citations, original values, text spans and mapping decisions |

Keep relative paths intact. The 484-file inventory covers selected data and versioned schemas; this README, current schema reference, validator and inventory files are additional support files. Existing collection files on `main` are retained; not every existing repository file is part of the handoff inventory.

## Validate locally

From the repository root, using Python 3 and its standard library:

```sh
python3 scripts/validate_kg_handoff.py
```

The validator checks selected-file hashes, graph counts, unique IDs, endpoints, evidence references, **64,312 source pointers**, **1,269 claim excerpts**, and **2,923 field-support anchors**. It does not need the development virtual environment, earlier graph builds or exploratory notebooks.

The graph's `input_manifest.json` records historical build lineage. Some build-time inputs are intentionally excluded from this consumption package; rebuilding all stages requires the development branch. Structural/source-support validation is not clinical approval.

## Reading records

- Node columns: `id`, `type`, `properties_json`, `evidence_ids`.
- Relationships also contain `start_id`, `end_id`, `mapping_id` and `confidence`.
- Parse `properties_json` and `evidence_ids` as JSON. Nested objects are not automatically native Neo4j properties; define the import representation before loading.
- Example: an Ashwagandha root-extract occurrence can `DENOTES_CONCEPT` the RxNorm root-extract concept (1309279). The occurrence retains KSM-66/withanolide details; the link does not assert exact material or branded-product equivalence.
- The graph preserves all 400 DSLD labels and 6,462 captured statements, including marketing/disclaimers, as attributed source text.

## Decisions and limitations

- Original values, unknowns, quantities, preparation qualifiers, provenance and source identities are preserved. Equivalent amounts or repeated names do not automatically merge products.
- Mapping confidence describes a specific relationship, not medical certainty. The latest revision added 34 general-concept mappings; it did not approve clinical claims.
- **Original mapping pool:** 4,145 pending and 48 excluded rows. **Additional contextual pool:** 282 pending and 21 excluded. These are candidate/occurrence rows, not unique ingredients. Historical discovery records remain unchanged; `review/general_concept_decisions.jsonl` contains updated dispositions.
- The 4,207 no-candidate lookup rows record original query outcomes; later discovery does not rewrite them. Missing graph links do not establish absence of a real-world relationship.
- All 1,269 NatMed annotations retain pending review and `clinical_approval=false`. Preserve original excerpts and qualifications when retrieving them.
- Topic navigation is not ingredient identity. Reddit direct mentions and inherited thread context remain distinct and are not clinical evidence.
- NatMed Fish Oil and Lactobacillus acidophilus monographs must not be generalized to every Omega-3 or probiotic product. NatMed is licensed material; retain existing private-access handling.
- PubChem, RxNorm and MeSH are separately collected terminology sources, not a downloaded UMLS Metathesaurus or implemented MetaMap pipeline.

## Development history and next steps

- The `preprocessing-kg-schema` branch retains construction notebooks, scripts, historical snapshots, audits and retrieval experiments. This handoff does not merge that branch wholesale.
- Earlier Python retrieval evaluations used a previous graph and supplied categories/IDs, not general LLM answering; they do not establish this graph's clinical accuracy or end-to-end performance.
- Next: prepare source-linked passages and reviewed question splits; compare BM25, MedCPT + FAISS and fusion/reranking; import Neo4j and add bounded graph retrieval; integrate the open-source LLM with citations, evidence checks and abstention.
- Louvain is a separate broad-query experiment. Question-aware R-GCN ranking is an optional extension requiring checked training preferences and comparison against text/evidence baselines.
- Further mappings can be addressed when evaluation identifies consequential gaps; no complete manual resolution of the pending pool is required before the POC.
