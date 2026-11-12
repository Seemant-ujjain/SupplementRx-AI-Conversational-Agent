"""NatMed baseline and local JSON Schema/source-support validation, not clinical review."""
import gzip
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from importlib.metadata import version
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from audit_dsld_baseline import collect_objects, profile
from review_dsld_name_groups import snapshot, sha

VERSION='natmed-baseline-audit-v1'

def leaves(value,prefix=''):
    if isinstance(value,dict):
        for k,v in value.items():yield from leaves(v,f'{prefix}.{k}' if prefix else k)
    elif value is not None:yield prefix,value

def supported_value(value,text):
    if type(value) in (int,float):
        try:return Decimal(str(value))==Decimal(text.strip())
        except InvalidOperation:return False
    return value==text

def validate_support(claim,records):
    errors=[];earlier=[]
    def fail(code,path=None):errors.append({'code':code,'field':path})
    src=claim['source'];r=records.get(src['record_id'])
    if not r:return [{'code':'missing_source_record','field':None}],[]
    idx=src['section_index']
    if not 0<=idx<len(r['sections']):return [{'code':'invalid_section_index','field':None}],[]
    section=r['sections'][idx];text=section['text'];start,end=src['start'],src['end']
    if not 0<=start<end<=len(text) or text[start:end]!=src['excerpt'] or claim['claim_text']!=src['excerpt']:fail('excerpt_or_bounds_mismatch')
    if src['content_hash']!=r['content_hash'] or sha(r['text'].encode())!=r['content_hash']:fail('content_hash_mismatch')
    if src['url']!=r['source_url'] or src['section_heading']!=section['heading']:fail('source_url_or_heading_mismatch')
    if claim['ingredient']['name']!=r['title']:fail('ingredient_source_title_mismatch')
    if r.get('evidence_role')!='clinical_reference':fail('source_evidence_role_mismatch')
    fields={}
    for k in ['ingredient','population','indication','effectiveness_rating','safety_rating','adverse_effect_category','dose','evidence_grade','interaction']:
        fields.update(dict(leaves(claim[k],k)))
    fields.pop('ingredient.name',None)
    if set(fields)!=set(claim['field_support']):fail('field_support_key_mismatch')
    for field,anchor in claim['field_support'].items():
        a,b=anchor['start'],anchor['end']
        if not 0<=a<b<=len(text):fail('anchor_out_of_bounds',field);continue
        if field in fields and not supported_value(fields[field],text[a:b]):fail('anchor_value_mismatch',field)
        if not start<=a<b<=end:
            if field=='effectiveness_rating' and b<=start and claim.get('indication'):
                earlier.append({'claim_id':claim['id'],'record_id':src['record_id'],'section_index':idx,'start':a,'end':b,'excerpt_start':start,'rating':claim[field]})
            else:fail('anchor_outside_excerpt',field)
    dose=claim['dose']
    if dose.get('minimum') is not None and dose.get('maximum') is not None and dose['minimum']>dose['maximum']:fail('reversed_dose_range')
    return errors,earlier

