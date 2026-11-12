# DSLD baseline completion

## Summary

```json
{
  "labels": 400,
  "object_paths_profiled": 31,
  "field_profiles": 213,
  "normalized_name_candidate_groups": 71,
  "new_normalized_name_groups_beyond_exact_names": 4,
  "shared_compact_upc_sku_groups": 62,
  "shared_upc_sku_groups_crossing_exact_names": 10,
  "ingredient_occurrences": 5438,
  "distinct_ingredient_ids": 1847,
  "ingredient_ids_with_multiple_names": 0,
  "normalized_ingredient_names_with_multiple_ids": 291,
  "unii_shape_review_occurrences": 382,
  "upc_sku_present_labels": 348,
  "relationships": {
    "occurrences": 1739,
    "distinct_directed_relationships": 1720,
    "internal_occurrences": 823,
    "external_occurrences": 916,
    "distinct_external_targets": 451,
    "self_references": 0,
    "internal_edges_without_same_type_reverse": 5,
    "type_counts": {
      "Image difference, same product": 767,
      "Package size difference, same product": 775,
      "Bundle set": 53,
      "Flavor difference": 144
    }
  },
  "entry_date_min": "2011-10-26",
  "entry_date_max": "2025-09-25",
  "entry_year_counts": {
    "2011": 6,
    "2012": 19,
    "2013": 22,
    "2014": 45,
    "2015": 25,
    "2016": 30,
    "2017": 29,
    "2018": 31,
    "2019": 28,
    "2020": 67,
    "2021": 25,
    "2022": 23,
    "2023": 18,
    "2024": 17,
    "2025": 15
  },
  "date_issue_count": 0,
  "content_coverage": {
    "directions": {
      "statements": 455,
      "labels": 398
    },
    "precautions": {
      "statements": 1244,
      "labels": 366
    },
    "allergy_precautions": {
      "statements": 68,
      "labels": 61
    },
    "pregnancy_nursing_medication_precautions": {
      "statements": 308,
      "labels": 287
    },
    "contains_statements": {
      "statements": 550,
      "labels": 322
    },
    "does_not_contain_statements": {
      "statements": 454,
      "labels": 295
    },
    "general_statements": {
      "statements": 1257,
      "labels": 351
    },
    "fda_disclaimer": {
      "statements": 319,
      "labels": 316
    },
    "claim_classification_codes": {
      "labels": 400
    },
    "other_ingredient_list": {
      "labels": 387
    },
    "other_ingredient_free_text": {
      "labels": 1
    }
  },
  "records_merged": 0,
  "records_corrected": 0
}
```

## Scope and limits

- Profiles count missing keys relative to objects actually present at each nested path; empty parent containers do not contribute child objects.
- Placeholder tokens are candidates only. Literal Not Present or Not Applicable can be meaningful; no global null replacement is made. Zero and False are populated values.
- Normalized names use Unicode NFKC, case folding and whitespace only. No punctuation removal, fuzzy matching or semantic equivalence is asserted.
- UPC/SKU comparisons remove whitespace only, preserve leading zeros, and do not verify barcode ownership, check digits or product identity.
- Ingredient-ID/name and UNII-shape findings are profiling candidates, not approved cross-source identities or authoritative registry validation.
- Relationship targets outside the 400-label sample are unresolved locally, not necessarily broken links. Asymmetric source annotations need not be errors.
- Entry dates describe DSLD entry, not manufacture, revision, expiry or current availability.
- Statement coverage measures text availability, not accuracy, effectiveness, complete safety coverage or independent evidence. Claim codes are classification metadata, not extracted clinical claims.
- Baseline structural/quality profiling is now sufficient for shared-schema discussion together with previous quantity and duplicate audits. Label-image verification, clinical review, full semantic deduplication and source vocabulary definitions remain unresolved.

## Field meanings

- **label**: One source label record, not necessarily one unique commercial product.
- **id**: DSLD label identifier; use source namespace.
- **upcSku**: Source UPC/SKU text; not assumed unique or externally verified.
- **ingredientRows**: Listed ingredient tree; preserve nested membership and attached quantities/forms.
- **ingredientRows[].quantity**: Reported amount/operator/unit and serving reference; daily-value metadata is separate.
- **forms**: Ingredient forms attached to the parent ingredient; do not assign parent amount independently to each form.
- **otheringredients**: Separate ingredient list/free text; do not infer absent amounts or combine with active-dose rows.
- **statements**: Typed source label text (directions, precautions, general claims etc.); preserve original wording.
- **claims**: Source claim classification codes/descriptions, not independently validated clinical facts.
- **servingSizes**: Serving sizes, daily-serving bounds and notes; source nulls remain unknown.
- **labelRelationships**: Source-asserted label links with relation type; targets can lie outside the sample.
- **entryDate/events**: Source entry date and typed events; not a clinical freshness guarantee.
- **offMarket**: Source market-status flag; retain historical labels.
- **remaining_fields**: Observed JSON types/states are documented in field_profiles.json; business semantics not established by profiling alone.
