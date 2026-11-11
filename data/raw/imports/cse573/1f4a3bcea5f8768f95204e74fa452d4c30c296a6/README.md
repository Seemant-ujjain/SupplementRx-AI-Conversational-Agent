# SupplementsRx collection pipeline

Repository: `CSE573`. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the supplied
proposal, data-source guidance, current decisions, completed work, and remaining
research stages. The collected dataset is included as compressed archives;
run `python3 scripts/restore_dataset.py` after cloning to restore `data/` and `exports/`.

For a plain-language explanation of the sources, collection dates, scraping
method, output format, and limitations, see [DATASET_SPEC.md](DATASET_SPEC.md).

For the structured values themselves, start with the
[readable pending-claim sample](datasets/clinical_claims.sample.json), then the
[coverage/issue report](datasets/clinical_extraction_report.json). Check
[next-stage readiness](READINESS_AUDIT.md) before using them: pending annotations
are not medically approved clinical facts.

Collect Reddit discussions and NatMed professional monographs for these ten topics:
Magnesium, Vitamin D, Ashwagandha, Melatonin, Omega-3, Vitamin B12, Iron,
Turmeric, Probiotics, and Creatine.

## Collected prototype dataset — Reddit October 27, NatMed recaptured October 28, 2026

The bounded Reddit collection and the ten selected NatMed sources are saved:
4,880 Reddit posts/comments, 10 NatMed monographs, and 6,250 RAG passages from
4,890 total records. The ten NatMed monographs were recaptured on October 28
from an authenticated session (see below); the Reddit records are unchanged.
`data/collection_summary.json` is the original October 27 completion record and
still lists 5,538 passages. Every captured monograph has the five main
clinical sections, its condition-interaction sections and its full bibliography;
this is an extraction check, not medical validation. Omega-3 is represented by
Fish Oil, and Probiotics by Lactobacillus acidophilus. Preserve those
source-specific limits downstream.

The import/export pipeline uses Python 3.10+ and the standard library. Browser
collection optionally uses a Python 3.12 virtual environment with Playwright;
virtual environments are not included in the repository.

```sh
git clone https://github.com/ARYN26/CSE573.git
cd CSE573
python3 scripts/restore_dataset.py
python3 -m supplementsrx status
python3 -m unittest discover -s tests -v
```

## Existing Reddit data

Use your current scraper's JSON or JSONL immediately:

```sh
python3 -m supplementsrx reddit-import /absolute/path/to/reddit_output.json
```

Supported input shapes:

- Native Reddit listing JSON (`kind: Listing`, `data.children`).
- Native thread JSON (post listing followed by a comment listing), including nested replies.
- A list of flat posts/comments, a `posts` wrapper, or one JSON object per JSONL line.
- Flat posts with nested `comments` lists; the importer carries the parent thread ID to children.

Flat posts need `id`, `title`, and `selftext` or `text`. Flat comments need `id`, `body`,
and either `link_id`/parent thread context or a `permalink`. Include `subreddit`,
`created_utc`, `parent_id`, and `permalink` when available. Usernames and profile data
are not copied into the normalized store. Unsupported input fails with a clear error;
it is not silently treated as an empty successful import.

## Old Reddit collection — no API keys

### Running in your existing signed-in Chrome

The reusable collectors run inside your existing Chrome session; cookies and
passwords are not exported or copied. Open Old Reddit or the NatMed home page,
paste the corresponding script in that tab's developer console, then use its
configuration file picker:

- `browser/reddit_signed_chrome.js`: select `config/supplements.json`.
- `browser/natmed_direct_signed_chrome.js`: select `config/natmed_manifest.json`,
  then click **Start source window** and allow its popup.

