# MeSH baseline audit

```json
{
  "source_labels": 400,
  "query_groups": 739,
  "source_name_variants": 753,
  "source_occurrences_verified": 3391,
  "search_status": {
    "not_found": 469,
    "matched": 270
  },
  "single_record_queries": 264,
  "ambiguous_queries": 6,
  "candidate_links": 276,
  "candidate_records": 247,
  "record_types": {
    "SCR_Chemical": 49,
    "SCR_Organism": 3,
    "TopicalDescriptor": 195
  },
  "shared_records_across_queries": 23,
  "unique_entry_terms": 270,
  "unique_rdf_subjects": 2360,
  "unique_rdf_statements": 24792,
  "repeated_triple_occurrences": 400,
  "subjects_with_scope_notes": 206,
  "records_missing_labels": 0,
  "records_missing_identifiers": 0,
  "records_without_tree_numbers": 52,
  "shared_label_groups_across_rdf_subjects": 802,
  "relation_counts": {
    "preferredMappedTo": 62,
    "mappedTo": 9,
    "narrowerConcept": 487,
    "relatedConcept": 64,
    "broaderConcept": 11,
    "broaderDescriptor": 281,
    "treeNumber": 421,
    "seeAlso": 67
  },
  "relation_targets_without_description": 791,
  "possibly_truncated_queries": 0,
  "available_years_start": [
    "current",
    "2026",
    "2025",
    "2024"
  ],
  "available_years_end": [
    "current",
    "2026",
    "2025",
    "2024"
  ],
  "available_years_unchanged": true,
  "collection_started": "2026-10-28T06:22:58.146429+00:00",
  "collection_finished": "2026-10-28T06:28:20.215400+00:00",
  "mechanical_errors": 0,
  "approved_mappings": 0,
  "records_merged": 0
}
```

- Offline audit of saved MeSH lookup/SPARQL responses, not a live vocabulary validation.
- Terms (T), concepts (M), descriptors (D) and supplementary records (C) have distinct roles. Shared labels across them do not imply duplicate entities.
- Candidate links resolve exact entry-term searches through concepts to records. Exact lookup and a single record do not establish ingredient/formulation equivalence.
- Repeated RDF triples can be repeated batch/context statements; compare subject, predicate and full RDF object including datatype/language. Preserve source contexts before graph deduplication.
- Tree numbers and broader relations describe vocabulary hierarchy, not clinical efficacy, chemical equivalence or product identity. Supplementary records need not have descriptor tree numbers.
- Relation targets outside the captured descriptions are not necessarily invalid links. This is a bounded subgraph, not the entire MeSH hierarchy.
- The current endpoint and unchanged available-year metadata do not pin every response to a verified immutable release. Retain request/capture timestamps and raw metadata.
- Scope notes are terminology descriptions, not independently validated clinical claims. No missing units, doses, ratings or indications are inferred.
- Query provenance covers DSLD ingredients/nested rows/forms including co-ingredients; otheringredients are outside collection scope. No-match is not absence under all terms.
