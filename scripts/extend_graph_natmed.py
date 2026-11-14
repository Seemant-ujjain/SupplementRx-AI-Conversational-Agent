"""Add one pending, source-supported NatMed annotation to the immutable pilot graph."""
from pathlib import Path
import csv, io, json, hashlib, re
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
BASE='data/graph/pilot-graph-v1-d6d19a044338fcf0'
PILOT='data/processed/poc/pilot-v1-a88f090b41e160766e4a'
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def main():
 base=ROOT/BASE;p=ROOT/PILOT
 bm=json.loads((base/'manifest.json').read_bytes());pm=json.loads((p/'manifest.json').read_bytes())
 for name,h in bm['files'].items():assert sha((base/name).read_bytes())==h
 tables={}
 for name,spec in pm['tables'].items():
  raw=(p/spec['file']).read_bytes();assert sha(raw)==spec['sha256'];tables[name]={r['id']:r for r in map(json.loads,raw.splitlines())}
 artifacts=tables['artifacts'];evidence=tables['evidence'].copy()
 for a in artifacts.values():assert sha((ROOT/a['relative_path']).read_bytes())==a['sha256']
 nodes=[r for f in sorted((base/'nodes').glob('*.csv')) for r in csv.DictReader(f.open())]
 edges=list(csv.DictReader((base/'relationships/relationships.csv').open()))
 original_nodes=list(nodes);original_edges=list(edges)
 c=next(x for x in tables['assertions'].values() if x['kind']=='clinical');f=c['original_fields'];src=f['source']
 mono=tables['snapshots'][c['subject_snapshot_id']];subject=tables['occurrences'][c['occurrence_id']]
 assert f['review']['state']=='pending' and f['population'] is None
 assert all(v is None for v in f['dose'].values())
 section=mono['attributes']['sections'][src['section_index']]
 assert section['heading']==src['section_heading'] and mono['attributes']['content_hash']==src['content_hash']
 assert section['text'][src['start']:src['end']]==src['excerpt']==f['claim_text']
 span=f['field_support']['safety_rating'];assert f['claim_text'][span['start']:span['end']]==f['safety_rating']
 excerpt_eid=next(i for i in c['evidence_ids'] if evidence[i]['support_role']=='claim_excerpt')
 excerpt_id='excerpt:'+sha(enc([mono['id'],src['section_index'],src['start'],src['end']]))
 def add_node(identifier,kind,data):nodes.append(dict(id=identifier,type=kind,properties_json=json.dumps(data,ensure_ascii=False,sort_keys=True)))
 def add_edge(start,end,kind,eids=(),confidence='',props=None):
  edges.append(dict(id='edge:'+sha(enc([start,end,kind])),start_id=start,end_id=end,type=kind,mapping_id='',confidence=confidence,evidence_ids=json.dumps(sorted(set(eids))),properties_json=json.dumps(props or {},sort_keys=True)))
 def anchor(snapshot,suffix,value,role):
  pointer=snapshot['locator']['pointer']+suffix;artifact=artifacts[snapshot['artifact_id']]
  raw=(ROOT/artifact['relative_path']).read_bytes()
  actual=[json.loads(line) for line in raw.splitlines() if line.strip()] if artifact['relative_path'].endswith('.jsonl') else json.loads(raw)
  for part in pointer.strip('/').split('/'):
   part=part.replace('~1','/').replace('~0','~');actual=actual[int(part)] if isinstance(actual,list) else actual[part]
  assert actual==value
  eid='evidence:'+sha(enc([snapshot['id'],pointer,role]))
  evidence[eid]=dict(id=eid,artifact_id=snapshot['artifact_id'],snapshot_id=snapshot['id'],locator_kind='json_pointer',locator={'pointer':pointer},original_value=value,support_role=role)
  return eid
 scientific=mono['attributes']['sections'][1]['text'];assert 'Withania somnifera' in scientific
 sci_eid=anchor(mono,'/sections/1/text',scientific,'botanical_subject_context')
 add_node(mono['id'],'Monograph',dict(mono,source_record=tables['source_records'][mono['record_id']],coverage='one selected annotation; monograph capture completeness not clinically validated'))
 add_node(subject['id'],'MonographSubject',subject)
 add_node(c['id'],'ClinicalClaim',dict(c,clinical_approval=False,retrieval_policy='attributed_pending_source_excerpt_only',limitations=['Mixed oral and topical contexts','Population unknown','Formulation unspecified','Not a complete safety assessment']))
 add_node(excerpt_id,'SourceExcerpt',dict(text=src['excerpt'],source=src,evidence_ids=[excerpt_eid],review_state='pending'))
 add_edge(mono['id'],subject['id'],'HAS_SUBJECT',subject['evidence_ids'])
 add_edge(mono['id'],c['id'],'HAS_PENDING_CLAIM',c['evidence_ids'])
 add_edge(c['id'],subject['id'],'ABOUT_SUBJECT',subject['evidence_ids']+c['evidence_ids'])
 add_edge(c['id'],excerpt_id,'SUPPORTED_BY_EXCERPT',c['evidence_ids'],props={'support':'textual alignment only; not clinical validation'})
 add_edge(excerpt_id,mono['id'],'EXCERPT_OF',[excerpt_eid])
 refdoc=next(s for s in tables['snapshots'].values() if tables['source_records'][s['record_id']]['native_type']=='reference_document')
 # Retain the complete captured bibliography, without asserting individual study support.
 ref_text=refdoc['attributes']['text'];ref_eid=anchor(refdoc,'/text',ref_text,'captured_bibliography')
 citations=list(dict.fromkeys(n for group in re.findall(r'\(([\d,\s]+)\)',src['excerpt']) for n in re.findall(r'\d+',group)))
 bibliography_ids=set(re.findall(r'^\s*(\d+)\.',ref_text,re.M));assert set(citations)<=bibliography_ids
 add_node(refdoc['id'],'ReferenceDocument',dict(refdoc,source_record=tables['source_records'][refdoc['record_id']],content_status='captured_bibliography_not_full_text_study_review'))
 add_edge(mono['id'],refdoc['id'],'HAS_REFERENCE_DOCUMENT',[ref_eid])
 add_edge(excerpt_id,refdoc['id'],'CITES_ENTRIES',[excerpt_eid,ref_eid],props={'citation_numbers':citations,'scope':'Numbers explicitly cited in this excerpt; presence in bibliography does not establish clinical support.'})
 links=[]
 for n in original_nodes:
  if n['type']!='IngredientOccurrence':continue
  o=json.loads(n['properties_json']);a=o['attributes']
  if a.get('ingredientGroup')!='Ashwagandha':continue
  assert a['category']=='botanical' and 'Genus: Withania Species: somnifera' in a['notes']
  props=dict(rule='NATMED-SUBJECT-01',scope='Shared botanical subject only; not exact formulation, product safety or dose applicability',reason='DSLD ingredient group Ashwagandha and explicit Withania somnifera agree with monograph title and scientific-name section.',clinical_approval=False,source_role=o['role'],source_formulation=o['original_name'])
  add_edge(o['id'],subject['id'],'RELATED_BOTANICAL_SUBJECT',o['evidence_ids']+[sci_eid],'High',props);links.append(o['id'])
 assert len(links)==2
 ids={n['id'] for n in nodes};assert len(ids)==len(nodes)
 assert len({e['id'] for e in edges})==len(edges)
 assert all(e['start_id'] in ids and e['end_id'] in ids for e in edges)
 assert nodes[:len(original_nodes)]==original_nodes and edges[:len(original_edges)]==original_edges
 assert Counter(e['type'] for e in edges)['EXACT_MATERIAL_MATCH']==6
 assert all(e['type']=='RELATED_BOTANICAL_SUBJECT' for e in edges[len(original_edges):] if e['start_id'] in links)
 assert not any(e['start_id'] in {n['id'] for n in nodes if n['type']=='ProductLabel'} and e['end_id']==c['id'] for e in edges)
 eids={i for e in edges for i in json.loads(e['evidence_ids'])};assert eids<=set(evidence)
 # Retrieve through actual edges, not an independently constructed medical answer.
 def targets(identifier,kind):return [e['end_id'] for e in edges if e['start_id']==identifier and e['type']==kind]
 paths=[]
 for oid in links:
  label=next(e['start_id'] for e in edges if e['end_id']==oid and e['type']=='DECLARES_OCCURRENCE')
  assert targets(oid,'RELATED_BOTANICAL_SUBJECT')==[subject['id']]
  assert targets(c['id'],'ABOUT_SUBJECT')==[subject['id']]
  assert targets(c['id'],'SUPPORTED_BY_EXCERPT')==[excerpt_id]
  paths.append(dict(label_id=json.loads(next(n for n in nodes if n['id']==label)['properties_json'])['source_record']['native_id'],node_ids=[label,oid,subject['id'],c['id'],excerpt_id,mono['id']],traversal=['DECLARES_OCCURRENCE','RELATED_BOTANICAL_SUBJECT','ABOUT_SUBJECT (reverse)','SUPPORTED_BY_EXCERPT','EXCERPT_OF']))
 retrieval=dict(question='What does the selected saved Ashwagandha safety annotation say, with its source and limitations?',review_state=f['review']['state'],clinical_approval=False,source_url=src['url'],source_record_id=src['record_id'],section=src['section_heading'],original_excerpt=src['excerpt'],population=f['population'],formulation=f['ingredient']['formulation'],dose=f['dose'],citation_numbers=citations,paths=paths,limitations=['One pending annotation, not a full monograph safety summary','Oral and topical contexts remain together; structured dose fields stay unknown','Botanical-subject links do not establish applicability to either branded blend','References are captured bibliography entries, not independently validated clinical evidence'])
 files={}
 def csvdata(rows,fields):
  buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=fields);w.writeheader();w.writerows(rows);return buf.getvalue().encode()
 for kind in sorted({n['type'] for n in nodes}):files['nodes/'+kind+'.csv']=csvdata(sorted([n for n in nodes if n['type']==kind],key=lambda n:n['id']),list(nodes[0]))
 files['relationships/relationships.csv']=csvdata(sorted(edges,key=lambda e:e['id']),list(edges[0]))
 files['review/pending_and_excluded.json']=(base/'review/pending_and_excluded.json').read_bytes()
 files['provenance/evidence.jsonl']=b''.join(json.dumps(evidence[i],sort_keys=True,ensure_ascii=False).encode()+b'\n' for i in sorted(eids))
 files['provenance/artifacts.json']=enc(artifacts)
 files['checks/natmed_retrieval.json']=enc(retrieval)
 validation=dict(endpoints_resolve=True,original_graph_rows_unchanged=True,excerpt_offsets_match=True,safety_rating_span_matches=True,cited_numbers_in_bibliography=True,pending_review_preserved=True,unknown_dose_and_population_preserved=True,no_product_safety_edges=True,exact_material_links_unchanged=True,subject_links=2,clinical_approvals=0)
 info=dict(version='pilot-natmed-v1',base_graph=BASE,base_manifest_sha256=sha((base/'manifest.json').read_bytes()),pilot=PILOT,pilot_manifest_sha256=sha((p/'manifest.json').read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),scope='Original DSLD/terminology graph plus one pending Ashwagandha annotation, monograph, subject, excerpt and captured reference document. Reddit and remaining NatMed claims are not exported.',counts=dict(nodes=len(nodes),edges=len(edges),pending_clinical_claims=1,related_subject_links=2,cited_bibliography_entries=len(citations)),node_types=dict(Counter(n['type'] for n in nodes)),edge_types=dict(Counter(e['type'] for e in edges)),validation=validation,files={k:sha(v) for k,v in files.items()})
 files['manifest.json']=enc(info);out=ROOT/'data/graph'/('pilot-natmed-v1-'+sha(files['manifest.json'])[:16])
 for name,data in files.items():
  path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():assert path.read_bytes()==data
  else:path.write_bytes(data)
 for name,h in bm['files'].items():assert sha((base/name).read_bytes())==h
 print(out.relative_to(ROOT));print(info['counts']);return out
if __name__=='__main__':main()
