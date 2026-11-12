"""Step 2: side-by-side source candidates; no accepted identities or transformations."""
import csv
import io
import json
from collections import Counter,defaultdict
from pathlib import Path
from audit_pubchem import resolve_path
from audit_mesh import bindings, TYPE, LABEL, V
from review_dsld_name_groups import snapshot, sha

VERSION='terminology-review-v1'
RUNS={'pubchem':'20261028T035149634190Z','rxnorm':'20261028T060819025094Z','mesh':'20261028T062833838481Z'}
FOCUS=['magnesium','magnesium citrate','magnesium taurinate','creatine','creatine monohydrate','creatine hcl','creatine hydrochloride','creatine citrate','ashwagandha','ashwagandha root extract','withania somnifera','turmeric','curcumin','probiotics','probiotic blend','lactobacillus acidophilus','lactobacillus acidophilus (ncfm)','fish oil','omega-3']

def signature(q):
    return json.dumps(q,sort_keys=True,ensure_ascii=False)

def flags_for(candidates,methods):
    flags=[]
    for source,rows in candidates.items():
        if not rows:flags.append(source+'_no_candidate')
        if len(rows)>1:flags.append(source+'_multiple_candidates')
    if methods['rxnorm']=='normalized':flags.append('rxnorm_normalized_search')
    return flags

