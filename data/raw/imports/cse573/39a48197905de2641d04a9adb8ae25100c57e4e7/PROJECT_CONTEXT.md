# CSE573 — SupplementsRx AI project context

Updated October 27, 2026. This file consolidates the user-supplied proposal,
data-source guidance, subscription context, and decisions made during the
collection work. Proposal material below is a structured summary of the supplied
PDF, not a claim that its planned system has already been implemented.

## Source material supplied by the user

1. **`Proposal.pdf`** — “SupplementsRx AI: Conversational Agent,” Arizona State
   University. Authors: Onkar Vachista Falle, Ashish Kurse, Jason Lu, Aryan
   Srivastava, and Seemant Ujjain.
2. **`P2 SupplementsRx AI -- Data Sources.docx`** — source recommendations,
   ontology resources, prototype-scope guidance, and NatMed access information.
3. A forwarded **NatMed Pro renewal receipt** — the subscription was renewed on
   October 2, 2026, with an expiration date of September 23, 2027 according to
   that receipt.
4. The user's ten-supplement list and instructions to build and launch the
   collection pipeline, use Old Reddit without API keys, and use the existing
   signed-in Chrome session.
5. The user's request to create GitHub repository **`ARYN26/CSE573`**, upload
   the project, and include this context in Markdown.

Passwords, login identifiers from the shared subscription, payment identifiers,
and the original credential-containing Word document are intentionally omitted.
The original source documents remain outside this repository. No credential is
needed to understand or restore the saved dataset.

## Current decisions and implemented scope

### The ten target topics

```python
SUPPLEMENTS = [
    "Magnesium",
    "Vitamin D",
    "Ashwagandha",
    "Melatonin",
    "Omega-3",
    "Vitamin B12",
    "Iron",
    "Turmeric",
    "Probiotics",
    "Creatine",
]
```

- Collect a bounded prototype dataset rather than a full historical archive.
- Use **Old Reddit HTML** for the primary Reddit workflow. API credentials are
  not required for that workflow. Optional API code remains a separate alternative.
- Use the user's **existing signed-in Chrome session** for collection. A fresh
  automated browser requires a separate login and is not the preferred workflow.
- Keep Reddit discussions labeled **`evidence_role=user_report`** and NatMed
  monographs labeled **`evidence_role=clinical_reference`** throughout exports.
- Preserve source text, URLs, timestamps, section labels, references, formulations,
  and population qualifications. Do not turn an anecdote into a clinical fact.
- Use aliases to identify candidate mentions, with word-boundary matching.
  Aliases are not UMLS mappings or assertions of clinical equivalence.
- Retain comments with either their own supplement mentions or their thread's
  topic; the latter are marked **`mention_scope=thread_context`**.
- Preserve native post/comment IDs and thread/parent relationships. Usernames and
  profile metadata are not retained in normalized records. Scores are currently
  unpopulated in the HTML-derived dataset.
- Deduplicate by stable source ID, preserve collection metadata, and export
  section-aware passages for later retrieval work.
- Respect rate limits. After a Reddit HTTP 429, collection was resumed at an
  eight-second minimum request interval with a minimum fifteen-minute cooldown
  on a further 429, while honoring longer `Retry-After` values.
- Do not generalize one formulation or probiotic organism's evidence to a whole
  supplement category. The selected Omega-3 source is **Fish Oil**, and the
  selected Probiotics source is **Lactobacillus acidophilus**.
- Store the project in a **private GitHub repository** because its dataset
  contains licensed NatMed text. This was the chosen publication default; public
  redistribution of the corpus was not requested.

### Verified collection result

The prototype collection completed on October 27, 2026:

| Artifact | Count |
| --- | ---: |
| Reddit posts | 287 |
| Reddit comments | 4,593 |
| Total Reddit records | 4,880 |
| NatMed monographs | 10 |
| Total source records | 4,890 |
| Derived RAG passages | 5,538 |

Actual Reddit records came from **r/Supplements (2,426 records)** and
**r/herbalism (2,454 records)**. r/Nootropics was searched but returned no records
in this run. The configured sample limit was 20 threads per topic/subreddit and
50 rendered comments per thread. Collapsed/load-more comments were not expanded.

