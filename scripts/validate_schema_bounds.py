"""Check the frozen KG against retrospective POC schema bounds; never edit KG inputs."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def json_type(value):
    if value is None: return 'null'
    if isinstance(value, bool): return 'boolean'
    if isinstance(value, dict): return 'object'
    if isinstance(value, list): return 'array'
    if isinstance(value, str): return 'string'
    return 'number'

def validate(root=ROOT):
    csv.field_size_limit(20_000_000)
    spec_path = root / 'schemas/kg_schema_bounds_v1.json'
    spec = json.loads(spec_path.read_text())
    graph = root / spec['graph']
    files = sorted(p for p in graph.rglob('*') if p.is_file())
    before = {str(p.relative_to(root)): digest(p) for p in files}
    failures = []
    def check(ok, code, record):
        if not ok: failures.append({'check': code, 'record': record})
    check(digest(graph/'manifest.json') == spec['graph_manifest_sha256'], 'pinned_manifest', str(graph))
    lower, upper = spec['lower_bound'], spec['upper_bound']
    allowed_nodes = {n['type']: n for n in upper['nodes']}
    allowed_edges = {e['type']: e for e in upper['relationships']}
    check(set(lower['node_types']) <= set(allowed_nodes), 'lower_node_subset', 'schema')
    check(set(lower['relationship_types']) <= set(allowed_edges), 'lower_edge_subset', 'schema')
    evidence = set()
    for line in (graph/'provenance/evidence.jsonl').read_text().splitlines():
        eid = json.loads(line)['id']
        check(eid not in evidence, 'unique_evidence_id', eid)
        evidence.add(eid)
    def property_check(props, allowed, rid):
        for key, value in props.items():
            check(key in allowed, 'allowed_property', rid+':'+key)
            if key in allowed:
                check(json_type(value) in allowed[key], 'property_type', rid+':'+key)
    nodes = {}; counts = Counter(); nulls = Counter(); claims = Counter()
    for path in sorted((graph/'nodes').glob('*.csv')):
        with path.open() as handle:
            reader = csv.DictReader(handle)
            check(path.stem in allowed_nodes, 'allowed_node_type', path.stem)
            if path.stem not in allowed_nodes: continue
            check(reader.fieldnames == allowed_nodes[path.stem]['csv_columns'], 'node_columns', path.stem)
            for row in reader:
                rid, kind = row['id'], row['type']
                check(bool(rid) and rid not in nodes, 'unique_node_id', rid)
                check(kind == path.stem, 'node_file_type', rid)
                props = json.loads(row['properties_json'])
                nodes[rid] = (kind, props); counts[kind] += 1
                property_check(props, allowed_nodes[path.stem]['allowed_properties'], rid)
                for key in lower['required_properties'].get(kind, []):
                    check(key in props, 'required_property_present', rid+':'+key)
                refs = json.loads(row['evidence_ids'])
                check(bool(refs) and all(e in evidence for e in refs), 'node_evidence_reference', rid)
                if kind == 'ClinicalClaim':
                    check(props['review_state'] == 'pending' and props['clinical_approval'] is False, 'pending_claim_preserved', rid)
                    claims[props['review_state']] += 1
                    for key in lower['clinical_original_fields']:
                        check(key in props['original_fields'], 'clinical_field_present', rid+':'+key)
                        if props['original_fields'].get(key) is None: nulls[key] += 1
                if kind in ('RedditPost','RedditComment'):
                    check(props['clinical_approval'] is False and props['evidence_role'] == 'user_report', 'reddit_role', rid)
                if kind == 'ExternalRecordReference':
                    check(props['content_loaded'] is False, 'reference_not_loaded', rid)
    edge_ids = set(); edge_counts = Counter(); degree = Counter(); mapping_count = 0
    with (graph/'relationships/relationships.csv').open() as handle:
        reader = csv.DictReader(handle)
        check(reader.fieldnames == upper['relationship_columns'], 'edge_columns', 'relationships')
        for row in reader:
            rid, kind = row['id'], row['type']
            check(bool(rid) and rid not in edge_ids, 'unique_edge_id', rid); edge_ids.add(rid)
            edge_counts[kind] += 1
            check(kind in allowed_edges, 'allowed_edge_type', rid)
            check(row['start_id'] in nodes and row['end_id'] in nodes, 'edge_endpoints_exist', rid)
            if kind in allowed_edges:
                if row['start_id'] in nodes and row['end_id'] in nodes:
                    pair = [nodes[row['start_id']][0], nodes[row['end_id']][0]]
                    check(pair in allowed_edges[kind]['allowed_endpoints'], 'permitted_endpoint_types', rid)
                property_check(json.loads(row['properties_json']), allowed_edges[kind]['allowed_properties'], rid)
            refs = json.loads(row['evidence_ids'])
            check(bool(refs) and all(e in evidence for e in refs), 'edge_evidence_reference', rid)
            degree[(row['start_id'],'out',kind)] += 1
            degree[(row['end_id'],'in',kind)] += 1
            if kind in ('DENOTES_CONCEPT','EXACT_MATERIAL_MATCH','MEMBER_OF_CATEGORY','RELATED_BOTANICAL_SUBJECT','RELATED_INGREDIENT_SUBJECT'):
                mapping_count += 1
                check(row['confidence'] == 'High' and bool(row['mapping_id']), 'mapping_gate', rid)
    for kind in lower['node_types']: check(counts[kind] > 0, 'lower_node_capability_present', kind)
    for kind in lower['relationship_types']: check(edge_counts[kind] > 0, 'lower_edge_capability_present', kind)
    for constraint in lower['cardinalities']:
        for rid, (kind, _) in nodes.items():
            if kind != constraint['node_type']: continue
            count = sum(degree[(rid,constraint['direction'],r)] for r in constraint['relationships'])
            check(count >= constraint['minimum'] and (constraint['maximum'] is None or count <= constraint['maximum']), 'lower_cardinality', rid+':'+','.join(constraint['relationships']))
    for path, old in before.items(): check(digest(root/path) == old, 'unchanged_graph_file', path)
    manifest = json.loads((graph/'manifest.json').read_text())
    for path, expected in manifest['files'].items():
        check(digest(graph/path) == expected, 'manifest_file_integrity', path)
    result = {'schema': str(spec_path.relative_to(root)), 'schema_sha256': digest(spec_path), 'graph':spec['graph'],
        'nodes':sum(counts.values()), 'edges':sum(edge_counts.values()), 'node_types':len(counts), 'relationship_types':len(edge_counts),
        'lower_node_types':len(lower['node_types']), 'lower_relationship_types':len(lower['relationship_types']),
        'upper_only_node_types':sorted(set(allowed_nodes)-set(lower['node_types'])),
        'upper_only_relationship_types':sorted(set(allowed_edges)-set(lower['relationship_types'])),
        'claim_review_states':dict(claims), 'explicitly_null_clinical_fields':dict(nulls), 'mapping_edges_checked':mapping_count,
        'evidence_ids':len(evidence), 'graph_files_hash_checked':len(before), 'failures':failures, 'passed':not failures,
        'limits':['Checks evidence ID resolution, not revalidation of every source pointer/span.','Nested source objects remain under existing contracts; not fully revalidated here.','Type/path availability does not prove full answer coverage or clinical correctness.']}
    out=root/'reports/schema_bounds_validation_v1.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    raise SystemExit(0 if validate()['passed'] else 1)
