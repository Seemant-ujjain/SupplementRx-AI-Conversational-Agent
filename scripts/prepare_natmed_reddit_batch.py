"""Full saved-source preparation; structural support is not clinical approval."""
from pathlib import Path
from collections import Counter,defaultdict
import json,re,sys,os,tempfile,shutil
from importlib.metadata import version
from jsonschema import Draft202012Validator,FormatChecker
from preprocess_pilot import sha,key,encode,states,search_key,pointer
from audit_natmed import validate_support
from audit_reddit import record_issues,passage_valid
ROOT=Path(__file__).resolve().parents[1]
SPEC='schemas/natmed_reddit_preparation_batch_v1.json'
AUDITS={'natmedpro':'natmed-baseline-audit-v1-b548c344b8c0a9b7','reddit':'reddit-baseline-audit-v1-058aea355a5bb848'}

def literal_hits(record,terms):
    return [dict(field=field,term=term,start=m.start(),end=m.end(),text=m.group()) for field in ['title','text'] for term in terms for m in re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',record.get(field) or '',re.I)]
def topic_status(scope,hits):
    if scope=='thread_context':return 'inherited_thread_context'
    if scope=='own_text':return 'literal_alias_in_record' if hits else 'topic_not_verified_in_own_text_record'
    raise ValueError('Unknown mention scope')
def resolve_reference(value,by_native,field,record_type):
    if field=='parent_id' and record_type=='post':return 'not_applicable',None
    if value is None or value=='':return 'missing_identifier',None
    if not isinstance(value,str) or not re.fullmatch(r't[13]_[a-z0-9]+',value) or (field=='thread_id' and not value.startswith('t3_')):return 'invalid_identifier',None
    return ('resolved',by_native[value]['id']) if value in by_native else ('outside_saved_collection',None)
def build(root=ROOT):
    root=Path(root);inputs={SPEC:sha((root/SPEC).read_bytes())};outputs={};reports={}
    for source,run in AUDITS.items():
        ap=f'data/processed/{source}/{run}';manifest_path=ap+'/manifest.json';am=json.loads((root/manifest_path).read_bytes());inputs[manifest_path]=sha((root/manifest_path).read_bytes())
        audit_path=ap+'/audit.json';audit_bytes=(root/audit_path).read_bytes();assert sha(audit_bytes)==am['files']['audit.json']['sha256'];inputs[audit_path]=sha(audit_bytes);audit=json.loads(audit_bytes)
        documents={}
        def read(path):
            raw=(root/path).read_bytes();assert sha(raw)==am['inputs'][path],path;inputs[path]=sha(raw)
            result=[json.loads(l) for l in raw.splitlines() if l.strip()] if path.endswith('.jsonl') else json.loads(raw)
            documents[path]=result;return result
        rp=f'data/raw/{source}/records.jsonl';pp=f'data/raw/{source}/upstream_derived/passages.jsonl'
        records=read(rp);passages=read(pp);cm=read(f'data/raw/{source}/collection_manifest.json')
        byid={r['id']:r for r in records};assert len(byid)==len(records)
        tables={t:[] for t in ['records','passages','topic_associations','references','claims','field_support','reference_documents','html_bindings','review_queue']}
        checked=set()
        def provenance(path,loc,expected=None):
            value=pointer(documents[path],loc)
            if expected is not None:assert value==expected
            checked.add((path,loc));return dict(file=path,sha256=inputs[path],pointer=loc)
        def queue(owner,reason,details=None):tables['review_queue'].append(dict(id=key('imported_preparation_review',source,owner,reason),owner_id=owner,reason=reason,status='needs_review',details=details))
        for i,r in enumerate(records):
            assert sha(r['text'].encode())==r['content_hash']
            if source=='reddit':assert not record_issues(r)
            else:assert r['evidence_role']=='clinical_reference' and r['record_type']=='monograph'
            tables['records'].append(dict(id=r['id'],source=source,original_fields=r,field_states=states(r),display_title=r['title'].strip(),search_title=search_key(r['title']),evidence_role=r['evidence_role'],clinical_approval=False,provenance=provenance(rp,f'/{i}',r)))
            for j,t in enumerate(r.get('supplements',[])):
                name=t['supplement'] if isinstance(t,dict) else t;terms=t.get('matched_terms',[]) if isinstance(t,dict) else []
                hits=literal_hits(r,terms) if source=='reddit' else []
                status=topic_status(r['mention_scope'],hits) if source=='reddit' else 'source_monograph_topic'
                tid=key('prepared_imported_topic',source,r['id'],str(j))
                tables['topic_associations'].append(dict(id=tid,record_id=r['id'],topic=name,original_topic=t,original_mention_scope=r.get('mention_scope'),literal_hits=hits,topic_status=status,confidence=None,clinical_inference=False,provenance=provenance(rp,f'/{i}/supplements/{j}',t)))
                if status=='topic_not_verified_in_own_text_record':queue(tid,status)
        for i,p in enumerate(passages):
            r=byid[p['record_id']]
            if source=='reddit':assert passage_valid(p,r)
            else:
                section=r['sections'][p['section_index']];words=section['text'].split();a,n=p['word_start'],p['word_count']
                assert type(a) is int and type(n) is int and 0<=a and n>0 and a+n<=len(words)
                assert p['text']==' '.join(words[a:a+n]) and p['source_content_hash']==r['content_hash'] and p['source_url']==r['source_url'] and p['section']==section['heading']
            tables['passages'].append(dict(id=p['id'],record_id=p['record_id'],original_fields=p,field_states=states(p),source_binding_valid=True,clinical_approval=False,provenance=provenance(pp,f'/{i}',p)))
        if source=='natmedpro':
            cp=f'data/raw/{source}/upstream_derived/pending_clinical/clinical_claims.jsonl';sp=f'data/raw/{source}/upstream_derived/pending_clinical/clinical_claim.schema.json'
            clinical_manifest=read(f'data/raw/{source}/upstream_derived/pending_clinical/clinical_claims_manifest.json');claims=read(cp);schema=read(sp);Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema,format_checker=FormatChecker())
            extraction=read(f'data/raw/{source}/upstream_derived/pending_clinical/clinical_extraction_report.json');html=read(f'data/raw/{source}/source_html.jsonl')
            indices={r['id']:i for i,r in enumerate(records)};earlier=[];ratings=defaultdict(set)
            for c in claims:
                if c.get('effectiveness_rating'):ratings[(c['source']['record_id'],c['source']['section_index'])].add(c['effectiveness_rating'])
            for i,c in enumerate(claims):
                validator.validate(c);errors,heads=validate_support(c,byid);assert not errors,(c['id'],errors);earlier.extend(heads)
                assert c['review']['state']=='pending'
                s=c['source'];ri=indices[s['record_id']];text=byid[s['record_id']]['sections'][s['section_index']]['text'];loc=f'/{ri}/sections/{s["section_index"]}/text'
                source_span=dict(provenance(rp,loc),start=s['start'],end=s['end'],coordinate_system='unicode_codepoints')
                tables['claims'].append(dict(id=c['id'],record_id=s['record_id'],original_fields=c,field_states=states(c),nested_field_states={k:states(c[k]) for k in ['ingredient','dose','interaction','source','review']},technical_validation='schema_and_source_support_passed',review_state=c['review']['state'],clinical_approval=False,confidence=None,provenance=provenance(cp,f'/{i}',c),source_span=source_span))
                queue(c['id'],'pending_clinical_review')
                for field,a in c['field_support'].items():
                    outside=not s['start']<=a['start']<a['end']<=s['end']
                    tables['field_support'].append(dict(id=key('prepared_claim_field',c['id'],field),claim_id=c['id'],field=field,source_text=text[a['start']:a['end']],anchor_scope='earlier_section_heading' if outside else 'within_excerpt',source_span=dict(provenance(rp,loc),start=a['start'],end=a['end'],coordinate_system='unicode_codepoints'),original_anchor_provenance=provenance(cp,f'/{i}/field_support/'+field,a)))
            for anchor in earlier:
                rkey=(anchor['record_id'],anchor['section_index']);text=byid[rkey[0]]['sections'][rkey[1]]['text']
                assert not any(re.search(r'(?m)^\s*'+re.escape(rating)+r'\s*$',text[anchor['end']:anchor['excerpt_start']]) for rating in ratings[rkey])
            for i,r in enumerate(records):
                queue(r['id'],'source_capture_requires_review',r['capture_quality'])
                for j,doc in enumerate(r['reference_documents']):
                    assert sha(doc['text'].encode())==doc['content_hash']
                    tables['reference_documents'].append(dict(id=key('prepared_bibliography',r['id'],str(j)),record_id=r['id'],original_fields=doc,content_status='captured_bibliography_not_independent_study_validation',provenance=provenance(rp,f'/{i}/reference_documents/{j}',doc)))
            for i,h in enumerate(html):
                r=byid[h['record_id']];assert sha(h['html'].encode())==h['sha256']==r['source_html_sha256']==clinical_manifest['inputs']['source_html_sha256'][r['id']]
                tables['html_bindings'].append(dict(id=key('prepared_html',r['id']),record_id=r['id'],html_sha256=h['sha256'],provenance=provenance(f'data/raw/{source}/source_html.jsonl',f'/{i}',h)))
            assert {h['record_id'] for h in html}==set(byid)
            summary=dict(records=len(records),passages=len(passages),claims=len(claims),claim_types=dict(Counter(c['claim_type'] for c in claims)),field_support_anchors=len(tables['field_support']),earlier_heading_anchors=len(earlier),pending_clinical_claims=len(claims),upstream_extraction_issues=audit['summary']['upstream_reported_extraction_issues'],upstream_missing_bibliography_numbers=audit['summary']['upstream_reported_missing_bibliography_citation_refs'])
            assert (len(records),len(passages),len(claims),len(tables['field_support']),len(earlier))==(10,1179,1269,2923,769)
            supplemental={'upstream_extraction_report.json':extraction}
        else:
            native={r['native_id']:r for r in records};assert len(native)==len(records)
            for i,r in enumerate(records):
                for field in ['parent_id','thread_id']:
                    value=r.get(field);status,target=resolve_reference(value,native,field,r['record_type'])
                    if target:
                        target_row=byid[target]
                        assert field!='thread_id' or target_row['record_type']=='post'
                        if field=='parent_id':assert target_row['thread_id']==r['thread_id']
                    rid=key('prepared_reddit_reference',r['id'],field)
                    tables['references'].append(dict(id=rid,record_id=r['id'],relation='REPLY_TO' if field=='parent_id' else 'IN_THREAD',original_identifier=value,status=status,target_record_id=target,availability_scope='full_saved_reddit_collection',provenance=provenance(rp,f'/{i}/{field}')))
                    if status not in {'resolved','not_applicable'}:queue(rid,status)
            summary=dict(records=len(records),passages=len(passages),record_types=dict(Counter(r['record_type'] for r in records)),original_mention_scopes=dict(Counter(r['mention_scope'] for r in records)),topic_association_statuses=dict(Counter(r['topic_status'] for r in tables['topic_associations'])),reference_statuses=dict(Counter(r['status'] for r in tables['references'])),missing_parent_ids=sum(r['record_type']=='comment' and not r['parent_id'] for r in records),health_claims_created=0)
            assert (len(records),len(passages))==(4880,5071)
            supplemental={'context_review_from_audit.json':audit['context_review']}
        for table,rows in tables.items():assert len({r['id'] for r in rows})==len(rows),(source,table)
        for table in ['passages','topic_associations','references','claims','reference_documents','html_bindings']:
            assert all(r['record_id'] in byid for r in tables[table])
        claimids={c['id'] for c in tables['claims']};assert all(r['claim_id'] in claimids for r in tables['field_support'])
        assert all(r['target_record_id'] is None or r['target_record_id'] in byid for r in tables['references'])
        assert all(r['original_fields']==byid[r['id']] for r in tables['records'])
        assert all(r['original_fields']==original for r,original in zip(tables['passages'],passages))
        if source=='natmedpro':assert all(r['original_fields']==original for r,original in zip(tables['claims'],claims))
        reports[source]=dict(summary=summary,table_counts={k:len(v) for k,v in tables.items()},verified_source_pointers=len(checked),checks=dict(complete_counts=True,original_fields_unchanged=True,record_and_passage_bindings=True,foreign_keys_resolve=True,clinical_approvals=0,semantic_merges=0))
        supplemental['duplicate_review_from_audit.json']=audit['duplicates']
        outputs[source]=(tables,supplemental)
    return outputs,reports,inputs

