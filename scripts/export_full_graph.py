"""Build an immutable collection-wide attributed graph, without canonical merges."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, io, json, os, shutil, sys, tempfile
from preprocess_pilot import sha, encode, key
from decide_ingredient_mappings import DSLD, TERMS, IMPORTED, PILOT
ROOT=Path(__file__).resolve().parents[1]
MAPS='data/processed/identity/ingredient-decisions-v1-1e02682e87ad7456218b'
IDENTITY='data/processed/identity/identity-duplicates-v1-3aa86ab20b94fd928b6b'
SPEC='schemas/full_graph_export_v1.json'

def parent_relation(role):
    if role=='standardization_marker_class':return 'HAS_STANDARDIZATION_MARKER'
    return 'HAS_DECLARED_FORM' if role in {'form','other_form'} else 'HAS_DECLARED_COMPONENT'

def validate(nodes,edges,evidence,expected_mappings):
    ids={n['id'] for n in nodes};evidence_ids=set(evidence);assert len(ids)==len(nodes),'Duplicate nodes'
    assert len({e['id'] for e in edges})==len(edges),'Duplicate edges'
    assert all(e['start_id'] in ids and e['end_id'] in ids for e in edges),'Dangling endpoint'
    assert all(n['evidence_ids'] and set(n['evidence_ids'])<=evidence_ids for n in nodes),'Missing node evidence'
    assert all(e['evidence_ids'] and set(e['evidence_ids'])<=evidence_ids for e in edges),'Missing edge evidence'
    mapped=[e for e in edges if e['mapping_id']]
    assert Counter(e['mapping_id'] for e in mapped)==Counter(expected_mappings.keys()),'Incorrect mapping eligibility'
    for e in mapped:
        d=expected_mappings[e['mapping_id']]
        assert e['confidence']=='High' and e['type']==d['relation'],'Mapping promotion'
        assert (e['start_id'],e['end_id'])==(d['start'],d['end']),'Wrong mapping endpoints'
    for n in nodes:
        if n['type']=='ClinicalClaim':
            assert n['properties']['review_state']=='pending' and n['properties']['clinical_approval'] is False
            assert n['properties']['retrieval_policy']=='attributed_pending_source_excerpt_only'
    types={n['id']:n['type'] for n in nodes}
    assert not any(types[e['start_id']]=='ProductLabel' and types[e['end_id']]=='ClinicalClaim' for e in edges),'Product clinical applicability inferred'
    assert not any(e['type'] in {'SAME_AS','TREATS','SAFE_FOR','RECOMMENDED_DOSE'} for e in edges)
    return dict(unique_ids=True,endpoints_resolve=True,evidence_resolves=True,high_mapping_eligibility_exact=True,
                mapping_relations_preserved=True,pending_clinical_status_preserved=True,no_product_clinical_inference=True)

def build(root=ROOT):
    root=Path(root);inputs={};cache={};locators={};evidence={};nodes={};edges={};expected={};review={};sidecars={}
    def read(p,expected_hash=None):
        if p not in cache:cache[p]=(root/p).read_bytes()
        b=cache[p];h=sha(b)
        if expected_hash is not None:assert h==expected_hash,p
        inputs[p]=h;return b
    def obj(p):return json.loads(read(p))
    def checked_manifest(folder):
        m=obj(folder+'/manifest.json')
        for p,h in m['files'].items():read(folder+'/'+p,h if isinstance(h,str) else h['sha256'])
        for p,h in obj(folder+'/input_manifest.json')['inputs'].items():read(p,h if isinstance(h,str) else h['sha256'])
    for folder in [DSLD,TERMS,IMPORTED,MAPS,IDENTITY]:checked_manifest(folder)
    obj(SPEC)
    def rows(folder,table):
        p=folder+'/'+table+'.jsonl';result=[json.loads(l) for l in read(p).splitlines()]
        for i,r in enumerate(result):
            if 'id' in r:locators[(p,r['id'])]=dict(file=p,sha256=inputs[p],pointer=f'/{i}')
        return result
    def ev(folder,table,row):
        p=folder+'/'+table+'.jsonl';loc=locators[(p,row['id'])];eid=key('graph_evidence',p,loc['sha256'],loc['pointer'])
        evidence[eid]=dict(id=eid,locator=loc,support_role='prepared_source_or_decision_row',source_provenance=row.get('provenance'),scope='Technical traceability, not clinical validation')
        return [eid]
    def node(i,t,p,eids):
        r=dict(id=i,type=t,properties=p,evidence_ids=sorted(set(eids)))
        if i in nodes:assert nodes[i]==r,('Conflicting node',i)
        else:nodes[i]=r
    def edge(a,b,t,eids,p=None,mid='',confidence='',token=''):
        i=key('full_edge',a,b,t,mid,token);r=dict(id=i,start_id=a,end_id=b,type=t,mapping_id=mid,confidence=confidence,evidence_ids=sorted(set(eids)),properties=p or {})
        if i in edges:assert edges[i]==r,('Conflicting edge',i)
        else:edges[i]=r
    def mapping(d,target,folder,table):
        assert d['confidence']=='High' and d['proposed_relation']
        mid=d['id'];expected[mid]=dict(start=d['origin_occurrence_id'],end=target,relation=d['proposed_relation'].upper())
        edge(d['origin_occurrence_id'],target,d['proposed_relation'].upper(),ev(folder,table,d),dict(decision=d,graph_applied=True,clinical_approval=False,scope='Relation-specific only; no whole-product applicability'),mid,'High')
    def external(source,native,eids):
        i=key('external_reference',source,native)
        if i not in nodes:node(i,'ExternalRecordReference',dict(source=source,native_id=native,content_loaded=False),eids)
        else:nodes[i]['evidence_ids']=sorted(set(nodes[i]['evidence_ids']+eids))
        return i
    # DSLD: all source labels, occurrences, servings and source assertions, including conflicts.
    dt={t:rows(DSLD,t) for t in ['source_records','snapshots','occurrences','servings','assertions','evidence','artifacts','transformations','quantity_comparison_review','review_queue','source_references']}
    records={r['id']:r for r in dt['source_records']};snapshots={r['id']:r for r in dt['snapshots']}
    evidence.update({r['id']:r for r in dt['evidence']})
    for a in dt['artifacts']:read(a['relative_path'],a['sha256'])
    transformations=defaultdict(list);issues=defaultdict(list);quantity={r['assertion_id']:r for r in dt['quantity_comparison_review']}
    for r in dt['transformations']:transformations[r['owner_id']].append(r)
    for r in dt['review_queue']:issues[r['owner_id']].append(r)
    def enriched(r):return dict(r,transformations=transformations[r['id']],review_issues=issues[r['id']])
    for s in dt['snapshots']:
        assert records[s['record_id']]['source_system']=='dsld'
        node(s['id'],'ProductLabel',dict(enriched(s),source_record=records[s['record_id']],identity_scope='source_label_snapshot_not_canonical_product'),ev(DSLD,'snapshots',s))
    roles={r['origin_occurrence_id']:r['interpreted_role'] for r in obj(PILOT)['reviews']}
    for r in dt['occurrences']:
        eids=r['evidence_ids'];role=roles.get(r['id'],r['role'])
        node(r['id'],'IngredientOccurrence',dict(enriched(r),interpreted_role=role),eids)
        edge(r['snapshot_id'],r['id'],'DECLARES_OCCURRENCE',eids)
        if r['parent_id']:edge(r['parent_id'],r['id'],parent_relation(role),eids)
    for r in dt['servings']:
        node(r['id'],'Serving',enriched(r),r['evidence_ids']);edge(r['snapshot_id'],r['id'],'DECLARES_SERVING',r['evidence_ids'])
    for r in dt['assertions']:
        node(r['id'],'LabelAssertion',dict(enriched(r),quantity_comparison=quantity.get(r['id']),quantity_policy='Normalized values are comparisons only; preserve source basis, operators and blocked status; no recommended dose'),r['evidence_ids'])
        edge(r['snapshot_id'],r['id'],'HAS_ASSERTION',r['evidence_ids'])
        if r['occurrence_id']:edge(r['id'],r['occurrence_id'],'ABOUT_OCCURRENCE',r['evidence_ids'])
        if r['serving_id']:edge(r['id'],r['serving_id'],'HAS_SERVING_BASIS',r['evidence_ids'])
    for r in dt['source_references']:
        target=r['target_snapshot_id']
        if target is None and r['target_key']:target=external('dsld',r['target_key']['native_id'],r['evidence_ids'])
        if target:edge(r['source_snapshot_id'],target,'SOURCE_LABEL_RELATION' if r['target_snapshot_id'] else 'SOURCE_LABEL_REFERENCE',r['evidence_ids'],dict(r,identity_equivalence=False),token=r['id'])
    review['dsld_issues']=dt['review_queue'];review['dsld_quantity']=dt['quantity_comparison_review']
    # Terminology source-native identities. Unlinked records are retained as vocabulary records.
    term_lookup={};mesh_statements=rows(TERMS+'/mesh','rdf_statements');literals=defaultdict(list)
    for s in mesh_statements:
        if s['typed_object']['type']!='uri':literals[s['subject_id']].append(s)
    for source in ['pubchem','rxnorm','mesh']:
        folder=TERMS+'/'+source;table='subjects' if source=='mesh' else 'records'
        properties=defaultdict(list)
        if source!='mesh':
            for p in rows(folder,'properties'):properties[p['record_id']].append(p)
        for r in rows(folder,table):
            term_lookup[(source,r['native_id'])]=r['id']
            node(r['id'],'ChemicalCompound' if source=='pubchem' else 'TerminologyConcept',dict(r,source_properties=properties[r['id']],rdf_literals=literals[r['id']],identity_scope='source_namespace_and_native_id',mapping_approval=False),ev(folder,table,r))
        review[source+'_preparation']=rows(folder,'review_queue')
    for s in mesh_statements:
        if s['typed_object']['type']!='uri':continue
        eids=ev(TERMS+'/mesh','rdf_statements',s)
        target=s['target_subject_id'] or external('mesh_uri',s['typed_object']['value'],eids)
        edge(s['subject_id'],target,'MESH_RELATION',eids,s,token=s['id'])
    # NatMed and Reddit source records and passages. No health outcomes extracted from Reddit.
    imported={}
    for source in ['natmedpro','reddit']:
        folder=IMPORTED+'/'+source;imported[source]={t:rows(folder,t) for t in ['records','passages','topic_associations','review_queue']}
        for r in imported[source]['records']:
            typ='Monograph' if source=='natmedpro' else {'post':'RedditPost','comment':'RedditComment'}[r['original_fields']['record_type']]
            node(r['id'],typ,dict(r,retrieval_policy='attributed_source_only',clinical_approval=False),ev(folder,'records',r))
            if source=='natmedpro':
                sid=key('monograph_subject',r['id']);node(sid,'MonographSubject',dict(monograph_id=r['id'],name=r['display_title'],scope='General subject, not exact formulation'),ev(folder,'records',r));edge(r['id'],sid,'HAS_SUBJECT',ev(folder,'records',r))
        for r in imported[source]['passages']:
            assert r['source_binding_valid']
            node(r['id'],'SourcePassage',dict(r,source=source,evidence_role='clinical_reference' if source=='natmedpro' else 'user_report',clinical_approval=False),ev(folder,'passages',r))
            edge(r['id'],r['record_id'],'PASSAGE_OF',ev(folder,'passages',r))
        review[source+'_preparation']=imported[source]['review_queue']
    claims=rows(IMPORTED+'/natmedpro','claims');supports=defaultdict(list)
    for r in rows(IMPORTED+'/natmedpro','field_support'):supports[r['claim_id']].append(r)
    for c in claims:
        assert c['review_state']=='pending' and not c['clinical_approval'] and c['technical_validation']=='schema_and_source_support_passed'
        eids=ev(IMPORTED+'/natmedpro','claims',c);f=c['original_fields'];span=c['source_span']
        node(c['id'],'ClinicalClaim',dict(c,field_support_anchors=supports[c['id']],retrieval_policy='attributed_pending_source_excerpt_only'),eids)
        xid=key('source_excerpt',span['file'],span['sha256'],span['pointer'],str(span['start']),str(span['end']))
        if xid not in nodes:node(xid,'SourceExcerpt',dict(text=f['source']['excerpt'],source_span=span,review_state='pending',clinical_approval=False),eids)
        else:
            assert nodes[xid]['properties']['text']==f['source']['excerpt'];nodes[xid]['evidence_ids']=sorted(set(nodes[xid]['evidence_ids']+eids))
        edge(c['record_id'],c['id'],'HAS_PENDING_CLAIM',eids)
        edge(c['id'],key('monograph_subject',c['record_id']),'ABOUT_SUBJECT',eids)
        edge(c['id'],xid,'SUPPORTED_BY_EXCERPT',eids,dict(support='Textual alignment only'))
        # Same source span may support different structured claims; keep bindings distinct.
        edge(xid,c['record_id'],'EXCERPT_OF',eids,token=c['id'])
    for r in rows(IMPORTED+'/natmedpro','reference_documents'):
        eids=ev(IMPORTED+'/natmedpro','reference_documents',r);node(r['id'],'ReferenceDocument',r,eids);edge(r['record_id'],r['id'],'HAS_REFERENCE_DOCUMENT',eids)
    refs=rows(IMPORTED+'/reddit','references')
    for r in refs:
        if r['status']=='resolved':target=r['target_record_id'];kind=r['relation']
        elif r['original_identifier']:
            target=external('reddit',r['original_identifier'],ev(IMPORTED+'/reddit','references',r));kind=r['relation']+'_REFERENCE'
        else:continue
        edge(r['record_id'],target,kind,ev(IMPORTED+'/reddit','references',r),r,token=r['id'])
    review['reddit_references']=refs
    # Navigation topics are not material entities. Keep literal-hit provenance.
    topics={};topic_rows={r['id']:r for s in imported.values() for r in s['topic_associations']}
    for d in rows(MAPS,'source_topic_context'):
        eids=ev(MAPS,'source_topic_context',d);tid=key('supplement_topic',d['topic']);topics[d['topic']]=tid
        if tid not in nodes:node(tid,'SupplementTopic',dict(name=d['topic'],scope='Navigation only; not material identity'),eids)
        if d['relation']=='unresolved_topic_context':continue
        edge(d['record_id'],tid,d['relation'].upper(),eids,dict(d,source_association=topic_rows[d['id']],clinical_inference=False),token=d['id'])
    for r in dt['occurrences']:
        topic=r['attributes'].get('ingredientGroup')
        if r['role']=='ingredient' and topic in topics:edge(r['id'],topics[topic],'HAS_DECLARED_TOPIC',r['evidence_ids'],dict(scope='Exact source ingredientGroup navigation only'))
    mappings=rows(MAPS,'terminology_decisions');subjects=rows(MAPS,'natmed_subject_decisions');additional=rows(MAPS,'additional_reviewed_proposals')
    for d in mappings:
        if d['confidence']=='High':mapping(d,d['target_record_id'],MAPS,'terminology_decisions')
    for d in subjects:
        if d['confidence']=='High':mapping(d,key('monograph_subject',d['monograph_id']),MAPS,'natmed_subject_decisions')
    for d in additional:
        if d['confidence']=='High':mapping(d,term_lookup[(d['target_source'],d['target_native_id'])],MAPS,'additional_reviewed_proposals')
    review['mapping_pending_excluded']=[d for d in mappings+subjects+additional if d['confidence']!='High']
    review['no_candidate_queries']=rows(MAPS,'no_candidate_queries');review['natmed_no_subject_bridge']=rows(MAPS,'natmed_no_subject_bridge')
    review['pending_clinical_claims']=[dict(id=c['id'],review_state=c['review_state'],clinical_approval=False) for c in claims]
    # Preserve Step4 decisions and optional exact-text index, without adding same-as edges.
    for p in sorted((root/IDENTITY).glob('*.jsonl')):sidecars['review/identity/'+p.name]=read(str(p.relative_to(root)))
    for s in ['natmedpro','reddit']:
        for name in ['duplicate_review_from_audit.json','upstream_extraction_report.json','context_review_from_audit.json']:
            p=f'{IMPORTED}/{s}/{name}'
            if (root/p).exists():sidecars[f'review/{s}/{name}']=read(p)
    checks=validate(list(nodes.values()),list(edges.values()),evidence,expected)
    counts=dict(nodes=len(nodes),edges=len(edges),mapping_edges=len(expected),terminology_mapping_edges=sum(d['confidence']=='High' for d in mappings),natmed_subject_mapping_edges=sum(d['confidence']=='High' for d in subjects),additional_category_edges=len(additional),pending_clinical_claims=len(claims),pending_or_excluded_mappings=len(review['mapping_pending_excluded']))
    report=dict(stage='Step 5 expanded export; Step 6 representative-question validation and freeze pending',counts=counts,node_types=dict(Counter(n['type'] for n in nodes.values())),edge_types=dict(Counter(e['type'] for e in edges.values())),checks=checks,canonical_merges=0,clinical_approvals=0,limitations=['All source records retained; presence of a concept node does not activate a candidate mapping.','Pending claims are attributed source annotations, not approved clinical facts.','Source-declared label relationships do not establish product equivalence.','Unresolved mapping/reference and preparation queues remain exported.','No embeddings, database import, or general answering system.'])
    return list(nodes.values()),list(edges.values()),evidence,review,sidecars,report,inputs,expected

def run(root=ROOT):
    root=Path(root);nodes,edges,evidence,review,files,report,inputs,expected=build(root)
    def csv_bytes(rows,fields):
        buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
        for r in sorted(rows,key=lambda r:r['id']):w.writerow({k:encode(r[k[:-5]]) if k.endswith('_json') else encode(r[k]) if isinstance(r[k],(dict,list)) else r[k] for k in fields})
        return buf.getvalue().encode()
    for typ in sorted({n['type'] for n in nodes}):files['nodes/'+typ+'.csv']=csv_bytes([n for n in nodes if n['type']==typ],['id','type','properties_json','evidence_ids'])
    files['relationships/relationships.csv']=csv_bytes(edges,['id','start_id','end_id','type','mapping_id','confidence','evidence_ids','properties_json'])
    for name,rows_ in review.items():files['review/'+name+'.jsonl']=(''.join(encode(r)+'\n' for r in rows_)).encode()
    files['provenance/evidence.jsonl']=(''.join(encode(evidence[i])+'\n' for i in sorted(evidence))).encode()
    files['validation_report.json']=(encode(report)+'\n').encode()
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in ['scripts/export_full_graph.py','scripts/preprocess_pilot.py','scripts/decide_ingredient_mappings.py','tests/test_export_full_graph.py']},python=sys.version.split()[0])
    files['input_manifest.json']=(encode(signature)+'\n').encode()
    manifest=dict(version='full-graph-v1',spec=SPEC,**report,files={p:sha(b) for p,b in sorted(files.items())})
    files['manifest.json']=(encode(manifest)+'\n').encode();out=root/'data/graph'/('full-graph-v1-'+sha(files['manifest.json'])[:20])
    if out.exists():
        assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(files)
        for p,b in files.items():assert (out/p).read_bytes()==b,p
    else:
        out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.full-graph-',dir=out.parent))
        try:
            for p,b in files.items():(tmp/p).parent.mkdir(parents=True,exist_ok=True);(tmp/p).write_bytes(b)
            os.rename(tmp,out)
        except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
    for p,h in inputs.items():assert sha((root/p).read_bytes())==h,p
    print(out.relative_to(root));print(json.dumps(report,indent=2));return out,report
if __name__=='__main__':run()
