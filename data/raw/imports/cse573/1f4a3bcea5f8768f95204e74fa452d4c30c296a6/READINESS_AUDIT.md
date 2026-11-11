# Next-stage readiness audit

Audit scope: saved source records, passages, SQLite snapshot, citations, pending clinical extraction, review admission, retrieval/evaluation integrity, and installed-package operation. Findings dated before October 28 describe the October 27 capture; where the October 28 authenticated NatMed recapture supersedes them, they are marked **superseded** and kept as history. No publisher-original comparison, study validation or medical approval has been performed.

## Verdict

**Usable for bounded research retrieval and pending source-grounded annotation. Not ready for approved clinical recommendations, a clinical safety graph, or a Safety Intercept.** Those remain blocked on qualified human source and claim review, not on capture completeness: the October 28 recapture closed the collapsed-content and missing-bibliography gaps.

A valid annotation means its fields and source spans passed mechanical checks. It does not certify a medical claim or establish complete source capture. All 1,269 extracted annotations remain pending; approved count is zero. `capture_quality.complete` stays false and `requires_clinical_review` true for all ten monographs. Still required before clinical use: qualified human source/claim review, UMLS mapping, DSLD collection and QA qrels.

## Independently found software defects and verification

This table and the October 28 code-audit table below record defects and fixes found against the October 27 dataset. Dataset counts quoted in them (for example 1,135 annotations or 5,538 passages) are historical.

| Defect | Before-fix evidence | Fix and observed after-fix result |
| --- | --- | --- |
| Reviewed-only consumers trusted copied passage flags | Changing a real Magnesium passage's two flags admitted it while its source remained unreviewed | Admission now requires authoritative records, current source hash, complete source capture, named/time-stamped hash-bound human approval and consistent passage metadata. Real spoof probe now returns no approved retrieval evidence; evaluation rejects its qrel. |
| Numeric anchors could select only part of a source quantity | A real source `350 mg` accepted an annotation selecting only `50` | Full numeric-token boundaries are checked for scalar doses, ranges and durations. The original real-data probe is now rejected; regressions cover all three paths. |
| Evaluation did not bind passage identity to the exact source window | Safety text substituted under a real Magnesium dosing passage ID was scored | Canonical source/section/word-start ID, section metadata, word count/chunk size, full source hash and exact reconstructed text are checked. The original substitution probe is rejected. |
| Non-editable wheels omitted mandatory JSON resources | The prior wheel failed outside the checkout even with explicit records/schema inputs | The single checked-in config set is installed as shared data and resolved without trusting CWD. Before/after wheel smoke reproduced the failure and then validated all 1,135 real exported annotations from an installed package outside the checkout. No licensed datasets are bundled. |
| Whole-page citation inventories were copied to every passage | Raw monograph link inventory appeared on unrelated passage text | Passage links are scoped to parenthetical numeric labels actually present in that passage. Raw records retain the full inventory. This is syntactic attribution, not verified study support. |
| Dose demographic continuation could borrow an earlier dose's age group | Regression exposed two different age-specific doses sharing the first dose's population | Per-quantity clause boundaries now prevent suffix-to-prefix population leakage. Regressions cover synthetic cases and saved Iron/Vitamin D age associations. |

### Additional audit — October 28

The audit covered the local files and the changes in open PRs #2 and #4, with
independent dose, section-extraction and review-boundary analysis.

