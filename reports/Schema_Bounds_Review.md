# Retrospective lower- and upper-bound schema

## Definitions and design basis

This formalizes the existing audit-driven, POC-guided design; bounds were not the original construction method. The definition agreed for this project is:

- **Lower bound:** minimum representational capabilities needed for the selected POC question families, expressed as required types, relationships, properties and scoped cardinalities.
- **Upper bound:** the full permitted vocabulary for this POC version, including node types, directed endpoint pairs, CSV fields and top-level property types.
- The lower-bound vocabulary is a subset of the upper-bound vocabulary. This does **not** mean every node needs every relationship, every ingredient needs a terminology match, or every clinical field needs a known value.

Design evidence: `notebooks/Schema_Design_and_Mapping.ipynb` (Step 1 question/field review and later identity/provenance rules), `data/evaluation/retrieval_questions_v1.json` (historical question families), and the current graph export. Historical evaluation questions are used to identify requirements, not to claim fresh retrieval scores.

The machine-readable specification is [kg_schema_bounds_v1.json](../schemas/kg_schema_bounds_v1.json). It is a project specification, not an RDF/OWL ontology or a JSON Schema document. Nested source structures remain governed by existing source/processing contracts; this additional layer does not validate every nested source key.

## Lower bound: 14 node types, 20 relationship types

| Question family | Required capabilities |
| --- | --- |
| Product composition/comparison | ProductLabel and IngredientOccurrence; retain declarations, forms, components and standardization distinctions |
| Amount, usage and label warnings | LabelAssertion and Serving connected to the label and, where applicable, its ingredient occurrence and serving basis |
| NatMed effectiveness, safety, interactions and dose context | Monograph, MonographSubject, ClinicalClaim, SourceExcerpt and SourcePassage, with source support, field-state information and pending review |
| Terminology/chemical identity | TerminologyConcept and ChemicalCompound; preserve concept denotation versus exact-material match and original occurrence identity |
| User experiences | RedditPost, RedditComment and SourcePassage, with thread/reply context; ExternalRecordReference preserves uncaptured targets |

These are a scoped engineering minimum for our chosen source-preserving representation, not a mathematically unique minimal schema. Safety/interactions, populations, quantities and ratings can be properties of assertions; they do not require newly invented disease, drug or dose nodes.

Examples of enforceable requirements:

- Each current product label has one serving node, at least one declared occurrence and at least one assertion.
- Each clinical claim belongs to one monograph, has one subject link and one supporting-excerpt link; its required clinical keys may contain null values.
- Every passage links to one source record. Reddit comments have one collected or external thread target; a parent reply link is optional when unavailable.
- Node and relationship IDs are unique, endpoints exist and evidence IDs resolve. Accepted mapping edges have High confidence and mapping IDs.
- This frozen profile preserves pending clinical review, user-report evidence roles and unloaded external references.

These cardinalities describe this POC profile. Future multi-serving product representations or review-state transitions require explicit versioning, not silent changes to this frozen specification.

## Upper bound: 16 node types, 33 relationship types

The upper bound adopts the complete current export vocabulary, including its observed endpoint combinations and top-level property types. This is a deliberately conservative, versioned allowance; an observed schema does not independently prove scientific adequacy.

Beyond the lower bound it permits:

- **SupplementTopic** and navigation associations for label titles, ingredient names, source topics and direct versus inherited Reddit topics.
- **ReferenceDocument** and monograph reference-document links.
- MeSH relations, category membership, qualified ingredient/botanical subject links, and source label relations/references.

These structures remain useful and remain in the graph. “Outside the lower bound” means the minimum attributed-answer representation does not require them, not that they should be removed. Source citations and evidence pointers are still required where applicable; a standalone ReferenceDocument node is an additional representation. Cross-source navigation is permitted but never implies that a general clinical claim applies to a specific product.

New node types, relationship types, endpoint combinations or top-level properties require a revised upper-bound version. We do not include speculative future GNN or embedding nodes in this initial version.

## Findings from the current graph

- **Pass:** all 14 lower-bound node types and 20 relationship types are represented; scoped required-property and cardinality checks pass.
- **Pass:** all **35,998 nodes and 74,122 relationships** conform to the adopted upper-bound vocabulary and endpoint/property checks.
- **Pass:** identifiers, endpoint existence and references to **64,312 evidence records** pass; all **3,073 mapping relationships** retain High confidence and mapping IDs. This run does not independently re-adjudicate mapping meanings.
- **Preserved uncertainty:** all **1,269 clinical claims remain pending**, with clinical approval false.
- **Explicit null values:** population in **1,103** claims; safety rating in **1,222**; indication and effectiveness rating in **460** each. These fields are not applicable to every claim type, so these counts are not a clinical completeness score. Nested dose/interaction completeness was not newly evaluated by this check.
- **No graph edits:** hashes of all **48 files** in the graph directory remained unchanged and declared manifest file hashes match.

Schema conformance establishes representation and structural validity. It does not establish clinical approval, complete source capture, complete terminology mapping, per-supplement answer coverage or end-to-end retrieval performance. Those remain separate evaluations.

## Reproduce

```sh
python3 scripts/validate_schema_bounds.py
```

Only the report at `reports/schema_bounds_validation_v1.json` is written. The validator reads the frozen specification and graph; it does not regenerate the specification from whatever input it is asked to validate. Future scope changes require intentional specification review.
