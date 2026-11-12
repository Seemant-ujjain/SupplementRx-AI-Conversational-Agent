# DSLD ingredient and serving comparison

## Comparison rules

- Whitespace is collapsed; names and units otherwise remain exact. No synonym matching or unit conversion.
- Ingredient/form/quantity list order is ignored while multiplicity and nested ingredient membership are preserved.
- Compared ingredient core contains names, forms (excluding source IDs/categories), and quantity/operator/unit/serving-basis fields. Daily values, ingredient notes, IDs/categories/aliases and row order are outside this core.
- Serving comparison retains serving order, quantities, units, daily-serving ranges and inSFB. Notes are flagged separately; missing and empty notes can differ.
- Amount/form/daily-value differences are reported only for uniquely matched ingredient-name paths. Added/removed names may be renamings; ambiguous repeated paths are not paired arbitrarily.
- Other ingredients are flagged by raw JSON equality only. Equal compared core does not establish identical formulations, products or excipients.
- Label IDs in each pair define left/right; this is not chronological revision order. No dates or source relationships prove causality.

## Summary

```json
{
  "groups": 70,
  "labels": 206,
  "pairs": 304,
  "groups_all_pairs_same_compared_core": 27,
  "groups_with_core_difference": 43,
  "pair_status_counts": {
    "core_difference_needs_review": 157,
    "same_compared_core_identity_unresolved": 147
  },
  "group_flag_counts": {
    "daily_value_difference": 20,
    "ingredient_name_or_hierarchy_difference": 21,
    "ingredient_notes_or_description_difference": 50,
    "other_ingredients_raw_difference": 49,
    "form_difference": 20,
    "amount_or_basis_difference": 20,
    "serving_definition_difference": 16,
    "serving_notes_difference": 16,
    "ambiguous_repeated_ingredient_path": 1
  },
  "pair_flag_counts": {
    "daily_value_difference": 105,
    "ingredient_name_or_hierarchy_difference": 104,
    "ingredient_notes_or_description_difference": 193,
    "other_ingredients_raw_difference": 197,
    "form_difference": 58,
    "amount_or_basis_difference": 55,
    "serving_definition_difference": 29,
    "serving_notes_difference": 43,
    "ambiguous_repeated_ingredient_path": 1
  },
  "pairs_raw_ingredients_differ_but_compared_core_equal": 72,
  "records_removed": 0,
  "records_merged": 0
}
```

## Groups

