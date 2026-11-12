"""Compare stored ingredient/serving evidence; never infer formulation identity."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from review_dsld_name_groups import snapshot, sha
from preprocess_dsld import preprocess

VERSION = 'dsld-ingredient-review-v1'

def normalized(value):
    # Whitespace only; no case folding, synonym mapping or unit conversion.
    if isinstance(value, str): return re.sub(r'\s+', ' ', value).strip()
    if isinstance(value, list): return [normalized(v) for v in value]
    if isinstance(value, dict): return {k:normalized(v) for k,v in value.items()}
    return value

def canon(value): return json.dumps(value, sort_keys=True, ensure_ascii=False)

def ordered(items): return sorted(items, key=canon)

def quantities(row, dv=False):
    return ordered([normalized({k:v for k,v in q.items() if (k=='dailyValueTargetGroup') == dv})
                    for q in row.get('quantity', [])])

def forms(row):
    return ordered([normalized({k:v for k,v in f.items()
                               if k not in ('order','ingredientId','category','ingredientGroup')})
                    for f in row.get('forms', [])])

def core(rows):
    return ordered([{'name':normalized(r.get('name')), 'forms':forms(r),
                     'quantities':quantities(r), 'nested':core(r.get('nestedRows', []))}
                    for r in rows])

def serving(label):
    # Keep order because ingredient quantities refer to servingSizeOrder.
    return ordered([normalized({k:v for k,v in s.items() if k!='notes'})
                    for s in label.get('servingSizes',[])])

def indexed(rows, parent=(), result=None):
    if result is None: result=defaultdict(list)
    for r in rows:
        path=parent+(normalized(r.get('name')),)
        result[path].append(r)
        indexed(r.get('nestedRows',[]),path,result)
    return result

def compare(a,b):
    ar,br=a.get('ingredientRows',[]),b.get('ingredientRows',[])
    ai,bi=indexed(ar),indexed(br)
    details=[]; flags=[]
    added=sorted(set(bi)-set(ai),key=canon);removed=sorted(set(ai)-set(bi),key=canon)
    if added or removed: flags.append('ingredient_name_or_hierarchy_difference')
    for path in sorted(set(ai)&set(bi),key=canon):
        if len(ai[path])!=1 or len(bi[path])!=1:
            flags.append('ambiguous_repeated_ingredient_path');continue
        x,y=ai[path][0],bi[path][0]
        for key,fn in [('amount_or_basis',quantities),('form',forms),('daily_value',lambda r:quantities(r,True))]:
            left,right=fn(x),fn(y)
            if left!=right:
                flags.append(key+'_difference')
                details.append({'ingredient_path':list(path),'field':key,'left':left,'right':right})
    if serving(a)!=serving(b):flags.append('serving_definition_difference')
    if a.get('otheringredients')!=b.get('otheringredients'):flags.append('other_ingredients_raw_difference')
    note_fields=['description','notes']
    notes=lambda idx: ordered([{'path':list(p),'values':[normalized({k:r.get(k) for k in note_fields}) for r in rs]} for p,rs in idx.items()])
    if notes(ai)!=notes(bi):flags.append('ingredient_notes_or_description_difference')
    if [normalized(s.get('notes')) for s in a.get('servingSizes',[])] != [normalized(s.get('notes')) for s in b.get('servingSizes',[])]: flags.append('serving_notes_difference')
    same_core=core(ar)==core(br)
    return {'label_ids':[str(a['id']),str(b['id'])], 'flags':sorted(set(flags)),
        'raw_ingredient_rows_equal':ar==br, 'ingredient_core_equal':same_core,
        'serving_core_equal':serving(a)==serving(b),
        'added_name_paths_in_right':[list(p) for p in added],
        'removed_name_paths_in_right':[list(p) for p in removed],
        'matched_ingredient_differences':details,
        'serving_left':a.get('servingSizes'), 'serving_right':b.get('servingSizes'),
        'status':'core_difference_needs_review' if not same_core or serving(a)!=serving(b) else 'same_compared_core_identity_unresolved'}

def review(project):
    import itertools
    project=Path(project); before=snapshot(project/'data/raw')
    inventory,_=preprocess(project)
    rows=[json.loads(l) for l in (inventory/'label_inventory.jsonl').read_text().splitlines()]
    lookup={r['dsld_id']:r for r in rows}
    groups=json.loads((inventory/'repeated_name_groups.json').read_text())
    results=[]
    for g in groups:
        pairs=[compare(lookup[a]['raw_label'],lookup[b]['raw_label']) for a,b in itertools.combinations(g['label_ids'],2)]
        results.append({**g,'review_status':'ingredient_serving_comparison_complete_identity_pending',
            'flags':sorted({f for p in pairs for f in p['flags']}),
            'pairs':pairs,
            'all_pairs_same_compared_core':all(p['ingredient_core_equal'] and p['serving_core_equal'] for p in pairs)})
    pairs=[p for g in results for p in g['pairs']]
    summary={'groups':len(results),'labels':sum(len(g['label_ids']) for g in results),'pairs':len(pairs),
             'groups_all_pairs_same_compared_core':sum(g['all_pairs_same_compared_core'] for g in results),
             'groups_with_core_difference':sum(not g['all_pairs_same_compared_core'] for g in results),
             'pair_status_counts':dict(Counter(p['status'] for p in pairs)),
             'group_flag_counts':dict(Counter(f for g in results for f in g['flags'])),
             'pair_flag_counts':dict(Counter(f for p in pairs for f in p['flags'])),
             'pairs_raw_ingredients_differ_but_compared_core_equal':sum(not p['raw_ingredient_rows_equal'] and p['ingredient_core_equal'] for p in pairs),
             'records_removed':0,'records_merged':0}
    policy=['Whitespace is collapsed; names and units otherwise remain exact. No synonym matching or unit conversion.',
        'Ingredient/form/quantity list order is ignored while multiplicity and nested ingredient membership are preserved.',
        'Compared ingredient core contains names, forms (excluding source IDs/categories), and quantity/operator/unit/serving-basis fields. Daily values, ingredient notes, IDs/categories/aliases and row order are outside this core.',
        'Serving comparison retains serving order, quantities, units, daily-serving ranges and inSFB. Notes are flagged separately; missing and empty notes can differ.',
        'Amount/form/daily-value differences are reported only for uniquely matched ingredient-name paths. Added/removed names may be renamings; ambiguous repeated paths are not paired arbitrarily.',
        'Other ingredients are flagged by raw JSON equality only. Equal compared core does not establish identical formulations, products or excipients.',
        'Label IDs in each pair define left/right; this is not chronological revision order. No dates or source relationships prove causality.']
    lines=['# DSLD ingredient and serving comparison','', '## Comparison rules','']+['- '+p for p in policy]+['','## Summary','','```json',json.dumps(summary,indent=2),'```','','## Groups','','| Brand / product | Label IDs | All pairs have equal compared core | Review flags |','|---|---|---|---|']
    for g in results:
        vals=[g['brand_name']+' / '+g['product_name'],', '.join(g['label_ids']),str(g['all_pairs_same_compared_core']),', '.join(g['flags']) or 'None']
        lines.append('| '+' | '.join(v.replace('|','\\|').replace('\n',' ') for v in vals)+' |')
    lines+=['','## Evidence for ingredient amount, form and serving differences','', 'Name additions/removals and daily-value details for every pair are included in the JSON report. Amount and form comparisons below use uniquely matched name paths.','']
    for g in results:
        relevant=[p for p in g['pairs'] if any(f in p['flags'] for f in ['amount_or_basis_difference','form_difference','serving_definition_difference'])]
        if not relevant:continue
        lines+=['### '+g['brand_name']+' / '+g['product_name'],'']
        for p in relevant:
            lines+=['Labels '+ ' → '.join(p['label_ids'])+' (left → right; not chronology):','']
            for d in p['matched_ingredient_differences']:
                if d['field']=='daily_value':continue
                lines+=['- '+ ' / '.join(str(x) for x in d['ingredient_path'])+' — '+d['field']+': `'+canon(d['left'])+'` → `'+canon(d['right'])+'`']
            if not p['serving_core_equal']:lines+=['- Serving definitions: `'+canon(p['serving_left'])+'` → `'+canon(p['serving_right'])+'`']
            lines+=['']
    inputs={n:sha((inventory/n).read_bytes()) for n in ['label_inventory.jsonl','repeated_name_groups.json']}
    out=project/'data/processed/dsld'/(VERSION+'-'+sha(canon(inputs).encode())[:16])
    payloads={'review.json':(json.dumps({'summary':summary,'policy':policy,'groups':results},ensure_ascii=False,indent=2)+'\n').encode(), 'review.md':('\n'.join(lines)+'\n').encode()}
    unchanged=before==snapshot(project/'data/raw')
    if not unchanged:raise RuntimeError('Raw data changed')
    manifest={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'source_inventory':str(inventory.relative_to(project)),'inputs':inputs,
        'sources':{i:lookup[i]['source'] for g in groups for i in g['label_ids']},'raw_file_count':len(before),'raw_files_unchanged':unchanged,
        'files':{k:{'sha256':sha(v),'bytes':len(v)} for k,v in payloads.items()}}
    payloads['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if out.exists():
        for name,data in payloads.items():
            if (out/name).read_bytes()!=data:raise ValueError('Refusing to overwrite changed output: '+name)
    else:
        out.mkdir(parents=True)
        for name,data in payloads.items():(out/name).write_bytes(data)
    return out,summary

if __name__=='__main__':
    out,summary=review(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(summary,indent=2))
