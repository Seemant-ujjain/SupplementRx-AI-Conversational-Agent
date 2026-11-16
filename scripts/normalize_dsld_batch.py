"""Step 2: expand existing DSLD selected-field normalization to all 400 labels."""
from pathlib import Path
from collections import Counter
import sys,os,tempfile,shutil
from preprocess_pilot import Pilot,load,encode,sha,pointer,key,validate_tables

ROOT=Path(__file__).resolve().parents[1]
SPEC='schemas/dsld_normalization_batch_v1.json'
BASELINE='data/processed/dsld/dsld-baseline-audit-v1-1487bf52f8e90a1f/manifest.json'

def comparison_status(transform, quantity_reasons, serving_resolved):
    reasons=set(transform['reason_codes'])
    reasons.update(r for r in quantity_reasons if r!='inequality_amount')
    if not serving_resolved:reasons.add('unresolved_serving_order')
    if transform['normalized_value'] is None:return 'blocked',sorted(reasons)
    return ('pending_review' if reasons else 'eligible_for_scoped_comparison'),sorted(reasons)

def build(root=ROOT):
    root=Path(root);p=Pilot(root)
    spec=p.document(SPEC);baseline=p.document(BASELINE)
    label_ids=sorted(map(int,baseline['sources']));assert len(label_ids)==400
    # Selection override only: reuse the tested DSLD extractor without changing the pilot contract on disk.
    p.contract['pilot']['dsld_label_ids']=label_ids
    p.dsld()
    # Reference resolution is now against the entire selected DSLD collection.
    for r in p.tables['source_references'].values():
        if r['target_key']:r['target_key']['availability_scope']='selected_dsld_collection'
        r['reason_codes']=['target_outside_selected_dsld_collection' if x=='target_outside_selected_pilot' else x for x in r['reason_codes']]
    for r in p.tables['review_queue'].values():
        r['reason_codes']=['target_outside_selected_dsld_collection' if x=='target_outside_selected_pilot' else x for x in r['reason_codes']]
    # Preserve every audit finding, not only the quantity-level findings the pilot emitted.
    audit_findings=[]; finding_evidence={}
    for f in p.quantity_findings:
        sid=p.label_sids[int(f['label_id'])]
        eid=p.evidence(sid,f['pointer'],'quantity_audit_finding',f['value'])
        finding_evidence.setdefault((sid,f['code']),set()).add(eid)
        audit_findings.append(dict(f,evidence_id=eid,snapshot_id=sid))
    for (sid,code),eids in sorted(finding_evidence.items()):
        p.queue('snapshots',sid,'batch_source_audit',[code],sorted(eids))
    reviews=[]
    for t in p.tables['transformations'].values():
        if t['destination_field']!='mass_comparison':continue
        a=p.tables['assertions'][t['owner_id']]
        reasons=[code for r in p.tables['review_queue'].values() if r['owner_table']=='assertions' and r['owner_id']==a['id'] and r['stage']=='source_audit' for code in r['reason_codes']]
        status,codes=comparison_status(t,reasons,a['serving_id'] is not None)
        reviews.append(dict(id=key('quantity_comparison_review',t['id'],'dsld-normalization-batch-v1'),transformation_id=t['id'],assertion_id=a['id'],status=status,reason_codes=codes,evidence_ids=t['evidence_ids'],policy='Matching source basis/operator and compatible ingredient scope are still required; not a merge or dose decision'))
    validate_tables(p.tables,p.contract)
    expected_occurrences=set();expected_quantities=set();expected_servings=0
    def walk(rows,path,sid,role='ingredient'):
        for i,r in enumerate(rows):
            loc=f'{path}/{i}';expected_occurrences.add((sid,loc,role))
            for j,q in enumerate(r.get('quantity') or []):expected_quantities.add((sid,f'{loc}/quantity/{j}'))
            for j,f in enumerate(r.get('forms') or []):expected_occurrences.add((sid,f'{loc}/forms/{j}','form' if role=='ingredient' else 'other_form'))
            walk(r.get('nestedRows') or [],loc+'/nestedRows',sid,role)
    for lid,sid in p.label_sids.items():
        source=p.data[baseline['sources'][str(lid)]['file']]
        expected_servings+=len(source['servingSizes'])
        walk(source['ingredientRows'],'/ingredientRows',sid)
        walk((source.get('otheringredients') or {}).get('ingredients') or [],'/otheringredients/ingredients',sid,'other_ingredient')
    actual_occ={(o['snapshot_id'],p.tables['evidence'][o['evidence_ids'][0]]['locator']['pointer'],o['role']) for o in p.tables['occurrences'].values()}
    assert actual_occ==expected_occurrences and len(actual_occ)==len(p.tables['occurrences'])
    compositions=[a for a in p.tables['assertions'].values() if a['kind']=='composition']
    actual_q={(a['snapshot_id'],next(p.tables['evidence'][i]['locator']['pointer'] for i in a['evidence_ids'] if p.tables['evidence'][i]['support_role']=='quantity')) for a in compositions}
    assert actual_q==expected_quantities and len(actual_q)==len(compositions)==len(reviews)
    assert len(p.tables['servings'])==expected_servings
    for e in p.tables['evidence'].values():
        file=p.tables['artifacts'][e['artifact_id']]['relative_path']
        assert pointer(p.data[file],e['locator']['pointer'])==e['original_value']
    mass=[t for t in p.tables['transformations'].values() if t['destination_field']=='mass_comparison']
    assert sum(t['original_value']['unit']=='NP' for t in mass)==705
    assert all(t['normalized_value'] is None for t in mass if t['original_value']['unit']=='NP')
    bpi={}
    for t in mass:
        a=p.tables['assertions'][t['owner_id']]
        lid=int(p.tables['source_records'][p.tables['snapshots'][a['snapshot_id']]['record_id']]['native_id'])
        if lid==257287:assert t['normalized_value'] is None and t['value_state']=='conflicting'
        if lid in [25731,43261] and a['original_fields']['ingredient_name']=='Creatine':bpi[lid]=t['normalized_value']
    assert bpi[25731]==bpi[43261] and bpi[25731]['amount']=='1500'
    assert all(not p.tables[name] for name in ['mapping_assertions','canonical_identities','comparison_groups','review_events'])
    assert all(sha((root/path).read_bytes())==h for path,h in p.protected.items())
    report=dict(scope='DSLD selected fields across all 400 labels; other five sources not expanded',labels=400,occurrences=len(actual_occ),quantity_entries=len(compositions),servings=expected_servings,evidence_pointers_checked=len(p.tables['evidence']),mass_outcomes=dict(Counter(t['outcome'] for t in mass)),mass_block_reasons=dict(Counter(code for t in mass if t['outcome']=='blocked' for code in t['reason_codes'])),comparison_statuses=dict(Counter(r['status'] for r in reviews)),audit_findings=len(audit_findings),audit_findings_by_code=dict(Counter(f['code'] for f in audit_findings)),reference_availability=dict(Counter(r['target_availability'] for r in p.tables['source_references'].values())),review_rows_by_stage=dict(Counter(r['stage'] for r in p.tables['review_queue'].values())),checks=dict(table_schema_and_foreign_keys=True,recursive_source_coverage=True,original_quantity_values_retained=True,evidence_verified=True,bpi_equivalent_mass_separate_labels=True,betteryou_conflict_blocked=True,np_not_zero=True,raw_and_prior_artifacts_unchanged=True),accepted_mappings=0,semantic_merges=0,clinical_approvals=0,graph_updated=False,limitations=['Plain-mass comparison only; no IU/CFU/activity/volume conversions','Eligible comparisons still require compatible ingredient scope, operator and source basis','All original dates and market flags retained; no present-day availability inference','Snapshot audit queues can aggregate a reason per label; audit_findings retains every individual finding','Full schema and mapping stages remain separate; this batch reuses base table shapes'])
    return p,reviews,audit_findings,report

