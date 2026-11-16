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
| [Package inventory](reports/kg_handoff_file_list.json) / [path list](reports/kg_handoff_file_list.txt) | 479 data/schema files, about 500.5 MB, needed for the evidence-preserving handoff |
| Referenced `data/raw/` and `data/processed/` files | Resolve citations, original values, text spans and mapping decisions |

Keep relative paths intact. The 479-file inventory covers selected data and the current schema reference; this README, validator and inventory files are additional support files. Existing collection files on `main` are retained; not every existing repository file is part of the handoff inventory.

## Validate locally

From the repository root, using Python 3 and its standard library:

```sh
python3 scripts/validate_kg_handoff.py
```

The validator checks selected-file hashes, graph counts, unique IDs, endpoints, evidence references, **64,312 source pointers**, **1,269 claim excerpts**, and **2,923 field-support anchors**. It does not need the development virtual environment, earlier graph builds or exploratory notebooks.

Only `schemas/current_kg_reference.json` is included on `main`. The six historical processing/mapping specifications remain on `preprocessing-kg-schema`; their frozen lineage references are intentionally preserved.

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
- Next: reuse the current KG to build keyword and semantic indexes after the small indexing-preparation step below; compare BM25, MedCPT + FAISS and fusion/reranking; import Neo4j and add bounded graph retrieval; integrate the open-source LLM with citations, evidence checks and abstention.
- Louvain is a separate broad-query experiment. Question-aware R-GCN ranking is an optional extension requiring checked training preferences and comparison against text/evidence baselines.
- Further mappings can be addressed when evaluation identifies consequential gaps; no complete manual resolution of the pending pool is required before the POC.

## Planned embedding stage — not yet implemented

