# DSLD repeated-name review

All labels are retained. Comparison is complete; product identity decisions remain pending.

Exact field differences can reflect formatting, order, daily-value metadata, or genuine content changes. They do not establish reformulation.

DSLD entry dates do not establish revision order. Source relationship annotations may coexist or conflict with the stored fields.

## Summary

```json
{
  "group_count": 70,
  "label_count": 206,
  "pair_count": 304,
  "groups_with_field_differences": {
    "entryDate": 61,
    "events": 65,
    "ingredientRows": 54,
    "otheringredients": 49,
    "productVersionCode": 65,
    "statements": 68,
    "netContents": 40,
    "offMarket": 26,
    "upcSku": 32,
    "servingSizes": 23,
    "physicalState": 3
  },
  "groups_with_source_relationship_type": {
    "Image difference, same product": 51,
    "Package size difference, same product": 31,
    "Flavor difference": 2
  },
  "groups_without_internal_source_relationship": 8,
  "groups_with_multiple_on_market_labels": 16,
  "pairs_equal_except_id_and_src": 0,
  "pairs_same_nonempty_upc_sku": 126,
  "records_merged": 0,
  "records_removed": 0,
  "limitations": [
    "Field comparisons use exact stored JSON, including list order and formatting; differences do not prove reformulation.",
    "Source relationship annotations are retained as evidence, not independently validated identity decisions.",
    "Entry dates are DSLD entry dates, not release dates or a verified revision sequence.",
    "No unit conversion, synonym normalization, or ingredient equivalence is attempted.",
    "Only exact repeated brand/name groups are examined; duplicates across different names are outside scope."
  ]
}
```

## Group comparisons

