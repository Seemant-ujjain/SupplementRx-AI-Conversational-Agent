"""Three fixed POC answer checks; not a general question-answering system."""
from pathlib import Path
import json,csv,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/creatine-natmed-v1-f174e5e28b21603a'
PRIOR='data/graph/creatine-answer-review-v1-d8909281d959c7c8/report.json'
csv.field_size_limit(10_000_000)
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def validate(case,evidence):
 assert all(i in evidence for i in case['evidence_ids'])
 assert case['clinical_approval'] is False
 if case['id']=='label_comparison':
  assert case['included_label_ids']==['25731','43261'] and not case['included_claim_ids']
  assert case['product_equivalence_established'] is False and case['dose_recommendation'] is None
 elif case['id']=='source_safety':
  assert len(case['included_claim_ids'])==7 and all(r['review_state']=='pending' for r in case['source_records'])
  assert {'CHILDREN','PREGNANCY AND LACTATION','BIPOLAR DISORDER','KIDNEY DYSFUNCTION','PARKINSON DISEASE'}<=set(r['population'] for r in case['source_records'])
  assert case['clinical_conclusion'] is None and case['coverage']=='selected_annotations_not_complete_safety_review'
 elif case['id']=='unanswerable':
  assert case['status']=='insufficient_evidence' and case['recommended_product'] is None and not case['included_claim_ids']
  assert case['evidence_ids']==[] and case['reason']=='No comparative product-effectiveness evidence is represented in this bounded graph.'
 else:raise AssertionError('Unknown fixed case')