| Brand / product | Label IDs | All pairs have equal compared core | Review flags |
|---|---|---|---|
| Advanced Nutrition by Zahler / Iron Complex | 260089, 278513 | False | daily_value_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Allergy Research Group / Magnesium Citrate | 20453, 54244, 54431, 78492, 182963, 184238, 208093, 233067, 233300 | True | daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Anabolic Laboratories / Clinical Magnesium | 53757, 67421 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Ancient Nutrition / SBO Probiotics Trinity | 305812, 309193 | True | ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| BPI Sports / Creatine Alkaline | 25731, 43261 | False | amount_or_basis_difference, other_ingredients_raw_difference |
| Barlean's Seriously Delicious / Omega-3 Pina Colada | 218715, 239256 | True | ingredient_notes_or_description_difference |
| Barlean's Seriously Delicious / Omega-3 Strawberry Banana Smoothie | 218739, 239258, 239259 | False | amount_or_basis_difference, ingredient_notes_or_description_difference |
| BetterYou / Iron Daily Oral Spray | 228638, 257287 | False | amount_or_basis_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| BioCare / Nutrisorb Vitamin B12 | 302255, 309759 | True | ingredient_notes_or_description_difference |
| Bluebonnet / Magnesium Citrate | 203860, 204235 | True | None |
| DC / Creatine | 244633, 265692 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Douglas Laboratories / Ferronyl Iron | 70032, 232593 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Douglas Laboratories / Timed Release Iron | 5328, 9329, 30584, 232304 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Douglas Laboratories / Ultra Preventive III with Iron | 5128, 8729 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Douglas Laboratories / Vitamin B12 | 5083, 10768, 56047 | True | ingredient_notes_or_description_difference |
| Endo-met Laboratories / Vitamin D | 229019, 229021 | True | None |
| Enzymedica / Digest Basic + Probiotics | 260008, 260011, 296494, 296495, 328918 | False | daily_value_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Enzymedica / Digest Gold + Probiotics | 32494, 32500, 32502, 259959, 259960, 296521, 296522, 296523, 328922, 328923, 328924 | False | daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Floradix / Calcium Magnesium | 33728, 33733 | False | ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference |
| GNC AMP Advanced Muscle Performance / Creatine HCl 189 | 210596, 229725, 229733 | False | amount_or_basis_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference |
| GNC Mega Men / High Potency Omega-3 | 69537, 304637 | False | daily_value_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_notes_difference |
| GNC Pro Performance / Hybrid Creatine Complex Fruit Punch | 19397, 25606 | False | amount_or_basis_difference |
| Gaia Herbs Single Herbs / Ashwagandha Root | 44575, 79402 | False | ambiguous_repeated_ingredient_path, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Global Healing / Vitamin B12 5000 mcg | 251652, 296933 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference |
| Good 'N Natural / Melatonin 3 mg | 10840, 10842, 10843, 58222, 58513, 58514 | True | other_ingredients_raw_difference |
| Herbal Hills / Ashwagandha | 74939, 74940 | True | None |
| Himalaya / Ashwagandha | 25775, 40304, 40487, 80192, 80197, 207207 | False | ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_notes_difference |
| InnovixLabs / Triple Strength Omega-3 | 248198, 276213 | False | amount_or_basis_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference |
| InnovixLabs / Ultra Strength Omega-3 | 276214, 334990 | True | ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Integrative Therapeutics / Magnesium Malate | 185029, 246459 | True | ingredient_notes_or_description_difference, serving_notes_difference |
| Jarrow Formulas / Magnesium Optimizer | 7841, 29547, 37432, 212304 | False | amount_or_basis_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| Kyolic / Kyolic Omega-3 | 42106, 42437, 205111 | False | ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| MegaFood / Turmeric Strength For Joint | 178192, 178208 | False | ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference |
| Nature's Answer / Turmeric-3 | 175180, 185095 | False | amount_or_basis_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| Nature's Bounty / Melatonin 1 mg | 3749, 17141, 29168, 49277 | True | None |
| Nature's Bounty / Turmeric 450 mg | 240133, 242577 | True | other_ingredients_raw_difference |
| Nature's Plus Herbal Actives / Ashwagandha 450 mg | 13653, 69019 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Nature's Way / Ashwagandha Standardized | 39970, 54522 | False | daily_value_difference, form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Nature's Way / Turmeric Standardized | 17865, 40608 | True | other_ingredients_raw_difference |
| NutriCology / Magnesium Citrate | 183861, 199602, 234782, 235550 | True | daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Nutrilite / Vitamin D | 177381, 208064, 239369, 246400, 246446 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_notes_difference |
| Pharmax / Probiotics | 70943, 71008 | True | None |
| ProCaps Laboratories / Vitamin B12 100 | 69735, 220773, 248631 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, serving_definition_difference, serving_notes_difference |
| ProCaps Laboratories / Vitamin B12 250 | 179049, 220792, 248598 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| ProCaps Laboratories / Vitamin B12 500 | 69491, 179055, 220795, 248632, 275294 | False | amount_or_basis_difference, daily_value_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| ProCaps Laboratories / Vitamin B12-100 | 30426, 30599, 30603 | True | None |
| ProCaps Laboratories / Vitamin B12-250 | 4735, 30248 | False | amount_or_basis_difference, daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| ProCaps Laboratories / Vitamin B12-500 | 4701, 30249 | False | amount_or_basis_difference, daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| Pure Encapsulations / Melatonin-SR | 185040, 277770, 299064 | False | ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_notes_difference |
| Puritan's Pride / Melatonin 3 mg | 62015, 73873, 242416 | True | None |
| Seeking Health / Adeno B12 | 174318, 210776 | True | None |
| Seeking Health / Ashwagandha Extract | 174353, 210829, 233452 | True | daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Spring Valley / Omega-3 Fish Oil | 178317, 178792 | True | other_ingredients_raw_difference |
| Sundown Naturals / Melatonin 3 mg | 30617, 30624 | True | None |
| Terry Naturally / Clinical Iron | 39804, 51697 | False | daily_value_difference, form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| The Vitamin Shoppe / B12 With Folic Acid Raspberry | 37231, 37232, 60199, 60206 | True | other_ingredients_raw_difference, serving_notes_difference |
| The Vitamin Shoppe / Calcium Citrate + Vitamin D | 35161, 35162, 55705, 55706, 57581, 57583, 180697, 180868 | False | amount_or_basis_difference, daily_value_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| The Vitamin Shoppe / Calcium Citrate Plus Magnesium & Vitamin D | 32075, 32079, 54642, 55238, 73905 | False | amount_or_basis_difference, daily_value_difference, other_ingredients_raw_difference, serving_definition_difference, serving_notes_difference |
| The Vitamin Shoppe / Multi Minerals With Boron & Vitamin D | 32728, 32733 | True | None |
| The Vitamin Shoppe / Multi Minerals with Boron & Vitamin D | 180292, 180743, 180745 | False | form_difference, ingredient_notes_or_description_difference |
| Thorne / Iron Bisglycinate | 181918, 204236, 204338 | True | ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Thorne Research / Iron Bisglycinate | 50539, 63802 | False | other_ingredients_raw_difference, serving_definition_difference |
| Trace Minerals Research / Ionic Iron 22 mg | 57059, 78959 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_notes_difference |
| USANA / Vitamin D | 16210, 201183 | False | amount_or_basis_difference, daily_value_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Vimerson Health / Turmeric Curcumin | 285511, 315533 | True | ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Vitamer Laboratories / Mega Magnesium | 23668, 68831 | False | form_difference, ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| Vitamer Laboratories / Turmeric Factors | 23009, 67217 | False | ingredient_notes_or_description_difference, other_ingredients_raw_difference, serving_definition_difference |
| Vitamin World / Magnesium Citrate | 1452, 21158 | False | other_ingredients_raw_difference, serving_definition_difference |
| XYMOGEN / Iron Glycinate | 26594, 27878, 49558, 240225 | True | ingredient_notes_or_description_difference, other_ingredients_raw_difference |
| plnt / Ashwagandha | 80423, 208717 | False | amount_or_basis_difference, form_difference, ingredient_name_or_hierarchy_difference, ingredient_notes_or_description_difference, serving_definition_difference |