| Topic | Reddit records tagged | NatMed monograph | Verified monograph ID |
| --- | ---: | --- | ---: |
| Magnesium | 1,703 | Magnesium | 998 |
| Vitamin D | 764 | Vitamin D | 929 |
| Ashwagandha | 667 | Ashwagandha | 953 |
| Melatonin | 759 | Melatonin | 940 |
| Omega-3 | 934 | Fish Oil | 993 |
| Vitamin B12 | 572 | Vitamin B12 | 926 |
| Iron | 652 | Iron | 912 |
| Turmeric | 547 | Turmeric | 662 |
| Probiotics | 577 | Lactobacillus acidophilus | 790 |
| Creatine | 807 | Creatine | 873 |

Tagged counts overlap because one record can have multiple topics and comments
can inherit thread context. Monograph URLs use
`https://naturalmedicines.therapeuticresearch.com/IngredientsTherapiesMonographs/Pro?id=ID`;
the actual captured titles were checked before their records were accepted.

All ten clinical records contain the five main sections: safety, effectiveness,
dosing, adverse effects, and drug interactions, plus citation links. Section
presence is an extraction check, not clinical validation or proof that every
source detail was captured. `requires_clinical_review` remains true and
`capture_quality.complete` remains false pending review.

### What is implemented

- Python ingestion, normalization to a common JSON record structure, and SQLite storage.
- Existing Reddit JSON/JSONL import, Old Reddit HTML collection, and explicit deletion/edit reconciliation support.
- Signed-in Chrome collection scripts and an importer for their downloaded batches.
- NatMed direct monograph capture, saved HTML/text import, clinical section extraction, and citation-link retention.
- Stable IDs, deduplication, content hashes, source provenance, and coverage reports.
- RAG passage exports and a graph export containing source/supplement nodes and
  **`MENTIONS`** provenance edges.
- Automated parser, storage, import/export, reconciliation, and offline browser
  regressions, plus integrity-checked dataset archives and GitHub Actions.

### What is still planned

The complete conversational AI described by the proposal is not implemented yet.
Remaining stages include:

1. Clinical evidence review and typed extraction of dosage, evidence grade,
   interaction severity, population, formulation, and supporting claims.
2. DSLD product/label collection and integration.
3. UMLS/MetaMap normalization and entity/relation extraction experiments.
4. Claim-centered Neo4j graph loading, bounded graph retrieval, and Louvain experiments.
5. BM25, MedCPT/FAISS, Reciprocal Rank Fusion, and reranking.
6. The deterministic Safety Intercept and grounded answer generation.
7. Agent/backend/UI integration, held-out QA construction, and evaluation.

The current graph exports do not contain clinically validated interaction or
treatment edges. Clinical source fields are section text, not fully normalized
medical assertions. No UMLS CUI is guessed.

### Files and restoration

- `supplementsrx/`: ingestion, storage, parsers, exports, and command-line tools.
- `browser/reddit_signed_chrome.js`: signed-in Old Reddit runner; reads topic and
  subreddit configuration from a selected local JSON file.
- `browser/natmed_direct_signed_chrome.js`: title/ID-verified direct NatMed runner;
  reads the selected manifest and attempts every configured monograph.
- `config/supplements.json`: target topics, aliases, and subreddit configuration.
- `config/natmed_manifest.json`: verified captured source URLs and titles.
- `datasets/`: compressed copies of the source records, RAG passages, graph
  exports, examples, coverage, completion summary, and a consistent SQLite backup.
- `datasets/manifest.json`: original/compressed sizes and SHA-256 integrity hashes.
- `scripts/restore_dataset.py`: verifies and restores the standard local layout.
- `.github/workflows/ci.yml`: Windows/Linux Python regression and restore/CLI
  checks, plus Node-based offline collector regressions.

```sh
python3 scripts/restore_dataset.py
python3 -m supplementsrx status
python3 -m unittest discover -s tests -v
```

Restored files live in `data/` and `exports/`; those working directories remain
gitignored. The compressed `datasets/` copies are included in this private repo.
The `.venv`, caches, `.env`, browser sessions, cookies, and passwords are excluded.

Operational preference established during this work: when collection is
authorized, launch it and verify persisted records; report actual database counts
and errors rather than equating a prepared command or login page with progress.

## Supplied proposal: SupplementsRx AI — Conversational Agent

### Abstract and objective

The proposed system is an evidence-based conversational agent for dietary
supplements, addressing effectiveness, dosage, safety, and drug interactions.
NatMed Pro and the Dietary Supplement Label Database (DSLD) provide evidence and
product information; UMLS and MetaMap normalize biomedical terminology.

