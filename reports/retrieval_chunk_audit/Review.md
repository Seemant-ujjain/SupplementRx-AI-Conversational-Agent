# Existing retrieval chunks: audit and recommendations

This is a read-only audit of the current full-graph-concepts snapshot. Raw data, passages and graph files were left unchanged. No embeddings or retrieval index were created.

## Measurements

Exact token counts use `ncbi/MedCPT-Article-Encoder`, revision `d05a736da4bb84ee4057b7f7999485be6ed85465`, with tokenizers 0.22.2, truncation disabled and special tokens included. The model configuration allows 512 tokens. Adding title/section context was also measured as an illustrative sequence-pair template; the production template remains to be selected.

| Source | Existing text units | Median words | Maximum text tokens | Over 512 tokens |
| --- | ---: | ---: | ---: | ---: |
| NatMed | 1,179 passages | 220 | 584 | 2 |
| Reddit | 5,071 passages | 30 | 513 | 1 |
| DSLD | 6,463 label-statement assertions | 8 | 358 | 0 |

Adding the measured title/section context leaves the same three passages over the limit. DSLD statements are structured label assertions, not a previously generated chunk corpus. Its 6,463 assertions include the 6,462 preserved source statements plus one `other_ingredient_text` assertion whose text is “Ingredients”; this is not a missing-statement discrepancy.

## Findings

- **Coverage:** every NatMed/Reddit passage matches its whitespace-normalized source word slice. No nonempty source sections or source words are missing. This verifies captured-source coverage, not whether the original website capture was complete.
- **Boundaries:** 955 NatMed and 176 Reddit passages end before a punctuation-based sentence boundary. These are screening flags, not confirmed errors; overlap can preserve the sentence in an adjacent passage.
- **Claim context:** 473 of 1,269 NatMed claim excerpts do not fit wholly within any one existing passage. For 898 claims, no single passage contains both the complete excerpt and every field-support span. These counts overlap. Relevant evidence remains in the source and graph; retrieve linked context rather than assuming one passage is sufficient. This does not change pending clinical-review status.
- **Short text:** 1,878 Reddit passages have fewer than 20 words. Some need parent/thread context. 3,644 passages have `thread_context` mention scope versus 1,427 `own_text`; inherited supplement context must not be presented as a literal mention.
- **Repeated text:** NatMed has 5 exact-text groups with 11 extra occurrences; Reddit 25 groups with 207 extra occurrences; DSLD 952 groups with 2,909 extra occurrences. Repeated boilerplate is not proof of duplicate products or evidence. Preserve source-specific attribution even if identical embedding inputs reuse a vector.

## Examples

- NatMed `natmed:3684a1a282d205d7021e1e8c:s15:w2160`: 220 words become 584 tokens because the mechanism-of-action passage contains many numbered references. It ends “Melatonin has been reported as being”, with the continuation in source context.
- NatMed `natmed:9846bbe87087e6c66c605ff5:s5:w540`: an adverse-effects passage has 571 tokens; its citation-heavy content exceeds the limit despite using only 220 words.
- Reddit `reddit:t3_1x8aej0:s0:w180`: a discussion listing quantities and substances has 513 tokens, or 537 with title context. Its boundary splits “magnesium” from “oxide”. This is anecdotal discussion, not recommended dosing.

## Recommended next step

1. Create a separately versioned retrieval corpus linked to existing node IDs and source offsets; retain the frozen KG and raw records.
2. Use sentence/paragraph-aware boundaries with the exact tokenizer and reserved space for the chosen context template. Split oversized units; do not silently truncate.
3. Include ingredient and section context for NatMed, product and statement type for DSLD, and explicit parent/thread context for Reddit where needed. Preserve citations, confidence and review status as metadata.
4. Validate source coverage, token limits and representative context boundaries before building BM25 and embedding indexes. Keep clinical evidence and anecdotal discussion distinguishable.

Do not blanket-merge short statements or delete repeated text. Review the retrieval purpose of boilerplate and headings first.

## Reproduction and artifacts

- Run `scripts/audit_retrieval_chunks.py --tokenizer-dir <directory>` with Python and tokenizers 0.22.2 installed.
- The directory must contain `tokenizer.json`, `tokenizer_config.json`, and `config.json` from the pinned Hugging Face model revision, plus `metadata.json` containing the `model`, `revision`, and `files` hash mapping copied from `summary.json` → `tokenizer`.
- `summary.json` records tokenizer identity, exact input hashes, measurements and limitations.
- `items.jsonl` contains per-node measurements, source bounds and previews.
- `claim_context.jsonl` contains per-claim containment checks. These checks assess span coverage, not clinical validity.
- Tokenizer files and optional dependencies were downloaded into temporary directories, not added to the project environment or repository.
