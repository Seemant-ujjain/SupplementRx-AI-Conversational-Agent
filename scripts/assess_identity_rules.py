"""Audit-derived identity-rule coverage, not semantic approval or deduplication."""
import csv
import io
import json
from collections import Counter
from pathlib import Path
from review_dsld_name_groups import snapshot, sha

VERSION = "identity-coverage-v1"
RULE_VERSION = "step5a-id01-id22-draft-v1"


def route_query(q, shared_keys):
    counts = q["candidate_counts"]
    rules, reasons = [], []
    if any(counts.values()):
        rules += ["ID-06", "ID-07"]
        reasons.append("scope_review_not_performed")
    if any(n == 0 for n in counts.values()):
        rules.append("ID-13")
        reasons.append("one_or_more_sources_without_candidate")
    if any(n > 1 for n in counts.values()):
        rules.append("ID-12")
        reasons.append("multiple_candidates")
    if len(q["dsld_ingredient_ids"]) > 1:
        rules.append("ID-04")
        reasons.append("name_group_contains_distinct_source_ids")
    if q["query_key"] in shared_keys:
        rules.append("ID-14")
        reasons.append("target_shared_with_other_queries")
    if q["methods"]["rxnorm"] == "normalized":
        reasons.append("normalized_lookup_is_not_identity_evidence")
    return {"query_key": q["query_key"], "query": q["query"],
            "candidate_counts": counts, "applicable_rules": sorted(set(rules)),
            "coverage_status": "covered", "coverage_scope": "mechanical_routing_only",
            "semantic_assessment": "not_performed", "review_state": "needs_review",
            "reasons": reasons, "proposed_relation": None,
            "evidence_pointer": "/queries/" + str(q["_index"])}