## Evidence for ingredient amount, form and serving differences

Name additions/removals and daily-value details for every pair are included in the JSON report. Amount and form comparisons below use uniquely matched name paths.

### Anabolic Laboratories / Clinical Magnesium

Labels 53757 → 67421 (left → right; not chronology):

- Magnesium — form: `[{"name": "Magnesium Amino Acid Chelate", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Magnesium Citrate", "percent": null, "prefix": null, "uniiCode": null}, {"name": "Magnesium Malate", "percent": null, "prefix": "and", "uniiCode": null}]` → `[{"name": "Magnesium Amino Acid Chelate", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Magnesium Citrate", "percent": null, "prefix": null, "uniiCode": null}, {"name": "Magnesium Malate", "percent": null, "prefix": null, "uniiCode": null}]`

### BPI Sports / Creatine Alkaline

Labels 25731 → 43261 (left → right; not chronology):

- Creatine — amount_or_basis: `[{"operator": "=", "quantity": 1500, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 1.5, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "Gram(s)"}]`

### Barlean's Seriously Delicious / Omega-3 Strawberry Banana Smoothie

Labels 218739 → 239258 (left → right; not chronology):

- Total Carbohydrates / Sugar Alcohol — amount_or_basis: `[{"operator": "=", "quantity": 4, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]` → `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]`
- Total Carbohydrates — amount_or_basis: `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]` → `[{"operator": "=", "quantity": 6, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]`

Labels 218739 → 239259 (left → right; not chronology):

- Total Carbohydrates / Sugar Alcohol — amount_or_basis: `[{"operator": "=", "quantity": 4, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]` → `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]`
- Total Carbohydrates — amount_or_basis: `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]` → `[{"operator": "=", "quantity": 6, "servingSizeOrder": 1, "servingSizeQuantity": 15, "servingSizeUnit": "mL", "unit": "Gram(s)"}]`

### BetterYou / Iron Daily Oral Spray

Labels 228638 → 257287 (left → right; not chronology):