def run(root=ROOT):
    root=Path(root);p,reviews,findings,report=build(root)
    code_files=['scripts/normalize_dsld_batch.py','scripts/preprocess_pilot.py','tests/test_normalize_dsld_batch.py']
    signature=dict(spec_sha256=sha((root/SPEC).read_bytes()),inputs=p.inputs,selection=p.selected,label_ids=p.contract['pilot']['dsld_label_ids'],code_hashes={f:sha((root/f).read_bytes()) for f in code_files},python=sys.version.split()[0])
    build_id='dsld-normalized-v1-'+sha(encode(signature).encode())[:20]
    payloads={s['file']:(''.join(encode(p.tables[t][i])+'\n' for i in sorted(p.tables[t]))).encode() for t,s in p.contract['tables'].items()}
    payloads['quantity_comparison_review.jsonl']=(''.join(encode(r)+'\n' for r in sorted(reviews,key=lambda x:x['id']))).encode()
    payloads['audit_findings.jsonl']=(''.join(encode(r)+'\n' for r in findings)).encode()
    payloads['validation_report.json']=(encode(report)+'\n').encode();payloads['input_manifest.json']=(encode(signature)+'\n').encode()
    manifest=dict(build_id=build_id,base_contract='schemas/poc_preprocessing_contract_v0.1.json',batch_spec=SPEC,scope=report['scope'],tables={t:dict(file=s['file'],rows=len(p.tables[t]),sha256=sha(payloads[s['file']])) for t,s in p.contract['tables'].items()},files={name:sha(b) for name,b in payloads.items()},normalization_profile='Pilot allowlist plus batch comparison eligibility; no identity decisions')
    payloads['manifest.json']=(encode(manifest)+'\n').encode();out=root/'data/processed/dsld'/build_id
    if out.exists():
        assert {x.name for x in out.iterdir()}==set(payloads)
        for name,b in payloads.items():assert (out/name).read_bytes()==b,'Existing output differs: '+name
    else:
        out.parent.mkdir(parents=True,exist_ok=True);temp=Path(tempfile.mkdtemp(prefix='.dsld-normalized-',dir=out.parent))
        try:
            for name,b in payloads.items():(temp/name).write_bytes(b)
            os.rename(temp,out)
        except BaseException:shutil.rmtree(temp,ignore_errors=True);raise
    assert all(sha((root/path).read_bytes())==h for path,h in p.protected.items())
    print(out.relative_to(root));print(encode(report));return out,report
if __name__=='__main__':run()
