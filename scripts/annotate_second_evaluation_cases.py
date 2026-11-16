"""Explicit source decisions for the second additional warning diagnostic set."""
from pathlib import Path
import json,hashlib,sys
from kg_evaluation_common import GRAPH,warning_unit,ROOT
root=ROOT;sha=lambda b:hashlib.sha256(b).hexdigest()
selection=json.loads((root/'data/evaluation/additional_case_selection_v2.json').read_bytes());lock=selection['rule_lock'];assert sha((root/lock['script']).read_bytes())==lock['sha256']
primary={'J01':[3,4,5,6,12],'J02':[6,7,9,13],'J03':[],'J04':[5,6,8],'J05':[1,2,3,4,12,13],'J06':[2,3,4,5,6]}
known={u['original_text'] for u in json.loads((root/'data/evaluation/dsld_warning_evidence_review_v2.json').read_bytes())['units']}
known.update(d['original_statement']['notes'] for d in json.loads((root/'data/evaluation/additional_evaluation_cases_v1.json').read_bytes())['decisions'] if d['decision']=='primary' and 'notes' in d['original_statement'])
inputs={};cases=[];decisions=[];overlap=novel=0
for s in selection['selection']:
 f=f'data/raw/dsld/labels/label_{s["label_id"]}.json';b=(root/f).read_bytes();inputs[f]=sha(b);raw=json.loads(b);expected=[]
 for i,statement in enumerate(raw['statements']):
  role='primary' if i in primary[s['id']] else 'exclude';text=statement['notes'];unit=warning_unit(s['label_id'],text)
  reason='Captured warning, consultation requirement, tamper restriction, or explicit adult-use population context.' if role=='primary' else 'Routine directions, marketing, composition, identity, storage or disclaimer; outside primary warnings/use restrictions.'
  if (s['id'],i) in [('J01',12),('J04',5)]:reason='Adult-specific use context embedded in directions; consistent with the original adult-use relevance criterion. Preserve full wording, not a dosage recommendation.'
  decisions.append(dict(question_id=s['id'],unit_id=unit,source_file=f,source_sha256=inputs[f],pointer=f'/statements/{i}',original_statement=statement,decision=role,rationale=reason,exact_text_seen_in_prior_sets=text in known))
  if role=='primary':
   expected.append(unit)
   if text in known:overlap+=1
   else:novel+=1
 cases.append(dict(question_id=s['id'],question=f'What warnings and usage restrictions are captured for {s["product"]} (DSLD {s["label_id"]})?',request=dict(question_id=s['id'],category='product_label_warnings',topic=s['topic'],label_ids=[s['label_id']],monograph_id=None),expected_primary_units=sorted(set(expected)),optional_context_units=[],expected_separate_context_units=[],checks=['label_attribution'],facts={},review_status='assistant_source_reviewed_pending_user_adjudication',clinical_approval=False))
package=dict(version='second-additional-diagnostic-v1',graph=GRAPH,graph_manifest_sha256=sha((root/GRAPH/'manifest.json').read_bytes()),rule_lock=lock,inputs=inputs,cases=cases,decisions=decisions,overlap=dict(warning_occurrences_exact_text_overlap=overlap,warning_occurrences_novel_text=novel),limitations=['Six new warning-label examples after locking v3; original and first-diagnostic product families excluded.','Same saved collection/assistant, with overlapping boilerplate disclosed. Not an independent benchmark or clinical validation.','Original and first diagnostic cases informed v3 and are now development sets.','One selected label has no captured warning statements; no safety conclusion follows.'])
(root/'data/evaluation/additional_evaluation_cases_v2.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n');print('Second diagnostic:',len(cases),package['overlap'])
