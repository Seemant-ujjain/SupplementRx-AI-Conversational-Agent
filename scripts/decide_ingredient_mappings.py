"""Collection-wide mapping triage with explicit scope, confidence and retained evidence."""
from pathlib import Path
from collections import Counter,defaultdict
import json,re,sys,os,tempfile,shutil,csv,io
csv.field_size_limit(10_000_000)
from preprocess_pilot import sha,encode,key,search_key,dot_pointer
ROOT=Path(__file__).resolve().parents[1]
DSLD='data/processed/dsld/dsld-normalized-v1-66adbe28c3b0344457fb'
TERMS='data/processed/terminology/terminology-prepared-v1-f8afbddf6af7037ac98e'
IMPORTED='data/processed/imported/natmed-reddit-prepared-v1-b85118347d2f8de1a1ea'
PILOT='data/processed/identity/pilot-candidate-review-v1-f03a6ba885c074ba/review.json'
SCOPES='data/processed/identity/ingredient-scope-review-v2-36f4c0d499c594f7/review.json'
SPEC='schemas/ingredient_mapping_decisions_v1.json'
GRAPH='data/graph/creatine-natmed-v1-f174e5e28b21603a'

def decide(source,name,target_name,active,alternatives,attributes):
    a,b=search_key(name),search_key(target_name or '')
    hcl=lambda s:bool(re.search(r'\b(hcl|hydrochloride)\b',s))
    hydrate=lambda s:bool(re.search(r'\b(monohydrate|dihydrate|trihydrate|hydrate)\b',s))
    if hcl(a) and hydrate(b) and not hcl(b):return 'Low',None,'M4','Explicit hydrochloride designation conflicts with the returned hydrate form.'
    if 'allergenic extract' in b and 'allergenic' not in a:return 'Low',None,'M4','Target denotes an allergenic preparation not declared by the source ingredient.'
    if not active:return 'Medium',None,'M3','Inactive, suppressed or insufficiently established target status needs review.'
    if alternatives!=1:return 'Medium',None,'M3','Multiple saved candidates require scope review; preferred-name agreement alone is insufficient.'
    if source=='pubchem':return 'Medium',None,'M3','A compound name/alias does not establish the label material, hydration, stereochemistry or composition without reviewed support.'
    if a!=b:return 'Medium',None,'M3','Preferred names differ; a saved synonym or broader/narrower relation needs explicit review.'
    category=(attributes.get('category') or '').casefold()
    if category=='botanical' or re.search(r'\b(blend|extract|powder|strain|whole|root|leaf)\b',a):
        return 'Medium',None,'M3','Botanical, blend, strain or preparation scope requires review beyond preferred-name agreement.'
    return 'High','denotes_concept','M2','Single active target has the same explicit preferred name; link is limited to the named concept, not exact material or product identity.'

def action(confidence):return {'High':'eligible_for_graph_construction','Medium':'pending_scope_review','Low':'exclude_exact_match'}[confidence]

