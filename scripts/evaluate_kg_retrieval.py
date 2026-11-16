"""Evaluate fixed-request graph retrieval on assistant-reviewed development cases."""
from pathlib import Path
from collections import defaultdict
import json,statistics
from kg_evaluation_common import ROOT,GRAPH,SavedGraph,sha
from kg_retrieval_baseline import retrieve

def evidence_scores(expected,returned):
 expected=set(expected);returned=set(returned);tp=expected&returned;fp=returned-expected
 return dict(expected=len(expected),retrieved=len(returned),true_positive=len(tp),false_positive=len(fp),false_negative=len(expected-returned),precision=len(tp)/len(returned) if returned else None,recall=len(tp)/len(expected) if expected else None,false_positive_ids=sorted(fp),false_negative_ids=sorted(expected-returned))

def check_response(g,case,response):
 violations=[]
 for p in response['primary']+response['context']:
  if not p['evidence_ids']:violations.append('missing_evidence')
  if p['node_id'] and p['evidence_ids']!=g.nodes[p['node_id']]['evidence_ids']:violations.append('evidence_binding_changed')
  if any(i not in g.edges for i in p['path_edge_ids']):violations.append('invalid_path')
  if p['source']=='NatMed':
   d=p['data'];source=g.nodes[p['node_id']]['properties']
   if d['original_fields']!=source['original_fields'] or d['field_support_anchors']!=source['field_support_anchors']:violations.append('clinical_source_changed')
   if d['review_state']!='pending' or d['clinical_approval'] is not False:violations.append('clinical_status_promoted')
   if p['extra']['source_title']!=g.nodes[p['extra']['monograph_id']]['properties']['display_title']:violations.append('source_scope_changed')
  if p['source']=='reviewed_mapping':
   e=next((e for e in g.edges.values() if e['mapping_id']==p['unit_id']),None)
   if not e or p['data']['relation_type']!=e['type'] or p['data']['confidence']!='High':violations.append('mapping_scope_promoted')
   if e and p['evidence_ids']!=e['evidence_ids']:violations.append('evidence_binding_changed')
  if p['source']=='DSLD' and p['node_id'] and g.nodes[p['node_id']]['type']=='LabelAssertion':
   if p['data']['original_fields']!=g.nodes[p['node_id']]['properties']['original_fields']:violations.append('label_source_changed')
 if response['clinical_approval'] or response['product_applicability_established'] or response['equivalence_established']:violations.append('unsupported_clinical_or_identity_conclusion')
 checks=case['checks'];facts=case['facts']
 if 'personal_recommendation_abstention' in checks and (response['status']!='insufficient_information' or response['recommended_product'] is not None):violations.append('missing_personal_abstention')
 if 'comparative_abstention' in checks and (response['status']!='partial_answer_comparative_abstention' or response['recommended_product'] is not None):violations.append('missing_comparative_abstention')
 if 'null_preservation' in checks:
  if len(response['primary'])!=1 or any(response['primary'][0]['data']['original_fields'][k]!=v for k,v in facts['unknown_fields'].items()):violations.append('null_changed')
 if 'quantity_basis' in checks:
  for p in response['primary']:
   if p['unit_id'] in facts['quantities'] and p['data']['original_fields']['quantity']!=facts['quantities'][p['unit_id']]:violations.append('quantity_changed')
  if response['recommended_dose'] is not None:violations.append('dose_recommendation_inferred')
 if 'reddit_context_separation' in checks:
  if any(p['extra']['relation_type']!='MENTIONS_TOPIC' for p in response['primary']):violations.append('reddit_context_promoted')
  if any(p['extra']['relation_type']!='INHERITED_THREAD_TOPIC' for p in response['context']):violations.append('reddit_direct_demoted')
 if 'source_separation' in checks and not {'DSLD','NatMed'}<=set(p['source'] for p in response['primary']):violations.append('source_lane_missing')
 if case['question_id']=='Q30':
  c=response.get('quantity_comparison',{});expected_difference=facts['otheringredients']['25731']!=facts['otheringredients']['43261']
  if not c.get('equivalent_declared_mass_and_basis') or c.get('other_ingredient_declarations_differ')!=expected_difference:violations.append('comparison_incorrect')
 return sorted(set(violations))

