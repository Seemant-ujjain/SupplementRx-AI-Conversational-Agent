# General ingredient-concept mapping update

**Applied 34 DENOTES_CONCEPT links to a new graph version.** The rule assesses the entire original review pool and the contextual candidate additions; it is not limited to the 13 highlighted examples.

## Rule and scope

Require an active RxNorm ingredient concept, explicit compatible plant part and preparation, and a saved exact query-to-target identity bridge with matching scope. Conflicting or competing targets stay pending; prior exclusions are preserved. Standardization, concentration and branded preparation details remain on the original ingredient occurrence. They do not prevent linking to a more general ingredient concept, but are never propagated to that concept.

The rule does not establish exact material, formulation, brand, product or clinical equivalence. It is user-authorized rule assessment, not individual human or clinical review. PubChem structure matching, MeSH broader/narrower relations and NatMed subject links require separate evidence rules.

## Before and after

| Item | Outcome |
|---|---:|
| Original review rows assessed | 4,214 (4,166 pending + 48 excluded) |
| Additional contextual candidate rows assessed | 316 |
| Original pending rows promoted | 21 |
| Additional contextual rows promoted | 13 |
| New DENOTES_CONCEPT relationships | 34 |
| Original pending rows remaining | 4,145 |
| Original exclusions retained | 48 |
| Additional contextual rows still pending | 282 |
| Additional contextual exact-match exclusions retained | 21 |

The 4,207 original no-candidate query rows are historical lookup outcomes and remain unchanged. A new candidate discovery or concept link does not rewrite what the original query returned. The graph manifest's `pending_or_excluded_mappings` counts the original queue (4,193); contextual candidate dispositions are separately recorded in `review/general_concept_decisions.jsonl`. Across both assessed pools, 4,427 rows remain pending and 69 excluded. These are candidate/occurrence rows, not unique ingredients.

## Accepted cases

| Ingredient family | Newly linked occurrences |
|---|---:|
| Ashwagandha | 16 (9 original + 7 contextual) |
| Turmeric | 14 (8 original + 6 contextual) |
| Green tea | 1 |
| Chicory | 1 |
| Milk thistle | 1 |
| Garcinia cambogia | 1 |

The two original Ashwagandha/Turmeric general-name examples were resolved through explicit root information and saved exact root-extract query bridges. Their percentages and branded names remain unchanged on source occurrences.

## Files and validation

- Rule: `schemas/general_concept_mapping_v1.json`.
- Reproduce: `supplementsrx_env/bin/python scripts/apply_general_concept_mappings.py`.
- Decisions: `data/processed/identity/general-concept-decisions-v1-8613b59b7b926ebc30c0/`.
- **Latest graph:** `data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9/`.
- Freeze: `data/graph/poc-concepts-release-v1-9250419f3c2fc93805f9/`.
- Graph totals: **35,998 nodes, 74,122 relationships**.
- All existing nodes and relationships preserved; only 34 mapping edges and their decision evidence were added. All 1,269 clinical annotations remain pending.
- Verified graph hashes, unique IDs, valid endpoints, evidence references, decision pointers, mapping relations, and absence of product-clinical inference.
- Earlier graph, readiness review and retrieval evaluation remain historical snapshots. The retrieval scripts intentionally stay pinned to their evaluated graph; this update does not claim re-evaluated retrieval metrics.
- `review/contextual_candidates.jsonl` preserves discovery history; `review/general_concept_decisions.jsonl` records the updated dispositions.

## Why thousands remain

This rule resolves one well-supported class: general ingredient concepts with explicit matching plant part and preparation. It does not justify converting chemical structures, broad taxonomy terms or insufficiently qualified names into identity matches. Address remaining cases by their reason and intended relationship, rather than lowering confidence thresholds to reduce the queue.