def build(root=ROOT):
    root=Path(root);inputs={};cache={}
    def checked(path,expected=None):
        b=(root/path).read_bytes();h=sha(b)
        if expected is not None:assert h==expected,path
        inputs[path]=h;return b
    def manifest(folder):
        m=json.loads(checked(folder+'/manifest.json'))
        for p,h in m['files'].items():checked(folder+'/'+p,h if isinstance(h,str) else h['sha256'])
        return m
    for folder in [DSLD,TERMS,IMPORTED]:manifest(folder)
    checked(SPEC)
    def rows(folder,table):
        p=folder+'/'+table+'.jsonl'
        if p not in cache:cache[p]=[json.loads(l) for l in (root/p).read_bytes().splitlines()]
        return cache[p]
    occ={r['id']:r for r in rows(DSLD,'occurrences')};snap={r['id']:r for r in rows(DSLD,'snapshots')};rec={r['id']:r for r in rows(DSLD,'source_records')};ev={r['id']:r for r in rows(DSLD,'evidence')}
    byloc={(rec[snap[o['snapshot_id']]['record_id']]['native_id'],ev[o['evidence_ids'][0]]['locator']['pointer']):o for o in occ.values()}
    prior=json.loads(checked(PILOT));scope=json.loads(checked(SCOPES))
    for a in prior['artifacts'].values():checked(a['relative_path'],a['sha256'])
    overrides={};pilot_keys=set()
    for i,r in enumerate(prior['reviews']):
        origin=occ[r['origin_occurrence_id']];assert origin['attributes']==r['origin_attributes']
        k=(origin['id'],r['target_source'],r['target_id']);pilot_keys.add(k)
        conf={'supported_for_review':'High','needs_evidence':'Medium','incompatible_exact_match':'Low'}[r['outcome']]
        overrides[k]=(conf,r['proposed_relation'] if conf=='High' else None,'M1',r['rationale'],dict(file=PILOT,pointer=f'/reviews/{i}'))
    extra=[]
    for i,r in enumerate(scope['review_rows']):
        if not r['target']:continue
        o=byloc[(str(r['label_id']),dot_pointer(r['origin_path']))]
        case=next(c for c in scope['cases'] if c['case_id']==r['case_id'])
        checked(case['origin']['source_file'],case['origin']['source_sha256'])
        target=r['target'];src='pubchem' if target.startswith('pubchem:') else 'rxnorm' if target.startswith('rxnorm:') else 'mesh'
        native=target.split(':')[-1] if src!='mesh' else target
        conf='High' if r['recommendation']=='supported_for_review' else 'Medium'
        values=(conf,r['relation'] if conf=='High' else None,'M1',r['rationale'],dict(file=SCOPES,pointer=f'/review_rows/{i}',evidence_case_pointer=r['evidence_case_pointer']))
        k=(o['id'],src,native)
        if r['method']=='saved_lookup_candidate':overrides.setdefault(k,values)
        else:extra.append(dict(id=key('additional_mapping_proposal',o['id'],native,r['relation']),origin_occurrence_id=o['id'],target_source=src,target_native_id=native,confidence=conf,proposed_relation=r['relation'],rule='M1',reason=r['rationale'],action=action(conf),evidence=values[-1],graph_applied=False))
    decisions=[];unmatched=[];used=set();coverage=[]
    for source in ['pubchem','rxnorm','mesh']:
        folder=TERMS+'/'+source;targets={r['id']:r for r in rows(folder,'records')};queries={q['id']:q for q in rows(folder,'queries')}
        origins=defaultdict(list)
        for r in rows(folder,'query_origins'):origins[r['query_id']].append(r)
        mesh_active={}
        if source=='mesh':
            for r in rows(folder,'rdf_statements'):
                if r['predicate_uri'].endswith('#active'):mesh_active[r['subject_id']]=r['typed_object']['value']=='true'
        candidate_counts=Counter(c['query_id'] for c in rows(folder,'candidates'))
        for candidate in rows(folder,'candidates'):
            target=targets[candidate['target_record_id']];native=target['native_id'];fields=target['original_fields']
            target_name=target.get('display_name')
            if source=='mesh':target_name=next((v['value'] for v in fields['labels'] if v.get('xml:lang','en')=='en'),None)
            active=(fields.get('suppress')=='N') if source=='rxnorm' else mesh_active.get(target['id'],False) if source=='mesh' else True
            for org in origins[candidate['query_id']]:
                o=occ[org['dsld_occurrence_id']];k=(o['id'],source,native)
                if k in overrides:
                    conf,relation,rule,reason,previous=overrides[k];used.add(k)
                else:
                    conf,relation,rule,reason=decide(source,o['original_name'],target_name,active,candidate_counts[candidate['query_id']],o['attributes']);previous=None
                decisions.append(dict(id=key('mapping_decision',candidate['id'],o['id'],SPEC),candidate_id=candidate['id'],query_id=candidate['query_id'],origin_occurrence_id=o['id'],label_id=rec[snap[o['snapshot_id']]['record_id']]['native_id'],original_name=o['original_name'],origin_role=o['role'],target_source=source,target_record_id=target['id'],target_native_id=native,target_name=target_name,confidence=conf,proposed_relation=relation,assessed_relation=relation or ('exact_material_match' if conf=='Low' else 'unresolved'),rule=rule,reason=reason,action=action(conf),review_state='rule_assessed',human_reviewed=False,clinical_approval=False,graph_applied=False,prior_review=previous,evidence=dict(query_origin_id=org['id'],dsld_evidence_ids=o['evidence_ids'],candidate_provenance=candidate['provenance'],target_table=folder+'/records.jsonl',target_record_id=target['id'])))
        for q in queries.values():
            if not q['candidate_native_ids']:
                for org in origins[q['id']]:unmatched.append(dict(id=key('unresolved_lookup',q['id'],org['dsld_occurrence_id']),source=source,query_id=q['id'],origin_occurrence_id=org['dsld_occurrence_id'],original_query=q['original_query'],confidence=None,proposed_relation=None,status='no_candidate',action='retain_unresolved',provenance=q['provenance']))
        actual=sum(len(origins[c['query_id']]) for c in rows(folder,'candidates'))
        assert len([d for d in decisions if d['target_source']==source])==actual
        coverage.append(dict(source=source,queries=len(queries),query_candidates=len(rows(folder,'candidates')),occurrence_candidate_decisions=actual,no_candidate_occurrences=sum(r['source']==source for r in unmatched)))
    assert pilot_keys<=used
    assert len({d['id'] for d in decisions})==len(decisions)
    assert all(d['proposed_relation'] and d['action']=='eligible_for_graph_construction' for d in decisions if d['confidence']=='High')
    assert all(d['rule']=='M1' for d in decisions if d['proposed_relation']=='exact_material_match')
    # NatMed subject proposals: no form equivalence or clinical applicability is inferred.
    gm=manifest(GRAPH)
    graph_nodes={r['id']:json.loads(r['properties_json']) for f in (root/GRAPH/'nodes').glob('*.csv') for r in csv.DictReader(io.StringIO(f.read_text()))}
    graph_edges=list(csv.DictReader(io.StringIO((root/GRAPH/'relationships/relationships.csv').read_text())))
    subject_monographs={e['end_id']:graph_nodes[e['start_id']] for e in graph_edges if e['type']=='HAS_SUBJECT'}
    previous_subjects={}
    for edge in graph_edges:
        if edge['type'] in {'RELATED_BOTANICAL_SUBJECT','RELATED_INGREDIENT_SUBJECT'}:
            mono=subject_monographs[edge['end_id']]
            previous_subjects[(edge['start_id'],mono['source_record']['native_id'])]=(edge,mono)
    subjects=[]
    for m in rows(IMPORTED+'/natmedpro','records'):
        name=m['original_fields']['title'];n=search_key(name)
        for o in occ.values():
            if o['role']!='ingredient':continue
            exact=search_key(o['original_name'])==n;group=search_key(o['attributes'].get('ingredientGroup') or '')==n
            if not(exact or group):continue
            conf='High' if exact else 'Medium'
            relation='related_ingredient_subject' if exact else None
            reason='Same explicit general subject name; no exact formulation or product applicability.' if exact else 'Ingredient-group association alone does not establish the preparation/subject scope; review needed.'
            previous=previous_subjects.get((o['id'],m['id']))
            prior_subject=None
            if previous:
                edge,mono=previous
                assert mono['attributes']==m['original_fields']
                conf='High';relation=edge['type'].lower();reason=json.loads(edge['properties_json']).get('reason',reason)
                prior_subject=dict(graph=GRAPH,edge_id=edge['id'],evidence_ids=json.loads(edge['evidence_ids']))
            subjects.append(dict(id=key('natmed_subject_mapping',o['id'],m['id']),origin_occurrence_id=o['id'],original_name=o['original_name'],monograph_id=m['id'],monograph_title=name,confidence=conf,proposed_relation=relation,rule='M1' if previous else 'M6',reason=reason,prior_review=prior_subject,action=action(conf),clinical_approval=False,graph_applied=False,evidence=dict(dsld_evidence_ids=o['evidence_ids'],monograph_provenance=m['provenance'])))
    assert sum(s['prior_review'] is not None for s in subjects)==len(previous_subjects)==4
    # Keep topic context outside ingredient-identity decisions.
    source_topics=[]
    for source in ['natmedpro','reddit']:
        for t in rows(IMPORTED+'/'+source,'topic_associations'):
            source_topics.append(dict(id=t['id'],source=source,record_id=t['record_id'],topic=t['topic'],source_status=t['topic_status'],relation={'source_monograph_topic':'has_source_topic','literal_alias_in_record':'mentions_topic','inherited_thread_context':'inherited_thread_topic','topic_not_verified_in_own_text_record':'unresolved_topic_context'}[t['topic_status']],identity_mapping=False,clinical_inference=False,graph_applied=False,provenance=t['provenance']))
    report=dict(scope='Rule-based triage of all saved terminology candidate/occurrence combinations, not exhaustive clinical or human identity review',coverage=coverage,terminology_confidence=dict(Counter(d['confidence'] for d in decisions)),terminology_relations=dict(Counter(d['proposed_relation'] or 'unresolved' for d in decisions)),rule_counts=dict(Counter(d['rule'] for d in decisions)),prior_pilot_decisions_preserved=len(pilot_keys),prior_scope_decisions_carried=sum(k in used and k not in pilot_keys for k in overrides),additional_reviewed_proposals=len(extra),no_candidate_occurrences=len(unmatched),prior_natmed_subject_links_preserved=len(previous_subjects),natmed_subject_proposals=dict(Counter(d['confidence'] for d in subjects)),source_topic_links=len(source_topics),checks=dict(all_candidate_occurrence_pairs_assessed=True,all_40_pilot_reviews_preserved=True,no_automatic_new_exact_material_matches=True,no_candidate_distinct_from_low=True,source_topics_separate_from_identity=True),graph_updated=False,canonical_merges=0,clinical_approvals=0,limitations=['High concept links rely on exact preferred name plus scope/status gates, not proof of exact material identity','Unreviewed synonyms, PubChem specificity and qualified botanical preparations remain Medium','No-match records are unresolved, not Low; no network enrichment performed','NatMed matching only proposes general subject relationships; unmatched names remain source-scoped','Earlier review proposals retain their pending human/clinical approval history; eligibility is rule-based'])
    report['natmed_monograph_coverage']=[dict(monograph_id=m['id'],title=m['original_fields']['title'],counts=dict(Counter(r['confidence'] for r in subjects if r['monograph_id']==m['id']))) for m in rows(IMPORTED+'/natmedpro','records')]
    # Explicit NatMed no-target inventory covers each monograph and each ingredient occurrence.
    eligible_origins={o['id'] for o in occ.values() if o['role']=='ingredient'};proposed_origins={r['origin_occurrence_id'] for r in subjects}
    natmed_unmatched=[dict(origin_occurrence_id=i,status='no_saved_subject_name_or_group_bridge',confidence=None) for i in sorted(eligible_origins-proposed_origins)]
    report['natmed_no_subject_bridge_occurrences']=len(natmed_unmatched)
    return dict(terminology_decisions=decisions,no_candidate_queries=unmatched,natmed_subject_decisions=subjects,natmed_no_subject_bridge=natmed_unmatched,additional_reviewed_proposals=extra,source_topic_context=source_topics),report,inputs

