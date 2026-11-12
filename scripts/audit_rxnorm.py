"""Offline RxNorm baseline audit; no mapping approvals or source edits."""
import json
from collections import Counter, defaultdict
from pathlib import Path
from audit_dsld_baseline import profile, normalized_name
from audit_pubchem import resolve_path
from audit_dsld_quantities import walk
from review_dsld_name_groups import snapshot, sha

VERSION='rxnorm-baseline-audit-v1'
RUN='20261028T060819025094Z'

def response_ids(search):
    return set(search.get('response',{}).get('idGroup',{}).get('rxnormId',[]))

def search_issues(result):
    problems=[];searches=result.get('searches',[]);ids=set(result.get('rxcuis',[]))
    if len(ids)!=len(result.get('rxcuis',[])):problems.append('duplicate_candidate_ids')
    method=result.get('match_method')
    modes=[s.get('mode') for s in searches]
    if modes not in [['exact'],['exact','normalized']]:problems.append('unexpected_search_sequence')
    if len(searches)>1 and response_ids(searches[0]):problems.append('fallback_after_exact_candidates')
    if ids:
        selected=[s for s in searches if s.get('mode')==method]
        if len(selected)!=1 or response_ids(selected[0])!=ids:problems.append('selected_response_mismatch')
        if result.get('status')!='matched' or result.get('requires_identity_review') is not True:problems.append('matched_status_or_review_flag')
    elif result.get('status')!='not_found' or any(response_ids(s) for s in searches):problems.append('no_match_response_mismatch')
    return problems

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw)
    folder=raw/'rxnorm/runs'/RUN;data=(folder/'collection.json').read_bytes();mb=(folder/'collection_manifest.json').read_bytes()
    source=json.loads(data);manifest=json.loads(mb);errors=[]
    def check(ok,code,detail=None):
        if not ok:errors.append({'code':code,'detail':detail})
    check(sha(data)==manifest['sha256'] and len(data)==manifest['bytes'],'collection_manifest_mismatch')
    queries=source['queries'];results=source['search_results'];records=source['records'];provenance=source['dsld_provenance']
    check(set(queries)==set(results),'query_result_key_mismatch')
    check(sha((raw/'dsld/collection_manifest.json').read_bytes())==provenance['manifest_sha256'],'dsld_manifest_changed')
    dsld={};expected=set()
    for lid,h in provenance['label_sha256'].items():
        b=(raw/'dsld/labels'/f'label_{lid}.json').read_bytes();check(sha(b)==h,'dsld_label_changed',lid);dsld[lid]=json.loads(b)
        for pointer,row in walk(dsld[lid]['ingredientRows']):
            def dotpath(p):
                tokens=p.strip('/').split('/');out=''
                for t in tokens:out+=('['+t+']') if t.isdigit() else ('.' if out else '')+t
                return out
            if (row.get('name') or '').strip():expected.add((lid,dotpath(pointer)))
            for i,form in enumerate(row.get('forms') or []):
                if (form.get('name') or '').strip():expected.add((lid,dotpath(pointer+f'/forms/{i}')))
    occurrences=[];paths=[];mapping=[];id_queries=defaultdict(list);requests=[];categories=defaultdict(Counter)
    for key,q in queries.items():
        s=results[key]
        for issue in search_issues(s):check(False,issue,key)
        for search in s['searches']:
            check(search['status']=='ok' and bool(search.get('requests')),'search_transport_failure',key)
            requests.extend(search.get('requests',[]))
            for req in search.get('requests',[]):
                check(req.get('params',{}).get('name')==q['query'],'request_name_mismatch',key)
                check(req.get('params',{}).get('allsrc')==0 and req.get('params',{}).get('search')=={'exact':0,'normalized':1}.get(search['mode']),'request_policy_mismatch',key)
        cats=set()
        for o in q['occurrences']:
            occurrences.append(o);paths.append((o['dsld_id'],o['json_path']));cats.update(o['search_categories'])
            try:r=resolve_path(dsld[o['dsld_id']],o['json_path'])
            except (KeyError,IndexError,ValueError,TypeError):check(False,'unresolved_occurrence',o);continue
            check(r.get('name')==o['name'] and r.get('ingredientId')==o['ingredient_id'],'source_occurrence_mismatch',o)
            check(o['name'] in q['variants'],'variant_missing',o)
        candidates=[]
        for rid in s['rxcuis']:
            id_queries[rid].append(key);r=records.get(rid);check(r is not None,'missing_concept_record',rid)
            if r:
                props=r['properties']['response'].get('properties',{})
                candidates.append({'rxcui':rid,'name':props.get('name'),'tty':props.get('tty'),
                    'query_matches_preferred_name':normalized_name(q['query'])==normalized_name(props.get('name'))})
        for cat in sorted(cats):categories[cat][s.get('match_method') or s['status']]+=1
        mapping.append({'query_key':key,'query':q['query'],'variants':q['variants'],'match_method':s.get('match_method'),
            'status':s['status'],'candidates':candidates,'candidate_count':len(candidates),
            'occurrence_count':len(q['occurrences']),'categories':sorted(cats),
            'mapping_status':'unreviewed' if candidates else 'no_candidate_returned'})
    check(set(paths)==expected,'scope_coverage_mismatch',{'missing':sorted(expected-set(paths)),'extra':sorted(set(paths)-expected)})
    check(len(paths)==len(set(paths)),'duplicate_occurrence_paths')
    check(set(records)==set(id_queries),'record_candidate_set_mismatch')
    props_list=[];all_props=[];code_index=defaultdict(set);name_index=defaultdict(set);duplicates=0
    for rid,r in records.items():
        for endpoint in ['properties','all_properties']:
            payload=r[endpoint];check(payload['status']=='ok' and payload.get('valid') is True,'incomplete_endpoint',{'rxcui':rid,'endpoint':endpoint})
            trace=payload.get('requests',[]);requests.extend(trace)
            check(any(req.get('status_code')==200 and req.get('response')==payload['response'] for req in trace),'endpoint_response_trace_mismatch',{'rxcui':rid,'endpoint':endpoint})
        p=r['properties']['response'].get('properties',{});props_list.append(p)
        check(rid==r['rxcui']==p.get('rxcui'),'rxcui_disagreement',rid)
        check(bool(p.get('name')) and bool(p.get('tty')),'missing_name_or_tty',rid)
        entries=r['all_properties']['response'].get('propConceptGroup',{}).get('propConcept',[]);all_props.extend(entries)
        triples=[(e.get('propCategory'),e.get('propName'),e.get('propValue')) for e in entries];duplicates+=len(triples)-len(set(triples))
        check(any(e.get('propName')=='RxCUI' and e.get('propValue')==rid for e in entries),'missing_self_rxcui_property',rid)
        check(any(e.get('propName')=='TTY' and e.get('propValue')==p.get('tty') for e in entries),'tty_property_mismatch',rid)
        for e in entries:
            if e.get('propCategory')=='NAMES' and e.get('propValue'):name_index[normalized_name(e['propValue'])].add(rid)
            if e.get('propCategory')=='CODES' and e.get('propValue') and e.get('propName')!='SPL_SET_ID':code_index[(e['propName'],e['propValue'])].add(rid)
    for v in ['version_start','version_end']:requests.extend(source[v].get('requests',[]))
    stable=source['version_start']['response']==source['version_end']['response']
    check(stable,'version_changed_during_collection')
    profiles=profile({'query':list(queries.values()),'occurrence':occurrences,'search_result':list(results.values()),
        'concept_properties':props_list,'property_entry':all_props,'request':requests})
    shared=[{'rxcui':rid,'name':records[rid]['properties']['response']['properties']['name'],'query_keys':qs} for rid,qs in id_queries.items() if len(qs)>1]
    shared_names=[{'normalized_name':n,'rxcuis':sorted(ids)} for n,ids in name_index.items() if len(ids)>1]
    shared_codes=[{'code_system':k,'value':v,'rxcuis':sorted(ids)} for (k,v),ids in code_index.items() if len(ids)>1]
    summary={'source_labels':len(dsld),'query_groups':len(queries),'name_variants':sum(len(q['variants']) for q in queries.values()),
        'dsld_occurrences_verified':len(occurrences),'search_status':dict(Counter(s['status'] for s in results.values())),
        'match_methods':dict(Counter(s['match_method'] for s in results.values() if s.get('match_method'))),
        'single_candidate_queries':sum(len(s['rxcuis'])==1 for s in results.values()),'ambiguous_queries':sum(len(s['rxcuis'])>1 for s in results.values()),
        'ambiguity_by_method':dict(Counter(s['match_method'] for s in results.values() if len(s['rxcuis'])>1)),
        'concept_records':len(records),'candidate_links':sum(len(s['rxcuis']) for s in results.values()),
        'term_types':dict(Counter(p.get('tty') for p in props_list)), 'suppression_flags':dict(Counter(p.get('suppress') for p in props_list)),
        'rxcuis_reached_by_multiple_queries':len(shared),'shared_normalized_property_names':len(shared_names),
        'shared_external_code_groups_excluding_spl_set_id':len(shared_codes),'shared_code_groups_by_system':dict(Counter(e['code_system'] for e in shared_codes)),
        'property_entries':len(all_props),'property_categories':dict(Counter(p['propCategory'] for p in all_props)),
        'property_name_counts':dict(Counter(p['propName'] for p in all_props)),'duplicate_property_triples_within_record':duplicates,
        'blank_synonym_fields':sum(not p.get('synonym') for p in props_list),'blank_umlscui_fields':sum(not p.get('umlscui') for p in props_list),
        'query_candidate_preferred_name_mismatches':sum(not c['query_matches_preferred_name'] for row in mapping for c in row['candidates']),
        'version_start':source['version_start']['response'],'version_end':source['version_end']['response'],'version_stable':stable,
        'search_policy':source['search_policy'],'category_counts':{k:dict(v) for k,v in categories.items()},
        'collection_started':source['started_at_utc'],'collection_finished':source['finished_at_utc'],
        'mechanical_errors':len(errors),'approved_mappings':0,'records_merged':0}
    policy=['Offline audit of saved RxNorm responses. No live lookup or external identifier validation.',
        'Exact and normalized describe the recorded search method, not approved chemical identity. Preferred-name mismatch alone is not proof of a bad mapping.',
        'Normalized candidates may omit the queried form or return several related concepts. Preserve the full query, source occurrence, candidate set and review state.',
        'No-match is an outcome of this lookup strategy, not proof of absence from RxNorm. No approximate search was collected.',
        'Term types IN, PIN and MIN remain explicit; do not flatten all concepts into interchangeable ingredient identities.',
        'Shared IDs allow reuse of a concept node, not approval of all incoming ingredient mappings. Shared names/codes do not trigger automatic merging.',
        'SPL_SET_ID property counts reflect source property volume, not numbers of unique ingredients or independent clinical evidence. Shared-code review excludes SPL_SET_ID and retains code namespaces.',
        'Blank synonym/umlscui fields are distinguished from missing concept identity. No UMLS access or clinical efficacy validation is supplied by this collection.',
        'Category membership reflects overlapping DSLD retrieval provenance, including co-ingredients, not indication or efficacy.',
        'Query scope excludes DSLD otheringredients; collection timestamp and stable vocabulary version do not verify product currency.']
    report={'summary':summary,'policy':policy,'errors':errors,'mapping_review':mapping,'shared_concepts':shared,
        'shared_property_names':shared_names,'shared_external_codes':shared_codes,
        'field_dictionary':{'query':'Grouped DSLD name with variants and source occurrences.',
        'searches':'Ordered exact then, when needed, normalized API responses and request parameters.',
        'record':'One RxCUI-keyed concept with properties and allProperties snapshots.',
        'tty':'Preserved concept term type; relevant to mapping scope.',
        'all_properties':'Typed attributes, source codes, names and source metadata; not clinical evidence.',
        'version_start/version_end':'Vocabulary and API version responses bracketing collection.'}}
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),
        'field_profiles.json':(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# RxNorm baseline audit','','```json',json.dumps(summary,indent=2),'```','']+['- '+p for p in policy])+'\n').encode()}
    if snapshot(raw)!=before:raise RuntimeError('Raw files changed')
    out=project/'data/processed/rxnorm'/(VERSION+'-'+sha(data+mb+Path(__file__).read_bytes())[:16])
    m={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'source_collection':str((folder/'collection.json').relative_to(project)),
        'source_sha256':sha(data),'source_manifest_sha256':sha(mb),'raw_file_count':len(before),'raw_files_unchanged':True,
        'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing to overwrite changed report: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
