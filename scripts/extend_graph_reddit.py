"""Add bounded Reddit discussion/context records and test source-separated retrieval."""
from pathlib import Path
import csv,io,json,hashlib,re
from collections import Counter
csv.field_size_limit(10_000_000)
ROOT=Path(__file__).resolve().parents[1]
BASE='data/graph/pilot-natmed-v1-22d3e423dc43f4fd'
PILOT='data/processed/poc/pilot-v1-a88f090b41e160766e4a'
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def matches(text,terms):
 return [dict(term=t,start=m.start(),end=m.end(),text=m.group()) for t in terms for m in re.finditer(r'(?<!\w)'+re.escape(t)+r'(?!\w)',text,re.I)]
def main():
 base=ROOT/BASE;p=ROOT/PILOT;bm=json.loads((base/'manifest.json').read_bytes());pm=json.loads((p/'manifest.json').read_bytes())
 for name,h in bm['files'].items():assert sha((base/name).read_bytes())==h
 tables={}
 for name,spec in pm['tables'].items():
  b=(p/spec['file']).read_bytes();assert sha(b)==spec['sha256'];tables[name]={r['id']:r for r in map(json.loads,b.splitlines())}
 artifacts=tables['artifacts']
 for a in artifacts.values():assert sha((ROOT/a['relative_path']).read_bytes())==a['sha256']
 evidence={r['id']:r for r in map(json.loads,(base/'provenance/evidence.jsonl').read_text().splitlines())}
 evidence.update(tables['evidence'])
 nodes=[r for f in sorted((base/'nodes').glob('*.csv')) for r in csv.DictReader(f.open())];edges=list(csv.DictReader((base/'relationships/relationships.csv').open()))
 oldnodes=list(nodes);oldedges=list(edges)
 def node(identifier,kind,data):nodes.append(dict(id=identifier,type=kind,properties_json=json.dumps(data,ensure_ascii=False,sort_keys=True)))
 def edge(start,end,kind,eids=(),confidence='',props=None):edges.append(dict(id='edge:'+sha(enc([start,end,kind])),start_id=start,end_id=end,type=kind,mapping_id='',confidence=confidence,evidence_ids=json.dumps(sorted(set(eids))),properties_json=json.dumps(props or {},sort_keys=True)))
 reddit={s['id']:s for s in tables['snapshots'].values() if tables['source_records'][s['record_id']]['source_system']=='reddit'}
 assert len(reddit)==3
 text_eids={}
 for sid,s in reddit.items():
  a=s['attributes'];assert a['record_type']=='comment' and a['evidence_role']=='user_report'
  raw=(ROOT/artifacts[s['artifact_id']]['relative_path']).read_bytes();row=json.loads(raw.splitlines()[s['locator']['jsonl_line']-1]);assert row['text']==a['text']
  eid='evidence:'+sha(enc([sid,'text']));text_eids[sid]=eid
  evidence[eid]=dict(id=eid,artifact_id=s['artifact_id'],snapshot_id=sid,locator_kind='json_pointer',locator={'pointer':s['locator']['pointer']+'/text','jsonl_line':s['locator']['jsonl_line']},original_value=a['text'],support_role='reddit_original_text')
  node(sid,'RedditComment',dict(s,source_record=tables['source_records'][s['record_id']],evidence_role='user_report',clinical_approval=False,interpretation='discussion/opinion; no personal-use or health-outcome claim extracted',text_evidence_id=eid))
 topics={a['topic_key']:a['original_topic'] for a in tables['topic_associations'].values()}
 for tid,name in sorted(topics.items()):node(tid,'SupplementTopic',dict(name=name,scope='Navigation topic, not chemical identity or clinical applicability'))
 for a in tables['topic_associations'].values():
  if a['snapshot_id'] in reddit:
   s=reddit[a['snapshot_id']];hits=matches(s['attributes']['text'],a['matched_terms'])
   if a['mention_scope']=='own_text':
    assert hits
    kind='MENTIONS_TOPIC';confidence='High';status='explicit_text_match_only'
   else:
    assert a['mention_scope']=='thread_context' and not hits
    kind='INHERITED_THREAD_TOPIC';confidence='';status='upstream_context_not_independently_verified'
   edge(s['id'],a['topic_key'],kind,a['evidence_ids']+[text_eids[s['id']]],confidence,dict(a,text_matches=hits,review_status=status,clinical_interpretation='No efficacy, safety, use or causality inference'))
  else:
   assert any(n['id']==a['snapshot_id'] and n['type']=='Monograph' for n in nodes)
   edge(a['snapshot_id'],a['topic_key'],'HAS_SOURCE_TOPIC',a['evidence_ids'],props={'scope':'Saved monograph topic; not clinical approval'})
 # Preserve target IDs as references; do not fabricate missing posts or parent relationships.
 refs=[r for r in tables['source_references'].values() if r['source_snapshot_id'] in reddit]
 seen=set()
 for r in refs:
  assert r['target_snapshot_id'] is None
  if r['target_key'] is None:
   assert r['original_reference'] is None
   continue
  native=r['target_key']['native_id'];rid='external_reddit_reference:'+sha(native.encode())
  if rid not in seen:
   node(rid,'ExternalRecordReference',dict(source='reddit',native_id=native,expected_type=r['target_key']['native_type'],availability='outside_selected_pilot',content_loaded=False,text=None));seen.add(rid)
  edge(r['source_snapshot_id'],rid,{'IN_THREAD':'IN_THREAD_REFERENCE','REPLY_TO':'REPLY_TO_REFERENCE'}[r['role']],r['evidence_ids'],props=r)
 # Link explicit DSLD ingredient-group declarations to navigation topics, not material identities.
 topic_by_name={name:tid for tid,name in topics.items()}
 for n in oldnodes:
  if n['type']!='IngredientOccurrence':continue
  o=json.loads(n['properties_json']);group=o['attributes'].get('ingredientGroup')
  if o['role']=='ingredient' and group in topic_by_name:
   edge(o['id'],topic_by_name[group],'HAS_DECLARED_TOPIC',o['evidence_ids'],'High',dict(rule='Exact source ingredientGroup to navigation topic',scope='Ingredient-group topic only; no clinical applicability or exact material inference'))
 ids={n['id'] for n in nodes};assert len(ids)==len(nodes) and len({e['id'] for e in edges})==len(edges)
 assert all(e['start_id'] in ids and e['end_id'] in ids for e in edges)
 assert nodes[:len(oldnodes)]==oldnodes and edges[:len(oldedges)]==oldedges
 counts=Counter(e['type'] for e in edges)
 assert counts['MENTIONS_TOPIC']==1 and counts['INHERITED_THREAD_TOPIC']==4
 assert counts['IN_THREAD_REFERENCE']==3 and counts['REPLY_TO_REFERENCE']==2
 assert counts['EXACT_MATERIAL_MATCH']==6 and counts['DENOTES_CONCEPT']==18
 missing_parent=next(sid for sid,s in reddit.items() if s['attributes']['parent_id'] is None)
 assert not any(e['start_id']==missing_parent and e['type']=='REPLY_TO_REFERENCE' for e in edges)
 assert matches('creatinelike', ['creatine'])==[] and len(matches('Creatine, creatine.', ['creatine']))==2
 eids={i for e in edges for i in json.loads(e['evidence_ids'])};assert eids<=set(evidence)
 byid={n['id']:n for n in nodes}
 def incoming(identifier,kind):return [e for e in edges if e['end_id']==identifier and e['type']==kind]
 def outgoing(identifier,kind):return [e for e in edges if e['start_id']==identifier and e['type']==kind]
 def data(identifier):return json.loads(byid[identifier]['properties_json'])
 def retrieve(name):
  tid=topic_by_name[name];products=[];clinical=[];discussion=[];context=[]
  for e in incoming(tid,'HAS_DECLARED_TOPIC'):
   for link in incoming(e['start_id'],'DECLARES_OCCURRENCE'):
    label=data(link['start_id']);o=data(e['start_id'])
    products.append(dict(source='DSLD',evidence_role='label_information',label_id=label['source_record']['native_id'],product_name=label['attributes']['fullName'],ingredient=o['original_name'],evidence_ids=o['evidence_ids'],path=[link['start_id'],o['id'],tid]))
  for e in incoming(tid,'HAS_SOURCE_TOPIC'):
   for link in outgoing(e['start_id'],'HAS_PENDING_CLAIM'):
    c=data(link['end_id']);f=c['original_fields']
    clinical.append(dict(source='NatMed',evidence_role='clinical_reference',review_state=f['review']['state'],clinical_approval=False,original_excerpt=f['source']['excerpt'],source_url=f['source']['url'],population=f['population'],dose=f['dose'],evidence_ids=c['evidence_ids'],path=[tid,e['start_id'],c['id']]))
  for kind,destination in [('MENTIONS_TOPIC',discussion),('INHERITED_THREAD_TOPIC',context)]:
   for e in incoming(tid,kind):
    s=data(e['start_id']);a=s['attributes'];destination.append(dict(source='Reddit',evidence_role='user_report',text=a['text'],source_url=a['source_url'],mention_scope=a['mention_scope'],interpretation=s['interpretation'],evidence_ids=json.loads(e['evidence_ids']),path=[s['id'],tid]))
  return dict(topic=name,product_labels=products,natmed_source_statements=clinical,reddit_direct_discussion=discussion,reddit_context_only_excluded_from_direct_results=context,gaps=[role for role,rows in [('product_labels',products),('natmed_source_statements',clinical),('reddit_direct_discussion',discussion)] if not rows])
 queries=[retrieve('Creatine'),retrieve('Ashwagandha')]
 assert len(queries[0]['product_labels'])==2 and len(queries[0]['reddit_direct_discussion'])==1 and not queries[0]['natmed_source_statements']
 assert len(queries[1]['product_labels'])==2 and len(queries[1]['natmed_source_statements'])==1 and not queries[1]['reddit_direct_discussion']
 assert all(q['gaps'] for q in queries)
 files={}
 def csvdata(rows,fields):
  b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields);w.writeheader();w.writerows(rows);return b.getvalue().encode()
 for kind in sorted({n['type'] for n in nodes}):files['nodes/'+kind+'.csv']=csvdata(sorted([n for n in nodes if n['type']==kind],key=lambda n:n['id']),list(nodes[0]))
 files['relationships/relationships.csv']=csvdata(sorted(edges,key=lambda e:e['id']),list(edges[0]))
 for name in ['review/pending_and_excluded.json','checks/natmed_retrieval.json']:files[name]=(base/name).read_bytes()
 files['review/reddit_context_references.json']=enc(refs)
 files['provenance/evidence.jsonl']=b''.join(json.dumps(evidence[i],ensure_ascii=False,sort_keys=True).encode()+b'\n' for i in sorted(eids))
 files['provenance/artifacts.json']=enc(artifacts)
 files['checks/source_separated_retrieval.json']=enc(dict(question='What saved product labels, NatMed statements and Reddit discussions are available for Creatine and Ashwagandha?',queries=queries,limitation='No single selected supplement has all three evidence roles in this bounded sample. Reddit discussion is not evidence of personal use or health effects. Context-only associations are not direct mentions.'))
 info=dict(version='pilot-reddit-v1',base_graph=BASE,base_manifest_sha256=sha((base/'manifest.json').read_bytes()),pilot_manifest_sha256=sha((p/'manifest.json').read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),counts=dict(nodes=len(nodes),edges=len(edges),reddit_comments=3,topic_nodes=len(topics),external_reference_nodes=len(seen),direct_mentions=1,context_only_associations=4),edge_types=dict(counts),validation=dict(unique_ids=True,endpoints_resolve=True,original_rows_unchanged=True,raw_text_verified=True,direct_text_spans_verified=True,inherited_context_not_promoted=True,missing_parent_not_invented=True,evidence_references_resolve=True,source_separated_queries_passed=2,clinical_approvals=0),scope='All six sources represented in a bounded graph; source coverage remains incomplete for individual supplement questions.',files={n:sha(b) for n,b in files.items()})
 files['manifest.json']=enc(info);out=ROOT/'data/graph'/('pilot-reddit-v1-'+sha(files['manifest.json'])[:16])
 for name,b in files.items():
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert target.read_bytes()==b
  else:target.write_bytes(b)
 for name,h in bm['files'].items():assert sha((base/name).read_bytes())==h
 print(out.relative_to(ROOT));print(info['counts']);return out
if __name__=='__main__':main()
