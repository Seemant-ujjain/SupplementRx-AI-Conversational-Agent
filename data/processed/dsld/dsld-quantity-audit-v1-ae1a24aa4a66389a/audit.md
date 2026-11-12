# DSLD quantity and serving audit

## Scope and limits

- This audit examines stored values, not actual product doses or label accuracy.
- NP is an unresolved source unit code. Its zero values must not automatically be interpreted as zero ingredient content. Its official semantics have not been verified.
- Zero quantities with named units and inequality operators are informational; they are not automatically errors.
- Serving-reference checks preserve original units and ranges. Out-of-range quantities may describe a daily total or another basis; do not automatically reject or correct them.
- Serving-unit text mismatches may be aliases; matching text is not proof of correct units.
- Note checking is limited to explicit mL numbers in mL serving notes. No exhaustive free-text or image verification, daily-value validation, or nested blend-total arithmetic is performed.
- Mass, IU, enzyme activity, energy, volume and nutrient-equivalent units are not universally interchangeable. No conversions are applied.
- Every finding includes a JSON pointer into the original label. Counts are occurrences and distinct labels per code; categories overlap.

## Findings

| Check | Occurrences | Labels |
|---|---:|---:|
| incomplete_daily_serving_range | 35 | 35 |
| inequality_amount | 24 | 14 |
| missing_quantity_serving_basis | 8 | 2 |
| ml_note_numeric_disagreement | 1 | 1 |
| np_unit_unresolved | 705 | 74 |
| quantity_basis_outside_serving_range | 67 | 9 |
| zero_amount_with_named_unit | 32 | 14 |

## Complete summary

```json
{
  "labels": 400,
  "ingredient_rows": 2339,
  "quantity_entries": 2392,
  "nested_ingredient_rows": 786,
  "np_entries": 705,
  "np_zero_entries": 705,
  "serving_definitions": 400,
  "quantity_unit_counts": {
    "mg": 1060,
    "NP": 705,
    "mcg": 204,
    "IU": 56,
    "{Calories}": 26,
    "g": 8,
    "ug": 1,
    "Gram(s)": 213,
    "DU": 3,
    "HUT": 3,
    "FCCFIP": 3,
    "CU": 3,
    "INVU": 3,
    "ALU": 3,
    "DP": 6,
    "GaIU": 3,
    "Endo-PGU": 3,
    "XU": 3,
    "HCU": 3,
    "BGU": 3,
    "Kcal": 1,
    "Calorie(s)": 62,
    "grams": 2,
    "mL": 1,
    "mcg DFE": 12,
    "mcg RAE": 1,
    "mg NE": 1
  },
  "serving_unit_counts": {
    "Capsule(s)": 162,
    "Tablet(s)": 82,
    "mL": 24,
    "Gram(s)": 25,
    "Softgel(s)": 29,
    "Gummy(ies)": 2,
    "tsp": 7,
    "Caplet(s)": 10,
    "Vegicap(s)": 1,
    "Soft Chew(s)": 4,
    "White Tablet(s)": 1,
    "Drop(s)": 3,
    "Vegetarian Capsule(s)": 11,
    "Vege Capsule(s)": 2,
    "Easy-to-swallow Veggie Capsule(s)": 1,
    "Softgel Capsule(s)": 2,
    "Bear(s)": 2,
    "Yellow Softgel Capsule(s)": 1,
    "Lozenge(s)": 4,
    "Veggie Capsule(s)": 11,
    "Veg Capsule(s)": 1,
    "Vegetable Capsule(s)": 7,
    "White Caplet(s)": 1,
    "Scoop(s)": 1,
    "Veggie Cap(s)": 1,
    "Teaspoon(s)": 1,
    "Gummie(s)": 1,
    "mg": 1,
    "Omega-3 Softgel(s)": 1,
    "Measuring Spoon(s)": 1
  },
  "operator_counts": {
    "=": 2368,
    ">=": 8,
    "<=": 2,
    "<": 13,
    ">": 1
  },
  "findings_by_code": {
    "incomplete_daily_serving_range": {
      "occurrences": 35,
      "labels": 35
    },
    "inequality_amount": {
      "occurrences": 24,
      "labels": 14
    },
    "missing_quantity_serving_basis": {
      "occurrences": 8,
      "labels": 2
    },
    "ml_note_numeric_disagreement": {
      "occurrences": 1,
      "labels": 1
    },
    "np_unit_unresolved": {
      "occurrences": 705,
      "labels": 74
    },
    "quantity_basis_outside_serving_range": {
      "occurrences": 67,
      "labels": 9
    },
    "zero_amount_with_named_unit": {
      "occurrences": 32,
      "labels": 14
    }
  },
  "severity_counts": {
    "review": 816,
    "info": 56
  },
  "labels_with_review_or_error": 100,
  "out_of_serving_range_entries_within_computed_daily_range": 52,
  "missing_quantity_rows": 0,
  "nonnumeric_or_negative_amount_entries": 0,
  "unresolved_serving_references": 0,
  "serving_unit_text_mismatches": 0,
  "records_corrected": 0,
  "records_removed": 0,
  "unit_conversions_applied": 0
}
```

Detailed source values, context and JSON pointers are in audit.json. No values were corrected.
