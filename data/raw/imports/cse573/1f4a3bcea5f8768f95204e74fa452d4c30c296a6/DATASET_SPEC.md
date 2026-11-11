# SupplementsRx Dataset Specification

## 1. What this dataset contains

This is a **bounded prototype dataset**, covering ten supplement topics. The Reddit records were collected on October 27, 2026. The ten NatMed monographs were recaptured on October 28, 2026 (see §4).

It contains source material for retrieval and research—not finished question/answer pairs or medically validated recommendations.

| Source | Saved data | Purpose |
|---|---|---|
| Reddit | 287 posts and 4,593 comments | Real-world questions and reported experiences |
| NatMed Pro | 10 professional ingredient monographs | Clinical-reference material requiring qualified human source and medical review |
| **Total** | **4,890 source records** | Converted into **6,250 searchable passages** (5,071 Reddit, 1,179 NatMed) |

Reddit experiences are **not treated as clinical evidence**.

## 2. Topics and exact NatMed sources

The project topics are broad labels. The actual captured monograph determines the limits of the evidence.

| Project topic | Captured NatMed monograph | Monograph ID | Recorded page-update date |
|---|---|---:|---|
| Magnesium | Magnesium | 998 | October 27, 2026 |
| Vitamin D | Vitamin D | 929 | October 27, 2026 |
| Ashwagandha | Ashwagandha | 953 | October 28, 2026 |
| Melatonin | Melatonin | 940 | October 27, 2026 |
| Omega-3 | **Fish Oil** | 993 | October 27, 2026 |
| Vitamin B12 | Vitamin B12 | 926 | October 27, 2026 |
| Iron | Iron | 912 | October 27, 2026 |
| Turmeric | Turmeric | 662 | October 28, 2026 |
| Probiotics | **Lactobacillus acidophilus** | 790 | October 28, 2026 |
| Creatine | Creatine | 873 | October 27, 2026 |

These are **monographs summarizing evidence**, not ten individual research papers. Page-update dates come from saved metadata; they are not the publication dates of the cited studies.
The saved text also states literature-review cutoffs from February 13 through
October 20, 2026. These are distinct from page-update dates and study publication
dates; the per-monograph cutoffs and freshness limitations are recorded in
[READINESS_AUDIT.md](READINESS_AUDIT.md).

Fish Oil does not represent every omega-3 formulation. *Lactobacillus acidophilus* does not represent every probiotic species, strain, or mixture.

## 3. Collection dates versus source dates

**Collection snapshots:** Reddit, October 27, 2026. NatMed, recaptured October 28, 2026 (the earlier October 27 NatMed capture was superseded).

**Reddit publication-date policy:** No fixed starting date was imposed. Searches used **all-time results, sorted newest first**.

The resulting saved sample covers:

| Subreddit | Posts | Comments | Earliest saved publication | Latest saved publication |
|---|---:|---:|---|---|
| r/Supplements | 133 | 2,293 | September 21, 2026 | October 27, 2026 |
| r/herbalism | 154 | 2,300 | June 27, 2020 | October 22, 2026 |

No r/Nootropics records are saved. The snapshot lacks query-completion logs, so
it does not establish whether every configured search completed or why this
subreddit contributed no records.

**This is not a complete Reddit archive for 2020–2026.** Those dates describe the records returned by the bounded searches.

Reddit’s first-import timestamps span approximately **05:36–07:33 UTC** on October 27. The NatMed recapture timestamps span approximately **23:24–23:26 UTC** on October 28. These stored timestamps do not establish the exact duration of browser scraping.

No publication-year restriction was applied to studies cited inside the NatMed monographs. Citation years come from the bibliographies; PubMed publication years are available separately for cited PMIDs (§5).

## 4. How collection worked

### Reddit

Scripts ran inside an existing signed-in Chrome session and read **Old Reddit HTML**, without Reddit API keys.

They:
1. Searched supplement names and aliases within the configured subreddits.
2. Opened discussion pages.
3. Captured post text and rendered comments.
4. Downloaded the results as JSON batches.

Configured limits were **20 threads per topic/subreddit** and **50 rendered comments per thread**. Collapsed/load-more comments were not expanded.

A comment could be retained because it mentioned a supplement itself or inherited its parent thread’s topic. These cases are distinguished by `mention_scope`.

### NatMed Pro

