# Context-based mapping candidate review

**Implemented:** discovery and review prioritization using explicit ingredient context and related saved queries. This extends candidate review; it does not approve new identity relationships or update the frozen KG.

## Rules

- Use each occurrence's name and explicit plant-part/genus/species notes. Keep the complete original attributes and evidence IDs.
- Consider saved queries sharing a bounded name family only when their scope qualifiers are supported by that occurrence. Preserve brands, chemical salts, quantities and other unrecognized qualifiers.
- Compare target scope separately. A successful query is not evidence that its target has the same preparation scope.
- Prioritize aligned active RxNorm targets for review. Missing qualifiers, whole/root ambiguity, multiple equally aligned targets, MeSH definition/status questions and PubChem structure specificity remain unresolved.
- Block preference for conflicting parts/forms or unsupported allergenic preparations. Preserve all earlier accepted and excluded decisions.
- Ranking is review order, not mapping approval. All new relationships remain unapplied.

## Results

| Measure | Result |
|---|---:|
| Source ingredient occurrences examined | 5,438 |
| Earlier terminology decisions preserved | 6,735 |
| New occurrence–candidate pairs | 316 |
| Occurrences with additional candidates | 127 |
| PubChem / RxNorm / MeSH additions | 59 / 121 / 136 |
| Medium, pending scope review | 295 |
| Low, excluded from exact matching | 21 |
| Highest review priority among new candidates | 13 |
| Previously no-candidate occurrence/source pairs with new proposals | 110 |
| Newly approved identity links | 0 |

The 110 pairs are newly discoverable candidates, not 110 resolved mappings. Historical 4,207 no-candidate rows still correctly describe the original queries. Review-row counts are not unique ingredient counts.

## Ashwagandha example

Seven occurrences named `Ashwagandha extract` have explicit root context and gain the saved RxNorm candidate `Withania somnifera root extract` (1309279). It has higher review priority than the original `whole extract` candidate (1876359), whose scope remains unresolved. Standardization and preparation details still require review; no root-specific qualifier was inferred from the ingredient name alone.

The rule also surfaces root-extract candidates for six turmeric occurrences. It is not an Ashwagandha-specific exception. Unsupported allergenic-extract candidates remain excluded from exact matching.

## Artifacts and next use

- Rules: `schemas/contextual_mapping_review_v1.json`.
- Reproduce: `supplementsrx_env/bin/python scripts/expand_contextual_mapping_candidates.py`.
- Output: `data/processed/identity/contextual-candidates-v1-04577ddde5348c406ee2/`.
- `new_candidates.jsonl`: new proposals, original attributes, explicit context, discovery queries, provenance and reasons.
- `candidate_comparisons.jsonl`: original versus additional candidates, ranked for review, with prior decision IDs retained.
- `review_report.json`, `input_manifest.json`, `manifest.json`: totals and reproducibility hashes.
- Notebook: appended context-candidate review section in `notebooks/Schema_Design_and_Mapping.ipynb`.

Next, review the higher-priority proposals and specify an appropriate relationship before exporting a new KG version. The current graph and earlier decision files remain unchanged. This is a bounded discovery improvement, not exhaustive synonym resolution; a proposal absent from this run is not evidence that no suitable candidate exists.
