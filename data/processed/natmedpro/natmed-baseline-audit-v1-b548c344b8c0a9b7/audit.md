# NatMed baseline and source-support audit

```json
{
  "monographs": 10,
  "passages": 1179,
  "claims": 1269,
  "html_captures": 10,
  "claim_types": {
    "safety": 107,
    "adverse_effect": 120,
    "effectiveness": 809,
    "dose": 85,
    "interaction": 148
  },
  "review_states": {
    "pending": 1269
  },
  "graph_nodes": 20,
  "graph_edges": 10,
  "graph_edge_types": {
    "MENTIONS": 10
  },
  "schema_draft": "2020-12",
  "claim_contract": "1.1",
  "jsonschema_version": "4.26.0",
  "schema_valid_claims": 1269,
  "schema_error_count": 0,
  "source_support_error_count": 0,
  "field_support_anchors_checked": 2923,
  "earlier_effectiveness_heading_anchors": 769,
  "integrity_error_count": 0,
  "duplicate_groups": {
    "record_text": 0,
    "passage_text": 5,
    "claim_text": 13,
    "claim_payload_except_id": 0,
    "claim_source_span_and_type": 12
  },
  "monographs_requiring_review": 10,
  "upstream_reported_extraction_issues": {
    "section_not_in_html": 1,
    "section_qualification": 10,
    "placeholder_not_negative_evidence": 7,
    "unquantified_dose_statement": 5,
    "no_structured_fields": 6,
    "inline_condition_heading": 2,
    "unresolved_dose_population": 8,
    "unresolved_dose_normalization": 9,
    "unresolved_dose_duration": 1
  },
  "upstream_reported_missing_bibliography_citation_refs": 55,
  "records_corrected": 0,
  "claims_approved": 0,
  "records_merged": 0
}
```

- This audit validates the local imported snapshot, not the current publisher website or upstream HEAD.
- JSON Schema validation uses Draft 2020-12 with URI/date-time format checks. It does not execute the upstream custom Python validator.
- Independent source checks cover hashes, URLs, section headings, source-title ingredient identity, excerpts, offsets, expected non-null field anchors, exact text/numeric values and dose-range ordering.
- Earlier effectiveness-rating anchors are allowed as specified by the contract. Intervening-heading checking uses ratings observed in the annotations; exhaustive publisher-HTML group interpretation remains pending.
- Passage text/word windows and source hashes are checked. Citation bibliographic linkage and whether a citation supports a claim are not clinically validated here.
- Reported 55 missing bibliography references and upstream extraction issues are imported findings, not newly established publisher errors.
- Exact duplicate text is a candidate only: repeated headings and overlapping passages are expected, and source/population/context must be preserved.
- Fish Oil does not represent every Omega-3 formulation; Lactobacillus acidophilus does not represent all probiotics. UMLS/chemical mappings remain separate.
- Structural validity and matching source spans do not approve a medical association, certify capture completeness, or convert source claims into recommendations.
- All pending states remain pending. No normalization, deduplication or clinical approval is performed.