The October 28 recapture used an authenticated, user-controlled Edge session. NatMed
pages are server-rendered, but about two-thirds of each monograph was hidden in
collapsed `.custom-details-content` blocks behind 300+ "more" toggles; the earlier
October 27 text capture never saved that content (Magnesium grew from 52.6k to
146.0k characters; monographs are now about 55k–228k characters). The collector now:

1. opens each selected professional monograph and checks its title and ID;
2. reveals the hidden blocks **in place** by class manipulation (no clicking) and
   takes the rendered text;
3. saves the raw page HTML after `natmed.scrub_source_html` removes every
   `<script>`/`<noscript>` element (they embed account, session and IP identifiers)
   and session parameters; the text is unchanged;
4. fetches each monograph's References page as authenticated same-origin server HTML,
   because the rendered page is DataTables-paginated and shows only 10 rows. Parsed
   rows equal the site's rendered "of N entries" total for all ten monographs.

The batches were imported through the real batch importer
(`watch_downloads.process_batch`), which validates and persists the HTML atomically
with the database commit. The pasted signed-in script and the optional Playwright
collector use the same reveal-and-fetch method.

Captured sections include safety, effectiveness, dosing, adverse effects,
interactions (with drugs, supplements, conditions and lab tests), formulation
information and mechanisms of action; "Nutrient Depletions" is its own section for
Magnesium, Vitamin D, Vitamin B12 and Iron.

**Completeness status:** no collapsed content or missing bibliography remains in the
saved captures. Inline citation reference numbers absent from the publisher
bibliography number 55 (Vitamin D 30, Fish Oil 10, Creatine 6, Turmeric 4, Iron 3,
Melatonin 1, Vitamin B12 1; none for Magnesium, Ashwagandha or
*L. acidophilus*); this is a publisher-side gap, reported and not corrected.
`capture_quality.complete` remains false and `requires_clinical_review` true:
comparison against the licensed originals and qualified human review are still required before clinical approval.


## 5. Processing and storage

The browser downloaded JSON batches. Python validated and normalized them into a common format, then stored them in SQLite.

Stable source IDs prevent duplicate records. Reddit post/comment IDs and parent relationships are preserved. Older clinical captures cannot overwrite newer ones.

| Artifact | What it contains |
|---|---|
| `data/pipeline.sqlite3` | Working database of normalized records, checkpoints, and events |
| `exports/records.jsonl` | Complete normalized source records |
| `exports/passages.jsonl` | Smaller, overlapping excerpts for retrieval |
| `exports/kg_nodes.jsonl` and `kg_edges.jsonl` | Source/topic nodes and `MENTIONS` provenance links—not validated medical relationships |
| `datasets/*.gz` | Compressed copies stored in the private GitHub repository |
| `datasets/manifest.json` | File sizes and SHA-256 hashes for integrity verification |
| `data/natmed_source_html.jsonl` | Scrubbed raw NatMed HTML, one row per monograph, bound to its record by `source_html_sha256` (archived as `datasets/natmed_source_html.jsonl.gz`) |
| `exports/clinical_claims.jsonl` | Derived, structured pending clinical annotations; separate from the source SQLite database |
| `exports/clinical_extraction_report.json` | Per-source/type/field extraction coverage and unresolved issues |
| `datasets/clinical_claims_manifest.json` | Source/schema fingerprints and clinical-output archive hashes |
| `datasets/pubmed_metadata.jsonl.gz`, `datasets/pubmed_report.json` | Public PubMed esummary metadata for the PMIDs cited in the bibliographies (not covered by the restore manifests) |

**JSONL** means one JSON object per line. **`.gz`** means the file is compressed.

Passages are normally up to **220 whitespace-separated words**, with **40-word overlap**, without crossing section boundaries.
Each passage now includes a source hash and exact section/word-window metadata.
Retrieval/evaluation check that identity against authoritative source records.
Passage citation links are restricted to numeric labels cited in that passage;
they are not a verified bibliography or proof that a study supports the claim.

Each NatMed record contains `reference_documents`: the separate publisher
References page keeps its URL, title, text, capture time and content hash. The text
is a title line followed by `N. citation[ PMID: x]` lines (6,435 references across
the ten monographs). These pages are not appended to the monograph or treated as
verified studies. Passages contain only their combined fingerprint.

