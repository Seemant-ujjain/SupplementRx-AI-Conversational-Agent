# Current KG review

**Outcome:** structurally ready for scoped research use, with documented limitations. This is not clinical approval or a claim of complete source coverage.

- Current graph: `data/graph/full-graph-statements-v1-27c544f4940e7162944c/`.
- Freeze record: `data/graph/poc-statements-release-v1-684ce1012b4f76e0af1a/`.
- Machine-readable findings: `reports/kg_readiness_review.json`.
- Reproduce: `supplementsrx_env/bin/python scripts/review_current_kg.py`.
- Review reads existing inputs and graph files; it writes only the separate review report. No graph, source data, mapping decisions or clinical statuses were changed.

## Representation

| Source | Current representation |
|---|---|
| DSLD | 400 label snapshots, 5,438 ingredient occurrences, 400 serving nodes; all 6,462 captured label statements preserved |
| PubChem | 239 chemical compound nodes |
| RxNorm | 287 terminology concept nodes |
| MeSH | 2,360 terminology concept nodes |
| NatMed | 10 monographs, 1,269 pending claim annotations, source passages/excerpts and reference documents |
| Reddit | 287 posts and 4,593 comments; direct mentions and inherited thread context kept separate |

Total: **35,998 nodes and 74,088 relationships**. Node presence does not imply an approved mapping. Additional node types preserve source passages, excerpts, references and supplement topics.

## Checks completed

- Current file hashes, input hashes and freeze record agree; counts agree with the manifest.
- Unique node/edge/evidence identifiers; no dangling relationship endpoints or missing evidence references.
- All 64,278 evidence pointers resolve to hash-verified saved inputs; original values match where stored.
- All 1,269 claim excerpts and 2,923 field-support anchors match their source spans. This checks extraction support, not clinical correctness.
- All 6,462 saved DSLD statements remain reachable from their labels, including marketing and disclaimers.
- Re-ran base mapping eligibility, navigation-extension and statement-preservation checks. Base nodes/edges remain unchanged; current edges match the statement-extension result.
- All 3,039 accepted mapping edges correspond to eligible High-confidence decisions with their intended relationship type and endpoints.
- No product-to-clinical-claim inference or automatic canonical product merge was introduced.

## Coverage across the ten supplements

| Topic | Navigable labels | Monographs | Pending claims | Direct Reddit records |
|---|---:|---:|---:|---:|
| Ashwagandha | 40 | 1 | 73 | 148 |
| Creatine | 40 | 1 | 76 | 198 |
| Iron | 46 | 1 | 89 | 150 |
| Magnesium | 188 | 1 | 168 | 384 |
| Melatonin | 40 | 1 | 159 | 135 |
| Omega-3 | 40 | 1 | 177 | 147 |
| Probiotics | 40 | 1 | 92 | 91 |
| Turmeric | 43 | 1 | 146 | 109 |
| Vitamin B12 | 56 | 1 | 96 | 143 |
| Vitamin D | 52 | 1 | 193 | 167 |

Labels and Reddit records can appear under multiple topics. Label navigation includes declared groups and literal ingredient/title mentions; it does not prove exact formulation applicability, ingredient presence or clinical relevance. All ten topics have these navigation paths, but this does not establish complete terminology or clinical coverage.

## Outstanding limitations and decisions

| Area | Finding | Decision for this KG |
|---|---|---|
| Mapping ambiguity | 4,166 Medium-confidence rows pending scope review; 48 Low-confidence exact matches excluded | Preserve review records; do not promote them to accepted identity links |
| Missing candidates | 4,207 lookup rows: PubChem 1,573, RxNorm 1,310, MeSH 1,324 | Preserve unresolved state; do not fabricate matches |
| NatMed | 1,269 annotations pending clinical review; 10 source-capture review rows | Allow attributed source retrieval with review status; do not present annotations as clinically approved facts |
| Ingredient-to-NatMed linkage | 1,823 rows have no saved subject-name/group bridge | Keep absent links explicit; topic navigation does not repair ingredient identity |
| DSLD | 2,845 issue rows retained, including references outside the selected collection | Preserve source discrepancies and unknowns; do not silently correct them |
| Reddit references | 99 missing-identifier and 113 outside-collection rows | Retain incomplete context explicitly; do not treat thread context as direct personal evidence |
| Deduplication | Source identities retained; no canonical product merges | Equivalent mass or repeated text alone does not establish identical formulation or independent corroboration |
| Retrieval | Two adult-use statements missed in the latest diagnostic evaluation | Evidence is present in the KG; retain as baseline retrieval limitations, without further rule tuning |

Review rows can overlap and are not counts of unique defective records. The MeSH, RxNorm and PubChem counts alone do not establish which source has the highest error rate.

## Readiness decision

- **Ready:** continued research, schema inspection, evidence tracing and controlled downstream prototyping using the documented source/review distinctions.
- **Not established:** clinical correctness, complete mapping recall, exact product equivalence, real-world medical recommendation quality or external source completeness.
- **Before team handoff:** prepare a minimal package and check its provenance dependencies. The evidence currently references raw/prepared files by repository path; copying only node/edge CSVs would not preserve independently resolvable source evidence.
- Keep historical builds locally for reproducibility. No re-freeze or rebuild is needed solely because of this review.
