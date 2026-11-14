"""Export a source-scoped DSLD/terminology pilot graph; no canonical merges."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import io
import json

ROOT = Path(__file__).resolve().parents[1]
CONFIDENCE = 'data/processed/identity/mapping-confidence-v1-7c8a0e7ea6f02e69/confidence.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)+'\n').encode()

def validate(nodes, edges, candidates, evidence):
    ids = [n['id'] for n in nodes]
    assert len(ids) == len(set(ids)), 'Duplicate node IDs'
    assert len({e['id'] for e in edges}) == len(edges), 'Duplicate edge IDs'
    assert all(e['start_id'] in ids and e['end_id'] in ids for e in edges), 'Dangling endpoint'
    high = {c['mapping_id']: c for c in candidates if c['confidence']=='High'}
    mapped = [e for e in edges if e['mapping_id']]
    assert {e['mapping_id'] for e in mapped} == set(high), 'Incorrect mapping eligibility'
    assert len(mapped) == len(high), 'Duplicate mapping edges'
    for e in mapped:
        c = high[e['mapping_id']]
        assert e['type'] == c['proposed_relation'].upper(), 'Relationship promoted or changed'
        assert e['start_id'] == c['origin_occurrence_id']
        assert e['confidence'] == 'High'
    assert all(i in evidence for e in edges for i in json.loads(e['evidence_ids'])), 'Missing evidence'
    return dict(unique_ids=True, all_endpoints_resolve=True, all_24_high_links_only=True,
                relationship_types_preserved=True, evidence_references_resolve=True,
                canonical_merges=0, derived_doses=0)

def build(root=ROOT):
    conf = json.loads((root/CONFIDENCE).read_bytes())
    review_path = root/conf['input_review']
    assert sha(review_path.read_bytes()) == conf['input_sha256']
    review = json.loads(review_path.read_bytes())
    pilot = root/'data/processed/poc'/review['pilot_build']
    assert sha((pilot/'manifest.json').read_bytes()) == review['pilot_manifest_sha256']
    manifest = json.loads((pilot/'manifest.json').read_bytes())
    tables = {}
    for name, spec in manifest['tables'].items():
        raw = (pilot/spec['file']).read_bytes()
        assert sha(raw) == spec['sha256']
        tables[name] = {r['id']:r for r in map(json.loads,raw.splitlines())}
    for artifact in tables['artifacts'].values():
        assert sha((root/artifact['relative_path']).read_bytes()) == artifact['sha256']
    nodes, edges = [], []
    def node(identifier, kind, data):
        nodes.append(dict(id=identifier,type=kind,properties_json=json.dumps(data,sort_keys=True,ensure_ascii=False)))
    def edge(start, end, kind, evidence_ids=(), mapping_id='', confidence='', properties=None):
        identifier = mapping_id or 'edge:'+sha(encoded([start,end,kind]))
        edges.append(dict(id=identifier,start_id=start,end_id=end,type=kind,mapping_id=mapping_id,
                          confidence=confidence,evidence_ids=json.dumps(sorted(set(evidence_ids))),
                          properties_json=json.dumps(properties or {},sort_keys=True)))
    snapshots=tables['snapshots']; records=tables['source_records']
    labels={s['id']:s for s in snapshots.values() if records[s['record_id']]['source_system']=='dsld'}
    issues=list(tables['review_queue'].values())
    def with_issues(row):
        return dict(row, unresolved_issues=[i for i in issues if i['owner_id']==row['id']])
    for s in labels.values():
        node(s['id'],'ProductLabel',dict(with_issues(s),source_record=records[s['record_id']],identity_scope='source_label_snapshot_not_canonical_product'))
    origins={r['id']:r for r in tables['occurrences'].values() if r['snapshot_id'] in labels}
    reviewed={r['origin_occurrence_id']:r for r in review['reviews']}
    for o in origins.values():
        role=reviewed.get(o['id'],{}).get('interpreted_role',o['role'])
        node(o['id'],'IngredientOccurrence',dict(with_issues(o),interpreted_role=role))
        edge(o['snapshot_id'],o['id'],'DECLARES_OCCURRENCE',o['evidence_ids'])
        if o['parent_id']:
            edge(o['parent_id'],o['id'],'HAS_STANDARDIZATION_MARKER' if role=='standardization_marker_class' else ('HAS_DECLARED_FORM' if role in {'form', 'other_form'} else 'HAS_DECLARED_COMPONENT'),o['evidence_ids'])
    for serving in tables['servings'].values():
        if serving['snapshot_id'] in labels:
            node(serving['id'],'Serving',with_issues(serving))
            edge(serving['snapshot_id'],serving['id'],'DECLARES_SERVING',serving['evidence_ids'])
    for assertion in tables['assertions'].values():
        if assertion['snapshot_id'] not in labels:continue
        node(assertion['id'],'LabelAssertion',dict(with_issues(assertion),quantity_policy='original_fields_only_no_derived_dose'))
        edge(assertion['snapshot_id'],assertion['id'],'HAS_ASSERTION',assertion['evidence_ids'])
        if assertion['occurrence_id']:
            edge(assertion['id'],assertion['occurrence_id'],'ABOUT_OCCURRENCE',assertion['evidence_ids'])
        if assertion['serving_id']:
            edge(assertion['id'],assertion['serving_id'],'HAS_SERVING_BASIS',assertion['evidence_ids'])
    lookup={r['mapping_id']:r for r in review['reviews']};target_ids=set()
    for c in conf['mappings']:
        if c['confidence']!='High':continue
        r=lookup[c['mapping_id']];s=snapshots[r['target_snapshot_id']]
        if s['id'] not in target_ids:
            node(s['id'],'ChemicalCompound' if c['target_source']=='pubchem' else 'TerminologyConcept',dict(s,source_record=records[s['record_id']]))
            target_ids.add(s['id'])
        edge(c['origin_occurrence_id'],s['id'],c['proposed_relation'].upper(),c['evidence_ids'],c['mapping_id'],'High',
             dict(rule_id=c['rule_id'],reason=c['reason'],target_id=c['target_id'],
                  activation_basis='User-authorized High-confidence pilot export; not independent clinical validation',
                  scope='Named form only; no whole-product equivalence' if c['proposed_relation']=='exact_material_match' else 'Concept only; not exact material'))
    assert len(labels)==7 and len([e for e in edges if e['mapping_id']])==24
    checks=validate(nodes,edges,conf['mappings'],tables['evidence'])
    blocked=[r for r in issues if r['stage']=='source_conflict' and r['owner_id'] in {n['id'] for n in nodes}]
    assert any('numeric_text_serving_conflict' in r['reason_codes'] for r in blocked)
    checks['serving_conflict_retained']=True
    # Negative checks: reject dangling edges, extra low-confidence links and relation promotion.
    for change in ['endpoint','eligibility','promotion']:
        altered=[dict(e) for e in edges];item=next(e for e in altered if e['mapping_id'] and e['type']=='DENOTES_CONCEPT')
        if change=='endpoint':item['end_id']='missing'
        elif change=='eligibility':item['mapping_id']=next(c['mapping_id'] for c in conf['mappings'] if c['confidence']=='Low')
        else:item['type']='EXACT_MATERIAL_MATCH'
        try:validate(nodes,altered,conf['mappings'],tables['evidence'])
        except AssertionError:pass
        else:raise AssertionError('Negative validation failed: '+change)
    checks['negative_checks_passed']=3
    files={}
    def csv_bytes(rows,fields):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows(rows);return stream.getvalue().encode()
    for kind in sorted({n['type'] for n in nodes}):
        files['nodes/'+kind+'.csv']=csv_bytes(sorted([n for n in nodes if n['type']==kind],key=lambda n:n['id']),['id','type','properties_json'])
    files['relationships/relationships.csv']=csv_bytes(sorted(edges,key=lambda e:e['id']),list(edges[0]))
    # Preserve unresolved/excluded candidates separately, never as active graph edges.
    files['review/pending_and_excluded.json']=encoded([c for c in conf['mappings'] if c['confidence']!='High'])
    evidence_ids={i for e in edges for i in json.loads(e['evidence_ids'])}
    files['provenance/evidence.jsonl']=b''.join(encoded(tables['evidence'][i]).replace(b'\n',b'')+b'\n' for i in sorted(evidence_ids))
    files['provenance/artifacts.json']=encoded(tables['artifacts'])
    info=dict(version='pilot-graph-v1',pilot_build=review['pilot_build'],confidence_file=CONFIDENCE,
              confidence_sha256=sha((root/CONFIDENCE).read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),
              scope='Seven DSLD labels, their source-scoped occurrences/assertions/servings and High-confidence terminology targets. NatMed/Reddit graph export deferred.',
              counts=dict(nodes=len(nodes),edges=len(edges),mapping_edges=24,pending=8,excluded_exact_matches=8),
              node_types=dict(Counter(n['type'] for n in nodes)),edge_types=dict(Counter(e['type'] for e in edges)),
              validation=checks,files={name:sha(data) for name,data in files.items()})
    files['manifest.json']=encoded(info)
    out=root/'data/graph'/('pilot-graph-v1-'+sha(files['manifest.json'])[:16])
    for name,data in files.items():
        path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==data
        else:path.write_bytes(data)
    print(out.relative_to(root));print(json.dumps(info['counts']));print(info['node_types'])
    return out

if __name__=='__main__':
    build()