def assess(project):
    project = Path(project)
    before = snapshot(project / "data/raw")
    inputs, verified = {}, {}

    def check(path, expected):
        path = Path(path)
        if not path.is_absolute():
            path = project / path
        if sha(path.read_bytes()) != expected:
            raise ValueError("Changed evidence: " + str(path))
        verified[str(path.relative_to(project))] = expected

    def load(pattern):
        paths = sorted((project / "data/processed").glob(pattern))
        if len(paths) != 1:
            raise ValueError("Expected exactly one pinned audit: " + pattern)
        path = paths[0]
        manifest_path = path.parent / "manifest.json"
        m = json.loads(manifest_path.read_text())
        check(path, m["files"][path.name]["sha256"])
        inputs[str(manifest_path.relative_to(project))] = sha(manifest_path.read_bytes())
        for source in m.get("sources", {}).values():
            check(source["file"], source["sha256"])
        for name, value in m.get("inputs", {}).items():
            if isinstance(value, dict) and "file" in value:
                check(value["file"], value["sha256"])
            elif isinstance(value, str) and name.startswith("data/") and not name.endswith(".DS_Store"):
                check(name, value)
        if "collection_sha256" in m:
            check("data/raw/dsld/collection.json", m["collection_sha256"])
        if "source_collection" in m:
            check(m["source_collection"], m["source_sha256"])
        inputs[str(path.relative_to(project))] = sha(path.read_bytes())
        return json.loads(path.read_text()), str(path.relative_to(project))

    audits, paths = {}, {}
    for name in ["dsld", "pubchem", "rxnorm", "mesh", "natmedpro", "reddit"]:
        audits[name], paths[name] = load(name + "/*baseline-audit-v1-*/audit.json")
    terms, term_path = load("terminology/terminology-review-v1-*/review.json")
    ingredients, ingredient_path = load("dsld/dsld-ingredient-review-v1-*/review.json")
    quantities, quantity_path = load("dsld/dsld-quantity-audit-v1-*/audit.json")
    # MeSH audit has no source_collection field; the combined review pins all three collections.
    shared_keys = {key for group in terms["shared_candidates"] for key in group["query_keys"]}
    queries = [route_query(dict(q, _index=i), shared_keys) for i, q in enumerate(terms["queries"])]
    assert len({q["query_key"] for q in queries}) == len(queries) == terms["summary"]["query_groups"]
    assert sum(any(n > 1 for n in q["candidate_counts"].values()) for q in queries) == terms["summary"]["queries_ambiguous_in_any_source"]
    groups = []
    for i, g in enumerate(ingredients["groups"]):
        groups.append({"group_id": g["group_id"], "label_ids": g["label_ids"],
                       "brand": g["brand_name"], "product": g["product_name"],
                       "applicable_rules": ["ID-04", "ID-15", "ID-16", "ID-22"],
                       "coverage_status": "rule_gap", "review_state": "needs_review",
                       "reason": "product_family_variant_acceptance_boundary_not_operational",
                       "source_flags": g["flags"], "evidence_pointer": "/groups/" + str(i)})
    assert len(groups) == ingredients["summary"]["groups"]
    findings = []

    def finding(source, pointer, rules, status, implication):
        value = audits[source]
        for part in pointer.strip("/").split("/"):
            value = value[part]
        findings.append(dict(source=source, evidence_file=paths[source], evidence_pointer=pointer,
                             observed=value, rules=rules.split(), coverage_status=status, implication=implication))

    finding("dsld", "/summary/labels", "ID-01 ID-05", "covered", "400-label baseline supports source-scoped retention; no product equivalence inferred.")
    finding("dsld", "/summary/normalized_ingredient_names_with_multiple_ids", "ID-04 ID-05", "covered", "291 name groups cannot be keys; this scope differs from 178 terminology-query groups.")
    finding("dsld", "/summary/relationships/distinct_external_targets", "ID-03 ID-22", "rule_gap", "451 external label targets need an explicit referenced-but-not-collected identity policy.")
    finding("dsld", "/summary/shared_compact_upc_sku_groups", "ID-15 ID-16", "rule_gap", "62 shared-code groups need product boundary criteria; not merge approvals.")
    finding("pubchem", "/summary/property_collision_groups", "ID-04 ID-07 ID-14", "covered", "Shared chemical properties are review evidence, not automatic identity keys.")
    finding("rxnorm", "/summary/ambiguity_by_method", "ID-06 ID-12", "covered", "Exact and normalized lookup stages both contain ambiguity.")
    finding("mesh", "/summary/relation_targets_without_description", "ID-08 ID-09 ID-22", "rule_gap", "791 edges lack target descriptions; preserve source edges without inventing target properties or identity.")
    finding("natmedpro", "/summary/claims", "ID-05 ID-18", "covered", "1269 claim occurrences remain separate; structural validity is not clinical approval.")
    finding("natmedpro", "/summary/duplicate_groups", "ID-04 ID-18", "covered", "Repeated spans/text do not establish identical assertions.")
    finding("natmedpro", "/summary/upstream_reported_missing_bibliography_citation_refs", "ID-19 ID-22", "rule_gap", "55 upstream-reported missing references need unresolved citation identities; this is not a fresh citation count.")
    finding("reddit", "/summary/records_in_duplicate_text_groups", "ID-04 ID-18", "covered", "230 records across 24 repeated-text groups retain their native identities.")
    finding("reddit", "/summary/mention_scopes", "ID-20", "covered", "3595 thread-context associations must not become direct ingredient-use claims.")
    finding("reddit", "/summary/comments_with_either_context_gap", "ID-03 ID-20 ID-22", "rule_gap", "159 comments need separate absent-ID and known-but-uncollected-target handling.")
    gaps = [
        {"id": "G1", "kind": "rule_gap", "rules": ["ID-07", "ID-08", "ID-09", "ID-10"], "issue": "Scope-specific acceptance evidence is not operationalized.", "next": "Specify minimum evidence by chemical form, botanical preparation, species/strain, mixture and category; audit metadata alone cannot decide exact scope matches."},
        {"id": "G2", "kind": "rule_gap", "rules": ["ID-15", "ID-16", "ID-17"], "issue": "Product family and variant boundaries remain provisional.", "next": "Specify which differences define separate variants, which fields are required, and how incomplete compositions block acceptance."},
        {"id": "G3", "kind": "rule_gap", "rules": ["ID-03", "ID-19", "ID-22"], "issue": "Missing source identity and a known target outside the snapshot are different states.", "next": "Define source-scoped unresolved reference records with target ID when known, capture status and provenance; never fabricate target attributes."},
        {"id": "G4", "kind": "rule_gap", "rules": ["ID-02", "ID-21"], "issue": "Fingerprint serialization and lifecycle acceptance propagation are not implemented.", "next": "Define payload fingerprint scope and change invalidation; separately test repeat capture, source replacement and split/merge fixtures."},
        {"id": "G5", "kind": "not_assessable", "rules": ["ID-07", "ID-11", "ID-19", "ID-21"], "issue": "No completed semantic decisions or longitudinal lifecycle assessment in this run.", "next": "Review definitions and citation identifiers case by case; do not interpret absence of measured conflicts as proof of equivalence. Historical imports exist but were not compared here."},
    ]
    report = {"version": VERSION, "rule_version": RULE_VERSION,
              "scope": "Mechanical routing of all saved terminology queries and repeated-name product groups; audit-level evidence for all six sources. Not exhaustive semantic resolution or a fresh baseline audit.",
              "summary": {"terminology_queries_routed": len(queries), "terminology_rule_counts_overlapping": dict(Counter(r for q in queries for r in q["applicable_rules"])),
                          "terminology_source_coverage": terms["summary"]["coverage_counts"],
                          "ambiguous_queries": terms["summary"]["queries_ambiguous_in_any_source"],
                          "product_groups_assessed": len(groups), "product_comparison_summary": ingredients["summary"],
                          "audit_findings_assessed": len(findings), "gap_register_entries": len(gaps),
                          "accepted_mappings": 0, "merged_entities": 0},
              "terminology_evidence_file": term_path, "product_evidence_file": ingredient_path,
              "quantity_context": {"file": quantity_path, "summary": quantities["summary"], "interpretation": "Quantity conflicts need later normalization safeguards; equal values cannot settle product identity."},
              "queries": queries, "product_groups": groups, "audit_findings": findings, "gaps": gaps}
    assert all(q["review_state"] == "needs_review" and q["proposed_relation"] is None for q in queries)
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    script_hash = sha(Path(__file__).read_bytes())
    out = project / "data/processed/identity" / (VERSION + "-" + sha(json.dumps(inputs, sort_keys=True).encode() + script_hash.encode())[:16])
    if snapshot(project / "data/raw") != before:
        raise RuntimeError("Raw data changed during assessment")
    manifest = {"version": VERSION, "rule_version": RULE_VERSION, "script_sha256": script_hash, "inputs": inputs,
                "verified_evidence_files": verified, "raw_file_count": len(before), "raw_files_unchanged": True,
                "files": {"assessment.json": {"sha256": sha(payload), "bytes": len(payload)}}}
    payloads = {"assessment.json": payload, "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()}
    if out.exists():
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise ValueError("Refusing to overwrite changed output: " + name)
    else:
        out.mkdir(parents=True)
        for name, data in payloads.items():
            (out / name).write_bytes(data)
    return out, report


if __name__ == "__main__":
    out, report = assess(Path(__file__).resolve().parents[1])
    print(out)
    print(json.dumps(report["summary"], indent=2))