The planned hybrid retrieval pipeline combines BM25, MedCPT, FAISS, fusion, and
reranking. A Neo4j knowledge graph connects products, ingredients, drugs,
conditions, evidence claims, and sources. A deterministic Safety Intercept checks
interactions, contraindications, dosage concerns, and insufficient evidence.
Experiments compare classical retrieval with modern RAG and graph methods for
accuracy, safety, and source traceability.

### Problem definition

The proposal identifies three problems:

1. **Safety and interaction risks:** consumers may combine supplements with
   medications without adequate contraindication or interaction warnings.
2. **LLM hallucinations:** confident medical answers without traceable evidence
   are unacceptable in this use case.
3. **Information ambiguity:** inconsistent product descriptions and unclear dose
   guidance make supplement information difficult to use reliably.

The intended agent serves as a conversational gatekeeper, performs active safety
checks, provides condition guidance and wellness coaching, and explicitly
acknowledges when verifiable evidence is unavailable. Authoritative evidence
grounds clinical answers; forums contribute real-world questions and experiences.

### Proposed datasets and preparation

- **NatMed Pro:** primary clinically reviewed source for ingredients,
  effectiveness, safety, adverse effects, interactions, and commercial products.
- **DSLD:** structured product names, ingredients, quantities, and label information.
- **UMLS / Metathesaurus:** standardized drugs, diseases, symptoms, ingredients,
  therapies, and conditions.
- **Discussion boards:** Reddit r/Supplements and r/Nootropics, LongeCity, and
  other selected forums for conversational context and user questions.

The proposed preparation flow is collection into JSON, cleaning and normalization,
MetaMap identification of biomedical mentions in unstructured text, UMLS concept
mapping, and transformation into graph entities and relations. Forum experience
must remain distinguishable from clinical evidence throughout that flow.

### Proposed methods

**Hybrid text retrieval.** BM25 handles exact terminology. MedCPT generates dense
biomedical embeddings indexed in FAISS. Reciprocal Rank Fusion combines lexical
and semantic rankings, and a cross-encoder reranks top passages. The generator
receives selected evidence with citation metadata.

**Evidence-preserving graph.** Neo4j stores products, ingredients, drugs,
conditions, claims, and sources. Claim nodes retain dosage, population,
effectiveness rating, interaction severity, and citations; qualified evidence is
not reduced to an unqualified binary fact. Graph retrieval uses bounded one- or
two-hop Cypher traversals.

**Biomedical extraction.** Structured NatMed/DSLD fields map to the ontology.
MetaMap maps forum mentions to UMLS concepts, with possible BioBERT experiments
for entity recognition. Compare rule-based relation extraction with constrained
LLM extraction into ontology-compliant JSON. No task-specific fine-tuning is
required by the proposal.

**Louvain community detection.** Graph communities may narrow retrieval for broad
questions and reveal related therapeutic areas. Community membership itself is
not medical evidence; answers remain tied to original claims and citations.

**Safety Intercept.** Before generation, deterministic graph/rule checks inspect
drug-supplement interactions, contraindicated conditions, pregnancy/lactation,
unsupported dosages, and insufficient evidence. Responses may require a warning,
uncertainty statement, or abstention instead of an unsupported recommendation.

### Proposed research phases

1. **Data acquisition/preparation:** parse NatMed/DSLD into normalized JSON;
   normalize forum concepts with MetaMap/UMLS while preserving user-report labels.
2. **Knowledge graph:** build a claim-centered graph preserving dose, evidence
   grade, severity, and source qualifications.
3. **Text retrieval experiments:** compare BM25, MedCPT/FAISS, and their fused
   results, followed by cross-encoder reranking.
4. **Graph retrieval/community detection:** compare Cypher-based evidence
   retrieval and Louvain-supported broad retrieval.
5. **Agent integration/safety:** combine graph/text evidence, apply deterministic
   safety checks, and generate cited answers with warnings or abstention as needed.
6. **Controlled evaluation/finalization:** use held-out questions, perform error
   analysis, refine the system, and package the prototype.

### Proposed evaluation

| Stage | Baseline | Proposed comparison | Metrics |
| --- | --- | --- | --- |
| Entity/relation extraction | Rules | UMLS/MetaMap plus constrained LLM extraction | Entity F1; relation precision/recall |
| Retrieval | BM25 | BM25 + MedCPT/FAISS with RRF | Recall@10; MRR |
| Answer generation | Text-RAG | Full system with graph and safety intercept | Correctness; citation support; safety recall; abstention |

The proposed **SupplementsRx-QA** set contains approximately 250 questions:
50 tuning and 200 held-out testing questions. About half originate from
de-identified forum posts and half from reworded NatMed content. Approximately
10% cover high-risk or out-of-scope cases. Two team members annotate reference
answers and evidence; report Cohen's kappa where appropriate.

