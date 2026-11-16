"""Apply scoped general-concept decisions to a new immutable graph revision."""
import csv, io, json
from collections import Counter, defaultdict
from pathlib import Path
from kg_evaluation_common import ROOT, GRAPH, sha
from preprocess_pilot import encode, key
from decide_ingredient_mappings import DSLD, TERMS
from expand_contextual_mapping_candidates import context, supported_query, qualifiers, assess, PARTS, PREPS
from expand_topic_navigation import write_immutable
from export_full_graph import validate

CONTEXT='data/processed/identity/contextual-candidates-v1-04577ddde5348c406ee2'
SPEC='schemas/general_concept_mapping_v1.json'

def eligible(o, target, source, queries, confidence):
    if confidence=='Low':return False,'prior_exclusion_preserved'
    if source!='rxnorm':return False,'requires_other_source_or_relation_rule'
    ctx=context(o)
    if not ctx['discovery_allowed']:return False,'negated_or_combined_context'
    if not (set(ctx['scope']) & PARTS and set(ctx['scope']) & PREPS):return False,'explicit_part_and_preparation_required'
    if target['original_fields'].get('tty')!='IN':return False,'target_not_ingredient_concept'
    rank,_,reasons=assess(ctx,target,source,None)
    if rank!=1:return False,','.join(reasons)
    for q in queries:
        if (q['match_method']=='exact' and str(target['native_id']) in q['candidate_native_ids']
            and supported_query(o,ctx,q['original_query'])
            and qualifiers(q['original_query'])==qualifiers(target['display_name'])):
            return True,'saved_exact_identity_bridge_and_explicit_scope_agree'
    return False,'no_saved_exact_scope_supported_identity_bridge'