def main():
 p=ROOT/GRAPH;m=json.loads((p/'manifest.json').read_bytes())
 for f,h in m['files'].items():assert sha((p/f).read_bytes())==h
 evidence={r['id']:r for r in map(json.loads,(p/'provenance/evidence.jsonl').read_text().splitlines())}
 artifacts=json.loads((p/'provenance/artifacts.json').read_text())
 nodes={r['id']:dict(r,data=json.loads(r['properties_json'])) for f in (p/'nodes').glob('*.csv') for r in csv.DictReader(f.open())}
 edges=list(csv.DictReader((p/'relationships/relationships.csv').open()))
 query=next(q for q in json.loads((p/'checks/source_separated_retrieval.json').read_bytes())['queries'] if q['topic']=='Creatine')
 prior=json.loads((ROOT/PRIOR).read_bytes());assert prior['graph_manifest_sha256']==sha((p/'manifest.json').read_bytes())
 records=next(s['label_records'] for s in prior['answer_sections'] if s['id']=='labels')
 comparisons=[];eids=set()
 for record in records:
  lid=record['path'][0];linked={e['end_id'] for e in edges if e['start_id']==lid and e['type']=='DECLARES_OCCURRENCE'}
  other=[nodes[i]['data'] for i in linked if nodes[i]['data']['role']=='other_ingredient']
  assert other
  for o in other:eids.update(o['evidence_ids'])
  eids.update(record['evidence_ids']);comparisons.append(dict(record,other_ingredients=sorted(o['original_name'] for o in other)))
 assert comparisons[0]['other_ingredients']!=comparisons[1]['other_ingredients']
 label=dict(id='label_comparison',question='Do the two saved BPI Creatine Alkaline labels have the same creatine amount and the same formulation?',status='answered_with_limit',answer='Both declare the same total creatine mass per two capsules: 1,500 mg on label 25731 and 1.5 g on label 43261. Both list creatine monohydrate and Creatine HCl, but their other-ingredient lists differ. Equal amounts do not establish identical formulations or justify merging these labels. These are saved label declarations, not recommended doses.',included_label_ids=['25731','43261'],included_claim_ids=[],source_records=comparisons,evidence_ids=sorted(eids),clinical_approval=False,product_equivalence_established=False,dose_recommendation=None,excluded_roles=['NatMed clinical statements','Reddit discussion'],exclusion_reason='Neither is needed to compare the saved labels.')
 safety=[c for c in query['natmed_source_statements'] if c['claim_type']=='safety'];assert len(safety)==7
 safety_records=[dict(claim_id=c['claim_id'],population=c['population'],source_rating=c['safety_rating'],original_excerpt=c['original_excerpt'],source_url=c['source_url'],review_state=c['review_state'],clinical_approval=False,evidence_ids=c['evidence_ids'],path=c['path']) for c in safety]
 # Return source passages rather than reducing mixed populations and qualifications to a blanket rating.
 safe=dict(id='source_safety',question='What safety statements and population qualifications are present in the selected saved Creatine NatMed annotations?',status='source_retrieval_only',answer='The selected set contains seven pending safety annotations: general short-term and long-term statements, plus statements concerning children, pregnancy/lactation, bipolar disorder, kidney dysfunction and Parkinson disease. Their original passages and source ratings are shown separately below. Unknown structured populations remain unknown. These records are not a complete safety review and do not establish that creatine or either BPI product is safe for an individual.',included_label_ids=[],included_claim_ids=[c['claim_id'] for c in safety],source_records=safety_records,evidence_ids=sorted({i for c in safety for i in c['evidence_ids']}),clinical_approval=False,clinical_conclusion=None,coverage='selected_annotations_not_complete_safety_review',excluded_claim_ids=[c['claim_id'] for c in query['natmed_source_statements'] if c['claim_type']!='safety'],excluded_roles=['Product label declarations','Reddit discussion'],exclusion_reason='Product composition and packaging discussion do not validate clinical safety. Effectiveness and dosing annotations are outside this source-safety question.')
 # Bounded-graph coverage inspection; absence here is not absence from the literature.
 clinical=[n['data'] for n in nodes.values() if n['type']=='ClinicalClaim']
 assert len(clinical)==11
 assert not any(e['type'] in {'MORE_EFFECTIVE_THAN','COMPARATIVE_PRODUCT_EFFECTIVENESS'} for e in edges)
 unsupported=dict(id='unanswerable',question='Which of these two BPI products is more effective for athletic performance?',status='insufficient_evidence',answer='The current graph cannot determine which is more effective. It contains label composition and general NatMed ingredient statements, but no comparative effectiveness evidence for these two products. Equal label amounts and a High-confidence ingredient link cannot establish product-level effectiveness. Product-specific comparative evidence would be needed.',included_label_ids=[],included_claim_ids=[],evidence_ids=[],clinical_approval=False,recommended_product=None,reason='No comparative product-effectiveness evidence is represented in this bounded graph.',coverage_check=dict(graph=GRAPH,clinical_claim_nodes_inspected=11,label_ids_considered=['25731','43261'],comparative_product_edges=0,scope='Only the current graph; not a claim about the wider literature'),excluded_roles=['General ingredient effectiveness','Reddit packaging opinion'],exclusion_reason='Neither answers a product-to-product effectiveness comparison.')
 cases=[label,safe,unsupported]
 for c in cases:validate(c,evidence)
 # Regression guards for unsupported product equivalence, lost review status, invented recommendations and citations.
 for kind in ['merge','clinical','recommendation','citation']:
  if kind=='merge':bad=copy.deepcopy(label);bad['product_equivalence_established']=True
  elif kind=='clinical':bad=copy.deepcopy(safe);bad['source_records'][0]['review_state']='approved'
  elif kind=='recommendation':bad=copy.deepcopy(unsupported);bad['recommended_product']='25731'
  else:bad=copy.deepcopy(label);bad['evidence_ids'].append('missing')
  try:validate(bad,evidence)
  except AssertionError:pass
  else:raise AssertionError('Negative guard failed: '+kind)
 source_references={c['id']:[dict(evidence_id=i,source_file=artifacts[evidence[i]['artifact_id']]['relative_path'],source_sha256=artifacts[evidence[i]['artifact_id']]['sha256'],locator=evidence[i]['locator']) for i in c['evidence_ids']] for c in cases}
 report=dict(graph=GRAPH,graph_manifest_sha256=sha((p/'manifest.json').read_bytes()),prior_answer_review=PRIOR,prior_answer_sha256=sha((ROOT/PRIOR).read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),cases=cases,source_references=source_references,validation=dict(cases_passed=3,negative_guards_passed=4,evidence_ids_resolve=True,source_roles_separated=True,pending_clinical_status_preserved=True,abstention_scope='bounded graph only',graph_unchanged=True),review=dict(status='assistant_reviewed_fixed_examples',limitation='Fixed cases with structural checks and assistant semantic review; not general QA evaluation, measured precision/recall or clinical validation. No automated medical truth check.',clinical_approval=False))
 data=enc(report);out=ROOT/'data/graph'/('contrasting-answer-review-v1-'+sha(data)[:16]);out.mkdir(exist_ok=True)
 target=out/'report.json'
 if target.exists():assert target.read_bytes()==data
 else:target.write_bytes(data)
 for f,h in m['files'].items():assert sha((p/f).read_bytes())==h
 print(out.relative_to(ROOT));print(report['validation']);return out
if __name__=='__main__':main()
