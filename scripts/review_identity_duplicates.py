"""Reproducible, source-preserving duplicate decisions for the full collection."""
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
import json, sys, tempfile, os, shutil
from preprocess_pilot import sha, encode, key
ROOT=Path(__file__).resolve().parents[1]
SPEC='schemas/identity_deduplication_decisions_v1.json'
NAME='data/processed/dsld/dsld-name-review-v1-0baa34b90a1fe69e/review.json'
CORE='data/processed/dsld/dsld-ingredient-review-v1-0baa34b90a1fe69e/review.json'
IMPORTED='data/processed/imported/natmed-reddit-prepared-v1-b85118347d2f8de1a1ea'
AUDITS={'natmedpro':'data/processed/natmedpro/natmed-baseline-audit-v1-b548c344b8c0a9b7/audit.json','reddit':'data/processed/reddit/reddit-baseline-audit-v1-058aea355a5bb848/audit.json'}

def direct_links(a,b):
    result=[]
    for left,right in [(a,b),(b,a)]:
        for i,r in enumerate(left.get('labelRelationships',[])):
            if str(r.get('labelId'))==str(right['id']):
                result.append(dict(from_label_id=str(left['id']),to_label_id=str(right['id']),source_type=r['type'],pointer=f'/labelRelationships/{i}'))
    return result

def compare_labels(a,b):
    fields=sorted(k for k in set(a)|set(b) if k not in {'id','src'} and (k not in a or k not in b or a[k]!=b[k]))
    links=direct_links(a,b)
    return dict(differing_fields=fields,payload_equal_except_id_src=not fields,direct_source_relationships=links,
                action='retain_separate_source_related_labels' if links else 'retain_separate_labels',
                identity_status='unresolved_product_equivalence',canonical_merge=False)

def repeated(rows,fn):
    groups=defaultdict(list)
    for r in rows:groups[encode(fn(r['original_fields']))].append(r['id'])
    return sorted(sorted(v) for v in groups.values() if len(v)>1)

def duplicate_key(category):
    if category in {'record_text','passage_text'}:return lambda r:r['text']
    if category=='claim_text':return lambda r:r['claim_text']
    if category=='claim_source_span_and_type':return lambda r:[r['source'][k] for k in ['record_id','section_index','start','end']]+[r['claim_type']]
    excluded={'id'} if category=='claim_payload_except_id' else {'id','native_id'}
    return lambda r:{k:v for k,v in r.items() if k not in excluded}

def content_decision(source,category,members):
    originals=[m['original_fields'] for m in members]
    fields=sorted(set().union(*(r.keys() for r in originals))-{'id','native_id'})
    differences=[k for k in fields if len({encode([k in r,r.get(k)]) for r in originals})>1]
    return dict(id=key('duplicate_review',source,category,*sorted(m['id'] for m in members)),source=source,category=category,
                member_ids=sorted(m['id'] for m in members),context_difference_fields=differences,
                action='retain_distinct_claims' if category.startswith('claim') else 'retain_distinct_source_records_or_passages',
                text_reuse_eligible=category.endswith('_text'),canonical_merge=False,clinical_approval=False,
                reason='Repeated text/span does not establish the same assertion, source occurrence, author or user experience.',
                evidence=[dict(id=m['id'],provenance=m['provenance']) for m in members])

