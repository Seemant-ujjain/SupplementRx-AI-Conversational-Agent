"""Source-scoped expected evidence and context requirements for NatMed Q11-Q20."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
QUESTIONS='data/evaluation/retrieval_questions_source_review_v2.json'
POLICY='data/evaluation/natmed_relevance_policy_v1.json'
INVENTORY='data/evaluation/natmed_question_evidence_inventory_v1.json'
CLAIMS='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl'
MONOS='data/raw/natmedpro/records.jsonl'

def sha(b):return hashlib.sha256(b).hexdigest()
def get(value,path):
 for k in path.split('.'):value=value[k]
 return value

def pointer(value,path):
 for k in path.strip('/').split('/') if path else []:
  k=k.replace('~1','/').replace('~0','~');value=value[int(k)] if isinstance(value,list) else value[k]
 return value

def relevance(claim,question_id,mid,policy):
 criterion=policy['questions'][question_id]
 if claim['source']['record_id']!=mid:return 'exclude','Different source monograph.'
 if claim['claim_type']!=criterion['claim_type']:return 'exclude','Different annotation type; outside this question’s primary evidence scope.'
 assert claim['source']['section_heading'] in criterion['sections']
 for exception in policy['supporting_context_exceptions']:
  if exception['question_id']==question_id and get(claim,exception['field'])==exception['equals']:return 'supporting_context',exception['reason']
 return 'primary','Addresses the requested saved-annotation type and monograph; retain complete source qualifications and field anchors.'

def build(root=ROOT):
 root=Path(root);inputs={}
 def read(p):
  b=(root/p).read_bytes();inputs[p]=sha(b);return b
 qset=json.loads(read(QUESTIONS));policy=json.loads(read(POLICY));inventory=json.loads(read(INVENTORY))
 claims=[json.loads(l) for l in read(CLAIMS).splitlines()];monos={m['id']:(i,m) for i,m in enumerate(map(json.loads,read(MONOS).splitlines()))}
 gp=qset['graph'];manifest=json.loads(read(gp+'/manifest.json'));assert inputs[gp+'/manifest.json']==qset['graph_manifest_sha256']
 for p in ['nodes/ClinicalClaim.csv','nodes/SourceExcerpt.csv','relationships/relationships.csv']:
  assert sha(read(gp+'/'+p))==manifest['files'][p]
 csv.field_size_limit(10000000)
 def rows(p):return list(csv.DictReader(read(p).decode().splitlines(keepends=True)))
 graph={r['id']:dict(properties=json.loads(r['properties_json']),evidence_ids=json.loads(r['evidence_ids'])) for r in rows(gp+'/nodes/ClinicalClaim.csv')}
 excerpts={r['id']:json.loads(r['properties_json']) for r in rows(gp+'/nodes/SourceExcerpt.csv')}
 edges=rows(gp+'/relationships/relationships.csv');edgeidx=defaultdict(list)
 for e in edges:edgeidx[(e['start_id'],e['type'])].append(e)
 cache={MONOS:[m for _,m in sorted(monos.values())]}
 def verify_span(s):
  if s['file'] not in cache:
   b=read(s['file']);cache[s['file']]=[json.loads(l) for l in b.splitlines()] if s['file'].endswith('.jsonl') else json.loads(b)
  assert inputs[s['file']]==s['sha256'];text=pointer(cache[s['file']],s['pointer']);assert 0<=s['start']<=s['end']<=len(text)
  return text[s['start']:s['end']]
 decisions=[];summaries=[];updated=copy.deepcopy(qset);matched_ids=set();support_count=0;heading_anchors=0
 for q in updated['questions'][10:20]:
  qid=q['id'];mid=q['evidence_seed_node_ids'][0];mi,m=monos[mid];criterion=policy['questions'][qid];assert m['title']==criterion['source_title']
  primary=[];support=[];excluded=[];local=[]
  for ci,c in enumerate(claims):
   if c['source']['record_id']!=mid:continue
   decision,reason=relevance(c,qid,mid,policy)
   if decision=='exclude':excluded.append(dict(claim_id=c['id'],reason=reason));continue
   matched_ids.add(c['id']);g=graph[c['id']]['properties'];assert g['original_fields']==c;assert g['review_state']=='pending' and g['clinical_approval'] is False
   src=c['source'];section=m['sections'][src['section_index']];assert m['content_hash']==src['content_hash']
   assert section['heading']==src['section_heading'];assert section['text'][src['start']:src['end']]==c['claim_text']==src['excerpt']
   assert verify_span(g['source_span'])==c['claim_text']
   anchors=g['field_support_anchors']
   for a in anchors:
    assert a['claim_id']==c['id'] and verify_span(a['source_span'])==a['source_text']
    b=read(a['original_anchor_provenance']['file']);assert sha(b)==a['original_anchor_provenance']['sha256']
    support_count+=1;heading_anchors+=a['anchor_scope']=='earlier_section_heading'
   parent=next(e for e in edgeidx[(mid,'HAS_PENDING_CLAIM')] if e['end_id']==c['id']);ex=edgeidx[(c['id'],'SUPPORTED_BY_EXCERPT')];assert len(ex)==1 and excerpts[ex[0]['end_id']]['text']==c['claim_text']
   subtype={'interactions with drugs':'drug_interaction','interactions with supplements':'supplement_interaction','interactions with lab tests':'laboratory_test_interference','interactions with conditions':'condition_specific_safety'}.get(src['section_heading'],c['claim_type'])
   row=dict(id='natmed_eval_unit:'+sha((qid+'\0'+c['id']).encode()),question_id=qid,claim_id=c['id'],decision=decision,rationale=reason,
    source_topic=q['topic'],source_monograph_title=m['title'],source_monograph_id=mid,source_url=src['url'],source_subtype=subtype,
    source_claim=dict(file=CLAIMS,sha256=inputs[CLAIMS],pointer=f'/{ci}'),source_excerpt=g['source_span'],original_excerpt=c['claim_text'],
    source_section=dict(file=MONOS,sha256=inputs[MONOS],pointer=f'/{mi}/sections/{src["section_index"]}/text',heading=section['heading']),
    original_structured_fields={k:v for k,v in c.items() if k not in {'id','claim_text','source','field_support'}},field_support_anchors=anchors,
    required_qualifications=criterion['qualifications'],graph_evidence_ids=graph[c['id']]['evidence_ids'],graph_path_edge_ids=[parent['id'],ex[0]['id']],
    review_status=policy['review_status'],clinical_approval=False,identity_scope='Source monograph only; no product/formulation/strain equivalence inferred')
   local.append(row);decisions.append(row);(primary if decision=='primary' else support).append(row)
  q.update(expected_relevant_evidence_ids=sorted({e for r in primary for e in r['graph_evidence_ids']}),expected_relevant_source_spans=[r['source_excerpt'] for r in primary],expected_evidence_unit_ids=[r['id'] for r in primary],expected_primary_claim_ids=[r['claim_id'] for r in primary],supporting_context_claim_ids=[r['claim_id'] for r in support],supporting_context_evidence_ids=sorted({e for r in support for e in r['graph_evidence_ids']}),expected_excluded_claims=excluded,expected_answerability='answerable_as_attributed_saved_annotations_with_source_scope',graph_answerability='expected_annotation_units_reachable',annotation_status=policy['review_status'],reviewer=policy['reviewer'],source_monograph_title=m['title'],required_qualifications=criterion['qualifications'],relevance_unit_policy=policy['unit'],supporting_context_scoring='Optional, labeled context: exclude from primary precision/recall denominators. If presented as a direct primary answer, score against its assigned role.')
  summaries.append(dict(question_id=qid,topic=q['topic'],source_title=m['title'],primary_units=len(primary),supporting_context_units=len(support),excluded_other_type_claims=len(excluded),source_subtypes=dict(Counter(r['source_subtype'] for r in local)),earlier_heading_anchors=sum(a['anchor_scope']=='earlier_section_heading' for r in local for a in r['field_support_anchors']),null_population_claims=sum(r['original_structured_fields']['population'] is None for r in local)))
 assert matched_ids=={r['claim_id'] for r in inventory['candidates']} and len(decisions)==260
 # Duplicate excerpt groups are context groups only; do not collapse differing dose/population assertions.
 shared=defaultdict(list)
 for d in decisions:shared[(d['source_monograph_id'],d['source_excerpt']['pointer'],d['source_excerpt']['start'],d['source_excerpt']['end'])].append(d['claim_id'])
 shared_groups=[ids for ids in shared.values() if len(ids)>1]
 updated['version']='source-review-v3';updated['status']='Q01-Q20 assistant source-relevance reviewed, pending user adjudication; Q21-Q30 remain unannotated; no retrieval scoring or clinical approval.';updated['natmed_annotation_file']='data/evaluation/natmed_relevance_review_v1.json'
 report=dict(status=policy['review_status'],scope=policy['scope'],graph=gp,summary=dict(questions_reviewed=10,candidate_annotations_reviewed=len(decisions),primary_units=sum(d['decision']=='primary' for d in decisions),supporting_context_units=sum(d['decision']=='supporting_context' for d in decisions),source_excerpts_verified=260,field_support_anchors_verified=support_count,earlier_section_heading_anchors=heading_anchors,shared_excerpt_groups=len(shared_groups),clinical_approvals=0),questions=summaries,decisions=decisions,shared_excerpt_groups=shared_groups,inputs=inputs,limitations=['Assistant review of retrieval relevance and captured source context; user adjudication and clinical review remain distinct and pending.','The evaluation universe is saved upstream annotations, not an exhaustive source-section extraction or wider clinical literature.','Source title restrictions and complete excerpt qualifications are required; structured fields alone cannot express every route, strain, formulation or combination.','No retrieval metric or clinical validity score has been measured.'])
 return report,updated

def run(root=ROOT):
 root=Path(root);report,questions=build(root)
 for name,value in [('natmed_relevance_review_v1.json',report),('retrieval_questions_source_review_v3.json',questions)]:
  (root/'data/evaluation'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report['summary'],indent=2));return report,questions
if __name__=='__main__':run()
