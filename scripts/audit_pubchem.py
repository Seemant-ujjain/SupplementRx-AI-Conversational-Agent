"""Offline PubChem baseline audit. Candidate results never imply approved identity."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from audit_dsld_baseline import profile, normalized_name
from review_dsld_name_groups import snapshot, sha

VERSION='pubchem-baseline-audit-v1'
RUN='20261028T035149634190Z'

def resolve_path(value,path):
    tokens=re.findall(r'([A-Za-z_][A-Za-z_0-9]*)|\[(\d+)\]',path)
    if ''.join(k if k else '['+i+']' for k,i in tokens)!=path.replace('.',''):
        raise ValueError('Unsupported DSLD path')
    for key,index in tokens:value=value[key] if key else value[int(index)]
    return value

def collisions(records,field):
    groups=defaultdict(list)
    for cid,r in records.items():
        v=r['properties'].get(field)
        if v:groups[v].append(cid)
    return [{'value':v,'cids':ids} for v,ids in groups.items() if len(ids)>1]

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw)
    folder=raw/'pubchem/runs'/RUN;data=(folder/'collection.json').read_bytes();mbytes=(folder/'collection_manifest.json').read_bytes()
    collection=json.loads(data);manifest=json.loads(mbytes)
    errors=[]
    def check(ok,code,detail=None):
        if not ok:errors.append({'code':code,'detail':detail})
    check(sha(data)==manifest['sha256'] and len(data)==manifest['bytes'],'manifest_mismatch')
    queries=collection['queries'];results=collection['search_results'];records=collection['records']
    check(set(queries)==set(results),'query_result_keys_differ')
    provenance=collection['dsld_provenance'];dsld={}
    check(sha((raw/'dsld/collection_manifest.json').read_bytes())==provenance['manifest_sha256'],'dsld_manifest_changed')
    for lid,digest in provenance['label_sha256'].items():
        b=(raw/'dsld/labels'/f'label_{lid}.json').read_bytes();check(sha(b)==digest,'dsld_label_changed',lid);dsld[lid]=json.loads(b)
    occurrences=[];cid_queries=defaultdict(list);mapping_rows=[];category=defaultdict(Counter);occ_keys=[]
    for key,q in queries.items():
        s=results[key];cids=s.get('cids',[])
        check(cids==sorted(set(s.get('response',{}).get('IdentifierList',{}).get('CID',[]))),'result_cids_differ_from_response',key)
        check(len(cids)==len(set(cids)),'duplicate_cid_within_result',key)
        check((s['status']=='ok' and bool(cids)) or (s['status']=='not_found' and not cids),'unexpected_search_status',key)
        check(bool(s.get('requests')),'missing_search_request_trace',key)
        for cid in cids:cid_queries[str(cid)].append(key)
        cats=set()
        for o in q['occurrences']:
            occurrences.append(o);occ_keys.append((o['dsld_id'],o['json_path']));cats.update(o.get('search_categories',[]))
            try:source=resolve_path(dsld[o['dsld_id']],o['json_path'])
            except (KeyError,IndexError,ValueError,TypeError):check(False,'unresolved_dsld_path',o);continue
            check(source.get('name')==o['name'] and source.get('ingredientId')==o['ingredient_id'],'dsld_occurrence_mismatch',o)
            check(o['name'] in q['variants'],'occurrence_name_not_in_variants',o)
        for cat in cats:
            category[cat]['queries']+=1;category[cat][s['status']]+=1
        candidates=[]
        for cid in cids:
            rec=records.get(str(cid));check(rec is not None,'candidate_record_missing',cid)
            if rec:
                candidates.append({'cid':cid,'title':rec['properties'].get('Title'),
                    'query_matches_title_or_synonym':normalized_name(q['query']) in {normalized_name(v) for v in [rec['properties'].get('Title','')]+rec['synonyms'].get('Synonym',[])}})
        mapping_rows.append({'query_key':key,'query':q['query'],'variants':q['variants'],'status':s['status'],
                             'candidate_count':len(cids),'candidates':candidates,'occurrence_count':len(q['occurrences']),
                             'dsld_ids':sorted({o['dsld_id'] for o in q['occurrences']}),
                             'categories':sorted(cats),'mapping_status':'unreviewed' if cids else 'no_candidate_returned'})
    expected=set()
    def source_walk(rows,lid,path='ingredientRows'):
        for i,row in enumerate(rows or []):
            ptr=f'{path}[{i}]'
            if (row.get('name') or '').strip():expected.add((lid,ptr))
            for j,f in enumerate(row.get('forms') or []):
                if (f.get('name') or '').strip():expected.add((lid,f'{ptr}.forms[{j}]'))
            source_walk(row.get('nestedRows'),lid,ptr+'.nestedRows')
    for lid,l in dsld.items():source_walk(l['ingredientRows'],lid)
    check(set(occ_keys)==expected,'query_scope_coverage_mismatch',{'missing':sorted(expected-set(occ_keys)),'extra':sorted(set(occ_keys)-expected)})
    check(len(occ_keys)==len(set(occ_keys)),'duplicate_occurrence_paths')
    properties={};synonyms={}
    for batch in collection['compound_responses']:
        check(batch['status']=='ok','batch_failure',batch.get('kind'))
        response=batch['response']
        for p in response.get('PropertyTable',{}).get('Properties',[]):properties[str(p['CID'])]=p
        for s in response.get('InformationList',{}).get('Information',[]):synonyms[str(s['CID'])]=s
    check(set(records)==set(cid_queries),'record_candidate_set_mismatch')
    synonym_index=defaultdict(set);within_duplicates=0;missing=[]
    for cid,r in records.items():
        check(str(r['cid'])==cid==str(r['properties'].get('CID'))==str(r['synonyms'].get('CID')),'cid_disagreement',cid)
        check(r['properties']==properties.get(cid),'properties_batch_mismatch',cid)
        check(r['synonyms']==synonyms.get(cid),'synonym_batch_mismatch',cid)
        names=r['synonyms'].get('Synonym',[]);within_duplicates+=len(names)-len(set(names))
        for name in names:synonym_index[normalized_name(name)].add(cid)
        try:weight=float(r['properties']['MolecularWeight']);check(0<weight<float('inf'),'invalid_weight',cid)
        except (KeyError,TypeError,ValueError):check(False,'invalid_weight',cid)
        if not r['properties'].get('IUPACName'):missing.append({'cid':cid,'title':r['properties'].get('Title')})
    fields=profile({'query':list(queries.values()),'occurrence':occurrences,'search_result':list(results.values()),
        'record':list(records.values()),'properties':[r['properties'] for r in records.values()],
        'synonyms':[r['synonyms'] for r in records.values()],
        'request':[req for s in list(results.values())+collection['compound_responses'] for req in s.get('requests',[])]})
    shared_synonyms=[{'normalized_synonym':n,'cids':sorted(cs)} for n,cs in synonym_index.items() if len(cs)>1]
    shared_cids=[{'cid':cid,'title':records[cid]['properties'].get('Title'),'query_keys':qs} for cid,qs in cid_queries.items() if len(qs)>1]
    structure={f:collisions(records,f) for f in ['InChIKey','InChI','ConnectivitySMILES','MolecularFormula','Title']}
    summary={'source_labels':len(dsld),'query_groups':len(queries),'original_name_variants':sum(len(q['variants']) for q in queries.values()),
        'dsld_occurrences_verified':len(occurrences),'occurrence_kinds':dict(Counter(o['kind'] for o in occurrences)),
        'search_status':dict(Counter(s['status'] for s in results.values())),
        'queries_with_response_order_changed_by_collector':sum(s['cids']!=s.get('response',{}).get('IdentifierList',{}).get('CID',[]) for s in results.values()),
        'single_candidate_queries':sum(len(s['cids'])==1 for s in results.values()),
        'ambiguous_queries':sum(len(s['cids'])>1 for s in results.values()),'compound_records':len(records),
        'candidate_edges':sum(len(s['cids']) for s in results.values()),'cids_reached_by_multiple_queries':len(shared_cids),
        'synonym_entries':sum(len(r['synonyms']['Synonym']) for r in records.values()),
        'exact_duplicate_synonym_entries_within_cid':within_duplicates,'normalized_synonyms_shared_across_cids':len(shared_synonyms),
        'property_collision_groups':{k:len(v) for k,v in structure.items()},'missing_iupac_names':missing,
        'query_candidate_pairs_without_title_or_synonym_text_match':sum(not c['query_matches_title_or_synonym'] for row in mapping_rows for c in row['candidates']),
        'category_query_counts':{k:dict(v) for k,v in category.items()},
        'collected_from':collection['started_at_utc'],'collected_to':collection['finished_at_utc'],
        'mechanical_errors':len(errors),'approved_mappings':0,'records_merged':0}
    policy=['Offline audit of the saved snapshot; no fresh PubChem queries or external chemistry validation.',
        'The collector sorts and deduplicates returned CID lists; CID order is not interpreted as confidence ranking. Original API order remains in response payloads.',
        'Queries cover DSLD ingredient rows, nested rows and forms, including co-ingredients; otheringredients are outside this collection scope.',
        'Category counts overlap and reflect DSLD retrieval provenance, not compound identity or clinical indications.',
        'A single returned CID is still an unreviewed mapping candidate; shared query terms, synonyms, formulas or connectivity strings do not establish ingredient equivalence.',
        'No-match means no result from this saved name lookup, not absence from PubChem. A botanical, mixture, organism or broad nutrient class need not correspond to one compound.',
        'Full structure strings and CIDs retain their distinctions. No stereochemical, salt, hydrate or parent-compound equivalence is inferred.',
        'Synonyms are source-provided labels, not approved identifiers, clinical claims or a universal merge dictionary.',
        'Missing IUPACName does not invalidate an otherwise present record. A collection timestamp is not a compound revision timestamp.',
        'Scope/path/hash and response consistency checks establish traceability, not correctness of ingredient-to-compound identity.']
    report={'summary':summary,'policy':policy,'errors':errors,'mapping_review':mapping_rows,'shared_cids':shared_cids,
        'shared_synonyms':shared_synonyms,'property_collisions':structure,
        'field_dictionary':{'query':'A grouped DSLD name submitted to the name endpoint; variants/occurrences preserve origins.',
            'search_result':'Saved response, candidate CIDs, requests and outcome; not an identity decision.',
            'record':'One CID-keyed compound snapshot with properties and synonym response.',
            'compound_responses':'Batch source payloads from which records were assembled.',
            'dsld_provenance':'Hashes binding the queries to the 400 source labels.'}}
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),
        'field_profiles.json':(json.dumps(fields,ensure_ascii=False,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# PubChem baseline audit','','```json',json.dumps(summary,indent=2),'```','']+['- '+p for p in policy])+'\n').encode()}
    if before!=snapshot(raw):raise RuntimeError('Raw files changed')
    fingerprint=sha(data+mbytes+Path(__file__).read_bytes())[:16]
    out=project/'data/processed/pubchem'/(VERSION+'-'+fingerprint)
    outmanifest={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'source_collection':str((folder/'collection.json').relative_to(project)),
        'source_sha256':sha(data),'source_manifest_sha256':sha(mbytes),'raw_file_count':len(before),'raw_files_unchanged':True,
        'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(outmanifest,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing overwrite of modified report: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