| Finding | Reproduced behavior and fix |
| --- | --- |
| Cross-entry clinical metadata | Ashwagandha's antidiabetes partner accepted the antihypertensive entry's severity and evidence grade. Interaction fields are now confined to their own partner entry. Safety populations cannot be borrowed from another entry; rating-only safety excerpts cannot omit the source line's qualifications. |
| Partial strings, units and repeated-unit ranges | Iron accepted `males` selected inside `females` and `mg` selected from `mg/kg/day`. Complete string tokens and unit denominators are now required. A repeated-unit range cannot become one endpoint. |
| Parenthetical/negated bounds and claim-type confusion | A Vitamin D parenthetical equivalent dropped the outer upper limit. A separate probe accepted `more than` selected from `not more than`, reversing a maximum. Bounds now reach through conversions and retain negations for doses/durations. Structured dose fields are prohibited on safety/non-dose claims. An Iron safety annotation with simulated approval and a truncated toxic dose now returns invalid and zero approved. |
| Forged retrieval metadata | A real Magnesium passage accepted an Ashwagandha topic, unrelated citation URLs, a fabricated UMLS mapping and a false verified-study scope. Export and binding validation now share one derivation for topic, normalization, reference and citation metadata. The forged passage is rejected. |
| Dose association and false dose candidate | A B12 statement that pediatric RDAs were not established was emitted as a dose. It is removed. Adjacent AI/RDA labels, older-adult context, infant age restrictions, frequency multiplicity, alternative quantities and maximum-bound wording are now handled conservatively. Three Magnesium sulfate quantities remain raw text rather than being presented as normalized Magnesium quantities. |
| Duplicated/borrowed section descriptions | Four cumulative adverse-effect duplicates were removed. Route descriptions merge within their category; unfamiliar safety labels cannot inherit the previous population. Fused effectiveness text is flagged rather than paired with the next condition. UI/citation debris is excluded. |
| Windows corrupt-archive cleanup | A malformed gzip masked its error with `PermissionError` and left an open temporary file. Cleanup now occurs after the stream closes. The same probe produces `BadGzipFile`, no leftover temporary file and unchanged local data. Truncation/hash failures and deliberate-overwrite protection have regressions. |
| Repeated review work | Reviewed-only queries previously checked every corpus record and rebound even already-ineligible sources. Each query now loads the manifest once, checks only indexed source identities and stops on source rejection. No review approval is cached; revocation/content-change regressions still pass. |

At the time of this code audit (**superseded** by the October 28 recapture below), the dataset had 85 dose, 809 effectiveness, 69 safety, 28 adverse-effect
and 139 interaction annotations (1,130 in total; 71 numeric doses) and 1,310 extraction issues. The current counts are in the recapture section.

Additional direct probes reject the real Iron partial-population annotation,
borrowed Ashwagandha interaction labels, and forged Magnesium passage metadata.
At that time all 5,538 passages bound and the pending-only, 467-passage reviewed
query returned no evidence in a three-run median of 0.089 seconds locally
(diagnostic measurement, not a benchmark or latency guarantee). Neither the
binding check nor the timing has been repeated against the 6,250-passage corpus.

Implementation: `clinical.py`, `retrieval.py`, `evaluation.py`, `core.py`, `resources.py`, and `dose_extract.py` under `supplementsrx/`.

## October 28 authenticated NatMed recapture

The ten NatMed sources were recaptured from an authenticated, user-controlled Edge session and imported through the real batch importer (`watch_downloads.process_batch`). The datasets were regenerated deterministically.

