from pathlib import Path
import json, hashlib, csv
root=Path.cwd(); p=root/'data/processed/poc/pilot-v1-a88f090b41e160766e4a'
sha=lambda b:hashlib.sha256(b).hexdigest()
protected={str(f):sha(f.read_bytes()) for base in [root/'data/raw',p] for f in base.rglob('*') if f.is_file()}
def rows(t):return {r['id']:r for r in map(json.loads,(p/(t+'.jsonl')).read_text().splitlines())}
manifest=json.loads((p/'manifest.json').read_text())
for spec in manifest['tables'].values():assert sha((p/spec['file']).read_bytes())==spec['sha256']
m,o,s,r,e,a,t,v=[rows(x) for x in ['mapping_assertions','occurrences','snapshots','source_records','evidence','artifacts','term_values','vocabulary_statements']]
for artifact in a.values(): assert sha((root/artifact['relative_path']).read_bytes())==artifact['sha256']
rules={}
def rule(name,source,native,outcome,relation,reason,next_action):
 rules[(name,source,native)]=(outcome,relation,reason,next_action)
def supported(name,source,native,relation,reason):
 rule(name,source,native,'supported_for_review',relation,reason,'Record an explicit reviewer decision before activating this relation; retain source occurrence and qualifiers.')
def gap(name,source,native,reason):
 rule(name,source,native,'needs_evidence',None,reason,'Resolve the stated scope/qualifier gap; leave this candidate inactive meanwhile.')
def incompatible(name,source,native,reason):
 rule(name,source,native,'incompatible_exact_match',None,reason,'Recommend excluding this candidate from exact identity matching; any alternative relation requires separate evidence and review.')
for name,pc,rx,mesh in [('Creatine','586','2907','D003401'),('Magnesium','5462224','6574','D008274'),('Iron','23925','90176','D007501')]:
 gap(name,'pubchem',pc,'The label declares a nutrient/ingredient through named forms; the CID specifies the parent compound or element. This does not establish the actual label material as that structure. A parent-related relation requires explicit scope review.')
 for source,native in [('rxnorm',rx),('mesh',mesh)]:
  supported(name,source,native,'denotes_concept','The declaration and saved terminology identify the same generic concept. Preserve the separately declared forms; this does not assert elemental metal, a free parent compound, or exact material identity in the product.')
supported('Creatine HCl','pubchem','134732','exact_material_match','Saved alias Creatine HCl and the hydrochloride structure agree with the explicit label form. This supports named-form identity only, not purity, quantity or product equivalence.')
for native in ['2907','1310467']:
 incompatible('Creatine HCl','rxnorm',native,'The explicit hydrochloride form is not the saved '+('unqualified creatine concept.' if native=='2907' else 'creatine monohydrate form.'))
for source,native in [('pubchem','80116'),('rxnorm','1310467')]:
 supported('Creatine Monohydrate',source,native,'exact_material_match','Both label and target explicitly identify the monohydrate. Retain the branded buffering prefix; identity of that technology or whole product is not established.')
gap('Magnesium Citrate','pubchem','6099959','The CID specifies trimagnesium dicitrate; the label omits stoichiometry and hydration. Do not equate this precise structure with the unspecified source material.')
for source,native in [('rxnorm','52356'),('mesh','C110422')]:
 supported('Magnesium Citrate',source,native,'denotes_concept','The named citrate concept agrees with the label form. Saved MeSH data do not supply a scope note here; this proposal is limited to the named concept and does not resolve stoichiometry or hydration.')
for name,native in [('Withanolides','D054358'),('Alkaloids','D000470')]:
 supported(name,'mesh',native,'denotes_concept','The parent botanical blend declares a percentage standardization marker. The saved MeSH scope is a chemical class, consistent with that marker; do not interpret the marker as the entire blend or a single constituent.')
incompatible('Withanolides','pubchem','11049407','Despite the broad Withanolides synonym, this CID has a single structure and the alias Withanolide S. A class-level percentage marker does not identify that individual constituent.')
gap('Ferric Sodium Edetate','pubchem','27461','Saved aliases and sodium/ferric EDTA structure support a named-material candidate, but the CID specifies a composition without water while the label does not resolve hydration. Review material-level versus hydrate-specific identity before exact matching.')
gap('Ferric Sodium Edetate','mesh','C019179','The saved Fe(III)-EDTA record includes sodium, ammonium and potassium concepts; its note refers to the parent compound. The sodium alias alone cannot make this broader record an exact sodium-salt match. Review a broader-concept relation or a specific concept target.')
gap('Ferric Ammonium Citrate','pubchem','118984355','The CID encodes a specific disconnected composition/charge; the label names ferric ammonium citrate without specifying that representation. Matching titles alone cannot establish exact material identity.')
for source,native in [('rxnorm','24897'),('mesh','C013531')]:
 supported('Ferric Ammonium Citrate',source,native,'denotes_concept','The named concept agrees with the label. MeSH explicitly describes an unspecified ammonium-ferric salt, supporting concept mapping rather than a precise composition.')
