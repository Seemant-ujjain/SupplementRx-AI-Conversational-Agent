"""Source/preparation-based expectations; independent from the graph retriever."""
from pathlib import Path
from collections import defaultdict
import json,copy,re
from kg_evaluation_common import ROOT,GRAPH,sha,warning_unit,load_jsonl
DSLD='data/processed/dsld/dsld-normalized-v1-66adbe28c3b0344457fb'
MAPS='data/processed/identity/ingredient-decisions-v1-1e02682e87ad7456218b'
IMPORTED='data/processed/imported/natmed-reddit-prepared-v1-b85118347d2f8de1a1ea'
def build(root=ROOT):
 root=Path(root);inputs={}
 def read(p):b=(root/p).read_bytes();inputs[p]=sha(b);return b
 def rows(p):return [json.loads(l) for l in read(p).splitlines()]
 qset=json.loads(read('data/evaluation/retrieval_questions_source_review_v3.json'));warnings=json.loads(read('data/evaluation/dsld_warning_evidence_review_v2.json'));natmed=json.loads(read('data/evaluation/natmed_relevance_review_v1.json'))
 assert qset['graph']==GRAPH
 records={r['id']:r for r in rows(DSLD+'/source_records.jsonl')};snaps=rows(DSLD+'/snapshots.jsonl');occ=rows(DSLD+'/occurrences.jsonl');assertions=rows(DSLD+'/assertions.jsonl');mappings=rows(MAPS+'/terminology_decisions.jsonl');subjects=rows(MAPS+'/natmed_subject_decisions.jsonl');categories=rows(MAPS+'/additional_reviewed_proposals.jsonl')
 labels={records[s['record_id']]['native_id']:s['id'] for s in snaps};native_by_sid={v:k for k,v in labels.items()}
 rawlabels={}
 for native in labels:
  f=f'data/raw/dsld/labels/label_{native}.json';rawlabels[native]=json.loads(read(f));assert inputs[f]==next(s['payload_digest'] for s in snaps if s['id']==labels[native])
 claims=rows('data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl');byclaim={c['id']:c for c in claims};rawreddit={r['id']:r for r in rows('data/raw/reddit/records.jsonl')};topics=rows(IMPORTED+'/reddit/topic_associations.jsonl')
 def scope(sid,topic):
  selected={o['id'] for o in occ if o['snapshot_id']==sid and o['role']=='ingredient' and o['attributes'].get('ingredientGroup')==topic}
  while True:
   extra={o['id'] for o in occ if o['snapshot_id']==sid and o['parent_id'] in selected}
   if extra<=selected:return selected
   selected|=extra
 def warning_ids(qid):return [warning_unit(u['label_id'],u['original_text']) for u in warnings['units'] if u['question_id']==qid]
 def safety(mid):return [c['id'] for c in claims if c['source']['record_id']==mid and c['claim_type']=='safety']
 cases=[]
 for q in qset['questions']:
  qid=q['id'];request=dict(question_id=qid,category=q['category'],topic=q['topic'])
  sid=q['evidence_seed_node_ids'][0];request['label_ids']=[native_by_sid[sid]] if sid in native_by_sid else []
  mid=next((i for i in q['evidence_seed_node_ids'] if i.startswith('natmed:')),None);request['monograph_id']=mid
  expected=[];support=[];context=[];checks=[];facts={};reason=''
  if int(qid[1:])<=10:
   expected=warning_ids(qid);checks=['label_attribution'];reason='Source-reviewed warning text units; duplicate exact text within a label counts once.'
  elif int(qid[1:])<=20:
   expected=q['expected_primary_claim_ids'];support=q['supporting_context_claim_ids'];checks=['clinical_pending','source_monograph_title'];facts['source_title']=q['source_monograph_title'];reason='Source-reviewed annotation IDs with the original qualifications and optional context roles.'
  elif qid=='Q21':
   ids=scope(sid,'Magnesium');selected=[a for a in assertions if a['snapshot_id']==sid and a['kind']=='composition' and a['occurrence_id'] in ids];expected=[a['id'] for a in selected];facts['quantities']={a['id']:a['original_fields']['quantity'] for a in selected};checks=['quantity_basis'];reason='All saved composition assertions for the declared Magnesium occurrence and its descendants; source quantities and basis retained.'
  elif qid=='Q22':
   ids=scope(sid,'Vitamin D');sel=[d for d in mappings if d['origin_occurrence_id'] in ids and d['confidence']=='High'];expected=[d['id'] for d in sel];facts['mapping_relations']={d['id']:d['proposed_relation'].upper() for d in sel};checks=['mapping_scope'];reason='Only reviewed High mapping decisions for Vitamin D and descendant forms; exclude co-ingredient Vitamin K mappings.'
  elif qid=='Q23':
   ids=scope(sid,'Ashwagandha');sel=[d for d in subjects if d['origin_occurrence_id'] in ids and d['monograph_id']==mid and d['confidence']=='High'];expected=warning_ids('Q03')+[d['id'] for d in sel]+safety(mid);facts['mapping_relations']={d['id']:d['proposed_relation'].upper() for d in sel};checks=['no_product_applicability','clinical_pending','source_separation'];reason='Source label warnings, approved subject relation and monograph safety statements remain separate; subject relation does not prove exact-product applicability.'
  elif qid=='Q24':
   request['label_ids']=[];q['question']='Which saved Reddit records directly mention Melatonin, and which are only inherited thread context?'
   for t in topics:
    if t['topic']!='Melatonin':continue
    r=rawreddit[t['record_id']]
    if t['topic_status']=='literal_alias_in_record':
     assert t['literal_hits']
     assert inputs[t['provenance']['file']]==t['provenance']['sha256']
     for hit in t['literal_hits']:assert r[hit['field']][hit['start']:hit['end']]==hit['text']
     expected.append(r['id'])
    elif t['topic_status']=='inherited_thread_context':context.append(r['id'])
   expected=sorted(set(expected));context=sorted(set(context));checks=['reddit_context_separation'];reason='Saved record-level literal-hit annotations validated against raw records; inherited topic rows are separate context, not direct evidence.'
  elif qid=='Q25':
   request['label_ids']=[];q['question']='Do the reviewed Omega-3 category links establish exact ingredient or formulation equivalence?'
   sel=[d for d in categories if d['confidence']=='High' and d['proposed_relation']=='member_of_category'];expected=[d['id'] for d in sel];facts['mapping_relations']={d['id']:'MEMBER_OF_CATEGORY' for d in sel};checks=['mapping_scope','no_equivalence'];reason='Two reviewed ALA-to-Omega-3 category proposals; these are collection-level links, not claims about the example fish-oil label.'
  elif qid=='Q26':
   cid=next(i for i in q['evidence_seed_node_ids'] if i.startswith('claim:'));request['claim_id']=cid;request['label_ids']=[];q['question']=f'Where saved Vitamin B12 annotation {cid} leaves dose or population unknown, what should the response show?';expected=[cid];facts['unknown_fields']={k:byclaim[cid][k] for k in ['dose','population']};checks=['null_preservation','clinical_pending'];reason='Preserve the selected raw annotation fields exactly, without borrowing values from another claim.'
  elif qid=='Q27':
   expected=warning_ids('Q07')+safety(mid);checks=['source_separation','no_product_applicability','clinical_pending'];reason='Primary NatMed precautions are scoped to captured safety/condition annotations (14); interaction/adverse-effect annotations are not silently mixed into this defined evaluation scope.'
   facts['clinical_scope']='Safety and condition-specific safety annotations; no complete medication interaction assessment.'
  elif qid=='Q28':
   checks=['personal_recommendation_abstention'];facts['answer_status']='insufficient_information';reason='Medicine and person-specific context are unspecified; no evidence unit can establish the requested personal safety conclusion.'
  elif qid=='Q29':
   request['label_ids']=[];q['question']='Which saved labels explicitly mention probiotics, and does that establish that their strains or formulations are equivalent?'
   for native,raw in rawlabels.items():
    title=bool(re.search(r'\bprobiotics?\b',raw.get('fullName',''),re.I));names=any(re.search(r'\bprobiotics?\b',o['original_name'],re.I) for o in occ if o['snapshot_id']==labels[native])
    if title or names:expected.append(labels[native])
   checks=['no_equivalence','unique_labels'];reason='Explicit title/ingredient-name mentions only; species-only inference excluded. Forty unique saved labels, not all probiotic products.'
  elif qid=='Q30':
   request['label_ids']=['25731','43261'];selected=[]
   for lid in request['label_ids']:
    ids=scope(labels[lid],'Creatine');selected.extend(a for a in assertions if a['snapshot_id']==labels[lid] and a['kind']=='composition' and a['occurrence_id'] in ids)
   expected=[a['id'] for a in selected];facts['quantities']={a['id']:a['original_fields']['quantity'] for a in selected};facts['otheringredients']={lid:rawlabels[lid]['otheringredients'] for lid in request['label_ids']};checks=['quantity_basis','no_equivalence','comparative_abstention'];reason='Source quantities/serving basis support comparison; differing other ingredients prevent identity inference and no comparative effectiveness evidence is represented.'
  case=dict(question_id=qid,request=request,expected_primary_units=sorted(set(expected)),optional_context_units=sorted(set(support)),expected_separate_context_units=sorted(set(context)),checks=checks,facts=facts,rationale=reason,review_status='assistant_source_reviewed_pending_user_adjudication',clinical_approval=False)
  cases.append(case)
  if int(qid[1:])>20:
   q.update(annotation_status='source_reviewed_pending_user_adjudication',reviewer='assistant_source_relevance_review',expected_evaluation_unit_ids=case['expected_primary_units'],expected_separate_context_units=case['expected_separate_context_units'],expected_answerability='insufficient_information' if qid=='Q28' else 'partial_answer_with_comparative_abstention' if qid=='Q30' else 'answerable_with_scope_limits',expected_result_scope=reason)
   q['expected_relevant_evidence_ids']=None;q['expected_relevant_source_spans']=None
   q['annotation_note']='Expected unit IDs and source/preparation provenance are in evaluation_cases_v1.json; legacy graph-evidence-ID/span fields remain unset for mixed-unit questions and must not be interpreted as unreviewed.'
 qset['version']='source-review-v4';qset['status']='All thirty questions have assistant-reviewed development expectations, pending user adjudication; no independent benchmark or clinical approval.'
 package=dict(version='development-v1',graph=GRAPH,graph_manifest_sha256=sha((root/GRAPH/'manifest.json').read_bytes()),cases=cases,inputs=inputs,limitations=['Fixed requests and known entity IDs; no natural-language understanding evaluation.','Expected evidence derives from raw sources, reviewed annotations and frozen preparation decisions, not retriever outputs. Some preparation rules are shared with graph construction, so this is development/conformance evaluation, not independent clinical precision/recall.','All source-relevance judgments await user adjudication.','Do not train on this set and report it as held-out performance.'])
 return package,qset

def run(root=ROOT):
 root=Path(root);package,qset=build(root)
 for p,v in [('evaluation_cases_v1.json',package),('retrieval_questions_source_review_v4.json',qset)]:
  (root/'data/evaluation'/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 print('Annotated 30 development cases; Q21-Q30 primary sizes:',{c['question_id']:len(c['expected_primary_units']) for c in package['cases'][20:]});return package,qset
if __name__=='__main__':run()