| Item | Result |
| --- | --- |
| Why the earlier capture was incomplete | NatMed pages are server-rendered, but about two-thirds of each monograph was hidden in collapsed `.custom-details-content` blocks behind 300+ "more" toggles; the old `innerText` capture never saved them. Magnesium grew from 52.6k to 146.0k characters; monographs are now about 55k–228k characters. |
| Capture method | Hidden blocks are revealed in place by class manipulation (no clicking) and the rendered text saved. Raw HTML is saved after `natmed.scrub_source_html` removes all `<script>`/`<noscript>` elements (they embed account id, session id and IP) and session parameters; text is unchanged. It is archived as `datasets/natmed_source_html.jsonl.gz` (restores to `data/natmed_source_html.jsonl`) and bound per record by `source_html_sha256`. |
| Bibliographies | Authenticated same-origin fetch of the server HTML of each References page (the rendered page is DataTables-paginated and shows only 10 rows). Parsed rows equal the site's "of N entries" totals for all ten; stored as `reference_documents` and hash-bound in the source approval. 6,435 references: Creatine 544, Magnesium 965, Vitamin D 628, Ashwagandha 137, Melatonin 1,022, Fish Oil 1,062, Vitamin B12 534, Iron 666, Turmeric 586, L. acidophilus 291. |
| Dataset changes | Record count unchanged at 4,890; all 4,880 Reddit records byte-identical; KG edges identical (7,992 `MENTIONS`); only the ten NatMed records changed. Passages 5,538 → 6,250. "Nutrient Depletions" is now its own section (Magnesium, Vitamin D, Vitamin B12, Iron), previously folded into the preceding section; no claims come from it. |
| Thread split | The fingerprint was regenerated (`--overwrite`) because it hashes full records; membership verified identical. |
| Pending claims | 1,269 (previously 1,130): 85 dose (71 numeric; `dose_extract` unchanged), 809 effectiveness, 107 safety, 120 adverse effect, 148 interaction; 0 approved. Safety includes Interactions-with-Conditions claims with the condition in `population` (`source.section_heading == "interactions with conditions"`). |
| Extraction method | Structure-driven extraction from the saved HTML (`supplementsrx/natmed_html.py`; `section_extract.py` rewritten; `extract-clinical --html`). Each excerpt holds one entry with its detail paragraphs; `effectiveness_rating` may anchor on the group heading earlier in the same section (the validator rejects it if a newer group intervenes). |
| Extraction issues | 1,310 → 49 (codes in `clinical_extraction_report.json`). Zero collapsed-content gaps. |
| Collectors | The pasted signed-in script and the optional Playwright collector use the in-place reveal and server-fetched bibliography. Batches carry scrubbed `source_html`; the importer validates and persists the HTML atomically with the database commit. Live smoke on October 28: the pasted script on live Ashwagandha reported complete, 59 detail blocks revealed, 137/137 references, 0 inline references missing; that batch imported through the real importer with 0 binding errors. |

### Measured limitations that remain

- Inline citation reference numbers absent from the publisher bibliography: 55 in total (Vitamin D 30, Fish Oil 10, Creatine 6, Turmeric 4, Iron 3, Melatonin 1, Vitamin B12 1; none for Magnesium, Ashwagandha or L. acidophilus). This is a publisher-side gap, reported and not corrected.
- Extraction: Ashwagandha warnings embedded in its overview are not parsed (`section_not_in_html`); two entries with inline condition headings (Magnesium PXE, Fish Oil heart transplant) yield issues, not claims. Placeholders, group-level qualifications and unquantified doses also produce issues rather than inferred facts.
- No comparison against the licensed originals and no medical review has been performed (`original_source_comparison` and `medical_review` are `not_performed` in the extraction report).
- Source/topic mappings are correct, but Fish Oil is not all omega-3 formulations and Lactobacillus acidophilus is not all probiotics or strains.
- Upper intake limits, RDAs, study-use summaries, loading doses, maintenance doses and population-specific quantities are not interchangeable treatment recommendations. The extractor preserves source qualifiers and retains ambiguous normalization as text plus issues.

### PubMed enrichment

`python -m supplementsrx pubmed-enrich` fetches public NCBI E-utilities esummary metadata only (title, journal, year, publication types, DOI) into `datasets/pubmed_metadata.jsonl.gz` and `datasets/pubmed_report.json`. 5,990 distinct PMIDs; 5,988 found. Counted per source bibliography (a PMID cited by two monographs counts twice): 2,456 Randomized Controlled Trials, 773 Meta-Analyses, 653 Systematic Reviews. 23 citation-year versus PubMed-year mismatches are flagged as possible wrong publisher links and not corrected. Publication type and year describe the cited study, not whether it supports a claim.

### Superseded October 27 findings

The following findings described the October 27 capture and no longer apply to the recaptured dataset: all ten `interactions with conditions` sections lacked substantive descriptions; 1,120 standalone `more` controls remained across 61 of 176 sections; the References sections held navigation instead of bibliographies (8,613 raw citation-link objects, 4,914 distinct URLs); and 1,310 extraction issues. The October 27 NatMed records also lacked record-level `source_batch_id` values, the original browser batches were unavailable locally, and the signed-in relay extension was disconnected; the recaptured records now carry a `source_batch_id`. Placeholder-only sections (`None known.`) still produce `placeholder_not_negative_evidence` issues (7), not negative-risk assertions.

