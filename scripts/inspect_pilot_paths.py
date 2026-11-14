"""Inspect saved graph paths against bounded POC questions; no clinical inference."""
from pathlib import Path
import json, csv, hashlib
from decimal import Decimal
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/pilot-graph-v1-d6d19a044338fcf0'
def main():
 p=ROOT/GRAPH;manifest=json.loads((p/'manifest.json').read_bytes())
 digest=lambda b:hashlib.sha256(b).hexdigest()
 for name,h in manifest['files'].items():assert digest((p/name).read_bytes())==h
 nodes={r['id']:dict(r,data=json.loads(r['properties_json'])) for f in (p/'nodes').glob('*.csv') for r in csv.DictReader(f.open())}
 edges=list(csv.DictReader((p/'relationships/relationships.csv').open()))
 evidence={r['id']:r for r in map(json.loads,(p/'provenance/evidence.jsonl').read_text().splitlines())}
 artifacts=json.loads((p/'provenance/artifacts.json').read_text())
 def outgoing(identifier,kind):return [e for e in edges if e['start_id']==identifier and e['type']==kind]
 labels={n['data']['source_record']['native_id']:n for n in nodes.values() if n['type']=='ProductLabel'}
 def children(label,kind):return [nodes[e['end_id']] for e in outgoing(labels[str(label)]['id'],kind)]
 def citations(ids):
  return [dict(evidence_id=i,path=artifacts[evidence[i]['artifact_id']]['relative_path'],sha256=artifacts[evidence[i]['artifact_id']]['sha256'],locator=evidence[i]['locator']) for i in sorted(set(ids))]
 def ingredient(label,name):return next(n for n in children(label,'DECLARES_OCCURRENCE') if n['data']['original_name']==name)
 cases=[]
 def record(identifier,question,status,result):cases.append(dict(id=identifier,question=question,status=status,result=result))
 amounts=[]
 for label in ['25731','43261']:
  o=ingredient(label,'Creatine')
  a=next(n for n in children(label,'HAS_ASSERTION') if n['data']['kind']=='composition' and outgoing(n['id'],'ABOUT_OCCURRENCE')[0]['end_id']==o['id'])
  d=a['data'];q=d['original_fields']['quantity'];serving=nodes[outgoing(a['id'],'HAS_SERVING_BASIS')[0]['end_id']]['data']
  assert q['operator']=='=' and q['servingSizeQuantity']==2 and q['servingSizeUnit']=='Capsule(s)'
  assert serving['attributes']['minQuantity']==serving['attributes']['maxQuantity']==2
  mass=Decimal(str(q['quantity']))*{'mg':Decimal(1),'Gram(s)':Decimal(1000)}[q['unit']]
  amounts.append(dict(label=label,original_quantity=q,comparison_mg=str(mass),path=[labels[label]['id'],a['id'],o['id']],citations=citations(d['evidence_ids']+serving['evidence_ids'])))
 assert [Decimal(a['comparison_mg']) for a in amounts]==[Decimal(1500),Decimal(1500)]
 record('Q2','Do the two BPI labels declare equal creatine mass per two capsules?','answered',dict(answer='Yes: 1500 mg and 1.5 g are equivalent at the same two-capsule basis. Labels remain distinct; this is not a recommended dose or proof of duplicate formulations.',records=amounts))
 composition=[]
 for label in ['25731','43261']:
  other=[n for n in children(label,'DECLARES_OCCURRENCE') if n['data']['role']=='other_ingredient']
  statements=[n for n in children(label,'HAS_ASSERTION') if n['data']['kind']=='label_statement']
  composition.append(dict(label=label,other_ingredients=[n['data']['original_name'] for n in other],statements=[dict(fields=n['data']['original_fields'],citations=citations(n['data']['evidence_ids'])) for n in statements],ingredient_citations=citations([i for n in other for i in n['data']['evidence_ids']])))
 assert all(c['other_ingredients'] for c in composition)
 assert composition[0]['other_ingredients']!=composition[1]['other_ingredients']
 record('Q3','Which other ingredients and label statements appear on each BPI label?','answered',dict(answer='The label-specific other-ingredient lists differ. Statements are retrieved verbatim; missing statements are not evidence of safety.',labels=composition))
 hcl=[]
 excluded=json.loads((p/'review/pending_and_excluded.json').read_text())
 for label in ['25731','43261']:
  o=ingredient(label,'Creatine HCl');links=[e for e in edges if e['start_id']==o['id'] and e['mapping_id']]
  assert len(links)==1 and links[0]['type']=='EXACT_MATERIAL_MATCH'
  target=nodes[links[0]['end_id']]['data']['source_record'];assert target['source_system']=='pubchem' and target['native_id']=='134732'
  low=[c for c in excluded if c['origin_occurrence_id']==o['id']];assert len(low)==2 and all(c['confidence']=='Low' for c in low)
  hcl.append(dict(label=label,path=[labels[label]['id'],o['id'],links[0]['end_id']],target=target,excluded_candidates=low,citations=citations(json.loads(links[0]['evidence_ids']))))
 record('Q8','Does Creatine HCl map equivalently across PubChem, RxNorm and MeSH?','answered_with_limit',dict(answer='PubChem CID 134732 has an active exact named-form link. The two RxNorm candidates per occurrence are excluded from exact matching. No MeSH link is present in this pilot; graph absence does not prove absence from MeSH.',paths=hcl))
 servings=children('257287','DECLARES_SERVING');assert len(servings)==1;s=servings[0]['data']
 assert s['attributes']['minQuantity']==52 and '0.52' in s['attributes']['notes']
 assert any('numeric_text_serving_conflict' in x['reason_codes'] for x in s['unresolved_issues'])
 record('Q10','Which fields show the BetterYou serving conflict?','answered_with_limit',dict(answer='Label 257287 has numeric 52 mL and a note stating 0.52 ml. Cause and correct value are unresolved; do not calculate a per-mL or daily dose. Label 228638 is outside this graph.',fields=s['attributes'],issues=s['unresolved_issues'],path=[labels['257287']['id'],servings[0]['id']],citations=citations(s['evidence_ids'])))
 markers=[]
 for label in ['74939','74940']:
  for name in ['Withanolides','Alkaloids']:
   o=ingredient(label,name);parent=o['data']['parent_id'];assert any(e['end_id']==o['id'] for e in outgoing(parent,'HAS_STANDARDIZATION_MARKER'))
   links=[e for e in edges if e['start_id']==o['id'] and e['mapping_id']];assert len(links)==1 and links[0]['type']=='DENOTES_CONCEPT'
   markers.append(dict(label=label,name=name,percent=o['data']['attributes']['percent'],path=[labels[label]['id'],parent,o['id'],links[0]['end_id']],citations=citations(json.loads(links[0]['evidence_ids']))))
 record('P1','Are Ashwagandha standardization markers kept as classes?','answered',markers)
 components=[e for e in edges if e['type']=='HAS_DECLARED_COMPONENT'];assert len(components)==8
 for e in components:assert nodes[e['end_id']]['data']['role']=='ingredient'
 for e in edges:
  if e['type']=='HAS_DECLARED_FORM':assert nodes[e['end_id']]['data']['role'] in {'form','other_form'}
 record('P2','Are nested blend ingredients distinguished from forms?','answered',dict(answer='Eight nested ingredient relationships now use HAS_DECLARED_COMPONENT. Earlier export incorrectly labeled them forms; that export is preserved but superseded.',component_count=8))
 record('coverage','Which original questions remain outside this graph?','out_of_scope',dict(Q1='Jarrow labels 7841/212304 are not selected; do not substitute another magnesium product.',Q4_Q7='NatMed clinical questions require a separate export and evidence review.',Q9='Reddit records are outside this graph.',Q10='Only label 257287 is available here; cross-label comparison remains partial.'))
 report=dict(graph=GRAPH,manifest_sha256=digest((p/'manifest.json').read_bytes()),script_sha256=digest(Path(__file__).read_bytes()),cases=cases,summary=dict(Counter(c['status'] for c in cases)),scope='Saved-source path inspection, not medical answers or a full POC evaluation.',validation='All case assertions passed; source citations resolve; no graph or raw files changed.')
 raw=(json.dumps(report,indent=2,ensure_ascii=False)+'\n').encode();out=ROOT/'data/graph'/('pilot-path-review-v1-'+digest(raw)[:16]);out.mkdir(exist_ok=True)
 target=out/'report.json'
 if target.exists():assert target.read_bytes()==raw
 else:target.write_bytes(raw)
 for name,h in manifest['files'].items():assert digest((p/name).read_bytes())==h
 print(out.relative_to(ROOT));print(report['summary'])
 return out
if __name__=='__main__':main()
