"""Validate the consumption package using only the Python standard library."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def pointer(value, path):
    for part in path.strip('/').split('/') if path else []:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value

def validate(root=ROOT):
    root = Path(root)
    inventory = json.loads((root / 'reports/kg_handoff_file_list.json').read_text())
    for item in inventory['files']:
        path = root / item['path']
        require(path.is_file() and sha(path) == item['sha256'], 'Package file mismatch: '+item['path'])
    graph = root / inventory['graph']
    manifest = json.loads((graph / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        require(sha(graph / name) == digest, 'Graph hash mismatch: '+name)
    freeze = json.loads((root / 'data/graph/poc-concepts-release-v1-9250419f3c2fc93805f9/freeze_manifest.json').read_text())
    require(freeze['graph'] == inventory['graph'] and freeze['graph_manifest_sha256'] == sha(graph/'manifest.json'), 'Freeze mismatch')
    csv.field_size_limit(10000000)
    def read_csv(path):
        with path.open() as handle:
            result = list(csv.DictReader(handle))
        for row in result:
            row['properties'] = json.loads(row.pop('properties_json'))
            row['evidence_ids'] = json.loads(row['evidence_ids'])
        return result
    nodes = [n for f in sorted((graph/'nodes').glob('*.csv')) for n in read_csv(f)]
    edges = read_csv(graph/'relationships/relationships.csv')
    evrows = [json.loads(l) for l in (graph/'provenance/evidence.jsonl').read_text().splitlines()]
    ni = {n['id']:n for n in nodes}; evidence = {e['id']:e for e in evrows}
    require(len(ni)==len(nodes), 'Duplicate nodes')
    require(len({e['id'] for e in edges})==len(edges), 'Duplicate edges')
    require(len(evidence)==len(evrows), 'Duplicate evidence IDs')
    require(len(nodes)==manifest['counts']['nodes'] and len(edges)==manifest['counts']['edges'], 'Count mismatch')
    require(dict(Counter(n['type'] for n in nodes))==manifest['node_types'], 'Node type mismatch')
    require(dict(Counter(e['type'] for e in edges))==manifest['edge_types'], 'Edge type mismatch')
    evidence_ids=set(evidence)
    for row in nodes+edges:
        require(bool(row['evidence_ids']) and set(row['evidence_ids'])<=evidence_ids, 'Unresolved evidence ID: '+row['id'])
    for e in edges:
        require(e['start_id'] in ni and e['end_id'] in ni, 'Dangling edge: '+e['id'])
    artifacts_path = root/'data/processed/dsld/dsld-normalized-v1-66adbe28c3b0344457fb/artifacts.jsonl'
    artifacts = {r['id']:r for r in map(json.loads, artifacts_path.read_text().splitlines())}
    cache={}
    def source(file, digest):
        if file not in cache:
            path=root/file
            raw=path.read_bytes()
            cache[file]=(hashlib.sha256(raw).hexdigest(),[json.loads(l) for l in raw.splitlines()] if path.suffix=='.jsonl' else json.loads(raw))
        actual,data=cache[file]
        require(actual==digest, 'Source hash mismatch: '+file)
        return data
    for e in evrows:
        if 'artifact_id' in e:
            a=artifacts[e['artifact_id']];file,digest=a['relative_path'],a['sha256']
        else:file,digest=e['locator']['file'],e['locator']['sha256']
        value=pointer(source(file,digest),e['locator']['pointer'])
        if 'original_value' in e:require(value==e['original_value'],'Evidence value mismatch: '+e['id'])
    def span_value(span):
        text=pointer(source(span['file'],span['sha256']),span['pointer'])
        require(0<=span['start']<=span['end']<=len(text),'Invalid text offsets')
        return text[span['start']:span['end']]
    claims=anchors=0
    for n in nodes:
        if n['type']!='ClinicalClaim':continue
        p=n['properties'];claims+=1
        require(p['review_state']=='pending' and p['clinical_approval'] is False,'Unexpected clinical status')
        require(span_value(p['source_span'])==p['original_fields']['source']['excerpt']==p['original_fields']['claim_text'],'Claim excerpt mismatch')
        for a in p['field_support_anchors']:
            anchors+=1;require(span_value(a['source_span'])==a['source_text'],'Field span mismatch')
    return dict(status='passed',graph=inventory['graph'],package_files=len(inventory['files']),nodes=len(nodes),relationships=len(edges),evidence_pointers=len(evrows),pending_claims=claims,field_support_anchors=anchors,scope='Consumption package integrity and source support; not clinical approval or full rebuild validation')

if __name__=='__main__':
    print(json.dumps(validate(),indent=2))