Reddit derives all topic aliases and subreddits from the selected configuration,
starts without historical checkpoints, and attempts all 30 default searches.
Each search is bounded to 20 threads and 50 rendered comments per thread.
The NatMed runner visits every configured monograph, including Creatine, verifies
the observed title and monograph ID, reveals hidden detail blocks in place, saves
the numeric citation links, scrubbed raw HTML and the server-fetched bibliography
(see [Targeted clinical recapture](#targeted-clinical-recapture-and-references)).
Fish Oil and Lactobacillus acidophilus remain source-specific mappings, not
clinical equivalents of every omega-3 formulation or probiotic strain.

Keep the tabs containing the **SupplementsRx** overlays open while collection
runs. They show live progress. Downloaded JSON batches have filenames beginning
`supplementsrx-reddit-` or `supplementsrx-natmed-`. Chrome's requested multiple-file
downloads for this collection have been allowed. The importer normalizes new
batches into SQLite and regenerates the exports:

```sh
python -u -m supplementsrx.watch_downloads
```

The importer watches Downloads for up to two hours and accepts only batches with
the collector metadata marker. It decodes JSON as UTF-8, validates the full batch
before mutation, and persists successfully imported content identities across
restarts. A failed batch does not commit a subset of its records. Older clinical
captures cannot replace newer ones. Accepted batches regenerate the exports.
Saved totals are in `data/live_collection_status.json`; the historical completed
prototype snapshot is in `data/collection_summary.json`.

Keep the collection tabs open. Use **Stop** to interrupt a run; closing/reloading
also interrupts in-page execution. An interrupted or partly failed run is not
complete. Inspect the overlay and downloaded batch metadata for failed targets
and successful query identities. Re-running starts a fresh bounded search;
stable IDs deduplicate records and durable batch identities prevent replaying
the same downloaded content.

### Targeted clinical recapture and References

Do not collect more Reddit merely to fill clinical gaps. The October 28 recapture
closed the collapsed-content and missing-bibliography gaps in the ten NatMed
captures; what remains is qualified human review
([the collection decision](READINESS_AUDIT.md#collection-decision--october-28-executed)).

NatMed pages are server-rendered, but about two-thirds of each monograph was hidden
in collapsed `.custom-details-content` blocks behind 300+ "more" toggles that the
earlier `innerText` capture never saved. The signed-in NatMed runner and the optional
Playwright collector now:

1. reveal the hidden blocks **in place** by class manipulation (no clicking) and take
   the rendered text; a target whose hidden details cannot be revealed and verified fails;
2. save the raw page HTML scrubbed by `natmed.scrub_source_html`, which removes all
   `<script>`/`<noscript>` elements (they embed account id, session id and IP) and
   session parameters without changing the text;
3. fetch the monograph's References page as authenticated same-origin server HTML,
   because the rendered page is DataTables-paginated and shows only 10 rows.
   Subscriber/error pages, missing links and insufficient citation cues fail the
   target rather than being saved as successful captures.

The optional Python collector also refuses to replace a source or checkpoint an
incomplete attempt. An unsupported publisher layout needs inspection, not a guessed success.

Bibliographies are stored in the source record's `reference_documents[]`: `url`,
`title`, `text` (a title line plus `N. citation[ PMID: x]` lines), `captured_at`,
`content_hash`. They remain pending source documents, not validated studies. Passage
exports carry only `reference_documents_sha256`, avoiding full-bibliography
duplication. The raw HTML is archived as `datasets/natmed_source_html.jsonl.gz`
(restores to `data/natmed_source_html.jsonl`) and bound to each record by
`source_html_sha256`. The importer validates identity, timestamps, hashes and the
HTML, and persists the HTML atomically with the database commit; observed
reveal/citation flags never grant medical completeness.

**October 28 result.** The ten monographs were recaptured from an authenticated,
user-controlled Edge session and imported through the real batch importer
(`watch_downloads.process_batch`). Magnesium grew from 52.6k to 146.0k characters;
monographs are now about 55k–228k characters. Parsed bibliography rows equal the
site's rendered "of N entries" totals for all ten: 6,435 references (Creatine 544,
Magnesium 965, Vitamin D 628, Ashwagandha 137, Melatonin 1,022, Fish Oil 1,062,
Vitamin B12 534, Iron 666, Turmeric 586, L. acidophilus 291). 55 inline citation
reference numbers are absent from the publisher bibliography (Vitamin D 30, Fish Oil
10, Creatine 6, Turmeric 4, Iron 3, Melatonin 1, Vitamin B12 1; none for Magnesium,
Ashwagandha or L. acidophilus): a publisher-side gap, reported and not corrected.
A live smoke of the pasted script on live Ashwagandha reported complete, 59 detail
blocks revealed, 137/137 references and 0 inline references missing; that batch
imported through the real importer with 0 binding errors. Login details are
deliberately not committed.

To recapture again, inspect the working exports rather than silently mixing them
with the checked-in dataset:

```sh
python -m supplementsrx clinical-review --records exports/records.jsonl --report data/clinical-recapture/source_review.json
python -m supplementsrx extract-clinical --records exports/records.jsonl --html data/natmed_source_html.jsonl --destination data/clinical-recapture
python -m supplementsrx validate-claims data/clinical-recapture/clinical_claims.jsonl.gz --records exports/records.jsonl
```

The commands use the active Python 3.10+ interpreter (`python3` on systems where
that is its name). Keep raw monograph/reference snapshots, review gaps and
fingerprints together; update frozen dataset/split versions deliberately.


### Standalone browser or HTTP command

The default Reddit collector reads **Old Reddit HTML**, including search pages,
post bodies, and rendered nested comments. It does not call Reddit JSON/OAuth API
endpoints and does not need `.env` or API credentials.

```sh
.venv/bin/python -m supplementsrx reddit-collect --max-posts 20 --max-comments 50
```

The collector opens a visible browser. Complete normal Reddit sign-in if asked,
then press Enter in the terminal once discussions are visible. Login cookies stay
in memory for that run and are not written to a browser profile/session file.
The anonymous Old Reddit probe on this machine redirected to `/login/?reason=lor2`,
so browser mode is the default. If anonymous access works in your environment,
you can use `--http` for standard HTTP fetching without opening a browser.

Defaults cover `r/Supplements`, `r/Nootropics`, and `r/herbalism`. The above command
processes at most 20 threads per supplement per subreddit and up to 50 comments
present in each rendered thread. Collapsed/load-more comments are not expanded.
These limits produce a bounded sample, not a complete historical archive. Search
can miss comments in posts whose searchable content does not mention a supplement.

Requests are paced at least three seconds apart. Standard HTTP mode also retries
429/transient server errors. Each fully processed search page is checkpointed.
Run the same command to resume; use `--refresh` for a new search. Stable source IDs
prevent duplicate normalized records. Login, block pages, and unrecognized markup
produce explicit errors rather than being counted as successful empty results.
The legacy HTML selectors are based on Reddit's published
[search-result template](https://github.com/reddit-archive/reddit/blob/master/r2/r2/templates/searchresultlink.html),
and are fixture-tested. Old Reddit discussions were also verified as accessible
in your existing Chrome session. The new collector has not yet completed a live
signed-in collection run; its fresh browser requires its own normal login.

Refresh rendered thread edits and explicit `[deleted]`/`[removed]` items with:

```sh
.venv/bin/python -m supplementsrx reddit-reconcile
```

This revisits Old Reddit HTML and regenerates this project's exports. A missing
or collapsed comment cannot be confirmed as deleted from HTML alone, so it remains
unverified. This is a material limitation of HTML reconciliation; it cannot certify
that all source deletions have been applied. Copies made elsewhere also need updating.

Observed edits that lose all target-topic relevance are removed rather than
leaving obsolete text. When an observed parent changes topic or becomes
ineligible, inherited comment topics are updated or removed; independent
own-text matches remain eligible.
No recurring job is installed.

An optional API alternative remains available as `reddit-api-collect` and
`reddit-api-reconcile`. Only those explicitly named commands use `.env.example`,
approved Reddit OAuth credentials, and `/api/info`. They are separate from the
default Old Reddit workflow. Their authentication follows Reddit's
[application-only OAuth documentation](https://github.com/reddit-archive/reddit/wiki/OAuth2#application-only-oauth).

## NatMed Pro

The October 28 recapture used an authenticated, user-controlled Edge session. The
renewal receipt is a billing record; sign in at [NatMed](https://naturalmedicines.therapeuticresearch.com/Home/ND)
using the credentials from your existing data sources document. This code does
not contain that account's password. TRC confirms that the current platform
uses the [same login and primary website address](https://info.trchealthcare.com/now-live-natmed-pro-website).

### Collect through an interactive browser

Use Python 3.12 or 3.13 for the optional browser environment if Playwright's
dependencies do not support your newer system Python:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[browser]'
python3 -m playwright install chromium
python3 -m supplementsrx natmed-collect --review
```

The collector opens a fresh visible browser. Sign in yourself and press Enter
in the terminal when your account is visible. It uses an in-memory browser context;
it does not save passwords, a browser profile, cookies, or session tokens. Your
Chrome login remains separate from this fresh collection browser.

`config/natmed_manifest.json` now contains verified source URLs for all ten target
topics from the completed signed-in Chrome run. For any newly added unset
entry, the collector opens the actual NatMed search page, lists professional
monograph links if they load, and asks you to choose a result or paste the exact
URL. It saves that selection for later runs. This is a one-time source mapping
step, not an assertion that a broad category is clinically interchangeable with
an individual ingredient. Add multiple manifest rows when necessary (especially
for Omega-3 forms and individual probiotic organisms/strains).

After mapping, it visits each URL, reveals the collapsed detail blocks in place,
captures the rendered text, numeric reference links, scrubbed raw HTML and the
server-fetched bibliography, validates clinical section presence, and stores
source excerpts. A capture whose hidden details or bibliography cannot be
verified is rejected, not stored. `--review` pauses before each capture.
Later runs can omit `--review`; completed monographs are checkpointed. Use
`--refresh` to recapture updates. A skipped/missing source stays missing in the
coverage report. The October 28 live smoke exercised the pasted signed-in script;
this Playwright collector is not covered by that run.

### Import saved monographs

Alternatively, save an expanded professional monograph as UTF-8 HTML or text.
Make a manifest with entries like:

```json
{
  "monographs": [
    {
      "supplement": "Creatine",
      "title": "Creatine",
      "url": "https://naturalmedicines.therapeuticresearch.com/IngredientsTherapiesMonographs/Pro?id=873",
      "file": "creatine.html",
      "captured_at": "2026-10-27T00:00:00+00:00"
    }
  ]
}
```

File paths resolve relative to that manifest. Run:

```sh
python3 -m supplementsrx natmed-import --manifest /absolute/path/to/manifest.json
```

Source text is preserved with its section labels and qualifications. Extracted
`clinical_section_excerpts` cover safety, effectiveness, dosing, adverse effects,
drug/supplement/condition interactions, references, and other recognized headings.
They are text excerpts, not machine-validated dosage or interaction facts.
Saved HTML imports preserve numeric/reference anchor URLs, resolving relative
links against the source URL. Plain-text imports cannot reconstruct missing
anchor URLs; they retain only the references actually present in that text.
Login/short preview pages are rejected. Section checks are conservative quality
signals; they cannot certify full source completeness or clinical correctness.

## Output and downstream use

Each successful collection/import regenerates:

| File | Contents |
| --- | --- |
| `data/pipeline.sqlite3` | Normalized source records, checkpoints, run events |
| `exports/records.jsonl` | Complete normalized source records |
| `exports/passages.jsonl` | Overlapping, section-aware RAG passages with source metadata |
| `exports/kg_nodes.jsonl` | Supplement and source nodes |
| `exports/kg_edges.jsonl` | `MENTIONS` provenance relationships |
| `exports/coverage.json` | Per-supplement counts by source and limitations |

```sh
python3 -m supplementsrx status
python3 -m supplementsrx export
```

Global options precede the command, for example:

```sh
python3 -m supplementsrx --db data/experiment.sqlite3 --output exports/experiment reddit-import my_posts.json
```

Reddit passages carry `evidence_role=user_report`; NatMed passages carry
`evidence_role=clinical_reference`. Restrict clinical answering and safety rules
to reviewed clinical evidence. A Reddit comment without its own supplement
mention can be included using its thread context and is explicitly labeled
`mention_scope=thread_context`. Split evaluation data by `thread_id`, not by
individual comments/chunks, to avoid leaking the same discussion across sets.
Passages retain source titles, `mention_scope`, parent/thread IDs, source creation
timestamps, capture-quality flags, normalization metadata, and batch identity
when available. Clinical passages remain review-required; preserving metadata
does not validate a medical claim.

Aliases identify candidate mentions only. Formulations remain in source text;
no UMLS CUI is guessed. This delivers collection, cleaning, normalization to a
common record structure, section extraction, chunking, and provenance exports.
DSLD collection, MetaMap/UMLS mapping, reviewed clinical claims, Neo4j loading,
dense/hybrid retrieval, and the deterministic Safety Intercept remain later stages.
Rule-based pending clinical extraction and BM25 research retrieval are described
below. No live source corpus has
been mixed with test fixtures: the default database contains the live prototype
corpus described above, while synthetic test data stays in temporary directories.

## Clinical capture review and claim contract

```sh
python3 -m supplementsrx clinical-review
python3 -m supplementsrx extract-clinical
python3 -m supplementsrx validate-claims datasets/clinical_claims.jsonl.gz
```

`evaluation/clinical_review.json` is a generated structural audit of the ten
saved sources: section contents/coverage, source hashes and mappings, citation
URLs, bibliography coverage and possible encoding anomalies. It is **not medical
approval** or a comparison against the licensed originals
(`original_access: unavailable`, `source_completeness: unverified`,
`medical_validity: unverified`). No collection or automatic source/claim approval
is performed. The October 28 recapture closed the earlier flags for unexpanded
details and missing bibliographies; each capture still needs qualified human review
against the originals before evidence is approved.

`config/clinical_claim.schema.json` defines one verbatim clinical annotation.
`validate-claims` accepts UTF-8 JSONL/gzip, a JSON array, or a `claims` wrapper.
It checks the schema plus source identity, hash, section consistency, excerpt
offsets, source-specific ingredient mapping, annotation support and review gates.
Invalid annotations return a nonzero exit code and machine-readable errors;
malformed files or schemas produce a command error instead.

- `source` contains `record_id`, URL, full-text SHA-256, `section_index`,
  `section_heading`, and zero-based half-open Unicode codepoint `start`/`end`
  offsets. `source.excerpt` must match the section span and `claim_text` exactly.
- `ingredient.name` is the exact monograph title, not its broader topic.
  Formulation, strain, population, evidence grade and interaction details remain
  explicit nulls when unknown; no equivalence or unsupported value is inferred.
- `dose` records source text, a positive value or ordered range where safely
  parsed, exact units, frequency, qualified duration, route and regimen. Bounds
  such as `up to` and upper-intake limits are retained, not turned into exact
  recommended doses. Mixed-scale/ambiguous quantities remain text-only with issues.
  Population/age, loading/maintenance and unit associations are not borrowed from
  another dose. Unknowns are explicit nulls; units and scales are not converted.
- Effectiveness claims retain the exact condition and publisher effectiveness
  category, including negative and insufficient-evidence categories. Safety
  ratings retain source population qualifiers. Interaction rating, severity,
  occurrence and evidence grade are separate source-labelled fields.
- `review.state` is pending, approved or rejected. Approval/rejection requires
  reviewer identity and timestamp. Approval also requires source
  `requires_clinical_review=false`, `capture_quality.complete=true`, and a
  source-level `clinical_review` attestation with state/reviewer/time, matching
  content hash and `source_completeness_verified=true`.
  When separate reference snapshots exist, that source attestation also needs
  `reference_documents_sha256` matching the fingerprint in `clinical-review`.
  Changing a bibliography invalidates that approval even if monograph text is unchanged.

The validator checks provenance mechanics and recorded attestations, not a
reviewer's expertise or medical truth. The shipped dataset contains **1,269
rule-extracted pending annotations** (0 approved), not human-approved clinical
assertions. Keep them out of clinical recommendations, graph safety assertions and
safety rules.

| Pending category | Entries |
| --- | ---: |
| Dose statements | 85 |
| Effectiveness entries | 809 |
| Safety/warning entries | 107 |
| Described adverse-effect entries | 120 |
| Described interactions | 148 |

Of the dose statements, 71 contain parsed numeric quantities (`dose_extract` is
unchanged). All ten sources are represented. Extraction is structure-driven: it
reads the saved HTML (`supplementsrx/natmed_html.py`, `section_extract.py`;
`extract-clinical --html`, default `datasets/natmed_source_html.jsonl.gz`, each row's
hash must match the record's `source_html_sha256`). 49 extraction issues (codes in
`clinical_extraction_report.json`) document placeholders, ambiguous layouts, group
qualifications and unnormalized fields; there are no collapsed-content gaps. These
issues are not counts of validated clinical errors or of missing publisher facts.
Known gaps: Ashwagandha warnings embedded in its overview are not parsed
(`section_not_in_html`), and two entries with inline condition headings (Magnesium
PXE, Fish Oil heart transplant) yield issues, not claims.

Rows represent source entries, not distinct studies, patients or positive medical
effects. Effectiveness includes negative/insufficient-evidence categories;
adverse-effect descriptions may retain uncertainty or absence observations.
Each excerpt holds one entry with its detail paragraphs. An `effectiveness_rating`
may anchor on the group heading earlier in the same section (the validator rejects
it if a newer group intervenes), so use `indication`, `interaction.partner` and
`field_support` to identify the actual association. The safety count includes
Interactions-with-Conditions claims, with the condition in `population`
(`source.section_heading == "interactions with conditions"`); they describe caution
in that condition, not an indication for use.

Compound units such as `mg/kg/day` cannot be shortened to `mg`; bounds also apply
to parenthetical unit equivalents. Amounts referring to a named salt/formulation
are left text-only when they cannot safely be attributed to the titled ingredient.
Interaction metadata cannot cross into another partner's entry, and safety
ratings must retain the complete source line and its population qualifications.

The output is immediately inspectable on GitHub:
- [`datasets/clinical_claims.sample.json`](datasets/clinical_claims.sample.json):
  real pending values with source excerpts and offsets.
- [`datasets/clinical_claims.jsonl.gz`](datasets/clinical_claims.jsonl.gz):
  all pending annotations.
- [`datasets/clinical_extraction_report.json`](datasets/clinical_extraction_report.json):
  per-source/type/field coverage and individual gaps.
- [`datasets/clinical_claims_manifest.json`](datasets/clinical_claims_manifest.json):
  source/schema fingerprints and compressed/raw output hashes.

`python3 scripts/restore_dataset.py` now restores both source and clinical
archives. Clinical outputs appear under `exports/clinical_claims.jsonl`,
`exports/clinical_claims.sample.json` and `exports/clinical_extraction_report.json`.
Use `--manifest datasets/clinical_claims_manifest.json` to restore only these
outputs. Existing differing local files remain protected.

## Research retrieval and evaluation

These commands read the shipped gzip archives directly; restoration is optional.
Research commands do not open or mutate the ingestion database or regenerate
source exports.

```sh
python3 -m supplementsrx search "magnesium sleep" --top-k 3
python3 -m supplementsrx search "magnesium sleep" --reviewed-only
python3 -m supplementsrx split
```

`search` defaults to NatMed passages, not forum anecdotes. `--source reddit` or
`--source all` explicitly selects other research corpora. Results retain source
titles, section, URL, evidence role, topic/context and clinical-review flags.
Scores are lexical BM25 rankings, not clinical confidence or recommendations.
`search --records` supplies authoritative records; every indexed passage is bound
to its source hash, exact section and word window, title/URL/role and thread.
Reviewed-only retrieval additionally requires a current hash-bound human source
approval, complete capture and matching passage review metadata. Altering copied
flags cannot admit a pending or revoked source. Current sources yield no reviewed
results; the API also fails closed without authoritative records.
Topics, normalization status, references, citation links and their scope labels
are also checked against the source-derived export metadata. Changing a topic or
substituting an unrelated study URL invalidates the passage even when its text
and source hash are unchanged. Source approval is reassessed per query, not cached.

BM25 uses Unicode NFKC/casefold word tokenization without stemming or inferred
medical equivalence, `k1=1.5`, `b=0.75`, positive Robertson IDF, and binary
query-term weights. Equal scores sort by passage ID. Corpus statistics use
the selected source corpus before ranking; `--k1` and `--b` configure research
searches. No-match queries return no filler passages.

`evaluation/thread_split.json` freezes all Reddit records into whole-thread
tuning/held-out groups with a seeded, input-order-independent assignment and
canonical source-data fingerprint. Clinical source records remain unsplit as
the retrieval reference corpus. The approximately 20/80 fraction applies to
**thread groups**, not record counts or the future 50/200-question QA set.
Re-running `split` is idempotent; replacing a different manifest requires
deliberate `--overwrite`. Do not change a frozen split after tuning.
The fingerprint includes the full records, including clinical review metadata.
Recording an approval therefore requires a new versioned corpus/split pair;
preserve the previous artifacts rather than silently replacing a benchmark.

### Human-judged retrieval evaluation

No human-annotated QA/qrels file is included yet, so no corpus Recall/MRR score
is claimed. Supply UTF-8 JSONL with these fields:

| Field | Requirement |
| --- | --- |
| `id` | Unique question identifier |
| `question` | Nonempty question text, de-identified before use |
| `origin` | Reddit: `source=reddit` and `thread_id`; clinical: `source=natmed` and `record_id` |
| `relevant_passage_ids` | Nonempty, human-judged IDs from the selected passage corpus |
| `partition` | Optional; must match the origin group's frozen assignment |

```sh
python3 -m supplementsrx evaluate questions.jsonl --report evaluation/tuning_metrics.json
python3 -m supplementsrx evaluate questions.jsonl --partition heldout --allow-heldout --report evaluation/heldout_metrics.json
```

The default evaluates only tuning questions. Held-out scoring requires explicit
opt-in. Every Reddit split thread, including all comments/chunks, is excluded
from evaluation candidates, even with `--source all`; a question's own discussion
cannot retrieve itself. Unknown or filtered-out relevant IDs, unjudged questions,
cross-partition duplicate normalized questions, stale source fingerprints and
passages inconsistent with source text are rejected rather than silently scored.
Clinical-origin QA additionally requires `--clinical-groups` pointing to JSON
with `schema_version=1` and `partitions.tuning.group_ids` /
`partitions.heldout.group_ids` assigning entire NatMed record IDs without overlap.
This groups question origins; it does not remove clinical reference passages.

Reports contain per-query results, macro Recall@k and explicitly truncated
MRR@k, configuration, source/split/passage/question fingerprints, and the number
of unreviewed candidates. Synthetic regression scores are not research results.

Passage `citation_links` are limited to parenthetical numeric citation labels
actually present in that passage. This is syntactic attribution, **not verified
study support**. Raw records retain the whole-page link inventory separately; the
captured bibliographies live in `reference_documents`, and neither is a verified
study list.

### PubMed metadata

```sh
python3 -m supplementsrx pubmed-enrich [--email you@example.com]
```

Reads the captured bibliographies and fetches public NCBI E-utilities esummary
metadata only (title, journal, year, publication types, DOI) into
`datasets/pubmed_metadata.jsonl.gz` and `datasets/pubmed_report.json`; it modifies
no source record. Current result: 5,990 distinct PMIDs, 5,988 found; per-bibliography
publication-type counts (a PMID cited by two monographs counts twice) sum to 2,456
Randomized Controlled Trials, 773 Meta-Analyses and 653 Systematic Reviews; 23
citation-year vs PubMed-year mismatches are flagged as possible wrong publisher
links and not corrected. Publication type and year describe the cited study, not
whether it supports a claim.

## Verification and project gates

```sh
python3 -m unittest discover -s tests -v
node --test browser/collectors.test.cjs
python3 scripts/restore_dataset.py --verify-only
```

GitHub Actions runs Python checks and the restore/CLI smoke on Windows and Linux
with Python 3.10 and 3.12, plus offline browser collector regressions on Node 24.
These browser regressions do not establish live Reddit/NatMed compatibility.
GitHub currently rejects branch protection for this private repository under
the account's plan; keep licensed data private and review passing PR checks
before merging until paid-plan enforcement is available.

The October 27 audit corrected ingestion and export behavior. The October 28
authenticated NatMed recapture then replaced the ten monograph captures (collapsed
details revealed, bibliographies captured, raw HTML bound); it did not medically
validate the corpus. The original Oct 27 browser download batches were never found
on this workstation, so that capture's historical encoding fidelity was not compared.
See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md#current-delivery-gates) for the
dependency-ordered clinical review, evaluation, retrieval, and safety milestones.

See [READINESS_AUDIT.md](READINESS_AUDIT.md) for independently measured data gaps,
reproduced defects and fixes, and explicit next-stage readiness gates.

Non-editable installations package the three JSON configs under the Python
installation's `share/supplementsrx/config`; source/editable installs use the
checkout's `config/`. No arbitrary working-directory config is loaded. Licensed
datasets are not bundled into wheels: pass explicit `--records`, `--passages` and
output paths when running an installed package outside the checkout.
