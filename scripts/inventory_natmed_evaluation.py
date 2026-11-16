"""Source-first evidence inventory for Q11-Q20; semantic adjudication remains pending."""
from pathlib import Path
from collections import Counter
import json,csv,hashlib
ROOT=Path(__file__).resolve().parents[1]
QUESTIONS='data/evaluation/retrieval_questions_source_review_v2.json'
CLAIMS='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl'
MONOGRAPHS='data/raw/natmedpro/records.jsonl'
def sha(b):return hashlib.sha256(b).hexdigest()
def run(root=ROOT):
 root=Path(root);qset=json.loads((root/QUESTIONS).read_bytes());gp=root/qset['graph'];assert sha((gp/'manifest.json').read_bytes())==qset['graph_manifest_sha256'];gm=json.loads((gp/'manifest.json').read_bytes());csv.field_size_limit(10000000)
 for p in ['nodes/ClinicalClaim.csv','relationships/relationships.csv']:assert sha((gp/p).read_bytes())==gm['files'][p]
 with (gp/'nodes/ClinicalClaim.csv').open() as h:graph={r['id']:dict(properties=json.loads(r['properties_json']),evidence_ids=json.loads(r['evidence_ids'])) for r in csv.DictReader(h)}
 with (gp/'relationships/relationships.csv').open() as h:edges=list(csv.DictReader(h))
 links={(e['start_id'],e['end_id'],e['type']):e['id'] for e in edges}
 claimbytes=(root/CLAIMS).read_bytes();monobytes=(root/MONOGRAPHS).read_bytes();claims=[json.loads(l) for l in claimbytes.splitlines()];monos={m['id']:(i,m) for i,m in enumerate(map(json.loads,monobytes.splitlines()))}
 claimhash=sha(claimbytes);monohash=sha(monobytes)
 inventory=[];summary=[]
 for q in qset['questions'][10:20]:
  mid=q['evidence_seed_node_ids'][0];kind=q['category'].removeprefix('natmed_');selected=[]
  for i,c in enumerate(claims):
   if c['source']['record_id']!=mid or c['claim_type']!=kind:continue
   source=c['source'];mi,m=monos[mid];section=m['sections'][source['section_index']]
   assert source['content_hash']==m['content_hash'];assert section['heading']==source['section_heading']
   assert section['text'][source['start']:source['end']]==source['excerpt']==c['claim_text']
   g=graph.get(c['id']);binding=None
   if g:
    assert g['properties']['original_fields']==c;assert g['properties']['review_state']=='pending' and g['properties']['clinical_approval'] is False
    edge=links.get((mid,c['id'],'HAS_PENDING_CLAIM'));binding=dict(node_id=c['id'],evidence_ids=g['evidence_ids'],edge_id=edge)
   item=dict(question_id=q['id'],claim_id=c['id'],claim_type=kind,monograph_id=mid,source_claim=dict(file=CLAIMS,sha256=claimhash,pointer=f'/{i}'),source_excerpt=dict(file=MONOGRAPHS,sha256=monohash,pointer=f'/{mi}/sections/{source["section_index"]}/text',start=source['start'],end=source['end'],text=source['excerpt']),source_heading=source['section_heading'],original_review=c['review'],original_population=c['population'],original_dose=c['dose'],original_interaction=c['interaction'],graph_binding=binding,coverage_state='collected_not_exported' if not g else 'exported_not_linked' if not binding['edge_id'] else 'preserved_and_linked',status='source_inventory_verified_pending_semantic_adjudication')
   inventory.append(item);selected.append(item)
  summary.append(dict(question_id=q['id'],topic=q['topic'],requested_claim_type=kind,source_annotation_count=len(selected),sections=dict(Counter(r['source_heading'] for r in selected)),coverage=dict(Counter(r['coverage_state'] for r in selected))))
 report=dict(status='source_inventory_verified_pending_semantic_adjudication',graph=qset['graph'],question_summaries=summary,candidates=inventory,summary=dict(questions=10,source_claim_candidates=len(inventory),coverage=dict(Counter(r['coverage_state'] for r in inventory))),limitations=['Source claim type and monograph selection are verified independently of graph retrieval; this is not a completed gold relevance set.','Original claim fields, nulls and pending review are preserved; source excerpt equality does not establish clinical correctness or complete extraction.','Safety questions can include interactions-with-conditions sections; interaction questions may include laboratory-test and supplement interactions, not just drugs.','Review full section context and field-support anchors before adjudicating relevance or scoring.','No precision/recall or clinical approval is claimed.'],inputs={QUESTIONS:sha((root/QUESTIONS).read_bytes()),CLAIMS:sha(claimbytes),MONOGRAPHS:sha(monobytes)})
 (root/'data/evaluation/natmed_question_evidence_inventory_v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report['summary'],indent=2));return report
if __name__=='__main__':run()
