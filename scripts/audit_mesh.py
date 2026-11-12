"""Offline MeSH baseline audit; preserve RDF identities and candidate mappings."""
import json
from collections import Counter,defaultdict
from pathlib import Path
from audit_pubchem import resolve_path
from audit_dsld_baseline import profile
from audit_dsld_quantities import walk
from review_dsld_name_groups import snapshot,sha

VERSION='mesh-baseline-audit-v1'
RUN='20261028T062833838481Z'
V='http://id.nlm.nih.gov/mesh/vocab#'
TYPE='http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
LABEL='http://www.w3.org/2000/01/rdf-schema#label'

def triple_key(b):
    return tuple(json.dumps(b[k],sort_keys=True) for k in ['subject','predicate','object'])

def bindings(batches):
    return [b for batch in batches for page in batch['pages'] for b in page['response'].get('results',{}).get('bindings',[])]

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw);folder=raw/'mesh/runs'/RUN
    data=(folder/'collection.json').read_bytes();mb=(folder/'collection_manifest.json').read_bytes();c=json.loads(data);m=json.loads(mb);errors=[]
    def check(ok,code,detail=None):
        if not ok:errors.append({'code':code,'detail':detail})
    check(sha(data)==m['sha256'] and len(data)==m['bytes'],'manifest_mismatch')
    q=c['queries'];search=c['search_results'];index=c['candidate_record_index']
    check(set(q)==set(search)==set(index),'query_index_keys')
    prov=c['dsld_provenance'];check(sha((raw/'dsld/collection_manifest.json').read_bytes())==prov['manifest_sha256'],'dsld_manifest_changed')
    dsld={};expected=set()
    for lid,h in prov['label_sha256'].items():
        b=(raw/'dsld/labels'/f'label_{lid}.json').read_bytes();check(sha(b)==h,'source_label_hash',lid);dsld[lid]=json.loads(b)
        for pointer,row in walk(dsld[lid]['ingredientRows']):
            def dot(p):
                out=''
                for t in p.strip('/').split('/'):out+=('['+t+']') if t.isdigit() else ('.' if out else '')+t
                return out
            if (row.get('name') or '').strip():expected.add((lid,dot(pointer)))
            for i,f in enumerate(row.get('forms') or []):
                if (f.get('name') or '').strip():expected.add((lid,dot(pointer+f'/forms/{i}')))
    resolution=bindings(c['term_resolution_responses']);rdf=bindings(c['record_subgraph_responses'])
    term_records=defaultdict(set);term_links=defaultdict(list)
    for b in resolution:
        term=b['term']['value'];term_records[term].add(b['record']['value']);term_links[term].append({k:v['value'] for k,v in b.items()})
    for group in ['term_resolution_responses','record_subgraph_responses']:
        for i,batch in enumerate(c[group]):
            check(batch['complete'] and all(p['status']=='ok' for p in batch['pages']),'incomplete_batch',{'group':group,'index':i})
    unique={triple_key(b):b for b in rdf};subject_props=defaultdict(lambda:defaultdict(list))
    for b in unique.values():subject_props[b['subject']['value']][b['predicate']['value']].append(b['object'])
    def values(s,p):return [o['value'] for o in subject_props.get(s,{}).get(p,[])]
    record_ids=set(r for ids in index.values() for r in ids);types=Counter();record_views=[]
    for rid in sorted(record_ids):
        check(rid in subject_props,'record_without_subgraph',rid)
        t=values(rid,TYPE);types.update(x.rsplit('#',1)[-1] for x in t)
        view={'uri':rid,'types':t,'labels':values(rid,LABEL),'identifiers':values(rid,V+'identifier'),
              'preferred_concepts':values(rid,V+'preferredConcept'),'concepts':values(rid,V+'concept'),
              'tree_numbers':values(rid,V+'treeNumber'),'active':values(rid,V+'active'),
              'dates':{k:values(rid,V+k) for k in ['dateCreated','dateEstablished','dateIntroduced','dateRevised','lastUpdated']}}
        record_views.append(view)
    occurrences=[];paths=[];mapping=[];reused=defaultdict(list)
    for key,query in q.items():
        s=search[key];terms=s['term_uris']
        check(set(terms)=={r['resource'] for r in s['response']},'term_response_disagreement',key)
        resolved=set().union(*(term_records[t] for t in terms)) if terms else set()
        check(set(index[key])==resolved,'candidate_resolution_disagreement',key)
        check(all(term_records[t] for t in terms),'unresolved_entry_term',key)
        check(s['status']==('matched' if terms else 'not_found'),'search_status_disagreement',key)
        for req in s['requests']:
            check(req['params'].get('label')==query['query'] and req['params'].get('match')=='exact','request_policy_disagreement',key)
        for o in query['occurrences']:
            occurrences.append(o);paths.append((o['dsld_id'],o['json_path']))
            try:r=resolve_path(dsld[o['dsld_id']],o['json_path'])
            except (KeyError,ValueError,IndexError,TypeError):check(False,'unresolved_dsld_path',o);continue
            check(r['name']==o['name'] and r['ingredientId']==o['ingredient_id'] and o['name'] in query['variants'],'source_occurrence_mismatch',o)
        for rid in index[key]:reused[rid].append(key)
        mapping.append({'query_key':key,'query':query['query'],'variants':query['variants'],'status':s['status'],
            'term_uris':terms,'resolution_links':[link for t in terms for link in term_links[t]],
            'candidates':[{'uri':rid,'labels':values(rid,LABEL),'types':values(rid,TYPE)} for rid in index[key]],
            'review_status':'unreviewed' if index[key] else 'no_candidate_returned'})
    check(set(paths)==expected and len(paths)==len(set(paths)),'source_scope_coverage')
    check(record_ids=={b['record']['value'] for b in resolution},'resolved_record_set')
    relations=[]
    for b in unique.values():
        if b['predicate']['value'] in {V+k for k in ['broaderDescriptor','broaderConcept','narrowerConcept','relatedConcept','mappedTo','preferredMappedTo','seeAlso','treeNumber']}:
            relations.append({'subject':b['subject']['value'],'predicate':b['predicate']['value'],'object':b['object'],
                              'target_description_in_snapshot':b['object']['value'] in subject_props})
    shared=[{'uri':rid,'labels':values(rid,LABEL),'query_keys':keys} for rid,keys in reused.items() if len(keys)>1]
    labels_index=defaultdict(set)
    for s,ps in subject_props.items():
        for pred in [LABEL,V+'prefLabel',V+'altLabel']:
            for v in ps.get(pred,[]):labels_index[v['value'].casefold().strip()].add(s)
    shared_labels=[{'text':label,'subject_uris':sorted(ids)} for label,ids in labels_index.items() if len(ids)>1]
    summary={'source_labels':len(dsld),'query_groups':len(q),'source_name_variants':sum(len(v['variants']) for v in q.values()),
        'source_occurrences_verified':len(occurrences),'search_status':dict(Counter(s['status'] for s in search.values())),
        'single_record_queries':sum(len(v)==1 for v in index.values()),'ambiguous_queries':sum(len(v)>1 for v in index.values()),
        'candidate_links':sum(map(len,index.values())),'candidate_records':len(record_ids),'record_types':dict(types),
        'shared_records_across_queries':len(shared),'unique_entry_terms':len({t for s in search.values() for t in s['term_uris']}),
        'unique_rdf_subjects':len(subject_props),'unique_rdf_statements':len(unique),'repeated_triple_occurrences':len(rdf)-len(unique),
        'subjects_with_scope_notes':sum(bool(ps.get(V+'scopeNote')) for ps in subject_props.values()),
        'records_missing_labels':sum(not v['labels'] for v in record_views),'records_missing_identifiers':sum(not v['identifiers'] for v in record_views),
        'records_without_tree_numbers':sum(not v['tree_numbers'] for v in record_views),
        'shared_label_groups_across_rdf_subjects':len(shared_labels),'relation_counts':dict(Counter(r['predicate'].split('#')[-1] for r in relations)),
        'relation_targets_without_description':sum(not r['target_description_in_snapshot'] for r in relations),
        'possibly_truncated_queries':sum(s['possibly_truncated'] for s in search.values()),
        'available_years_start':c['source_metadata_start']['response'],'available_years_end':c['source_metadata_end']['response'],
        'available_years_unchanged':c['source_metadata_start']['response']==c['source_metadata_end']['response'],
        'collection_started':c['started_at_utc'],'collection_finished':c['finished_at_utc'],
        'mechanical_errors':len(errors),'approved_mappings':0,'records_merged':0}
    profiles=profile({'query':list(q.values()),'occurrence':occurrences,'search_result':list(search.values()),
        'term_resolution_binding':resolution,'rdf_binding':rdf,'rdf_object':[b['object'] for b in rdf],
        'record_projection':record_views})
    policy=['Offline audit of saved MeSH lookup/SPARQL responses, not a live vocabulary validation.',
        'Terms (T), concepts (M), descriptors (D) and supplementary records (C) have distinct roles. Shared labels across them do not imply duplicate entities.',
        'Candidate links resolve exact entry-term searches through concepts to records. Exact lookup and a single record do not establish ingredient/formulation equivalence.',
        'Repeated RDF triples can be repeated batch/context statements; compare subject, predicate and full RDF object including datatype/language. Preserve source contexts before graph deduplication.',
        'Tree numbers and broader relations describe vocabulary hierarchy, not clinical efficacy, chemical equivalence or product identity. Supplementary records need not have descriptor tree numbers.',
        'Relation targets outside the captured descriptions are not necessarily invalid links. This is a bounded subgraph, not the entire MeSH hierarchy.',
        'The current endpoint and unchanged available-year metadata do not pin every response to a verified immutable release. Retain request/capture timestamps and raw metadata.',
        'Scope notes are terminology descriptions, not independently validated clinical claims. No missing units, doses, ratings or indications are inferred.',
        'Query provenance covers DSLD ingredients/nested rows/forms including co-ingredients; otheringredients are outside collection scope. No-match is not absence under all terms.']
    report={'summary':summary,'policy':policy,'errors':errors,'mapping_review':mapping,'record_projection':record_views,
        'shared_records':shared,'shared_labels':shared_labels,'relations':relations}
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),'field_profiles.json':(json.dumps(profiles,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# MeSH baseline audit','','```json',json.dumps(summary,indent=2),'```','']+['- '+p for p in policy])+'\n').encode()}
    if snapshot(raw)!=before:raise RuntimeError('Raw files changed')
    out=project/'data/processed/mesh'/(VERSION+'-'+sha(data+mb+Path(__file__).read_bytes())[:16])
    m={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'source_sha256':sha(data),'source_manifest_sha256':sha(mb),
        'raw_file_count':len(before),'raw_files_unchanged':True,'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing overwrite: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