def run(root=ROOT):
    root=Path(root);inputs={}
    def read(p):
        b=(root/p).read_bytes();inputs[p]=sha(b);return b
    def rows(p):return [json.loads(l) for l in read(p).splitlines()]
    for folder in [GRAPH,CONTEXT,DSLD,TERMS]:
        m=json.loads(read(folder+'/manifest.json'))
        for p,h in m['files'].items():assert sha(read(folder+'/'+p))==(h if isinstance(h,str) else h['sha256'])
    read(SPEC)
    occurrences={r['id']:r for r in rows(DSLD+'/occurrences.jsonl')}
    targets={r['id']:r for r in rows(TERMS+'/rxnorm/records.jsonl')}
    queries={r['id']:r for r in rows(TERMS+'/rxnorm/queries.jsonl')}
    pending=rows(GRAPH+'/review/mapping_pending_excluded.jsonl')
    added=rows(CONTEXT+'/new_candidates.jsonl')
    csv.field_size_limit(10_000_000)
    def csvrows(path):return list(csv.DictReader(io.StringIO(read(path).decode())))
    gm=json.loads(read(GRAPH+'/manifest.json'))
    nodes=[r for name in gm['files'] if name.startswith('nodes/') for r in csvrows(GRAPH+'/'+name)]
    ni={n['id']:n for n in nodes};edges=csvrows(GRAPH+'/relationships/relationships.csv')
    existing=defaultdict(set)
    for e in edges:
        if e['mapping_id']:existing[e['start_id']].add(e['end_id'])
    ledger=[]
    for kind,items in [('original',pending),('contextual',added)]:
        for r in items:
            source=r.get('target_source','natmedpro');oid=r['origin_occurrence_id'];tid=r.get('target_record_id')
            qs=[]
            if source=='rxnorm':
                ids=[r['query_id']] if kind=='original' else [d['query_id'] for d in r['discovery']]
                qs=[queries[qid] for qid in ids]
                ok,reason=eligible(occurrences[oid],targets[tid],source,qs,r['confidence'])
            else:ok,reason=False,('prior_exclusion_preserved' if r['confidence']=='Low' else 'requires_other_source_or_relation_rule')
            ledger.append(dict(id=key('general_concept_review',r['id'],SPEC),prior_id=r['id'],pool=kind,
                origin_occurrence_id=oid,target_record_id=tid,target_source=source,
                original_name=occurrences[oid]['original_name'],target_name=r.get('target_name'),
                eligible=ok,reason=reason,prior_confidence=r['confidence'],
                supporting_query_ids=[q['id'] for q in qs],source_attributes=occurrences[oid]['attributes'],
                dsld_evidence_ids=occurrences[oid]['evidence_ids']))
    groups=defaultdict(list)
    for d in ledger:
        if d['eligible']:groups[(d['origin_occurrence_id'],d['target_source'])].append(d)
    for (oid,_),group in groups.items():
        tids={d['target_record_id'] for d in group}
        rx_existing={tid for tid in existing[oid] if json.loads(ni[tid]['properties_json']).get('source')=='rxnorm'}
        if len(tids|rx_existing)>1:
            for d in group:d.update(eligible=False,reason='multiple_supported_or_previously_accepted_targets')
    accepted=[d for d in ledger if d['eligible']]
    for d in ledger:
        d.update(confidence='High' if d['eligible'] else d['prior_confidence'],
                 proposed_relation='denotes_concept' if d['eligible'] else None,
                 human_reviewed=False,clinical_approval=False,rule='GCONCEPT1')
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in
        ['scripts/apply_general_concept_mappings.py','scripts/expand_contextual_mapping_candidates.py','tests/test_general_concept_mappings.py']})
    report=dict(original_rows_assessed=len(pending),contextual_rows_assessed=len(added),
        original_promoted=sum(d['pool']=='original' for d in accepted),contextual_promoted=sum(d['pool']=='contextual' for d in accepted),
        accepted_candidate_rows=len(accepted),accepted_unique_pairs=len({(d['origin_occurrence_id'],d['target_record_id']) for d in accepted}),
        remaining_original_pending=sum(d['pool']=='original' and not d['eligible'] and d['prior_confidence']=='Medium' for d in ledger),
        original_exclusions_preserved=sum(d['pool']=='original' and d['prior_confidence']=='Low' for d in ledger),
        accepted_by_name=dict(Counter(d['original_name'] for d in accepted)),
        unresolved_by_reason=dict(Counter(d['reason'] for d in ledger if not d['eligible'])),clinical_approvals=0)
    files={'decisions.jsonl':(''.join(encode(d)+'\n' for d in ledger)).encode(),
           'report.json':(encode(report)+'\n').encode(),'input_manifest.json':(encode(signature)+'\n').encode()}
    files['manifest.json']=(encode(dict(files={p:sha(b) for p,b in files.items()},spec=SPEC))+'\n').encode()
    out=root/'data/processed/identity'/('general-concept-decisions-v1-'+sha(files['manifest.json'])[:20]);write_immutable(out,files)
    decision_path=str(out.relative_to(root))+'/decisions.jsonl';decision_hash=sha(files['decisions.jsonl'])
    evidence=rows(GRAPH+'/provenance/evidence.jsonl');newedges=[];seen=set();expected={}
    for e in edges:
        if e['mapping_id']:expected[e['mapping_id']]=dict(start=e['start_id'],end=e['end_id'],relation=e['type'])
    for index,d in enumerate(ledger):
        pair=(d['origin_occurrence_id'],d['target_record_id'])
        if not d['eligible'] or pair in seen or pair[1] in existing[pair[0]]:continue
        seen.add(pair);eid=key('graph_evidence',decision_path,str(index))
        evidence.append(dict(id=eid,locator_kind='json_pointer',locator=dict(file=decision_path,sha256=decision_hash,pointer='/'+str(index)),original_value=d,support_role='general_concept_mapping_decision'))
        ev=sorted(set([eid]+json.loads(ni[pair[0]]['evidence_ids'])+json.loads(ni[pair[1]]['evidence_ids'])))
        edge=dict(id=key('full_edge',*pair,'DENOTES_CONCEPT',d['id']),start_id=pair[0],end_id=pair[1],
            type='DENOTES_CONCEPT',mapping_id=d['id'],confidence='High',evidence_ids=encode(ev),
            properties_json=encode(dict(decision=d,graph_applied=True,clinical_approval=False,
                scope='General ingredient concept only; standardization, branded preparation and quantities remain on the source occurrence. No exact material or clinical equivalence.')))
        newedges.append(edge);expected[d['id']]=dict(start=pair[0],end=pair[1],relation='DENOTES_CONCEPT')
    def convert(r):return {**{k:v for k,v in r.items() if k not in ['properties_json','evidence_ids']},'properties':json.loads(r['properties_json']),'evidence_ids':json.loads(r['evidence_ids'])}
    checks=validate([convert(n) for n in nodes],[convert(e) for e in edges+newedges],{r['id']:r for r in evidence},expected)
    assert len({r['id'] for r in evidence})==len(evidence)
    checks.update(existing_nodes_and_edges_preserved=True,new_mapping_edges=len(newedges),all_original_review_rows_assessed=True)
    changed={'relationships/relationships.csv','provenance/evidence.jsonl','review/mapping_pending_excluded.jsonl','input_manifest.json','validation_report.json'}
    gf={p:(root/GRAPH/p).read_bytes() for p in gm['files'] if p not in changed}
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(edges[0]));w.writeheader();w.writerows(sorted(edges+newedges,key=lambda e:e['id']))
    gf['relationships/relationships.csv']=stream.getvalue().encode()
    gf['provenance/evidence.jsonl']=(''.join(encode(e)+'\n' for e in sorted(evidence,key=lambda e:e['id']))).encode()
    promoted={d['prior_id'] for d in accepted if d['pool']=='original'}
    gf['review/mapping_pending_excluded.jsonl']=(''.join(encode(r)+'\n' for r in pending if r['id'] not in promoted)).encode()
    gf['review/general_concept_decisions.jsonl']=files['decisions.jsonl']
    gf['review/contextual_candidates.jsonl']=(root/CONTEXT/'new_candidates.jsonl').read_bytes()
    # Discovery rows are historical; current dispositions live in general_concept_decisions.jsonl.
    gf['validation_report.json']=(encode(dict(status='passed_with_documented_limitations',base_graph=GRAPH,checks=checks,decisions=str(out.relative_to(root)),report=report,clinical_approval=False))+'\n').encode()
    gf['input_manifest.json']=(encode(dict(inputs={**inputs,decision_path:decision_hash},code=signature['code']))+'\n').encode()
    counts={**gm['counts'],'edges':len(edges)+len(newedges),'mapping_edges':gm['counts']['mapping_edges']+len(newedges),
        'terminology_mapping_edges':gm['counts']['terminology_mapping_edges']+len(newedges),
        'pending_or_excluded_mappings':len(pending)-len(promoted)}
    meta=dict(version='full-graph-concepts-v1',base_graph=GRAPH,counts=counts,node_types=gm['node_types'],
        edge_types=dict(Counter(e['type'] for e in edges+newedges)),validation=checks,files={p:sha(b) for p,b in gf.items()})
    gf['manifest.json']=(encode(meta)+'\n').encode();graph=root/'data/graph'/('full-graph-concepts-v1-'+sha(gf['manifest.json'])[:20]);write_immutable(graph,gf)
    freeze=dict(graph=str(graph.relative_to(root)),graph_manifest_sha256=sha(gf['manifest.json']),graph_files=meta['files'],clinical_approval=False,status='passed_with_documented_limitations')
    fb=(encode(freeze)+'\n').encode();release=root/'data/graph'/('poc-concepts-release-v1-'+sha(fb)[:20]);write_immutable(release,{'freeze_manifest.json':fb,'validation_report.json':gf['validation_report.json']})
    for p,h in inputs.items():assert sha((root/p).read_bytes())==h
    print(json.dumps(dict(decisions=str(out.relative_to(root)),graph=str(graph.relative_to(root)),release=str(release.relative_to(root)),report=report,checks=checks),indent=2))
    return out,graph,release,report

if __name__=='__main__':run()
