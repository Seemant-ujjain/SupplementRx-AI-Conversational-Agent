"""Collection-wide, type-independent preservation of captured DSLD label statements."""
from pathlib import Path
from collections import Counter
import csv,io,json,sys
from preprocess_pilot import key,encode,sha,states
from expand_topic_navigation import write_immutable
ROOT=Path(__file__).resolve().parents[1]
BASE='data/graph/full-graph-navigation-v1-073a086cbc98af6632ae'
SPEC='schemas/dsld_statement_preservation_v1.json'

def build(root=ROOT):
 root=Path(root);base=root/BASE;manifest=json.loads((base/'manifest.json').read_bytes());inputs={BASE+'/manifest.json':sha((base/'manifest.json').read_bytes()),SPEC:sha((root/SPEC).read_bytes())}
 for p,h in manifest['files'].items():assert sha((base/p).read_bytes())==h,p
 csv.field_size_limit(10000000)
 def rows(p):
  with (base/p).open() as h:return list(csv.DictReader(h))
 labels=rows('nodes/ProductLabel.csv');old=rows('nodes/LabelAssertion.csv');edges=rows('relationships/relationships.csv')
 evidence={r['id']:r for r in map(json.loads,(base/'provenance/evidence.jsonl').read_text().splitlines())};initial_eids=set(evidence)
 nodes={r['id']:r for r in old};edge_lookup={(r['start_id'],r['end_id'],r['type']):r for r in edges}
 contract_path='schemas/poc_preprocessing_contract_v0.1.json';contract=json.loads((root/contract_path).read_bytes());inputs[contract_path]=sha((root/contract_path).read_bytes());version=contract['rule_versions']['source_mapping']
 added=[];new_edges=[];inventory=[];all_paths=set();types=Counter()
 for label in labels:
  p=json.loads(label['properties_json']);sid=label['id'];native=p['source_record']['native_id'];source=f'data/raw/dsld/labels/label_{native}.json';b=(root/source).read_bytes();h=sha(b)
  assert h==p['payload_digest'],source
  inputs[source]=h;raw=json.loads(b);assert str(raw['id'])==native
  statements=raw.get('statements')
  if statements is None:statements=[]
  assert isinstance(statements,list)
  for i,s in enumerate(statements):
   assert isinstance(s,dict);path=f'/statements/{i}';all_paths.add((sid,path));loc={'pointer':path}
   eid=key('evidence',sid,'json_pointer',encode(loc),'label_statement');aid=key('assertion',sid,path,'label_statement',version)
   if aid in nodes:
    a=json.loads(nodes[aid]['properties_json']);assert a['original_fields']==s and a['snapshot_id']==sid
    assert eid in json.loads(nodes[aid]['evidence_ids']);assert evidence[eid]['original_value']==s
    assert (sid,aid,'HAS_ASSERTION') in edge_lookup
    status='already_preserved'
   else:
    assert eid not in evidence
    ev=dict(id=eid,contract_version=contract['version'],snapshot_id=sid,artifact_id=p['artifact_id'],locator_kind='json_pointer',locator=loc,support_role='label_statement',original_value=s,original_presence='present');evidence[eid]=ev
    a=dict(id=aid,contract_version=contract['version'],snapshot_id=sid,kind='label_statement',native_assertion_id=None,subject_snapshot_id=sid,occurrence_id=None,serving_id=None,original_fields=s,field_states=states(s),source_review={},evidence_role='label_information',evidence_ids=[eid],transformations=[],review_issues=[],quantity_comparison=None,quantity_policy='Source statement text only; no derived or recommended dose',statement_interpretation='Unclassified attributed label text; inclusion does not establish warning relevance or clinical truth')
    node=dict(id=aid,type='LabelAssertion',properties_json=encode(a),evidence_ids=encode([eid]));nodes[aid]=node;added.append(node)
    edge=dict(id=key('full_edge',sid,aid,'HAS_ASSERTION','',''),start_id=sid,end_id=aid,type='HAS_ASSERTION',mapping_id='',confidence='',evidence_ids=encode([eid]),properties_json=encode({}))
    new_edges.append(edge);edge_lookup[(sid,aid,'HAS_ASSERTION')]=edge;status='added';types[s.get('type') or '<missing>']+=1
   inventory.append(dict(label_id=native,snapshot_id=sid,source_file=source,source_sha256=h,source_pointer=path,assertion_id=aid,evidence_id=eid,status=status,source_type=s.get('type')))
 # Independently account for every raw statement pointer, without source-type selection.
 covered=set()
 for r in nodes.values():
  a=json.loads(r['properties_json'])
  if a['kind']!='label_statement':continue
  for eid in json.loads(r['evidence_ids']):
   e=evidence[eid];path=e['locator']['pointer']
   if path.startswith('/statements/'):
    covered.add((a['snapshot_id'],path));assert (a['snapshot_id'],r['id'],'HAS_ASSERTION') in edge_lookup
 assert covered==all_paths
 assert len({e['id'] for e in edges+new_edges})==len(edges)+len(new_edges)
 assert all(r['id'] in nodes and nodes[r['id']]==r for r in old)
 assert len(labels)==400
 report=dict(status='passed_with_documented_limitations',base_graph=BASE,labels=400,source_statement_occurrences=len(all_paths),previously_preserved=sum(r['status']=='already_preserved' for r in inventory),added_statements=len(added),new_evidence=len(set(evidence)-initial_eids),added_types=dict(types),nodes=manifest['counts']['nodes']+len(added),edges=len(edges)+len(new_edges),checks=dict(all_captured_statements_preserved=True,source_values_and_hashes_verified=True,all_statement_paths_reachable=True,existing_assertions_and_edges_unchanged=True,no_mapping_changes=True,no_clinical_approval=True),limitations=['All captured statements, including marketing/disclaimers, are preserved; they are not all warnings or verified facts.','Relevance decisions are separate from preservation.','Completeness is limited to the 400 saved statements arrays; no image/OCR or uncaptured source coverage claim.'])
 return list(nodes.values()),edges+new_edges,evidence,inventory,report,inputs,manifest

