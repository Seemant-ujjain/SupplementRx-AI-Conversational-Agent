"""Fixed-question POC answer review using only the saved graph; not a general QA engine."""
from pathlib import Path
from decimal import Decimal
import csv,json,hashlib,copy
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/creatine-natmed-v1-f174e5e28b21603a'
csv.field_size_limit(10_000_000)
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
def main():
 p=ROOT/GRAPH;m=json.loads((p/'manifest.json').read_bytes())
 for name,h in m['files'].items():assert sha((p/name).read_bytes())==h
 nodes={r['id']:dict(r,data=json.loads(r['properties_json'])) for f in (p/'nodes').glob('*.csv') for r in csv.DictReader(f.open())}
 edges=list(csv.DictReader((p/'relationships/relationships.csv').open()))
 ev={r['id']:r for r in map(json.loads,(p/'provenance/evidence.jsonl').read_text().splitlines())};art=json.loads((p/'provenance/artifacts.json').read_text())
 q=next(q for q in json.loads((p/'checks/source_separated_retrieval.json').read_bytes())['queries'] if q['topic']=='Creatine')
 question='What do the saved sources say about creatine for athletic performance, and what forms and amounts do the two BPI Creatine Alkaline labels declare?'
 def targets(identifier,kind):return [e['end_id'] for e in edges if e['start_id']==identifier and e['type']==kind]
 def clinical_relevant(c):return c['claim_type']=='effectiveness' and c['indication']=='Athletic performance.'
 selected=[c for c in q['natmed_source_statements'] if clinical_relevant(c)];assert len(selected)==1
 c=selected[0];assert c['review_state']=='pending' and c['clinical_approval'] is False
 assert c['effectiveness_rating']=='POSSIBLY EFFECTIVE'
 support='Oral creatine monohydrate seems to modestly improve rowing, jumping, and soccer performance. It is unclear if it is beneficial for sprinting, cycling, swimming, or tennis performance.'
 assert support in c['original_excerpt']
 assert 'some conflicting findings exist' in c['original_excerpt']
 labels=[]
 for result in sorted(q['product_labels'],key=lambda x:x['label_id']):
  lid,oid=result['path'][:2];o=nodes[oid]['data']
  assert oid in targets(lid,'DECLARES_OCCURRENCE')
  assertions=[nodes[aid]['data'] for aid in targets(lid,'HAS_ASSERTION') if nodes[aid]['data']['kind']=='composition' and oid in targets(aid,'ABOUT_OCCURRENCE')]
  assert len(assertions)==1;a=assertions[0];quantity=a['original_fields']['quantity']
  forms=[nodes[fid]['data']['original_name'] for fid in targets(oid,'HAS_DECLARED_FORM')]
  assert set(forms)=={'Creatine HCl','Creatine Monohydrate'}
  sid=targets(a['id'],'HAS_SERVING_BASIS');assert len(sid)==1;serving=nodes[sid[0]]['data']
  assert serving['attributes']['minQuantity']==serving['attributes']['maxQuantity']==2
  assert quantity['servingSizeQuantity']==2 and quantity['servingSizeUnit']=='Capsule(s)' and quantity['operator']=='='
  comparable=Decimal(str(quantity['quantity']))*{'mg':Decimal(1),'Gram(s)':Decimal(1000)}[quantity['unit']];assert comparable==1500
  evidence_ids=set(a['evidence_ids']+o['evidence_ids']+serving['evidence_ids'])
  for fid in targets(oid,'HAS_DECLARED_FORM'):evidence_ids.update(nodes[fid]['data']['evidence_ids'])
  labels.append(dict(label_id=result['label_id'],product_name=result['product_name'],original_quantity=quantity,forms=forms,source_serving=serving['attributes'],comparison_mg=str(comparable),evidence_ids=sorted(evidence_ids),path=[lid,a['id'],oid],identity_note='Separate source label; no product merging'))
 def citations(ids):
  return [dict(evidence_id=i,source_file=art[ev[i]['artifact_id']]['relative_path'],source_sha256=art[ev[i]['artifact_id']]['sha256'],locator=ev[i]['locator']) for i in ids]
 sections=[dict(id='performance',evidence_role='clinical_reference',text='The saved NatMed monograph rates athletic performance as POSSIBLY EFFECTIVE. Its selected passage describes possible modest benefits of oral creatine monohydrate for rowing, jumping and soccer, while benefits for sprinting, cycling, swimming and tennis are uncertain. It also reports conflicting findings. This annotation is pending clinical review.',source_url=c['source_url'],claim_id=c['claim_id'],review_state='pending',clinical_approval=False,evidence_ids=c['evidence_ids'],support_excerpt=support),
 dict(id='labels',evidence_role='label_information',text='The saved BPI Creatine Alkaline labels declare 1,500 mg (label 25731) and 1.5 g (label 43261) of creatine per two capsules—equivalent mass amounts. Both list creatine monohydrate and Creatine HCl as forms. The total amount is not a separate amount for each form.',label_records=labels,evidence_ids=sorted({i for l in labels for i in l['evidence_ids']})),
 dict(id='scope',evidence_role='answer_scope',text='These are label declarations, not recommended doses. The selected NatMed passage does not establish the effectiveness of either BPI product or its HCl component. The saved Reddit packaging discussion does not answer the athletic-performance question and is omitted.',evidence_ids=[])]
 excluded=[dict(source='NatMed',record_id=x['claim_id'],reason='Safety or dosing context is outside this effectiveness-and-label-composition question; not judged unreliable') for x in q['natmed_source_statements'] if not clinical_relevant(x)]
 excluded += [dict(source='Reddit',source_url=x['source_url'],reason='Direct creatine mention, but packaging/scoop discussion is irrelevant to athletic effectiveness') for x in q['reddit_direct_discussion']]
 excluded += [dict(source='Reddit',source_url=x['source_url'],reason='Inherited thread topic only; not a direct creatine statement') for x in q['reddit_context_only_excluded_from_direct_results']]
 def check(answer):
  by={s['id']:s for s in answer};clinical=by['performance'];label=by['labels']
  assert clinical['review_state']=='pending' and clinical['clinical_approval'] is False
  assert all(i in ev for s in answer for i in s['evidence_ids'])
  assert clinical['evidence_ids']==c['evidence_ids']
  assert 'monohydrate' in clinical['text'] and 'uncertain' in clinical['text'] and 'conflicting' in clinical['text']
  assert not any(s['evidence_role']=='user_report' for s in answer)
  assert len(label['label_records'])==2
  assert {r['label_id'] for r in label['label_records']}=={'25731','43261'}
  assert all(Decimal(r['comparison_mg'])==1500 for r in label['label_records'])
 check(sections)
 # Ensure structural guards detect lost review status and unresolved citations.
 for mutation in ['review','citation','reddit']:
  bad=copy.deepcopy(sections)
  if mutation=='review':bad[0]['review_state']='approved'
  elif mutation=='citation':bad[0]['evidence_ids']=['missing_evidence']
  else:bad.append(dict(id='irrelevant',evidence_role='user_report',evidence_ids=[],text='packaging'))
  try:check(bad)
  except AssertionError:pass
  else:raise AssertionError('Negative guard failed: '+mutation)
 report=dict(question=question,graph=GRAPH,graph_manifest_sha256=sha((p/'manifest.json').read_bytes()),script_sha256=sha(Path(__file__).read_bytes()),answer_sections=sections,source_references={s['id']:citations(s['evidence_ids']) for s in sections},excluded_records=excluded,review=dict(status='assistant_reviewed_fixed_example',automated_checks='Source IDs/paths, quantities/basis, forms, pending status, scope markers and citation resolution passed; three negative guards passed.',semantic_review='Paraphrase retains monohydrate scope, tentative rating, uncertainty and conflicting findings. No inference of product efficacy, dose advice or Reddit health effects.',limitation='One curated answer example, not a general retrieval/ranking system or an independent clinical validation.',clinical_approval=False),counts=dict(included_natmed_claims=1,included_label_records=2,included_reddit_records=0,excluded_natmed_claims=9,excluded_reddit_records=2))
 raw=enc(report);out=ROOT/'data/graph'/('creatine-answer-review-v1-'+sha(raw)[:16]);out.mkdir(exist_ok=True)
 target=out/'report.json'
 if target.exists():assert target.read_bytes()==raw
 else:target.write_bytes(raw)
 for name,h in m['files'].items():assert sha((p/name).read_bytes())==h
 print(out.relative_to(ROOT));print(report['counts']);return out
if __name__=='__main__':main()