| Brand / product | Label IDs | On-market in snapshot | Source relationships within group | Differing fields |
|---|---|---:|---|---|
| Advanced Nutrition by Zahler / Iron Complex | 260089, 278513 | 2 | None | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Allergy Research Group / Magnesium Citrate | 20453, 54244, 54431, 78492, 182963, 184238, 208093, 233067, 233300 | 2 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements, upcSku |
| Anabolic Laboratories / Clinical Magnesium | 53757, 67421 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements, upcSku |
| Ancient Nutrition / SBO Probiotics Trinity | 305812, 309193 | 1 | Image difference, same product | entryDate, events, ingredientRows, offMarket, otheringredients, productVersionCode, statements |
| BPI Sports / Creatine Alkaline | 25731, 43261 | 1 | Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements |
| Barlean's Seriously Delicious / Omega-3 Pina Colada | 218715, 239256 | 0 | Flavor difference | entryDate, events, ingredientRows, netContents, productVersionCode, statements |
| Barlean's Seriously Delicious / Omega-3 Strawberry Banana Smoothie | 218739, 239258, 239259 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, productVersionCode, statements, upcSku |
| BetterYou / Iron Daily Oral Spray | 228638, 257287 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, servingSizes, statements |
| BioCare / Nutrisorb Vitamin B12 | 302255, 309759 | 1 | Image difference, same product | entryDate, events, ingredientRows, offMarket, productVersionCode, statements |
| Bluebonnet / Magnesium Citrate | 203860, 204235 | 0 | None | events, ingredientRows, netContents, productVersionCode, statements, upcSku |
| DC / Creatine | 244633, 265692 | 2 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Douglas Laboratories / Ferronyl Iron | 70032, 232593 | 1 | Image difference, same product | entryDate, events, ingredientRows, offMarket, otheringredients, productVersionCode, statements |
| Douglas Laboratories / Timed Release Iron | 5328, 9329, 30584, 232304 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Douglas Laboratories / Ultra Preventive III with Iron | 5128, 8729 | 2 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements, upcSku |
| Douglas Laboratories / Vitamin B12 | 5083, 10768, 56047 | 0 | Image difference, same product | entryDate, events, ingredientRows, productVersionCode, statements |
| Endo-met Laboratories / Vitamin D | 229019, 229021 | 2 | Package size difference, same product | netContents |
| Enzymedica / Digest Basic + Probiotics | 260008, 260011, 296494, 296495, 328918 | 2 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements, upcSku |
| Enzymedica / Digest Gold + Probiotics | 32494, 32500, 32502, 259959, 259960, 296521, 296522, 296523, 328922, 328923, 328924 | 5 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements, upcSku |
| Floradix / Calcium Magnesium | 33728, 33733 | 0 | Package size difference, same product | ingredientRows, netContents, statements |
| GNC AMP Advanced Muscle Performance / Creatine HCl 189 | 210596, 229725, 229733 | 2 | Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, physicalState, productVersionCode, servingSizes, statements, upcSku |
| GNC Mega Men / High Potency Omega-3 | 69537, 304637 | 2 | None | entryDate, events, ingredientRows, otheringredients, physicalState, productVersionCode, servingSizes, statements |
| GNC Pro Performance / Hybrid Creatine Complex Fruit Punch | 19397, 25606 | 1 | Flavor difference; Image difference, same product | entryDate, events, ingredientRows, netContents, offMarket, productVersionCode, statements |
| Gaia Herbs Single Herbs / Ashwagandha Root | 44575, 79402 | 0 | Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, statements, upcSku |
| Global Healing / Vitamin B12 5000 mcg | 251652, 296933 | 2 | Image difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements |
| Good 'N Natural / Melatonin 3 mg | 10840, 10842, 10843, 58222, 58513, 58514 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, netContents, otheringredients, productVersionCode, statements, upcSku |
| Herbal Hills / Ashwagandha | 74939, 74940 | 2 | Package size difference, same product | netContents, statements, upcSku |
| Himalaya / Ashwagandha | 25775, 40304, 40487, 80192, 80197, 207207 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| InnovixLabs / Triple Strength Omega-3 | 248198, 276213 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, servingSizes, statements |
| InnovixLabs / Ultra Strength Omega-3 | 276214, 334990 | 1 | Image difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements |
| Integrative Therapeutics / Magnesium Malate | 185029, 246459 | 1 | Image difference, same product | entryDate, events, ingredientRows, netContents, offMarket, productVersionCode, servingSizes, statements |
| Jarrow Formulas / Magnesium Optimizer | 7841, 29547, 37432, 212304 | 0 | Image difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements |
| Kyolic / Kyolic Omega-3 | 42106, 42437, 205111 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, statements, upcSku |
| MegaFood / Turmeric Strength For Joint | 178192, 178208 | 0 | Package size difference, same product | events, ingredientRows, netContents, statements, upcSku |
| Nature's Answer / Turmeric-3 | 175180, 185095 | 0 | None | entryDate, events, ingredientRows, netContents, otheringredients, physicalState, productVersionCode, servingSizes, statements, upcSku |
| Nature's Bounty / Melatonin 1 mg | 3749, 17141, 29168, 49277 | 0 | Image difference, same product | entryDate, events, productVersionCode, statements |
| Nature's Bounty / Turmeric 450 mg | 240133, 242577 | 1 | Image difference, same product | entryDate, events, offMarket, otheringredients, productVersionCode, statements |
| Nature's Plus Herbal Actives / Ashwagandha 450 mg | 13653, 69019 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Nature's Way / Ashwagandha Standardized | 39970, 54522 | 0 | Image difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, statements |
| Nature's Way / Turmeric Standardized | 17865, 40608 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, otheringredients, productVersionCode, statements |
| NutriCology / Magnesium Citrate | 183861, 199602, 234782, 235550 | 2 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements, upcSku |
| Nutrilite / Vitamin D | 177381, 208064, 239369, 246400, 246446 | 0 | Image difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| Pharmax / Probiotics | 70943, 71008 | 2 | None | productVersionCode, statements, upcSku |
| ProCaps Laboratories / Vitamin B12 100 | 69735, 220773, 248631 | 0 | Image difference, same product | entryDate, events, ingredientRows, productVersionCode, servingSizes, statements, upcSku |
| ProCaps Laboratories / Vitamin B12 250 | 179049, 220792, 248598 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| ProCaps Laboratories / Vitamin B12 500 | 69491, 179055, 220795, 248632, 275294 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| ProCaps Laboratories / Vitamin B12-100 | 30426, 30599, 30603 | 0 | Image difference, same product | events |
| ProCaps Laboratories / Vitamin B12-250 | 4735, 30248 | 1 | Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, servingSizes, statements |
| ProCaps Laboratories / Vitamin B12-500 | 4701, 30249 | 1 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, servingSizes, statements |
| Pure Encapsulations / Melatonin-SR | 185040, 277770, 299064 | 2 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| Puritan's Pride / Melatonin 3 mg | 62015, 73873, 242416 | 2 | Image difference, same product; Package size difference, same product | entryDate, events, netContents, offMarket, productVersionCode, statements, upcSku |
| Seeking Health / Adeno B12 | 174318, 210776 | 1 | Image difference, same product | entryDate, events, offMarket, productVersionCode, statements |
| Seeking Health / Ashwagandha Extract | 174353, 210829, 233452 | 1 | Image difference, same product | entryDate, events, ingredientRows, netContents, offMarket, otheringredients, productVersionCode, statements |
| Spring Valley / Omega-3 Fish Oil | 178317, 178792 | 2 | None | entryDate, events, otheringredients, productVersionCode, statements, upcSku |
| Sundown Naturals / Melatonin 3 mg | 30617, 30624 | 1 | Package size difference, same product | events, netContents, offMarket, productVersionCode, statements, upcSku |
| Terry Naturally / Clinical Iron | 39804, 51697 | 1 | None | entryDate, events, ingredientRows, offMarket, otheringredients, productVersionCode, statements |
| The Vitamin Shoppe / B12 With Folic Acid Raspberry | 37231, 37232, 60199, 60206 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| The Vitamin Shoppe / Calcium Citrate + Vitamin D | 35161, 35162, 55705, 55706, 57581, 57583, 180697, 180868 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, statements, upcSku |
| The Vitamin Shoppe / Calcium Citrate Plus Magnesium & Vitamin D | 32075, 32079, 54642, 55238, 73905 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, servingSizes, statements, upcSku |
| The Vitamin Shoppe / Multi Minerals With Boron & Vitamin D | 32728, 32733 | 0 | Package size difference, same product | netContents, productVersionCode, statements, upcSku |
| The Vitamin Shoppe / Multi Minerals with Boron & Vitamin D | 180292, 180743, 180745 | 1 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, netContents, offMarket, productVersionCode, statements, upcSku |
| Thorne / Iron Bisglycinate | 181918, 204236, 204338 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements, upcSku |
| Thorne Research / Iron Bisglycinate | 50539, 63802 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, otheringredients, productVersionCode, servingSizes, statements |
| Trace Minerals Research / Ionic Iron 22 mg | 57059, 78959 | 0 | Image difference, same product; Package size difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, servingSizes, statements |
| USANA / Vitamin D | 16210, 201183 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Vimerson Health / Turmeric Curcumin | 285511, 315533 | 1 | None | entryDate, events, ingredientRows, offMarket, otheringredients, productVersionCode, statements |
| Vitamer Laboratories / Mega Magnesium | 23668, 68831 | 0 | Image difference, same product | entryDate, events, ingredientRows, otheringredients, productVersionCode, statements |
| Vitamer Laboratories / Turmeric Factors | 23009, 67217 | 1 | Image difference, same product | entryDate, events, ingredientRows, offMarket, otheringredients, productVersionCode, servingSizes, statements |
| Vitamin World / Magnesium Citrate | 1452, 21158 | 1 | Image difference, same product | entryDate, events, offMarket, otheringredients, productVersionCode, servingSizes, statements |
| XYMOGEN / Iron Glycinate | 26594, 27878, 49558, 240225 | 0 | Image difference, same product | entryDate, events, ingredientRows, netContents, otheringredients, productVersionCode, statements, upcSku |
| plnt / Ashwagandha | 80423, 208717 | 1 | Image difference, same product | entryDate, events, ingredientRows, netContents, offMarket, productVersionCode, servingSizes, statements |

## Recommended next decision

Keep a separate label entity for every DSLD ID. Preserve source-asserted relationships with provenance. Do not merge products by name, UPC/SKU, or entry date alone. Review ingredient/serving differences before assigning canonical product or formulation IDs.

The JSON companion contains source hashes, per-label ingredient/serving/package details, and every pair comparison. Raw labels remain the reference for all other fields.