Evaluate five capabilities: supplement insights, safety checks, condition
guidance, wellness coaching, and personalized Q&A. Measure interaction and
contraindication recall, appropriate abstention, and over-refusal; include an
ablation with the Safety Intercept disabled. Test remembered user context using
20 scripted multi-turn dialogues. Two members blindly rate 50 responses from
the full system and the Text-RAG baseline for correctness, completeness, potential
harm, and clarity. NatMed is the primary reference standard, supplemented by
NIH Office of Dietary Supplements fact sheets when necessary.

For future forum-derived evaluation, split by thread rather than individual
comments/passages so one discussion does not leak across tuning and test sets.
This split rule was adopted during pipeline planning; the QA set is not built yet.

### Original proposal timeline

These are the dates in the supplied proposal, not a report of completed work.

| Task | Original deadline |
| --- | --- |
| Data collection and preprocessing | October 15, 2026 |
| Knowledge graph construction | October 25, 2026 |
| Agent development | November 5, 2026 |
| System integration | November 12, 2026 |
| UI, testing, and deployment | November 22, 2026 |
| Final evaluation | November 30, 2026 |

### Current delivery gates

The original collection and graph deadlines have passed. They are historical
targets, not completed milestones or revised commitments. Use these acceptance
gates in order; the team must agree calendar dates rather than treating the
original dates as evidence of progress.

| Gate | Acceptance before proceeding | Proposal workstream |
| --- | --- | --- |
| Ingestion correctness | Audit regressions pass; archive hashes and corrected provenance verified; PR reviewed | Data scraping/preprocessing and testing |
| Clinical review and claim schema | Review all ten captures against licensed originals; record source span/citation, ingredient, formulation/strain, population, dose value/unit/frequency/duration, evidence grade, interaction severity, reviewer and review status; mark unsupported fields unknown | Data preprocessing and evaluation |
| Evaluation split and baseline | Agree tuning/held-out questions and thread-group split before tuning; establish BM25 Recall@10 and MRR baseline | RAG and testing |
| Clinical graph and Safety Intercept | Load reviewed claims with provenance; exercise interaction, contraindication, pregnancy/lactation, dosage and insufficient-evidence cases with expected warning/abstention outcomes | Graph construction, RAG and testing |
| Hybrid retrieval and cited answers | Compare MedCPT/FAISS, RRF and reranking against baseline; measure citation support, safety recall, abstention and over-refusal | RAG and evaluation |
| Agent/UI and final evaluation | Integrate only the verified retrieval/safety path; exercise multi-turn context and blinded baseline comparison | UI/system integration and evaluation |

No clinical claim was certified by the code audit. The corpus remains
`requires_clinical_review=true` and source completeness remains unverified.
Original downloaded browser batches were not found in this workstation's
Downloads directory, so historical source-text encoding fidelity could not be
compared against those batches. Do not guess repairs to medical text.

The audit adds explicit UTF-8 imports, refreshed-parent topic handling,
durable/atomic downloaded-batch ingestion, stale clinical-capture protection,
saved-HTML citation URLs, and passage source/context metadata. Regenerated
passages retain the original record and passage counts; source text is unchanged.
The obsolete NatMed search/frame runner and historical browser checkpoints are
removed. Offline browser checks are not proof of current live site compatibility.

The repository must stay private because it includes licensed NatMed text.
GitHub returned HTTP 403 for branch protection under the current account plan.
CI and PR review can operate, but enforced required checks/protected merging
need an account-plan upgrade; publishing the corpus is not an alternative.


### Division of work in the proposal

| Workstream | Team members |
| --- | --- |
| Data scraping/preprocessing | Seemant Ujjain, Aryan Srivastava |
| Clustering/graph construction | Seemant Ujjain, Ashish Kurse |
| RAG | Jason Lu, Ashish Kurse, Seemant Ujjain |
| UI/system integration | Ashish Kurse, Onkar Falle |
| Testing | Jason Lu, Onkar Falle, Aryan Srivastava |
| Evaluation/report | Everyone |

### References listed in the proposal

1. Therapeutic Research Center, Natural Medicines Database / NatMed Pro.
2. NIH Office of Dietary Supplements, Dietary Supplement Label Database.
3. U.S. National Library of Medicine, Unified Medical Language System.
4. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP
   tasks,” NeurIPS, 2020.
