"""Read-only review of the current graph; write a separate readiness report."""
import csv
import json
from collections import Counter
from pathlib import Path
from kg_evaluation_common import ROOT, GRAPH, sha
from export_full_graph import build as build_base, validate, DSLD
from validate_freeze_full_graph import check_claim_support, pointer
from expand_topic_navigation import coverage, build as build_navigation
from preserve_dsld_statements import build as build_statements


def review(root=ROOT):
    root = Path(root)
    folder = root / GRAPH
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    for name, digest in manifest['files'].items():
        assert sha((folder / name).read_bytes()) == digest, name
    freeze = json.loads((root / 'data/graph/poc-statements-release-v1-684ce1012b4f76e0af1a/freeze_manifest.json').read_bytes())
    assert freeze['graph'] == GRAPH
    assert freeze['graph_manifest_sha256'] == sha((folder / 'manifest.json').read_bytes())
    assert freeze['graph_files'] == manifest['files']
    signature = json.loads((folder / 'input_manifest.json').read_bytes())
    for name, digest in signature['inputs'].items():
        assert sha((root / name).read_bytes()) == digest, name
    csv.field_size_limit(10_000_000)
    def read_csv(path):
        with path.open() as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            row['properties'] = json.loads(row.pop('properties_json'))
            row['evidence_ids'] = json.loads(row['evidence_ids'])
        return rows
    nodes = [r for f in sorted((folder / 'nodes').glob('*.csv')) for r in read_csv(f)]
    edges = read_csv(folder / 'relationships/relationships.csv')
    evrows = [json.loads(l) for l in (folder / 'provenance/evidence.jsonl').read_text().splitlines()]
    evidence = {r['id']: r for r in evrows}
    assert len(evidence) == len(evrows)
    base_nodes, base_edges, _, _, _, _, _, expected = build_base(root)
    checks = validate(nodes, edges, evidence, expected)
    ni = {r['id']: r for r in nodes}
    ei = {r['id']: r for r in edges}
    assert all(ni[r['id']] == r for r in base_nodes)
    assert all(ei[r['id']] == r for r in base_edges)
    assert len(nodes) == manifest['counts']['nodes']
    assert len(edges) == manifest['counts']['edges']
    assert dict(Counter(n['type'] for n in nodes)) == manifest['node_types']
    assert dict(Counter(e['type'] for e in edges)) == manifest['edge_types']
    checks.update(check_claim_support(root, nodes))
    # Re-run existing extension checks without writing or replacing graph artifacts.
    build_navigation(root)
    assertions, expected_edges, expected_evidence, inventory, statement_report, _, _ = build_statements(root)
    for row in assertions:
        p = json.loads(row['properties_json'])
        assert ni[row['id']]['properties'] == p
    assert {r['id'] for r in expected_edges} == set(ei)
    for raw in expected_edges:
        row = dict(raw)
        row['properties'] = json.loads(row.pop('properties_json'))
        row['evidence_ids'] = json.loads(row['evidence_ids'])
        assert ei[row['id']] == row
    assert expected_evidence == evidence
    artifacts = {r['id']: r for r in map(json.loads, (root / DSLD / 'artifacts.jsonl').read_text().splitlines())}
    cache = {}
    for e in evidence.values():
        if 'artifact_id' in e:
            artifact = artifacts[e['artifact_id']]
            file, digest = artifact['relative_path'], artifact['sha256']
        else:
            file, digest = e['locator']['file'], e['locator']['sha256']
        if file not in cache:
            b = (root / file).read_bytes()
            cache[file] = (sha(b), [json.loads(l) for l in b.splitlines()] if file.endswith('.jsonl') else json.loads(b))
        actual, data = cache[file]
        assert actual == digest, file
        value = pointer(data, e['locator']['pointer'])
        if 'original_value' in e:
            assert value == e['original_value']
    checks.update(file_hashes_verified=True, freeze_matches=True, input_hashes_verified=True,
                  base_nodes_and_edges_unchanged=True, counts_match=True,
                  navigation_checks_rerun=True, statements_verified=len(inventory),
                  evidence_pointers_verified=len(evidence))
    queues = {}
    for f in sorted((folder / 'review').glob('*.jsonl')):
        rows = [json.loads(l) for l in f.read_text().splitlines()]
        queues[f.stem] = {'rows': len(rows)}
        for field in ['status', 'action', 'reason', 'confidence', 'source']:
            counts = Counter(str(r[field]) for r in rows if field in r)
            if counts:
                queues[f.stem][field] = dict(counts)
    source_nodes = Counter(n['properties'].get('source', '<other>') for n in nodes if n['type'] in ['ChemicalCompound', 'TerminologyConcept'])
    report = dict(status='ready_for_scoped_research_use_with_documented_limitations',
                  graph=GRAPH, graph_manifest_sha256=sha((folder / 'manifest.json').read_bytes()),
                  checks=checks, counts=manifest['counts'], node_types=manifest['node_types'],
                  terminology_nodes_by_source=dict(source_nodes), coverage=coverage(nodes, edges),
                  review_queues=queues, clinical_approval=False, canonical_product_merges=0,
                  limitations=['Structural/source-support validation is not clinical validation.',
                    'Pending/excluded mappings and no-candidate lookups remain unresolved; counts are review rows, not unique errors.',
                    'All 1269 NatMed annotations remain pending clinical review; source authority does not approve extracted annotations.',
                    'Literal topic mentions are navigation aids, not ingredient identity or product applicability.',
                    'Reddit direct mentions and inherited thread context are distinct; neither establishes clinical efficacy.',
                    'All 6462 saved DSLD statements are preserved, including marketing and disclaimers; not all are warnings.',
                    'Source label identities are preserved; equivalent amounts or duplicate text do not establish product equivalence.',
                    'Coverage is limited to saved inputs; no external completeness or medical correctness claim.',
                    'No Neo4j import, clinical deployment validation, or shareable standalone handoff package has been performed.'])
    return report

if __name__ == '__main__':
    result = review()
    destination = ROOT / 'reports/kg_readiness_review.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'checks', 'terminology_nodes_by_source']}, indent=2))
    print(destination)
