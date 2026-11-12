# Reddit baseline and source-support audit

```json
{
  "records": 4880,
  "record_types": {
    "comment": 4593,
    "post": 287
  },
  "passages": 5071,
  "evidence_roles": {
    "user_report": 4880
  },
  "mention_scopes": {
    "thread_context": 3595,
    "own_text": 1285
  },
  "duplicate_text_groups": 24,
  "records_in_duplicate_text_groups": 230,
  "duplicate_passage_text_groups": 25,
  "duplicate_record_payload_groups": 0,
  "comments_without_saved_thread": 60,
  "comments_without_saved_parent": 152,
  "comments_with_no_parent_id": 99,
  "comments_with_parent_id_outside_sample": 53,
  "comments_with_either_context_gap": 159,
  "own_text_records_without_literal_alias_hit": 0,
  "deleted_removed_placeholder_records": 0,
  "graph_nodes": 4890,
  "graph_edges": 7982,
  "graph_edge_types": {
    "MENTIONS": 7982
  },
  "duplicate_directed_graph_edges": 0,
  "subreddit_date_coverage": {
    "Supplements": {
      "records": 2426,
      "earliest": "2026-09-21T19:02:42+00:00",
      "latest": "2026-10-27T07:18:22+00:00"
    },
    "herbalism": {
      "records": 2454,
      "earliest": "2020-06-27T19:59:59+00:00",
      "latest": "2026-10-22T20:29:59+00:00"
    }
  },
  "null_scores": 4880,
  "null_source_update_dates": 4880,
  "structural_source_errors": 0,
  "claims_validated": 0,
  "clinical_approvals": 0,
  "records_merged": 0
}
```

- Local snapshot audit; no current Reddit re-fetch or new upstream inspection.
- No Reddit clinical-claim annotation schema is supplied in the imported artifacts. NatMed clinical_claim.schema.json is not applied to Reddit.
- Validation uses explicitly implemented local record/type/ID/URL/timestamp checks, source hashes, passage word windows/context, and graph endpoints/topic consistency. This is not an upstream formal JSON Schema certification.
- thread_context topics are inherited context, not evidence the comment itself mentions, used or benefited from the supplement. Literal alias-hit checks are lexical diagnostics only.
- Missing thread/parent records may result from bounded collection; retain dangling references rather than inventing context.
- Repeated text can occur in distinct discussions; do not merge posts/comments solely on text, and do not count overlapping passages as independent reports.
- Score and dates are source metadata, not reliability scores or proof of clinical truth. No ratings, indications, doses, interaction claims or effectiveness conclusions are inferred.
- Date ranges describe this bounded saved sample, not a representative or complete Reddit archive. Existing source metadata identifies search-alias normalization, not approved terminology mappings.
- Source text can contain personal information even when usernames are absent; POC selection must avoid adding author/profile data. No de-identification is performed by this audit.