def build(root=ROOT):
    root=Path(root);inputs={}
    def read(p,expected=None):
        b=(root/p).read_bytes();h=sha(b)
        if expected is not None:assert h==expected,p
        inputs[p]=h;return b
    def obj(p):return json.loads(read(p))
    obj(SPEC)
    # Check prepared artifacts against their immutable manifest, not just current file names.
    manifest=obj(IMPORTED+'/manifest.json')
    for p,h in manifest['files'].items():read(IMPORTED+'/'+p,h if isinstance(h,str) else h['sha256'])
    names=obj(NAME);cores={g['group_id']:g for g in obj(CORE)['groups']}
    pairs=[];groups=[];raw={}
    for gi,g in enumerate(names['groups']):
        for l in g['labels']:
            raw[l['label_id']]=json.loads(read(l['source']['file'],l['source']['sha256']))
        cp={tuple(sorted(p['label_ids'])):p for p in cores[g['group_id']]['pairs']}
        checked_pairs=[]
        for a,b in combinations(g['label_ids'],2):
            result=compare_labels(raw[a],raw[b]);prior=next(p for p in g['pair_comparisons'] if set(p['label_ids'])=={a,b})
            assert result['payload_equal_except_id_src']==prior['all_fields_except_id_and_src_equal']
            core=cp[tuple(sorted([a,b]))]
            row=dict(id=key('label_pair_review',*sorted([a,b])),group_id=g['group_id'],label_ids=[a,b],**result,
                     ingredient_core_equal=core['ingredient_core_equal'],serving_core_equal=core['serving_core_equal'],
                     audit_flags=core['flags'],evidence=dict(name_audit=NAME,group_pointer=f'/groups/{gi}',ingredient_audit=CORE,
                     labels=[l['source'] for l in g['labels'] if l['label_id'] in {a,b}]),graph_applied=False)
            pairs.append(row);checked_pairs.append(row)
        groups.append(dict(id=g['group_id'],brand=g['brand_name'],product=g['product_name'],label_ids=g['label_ids'],
                           pair_count=len(checked_pairs),all_pairs_same_compared_core=cores[g['group_id']]['all_pairs_same_compared_core'],
                           source_related_pairs=sum(bool(p['direct_source_relationships']) for p in checked_pairs),
                           action='review_group_only_not_canonical_product',canonical_merge=False))
    content=[];inventory=[];blobs={};bindings=[];duplicate_counts={}
    for source,auditpath in AUDITS.items():
        audit=obj(auditpath);tables={}
        for t in ['records','passages','claims']:
            tables[t]=[json.loads(l) for l in read(f'{IMPORTED}/{source}/{t}.jsonl').splitlines()]
            ids=[r['id'] for r in tables[t]];assert len(ids)==len(set(ids)),(source,t)
            inventory.append(dict(source=source,table=t,records=len(ids),unique_ids=len(set(ids)),identity_policy='retain_source_scoped_id',merged=0))
        duplicate_counts[source]={}
        for cat,expected in audit['duplicates'].items():
            table='claims' if cat.startswith('claim') else 'passages' if cat.startswith('passage') else 'records'
            rows=tables[table];lookup={r['id']:r for r in rows};actual=repeated(rows,duplicate_key(cat))
            assert actual==sorted(sorted(v) for v in expected),(source,cat,'saved audit no longer matches')
            duplicate_counts[source][cat]=len(actual)
            for ids in actual:
                members=[lookup[i] for i in ids];decision=content_decision(source,cat,members);decision['audit_file']=auditpath;content.append(decision)
                if decision['text_reuse_eligible']:
                    field='claim_text' if table=='claims' else 'text';text=members[0]['original_fields'][field]
                    # This index is not an independent evidence count and does not merge any source entities.
                    bid='exact_text:'+sha(text.encode('utf-8'));blobs[bid]=dict(id=bid,text=text,identity_scope='exact_utf8_text_only')
                    for m in members:bindings.append(dict(id=key('text_binding',source,table,m['id']),text_id=bid,source=source,table=table,record_id=m['id'],field=field,provenance=m['provenance']))
    report=dict(dsld_groups=len(groups),dsld_labels_in_groups=len(raw),dsld_pairs=len(pairs),
                dsld_groups_same_compared_core=sum(g['all_pairs_same_compared_core'] for g in groups),
                dsld_pairs_with_direct_source_links=sum(bool(p['direct_source_relationships']) for p in pairs),
                dsld_payload_duplicate_pairs=sum(p['payload_equal_except_id_src'] for p in pairs),
                duplicate_groups=duplicate_counts,exact_text_blobs=len(blobs),text_bindings=len(bindings),
                entity_merges=0,graph_updated=False,clinical_approvals=0,
                checks=dict(saved_duplicate_groups_recomputed=True,source_label_hashes_verified=True,prepared_manifest_verified=True,unique_source_ids=True),
                limitations=['DSLD review covers the 70 existing repeated-name groups, not exhaustive cross-name product equivalence.',
                            'Core/serving comparison retains the audit definition; unit equivalence alone cannot prove product identity.',
                            'Direct source relationships are attributed annotations, not canonical equivalence or transitive links.',
                            'Shared text is storage/index reuse only; distinct claims and Reddit contexts remain separate.',
                            'Terminology namespace/native-ID reuse remains as prepared; shared concept mappings never merge source ingredients or products.'])
    return dict(dsld_group_decisions=groups,dsld_pair_decisions=pairs,content_duplicate_decisions=content,source_identity_inventory=inventory,exact_text_blobs=list(blobs.values()),exact_text_bindings=bindings),report,inputs

def run(root=ROOT):
    root=Path(root);tables,report,inputs=build(root)
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in ['scripts/review_identity_duplicates.py','scripts/preprocess_pilot.py','tests/test_review_identity_duplicates.py']},python=sys.version.split()[0])
    build_id='identity-duplicates-v1-'+sha(encode(signature).encode())[:20]
    files={name+'.jsonl':(''.join(encode(r)+'\n' for r in rows)).encode() for name,rows in tables.items()}
    files['validation_report.json']=(encode(report)+'\n').encode();files['input_manifest.json']=(encode(signature)+'\n').encode()
    files['manifest.json']=(encode(dict(build_id=build_id,spec=SPEC,files={p:sha(b) for p,b in files.items()}))+'\n').encode()
    out=root/'data/processed/identity'/build_id
    if out.exists():
        assert {p.name for p in out.iterdir()}==set(files)
        for p,b in files.items():assert (out/p).read_bytes()==b
    else:
        out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.identity-review-',dir=out.parent))
        try:
            for p,b in files.items():(tmp/p).write_bytes(b)
            os.rename(tmp,out)
        except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
    for p,h in inputs.items():assert sha((root/p).read_bytes())==h
    print(out.relative_to(root));print(json.dumps(report,indent=2));return out,report
if __name__=='__main__':run()