PubMed enrichment (`python -m supplementsrx pubmed-enrich`) fetches public NCBI
E-utilities esummary metadata only (title, journal, year, publication types, DOI):
5,990 distinct PMIDs, 5,988 found. Counted per source bibliography (a PMID cited by two
monographs counts twice), the publication types include 2,456 Randomized Controlled
Trials, 773 Meta-Analyses and 653 Systematic Reviews. Publication type and year
describe the cited study, not whether it supports a claim. 23 citation-year versus
PubMed-year mismatches are flagged as possible wrong publisher links and not corrected.


## 6. What an output record looks like

An actual Reddit record, with fields omitted for readability:

```json
{
  "id": "reddit:t3_1xeivsd",
  "source": "reddit",
  "record_type": "post",
  "title": "Best magnesium, zinc, k2 supplement?",
  "evidence_role": "user_report",
  "thread_id": "t3_1xeivsd",
  "mention_scope": "own_text",
  "supplements": [
    {
      "supplement": "Magnesium",
      "matched_terms": ["magnesium"]
    }
  ],
  "requires_clinical_review": true
}
```

The full record also contains its text, original URL, timestamps, and content hash.

A NatMed record instead uses:
- `source: "natmed"`
- `record_type: "monograph"`
- `evidence_role: "clinical_reference"`
- Sectioned text, citation links, and capture-quality metadata.

**`clinical_reference` identifies the source category; it does not mean our saved capture is medically approved.** All current clinical captures remain review-required.

## 7. Privacy and use limits

- Normalized records exclude Reddit usernames/profile metadata.
- Free text may still contain personal information; evaluation questions require de-identification.
- Browser passwords, cookies, and session tokens are not exported.
- The repository remains **private because it contains licensed NatMed text**.
- Human source review and relevance annotation are required before clinical approval or reporting real retrieval benchmark scores.

## 8. Open the sample

From the cloned repository:

```sh
python scripts/restore_dataset.py
```

Then open **`exports/sample_records.json`**. It contains a Reddit post, a related comment, and a Magnesium monograph.

For structured clinical values, open **`exports/clinical_claims.sample.json`**.
The readable sample is also available directly on GitHub at
[`datasets/clinical_claims.sample.json`](datasets/clinical_claims.sample.json).

## 9. Structured clinical annotations and readiness

Structure-driven extraction from the saved HTML (`supplementsrx/natmed_html.py`,
`section_extract.py`; `extract-clinical --html`) supplies **1,269 pending
annotations** from the ten saved monographs: 85 dose (71 with numeric quantities),
809 effectiveness, 107 safety, 120 adverse-effect and 148 interaction claims. This
is a derived annotation layer, not additional source documents or medically
approved values. 49 extraction issues remain (the report lists their codes); there
are no collapsed-content gaps.

Fields retain exact source spans, ingredient identity, condition/rating where
explicit, population, dose quantity/unit/bounds/regimen/frequency/duration/route,
and separate interaction rating/severity/occurrence/evidence grade. Unknowns
remain null. Mixed-unit/scale ambiguity remains text plus an issue; no conversion
or unsupported equivalence is guessed.

Units such as `mg/kg/day` retain their full meaning; they cannot become `mg`.
Salt/formulation quantities stay text-only when attribution to the titled
ingredient is uncertain. Each excerpt holds one source entry with its detail
paragraphs. An `effectiveness_rating` may anchor on the group heading earlier in
the same section (the validator rejects it if a newer group intervenes); use the
structured condition/partner and its support offsets for the specific association.
Interactions-with-Conditions entries are safety claims with the condition in
`population` (`source.section_heading == "interactions with conditions"`); they
describe caution in that condition, not an indication.

All annotations remain `review.state=pending`; approved count is zero. A valid
source span does not certify a correct medical association or complete source.
Known gaps: Ashwagandha warnings embedded in its overview are not parsed
(`section_not_in_html`), and two entries with inline condition headings (Magnesium
PXE, Fish Oil heart transplant) yield issues, not claims. The 55 inline reference
numbers missing from the publisher bibliographies cannot be resolved from the capture.

Regenerate and validate with:

```sh
python -m supplementsrx extract-clinical
python -m supplementsrx validate-claims datasets/clinical_claims.jsonl.gz
```

See [`datasets/clinical_extraction_report.json`](datasets/clinical_extraction_report.json)
for field coverage and unresolved cases, and [READINESS_AUDIT.md](READINESS_AUDIT.md)
for what can proceed and what remains blocked.
