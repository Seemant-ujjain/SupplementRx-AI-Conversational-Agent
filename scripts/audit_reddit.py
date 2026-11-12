"""Offline Reddit baseline/structural validation, never clinical claim validation."""
import json
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from audit_dsld_baseline import collect_objects, profile
from review_dsld_name_groups import snapshot,sha

VERSION='reddit-baseline-audit-v1'

def record_issues(r):
    issues=[]
    for k in ['id','native_id','source_url','text','content_hash','record_type','source_created_at','collected_at']:
        if not isinstance(r.get(k),str) or not r[k].strip():issues.append('missing_or_invalid_'+k)
    if r.get('source')!='reddit' or r.get('evidence_role')!='user_report':issues.append('source_or_evidence_role')
    if r.get('id')!='reddit:'+str(r.get('native_id')):issues.append('native_identity')
    typ=r.get('record_type');native=r.get('native_id','')
    if typ not in ['post','comment'] or not native.startswith('t3_' if typ=='post' else 't1_'):issues.append('record_type_identity')
    if not isinstance(r.get('supplements'),list):issues.append('supplements_type')
    if r.get('mention_scope') not in ['own_text','thread_context']:issues.append('mention_scope')
    if isinstance(r.get('text'),str) and sha(r['text'].encode())!=r.get('content_hash'):issues.append('text_hash')
    for k in ['source_created_at','collected_at','first_collected_at']:
        try:
            dt=datetime.fromisoformat(r[k].replace('Z','+00:00'))
            if dt.tzinfo is None:issues.append('timezone_missing_'+k)
        except (KeyError,ValueError,TypeError):issues.append('timestamp_'+k)
    parsed=urlparse(r.get('source_url',''))
    if parsed.scheme not in ['http','https'] or parsed.hostname not in ['reddit.com','www.reddit.com','old.reddit.com']:issues.append('source_url')
    return issues

def passage_valid(p,r):
    try:
        words=r['text'].split();a=p['word_start'];n=p['word_count']
        return (type(a) is int and type(n) is int and a>=0 and n>0 and a+n<=len(words)
            and p['section_index']==0 and p['section']=='discussion'
            and p['text']==' '.join(words[a:a+n]) and p['source_content_hash']==r['content_hash']
            and all(p.get(k)==r.get(k) for k in ['source_url','source','evidence_role','record_type','mention_scope','thread_id','parent_id','supplements']))
    except (KeyError,TypeError):return False

def groups(rows,key):
    d=defaultdict(list)
    for r in rows:d[key(r)].append(r['id'])
    return [v for v in d.values() if len(v)>1]

