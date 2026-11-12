"""Complete DSLD baseline profiling; candidates are not identity decisions."""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from review_dsld_name_groups import snapshot, sha

VERSION='dsld-baseline-audit-v1'
PLACEHOLDERS={'np','tbd','n/a','na','unknown','not available','not applicable','not present'}

def normalized_name(value):
    if not isinstance(value,str):return ''
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())

def value_state(value):
    if value is None:return 'null'
    if isinstance(value,str):
        if not value.strip():return 'empty_string'
        if normalized_name(value) in PLACEHOLDERS:return 'placeholder_token_candidate'
    if isinstance(value,(dict,list)) and not value:return 'empty_container'
    return 'populated'

def profile(objects):
    result={}
    for path,items in sorted(objects.items()):
        fields={}
        for key in sorted(set().union(*(row.keys() for row in items))):
            vals=[r[key] for r in items if key in r]
            fields[key]={'parent_objects':len(items),'missing_key':len(items)-len(vals),
                'states':dict(Counter(value_state(v) for v in vals)),
                'types':dict(Counter(type(v).__name__ for v in vals)),
                'placeholder_examples':sorted({v for v in vals if isinstance(v,str) and value_state(v)=='placeholder_token_candidate'})}
        result[path]=fields
    return result

def collect_objects(value,path,objects):
    if isinstance(value,dict):
        objects[path].append(value)
        for k,v in value.items():collect_objects(v,path+'/'+k,objects)
    elif isinstance(value,list):
        for v in value:collect_objects(v,path+'[]',objects)

def ingredient_occurrences(label):
    def rows(items,path,role):
        for i,r in enumerate(items or []):
            ptr=f'{path}/{i}'
            yield {'label_id':str(label['id']),'pointer':ptr,'role':role,
                   **{k:r.get(k) for k in ['ingredientId','name','uniiCode','ingredientGroup']}}
            yield from rows(r.get('forms'),ptr+'/forms',role+'_form')
            yield from rows(r.get('nestedRows'),ptr+'/nestedRows',role+'_nested')
    yield from rows(label.get('ingredientRows'),'/ingredientRows','listed_ingredient')
    yield from rows((label.get('otheringredients') or {}).get('ingredients'),'/otheringredients/ingredients','other_ingredient')