- Iron — amount_or_basis: `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 0.52, "servingSizeUnit": "mL", "unit": "mg"}]` → `[{"operator": "=", "quantity": 5, "servingSizeOrder": 1, "servingSizeQuantity": 52, "servingSizeUnit": "mL", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 0.52, "minDailyServings": 1, "minQuantity": 0.52, "notes": "(4 sprays) (0.02 fl. oz)", "order": 1, "unit": "mL"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 52, "minDailyServings": 1, "minQuantity": 52, "notes": "4 sprays (approx 0.02 fl. oz [0.52 ml])", "order": 1, "unit": "mL"}]`

### DC / Creatine

Labels 244633 → 265692 (left → right; not chronology):

- Creatine — form: `[{"name": "Creatine Monohydrate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Creatine Monohydrate", "percent": null, "prefix": null, "uniiCode": null}]`

### Douglas Laboratories / Ferronyl Iron

Labels 70032 → 232593 (left → right; not chronology):

- Choline — form: `[]` → `[{"name": "Choline Bitartrate", "percent": null, "prefix": null, "uniiCode": "6K2W7T9V6Y"}]`
- Iron — form: `[{"name": "Ferronyl", "percent": null, "prefix": "from", "uniiCode": null}]` → `[{"name": "Ferronyl", "percent": null, "prefix": "as", "uniiCode": null}]`
- Vitamin E — amount_or_basis: `[{"operator": "=", "quantity": 30, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 20.1, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Vitamin E — form: `[{"name": "D-Alpha-Tocopheryl Acetate", "percent": null, "prefix": null, "uniiCode": "A7E6112E4N"}]` → `[{"name": "Vitamin E Succinate", "percent": null, "prefix": null, "uniiCode": "LU4B53JYVE"}]`

### Douglas Laboratories / Timed Release Iron

Labels 5328 → 232304 (left → right; not chronology):

- Iron — form: `[{"name": "Ferronyl", "percent": null, "prefix": "from", "uniiCode": null}]` → `[{"name": "Ferronyl", "percent": null, "prefix": "as", "uniiCode": null}]`

Labels 9329 → 232304 (left → right; not chronology):

- Iron — form: `[{"name": "Ferronyl", "percent": null, "prefix": "from", "uniiCode": null}]` → `[{"name": "Ferronyl", "percent": null, "prefix": "as", "uniiCode": null}]`

Labels 30584 → 232304 (left → right; not chronology):

- Iron — form: `[{"name": "Ferronyl", "percent": null, "prefix": "from", "uniiCode": null}]` → `[{"name": "Ferronyl", "percent": null, "prefix": "as", "uniiCode": null}]`

### Douglas Laboratories / Ultra Preventive III with Iron

Labels 5128 → 8729 (left → right; not chronology):

- Vitamin A — form: `[{"name": "Beta-Carotene", "percent": 60, "prefix": "as", "uniiCode": null}]` → `[{"name": "Beta-Carotene", "percent": null, "prefix": null, "uniiCode": "01YAE03M7J"}, {"name": "Vitamin A Palmitate", "percent": null, "prefix": null, "uniiCode": "1D1K0N0VVC"}]`
- Vitamin D3 — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]`

### Enzymedica / Digest Gold + Probiotics

Labels 259959 → 296521 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]`

Labels 259959 → 296523 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]`

Labels 259959 → 328922 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 259959 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 259960 → 296521 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]`

Labels 259960 → 296523 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]`

Labels 259960 → 328922 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 259960 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296521 → 296522 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]`

Labels 296521 → 328922 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296521 → 328923 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]`

Labels 296521 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296522 → 296523 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]`

Labels 296522 → 328922 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296522 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296523 → 328922 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 296523 → 328923 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]`

Labels 296523 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": "w/", "uniiCode": "2I5T75YG19"}]` → `[]`

Labels 328922 → 328923 (left → right; not chronology):

- Pectinase — form: `[]` → `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]`

Labels 328923 → 328924 (left → right; not chronology):

- Pectinase — form: `[{"name": "Phytase", "percent": null, "prefix": null, "uniiCode": "2I5T75YG19"}]` → `[]`

### GNC AMP Advanced Muscle Performance / Creatine HCl 189

Labels 210596 → 229725 (left → right; not chronology):

