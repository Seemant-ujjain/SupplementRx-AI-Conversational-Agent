"""Bind explicitly reviewed raw label statements to graph evidence; not a retriever."""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
DRAFT='data/evaluation/retrieval_questions_v1.json'
DECISIONS='data/evaluation/dsld_warning_review_decisions_v1.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def build(root=ROOT, draft_path=DRAFT):
 root=Path(root);draft=json.loads((root/draft_path).read_bytes());spec=json.loads((root/DECISIONS).read_bytes());gp=root/draft['graph'];csv.field_size_limit(10000000)
 gm=json.loads((gp/'manifest.json').read_bytes());assert sha((gp/'manifest.json').read_bytes())==draft['graph_manifest_sha256']
 used=['nodes/ProductLabel.csv','nodes/LabelAssertion.csv','relationships/relationships.csv','provenance/evidence.jsonl']
 for p in used:assert sha((gp/p).read_bytes())==gm['files'][p]
 def readnodes(t):
  with (gp/'nodes'/f'{t}.csv').open() as f:return {r['id']:dict(properties=json.loads(r['properties_json']),evidence_ids=json.loads(r['evidence_ids'])) for r in csv.DictReader(f)}
 labels=readnodes('ProductLabel');assertions=readnodes('LabelAssertion')
 bylabel={n['properties']['source_record']['native_id']:i for i,n in labels.items()}
 with (gp/'relationships/relationships.csv').open() as f:links={(r['start_id'],r['end_id']):r['id'] for r in csv.DictReader(f) if r['type']=='HAS_ASSERTION'}
 evidence={e['id']:e for e in map(json.loads,(gp/'provenance/evidence.jsonl').read_text().splitlines())}
 lookup=defaultdict(list)
 for aid,a in assertions.items():
  if a['properties']['kind']!='label_statement':continue
  for eid in a['evidence_ids']:
   e=evidence[eid];lookup[(a['properties']['snapshot_id'],e['locator']['pointer'])].append((aid,eid))
 byq=defaultdict(list);rawcache={};seen=set();evaluated=[]
 for d in spec['decisions']:
  pair=(d['question_id'],d['statement_index']);assert pair not in seen;seen.add(pair)
  f=d['source_file'];b=(root/f).read_bytes();assert sha(b)==d['source_sha256'];raw=json.loads(b);rawcache[f]=raw
  assert raw['statements'][d['statement_index']]==d['original_statement']
  lid=bylabel[d['label_id']];matches=lookup[(lid,d['source_pointer'])];bindings=[]
  for aid,eid in matches:
   assert assertions[aid]['properties']['original_fields']==d['original_statement']
   e=evidence[eid];assert e['original_value']==d['original_statement'];assert e['snapshot_id']==lid
   bindings.append(dict(assertion_id=aid,evidence_id=eid,edge_id=links.get((lid,aid))))
  state='collected_not_exported' if not bindings else 'exported_not_linked' if not any(x['edge_id'] for x in bindings) else 'preserved_and_linked'
  r=dict(d,label_node_id=lid,graph_bindings=bindings,coverage_state=state);evaluated.append(r);byq[d['question_id']].append(r)
 for f,raw in rawcache.items():assert len([r for r in evaluated if r['source_file']==f])==len(raw['statements'])
 questions=[];units=[];updated=copy.deepcopy(draft)
 for q in updated['questions']:
  if q['id'] not in byq:continue
  rows=byq[q['id']];groups=defaultdict(list)
  for r in rows:
   if r['decision']=='include':groups[r['original_statement']['notes']].append(r)
  local=[]
  for text,members in groups.items():
   uid='warning_unit:'+sha((q['id']+'\0'+members[0]['label_id']+'\0'+text).encode())
   sources=[dict(file=r['source_file'],sha256=r['source_sha256'],pointer=r['source_pointer']+'/notes',start=0,end=len(text),text=text,source_type=r['original_statement']['type']) for r in members]
   bindings=[b for r in members for b in r['graph_bindings']]
   unit=dict(id=uid,question_id=q['id'],label_id=members[0]['label_id'],original_text=text,source_spans=sources,acceptable_graph_bindings=bindings,rationales=list(dict.fromkeys(r['rationale'] for r in members)),scoring='One relevant unit; any listed source span/binding can satisfy this unit. Repeated returns do not earn extra recall.',review_status=spec['review_status'],clinical_approval=False)
   local.append(unit);units.append(unit)
  q.update(expected_relevant_evidence_ids=sorted({b['evidence_id'] for u in local for b in u['acceptable_graph_bindings']}),expected_relevant_source_spans=[s for u in local for s in u['source_spans']],expected_evidence_unit_ids=[u['id'] for u in local],expected_answerability='answerable_as_attributed_saved_label_warnings' if local else 'no_selected_warning_in_saved_statements',annotation_status=spec['review_status'],reviewer=spec['reviewer'],relevance_unit_policy=spec['relevance_unit'])
  q['graph_answerability']='partial_missing_exported_warning_evidence' if any(r['decision']=='include' and r['coverage_state']!='preserved_and_linked' for r in rows) else 'expected_warning_units_reachable'
  q['expected_excluded_statement_pointers']=[r['source_pointer'] for r in rows if r['decision']=='exclude']
  questions.append(dict(question_id=q['id'],topic=q['topic'],label_id=rows[0]['label_id'],statements_reviewed=len(rows),included_source_statements=sum(r['decision']=='include' for r in rows),unique_warning_units=len(local),repeated_text_occurrences=sum(len(u['source_spans'])-1 for u in local),included_coverage=dict(Counter(r['coverage_state'] for r in rows if r['decision']=='include'))))
 updated['version']='source-review-v1';updated['status']='Ten DSLD warning questions source-reviewed by assistant, pending user adjudication; remaining twenty questions unannotated; no retrieval scores.'
 updated['warning_annotation_file']='data/evaluation/dsld_warning_evidence_review_v1.json'
 report=dict(status=spec['review_status'],scope=spec['scope'],clinical_approval=False,questions=questions,units=units,statement_decisions=evaluated,summary=dict(questions_reviewed=len(questions),statements_reviewed=len(evaluated),included_source_statements=sum(r['decision']=='include' for r in evaluated),unique_warning_units=len(units),included_coverage=dict(Counter(r['coverage_state'] for r in evaluated if r['decision']=='include'))),limitations=['Assistant source-relevance annotation, not human adjudication or clinical validation.','Selected labels were chosen with many statements; this is not representative collection-wide warning coverage.','Full original statements are units; directions containing restrictions retain their original dose wording as context, not a recommendation.','Warnings concern the whole product, including co-ingredients; do not reassign every warning to the queried supplement.','No retrieval baseline or precision/recall measurement is implemented here.'],inputs={draft_path:sha((root/draft_path).read_bytes()),DECISIONS:sha((root/DECISIONS).read_bytes()),draft['graph']+'/manifest.json':draft['graph_manifest_sha256'],**{f:sha((root/f).read_bytes()) for f in rawcache}})
 return report,updated

def run(root=ROOT, draft_path=DRAFT, output_version="v1"):
 root=Path(root);report,questions=build(root,draft_path)
 questions['warning_annotation_file']=f'data/evaluation/dsld_warning_evidence_review_{output_version}.json'
 questions['version']='source-review-'+output_version
 for name,data in [(f'dsld_warning_evidence_review_{output_version}.json',report),(f'retrieval_questions_source_review_{output_version}.json',questions)]:
  (root/'data/evaluation'/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report['summary'],indent=2));return report,questions
if __name__=='__main__':run()