### Freshness and provenance

Page-update dates are not study publication dates or independently certified freshness. The saved pages state these literature-review cutoffs:

| Recorded literature-review cutoff | Captured monographs |
| --- | --- |
| February 13, 2026 | Lactobacillus acidophilus |
| July 22, 2026 | Fish Oil; Melatonin |
| August 20, 2026 | Vitamin B12; Iron |
| September 16, 2026 | Magnesium; Vitamin D; Creatine |
| October 20, 2026 | Ashwagandha; Turmeric |

The stated literature-review cutoffs are unchanged by the recapture. The NatMed records now carry October 28 capture timestamps and hash-bound raw HTML; neither certifies original-source completeness without human review.

### Reddit sampling and annotation

- Searches are bounded, all-time/newest-first samples, not a representative population or continuous historical archive.
- 3,595 records inherit topic labels from their threads; those are not 3,595 direct supplement mentions or usable clinical claims.
- Repeated text includes subreddit rules and safety boilerplate: 24 identical-text groups cover 230 records, including a rules message repeated 134 times. Filter/annotate these before selecting evaluation questions; do not treat them as independent experiences.
- Sixty own-text comments reference 19 threads whose post is not saved. Some direct parents are also absent. Thread IDs support grouping, not universal conversation reconstruction.
- Human relevance judgments are not yet supplied. Synthetic test scores are not corpus Recall/MRR results.

## Collection decision — October 28 (executed)

**Repair and recapture the ten NatMed sources; do not rewrite the entire scraper
or increase Reddit volume yet.** This was carried out on October 28 (see the recapture section above). Additional anecdotes cannot recover professional monograph content.

The saved Reddit corpus contains 1,285 own-text records across all ten topics.
A conservative mechanical screen retained non-duplicate own-text records with a
question mark and a saved thread post:

| Frozen partition | Candidate records | Distinct threads |
| --- | ---: | ---: |
| Tuning | 79 | 48 |
| Held-out | 298 | 179 |
| Total | 377 | 227 |

This screen used NFKC/casefold/whitespace-normalized exact-text deduplication
against the corpus. It is **not** human question selection, de-identification,
clinical answerability assessment or a relevance benchmark. Start an annotation
pilot with these candidates. Collect targeted Reddit examples only if that pilot
shows missing topics/question types or insufficient usable held-out coverage;
do not broaden a frozen benchmark silently.

### Implemented collection method

- Reveal hidden `.custom-details-content` blocks in place by class manipulation
  (no clicking) and take the rendered text; the settled-text and identity gates
  still apply, and a target whose hidden details cannot be revealed and verified fails.
- Fetch each monograph's References page as authenticated same-origin server HTML
  (the rendered page is paginated), bound to the same monograph ID; subscriber/error
  pages fail the target rather than being saved as captures.
- Save raw HTML scrubbed by `natmed.scrub_source_html`, bound per record by
  `source_html_sha256`; the importer validates and persists it atomically with the
  database commit.
- Validate document URLs, capture timestamps, content hashes and entire batches
  before database mutation. Failed standalone recaptures preserve prior records
  and never write successful checkpoints.
- Keep bibliography text in source `reference_documents`, not copied into each
  passage. Source approval must cover the current combined reference fingerprint;
  changed or corrupted reference snapshots cannot reuse the old approval.
- Completion UI distinguishes a finished capture run from required human
  source/medical review. No path automatically approves clinical evidence.

The pasted signed-in script and the optional Playwright collector share this method.
The live smoke and import results are in the recapture section above. Offline
browser fixtures were synthetic and disposable, never added to the dataset.

### Recapture outcome (replaces the earlier credentials blocker)

The earlier blocker — no authenticated session (the Chrome relay extension was disconnected, the Edge login form was empty, and an unauthenticated References request returned **Exclusive Subscriber Content**) — is obsolete. An authenticated session was obtained and the ten-source recapture completed on October 28. See the recapture section above for results.

## Repository governance audit — October 28