5. Xiong, Jin, Lu, and Zhang, “Benchmarking retrieval-augmented generation for
   medicine,” Findings of ACL, 2024.
6. Gao et al., “Retrieval-augmented generation for large language models: A
   survey,” arXiv:2312.10997, 2023.
7. Edge et al., “From local to global: A graph RAG approach to query-focused
   summarization,” arXiv:2404.16130, 2024.
8. Soman et al., “Biomedical knowledge graph-optimized prompt generation for
   large language models,” Bioinformatics, 2024.
9. Aronson and Lang, “An overview of MetaMap: Historical perspective and recent
   advances,” Journal of the American Medical Informatics Association, 2010.
10. Lee et al., “BioBERT: A pre-trained biomedical language representation model
    for biomedical text mining,” Bioinformatics, 2020.
11. Blondel et al., “Fast unfolding of communities in large networks,” Journal
    of Statistical Mechanics: Theory and Experiment, 2008.
12. Ji et al., “Survey of hallucination in natural language generation,” ACM
    Computing Surveys, 2023.
13. Singhal et al., “Large language models encode clinical knowledge,” Nature, 2023.

These entries reproduce the proposal's reference list in shortened form; they
have not been independently re-audited as part of repository preparation.

## Supplied data-source guidance

### Prototype approach and ontology

The Word document recommends beginning with three to five web sources and a
limited page depth, then expanding after the agentic foundation is validated.
The suggested ontology includes drugs, diseases, symptoms, ingredients and
therapies, commercial products, and conditions.

Resources supplied in that document:

- [NatMed Pro](https://naturalmedicines.therapeuticresearch.com/Home/ND)
- [UMLS](https://www.nlm.nih.gov/research/umls/index.html)
- [UMLS Metathesaurus](https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/index.html)
- [MetaMap source](https://github.com/LHNCBC/MetaMap-src)
- [SPECIALIST NLP](https://lhncbc.nlm.nih.gov/LSG/index.html)

The document describes NatMed access to 1,400+ monographs/clinical resources,
300,000+ commercial products, and interactive safety/clinical tools. These are
claims recorded in the supplied guidance, not a measurement of the scraped corpus.
The current prototype collected ten monographs rather than the full database.

### Discussion boards recommended in the source document

| Suggested segment | Source | URL |
| --- | --- | --- |
| Older adults / longevity / cognition | LongeCity Supplements | https://www.longecity.org/forum/forum/6-supplements/ |
| Older adults / cognition | LongeCity Nootropic Stacks | https://www.longecity.org/forum/forum/412-nootropic-stacks/ |
| Older adults / cognition | Reddit r/Nootropics | https://www.reddit.com/r/Nootropics/ |
| Adult women / herbal wellness | Reddit r/herbalism | https://www.reddit.com/r/herbalism/ |
| Sports / fitness | Anabolic Minds | https://anabolicminds.com/community/ |
| Sports / fitness | T Nation | https://forums.t-nation.com/c/supplements-and-nutrition/25 |
| Sports / fitness | Bodybuilding.com | https://forum.bodybuilding.com/forumdisplay.php?f=1 |
| Sports / fitness | UK-Muscle | https://www.uk-muscle.co.uk/forums/supplementation.22/ |
| Sports / fitness | Australian BodyBuilding | https://ausbb.com/forums/bodybuilding-supplements.7/ |
| Sports / fitness | EliteFitness | https://www.elitefitness.com/forum/bodybuilding-supplements/ |
| Sports / fitness | MuscleMecca | https://www.musclemecca.com/forums/supplements-forum.6/ |
| Sports / fitness | Sherdog | https://forums.sherdog.com/forums/dieting-supplement-discussion.12/ |
| General wellness | Reddit r/Supplements | https://www.reddit.com/r/Supplements/ |
| General wellness | PricePlow | https://forum.priceplow.com/c/supplements/5 |

Those segment labels are the source document's suggestions; no demographic
attributes were inferred about individual Reddit authors.

The recommended top five prototype forums were r/Supplements, LongeCity
Supplements, r/Nootropics, r/herbalism, and Anabolic Minds. The implemented run
focused on Reddit plus NatMed. The other listed forums and DSLD remain candidates
for later work; they were not collected in this prototype.

## Practical next step

Review source-qualified clinical excerpts and establish a claim schema before
building clinical edges or a safety engine. Keep the current raw source records
as provenance, map forum entities with UMLS/MetaMap, and build separate evaluation
splits by thread. Refer to the proposal's planned methods above when implementing
the downstream graph, retrieval, agent, and evaluation stages.