def run(root=ROOT):
    root=Path(root);outputs,reports,inputs=build(root)
    code=['scripts/prepare_natmed_reddit_batch.py','scripts/audit_natmed.py','scripts/audit_reddit.py','scripts/preprocess_pilot.py','tests/test_prepare_natmed_reddit_batch.py']
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in code},python=sys.version.split()[0],jsonschema=version('jsonschema'))
    build_id='natmed-reddit-prepared-v1-'+sha(encode(signature).encode())[:20];files={}
    for source,(tables,supplemental) in outputs.items():
        for table,rows in tables.items():files[source+'/'+table+'.jsonl']=(''.join(encode(r)+'\n' for r in sorted(rows,key=lambda r:r['id']))).encode()
        for name,value in supplemental.items():files[source+'/'+name]=(encode(value)+'\n').encode()
    report=dict(sources=reports,scope='Full saved-source preparation only; cross-source identity review, deduplication and graph expansion remain separate',graph_updated=False,accepted_mappings=0,clinical_approvals=0,semantic_merges=0,limitations=['Original text retained, not clinically corrected','Earlier rating checks consider only known saved rating headings','Literal alias matches do not establish personal use or medical relevance','Inherited thread context is never promoted to a direct mention','Bibliography/HTML capture integrity does not prove clinical support; upstream extraction/reference gaps remain'])
    files['validation_report.json']=(encode(report)+'\n').encode();files['input_manifest.json']=(encode(signature)+'\n').encode()
    files['manifest.json']=(encode(dict(build_id=build_id,spec=SPEC,sources=reports,files={p:sha(b) for p,b in files.items()}))+'\n').encode()
    out=root/'data/processed/imported'/build_id
    if out.exists():
        assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(files)
        for path,b in files.items():assert (out/path).read_bytes()==b
    else:
        out.parent.mkdir(parents=True,exist_ok=True);temp=Path(tempfile.mkdtemp(prefix='.imported-preparation-',dir=out.parent))
        try:
            for path,b in files.items():target=temp/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
            os.rename(temp,out)
        except BaseException:shutil.rmtree(temp,ignore_errors=True);raise
    for path,h in inputs.items():assert sha((root/path).read_bytes())==h
    print(out.relative_to(root));print(encode(reports));return out,report
if __name__=='__main__':run()