incompatible('Acacia Gum','rxnorm','905301','The target explicitly denotes arabic gum allergenic extract. The source declares Acacia Gum, with no allergenic-extract preparation qualifier.')
supported('Acacia Gum','mesh','D006170','denotes_concept','The saved Gum Arabic scope describes exudate from Acacia species, consistent with Acacia Gum. Species and processing remain unknown; no exact botanical material identity is asserted.')
supported('Fructooligosaccharides','rxnorm','259372','denotes_concept','The saved IN concept fructooligosaccharide agrees with the FOS ingredient group and plural declaration. Chain length and mixture composition remain unknown.')
incompatible('Fructooligosaccharides','pubchem','439709','The CID identifies beta-D-fructose (C6H12O6), not the fructooligosaccharide material declared by the label. A component relationship would require separate support.')
reviews=[];used=set()
for mapping in m.values():
 origin=o[mapping['origin_occurrence_id']]; target=r[mapping['target_record_id']]; snapshot=s[mapping['target_snapshot_id']]; parent=o.get(origin['parent_id'])
 key=(origin['original_name'],target['source_system'],target['native_id'].split('/')[-1]);used.add(key)
 outcome,relation,reason,action=rules[key]
 related={target['native_id']}
 related.update(x['typed_object']['value'] for x in v.values() if x['subject_uri']==target['native_id'] and x['predicate_uri'].split('#')[-1] in ['concept','preferredConcept'])
 statements=[x for x in v.values() if x['subject_uri'] in related and x['predicate_uri'].split('#')[-1] in ['label','scopeNote','note','concept','preferredConcept']]
 terms=[x for x in t.values() if x['snapshot_id']==snapshot['id']]
 evidence_ids=set(mapping['evidence_ids']+origin['evidence_ids']+(parent['evidence_ids'] if parent else []))
 for x in terms+statements:evidence_ids.update(x['evidence_ids'])
 attrs=snapshot['attributes']; target_name=attrs.get('Title',attrs.get('name'))
 if target_name is None:target_name=next((x['object']['value'] for x in attrs['properties'] if x['predicate'].endswith('#label')),None)
 reviews.append(dict(mapping_id=mapping['id'],origin_occurrence_id=origin['id'],dsld_label_id=r[s[origin['snapshot_id']]['record_id']]['native_id'],ingredient=origin['original_name'],source_role=origin['role'],interpreted_role='standardization_marker_class' if origin['original_name'] in ['Withanolides','Alkaloids'] else origin['role'],target_source=target['source_system'],target_id=target['native_id'],target_name=target_name,outcome=outcome,proposed_relation=relation,rationale=reason,next_action=action,original_relation=mapping['relation'],original_review_state=mapping['review_state'],review_state='needs_review',approval_applied=False,A6='pending',clinical_approval=None,lookup_id=mapping['lookup_id'],origin_attributes=origin['attributes'],parent_context=parent,target_snapshot_id=snapshot['id'],target_attributes=attrs,target_terms=terms,target_scope_statements=statements,evidence_ids=sorted(evidence_ids),rule_versions=mapping['rule_versions']))
assert used==set(rules)
assert len(reviews)==40 and len({x['mapping_id'] for x in reviews})==40
assert {x['mapping_id'] for x in reviews}==set(m)
assert all(not x['approval_applied'] and x['A6']=='pending' for x in reviews)
assert all(i in e for x in reviews for i in x['evidence_ids'])
reviews.sort(key=lambda x:(x['ingredient'],str(x['dsld_label_id']),x['target_source'],x['target_id']))
from collections import Counter
groups=[]
for name in sorted({x['ingredient'] for x in reviews}):
 rr=[x for x in reviews if x['ingredient']==name];counts=Counter(x['outcome'] for x in rr)
 groups.append(dict(ingredient=name,labels=', '.join(sorted({str(x['dsld_label_id']) for x in rr})),candidates=len(rr),**{k:counts[k] for k in ['supported_for_review','needs_evidence','incompatible_exact_match']}))
result=dict(version='pilot-candidate-review-v1',pilot_build=manifest['build_id'],pilot_manifest_sha256=sha((p/'manifest.json').read_bytes()),scope='All 40 saved candidates in this bounded pilot; not all DSLD ingredients or an exhaustive external candidate search.',reviewer='assistant evidence review; recommendations only',approval_policy='No accepted decisions, canonical identities, merges or clinical approvals are produced.',counts=dict(Counter(x['outcome'] for x in reviews)),groups=groups,reviews=reviews,evidence={i:e[i] for i in sorted({i for x in reviews for i in x['evidence_ids']})},artifacts=a)
payload=(json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode();out=root/'data/processed/identity'/('pilot-candidate-review-v1-'+sha(payload)[:16]);out.mkdir(exist_ok=True,parents=True)
(out/'review.json').write_bytes(payload)
for filename,records,fields in [('group_summary.csv',groups,list(groups[0])),('candidate_review.csv',reviews,['mapping_id','origin_occurrence_id','dsld_label_id','ingredient','interpreted_role','target_source','target_id','target_name','outcome','proposed_relation','rationale','next_action','review_state','approval_applied'])]:
 with (out/filename).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)
assert all(sha(Path(path).read_bytes())==digest for path,digest in protected.items())
(out/'validation.json').write_text(json.dumps(dict(mapping_count=40,origin_occurrences=len({x['origin_occurrence_id'] for x in reviews}),ingredient_groups=len(groups),all_candidates_accounted_for=True,all_evidence_ids_resolve=True,pilot_table_hashes_verified=True,raw_artifact_hashes_verified=True,raw_and_pilot_files_unchanged=True,approvals_applied=0,counts=result['counts']),indent=2)+'\n')
print(out.relative_to(root));print(result['counts']);print(groups)
