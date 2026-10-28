# SupplementsRx Dataset Specification

## 1. What this dataset contains

This is a **bounded prototype dataset collected on October 27, 2026**, covering ten supplement topics.

It contains source material for retrieval and research—not finished question/answer pairs or medically validated recommendations.

| Source | Saved data | Purpose |
|---|---|---|
| Reddit | 287 posts and 4,593 comments | Real-world questions and reported experiences |
| NatMed Pro | 10 professional ingredient monographs | Clinical-reference material requiring capture-completeness and medical review |
| **Total** | **4,890 source records** | Converted into **5,538 searchable passages** |

Reddit experiences are **not treated as clinical evidence**.

## 2. Topics and exact NatMed sources

The project topics are broad labels. The actual captured monograph determines the limits of the evidence.

| Project topic | Captured NatMed monograph | Monograph ID | Recorded page-update date |
|---|---|---:|---|
| Magnesium | Magnesium | 998 | October 26, 2026 |
| Vitamin D | Vitamin D | 929 | October 26, 2026 |
| Ashwagandha | Ashwagandha | 953 | October 27, 2026 |
| Melatonin | Melatonin | 940 | October 26, 2026 |
| Omega-3 | **Fish Oil** | 993 | October 26, 2026 |
| Vitamin B12 | Vitamin B12 | 926 | October 26, 2026 |
| Iron | Iron | 912 | October 26, 2026 |
| Turmeric | Turmeric | 662 | October 27, 2026 |
| Probiotics | **Lactobacillus acidophilus** | 790 | October 27, 2026 |
| Creatine | Creatine | 873 | October 25, 2026 |

These are **monographs summarizing evidence**, not ten individual research papers. Page-update dates come from saved metadata; they are not the publication dates of the cited studies.

Fish Oil does not represent every omega-3 formulation. *Lactobacillus acidophilus* does not represent every probiotic species, strain, or mixture.

## 3. Collection dates versus source dates

**Collection snapshot:** October 27, 2026.

**Reddit publication-date policy:** No fixed starting date was imposed. Searches used **all-time results, sorted newest first**.

The resulting saved sample covers:

| Subreddit | Posts | Comments | Earliest saved publication | Latest saved publication |
|---|---:|---:|---|---|
| r/Supplements | 133 | 2,293 | September 21, 2026 | October 27, 2026 |
| r/herbalism | 154 | 2,300 | June 27, 2020 | October 22, 2026 |

r/Nootropics was also searched but contributed no saved records.

**This is not a complete Reddit archive for 2020–2026.** Those dates describe the records returned by the bounded searches.

Reddit’s first-import timestamps span approximately **05:36–07:33 UTC** on October 27. NatMed capture timestamps span approximately **05:41–12:57 UTC**. These stored timestamps do not establish the exact duration of browser scraping.

No publication-year restriction was applied to studies cited inside the NatMed monographs. Their dates have not been systematically extracted and verified.

## 4. How collection worked

### Reddit

Scripts ran inside an existing signed-in Chrome session and read **Old Reddit HTML**, without Reddit API keys.

They:
1. Searched supplement names and aliases within the configured subreddits.
2. Opened discussion pages.
3. Captured post text and rendered comments.
4. Downloaded the results as JSON batches.

Configured limits were **20 threads per topic/subreddit** and **50 rendered comments per thread**. Collapsed/load-more comments were not expanded.

A comment could be retained because it mentioned a supplement itself or inherited its parent thread’s topic. These cases are distinguished by `mention_scope`.

### NatMed Pro

Scripts used the signed-in browser to open the selected professional monographs, check their titles and IDs, expand visible sections, and capture text and numeric citation links.

Captured sections include safety, effectiveness, dosing, adverse effects, interactions, formulation information, and mechanisms of action.

**Completeness limitation:** All ten saved captures retain expandable-content markers, and their References sections contain navigation rather than full bibliographies. These flag possible omissions; original-source comparison is still required.

## 5. Processing and storage

The browser downloaded JSON batches. Python validated and normalized them into a common format, then stored them in SQLite.

Stable source IDs prevent duplicate records. Reddit post/comment IDs and parent relationships are preserved. Older clinical captures cannot overwrite newer ones.

| Artifact | What it contains |
|---|---|
| `data/pipeline.sqlite3` | Working database of normalized records, checkpoints, and events |
| `exports/records.jsonl` | Complete normalized source records |
| `exports/passages.jsonl` | Smaller, overlapping excerpts for retrieval |
| `exports/kg_nodes.jsonl` and `kg_edges.jsonl` | Source/topic nodes and `MENTIONS` provenance links—not validated medical relationships |
| `datasets/*.gz` | Compressed copies stored in the private GitHub repository |
| `datasets/manifest.json` | File sizes and SHA-256 hashes for integrity verification |

**JSONL** means one JSON object per line. **`.gz`** means the file is compressed.

Passages are normally up to **220 whitespace-separated words**, with **40-word overlap**, without crossing section boundaries.

## 6. What an output record looks like

An actual Reddit record, with fields omitted for readability:

```json
{
  "id": "reddit:t3_1xeivsd",
  "source": "reddit",
  "record_type": "post",
  "title": "Best magnesium, zinc, k2 supplement?",
  "evidence_role": "user_report",
  "thread_id": "t3_1xeivsd",
  "mention_scope": "own_text",
  "supplements": [
    {
      "supplement": "Magnesium",
      "matched_terms": ["magnesium"]
    }
  ],
  "requires_clinical_review": true
}
```

The full record also contains its text, original URL, timestamps, and content hash.

A NatMed record instead uses:
- `source: "natmed"`
- `record_type: "monograph"`
- `evidence_role: "clinical_reference"`
- Sectioned text, citation links, and capture-quality metadata.

**`clinical_reference` identifies the source category; it does not mean our saved capture is medically approved.** All current clinical captures remain review-required.

## 7. Privacy and use limits

- Normalized records exclude Reddit usernames/profile metadata.
- Free text may still contain personal information; evaluation questions require de-identification.
- Browser passwords, cookies, and session tokens are not exported.
- The repository remains **private because it contains licensed NatMed text**.
- Human source review and relevance annotation are required before clinical approval or reporting real retrieval benchmark scores.

## 8. Open the sample

From the cloned repository:

```sh
python scripts/restore_dataset.py
```

Then open **`exports/sample_records.json`**. It contains a Reddit post, a related comment, and a Magnesium monograph.