| Finding | Action and remaining risk |
| --- | --- |
| The repository was **public** from creation (2026-10-27 16:55 UTC), contrary to the documented private-licensed-data decision. NatMed monograph text was therefore publicly downloadable for about 28 hours. | Visibility restored to **private** on October 28. The API reported zero forks, stars and watchers. Uncounted anonymous clones or crawls cannot be ruled out or undone. |
| Credentials or tokens in history | All 14 commits across every branch and PR ref, including decompressed dataset archives and the SQLite snapshot, were scanned. No credentials, tokens or keys were found; three regex matches were reviewed as false positives. Commit emails use GitHub noreply addresses. No Actions secrets are configured. |
| PR #2 was an older, unfixed subset of PR #4 | Closed as superseded; its branch is retained. Merging it would have reintroduced copied review-flag admission and other defects fixed in #4. |
| CI ran twice per PR push and used Node 20-era action majors | Push runs are now limited to `main`; PRs run once, superseded runs are cancelled and jobs have time limits. `checkout`, `setup-python` and `setup-node` moved to v7. Private-repository Actions minutes are billed; Windows jobs cost more. |
| Merged branches remained | Two merged branches were deleted; they can be restored from their merged PRs. Branch deletion on merge is enabled. |
| `main` has no protection; private secret scanning unavailable | The current free plan rejects branch protection and secret scanning for private repositories. Write collaborators can force-push or delete `main`. GitHub Pro—available through GitHub Education for eligible students—would enable protection that requires CI and blocks force-pushes. |


## Verification actually exercised

Rerun after the October 28 recapture:

- 280 Python tests and 14 offline browser-collector behavior tests pass locally.
- All 12 dataset/clinical archives pass compressed and extracted SHA-256 checks, including the new raw-HTML archive.
- All 6,250 passages bind to their exact source section, word window, hash and source-derived metadata.
- Reviewed-only retrieval over the 1,179 NatMed passages returns no evidence (all sources pending), in a 0.55 s local median per query (diagnostic only).
- Earlier real-data probes (partial numeric quantities, forged review flags, mismatched passage identities, forced approval) are covered by the regression suite that passed above.

October 28 recapture:

- Actual extraction from the saved HTML produced 1,269 annotations, all pending, none approved.
- Imported through the real batch importer with 0 binding errors for the live smoke batch; datasets regenerated deterministically.
- All 4,880 Reddit records byte-identical; 7,992 `MENTIONS` edges identical; thread-split membership identical.
- Reference-row counts equal the site's "of N entries" totals for all ten monographs.

No claim of complete publisher capture without human review, reviewed medical correctness or real benchmark performance is made.

## What may proceed

| Next-stage use | Readiness |
| --- | --- |
| Inspect structured pending values and source excerpts | Supported, with coverage/issue report |
| Source-grounded human annotation and extraction review | Supported; retain unknowns, qualifications and pending status |
| Bounded research BM25 retrieval | Supported; all 6,250 passages re-verified against their sources |
| Grouped relevance annotation and evaluation tooling | Supported; real scoring requires human qrels and held-out protocol |
| Provenance/MENTIONS graph | Supported; not a clinical-relation graph |
| Approved clinical graph, Safety Intercept or recommendations | Blocked pending qualified human source/claim review (capture completeness is no longer the blocker) |

## Required handoff

1. Have qualified reviewers compare the captured monographs and bibliographies with the licensed originals and review extracted associations and unresolved issues; correct captures or annotations without guessing missing content.
2. Record hash-bound source-completeness approval and human claim review before admitting clinical assertions.
3. UMLS mapping and DSLD product/label collection.
4. De-identify and annotate evaluation questions/relevant passages using the frozen thread split (QA qrels); report real metrics only after those judgments exist.

Data products: [`datasets/clinical_claims.sample.json`](datasets/clinical_claims.sample.json), [`datasets/clinical_claims.jsonl.gz`](datasets/clinical_claims.jsonl.gz), [`datasets/clinical_extraction_report.json`](datasets/clinical_extraction_report.json), [`datasets/pubmed_report.json`](datasets/pubmed_report.json).