def run(root=ROOT):
    root=Path(root);tables,report,inputs=build(root)
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in ['scripts/decide_ingredient_mappings.py','scripts/preprocess_pilot.py','tests/test_decide_ingredient_mappings.py']},python=sys.version.split()[0])
    build_id='ingredient-decisions-v1-'+sha(encode(signature).encode())[:20];files={name+'.jsonl':(''.join(encode(r)+'\n' for r in sorted(rows,key=lambda r:r.get('id',r.get('origin_occurrence_id',''))))).encode() for name,rows in tables.items()}
    files['validation_report.json']=(encode(report)+'\n').encode();files['input_manifest.json']=(encode(signature)+'\n').encode()
    files['manifest.json']=(encode(dict(build_id=build_id,spec=SPEC,files={p:sha(b) for p,b in files.items()}))+'\n').encode();out=root/'data/processed/identity'/build_id
    if out.exists():
        assert {p.name for p in out.iterdir()}==set(files)
        for name,b in files.items():assert (out/name).read_bytes()==b
    else:
        out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.mapping-decisions-',dir=out.parent))
        try:
            for name,b in files.items():(tmp/name).write_bytes(b)
            os.rename(tmp,out)
        except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
    for path,h in inputs.items():assert sha((root/path).read_bytes())==h
    print(out.relative_to(root));print(encode(report));return out,report
if __name__=='__main__':run()