**First build text embeddings for evidence retrieval.** These are different from learned GNN/RGCN representations. Use the pretrained [MedCPT query encoder, article encoder and cross-encoder](https://github.com/ncbi/MedCPT) according to their intended roles; pin model revisions and evaluate on our supplement corpus before choosing final settings. No model fine-tuning is required for the initial retrieval experiment.

### Already completed versus remaining work

- **Already completed:** dataset audits, POC field selection, structured normalization, KG construction, source links and review metadata. NatMed and Reddit passages already exist in the KG; DSLD has structured label statements. Reuse these rather than restarting preprocessing.
- **Remaining indexing preparation:** choose the exact fields/text template for each source (for example, ingredient + section + passage); check token limits after adding context; split oversized text without silent truncation. Decide which supporting context is included in the text and which is fetched through graph links after retrieval.
- **Scope:** index useful passages, statements, names and synonyms, not every node or raw node JSON. PubChem, RxNorm and MeSH generally need searchable concept records rather than passage chunking; check long descriptions separately.
- **Traceability:** map every search/vector entry to stable KG node IDs and source metadata. Preserve distinct forms, ambiguous mappings, citations and pending review status.
- **Separate retrieval dataset is optional:** read and prepare text directly from the KG when building indexes. Saving that prepared text as JSONL is an optional reproducibility aid, not a new KG or a prerequisite. Keep the current graph export unchanged.

### What to encode

| Content | Representation and source separation |
|---|---|
| NatMed passages/excerpts | Title, section and source text; preserve population, modality, dose context, citations and annotation review status |
| DSLD label statements | Product/ingredient context plus original statement text; keep label claims distinct from clinical evidence |
| Reddit posts/comments/passages | Separate discussion index, explicitly user-reported; retain direct versus inherited context |
| Terminology labels/aliases | Optional separate entity-linking index; similarity proposes candidates, never approves identity mappings |

- Encode evidence text with the **article encoder** and incoming questions with the **query encoder**, following the model's input and pooling conventions. Do not substitute raw serialized node JSON for readable evidence text.
- Choose chunking/token limits before encoding. Retain source offsets and parent passage IDs; avoid losing qualifying sentences through truncation or splitting.
- Every chunk needs a stable ID, text hash, source, source record/passage IDs, associated graph node IDs, evidence IDs and review status. Several nodes may reference the same text; vector reuse must not erase separate provenance.
- Use the same chunk IDs for lexical and dense retrieval so results can be fused reliably. FAISS vector positions must resolve through an explicit row mapping, never an assumed graph CSV row order.
- Metadata filters and graph traversal enforce source/scope distinctions. A high similarity score is not clinical confidence or evidence that two ingredients are identical.

### Proposed storage layout

Create only the artifacts needed when implementing retrieval. The saved text corpus under `data/retrieval/` is optional; indexes still require entry-to-KG mappings and manifests recording source hashes and text preparation. Keep all generated artifacts outside the frozen graph export:

```text
data/retrieval/                    # OPTIONAL saved prepared text
  <corpus-version>/
    corpus_manifest.json           # Graph version, source hashes, chunking policy
    natmed/chunks.jsonl
    dsld/chunks.jsonl
    reddit/chunks.jsonl

data/embeddings/
  <embedding-run-id>/
    manifest.json                  # KG/text hashes, templates, encoder/revision, dimensions
    bm25/                          # Keyword index and entry-to-KG mapping; no embeddings
    natmed/
      vectors.npy                  # One vector per indexed chunk
      row_mapping.jsonl            # vector_row -> chunk_id -> graph/evidence IDs
      index.faiss
    dsld/                          # Same three files
    reddit/                        # Same three files; separate evidence role

data/evaluation/
  <evaluation-version>/
    questions.jsonl                # Question, expected evidence, split/group IDs
    retrieval_results.jsonl        # Ranked chunk IDs, source and method
    metrics.json                   # Recall@10, MRR and related measures
```

- Record exact model revisions, text templates, pooling, token limits, vector dimensions, normalization, similarity metric, FAISS settings, software versions and checksums. Choose and document compatible settings rather than assuming cosine or inner product is interchangeable.
- Validate row counts, finite vectors, unique chunk IDs, source/graph references and index dimensions. Check nearest-neighbor examples before evaluating the whole pipeline.
- For new data, encode new/changed chunks with the same pinned encoder and refresh their row mappings/index. If the encoder or text template changes, create a new version and re-encode the affected corpus. Never silently mix incompatible embedding runs.
- Neo4j stores the graph; FAISS is the proposal's initial vector index. Retrieve chunk IDs from FAISS, resolve graph IDs, then perform bounded Neo4j traversals for related evidence. Neo4j vector indexing can be evaluated later as an alternative, not an additional mandatory duplicate index.

### Implementation and evaluation order

1. Read selected content from the current KG and apply the indexing preparation above. Use reusable scripts and a separate retrieval notebook; preserve the construction notebooks and frozen graph.
2. Build entity lookup from identifiers, preferred names, synonyms and accepted mappings; retain ambiguous/unresolved matches.
3. Build the **BM25 keyword index (no embeddings)**, then generate **MedCPT text embeddings and FAISS vector indexes**. Both return entries linked to KG nodes; a saved intermediate corpus is optional.
4. Combine lexical and dense rankings with Reciprocal Rank Fusion; evaluate cross-encoder reranking separately. Fetch linked supporting context as needed.
5. Connect Neo4j graph queries and the open-source LLM for cited answers, preserving source distinctions, qualifications and uncertainty.
6. Evaluate lexical-only, dense-only and hybrid retrieval using independently reviewed tuning/test questions. Keep duplicate/thread families together and do not tune on held-out questions. Measure precision, recall/ranking, citation support, identity errors, qualification preservation, abstention and latency. Earlier Python rule-baseline scores are not results for this pipeline.
7. Explore Louvain communities and supervised RGCN ranking later. Neither is required to build the initial indexes; test their benefit against the baseline before adopting them.

### Optional RGCN extension

If a supervised graph experiment is adopted, create a separate versioned graph projection with node-ID mappings, directed relation-ID mappings, node features, edge text/features, split IDs and checked response-preference labels. Store checkpoints and training metadata under a separate `models/` run directory. Select meaningful relation types; do not automatically treat every provenance link or vocabulary hub as clinical reasoning evidence.

For the question-aware architecture in the supplied guide, frozen text vectors may be cached, but GNN-updated node states depend on both the question and trained weights. They are not one permanent `rgcn_embeddings.npy` for all questions. Train only after establishing a task and checked supervision, and compare against text/evidence baselines before claiming a benefit.
