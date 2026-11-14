"""Bounded Creatine NatMed expansion, with rule-based technical confidence."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import json,csv,io,hashlib,re,copy
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]
BASE='data/graph/pilot-reddit-v1-4029ca4e6dc2eae3'
MONO='data/raw/natmedpro/records.jsonl'
CLAIMS='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl'
SCHEMA='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claim.schema.json'
csv.field_size_limit(10_000_000)
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def key(kind,*parts):return 'creatine-expansion-'+kind+':'+sha(enc(parts))
def assess(c,m,validator):
 low=[];medium=[];s=c['source']
 if list(validator.iter_errors(c)):low.append('schema_invalid')
 if c['ingredient']['name']!=m['title'] or s['record_id']!=m['id'] or s['content_hash']!=m['content_hash'] or s['url']!=m['source_url']:low.append('source_or_subject_mismatch')
 if not 0<=s['section_index']<len(m['sections']):return 'Low',['invalid_section']
 section=m['sections'][s['section_index']]
 if section['heading']!=s['section_heading'] or not 0<=s['start']<=s['end']<=len(section['text']) or section['text'][s['start']:s['end']]!=s['excerpt'] or s['excerpt']!=c['claim_text']:low.append('excerpt_mismatch')
 for field,span in c['field_support'].items():
  value=c
  for part in field.split('.'):value=value[part]
  observed=section['text'][span['start']:span['end']]
  try:equal=Decimal(str(value))==Decimal(observed) if isinstance(value,(int,float)) else value==observed
  except Exception:equal=False
  if not equal or not 0<=span['start']<=span['end']<=len(section['text']):low.append('field_span_mismatch:'+field)
 def leaves(value,prefix=''):
  for k,v in value.items():
   field=prefix+k
   if isinstance(v,dict):yield from leaves(v,field+'.')
   elif v is not None:yield field
 for field in ['population','indication','safety_rating','effectiveness_rating','evidence_grade','adverse_effect_category']:
  if c.get(field) is not None and field not in c['field_support']:medium.append('missing_field_support:'+field)
 for field in list(leaves(c['dose'],'dose.'))+list(leaves(c['interaction'],'interaction.')):
  if field not in c['field_support']:medium.append('missing_field_support:'+field)
 return ('Low',low) if low else ('Medium',medium) if medium else ('High',['exact_subject_and_source_binding','schema_excerpt_and_populated_field_spans_verified'])
def main():
 base=ROOT/BASE;bm=json.loads((base/'manifest.json').read_bytes())
 for path,h in bm['files'].items():assert sha((base/path).read_bytes())==h
 inputs={p:sha((ROOT/p).read_bytes()) for p in [MONO,CLAIMS,SCHEMA]}
 monographs=[json.loads(l) for l in (ROOT/MONO).read_bytes().splitlines()];claims=[json.loads(l) for l in (ROOT/CLAIMS).read_bytes().splitlines()]
 mi,m=next((i,m) for i,m in enumerate(monographs) if m['title']=='Creatine')
 candidates=[(i,c) for i,c in enumerate(claims) if c['ingredient']['name']=='Creatine'];assert len(candidates)==76
 selected=[(i,c) for i,c in candidates if c['claim_type'] in {'safety','dose'} or (c['claim_type']=='effectiveness' and c['indication']=='Athletic performance.')];assert len(selected)==10
 validator=Draft202012Validator(json.loads((ROOT/SCHEMA).read_bytes()),format_checker=FormatChecker())
 review=[dict(claim_id=c['id'],claim_type=c['claim_type'],population=c['population'],indication=c['indication'],confidence=assess(c,m,validator)[0],reasons=assess(c,m,validator)[1],review_state=c['review']['state'],clinical_approval=False) for i,c in selected]
 # Negative fixtures: incompatibility is Low; missing positive support is Medium.
 bad=copy.deepcopy(selected[0][1]);bad['ingredient']['name']='Creatine HCl';assert assess(bad,m,validator)[0]=='Low'
 bad=copy.deepcopy(selected[0][1]);bad['source']['excerpt']='wrong';assert assess(bad,m,validator)[0]=='Low'
 bad=copy.deepcopy(selected[0][1]);bad['field_support']={};assert assess(bad,m,validator)[0] in {'Medium','Low'}
 nodes=[r for f in sorted((base/'nodes').glob('*.csv')) for r in csv.DictReader(f.open())];edges=list(csv.DictReader((base/'relationships/relationships.csv').open()));oldnodes=list(nodes);oldedges=list(edges)
 artifacts=json.loads((base/'provenance/artifacts.json').read_text());evidence={r['id']:r for r in map(json.loads,(base/'provenance/evidence.jsonl').read_text().splitlines())}
 aid_by_path={a['relative_path']:a['id'] for a in artifacts.values()}
 for path in [MONO,CLAIMS]:assert artifacts[aid_by_path[path]]['sha256']==inputs[path]
 def ev(path,index,pointer,value,role,span=None):
  row=monographs[index] if path==MONO else claims[index];observed=row
  for token in pointer.strip('/').split('/') if pointer else []:observed=observed[int(token)] if isinstance(observed,list) else observed[token]
  if span:observed=observed[span[0]:span[1]]
  assert observed==value
  eid=key('evidence',inputs[path],index,pointer,span,role)
  evidence[eid]=dict(id=eid,artifact_id=aid_by_path[path],locator_kind='character_span' if span else 'json_pointer',locator=dict(pointer=f'/{index}'+pointer,jsonl_line=index+1,**({'start':span[0],'end':span[1],'coordinate_system':'unicode_codepoints'} if span else {})),original_value=value,support_role=role)
  return eid
 ids={n['id'] for n in nodes}
 def node(identifier,kind,data):
  row=dict(id=identifier,type=kind,properties_json=json.dumps(data,ensure_ascii=False,sort_keys=True))
  if identifier in ids:assert next(n for n in nodes if n['id']==identifier)==row
  else:nodes.append(row);ids.add(identifier)
 def edge(start,end,kind,eids=(),confidence='',props=None):
  row=dict(id=key('edge',start,end,kind),start_id=start,end_id=end,type=kind,mapping_id='',confidence=confidence,evidence_ids=json.dumps(sorted(set(eids))),properties_json=json.dumps(props or {},sort_keys=True))
  if any(e['id']==row['id'] for e in edges):assert next(e for e in edges if e['id']==row['id'])==row
  else:edges.append(row)
 mid=key('monograph',m['id'],inputs[MONO]);subject=key('subject',mid);topic=next(n['id'] for n in nodes if n['type']=='SupplementTopic' and json.loads(n['properties_json'])['name']=='Creatine')
 me=ev(MONO,mi,'/title',m['title'],'monograph_subject');whole=ev(MONO,mi,'',m,'monograph_record')
 node(mid,'Monograph',dict(id=mid,attributes=m,source_record={'native_id':m['id'],'source_system':'natmedpro'},evidence_ids=[whole],coverage='Ten selected annotations, not a complete clinical assessment'))
 node(subject,'MonographSubject',dict(id=subject,original_name='Creatine',role='monograph_subject',evidence_ids=[me]))
 edge(mid,subject,'HAS_SUBJECT',[me]);edge(mid,topic,'HAS_SOURCE_TOPIC',[me],'High',{'scope':'General Creatine topic; not exact formulation or clinical approval'})
 refs=m['reference_documents'];assert len(refs)==1
 rid=key('reference_document',mid,0);reid=ev(MONO,mi,'/reference_documents/0',refs[0],'captured_bibliography');node(rid,'ReferenceDocument',dict(id=rid,attributes=refs[0],content_status='captured_bibliography_not_full_text_study_review'));edge(mid,rid,'HAS_REFERENCE_DOCUMENT',[reid])
 refnums=set(re.findall(r'^\s*(\d+)\.',refs[0]['text'],re.M))
 retrieval=[];evidence_issues=[]
 for (i,c),decision in zip(selected,review):
  if decision['confidence']!='High':continue
  s=c['source'];section=m['sections'][s['section_index']];assert c['review']['state']=='pending'
  ce=ev(CLAIMS,i,'',c,'clinical_annotation');path=f'/sections/{s["section_index"]}/text';ee=ev(MONO,mi,path,s['excerpt'],'claim_excerpt',(s['start'],s['end']));eids=[ce,ee]
  for field,span in c['field_support'].items():eids.append(ev(MONO,mi,path,section['text'][span['start']:span['end']],field,(span['start'],span['end'])))
  cid=key('claim',c['id'],inputs[CLAIMS]);xid=key('excerpt',mid,s['section_index'],s['start'],s['end'])
  node(cid,'ClinicalClaim',dict(id=cid,native_assertion_id=c['id'],original_fields=c,source_review=c['review'],evidence_role='clinical_reference',technical_confidence='High',clinical_approval=False,evidence_ids=eids,retrieval_policy='Original attributed excerpt and structured fields together; no product-specific advice'))
  node(xid,'SourceExcerpt',dict(id=xid,text=s['excerpt'],source=s,evidence_ids=[ee],review_state='pending'))
  edge(mid,cid,'HAS_PENDING_CLAIM',eids,'High',{'confidence_scope':'Source alignment only; pending clinical review'})
  edge(cid,subject,'ABOUT_SUBJECT',[me,ce],'High',{'scope':'General Creatine subject, not every formulation'})
  edge(cid,xid,'SUPPORTED_BY_EXCERPT',eids,'High',{'scope':'Textual support, not clinical truth'})
  edge(xid,mid,'EXCERPT_OF',[ee])
  cited=list(dict.fromkeys(n for group in re.findall(r'\(([\d,\s]+)\)',s['excerpt']) for n in re.findall(r'\d+',group)))
  missing=sorted(set(cited)-refnums)
  if missing:evidence_issues.append({'claim_id':c['id'],'missing_bibliography_numbers':missing})
  if cited:edge(xid,rid,'CITES_ENTRIES',[ee,reid],props={'citation_numbers':cited,'missing_bibliography_numbers':missing,'scope':'Source citations, not independent study validation'})
  retrieval.append(dict(claim_node=cid,claim_id=c['id'],claim_type=c['claim_type'],technical_confidence='High',review_state='pending',clinical_approval=False,source_url=s['url'],original_excerpt=s['excerpt'],population=c['population'],indication=c['indication'],dose=c['dose'],ingredient=c['ingredient'],safety_rating=c['safety_rating'],effectiveness_rating=c['effectiveness_rating'],citation_numbers=cited,evidence_ids=eids))
 # Only general DSLD Creatine declarations link here; do not propagate claim applicability to HCl or branded blends.
 subject_links=[]
 for n in oldnodes:
  if n['type']!='IngredientOccurrence':continue
  o=json.loads(n['properties_json'])
  if o['original_name']=='Creatine' and o['role']=='ingredient':
   assert o['attributes']['ingredientGroup']=='Creatine'
   edge(o['id'],subject,'RELATED_INGREDIENT_SUBJECT',o['evidence_ids']+[me],'High',{'rule':'CREATINE-SUBJECT-01','scope':'Same general ingredient subject only; no exact material identity or product safety/dose applicability'})
   subject_links.append(o['id'])
 assert len(subject_links)==2
 # Saved warning and formulation sections remain retrievable alongside selected claims, without new medical interpretations.
 for index in [3,8]:
  sec=m['sections'][index];eid=ev(MONO,mi,f'/sections/{index}/text',sec['text'],'source_context');xid=key('context',mid,index)
  node(xid,'SourceExcerpt',dict(id=xid,text=sec['text'],section_heading=sec['heading'],evidence_ids=[eid],role='original_context_not_clinically_approved'))
  edge(mid,xid,'HAS_CONTEXT_EXCERPT',[eid])
 assert nodes[:len(oldnodes)]==oldnodes and edges[:len(oldedges)]==oldedges
 assert len(ids)==len(nodes) and len({e['id'] for e in edges})==len(edges)
 assert all(e['start_id'] in ids and e['end_id'] in ids for e in edges)
 assert len(retrieval)==10 and Counter(e['type'] for e in edges)['EXACT_MATERIAL_MATCH']==6
 assert not evidence_issues
 referenced={i for e in edges for i in json.loads(e['evidence_ids'])};assert referenced<=set(evidence)
 # Rerun the Creatine source-role query from graph edges.
 query=json.loads((base/'checks/source_separated_retrieval.json').read_bytes());creatine=next(q for q in query['queries'] if q['topic']=='Creatine')
 mono_targets=[e['start_id'] for e in edges if e['end_id']==topic and e['type']=='HAS_SOURCE_TOPIC'];assert mid in mono_targets
 retrieved_ids={e['end_id'] for e in edges if e['start_id'] in mono_targets and e['type']=='HAS_PENDING_CLAIM'}
 assert retrieved_ids=={r['claim_node'] for r in retrieval}
 creatine['natmed_source_statements']=[dict(r,source='NatMed',evidence_role='clinical_reference',path=[topic,mid,r['claim_node']]) for r in retrieval];creatine['gaps']=[]
 assert len(creatine['product_labels'])==2 and len(creatine['reddit_direct_discussion'])==1
 query['limitation']='Creatine now has all three source roles, but Reddit is a packaging discussion, not a health-effect report. NatMed selection is partial and pending; clinical confidence is not inferred from technical confidence.'
 files={}
 def csvbytes(rows,fields):
  b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields);w.writeheader();w.writerows(rows);return b.getvalue().encode()
 for kind in sorted({n['type'] for n in nodes}):files['nodes/'+kind+'.csv']=csvbytes(sorted([n for n in nodes if n['type']==kind],key=lambda n:n['id']),list(nodes[0]))
 files['relationships/relationships.csv']=csvbytes(sorted(edges,key=lambda e:e['id']),list(edges[0]))
 for name in bm['files']:
  if name.startswith('review/') or name=='checks/natmed_retrieval.json':files[name]=(base/name).read_bytes()
 files['checks/source_separated_retrieval.json']=enc(query)
 files['review/creatine_selection.json']=enc(dict(total_available=76,available_by_type=dict(Counter(c['claim_type'] for i,c in candidates)),selected=review,not_selected=[dict(claim_id=c['id'],reason='Outside bounded scope, not a low-confidence judgment') for i,c in candidates if c['id'] not in {r['claim_id'] for r in review}],criteria='All seven safety and both adult-dose annotations plus athletic performance effectiveness; general subject mapping and exact source support required. Retain cautions, unknowns and complete passages.',confidence_rules={'High':'Compatible general subject, schema/source/excerpt/field spans verified; eligible as pending attributed content','Medium':'Missing positive support; hold from active export','Low':'Conflicting identity/source/schema/span; exclude from active export'},clinical_approval=False))
 files['provenance/evidence.jsonl']=b''.join(json.dumps(evidence[i],ensure_ascii=False,sort_keys=True).encode()+b'\n' for i in sorted(referenced));files['provenance/artifacts.json']=enc(artifacts)
 validation=dict(endpoints_resolve=True,original_graph_rows_preserved=True,selected_source_and_field_spans_verified=True,all_selected_citations_in_bibliography=True,pending_status_preserved=True,unknown_fields_preserved=True,negative_checks_passed=3,creatine_three_source_roles=True,clinical_approvals=0)
 info=dict(version='creatine-natmed-v1',base_graph=BASE,base_manifest_sha256=sha((base/'manifest.json').read_bytes()),inputs=inputs,script_sha256=sha(Path(__file__).read_bytes()),counts=dict(nodes=len(nodes),edges=len(edges),added_claims=len(retrieval),selected_confidence=dict(Counter(r['confidence'] for r in review)),selected_by_type=dict(Counter(r['claim_type'] for r in review))),validation=validation,files={k:sha(v) for k,v in files.items()})
 files['manifest.json']=enc(info);out=ROOT/'data/graph'/('creatine-natmed-v1-'+sha(files['manifest.json'])[:16])
 for name,b in files.items():
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert target.read_bytes()==b
  else:target.write_bytes(b)
 for path,h in inputs.items():assert sha((ROOT/path).read_bytes())==h
 for path,h in bm['files'].items():assert sha((base/path).read_bytes())==h
 print(out.relative_to(ROOT));print(info['counts']);return out
if __name__=='__main__':main()
