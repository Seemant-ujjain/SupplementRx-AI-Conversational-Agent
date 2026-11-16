"""Locked-rule comparison on original development and newly reviewed diagnostic cases."""
from pathlib import Path
import json
from kg_evaluation_common import ROOT,GRAPH,SavedGraph,sha
from kg_retrieval_baseline import retrieve as v1
from kg_retrieval_v2 import retrieve as v2
from evaluate_kg_retrieval import evidence_scores,check_response

def mean(rows,k):
 values=[r['scores'][k] for r in rows if r['scores'][k] is not None];return sum(values)/len(values) if values else None

def score_set(g,package,retrieve):
 results=[];responses=[]
 for case in package['cases']:
  response=retrieve(g,case['request']);primary=[p['unit_id'] for p in response['primary']];context=[p['unit_id'] for p in response['context']]
  score=evidence_scores(case['expected_primary_units'],primary)
  optional=case['optional_context_units']
  results.append(dict(question_id=case['question_id'],scores=score,contract_violations=check_response(g,case,response),optional_context_returned=sorted(set(optional)&set(context)),required_context_scores=evidence_scores(case['expected_separate_context_units'],context) if case['expected_separate_context_units'] else None))
  responses.append(response)
 return dict(questions=len(results),macro_precision=mean(results,'precision'),macro_recall=mean(results,'recall'),precision_denominator=sum(r['scores']['precision'] is not None for r in results),recall_denominator=sum(r['scores']['recall'] is not None for r in results),no_primary_expected=sum(not c['expected_primary_units'] for c in package['cases']),total_false_positives=sum(r['scores']['false_positive'] for r in results),total_false_negatives=sum(r['scores']['false_negative'] for r in results),contract_violations=sum(len(r['contract_violations']) for r in results),errors=[r['question_id'] for r in results if r['scores']['false_positive'] or r['scores']['false_negative']],results=results),responses

def run(root=ROOT):
 root=Path(root);lock=json.loads((root/'data/evaluation/retrieval_v2_rule_lock.json').read_bytes());assert sha((root/lock['script']).read_bytes())==lock['sha256'],'Locked rules changed'
 original=json.loads((root/'data/evaluation/evaluation_cases_v1.json').read_bytes());additional=json.loads((root/'data/evaluation/additional_evaluation_cases_v1.json').read_bytes());assert additional['rule_lock']==lock
 for package in [original,additional]:
  assert package['graph']==GRAPH
  for p,h in package['inputs'].items():assert sha((root/p).read_bytes())==h,p
 g=SavedGraph(root);files={};report=dict(rule_lock=lock,graph=GRAPH,additional_overlap=additional['overlap'],limitations=additional['limitations']+['All-query macro scores may hide denominator differences when no primary evidence is returned; inspect misses and denominators.','Do not call original-set improvement independent generalization or clinical accuracy.'],sets={})
 for name,package in [('original_development',original),('additional_diagnostic',additional)]:
  report['sets'][name]={}
  for version,retriever in [('v1',v1),('v2',v2)]:
   score,responses=score_set(g,package,retriever);report['sets'][name][version]=score;files[name+'_'+version+'_responses.json']=(json.dumps(responses,ensure_ascii=False,indent=2)+'\n').encode()
 report['adoption_decision']='do_not_replace_v1_with_v2' if report['sets']['additional_diagnostic']['v2']['macro_recall'] < report['sets']['additional_diagnostic']['v1']['macro_recall'] else 'review_before_adoption'
 report['next_revision_requirements']=['Retain a conservative source-precaution fallback unless content explicitly demonstrates non-warning administrative/marketing text.','Do not demote dose-caution text merely because structured numeric fields are null.','Keep this diagnostic set as development data after inspection; evaluate future changes on another newly selected set.']
 files['comparison.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
 signature=dict(graph_manifest_sha256=sha((root/GRAPH/'manifest.json').read_bytes()),inputs={p:sha((root/p).read_bytes()) for p in ['data/evaluation/evaluation_cases_v1.json','data/evaluation/additional_evaluation_cases_v1.json','data/evaluation/additional_case_selection_v1.json','data/evaluation/retrieval_v2_rule_lock.json']},code={p:sha((root/p).read_bytes()) for p in ['scripts/compare_retrieval_revisions.py','scripts/kg_retrieval_v2.py','scripts/kg_retrieval_baseline.py','scripts/kg_evaluation_common.py','scripts/evaluate_kg_retrieval.py','scripts/select_additional_warning_cases.py','scripts/annotate_additional_evaluation_cases.py']},files={p:sha(b) for p,b in files.items()})
 files['manifest.json']=(json.dumps(signature,sort_keys=True,indent=2)+'\n').encode();out=root/'data/evaluation/retrieval_v2_comparison';out.mkdir(exist_ok=True)
 for p,b in files.items():(out/p).write_bytes(b)
 print(json.dumps({name:{v:{k:s[k] for k in ['macro_precision','macro_recall','precision_denominator','recall_denominator','errors','total_false_positives','total_false_negatives','contract_violations']} for v,s in versions.items()} for name,versions in report['sets'].items()},indent=2));return report
if __name__=='__main__':run()
