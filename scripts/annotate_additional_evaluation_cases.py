from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,'scripts')
from kg_evaluation_common import GRAPH,warning_unit
root=Path.cwd();sha=lambda b:hashlib.sha256(b).hexdigest()
selection=json.load(open('data/evaluation/additional_case_selection_v1.json'));lock=selection['rule_lock'];assert sha(Path(lock['script']).read_bytes())==lock['sha256']
primary={'H01':[2],'H02':[],'H03':[3,4],'H04':[3,6,13,14,15],'H05':[2,3,4,14],'H06':[],'H07':[6,7],'H08':[4,5,6,7],'H09':[13,15],'H10':[15,16,17,18]}
context={'H04':[2],'H10':[1]}
old=json.load(open('data/evaluation/dsld_warning_evidence_review_v2.json'));known_text={u['original_text'] for u in old['units']};oldcases=json.load(open('data/evaluation/evaluation_cases_v1.json'));known_claims={i for c in oldcases['cases'] for i in c['expected_primary_units']+c['optional_context_units'] if i.startswith('claim:')}
inputs={};decisions=[];cases=[];novel=0;overlap=0
for s in selection['selection']:
 f=f'data/raw/dsld/labels/label_{s["label_id"]}.json';b=Path(f).read_bytes();inputs[f]=sha(b);r=json.loads(b);expected=[];support=[]
 for i,statement in enumerate(r['statements']):
  decision='primary' if i in primary[s['id']] else 'context' if i in context.get(s['id'],[]) else 'exclude';text=statement['notes'];unit=warning_unit(s['label_id'],text)
  reason='Explicit captured precaution, warning, consultation requirement or usage restriction.' if decision=='primary' else 'Optional locating/intended-use context; does not itself state a specific precaution.' if decision=='context' else 'Routine directions, storage, identity, composition, marketing or disclaimer outside primary warning scope.'
  if s['id']=='H10' and i==15:reason='Directions contain the loading-phase restriction and hydration/administration instructions; preserve whole original text as context, not a recommendation.'
  if s['id']=='H04' and i==2:reason='Warning locator only; retain optionally while the specific side-panel precautions are separate primary units.'
  decisions.append(dict(question_id=s['id'],source_file=f,source_sha256=inputs[f],pointer=f'/statements/{i}',original_statement=statement,decision=decision,rationale=reason,unit_id=unit,exact_text_seen_in_original_warning_set=text in known_text))
  if decision=='primary':
   expected.append(unit)
   if text in known_text:overlap+=1
   else:novel+=1
  elif decision=='context':support.append(unit)
 cases.append(dict(question_id=s['id'],question=f'What warnings and usage restrictions are captured for {s["product"]} (DSLD {s["label_id"]})?',request=dict(question_id=s['id'],category='product_label_warnings',topic=s['topic'],label_ids=[s['label_id']],monograph_id=None),expected_primary_units=sorted(set(expected)),optional_context_units=sorted(set(support)),expected_separate_context_units=[],checks=['label_attribution'],facts={},review_status='assistant_source_reviewed_pending_user_adjudication',clinical_approval=False))
claimfile='data/raw/natmedpro/upstream_derived/pending_clinical/clinical_claims.jsonl';b=Path(claimfile).read_bytes();inputs[claimfile]=sha(b);claims=[json.loads(l) for l in b.splitlines()]
monofile='data/raw/natmedpro/records.jsonl';b=Path(monofile).read_bytes();inputs[monofile]=sha(b);monos={r['id']:r for r in map(json.loads,b.splitlines())}
for qid,topic,mid,kind in [('H11','Ashwagandha','natmed:0d296c0daa1cccb456da568c','adverse_effect'),('H12','Creatine','natmed:1dcdcb859542de37540c85e3','dose')]:
 expected=[];support=[]
 for i,c in enumerate(claims):
  if c['source']['record_id']!=mid or c['claim_type']!=kind:continue
  assert c['id'] not in known_claims
  src=c['source'];section=monos[mid]['sections'][src['section_index']];assert section['text'][src['start']:src['end']]==c['claim_text']
  role='context' if qid=='H11' and c['adverse_effect_category']=='General' else 'primary'
  (support if role=='context' else expected).append(c['id']);decisions.append(dict(question_id=qid,unit_id=c['id'],source_file=claimfile,source_sha256=inputs[claimfile],pointer=f'/{i}',original_statement=c,decision=role,rationale='General tolerability is optional context; specific adverse-effect contexts are primary.' if qid=='H11' else 'Keep loading and maintenance dose/population contexts separate despite their shared source excerpt.'))
 cases.append(dict(question_id=qid,question=f'What {kind} contexts occur in the saved {topic} NatMed annotations?',request=dict(question_id=qid,category='natmed_'+kind,topic=topic,label_ids=[],monograph_id=mid),expected_primary_units=expected,optional_context_units=support,expected_separate_context_units=[],checks=['clinical_pending','source_monograph_title'],facts={'source_title':monos[mid]['title']},review_status='assistant_source_reviewed_pending_user_adjudication',clinical_approval=False))
package=dict(version='additional-diagnostic-v1',graph=GRAPH,graph_manifest_sha256=sha((Path(GRAPH)/'manifest.json').read_bytes()),rule_lock=lock,inputs=inputs,cases=cases,decisions=decisions,overlap=dict(warning_occurrences_exact_text_overlap=overlap,warning_occurrences_novel_text=novel,clinical_claim_id_overlap=0),limitations=['Twelve newly annotated cases outside the original 30; same saved collection and same assistant reviewer. Not an independent held-out benchmark.','Original products and connected source relationships/exact brand-product families were excluded. Some warning boilerplate overlaps; see overlap counts.','Rules were locked before case selection and source annotation. No tuning on these cases within v2.','Two labels have no captured warning statements; absence in the saved record is not safety assurance.'])
Path('data/evaluation/additional_evaluation_cases_v1.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n');print('Annotated',len(cases),'additional cases;',package['overlap'])