def review(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw);sources={};inputs={}
    for src,run in RUNS.items():
        path=raw/src/'runs'/run/'collection.json';b=path.read_bytes();m=json.loads((path.parent/'collection_manifest.json').read_text())
        if sha(b)!=m['sha256'] or len(b)!=m['bytes']:raise ValueError('Source manifest mismatch: '+src)
        sources[src]=json.loads(b);inputs[src]={'file':str(path.relative_to(project)),'sha256':sha(b),'manifest_sha256':sha((path.parent/'collection_manifest.json').read_bytes())}
    pc,rx,mesh=(sources[k] for k in ['pubchem','rxnorm','mesh']);keys=set(pc['queries'])
    if any(set(s['queries'])!=keys for s in sources.values()):raise ValueError('Query inventories differ')
    for key in sorted(keys):
        if len({signature(s['queries'][key]) for s in sources.values()})!=1:raise ValueError('Query provenance differs: '+key)
    labels={}
    for src,s in sources.items():
        prov=s['dsld_provenance']
        if sha((raw/'dsld/collection_manifest.json').read_bytes())!=prov['manifest_sha256']:raise ValueError('DSLD manifest mismatch')
        for lid,h in prov['label_sha256'].items():
            b=(raw/'dsld/labels'/f'label_{lid}.json').read_bytes()
            if sha(b)!=h:raise ValueError('DSLD source changed')
            labels[lid]=json.loads(b)
    mprops=defaultdict(lambda:defaultdict(list))
    for b in bindings(mesh['record_subgraph_responses']):
        vals=mprops[b['subject']['value']][b['predicate']['value']]
        if b['object'] not in vals:vals.append(b['object'])
    def mv(uri,pred):return [o['value'] for o in mprops[uri].get(pred,[])]
    term_links=defaultdict(list)
    for b in bindings(mesh['term_resolution_responses']):term_links[b['term']['value']].append({k:v['value'] for k,v in b.items()})
    rows=[];occurrences=[];reverse=defaultdict(list)
    for key in sorted(keys):
        q=pc['queries'][key];ps=pc['search_results'][key];rs=rx['search_results'][key];ms=mesh['search_results'][key]
        candidates={'pubchem':[],'rxnorm':[],'mesh':[]}
        for cid in ps['cids']:
            p=pc['records'][str(cid)]['properties']
            candidates['pubchem'].append({'id':f'pubchem:CID:{cid}','source_id':cid,'name':p.get('Title'),
                'properties':p,'source_pointer':f'/records/{cid}/properties'})
        for rid in rs['rxcuis']:
            p=rx['records'][rid]['properties']['response']['properties']
            candidates['rxnorm'].append({'id':'rxnorm:'+rid,'source_id':rid,'name':p['name'],'term_type':p['tty'],
                'source_pointer':f'/records/{rid}/properties/response/properties'})
        for uri in mesh['candidate_record_index'][key]:
            concepts=sorted(set(mv(uri,V+'concept')+mv(uri,V+'preferredConcept')))
            candidates['mesh'].append({'id':uri,'source_id':uri.rsplit('/',1)[-1],'name':mv(uri,LABEL),
                'record_types':mv(uri,TYPE),'concept_scope_notes':[{'concept':c,'scope_notes':mv(c,V+'scopeNote')} for c in concepts if mv(c,V+'scopeNote')],
                'resolution_links':[link for t in ms['term_uris'] for link in term_links[t] if link['record']==uri]})
        methods={'pubchem':'saved_name_lookup','rxnorm':rs.get('match_method'),'mesh':ms.get('match_method')}
        flags=flags_for(candidates,methods)
        if len({o['ingredient_id'] for o in q['occurrences']})>1:flags.append('multiple_dsld_ingredient_ids_in_name_group')
        counts={src:len(cs) for src,cs in candidates.items()}
        coverage='none_returned' if not any(counts.values()) else ('all_three_have_candidates' if all(counts.values()) else 'partial_source_coverage')
        row={'query_key':key,'query':q['query'],'variants':q['variants'],'dsld_ingredient_ids':sorted({o['ingredient_id'] for o in q['occurrences']}),
            'occurrence_count':len(q['occurrences']),'occurrence_kinds':sorted({o['kind'] for o in q['occurrences']}),
            'candidates':candidates,'candidate_counts':counts,'methods':methods,
            'source_status':{'pubchem':ps['status'],'rxnorm':rs['status'],'mesh':ms['status']},
            'coverage':coverage,'review_flags':flags,'identity_decision':'unresolved_no_equivalence_asserted',
            'source_query_keys':{src:key for src in sources}}
        rows.append(row)
        for src,cs in candidates.items():
            for c in cs:reverse[(src,c['id'])].append(key)
        for o in q['occurrences']:
            original=resolve_path(labels[o['dsld_id']],o['json_path'])
            if original['name']!=o['name'] or original['ingredientId']!=o['ingredient_id']:raise ValueError('Occurrence mismatch')
            occurrences.append({'query_key':key,**o,'source_file':f"data/raw/dsld/labels/label_{o['dsld_id']}.json",
                'source_sha256':pc['dsld_provenance']['label_sha256'][o['dsld_id']]})
    summary={'query_groups':len(rows),'source_name_variants':sum(len(r['variants']) for r in rows),'source_labels':len(labels),
        'verified_occurrences':len(occurrences),'coverage_counts':dict(Counter(r['coverage'] for r in rows)),
        'one_candidate_in_every_source':sum(all(n==1 for n in r['candidate_counts'].values()) for r in rows),
        'queries_ambiguous_in_any_source':sum(any(n>1 for n in r['candidate_counts'].values()) for r in rows),
        'flag_counts':dict(Counter(f for r in rows for f in r['review_flags'])),
        'queries_with_multiple_dsld_ids':sum(len(r['dsld_ingredient_ids'])>1 for r in rows),
        'focus_queries':len([r for r in rows if r['query_key'] in FOCUS]),'approved_mappings':0,'merged_entities':0}
    policy=['The three query inventories, original variants and occurrence lists must match before side-by-side review. All source occurrences are rechecked against current saved DSLD records.',
        'Coverage/count flags are mechanical review routing, not scores of mapping accuracy or proof of agreement.',
        'All-three-single-candidate does not mean all three represent equivalent ingredients. Distinct namespace IDs and source roles remain separate.',
        'Shared candidates across differently named queries are retained for scope review, not transitive identity merging.',
        'No normalization of dose/identity, clinical approval, schema finalization or entity merging occurs in Step 2.']
    report={'summary':summary,'policy':policy,'queries':rows,'shared_candidates':[{'source':src,'candidate_id':cid,'query_keys':ks} for (src,cid),ks in sorted(reverse.items()) if len(ks)>1]}
    def csv_bytes(items,fields):
        b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(items);return b.getvalue().encode()
    flat=[]
    for r in rows:
        entry={'query_key':r['query_key'],'query':r['query'],'dsld_ingredient_ids':json.dumps(r['dsld_ingredient_ids']),
            'occurrence_count':r['occurrence_count'],'coverage':r['coverage'],'review_flags':'; '.join(r['review_flags']),'identity_decision':r['identity_decision']}
        for src in sources:
            entry[src+'_candidates']=json.dumps([{'id':c['id'],'name':c['name']} for c in r['candidates'][src]],ensure_ascii=False)
            entry[src+'_method']=r['methods'][src]
        flat.append(entry)
    occ_flat=[{**o,'search_categories':json.dumps(o['search_categories'])} for o in occurrences]
    payloads={'review.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),
        'query_comparison.csv':csv_bytes(flat,list(flat[0])), 'dsld_occurrences.csv':csv_bytes(occ_flat,list(occ_flat[0]))}
    if snapshot(raw)!=before:raise RuntimeError('Raw files changed')
    out=project/'data/processed/terminology'/(VERSION+'-'+sha(json.dumps(inputs,sort_keys=True).encode()+Path(__file__).read_bytes())[:16])
    manifest={'rules_version':VERSION,'inputs':inputs,'script_sha256':sha(Path(__file__).read_bytes()),'raw_file_count':len(before),'raw_files_unchanged':True,
        'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing modified output: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=review(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