def run(root=ROOT):
 root=Path(root);casepath=root/'data/evaluation/evaluation_cases_v1.json';package=json.loads(casepath.read_bytes());assert package['graph']==GRAPH
 for p,h in package['inputs'].items():assert sha((root/p).read_bytes())==h,p
 g=SavedGraph(root);assert sha((root/GRAPH/'manifest.json').read_bytes())==package['graph_manifest_sha256']
 results=[];responses=[]
 for case in package['cases']:
  response=retrieve(g,case['request']) # Expected IDs/criteria are never passed to retriever.
  score=evidence_scores(case['expected_primary_units'],[p['unit_id'] for p in response['primary']])
  separate_context=evidence_scores(case['expected_separate_context_units'],[p['unit_id'] for p in response['context']]) if case['expected_separate_context_units'] else None
  results.append(dict(question_id=case['question_id'],category=case['request']['category'],scores=score,separate_context_scores=separate_context,contract_violations=check_response(g,case,response),status=response['status']))
  responses.append(response)
 grouped=defaultdict(list)
 for r in results:grouped[r['category']].append(r)
 def mean(rows,k):
  values=[r['scores'][k] for r in rows if r['scores'][k] is not None];return sum(values)/len(values) if values else None
 source_rows=defaultdict(list)
 def unit_source(i):
  if i.startswith(('warning:','assertion:','snapshot:')):return 'DSLD'
  if i.startswith('claim:'):return 'NatMed'
  if i.startswith('reddit:'):return 'Reddit'
  return 'reviewed_mapping'
 for case,response in zip(package['cases'],responses):
  for source in ['DSLD','NatMed','Reddit','reviewed_mapping']:
   expected=[i for i in case['expected_primary_units'] if unit_source(i)==source];returned=[p['unit_id'] for p in response['primary'] if p['source']==source]
   if expected or returned:source_rows[source].append(dict(scores=evidence_scores(expected,returned)))
 report=dict(scope='Development-set fixed-request evidence retrieval, not natural-language QA, independent benchmark or clinical correctness',graph=GRAPH,questions=30,macro_precision=mean(results,'precision'),macro_recall=mean(results,'recall'),precision_denominator_questions=sum(r['scores']['precision'] is not None for r in results),recall_denominator_questions=sum(r['scores']['recall'] is not None for r in results),questions_with_retrieval_errors=[r['question_id'] for r in results if r['scores']['false_positive'] or r['scores']['false_negative']],contract_violation_count=sum(len(r['contract_violations']) for r in results),by_source={source:dict(question_source_pairs=len(rs),macro_precision=mean(rs,'precision'),macro_recall=mean(rs,'recall')) for source,rs in source_rows.items()},by_category={c:dict(questions=len(rs),macro_precision=mean(rs,'precision'),macro_recall=mean(rs,'recall')) for c,rs in grouped.items()},results=results,limitations=package['limitations']+['Baseline warning selection uses only source Precautions types, deliberately without question-specific gold exceptions.','Optional context returned as primary evidence is scored as a primary-role false positive.','Contract checks inspect structured packets and fixed abstention behavior, not open-ended generated answers.','No ranking/top-k or learned model; scores use all returned unique source units.'])
 out=root/'data/evaluation/baseline_v1';out.mkdir(exist_ok=True)
 for name,value in [('results.json',report),('responses.json',responses)]:
  (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 manifest=dict(graph_manifest_sha256=package['graph_manifest_sha256'],case_file_sha256=sha(casepath.read_bytes()),inputs=package['inputs'],code={p:sha((root/p).read_bytes()) for p in ['scripts/kg_evaluation_common.py','scripts/kg_retrieval_baseline.py','scripts/evaluate_kg_retrieval.py','scripts/annotate_contrasting_questions.py']},files={p.name:sha(p.read_bytes()) for p in out.iterdir() if p.name!='manifest.json'})
 (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['questions','macro_precision','macro_recall','questions_with_retrieval_errors','contract_violation_count']},indent=2));return report,responses
if __name__=='__main__':run()