def run(root=ROOT):
 root=Path(root);nodes,edges,evidence,inventory,report,inputs,base=build(root)
 def csvdata(rows,fields):
  h=io.StringIO(newline='');w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(sorted(rows,key=lambda r:r['id']));return h.getvalue().encode()
 replace={'nodes/LabelAssertion.csv','relationships/relationships.csv','provenance/evidence.jsonl','input_manifest.json','validation_report.json'}
 files={p:(root/BASE/p).read_bytes() for p in base['files'] if p not in replace}
 files['nodes/LabelAssertion.csv']=csvdata(nodes,['id','type','properties_json','evidence_ids'])
 files['relationships/relationships.csv']=csvdata(edges,['id','start_id','end_id','type','mapping_id','confidence','evidence_ids','properties_json'])
 files['provenance/evidence.jsonl']=(''.join(encode(evidence[i])+'\n' for i in sorted(evidence))).encode()
 files['review/statement_preservation_inventory.jsonl']=(''.join(encode(r)+'\n' for r in inventory)).encode()
 files['validation_report.json']=(encode(report)+'\n').encode()
 for p,h in base['files'].items():inputs[BASE+'/'+p]=h
 signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in ['scripts/preserve_dsld_statements.py','scripts/preprocess_pilot.py','scripts/expand_topic_navigation.py','tests/test_preserve_dsld_statements.py']},python=sys.version.split()[0])
 files['input_manifest.json']=(encode(signature)+'\n').encode()
 meta=dict(version='full-graph-statements-v1',base_graph=BASE,counts={**base['counts'],'nodes':report['nodes'],'edges':report['edges'],'statements_added':report['added_statements']},node_types={**base['node_types'],'LabelAssertion':len(nodes)},edge_types=dict(Counter(e['type'] for e in edges)),validation=report['checks'],files={p:sha(b) for p,b in sorted(files.items())})
 files['manifest.json']=(encode(meta)+'\n').encode();out=root/'data/graph'/('full-graph-statements-v1-'+sha(files['manifest.json'])[:20]);write_immutable(out,files)
 freeze=dict(graph=str(out.relative_to(root)),graph_manifest_sha256=sha(files['manifest.json']),graph_files=meta['files'],status=report['status'],clinical_approval=False,scope='Statement-preservation revision; attribution is not clinical validation')
 fb=(encode(freeze)+'\n').encode();release=root/'data/graph'/('poc-statements-release-v1-'+sha(fb)[:20]);write_immutable(release,{'freeze_manifest.json':fb,'validation_report.json':files['validation_report.json']})
 for p,h in inputs.items():assert sha((root/p).read_bytes())==h
 print(out.relative_to(root));print(release.relative_to(root));print(json.dumps(report,indent=2));return out,release,report
if __name__=='__main__':run()
