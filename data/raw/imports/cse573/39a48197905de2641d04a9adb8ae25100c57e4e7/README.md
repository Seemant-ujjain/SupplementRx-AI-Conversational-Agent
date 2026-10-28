# SupplementsRx collection pipeline

Repository: `CSE573`. See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the supplied
proposal, data-source guidance, current decisions, completed work, and remaining
research stages. The collected dataset is included as compressed archives;
run `python3 scripts/restore_dataset.py` after cloning to restore `data/` and `exports/`.

For a plain-language explanation of the sources, collection dates, scraping
method, output format, and limitations, see [DATASET_SPEC.md](DATASET_SPEC.md).

Collect Reddit discussions and NatMed professional monographs for these ten topics:
Magnesium, Vitamin D, Ashwagandha, Melatonin, Omega-3, Vitamin B12, Iron,
Turmeric, Probiotics, and Creatine.

## Completed prototype collection — October 27, 2026

The bounded Reddit collection and the ten selected NatMed sources are saved:
4,880 Reddit posts/comments, 10 NatMed monographs, and 5,538 RAG passages from
4,890 total records. Completion and exact source titles are recorded in
`data/collection_summary.json`. Every captured monograph has the five main
clinical sections and citation links; this is an extraction check, not medical
validation. Omega-3 is represented by Fish Oil, and Probiotics by
Lactobacillus acidophilus. Preserve those source-specific limits downstream.

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
the observed title and monograph ID, and preserves numeric citation links.
The obsolete search/frame NatMed implementation has been removed.
Fish Oil and Lactobacillus acidophilus remain source-specific mappings, not
clinical equivalents of every omega-3 formulation or probiotic strain.

Keep the tabs containing the **SupplementsRx** overlays open while collection
runs. They show live progress. Downloaded JSON batches have filenames beginning
`supplementsrx-reddit-` or `supplementsrx-natmed-`. Chrome's requested multiple-file
downloads for this collection have been allowed. The importer normalizes new
batches into SQLite and regenerates the exports:

```sh
.venv/bin/python -u -m supplementsrx.watch_downloads
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

Login was verified in Chrome on October 26, 2026: the site showed the subscribed
account and opened the professional Creatine monograph. The renewal receipt is a
billing record; sign in at [NatMed](https://naturalmedicines.therapeuticresearch.com/Home/ND)
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

After mapping, it visits each URL, clicks the observed `EXPAND ALL` controls,
captures visible text and numeric reference links, validates clinical section
presence, and stores source excerpts. `--review` pauses before each capture.
Later runs can omit `--review`; completed monographs are checkpointed. Use
`--refresh` to recapture updates. A skipped/missing source stays missing in the
coverage report. The live browser collector has **not** been run end to end;
the account login and monograph access were verified separately through Chrome.

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
DSLD collection, MetaMap/UMLS mapping, claim-level clinical relation extraction,
Neo4j loading, embeddings/retrieval, and the deterministic Safety Intercept are
later proposal stages and are not implemented here. No live source corpus has
been mixed with test fixtures: the default database contains the live prototype
corpus described above, while synthetic test data stays in temporary directories.

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

The October 27 audit corrected ingestion and export behavior; it did not
recollect or medically validate the corpus. Original browser download batches
were not present in this workstation's Downloads directory, so existing source
text could not be compared against those originals for historical encoding loss.
See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md#current-delivery-gates) for the
dependency-ordered clinical review, evaluation, retrieval, and safety milestones.
