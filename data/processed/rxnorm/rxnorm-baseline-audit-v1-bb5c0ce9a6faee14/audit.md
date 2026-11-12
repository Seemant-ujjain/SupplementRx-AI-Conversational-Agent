# RxNorm baseline audit

```json
{
  "source_labels": 400,
  "query_groups": 739,
  "name_variants": 753,
  "dsld_occurrences_verified": 3391,
  "search_status": {
    "matched": 313,
    "not_found": 426
  },
  "match_methods": {
    "exact": 282,
    "normalized": 31
  },
  "single_candidate_queries": 282,
  "ambiguous_queries": 31,
  "ambiguity_by_method": {
    "exact": 21,
    "normalized": 10
  },
  "concept_records": 287,
  "candidate_links": 347,
  "term_types": {
    "IN": 256,
    "PIN": 30,
    "MIN": 1
  },
  "suppression_flags": {
    "N": 287
  },
  "rxcuis_reached_by_multiple_queries": 46,
  "shared_normalized_property_names": 0,
  "shared_external_code_groups_excluding_spl_set_id": 31,
  "shared_code_groups_by_system": {
    "MMSL_CODE": 1,
    "DRUGBANK": 14,
    "UNII_CODE": 15,
    "SNOMEDCT": 1
  },
  "property_entries": 180747,
  "property_categories": {
    "ATTRIBUTES": 989,
    "CODES": 177517,
    "NAMES": 640,
    "SOURCES": 1601
  },
  "property_name_counts": {
    "GENERAL_CARDINALITY": 287,
    "PRESCRIBABLE": 223,
    "TTY": 287,
    "DRUGBANK": 226,
    "RxCUI": 287,
    "SNOMEDCT": 265,
    "SPL_SET_ID": 175552,
    "UNII_CODE": 268,
    "VUID": 226,
    "RXNAV_STR": 287,
    "RxNorm Name": 287,
    "Source": 1601,
    "RXNAV_HUMAN_DRUG": 152,
    "RXNAV_VET_DRUG": 35,
    "ATC": 102,
    "MMSL_CODE": 486,
    "USP": 105,
    "RxNorm Synonym": 66,
    "ACTIVATED": 4,
    "SCHEDULE": 1
  },
  "duplicate_property_triples_within_record": 0,
  "blank_synonym_fields": 226,
  "blank_umlscui_fields": 287,
  "query_candidate_preferred_name_mismatches": 193,
  "version_start": {
    "version": "05-Oct-2026",
    "apiVersion": "3.1.356"
  },
  "version_end": {
    "version": "05-Oct-2026",
    "apiVersion": "3.1.356"
  },
  "version_stable": true,
  "search_policy": {
    "allsrc": 0,
    "exact_then_normalized": true,
    "approximate": false
  },
  "category_counts": {
    "Iron": {
      "exact": 87,
      "not_found": 59,
      "normalized": 11
    },
    "Turmeric": {
      "not_found": 47,
      "exact": 20,
      "normalized": 2
    },
    "Probiotics": {
      "not_found": 160,
      "exact": 95,
      "normalized": 5
    },
    "Ashwagandha": {
      "not_found": 27,
      "exact": 13
    },
    "Creatine": {
      "not_found": 64,
      "exact": 48,
      "normalized": 9
    },
    "Omega-3": {
      "not_found": 57,
      "exact": 33,
      "normalized": 2
    },
    "Vitamin B12": {
      "exact": 56,
      "not_found": 16
    },
    "Magnesium": {
      "exact": 34,
      "not_found": 18
    },
    "Vitamin D": {
      "exact": 38,
      "not_found": 18,
      "normalized": 2
    },
    "Melatonin": {
      "exact": 7,
      "not_found": 5
    }
  },
  "collection_started": "2026-10-28T06:03:20.931956+00:00",
  "collection_finished": "2026-10-28T06:08:03.215770+00:00",
  "mechanical_errors": 0,
  "approved_mappings": 0,
  "records_merged": 0
}
```

- Offline audit of saved RxNorm responses. No live lookup or external identifier validation.
- Exact and normalized describe the recorded search method, not approved chemical identity. Preferred-name mismatch alone is not proof of a bad mapping.
- Normalized candidates may omit the queried form or return several related concepts. Preserve the full query, source occurrence, candidate set and review state.
- No-match is an outcome of this lookup strategy, not proof of absence from RxNorm. No approximate search was collected.
- Term types IN, PIN and MIN remain explicit; do not flatten all concepts into interchangeable ingredient identities.
- Shared IDs allow reuse of a concept node, not approval of all incoming ingredient mappings. Shared names/codes do not trigger automatic merging.
- SPL_SET_ID property counts reflect source property volume, not numbers of unique ingredients or independent clinical evidence. Shared-code review excludes SPL_SET_ID and retains code namespaces.
- Blank synonym/umlscui fields are distinguished from missing concept identity. No UMLS access or clinical efficacy validation is supplied by this collection.
- Category membership reflects overlapping DSLD retrieval provenance, including co-ingredients, not indication or efficacy.
- Query scope excludes DSLD otheringredients; collection timestamp and stable vocabulary version do not verify product currency.