def run(project):
    project=Path(project);raw=project/'data/raw';before=snapshot(raw);base=raw/'reddit'
    def read(name):return [json.loads(l) for l in (base/name).read_text().splitlines() if l.strip()]
    records=read('records.jsonl');passages=read('upstream_derived/passages.jsonl');nodes=read('upstream_derived/kg_nodes.jsonl');edges=read('upstream_derived/kg_edges.jsonl')
    errors=[]
    def check(ok,code,detail=None):
        if not ok:errors.append({'code':code,'detail':detail})
    manifest=json.loads((base/'collection_manifest.json').read_text())
    for name,meta in manifest['files'].items():
        b=(base/name).read_bytes();check(sha(b)==meta['sha256'] and len(b)==meta['bytes'],'manifest_mismatch',name)
    for typ,rows in [('record',records),('passage',passages),('node',nodes)]:check(len({r['id'] for r in rows})==len(rows),'duplicate_ids',typ)
    byid={r['id']:r for r in records};native={r['native_id']:r for r in records};postids={r['native_id'] for r in records if r['record_type']=='post'}
    check(len(native)==len(records),'duplicate_native_ids')
    missing_threads=[];missing_parents=[];own_text_unmatched=[];placeholder=[]
    for r in records:
        for issue in record_issues(r):check(False,issue,r['id'])
        if r['record_type']=='comment':
            if r.get('thread_id') not in postids:missing_threads.append(r['id'])
            if r.get('parent_id') not in native:missing_parents.append(r['id'])
            else:check(native[r['parent_id']].get('thread_id')==r.get('thread_id'),'parent_thread_disagreement',r['id'])
        if r['text'].strip().casefold() in ['[deleted]','[removed]']:placeholder.append(r['id'])
        terms=[t for s in r['supplements'] for t in s.get('matched_terms',[])]
        if r['mention_scope']=='own_text' and not any(t.casefold() in (r.get('title','')+' '+r['text']).casefold() for t in terms):own_text_unmatched.append(r['id'])
    for p in passages:check(p['record_id'] in byid and passage_valid(p,byid[p['record_id']]),'passage_source_binding',p['id'])
    check(set(byid)=={p['record_id'] for p in passages},'records_without_passages')
    nodeids={n['id'] for n in nodes}
    for e in edges:check(e['source'] in nodeids and e['target'] in nodeids,'missing_graph_endpoint',e)
    expected={('source:'+r['id'],'supplement:'+s['supplement'],'MENTIONS') for r in records for s in r['supplements']}
    actual={(e['source'],e['target'],e['type']) for e in edges};check(actual==expected,'graph_mentions_differ_from_source_topics')
    duplicates={'record_text':groups(records,lambda r:r['text']),'passage_text':groups(passages,lambda r:r['text']),
        'record_payload_except_identity':groups(records,lambda r:json.dumps({k:v for k,v in r.items() if k not in ['id','native_id']},sort_keys=True))}
    objects=defaultdict(list)
    for prefix,rows in [('record',records),('passage',passages)]:
        for r in rows:collect_objects(r,prefix,objects)
    profiles=profile(objects)
    dated={sub:{'records':len(rs),'earliest':min(r['source_created_at'] for r in rs),'latest':max(r['source_created_at'] for r in rs)}
        for sub in sorted({r['subreddit'] for r in records}) for rs in [[r for r in records if r['subreddit']==sub]]}
    summary={'records':len(records),'record_types':dict(Counter(r['record_type'] for r in records)), 'passages':len(passages),
        'evidence_roles':dict(Counter(r['evidence_role'] for r in records)), 'mention_scopes':dict(Counter(r['mention_scope'] for r in records)),
        'duplicate_text_groups':len(duplicates['record_text']),'records_in_duplicate_text_groups':sum(map(len,duplicates['record_text'])),
        'duplicate_passage_text_groups':len(duplicates['passage_text']), 'duplicate_record_payload_groups':len(duplicates['record_payload_except_identity']),
        'comments_without_saved_thread':len(missing_threads),'comments_without_saved_parent':len(missing_parents),
        'comments_with_no_parent_id':sum(r['record_type']=='comment' and not r.get('parent_id') for r in records),
        'comments_with_parent_id_outside_sample':sum(r['record_type']=='comment' and bool(r.get('parent_id')) and r['parent_id'] not in native for r in records),
        'comments_with_either_context_gap':len(set(missing_threads)|set(missing_parents)),
        'own_text_records_without_literal_alias_hit':len(own_text_unmatched),'deleted_removed_placeholder_records':len(placeholder),
        'graph_nodes':len(nodes),'graph_edges':len(edges),'graph_edge_types':dict(Counter(e['type'] for e in edges)),
        'duplicate_directed_graph_edges':len(edges)-len(actual),'subreddit_date_coverage':dated,
        'null_scores':sum(r.get('score') is None for r in records),'null_source_update_dates':sum(r.get('source_updated_at') is None for r in records),
        'structural_source_errors':len(errors),'claims_validated':0,'clinical_approvals':0,'records_merged':0}
    policy=['Local snapshot audit; no current Reddit re-fetch or new upstream inspection.',
        'No Reddit clinical-claim annotation schema is supplied in the imported artifacts. NatMed clinical_claim.schema.json is not applied to Reddit.',
        'Validation uses explicitly implemented local record/type/ID/URL/timestamp checks, source hashes, passage word windows/context, and graph endpoints/topic consistency. This is not an upstream formal JSON Schema certification.',
        'thread_context topics are inherited context, not evidence the comment itself mentions, used or benefited from the supplement. Literal alias-hit checks are lexical diagnostics only.',
        'Missing thread/parent records may result from bounded collection; retain dangling references rather than inventing context.',
        'Repeated text can occur in distinct discussions; do not merge posts/comments solely on text, and do not count overlapping passages as independent reports.',
        'Score and dates are source metadata, not reliability scores or proof of clinical truth. No ratings, indications, doses, interaction claims or effectiveness conclusions are inferred.',
        'Date ranges describe this bounded saved sample, not a representative or complete Reddit archive. Existing source metadata identifies search-alias normalization, not approved terminology mappings.',
        'Source text can contain personal information even when usernames are absent; POC selection must avoid adding author/profile data. No de-identification is performed by this audit.']
    report={'summary':summary,'policy':policy,'errors':errors,'duplicates':duplicates,
        'context_review':{'missing_threads':missing_threads,'missing_parents':missing_parents,'own_text_no_literal_alias':own_text_unmatched,'placeholder_records':placeholder},
        'source_repository':manifest['source_repository'],'source_commit':manifest['source_commit']}
    payloads={'audit.json':(json.dumps(report,indent=2)+'\n').encode(),'field_profiles.json':(json.dumps(profiles,indent=2)+'\n').encode(),
        'audit.md':('\n'.join(['# Reddit baseline and source-support audit','','```json',json.dumps(summary,indent=2),'```','']+['- '+p for p in policy])+'\n').encode()}
    if snapshot(raw)!=before:raise RuntimeError('Raw changed')
    inputs={str(p.relative_to(project)):sha(p.read_bytes()) for p in sorted(base.rglob('*')) if p.is_file()}
    out=project/'data/processed/reddit'/(VERSION+'-'+sha(json.dumps(inputs,sort_keys=True).encode()+Path(__file__).read_bytes())[:16])
    m={'rules_version':VERSION,'script_sha256':sha(Path(__file__).read_bytes()),'inputs':inputs,'raw_file_count':len(before),'raw_files_unchanged':True,
        'files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in payloads.items()}}
    payloads['manifest.json']=(json.dumps(m,indent=2)+'\n').encode()
    if out.exists():
        for n,b in payloads.items():
            if (out/n).read_bytes()!=b:raise ValueError('Refusing changed output: '+n)
    else:
        out.mkdir(parents=True)
        for n,b in payloads.items():(out/n).write_bytes(b)
    return out,report

if __name__=='__main__':
    out,r=run(Path(__file__).resolve().parents[1]);print(out);print(json.dumps(r['summary'],indent=2))
