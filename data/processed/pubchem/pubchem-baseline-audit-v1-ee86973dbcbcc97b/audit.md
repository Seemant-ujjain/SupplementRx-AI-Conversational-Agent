# PubChem baseline audit

```json
{
  "source_labels": 400,
  "query_groups": 739,
  "original_name_variants": 753,
  "dsld_occurrences_verified": 3391,
  "occurrence_kinds": {
    "form": 1052,
    "ingredient": 2339
  },
  "search_status": {
    "ok": 228,
    "not_found": 511
  },
  "queries_with_response_order_changed_by_collector": 6,
  "single_candidate_queries": 221,
  "ambiguous_queries": 7,
  "compound_records": 239,
  "candidate_edges": 272,
  "cids_reached_by_multiple_queries": 30,
  "synonym_entries": 46426,
  "exact_duplicate_synonym_entries_within_cid": 0,
  "normalized_synonyms_shared_across_cids": 74,
  "property_collision_groups": {
    "InChIKey": 8,
    "InChI": 8,
    "ConnectivitySMILES": 13,
    "MolecularFormula": 21,
    "Title": 0
  },
  "missing_iupac_names": [
    {
      "cid": "10475633",
      "title": "Arterolane"
    },
    {
      "cid": "92003852",
      "title": "Boron glycinate"
    },
    {
      "cid": "166596686",
      "title": "Cyanocobalamin"
    }
  ],
  "query_candidate_pairs_without_title_or_synonym_text_match": 3,
  "category_query_counts": {
    "Iron": {
      "queries": 157,
      "ok": 103,
      "not_found": 54
    },
    "Turmeric": {
      "queries": 69,
      "not_found": 56,
      "ok": 13
    },
    "Probiotics": {
      "queries": 260,
      "not_found": 206,
      "ok": 54
    },
    "Omega-3": {
      "queries": 92,
      "not_found": 69,
      "ok": 23
    },
    "Ashwagandha": {
      "queries": 40,
      "not_found": 31,
      "ok": 9
    },
    "Creatine": {
      "queries": 121,
      "not_found": 60,
      "ok": 61
    },
    "Vitamin B12": {
      "queries": 72,
      "ok": 31,
      "not_found": 41
    },
    "Magnesium": {
      "queries": 52,
      "ok": 30,
      "not_found": 22
    },
    "Vitamin D": {
      "queries": 58,
      "ok": 41,
      "not_found": 17
    },
    "Melatonin": {
      "queries": 12,
      "ok": 3,
      "not_found": 9
    }
  },
  "collected_from": "2026-10-28T03:46:55.494855+00:00",
  "collected_to": "2026-10-28T03:51:37.094714+00:00",
  "mechanical_errors": 0,
  "approved_mappings": 0,
  "records_merged": 0
}
```

- Offline audit of the saved snapshot; no fresh PubChem queries or external chemistry validation.
- The collector sorts and deduplicates returned CID lists; CID order is not interpreted as confidence ranking. Original API order remains in response payloads.
- Queries cover DSLD ingredient rows, nested rows and forms, including co-ingredients; otheringredients are outside this collection scope.
- Category counts overlap and reflect DSLD retrieval provenance, not compound identity or clinical indications.
- A single returned CID is still an unreviewed mapping candidate; shared query terms, synonyms, formulas or connectivity strings do not establish ingredient equivalence.
- No-match means no result from this saved name lookup, not absence from PubChem. A botanical, mixture, organism or broad nutrient class need not correspond to one compound.
- Full structure strings and CIDs retain their distinctions. No stereochemical, salt, hydrate or parent-compound equivalence is inferred.
- Synonyms are source-provided labels, not approved identifiers, clinical claims or a universal merge dictionary.
- Missing IUPACName does not invalidate an otherwise present record. A collection timestamp is not a compound revision timestamp.
- Scope/path/hash and response consistency checks establish traceability, not correctness of ingredient-to-compound identity.