- PEG-Creatine System — amount_or_basis: `[{"operator": "=", "quantity": 1250, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "White Caplet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 1250, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- PEG-Creatine System — form: `[{"name": "Creatine Hydrochloride", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Con-Cret", "percent": null, "prefix": "with", "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "order": 1, "unit": "White Caplet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "order": 1, "unit": "Tablet(s)"}]`

Labels 210596 → 229733 (left → right; not chronology):

- PEG-Creatine System — amount_or_basis: `[{"operator": "=", "quantity": 1250, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "White Caplet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 1250, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- PEG-Creatine System — form: `[{"name": "Creatine Hydrochloride", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Con-Cret", "percent": null, "prefix": "with", "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "order": 1, "unit": "White Caplet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "order": 1, "unit": "Tablet(s)"}]`

### GNC Pro Performance / Hybrid Creatine Complex Fruit Punch

Labels 19397 → 25606 (left → right; not chronology):

- Total Carbohydrates / Sugar — amount_or_basis: `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 48.17, "servingSizeUnit": "Gram(s)", "unit": "g"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 48.17, "servingSizeUnit": "Gram(s)", "unit": "Gram(s)"}]`
- Total Carbohydrates — amount_or_basis: `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 48.17, "servingSizeUnit": "Gram(s)", "unit": "g"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 48.17, "servingSizeUnit": "Gram(s)", "unit": "Gram(s)"}]`

### Global Healing / Vitamin B12 5000 mcg

Labels 251652 → 296933 (left → right; not chronology):

- Vitamin B12 — form: `[{"name": "Adenosylcobalamin", "percent": 20, "prefix": null, "uniiCode": "F0R1QK73KB"}, {"name": "Hydroxocobalamin", "percent": 20, "prefix": null, "uniiCode": "Q40X8H422O"}, {"name": "Methylcobalamin", "percent": 60, "prefix": "as", "uniiCode": "BR1SN1JS2W"}]` → `[{"name": "Adenosylcobalamin", "percent": null, "prefix": null, "uniiCode": "F0R1QK73KB"}, {"name": "Hydroxocobalamin", "percent": null, "prefix": null, "uniiCode": "Q40X8H422O"}, {"name": "Methylcobalamin", "percent": null, "prefix": null, "uniiCode": "BR1SN1JS2W"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "mL"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "mL"}]`

### InnovixLabs / Triple Strength Omega-3

Labels 248198 → 276213 (left → right; not chronology):

- Total Omega-3 Fatty Acids / Docosahexaenoic Acid — amount_or_basis: `[{"operator": "=", "quantity": 288, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 360, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Total Omega-3 Fatty Acids / Eicosapentaenoic Acid — amount_or_basis: `[{"operator": "=", "quantity": 552, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 480, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Total Omega-3 Fatty Acids / Other Omega-3 Fatty Acids — amount_or_basis: `[{"operator": "=", "quantity": 60, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 36, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 3, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

### Jarrow Formulas / Magnesium Optimizer

Labels 7841 → 29547 (left → right; not chronology):

- Magnesium — form: `[{"name": "Magnesium Citrate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Magnesium Malate", "percent": null, "prefix": "as", "uniiCode": null}]`

Labels 7841 → 37432 (left → right; not chronology):

- Magnesium — form: `[{"name": "Magnesium Citrate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Magnesium Malate", "percent": null, "prefix": "as", "uniiCode": null}]`

Labels 7841 → 212304 (left → right; not chronology):

- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Magnesium — form: `[{"name": "Magnesium Citrate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Magnesium Malate", "percent": null, "prefix": "as", "uniiCode": null}]`
- Potassium — amount_or_basis: `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Taurine — amount_or_basis: `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Tablet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "notes": "", "order": 1, "unit": "Tablet(s)"}]`

Labels 29547 → 212304 (left → right; not chronology):

- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Potassium — amount_or_basis: `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Taurine — amount_or_basis: `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Tablet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "notes": "", "order": 1, "unit": "Tablet(s)"}]`

Labels 37432 → 212304 (left → right; not chronology):

- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Potassium — amount_or_basis: `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Taurine — amount_or_basis: `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 350, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Tablet(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Tablet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 2, "maxQuantity": 2, "minDailyServings": 1, "minQuantity": 2, "notes": "", "order": 1, "unit": "Tablet(s)"}]`

### Nature's Answer / Turmeric-3

Labels 175180 → 185095 (left → right; not chronology):

- Turmeric (Curcuma longa) rhizome extract — amount_or_basis: `[{"operator": "=", "quantity": 200, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "mL", "unit": "mg"}]` → `[{"operator": "=", "quantity": 200, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "approx. 28 drops", "order": 1, "unit": "mL"}]` → `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 1, "minDailyServings": 3, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

### Nature's Plus Herbal Actives / Ashwagandha 450 mg

Labels 13653 → 69019 (left → right; not chronology):

- Ashwagandha — form: `[{"name": "Withanolides", "percent": 1.5, "prefix": "standardized", "uniiCode": null}]` → `[{"name": "Withanolides", "percent": 1.5, "prefix": "standardized [6.75 mg]", "uniiCode": null}]`

### Nature's Way / Ashwagandha Standardized

Labels 39970 → 54522 (left → right; not chronology):

- Ashwagandha extract — form: `[{"name": "Withanolides", "percent": 2.5, "prefix": null, "uniiCode": null}]` → `[{"name": "Withanolides", "percent": 4, "prefix": null, "uniiCode": null}]`

### Nutrilite / Vitamin D

Labels 177381 → 246400 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

Labels 177381 → 246446 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

Labels 208064 → 246400 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

Labels 208064 → 246446 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

Labels 239369 → 246400 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

Labels 239369 → 246446 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`
- Vitamin D — form: `[{"name": "Cholecalciferol", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]` → `[{"name": "Vitamin D2", "percent": null, "prefix": null, "uniiCode": "VS041H42XC"}, {"name": "Vitamin D3", "percent": null, "prefix": null, "uniiCode": "1C6V77QF41"}]`
- Vitamin K2 — form: `[{"name": "fermented Soy Beans", "percent": null, "prefix": "from an extract of", "uniiCode": null}]` → `[]`

### ProCaps Laboratories / Vitamin B12 100

Labels 69735 → 220773 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

Labels 69735 → 248631 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Magnesium — form: `[{"name": "Magnesium Oxide", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Magnesium Citrate", "percent": null, "prefix": "as", "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 220773 → 248631 (left → right; not chronology):

- Magnesium — form: `[{"name": "Magnesium Oxide", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Magnesium Citrate", "percent": null, "prefix": "as", "uniiCode": null}]`

### ProCaps Laboratories / Vitamin B12 250

Labels 179049 → 220792 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Folate Complex — form: `[{"name": "Folic Acid", "percent": null, "prefix": null, "uniiCode": "935E97BOY8"}, {"name": "L-Methylfolate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "L-Methylfolate", "percent": null, "prefix": null, "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

Labels 179049 → 248598 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 220792 → 248598 (left → right; not chronology):

- Folate Complex — form: `[{"name": "L-Methylfolate", "percent": null, "prefix": null, "uniiCode": null}]` → `[{"name": "Folic Acid", "percent": null, "prefix": null, "uniiCode": "935E97BOY8"}, {"name": "L-Methylfolate", "percent": null, "prefix": "as", "uniiCode": null}]`

### ProCaps Laboratories / Vitamin B12 500

Labels 69491 → 179055 (left → right; not chronology):

- Biotin — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]`
- Vitamin B12 — form: `[{"name": "Cyanocobalamin", "percent": null, "prefix": null, "uniiCode": "P6YC3EG204"}]` → `[{"name": "Methylcobalamin", "percent": null, "prefix": null, "uniiCode": "BR1SN1JS2W"}, {"name": "Vitamin B12", "percent": null, "prefix": null, "uniiCode": "8406EY2OQA"}]`

Labels 69491 → 220795 (left → right; not chronology):

- Biotin — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]`
- Vitamin B12 — form: `[{"name": "Cyanocobalamin", "percent": null, "prefix": null, "uniiCode": "P6YC3EG204"}]` → `[{"name": "Methylcobalamin", "percent": null, "prefix": null, "uniiCode": "BR1SN1JS2W"}, {"name": "Vitamin B12", "percent": null, "prefix": null, "uniiCode": "8406EY2OQA"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

Labels 69491 → 248632 (left → right; not chronology):

- Biotin — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]`
- Vitamin B12 — form: `[{"name": "Cyanocobalamin", "percent": null, "prefix": null, "uniiCode": "P6YC3EG204"}]` → `[{"name": "Methylcobalamin", "percent": null, "prefix": null, "uniiCode": "BR1SN1JS2W"}, {"name": "Vitamin B12", "percent": null, "prefix": null, "uniiCode": "8406EY2OQA"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 69491 → 275294 (left → right; not chronology):

- Biotin — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]`
- Vitamin B12 — form: `[{"name": "Cyanocobalamin", "percent": null, "prefix": null, "uniiCode": "P6YC3EG204"}]` → `[{"name": "Methylcobalamin", "percent": null, "prefix": null, "uniiCode": "BR1SN1JS2W"}, {"name": "Vitamin B12", "percent": null, "prefix": null, "uniiCode": "8406EY2OQA"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 179055 → 220795 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Folate Complex — form: `[{"name": "Folic Acid", "percent": null, "prefix": null, "uniiCode": "935E97BOY8"}, {"name": "L-Methylfolate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "L-Methylfolate", "percent": null, "prefix": null, "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

Labels 179055 → 248632 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Folate Complex — form: `[{"name": "Folic Acid", "percent": null, "prefix": null, "uniiCode": "935E97BOY8"}, {"name": "L-Methylfolate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "L-Methylfolate", "percent": null, "prefix": null, "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 179055 → 275294 (left → right; not chronology):

- Folate Complex — amount_or_basis: `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 33, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg DFE"}]`
- Folate Complex — form: `[{"name": "Folic Acid", "percent": null, "prefix": null, "uniiCode": "935E97BOY8"}, {"name": "L-Methylfolate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "L-Methylfolate", "percent": null, "prefix": null, "uniiCode": null}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

### ProCaps Laboratories / Vitamin B12-250

Labels 4735 → 30248 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 60, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 40, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 30, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin C — amount_or_basis: `[{"operator": "=", "quantity": 90, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 60, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

### ProCaps Laboratories / Vitamin B12-500

Labels 4701 → 30249 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Folic Acid — amount_or_basis: `[{"operator": "=", "quantity": 100, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mcg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 40, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 25, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin C — amount_or_basis: `[{"operator": "=", "quantity": 90, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 60, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

### Terry Naturally / Clinical Iron

Labels 39804 → 51697 (left → right; not chronology):

- Copper — form: `[{"name": "TRAACS Copper Bisglycinate Chelate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "TRAACS Copper Bisglycinate Chelate", "percent": null, "prefix": "from", "uniiCode": null}]`
- Iron — form: `[{"name": "Ferrochel", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Ferrochel", "percent": null, "prefix": "from", "uniiCode": null}]`
- Magnesium — form: `[{"name": "TRAACS Magnesium Bisglycinate Chelate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "DiMagnesium Malate", "percent": null, "prefix": "from", "uniiCode": null}]`
- Zinc — form: `[{"name": "TRAACS Zinc Bisglycinate Chelate", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "TRAACS Zinc Bisglycinate Chelate", "percent": null, "prefix": "from", "uniiCode": null}]`

### The Vitamin Shoppe / Calcium Citrate + Vitamin D

Labels 35161 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 35161 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 35162 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 35162 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 55705 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 55705 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 55706 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 55706 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 57581 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 57581 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 57583 → 180697 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

Labels 57583 → 180868 (left → right; not chronology):

- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 400, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 10, "servingSizeOrder": 1, "servingSizeQuantity": 4, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

### The Vitamin Shoppe / Calcium Citrate Plus Magnesium & Vitamin D

Labels 32075 → 54642 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`

Labels 32075 → 55238 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`

Labels 32075 → 73905 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 2, "minDailyServings": 3, "minQuantity": 2, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 2, "minDailyServings": null, "minQuantity": 2, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 32079 → 54642 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`

Labels 32079 → 55238 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`

Labels 32079 → 73905 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 1000, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}, {"operator": "=", "quantity": 568, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}, {"operator": "=", "quantity": 612, "servingSizeOrder": 1, "servingSizeQuantity": 6, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 2, "minDailyServings": 3, "minQuantity": 2, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 2, "minDailyServings": null, "minQuantity": 2, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 54642 → 73905 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 2, "minDailyServings": 3, "minQuantity": 2, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 2, "minDailyServings": null, "minQuantity": 2, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

Labels 55238 → 73905 (left → right; not chronology):

- Calcium — amount_or_basis: `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 333, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Magnesium — amount_or_basis: `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 189, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "mg"}]`
- Vitamin D — amount_or_basis: `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": 2, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 204, "servingSizeOrder": 1, "servingSizeQuantity": null, "servingSizeUnit": "Capsule(s)", "unit": "IU"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 2, "minDailyServings": 3, "minQuantity": 2, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 2, "minDailyServings": null, "minQuantity": 2, "notes": "", "order": 1, "unit": "Capsule(s)"}]`

### The Vitamin Shoppe / Multi Minerals with Boron & Vitamin D

Labels 180292 → 180743 (left → right; not chronology):

- Iodine — form: `[{"name": "Kelp", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Potassium Iodide", "percent": null, "prefix": "and", "uniiCode": null}]` → `[{"name": "Kelp", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Potassium Iodide", "percent": null, "prefix": "as", "uniiCode": null}]`

Labels 180743 → 180745 (left → right; not chronology):

- Iodine — form: `[{"name": "Kelp", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Potassium Iodide", "percent": null, "prefix": "as", "uniiCode": null}]` → `[{"name": "Kelp", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Potassium Iodide", "percent": null, "prefix": "and", "uniiCode": null}]`

### Thorne Research / Iron Bisglycinate

Labels 50539 → 63802 (left → right; not chronology):

- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

### Trace Minerals Research / Ionic Iron 22 mg

Labels 57059 → 78959 (left → right; not chronology):

- Sulfate — form: `[{"name": "FeSO4", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "ITM", "percent": null, "prefix": null, "uniiCode": null}]` → `[{"name": "FeSO4", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "ITM", "percent": null, "prefix": "&", "uniiCode": null}]`

### USANA / Vitamin D

Labels 16210 → 201183 (left → right; not chronology):

- Vitamin D3 — amount_or_basis: `[{"operator": "=", "quantity": 2000, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "IU"}]` → `[{"operator": "=", "quantity": 50, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Tablet(s)", "unit": "mcg"}]`

### Vitamer Laboratories / Mega Magnesium

Labels 23668 → 68831 (left → right; not chronology):

- Magnesium — form: `[{"name": "Magnesium Amino Acid Chelate", "percent": null, "prefix": "from", "uniiCode": null}, {"name": "Magnesium Citrate", "percent": null, "prefix": null, "uniiCode": null}, {"name": "Magnesium Malate", "percent": null, "prefix": "and", "uniiCode": null}]` → `[{"name": "Magnesium Amino Acid Chelate", "percent": null, "prefix": null, "uniiCode": null}, {"name": "Magnesium Citrate", "percent": null, "prefix": null, "uniiCode": null}, {"name": "Magnesium Malate", "percent": null, "prefix": "and", "uniiCode": null}]`

### Vitamer Laboratories / Turmeric Factors

Labels 23009 → 67217 (left → right; not chronology):

- Serving definitions: `[{"inSFB": true, "maxDailyServings": null, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Tablet(s)"}]` → `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Tablet(s)"}]`

### Vitamin World / Magnesium Citrate

Labels 1452 → 21158 (left → right; not chronology):

- Serving definitions: `[{"inSFB": true, "maxDailyServings": 1, "maxQuantity": 5, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": 5, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "order": 1, "unit": "Capsule(s)"}]`

### plnt / Ashwagandha

Labels 80423 → 208717 (left → right; not chronology):

- Ashwagandha extract — amount_or_basis: `[{"operator": "=", "quantity": 95, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Vegetarian Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 95, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Vegetable Capsule(s)", "unit": "mg"}]`
- Ashwagandha extract — form: `[]` → `[{"name": "Withanolides", "percent": null, "prefix": "std to", "uniiCode": null}]`
- organic Ashwagandha — amount_or_basis: `[{"operator": "=", "quantity": 380, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Vegetarian Capsule(s)", "unit": "mg"}]` → `[{"operator": "=", "quantity": 380, "servingSizeOrder": 1, "servingSizeQuantity": 1, "servingSizeUnit": "Vegetable Capsule(s)", "unit": "mg"}]`
- Serving definitions: `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Vegetarian Capsule(s)"}]` → `[{"inSFB": true, "maxDailyServings": 3, "maxQuantity": 1, "minDailyServings": 1, "minQuantity": 1, "notes": "", "order": 1, "unit": "Vegetable Capsule(s)"}]`