def duplicate_candidates(labels,keyfn):
    groups=defaultdict(list)
    for l in labels:
        key=keyfn(l)
        if key and (not isinstance(key,tuple) or all(key)):groups[key].append(l)
    return [{'key':list(k) if isinstance(k,tuple) else k,
             'label_ids':[str(l['id']) for l in members],
             'raw_names':[{'label_id':str(l['id']),'brand':l.get('brandName'),'name':l.get('fullName')} for l in members],
             'crosses_exact_name_groups':len({(l.get('brandName'),l.get('fullName')) for l in members})>1}
            for k,members in groups.items() if len(members)>1]

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw)
    data=(raw/'dsld/collection.json').read_bytes();collection=json.loads(data);labels=collection['labels'];ids={str(l['id']) for l in labels}
    if len(ids)!=len(labels) or collection['record_count']!=len(labels):raise ValueError('Collection IDs/count inconsistent')
    sources={};objects=defaultdict(list)
    for l in labels:
        p=raw/'dsld/labels'/f"label_{l['id']}.json";b=p.read_bytes()
        if json.loads(b)!=l:raise ValueError('Individual record mismatch')
        sources[str(l['id'])]={'file':str(p.relative_to(project)),'sha256':sha(b)}
        collect_objects(l,'label',objects)
    profiles=profile(objects)
    names=duplicate_candidates(labels,lambda l:(normalized_name(l.get('brandName')),normalized_name(l.get('fullName'))))
    skus=duplicate_candidates(labels,lambda l:re.sub(r'\s+','',l.get('upcSku') or ''))
    occurrences=[o for l in labels for o in ingredient_occurrences(l)]
    id_names=defaultdict(set);name_ids=defaultdict(set);id_occ=defaultdict(list)
    for o in occurrences:
        iid=o['ingredientId'];name=normalized_name(o['name'])
        if iid is not None:
            id_names[str(iid)].add(o['name'] or '');id_occ[str(iid)].append(o)
            if name:name_ids[name].add(str(iid))
    identifier_review={'ingredient_occurrences':len(occurrences),
        'distinct_ingredient_ids':len(id_names),
        'missing_ingredient_id_occurrences':[o for o in occurrences if o['ingredientId'] is None],
        'ids_with_multiple_raw_names':[{'ingredient_id':i,'names':sorted(ns),'occurrences':id_occ[i]} for i,ns in id_names.items() if len(ns)>1],
        'normalized_names_with_multiple_ids':[{'normalized_name':n,'ingredient_ids':sorted(v)} for n,v in name_ids.items() if len(v)>1],
        'unii_states':dict(Counter(value_state(o['uniiCode']) for o in occurrences)),
        'unii_nonempty_not_10_alphanumeric':[o for o in occurrences if o['uniiCode'] and not re.fullmatch('[A-Za-z0-9]{10}',str(o['uniiCode']))],
        'upc_sku_present_labels':sum(bool((l.get('upcSku') or '').strip()) for l in labels),
        'upc_sku_compact_length_counts':dict(Counter(len(re.sub(r'\s+','',l['upcSku'])) for l in labels if (l.get('upcSku') or '').strip()))}
    relationships=[]
    for l in labels:
        for i,r in enumerate(l.get('labelRelationships') or []):
            relationships.append({'source_label_id':str(l['id']),'target_label_id':str(r.get('labelId')),
                                  'type':r.get('type'),'pointer':f'/labelRelationships/{i}',
                                  'target_in_sample':str(r.get('labelId')) in ids,
                                  'self_reference':str(l['id'])==str(r.get('labelId'))})
    edges={(r['source_label_id'],r['target_label_id'],r['type']) for r in relationships}
    rel_summary={'occurrences':len(relationships),'distinct_directed_relationships':len(edges),
        'internal_occurrences':sum(r['target_in_sample'] for r in relationships),
        'external_occurrences':sum(not r['target_in_sample'] for r in relationships),
        'distinct_external_targets':len({r['target_label_id'] for r in relationships if not r['target_in_sample']}),
        'self_references':sum(r['self_reference'] for r in relationships),
        'internal_edges_without_same_type_reverse':sum((b,a,t) not in edges for a,b,t in edges if b in ids),
        'type_counts':dict(Counter(r['type'] for r in relationships))}
    dates=[];date_issues=[];event_dates=[]
    for l in labels:
        for ptr,v in [('/entryDate',l.get('entryDate'))]+[(f'/events/{i}/date',e.get('date')) for i,e in enumerate(l.get('events') or [])]:
            try:d=date.fromisoformat(v)
            except (TypeError,ValueError):date_issues.append({'label_id':str(l['id']),'pointer':ptr,'value':v});continue
            (dates if ptr=='/entryDate' else event_dates).append(d.isoformat())
        for e in l.get('events') or []:
            if e.get('type')=='Date entered into DSLD' and e.get('date')!=l.get('entryDate'):
                date_issues.append({'label_id':str(l['id']),'code':'entry_event_disagrees','entryDate':l.get('entryDate'),'event':e})
    coverage={};examples={}
    predicates={'directions':lambda t:'Directions' in t,'precautions':lambda t:t.startswith('Precautions'),
        'allergy_precautions':lambda t:'Allergies' in t,'pregnancy_nursing_medication_precautions':lambda t:'Pregnant or Nursing or Prescription' in t,
        'contains_statements':lambda t:t=='Formula re: Contains','does_not_contain_statements':lambda t:t=='Formulation re: Does NOT Contain',
        'general_statements':lambda t:t=='General Statements: All Other Content','fda_disclaimer':lambda t:t=='FDA Disclaimer Statement'}
    for category,predicate in predicates.items():
        found=[{'label_id':str(l['id']),'pointer':f'/statements/{i}','statement':s} for l in labels for i,s in enumerate(l.get('statements') or []) if predicate(s.get('type') or '') and isinstance(s.get('notes'),str) and s['notes'].strip()]
        coverage[category]={'statements':len(found),'labels':len({f['label_id'] for f in found})};examples[category]=found[:3]
    coverage['claim_classification_codes']={'labels':sum(bool(l.get('claims')) for l in labels)}
    coverage['other_ingredient_list']={'labels':sum(bool((l.get('otheringredients') or {}).get('ingredients')) for l in labels)}
    coverage['other_ingredient_free_text']={'labels':sum(bool(((l.get('otheringredients') or {}).get('text') or '').strip()) for l in labels)}
    summary={'labels':len(labels),'object_paths_profiled':len(profiles),'field_profiles':sum(len(v) for v in profiles.values()),
        'normalized_name_candidate_groups':len(names),'new_normalized_name_groups_beyond_exact_names':sum(g['crosses_exact_name_groups'] for g in names),
        'shared_compact_upc_sku_groups':len(skus),'shared_upc_sku_groups_crossing_exact_names':sum(g['crosses_exact_name_groups'] for g in skus),
        'ingredient_occurrences':len(occurrences),'distinct_ingredient_ids':len(id_names),
        'ingredient_ids_with_multiple_names':len(identifier_review['ids_with_multiple_raw_names']),
        'normalized_ingredient_names_with_multiple_ids':len(identifier_review['normalized_names_with_multiple_ids']),
        'unii_shape_review_occurrences':len(identifier_review['unii_nonempty_not_10_alphanumeric']),
        'upc_sku_present_labels':identifier_review['upc_sku_present_labels'],'relationships':rel_summary,
        'entry_date_min':min(dates) if dates else None,'entry_date_max':max(dates) if dates else None,
        'entry_year_counts':dict(Counter(d[:4] for d in dates)),'date_issue_count':len(date_issues),'content_coverage':coverage,
        'records_merged':0,'records_corrected':0}
    policy=['Profiles count missing keys relative to objects actually present at each nested path; empty parent containers do not contribute child objects.',
        'Placeholder tokens are candidates only. Literal Not Present or Not Applicable can be meaningful; no global null replacement is made. Zero and False are populated values.',
        'Normalized names use Unicode NFKC, case folding and whitespace only. No punctuation removal, fuzzy matching or semantic equivalence is asserted.',
        'UPC/SKU comparisons remove whitespace only, preserve leading zeros, and do not verify barcode ownership, check digits or product identity.',
        'Ingredient-ID/name and UNII-shape findings are profiling candidates, not approved cross-source identities or authoritative registry validation.',
        'Relationship targets outside the 400-label sample are unresolved locally, not necessarily broken links. Asymmetric source annotations need not be errors.',
        'Entry dates describe DSLD entry, not manufacture, revision, expiry or current availability.',
        'Statement coverage measures text availability, not accuracy, effectiveness, complete safety coverage or independent evidence. Claim codes are classification metadata, not extracted clinical claims.',
        'Baseline structural/quality profiling is now sufficient for shared-schema discussion together with previous quantity and duplicate audits. Label-image verification, clinical review, full semantic deduplication and source vocabulary definitions remain unresolved.']
    dictionary={'label':'One source label record, not necessarily one unique commercial product.',
        'id':'DSLD label identifier; use source namespace.', 'upcSku':'Source UPC/SKU text; not assumed unique or externally verified.',
        'ingredientRows':'Listed ingredient tree; preserve nested membership and attached quantities/forms.',
        'ingredientRows[].quantity':'Reported amount/operator/unit and serving reference; daily-value metadata is separate.',
        'forms':'Ingredient forms attached to the parent ingredient; do not assign parent amount independently to each form.',
        'otheringredients':'Separate ingredient list/free text; do not infer absent amounts or combine with active-dose rows.',
        'statements':'Typed source label text (directions, precautions, general claims etc.); preserve original wording.',
        'claims':'Source claim classification codes/descriptions, not independently validated clinical facts.',
        'servingSizes':'Serving sizes, daily-serving bounds and notes; source nulls remain unknown.',
        'labelRelationships':'Source-asserted label links with relation type; targets can lie outside the sample.',
        'entryDate/events':'Source entry date and typed events; not a clinical freshness guarantee.',
        'offMarket':'Source market-status flag; retain historical labels.',
        'remaining_fields':'Observed JSON types/states are documented in field_profiles.json; business semantics not established by profiling alone.'}
    report={'summary':summary,'policy':policy,'field_dictionary':dictionary,'identifier_review':identifier_review,
        'duplicate_candidates':{'normalized_names':names,'shared_compact_upc_sku':skus},'relationships':relationships,
        'date_issues':date_issues,'statement_examples':examples}
    payloads={'audit.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),
        'field_profiles.json':(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# DSLD baseline completion','','## Summary','','```json',json.dumps(summary,indent=2),'```','','## Scope and limits','']+['- '+p for p in policy]+['','## Field meanings','']+['- **'+k+'**: '+v for k,v in dictionary.items()])+'\n').encode()}
    fingerprint=sha(json.dumps({'source':sha(data),'script':sha(Path(__file__).read_bytes()),'labels':sources},sort_keys=True).encode())
    out=project/'data/processed/dsld'/(VERSION+'-'+fingerprint[:16])
    if snapshot(raw)!=before:raise RuntimeError('Raw data changed')
    manifest={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'collection_sha256':sha(data),'sources':sources,
        'raw_file_count':len(before),'raw_files_unchanged':True,'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing to overwrite edited output: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,report=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(report['summary'],indent=2))
