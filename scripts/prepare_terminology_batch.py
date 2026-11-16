"""Offline selected-field preparation for three terminology sources, without mapping approvals."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,os,tempfile,shutil
from preprocess_pilot import load,encode,sha,key,esc,pointer,dot_pointer,search_key,states
ROOT=Path(__file__).resolve().parents[1]
SPEC='schemas/terminology_preparation_batch_v1.json'
DSLD='data/processed/dsld/dsld-normalized-v1-66adbe28c3b0344457fb'
INPUTS='data/processed/terminology/terminology-review-v1-34294732268f2352/manifest.json'

def outcome(status,ids):
    if status not in {'ok','matched','not_found'}:raise ValueError('Unsuccessful/unknown source response')
    if (status=='not_found')!= (not ids):raise ValueError('Status/candidate disagreement')
    return 'no_candidate' if not ids else 'ambiguous_candidates' if len(ids)>1 else 'single_candidate'

def rdf_key(binding):return key('prepared_rdf',binding['subject']['value'],binding['predicate']['value'],encode(binding['object']))

def build(root=ROOT):
    root=Path(root);im=load((root/INPUTS).read_bytes());dm=load((root/DSLD/'manifest.json').read_bytes())
    for f,h in dm['files'].items():assert sha((root/DSLD/f).read_bytes())==h
    def rows(t):return {r['id']:r for r in map(load,(root/DSLD/(t+'.jsonl')).read_bytes().splitlines())}
    dr,ds,de,do=[rows(t) for t in ['source_records','snapshots','evidence','occurrences']]
    di={(dr[ds[o['snapshot_id']]['record_id']]['native_id'],de[o['evidence_ids'][0]]['locator']['pointer']):o for o in do.values()}
    sources={};input_hashes={INPUTS:sha((root/INPUTS).read_bytes()),SPEC:sha((root/SPEC).read_bytes()),DSLD+'/manifest.json':sha((root/DSLD/'manifest.json').read_bytes())}
    for source,meta in im['inputs'].items():
        raw=(root/meta['file']).read_bytes();assert sha(raw)==meta['sha256'];input_hashes[meta['file']]=sha(raw);sources[source]=load(raw)
    assert set(sources)=={'pubchem','rxnorm','mesh'}
    assert sources['pubchem']['queries']==sources['rxnorm']['queries']==sources['mesh']['queries']
    outputs={};reports={}
    for source,c in sources.items():
        tables={t:[] for t in ['records','properties','queries','query_origins','candidates','review_queue','subjects','rdf_statements','term_resolution','external_references']}
        checked=set()
        def prov(p,expected=None):
            val=pointer(c,p)
            if expected is not None:assert val==expected
            checked.add(p);return dict(source=source,pointer=p)
        def record_id(native):return key('prepared_record',source,str(native))
        def prop(native,name,value,p):
            r=dict(id=key('prepared_property',source,p),record_id=record_id(native),property_name=name,original_value=value,value_type=type(value).__name__,provenance=prov(p,value))
            if isinstance(value,str):r.update(display_value=value.strip(),search_value=search_key(value))
            tables['properties'].append(r)
        native_ids=set();resolution_by_term=defaultdict(set);resolution_rows=defaultdict(list)
        if source in {'pubchem','rxnorm'}:
            for native,record in sorted(c['records'].items()):
                rp='/records/'+esc(native);native_ids.add(native)
                if source=='pubchem':
                    values=record['properties'];assert str(record['cid'])==str(values['CID'])==native
                    fields=['CID','Title','IUPACName','MolecularFormula','MolecularWeight','ConnectivitySMILES','InChI','InChIKey'];base=rp+'/properties';name=values.get('Title')
                else:
                    values=record['properties']['response']['properties'];assert str(record['rxcui'])==str(values['rxcui'])==native
                    fields=['rxcui','name','synonym','tty','language','suppress','umlscui'];base=rp+'/properties/response/properties';name=values.get('name')
                tables['records'].append(dict(id=record_id(native),source=source,native_id=native,original_fields=values,field_states=states(values,fields),display_name=name.strip() if isinstance(name,str) else None,search_name=search_key(name) if isinstance(name,str) else None,provenance=prov(rp),mapping_approval=False))
                for k,v in values.items():prop(native,k,v,base+'/'+esc(k))
                if source=='pubchem':
                    assert str(record['synonyms']['CID'])==native
                    for i,v in enumerate(record['synonyms'].get('Synonym',[])):prop(native,'synonym',v,rp+f'/synonyms/Synonym/{i}')
                else:
                    for i,v in enumerate(record['all_properties']['response'].get('propConceptGroup',{}).get('propConcept',[])):
                        if v['propCategory'] in {'NAMES','SOURCES'} or (v['propCategory']=='CODES' and v['propName'] in {'UNII_CODE','DRUGBANK','SNOMEDCT'}):prop(native,v['propName'],v,rp+f'/all_properties/response/propConceptGroup/propConcept/{i}')
        else:
            native_ids={v for ids in c['candidate_record_index'].values() for v in ids};rdf={};subjects=defaultdict(list)
            for bi,batch in enumerate(c['record_subgraph_responses']):
                assert batch['complete']
                for pi,page in enumerate(batch['pages']):
                    assert page['status']=='ok'
                    for i,b in enumerate(page['response']['results']['bindings']):
                        bp=f'/record_subgraph_responses/{bi}/pages/{pi}/response/results/bindings/{i}';eid=prov(bp,b);rid=rdf_key(b)
                        assert b['object']['type'] in {'uri','literal','typed-literal','bnode'}
                        if rid not in rdf:rdf[rid]=dict(id=rid,subject_id=record_id(b['subject']['value']),subject_uri=b['subject']['value'],predicate_uri=b['predicate']['value'],typed_object=b['object'],provenance=[])
                        rdf[rid]['provenance'].append(eid)
                        subjects[b['subject']['value']].append(rid)
            assert native_ids<=set(subjects)
            tables['rdf_statements']=sorted(rdf.values(),key=lambda r:r['id'])
            for uri,sids in sorted(subjects.items()):
                values=[rdf[i] for i in sorted(set(sids))];labels=[v['typed_object'] for v in values if v['predicate_uri'].endswith('#label')]
                fields={'labels':labels,'types':[v['typed_object'] for v in values if v['predicate_uri'].endswith('#type')]}
                row=dict(id=record_id(uri),source=source,native_id=uri,original_fields=fields,field_states={'labels':'present' if labels else 'absent','types':'present' if fields['types'] else 'absent'},rdf_statement_ids=sorted(set(sids)),is_candidate_record=uri in native_ids,mapping_approval=False)
                tables['subjects'].append(row)
                if uri in native_ids:tables['records'].append(row)
            for r in tables['rdf_statements']:
                obj=r['typed_object'];is_uri=obj['type']=='uri';known=is_uri and obj['value'] in subjects
                r['target_subject_id']=record_id(obj['value']) if known else None
                if is_uri and not known:tables['external_references'].append(dict(id=key('prepared_external',r['id']),statement_id=r['id'],target_uri=obj['value'],status='not_described_in_saved_subgraphs',content_status='unknown',provenance=r['provenance']))
            for bi,batch in enumerate(c['term_resolution_responses']):
                assert batch['complete']
                for pi,page in enumerate(batch['pages']):
                    assert page['status']=='ok'
                    for i,b in enumerate(page['response']['results']['bindings']):
                        bp=f'/term_resolution_responses/{bi}/pages/{pi}/response/results/bindings/{i}'
                        row=dict(id=key('prepared_resolution',bp),binding=b,provenance=prov(bp,b));tables['term_resolution'].append(row)
                        resolution_by_term[b['term']['value']].add(b['record']['value']);resolution_rows[b['term']['value']].append(row['id'])
        for qk,q in sorted(c['queries'].items()):
            result=c['search_results'][qk];qp='/queries/'+esc(qk);rp='/search_results/'+esc(qk)
            ids=[str(i) for i in result['cids']] if source=='pubchem' else result['rxcuis'] if source=='rxnorm' else c['candidate_record_index'][qk]
            assert set(ids)<=native_ids
            status=outcome(result['status'],ids);qid=key('prepared_query',source,qk)
            resolution_ids=[]
            if source=='mesh':
                resolved=set()
                for term in result['term_uris']:resolved.update(resolution_by_term[term]);resolution_ids.extend(resolution_rows[term])
                assert resolved==set(ids) and not result['possibly_truncated'];prov('/candidate_record_index/'+esc(qk),ids)
            tables['queries'].append(dict(id=qid,query_key=qk,original_query=q['query'],variants=q['variants'],search_name=search_key(q['query']),source_status=result['status'],outcome=status,match_method=result.get('match_method','saved_name_lookup'),candidate_native_ids=ids,source_response=result,term_resolution_ids=sorted(set(resolution_ids)),provenance=[prov(qp,q),prov(rp,result)]))
            for i,o in enumerate(q['occurrences']):
                label=str(o['dsld_id']);loc=dot_pointer(o['json_path']);origin=di[(label,loc)]
                assert origin['original_name']==o['name'] and str(origin['native_ingredient_id'])==str(o['ingredient_id'])
                assert ds[origin['snapshot_id']]['payload_digest']==c['dsld_provenance']['label_sha256'][label]
                tables['query_origins'].append(dict(id=key('prepared_origin',qid,str(i)),query_id=qid,dsld_occurrence_id=origin['id'],original_context=o,provenance=prov(qp+f'/occurrences/{i}',o),dsld_evidence_ids=origin['evidence_ids']))
            for native in ids:
                cid=key('prepared_candidate',qid,native)
                tables['candidates'].append(dict(id=cid,query_id=qid,target_record_id=record_id(native),relation='candidate_unspecified',review_state='needs_review',confidence=None,provenance=[prov(rp,result)]))
                tables['review_queue'].append(dict(id=key('prepared_review',cid),owner_id=cid,reason_codes=['scope_review_required']+(['ambiguous_candidates'] if len(ids)>1 else []),status='needs_review'))
            if not ids:tables['review_queue'].append(dict(id=key('prepared_review',qid),owner_id=qid,reason_codes=['no_candidate'],status='unresolved'))
        for name,rows in tables.items():assert len({r['id'] for r in rows})==len(rows),(source,name)
        recids={r['id'] for r in tables['records']};qids={q['id'] for q in tables['queries']}
        assert all(r['query_id'] in qids and r['dsld_occurrence_id'] in do for r in tables['query_origins'])
        assert all(r['target_record_id'] in recids and r['query_id'] in qids and r['confidence'] is None and r['review_state']=='needs_review' for r in tables['candidates'])
        assert all(r['record_id'] in recids for r in tables['properties'])
        assert len(tables['queries'])==739 and len(tables['query_origins'])==3391
        if source=='mesh':
            assert len(tables['records'])==247 and len(tables['subjects'])==2360 and len(tables['rdf_statements'])==24792
        else:assert len(tables['records'])=={'pubchem':239,'rxnorm':287}[source]
        if source=='pubchem':assert sum(r['property_name']=='synonym' for r in tables['properties'])==46426
        reports[source]=dict(rows={t:len(r) for t,r in tables.items()},query_outcomes=dict(Counter(q['outcome'] for q in tables['queries'])),verified_source_pointers=len(checked),accepted_mappings=0,confidence_assigned=0,clinical_fields='not_supplied_by_source',field_policy='Original values/types and missing states retained; display/search values are separate; no casefolded identity merges')
        meta={k:v for k,v in c.items() if k in {'source','scope','started_at_utc','finished_at_utc','version_start','version_end','source_metadata_start','source_metadata_end','search_policy','dsld_provenance'}}
        outputs[source]=(tables,meta)
    return outputs,reports,input_hashes

def run(root=ROOT):
    root=Path(root);outputs,reports,inputs=build(root)
    code=['scripts/prepare_terminology_batch.py','scripts/preprocess_pilot.py','tests/test_prepare_terminology_batch.py']
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in code},python=sys.version.split()[0])
    build_id='terminology-prepared-v1-'+sha(encode(signature).encode())[:20];files={}
    for source,(tables,meta) in outputs.items():
        for table,rows in tables.items():files[f'{source}/{table}.jsonl']=(''.join(encode(r)+'\n' for r in sorted(rows,key=lambda r:r['id']))).encode()
        files[source+'/source_metadata.json']=(encode(meta)+'\n').encode()
    report=dict(scope='Collection-wide selected-field preparation, not mapping approval or graph expansion',sources=reports,dsld_dependency=DSLD,graph_updated=False,clinical_approvals=0,semantic_merges=0,checks=dict(source_hashes=True,query_inventory_consistent=True,dsld_occurrences_verified=True,all_candidates_preserved=True,mesh_typed_values_preserved=True,source_pointers_resolve=True),limitations=['Previously reviewed pilot links remain in their own immutable artifacts; these new candidate tables do not override those decisions','Properties excluded by the POC selection remain in hash-pinned raw responses','MeSH object-only URI targets are not fabricated as described concepts','No-match reflects saved lookup policy, not absence from a vocabulary'])
    files['validation_report.json']=(encode(report)+'\n').encode();files['input_manifest.json']=(encode(signature)+'\n').encode()
    manifest=dict(build_id=build_id,spec=SPEC,dsld_dependency=DSLD,files={p:sha(b) for p,b in files.items()},sources=reports)
    files['manifest.json']=(encode(manifest)+'\n').encode();out=root/'data/processed/terminology'/build_id
    if out.exists():
        assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(files)
        for p,b in files.items():assert (out/p).read_bytes()==b
    else:
        out.parent.mkdir(parents=True,exist_ok=True);temp=Path(tempfile.mkdtemp(prefix='.terminology-prepared-',dir=out.parent))
        try:
            for path,b in files.items():target=temp/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
            os.rename(temp,out)
        except BaseException:shutil.rmtree(temp,ignore_errors=True);raise
    for p,h in inputs.items():assert sha((root/p).read_bytes())==h
    print(out.relative_to(root));print(encode(reports));return out,report
if __name__=='__main__':run()