def duplicate_groups(rows,key):
    groups=defaultdict(list)
    for r in rows:groups[key(r)].append(r['id'])
    return [ids for ids in groups.values() if len(ids)>1]

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw);base=raw/'natmedpro';pending=base/'upstream_derived/pending_clinical'
    def readlines(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    records=readlines(base/'records.jsonl');passages=readlines(base/'upstream_derived/passages.jsonl');claims=readlines(pending/'clinical_claims.jsonl');html=readlines(base/'source_html.jsonl')
    byid={r['id']:r for r in records};errors=[]
    def check(ok,code,detail=None):
        if not ok:errors.append({'code':code,'detail':detail})
    manifest=json.loads((base/'collection_manifest.json').read_text())
    for name,meta in manifest['files'].items():
        b=(base/name).read_bytes();check(len(b)==meta['bytes'] and sha(b)==meta['sha256'],'manifest_mismatch',name)
    cm=json.loads((pending/'clinical_claims_manifest.json').read_text());schema_bytes=(pending/'clinical_claim.schema.json').read_bytes();schema=json.loads(schema_bytes)
    check(sha(json.dumps(schema,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==cm['inputs']['clinical_schema_sha256'],'clinical_schema_fingerprint_mismatch')
    archive=project/manifest['upstream_archive_directory']/'datasets/records.jsonl.gz'
    combined_records=[json.loads(line) for line in gzip.decompress(archive.read_bytes()).decode().splitlines() if line.strip()]
    combined_fingerprint=sha(json.dumps(sorted(combined_records,key=lambda r:r['id']),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
    check(combined_fingerprint==cm['inputs']['source_records_sha256'],'upstream_combined_source_fingerprint_mismatch')
    Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema,format_checker=FormatChecker())
    for kind,rows in [('monograph',records),('passage',passages),('claim',claims)]:check(len({r['id'] for r in rows})==len(rows),'duplicate_ids',kind)
    for r in records:
        check(sha(r['text'].encode())==r['content_hash'],'monograph_text_hash',r['id'])
        for doc in r['reference_documents']:check(sha(doc['text'].encode())==doc['content_hash'],'reference_document_hash',r['id'])
    for h in html:
        r=byid.get(h['record_id']);check(r is not None and sha(h['html'].encode())==h['sha256']==r['source_html_sha256']==cm['inputs']['source_html_sha256'].get(h['record_id']),'html_binding',h['record_id'])
    check({h['record_id'] for h in html}==set(byid),'html_record_coverage')
    for p in passages:
        try:
            r=byid[p['record_id']];s=r['sections'][p['section_index']];words=s['text'].split();a=p['word_start'];n=p['word_count']
            valid=(a>=0 and n>0 and a+n<=len(words) and ' '.join(words[a:a+n])==p['text'] and p['source_content_hash']==r['content_hash'] and p['source_url']==r['source_url'] and p['section']==s['heading'])
        except (KeyError,IndexError,TypeError):valid=False
        check(valid,'passage_binding',p['id'])
    schema_errors=[];support_errors=[];earlier=[];valid_claims=[]
    for c in claims:
        es=list(validator.iter_errors(c))
        schema_errors.extend({'claim_id':c.get('id'),'path':list(e.absolute_path),'message':e.message} for e in es)
        if es:continue
        valid_claims.append(c);es,heads=validate_support(c,byid);support_errors.extend({'claim_id':c['id'],**e} for e in es);earlier.extend(heads)
    # Check intervening publisher ratings known from this source's annotations.
    ratings=defaultdict(set)
    for c in valid_claims:
        if c.get('effectiveness_rating'):ratings[(c['source']['record_id'],c['source']['section_index'])].add(c['effectiveness_rating'])
    for anchor in earlier:
        key=(anchor['record_id'],anchor['section_index']);text=byid[key[0]]['sections'][key[1]]['text']
        for rating in sorted(ratings[key]):
            if re.search(r'(?m)^\s*'+re.escape(rating)+r'\s*$',text[anchor['end']:anchor['excerpt_start']]):
                support_errors.append({'claim_id':anchor['claim_id'],'code':'possible_intervening_rating_heading','field':'effectiveness_rating'})
    nodes=readlines(base/'upstream_derived/kg_nodes.jsonl');edges=readlines(base/'upstream_derived/kg_edges.jsonl');node_ids={n['id'] for n in nodes}
    check(len(node_ids)==len(nodes),'duplicate_graph_node_ids')
    for e in edges:check(e['source'] in node_ids and e['target'] in node_ids,'graph_endpoint_missing',e)
    objects=defaultdict(list)
    for root,rows in [('record',records),('passage',passages),('claim',claims)]:
        for r in rows:collect_objects(r,root,objects)
    profiles=profile(objects)
    coverage={}
    for typ in sorted({c['claim_type'] for c in claims}):
        typed=[c for c in claims if c['claim_type']==typ];field_names=sorted({k for c in typed for k,v in leaves(c) if k.startswith(('dose.','ingredient.','interaction.')) or k in ['population','indication','effectiveness_rating','safety_rating','evidence_grade','adverse_effect_category']})
        # Include null fields too, using the schema's annotation paths and explicit scalar names.
        field_names=sorted(set(field_names)|{'ingredient.formulation','ingredient.strain','population','indication','evidence_grade','effectiveness_rating','safety_rating','dose.value','dose.minimum','dose.maximum','dose.unit','dose.frequency','dose.route','dose.duration','interaction.partner','interaction.rating','interaction.severity','interaction.occurrence'})
        def get(c,path):
            for part in path.split('.'):
                if not isinstance(c,dict):return None
                c=c.get(part)
            return c
        coverage[typ]={'claims':len(typed),'fields':{k:{'populated':sum(get(c,k) is not None for c in typed),'null_or_absent':sum(get(c,k) is None for c in typed)} for k in field_names}}
    upstream=json.loads((pending/'clinical_extraction_report.json').read_text())
    source_summary=[{'id':r['id'],'title':r['title'],'topics':r['supplements'],'sections':len(r['sections']),
        'passages':sum(p['record_id']==r['id'] for p in passages),'claims':sum(c['source']['record_id']==r['id'] for c in claims),
        'source_updated_at':r['source_updated_at'],'collected_at':r['collected_at'],'requires_clinical_review':r['requires_clinical_review'],
        'capture_complete':r['capture_quality']['complete'],'bibliography_coverage':r['capture_quality'].get('bibliography_coverage')} for r in records]
    dup={'record_text':duplicate_groups(records,lambda r:r['text']), 'passage_text':duplicate_groups(passages,lambda r:r['text']),
         'claim_text':duplicate_groups(claims,lambda r:r['claim_text']),
         'claim_payload_except_id':duplicate_groups(claims,lambda c:json.dumps({k:v for k,v in c.items() if k!='id'},sort_keys=True)),
         'claim_source_span_and_type':duplicate_groups(claims,lambda c:(c['source']['record_id'],c['source']['section_index'],c['source']['start'],c['source']['end'],c['claim_type']))}
    summary={'monographs':len(records),'passages':len(passages),'claims':len(claims),'html_captures':len(html),
        'claim_types':dict(Counter(c['claim_type'] for c in claims)),'review_states':dict(Counter(c['review']['state'] for c in claims)),
        'graph_nodes':len(nodes),'graph_edges':len(edges),'graph_edge_types':dict(Counter(e['type'] for e in edges)),
        'schema_draft':'2020-12','claim_contract':cm['claim_contract'],'jsonschema_version':version('jsonschema'),
        'schema_valid_claims':len(valid_claims),'schema_error_count':len(schema_errors),'source_support_error_count':len(support_errors),
        'field_support_anchors_checked':sum(len(c['field_support']) for c in valid_claims),'earlier_effectiveness_heading_anchors':len(earlier),
        'integrity_error_count':len(errors),'duplicate_groups':{k:len(v) for k,v in dup.items()},
        'monographs_requiring_review':sum(r['requires_clinical_review'] for r in records),
        'upstream_reported_extraction_issues':upstream['extraction_issue_counts'],
        'upstream_reported_missing_bibliography_citation_refs':sum((r['capture_quality'].get('bibliography_coverage') or {}).get('inline_citation_refs_missing_from_bibliography',0) for r in records),
        'records_corrected':0,'claims_approved':0,'records_merged':0}
    policy=['This audit validates the local imported snapshot, not the current publisher website or upstream HEAD.',
        'JSON Schema validation uses Draft 2020-12 with URI/date-time format checks. It does not execute the upstream custom Python validator.',
        'Independent source checks cover hashes, URLs, section headings, source-title ingredient identity, excerpts, offsets, expected non-null field anchors, exact text/numeric values and dose-range ordering.',
        'Earlier effectiveness-rating anchors are allowed as specified by the contract. Intervening-heading checking uses ratings observed in the annotations; exhaustive publisher-HTML group interpretation remains pending.',
        'Passage text/word windows and source hashes are checked. Citation bibliographic linkage and whether a citation supports a claim are not clinically validated here.',
        'Reported 55 missing bibliography references and upstream extraction issues are imported findings, not newly established publisher errors.',
        'Exact duplicate text is a candidate only: repeated headings and overlapping passages are expected, and source/population/context must be preserved.',
        'Fish Oil does not represent every Omega-3 formulation; Lactobacillus acidophilus does not represent all probiotics. UMLS/chemical mappings remain separate.',
        'Structural validity and matching source spans do not approve a medical association, certify capture completeness, or convert source claims into recommendations.',
        'All pending states remain pending. No normalization, deduplication or clinical approval is performed.']
    report={'summary':summary,'policy':policy,'sources':source_summary,'field_coverage_by_claim_type':coverage,
        'duplicates':dup,'schema_errors':schema_errors,'source_support_errors':support_errors,'integrity_errors':errors,
        'earlier_effectiveness_anchors':earlier,'upstream_readiness':upstream['readiness']}
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),'field_profiles.json':(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# NatMed baseline and source-support audit','','```json',json.dumps(summary,indent=2),'```','']+['- '+p for p in policy])+'\n').encode()}
    if snapshot(raw)!=before:raise RuntimeError('Raw data changed')
    inputs={str(p.relative_to(project)):sha(p.read_bytes()) for p in sorted(base.rglob('*')) if p.is_file()}
    out=project/'data/processed/natmedpro'/(VERSION+'-'+sha(json.dumps(inputs,sort_keys=True).encode()+Path(__file__).read_bytes())[:16])
    m={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'inputs':inputs,'jsonschema_version':version('jsonschema'),
       'raw_file_count':len(before),'raw_files_unchanged':True,'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing overwrite of edited output: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
