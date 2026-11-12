"""Read-only comparison of repeated DSLD names; no product identity decisions."""
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

VERSION = 'dsld-name-review-v1'
FIELDS = ['upcSku', 'productVersionCode', 'ingredientRows', 'otheringredients',
          'servingSizes', 'netContents', 'physicalState', 'statements', 'offMarket',
          'entryDate', 'events']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def snapshot(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and p.name != '.DS_Store'}

def compare(a, b):
    links = [{'from_label_id': str(s['id']), 'to_label_id': str(t['id']),
              'type': r['type']} for s, t in [(a,b), (b,a)]
             for r in s.get('labelRelationships', []) if str(r['labelId']) == str(t['id'])]
    # UPC/SKU text is retained exactly: no assumption that every value is a UPC.
    return {'label_ids': [str(a['id']), str(b['id'])],
            'differing_fields': [k for k in FIELDS if a.get(k) != b.get(k)],
            'same_nonempty_upc_sku': bool(a.get('upcSku', '').strip()) and a.get('upcSku') == b.get('upcSku'),
            'source_relationships': links,
            'all_fields_except_id_and_src_equal':
                {k:v for k,v in a.items() if k not in ('id','src')} ==
                {k:v for k,v in b.items() if k not in ('id','src')}}

def review(project):
    project = Path(project)
    before = snapshot(project/'data/raw')
    from preprocess_dsld import preprocess
    inventory_dir, _ = preprocess(project)
    inventory = [json.loads(line) for line in (inventory_dir/'label_inventory.jsonl').read_text().splitlines()]
    labels = {r['dsld_id']: r for r in inventory}
    groups = json.loads((inventory_dir/'repeated_name_groups.json').read_text())
    reviews = []
    for group in groups:
        members = [labels[i]['raw_label'] for i in group['label_ids']]
        pairs = [compare(a,b) for a,b in itertools.combinations(members, 2)]
        differences = sorted({k for pair in pairs for k in pair['differing_fields']})
        link_types = sorted({r['type'] for p in pairs for r in p['source_relationships']})
        reviews.append({**group, 'review_status': 'comparison_complete_identity_pending',
            'differing_fields': differences, 'source_relationship_types': link_types,
            'on_market_label_count': sum(type(r.get('offMarket')) is int and r['offMarket']==0 for r in members),
            'labels': [{'label_id':str(r['id']), 'source':labels[str(r['id'])]['source'],
                       **{k:r.get(k) for k in FIELDS if k not in ('ingredientRows','statements','otheringredients')},
                       'ingredientRows':r.get('ingredientRows'), 'otheringredients':r.get('otheringredients')}
                      for r in members], 'pair_comparisons':pairs})
    pairs = [p for g in reviews for p in g['pair_comparisons']]
    summary = {'group_count':len(reviews), 'label_count':sum(len(g['label_ids']) for g in reviews),
        'pair_count':len(pairs), 'groups_with_field_differences':dict(Counter(k for g in reviews for k in g['differing_fields'])),
        'groups_with_source_relationship_type':dict(Counter(k for g in reviews for k in g['source_relationship_types'])),
        'groups_without_internal_source_relationship':sum(not g['source_relationship_types'] for g in reviews),
        'groups_with_multiple_on_market_labels':sum(g['on_market_label_count']>1 for g in reviews),
        'pairs_equal_except_id_and_src':sum(p['all_fields_except_id_and_src_equal'] for p in pairs),
        'pairs_same_nonempty_upc_sku':sum(p['same_nonempty_upc_sku'] for p in pairs),
        'records_merged':0, 'records_removed':0,
        'limitations':['Field comparisons use exact stored JSON, including list order and formatting; differences do not prove reformulation.',
                      'Source relationship annotations are retained as evidence, not independently validated identity decisions.',
                      'Entry dates are DSLD entry dates, not release dates or a verified revision sequence.',
                      'No unit conversion, synonym normalization, or ingredient equivalence is attempted.',
                      'Only exact repeated brand/name groups are examined; duplicates across different names are outside scope.']}
    lines = ['# DSLD repeated-name review', '',
             'All labels are retained. Comparison is complete; product identity decisions remain pending.', '',
             'Exact field differences can reflect formatting, order, daily-value metadata, or genuine content changes. They do not establish reformulation.', '',
             'DSLD entry dates do not establish revision order. Source relationship annotations may coexist or conflict with the stored fields.', '',
             '## Summary', '', '```json', json.dumps(summary,indent=2), '```', '',
             '## Group comparisons', '',
             '| Brand / product | Label IDs | On-market in snapshot | Source relationships within group | Differing fields |',
             '|---|---|---:|---|---|']
    def safe(s): return str(s).replace('|','\\|').replace('\n',' ')
    for g in reviews:
        lines.append('| '+' | '.join(map(safe,[g['brand_name']+' / '+g['product_name'], ', '.join(g['label_ids']),g['on_market_label_count'], '; '.join(g['source_relationship_types']) or 'None', ', '.join(g['differing_fields']) or 'None of the compared fields']))+' |')
    lines += ['', '## Recommended next decision', '',
              'Keep a separate label entity for every DSLD ID. Preserve source-asserted relationships with provenance. Do not merge products by name, UPC/SKU, or entry date alone. Review ingredient/serving differences before assigning canonical product or formulation IDs.', '',
              'The JSON companion contains source hashes, per-label ingredient/serving/package details, and every pair comparison. Raw labels remain the reference for all other fields.', '']
    inputs = {n:sha((inventory_dir/n).read_bytes()) for n in ['label_inventory.jsonl','repeated_name_groups.json']}
    out = project/'data/processed/dsld'/ (VERSION+'-'+sha(json.dumps(inputs,sort_keys=True).encode())[:16])
    payloads = {'review.json':(json.dumps({'summary':summary,'groups':reviews},ensure_ascii=False,indent=2)+'\n').encode(),
                'review.md':'\n'.join(lines).encode()}
    manifest = {'rules_version':VERSION, 'script_sha256':sha(Path(__file__).read_bytes()),
                'source_inventory':str(inventory_dir.relative_to(project)), 'inputs':inputs,
                'files':{k:{'sha256':sha(v),'bytes':len(v)} for k,v in payloads.items()},
                'raw_file_count':len(before), 'raw_files_unchanged':before==snapshot(project/'data/raw')}
    if not manifest['raw_files_unchanged']: raise RuntimeError('Raw files changed')
    payloads['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if out.exists():
        for name,data in payloads.items():
            if (out/name).read_bytes()!=data: raise ValueError('Refusing to overwrite changed review: '+name)
    else:
        out.mkdir(parents=True)
        for name,data in payloads.items(): (out/name).write_bytes(data)
    return out, summary

if __name__ == '__main__':
    out, summary = review(Path(__file__).resolve().parents[1])
    print(out)
    print(json.dumps(summary,indent=2))
