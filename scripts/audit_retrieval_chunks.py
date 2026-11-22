"""Read-only audit of existing chunks; optional exact MedCPT tokenizer measurement."""
import argparse,csv,hashlib,json,re,statistics
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/full-graph-concepts-v1-08c99550a0fa0f86aca9'

def sha(b):return hashlib.sha256(b).hexdigest()
def stats(values):
    s=sorted(values)
    return dict(min=min(s),median=statistics.median(s),p95=s[int(.95*(len(s)-1))],max=max(s)) if s else {}
def word_spans(text):return list(re.finditer(r'\S+',text))
def run(tokenizer_dir, root=ROOT):
    from tokenizers import Tokenizer
    import tokenizers
    root=Path(root);td=Path(tokenizer_dir);metadata=json.loads((td/'metadata.json').read_text())
    for name,h in metadata['files'].items():assert sha((td/name).read_bytes())==h
    tok=Tokenizer.from_file(str(td/'tokenizer.json'));tok.no_truncation();tok.no_padding()
    limit=json.loads((td/'config.json').read_text())['max_position_embeddings']
    graph=root/GRAPH;manifest=json.loads((graph/'manifest.json').read_text());inputs={}
    def read(p):
        b=(root/p).read_bytes();inputs[p]=sha(b);return b
    for f in ['nodes/SourcePassage.csv','nodes/LabelAssertion.csv','nodes/ProductLabel.csv','nodes/ClinicalClaim.csv']:
        assert sha(read(GRAPH+'/'+f))==manifest['files'][f]
    csv.field_size_limit(10000000)
    def nodes(kind):
        with (graph/'nodes'/(kind+'.csv')).open() as h:
            for r in csv.DictReader(h):yield r['id'],json.loads(r['properties_json'])
    raw={s:{r['id']:r for r in map(json.loads,read('data/raw/'+s+'/records.jsonl').splitlines())} for s in ['natmedpro','reddit']}
    allrows=[];groups=defaultdict(list);duplicates=defaultdict(list);source_words={};section_spans={}
    for node,p in nodes('SourcePassage'):
        f=p['original_fields'];s=p['source'];text=f.get('text') or '';record=raw[s][f['record_id']]
        source_text=record['sections'][f['section_index']]['text'] if s=='natmedpro' else record['text']
        k=(s,f['record_id'],f['section_index']);words=word_spans(source_text);start=f['word_start'];end=start+len(text.split())
        matches=' '.join(source_text.split()[start:end])==text
        a=words[start].start() if words and start<len(words) else 0
        b=words[end-1].end() if words and 0<end<=len(words) else 0
        prefix=' | '.join(str(x) for x in [f.get('title'),f.get('section')] if x)
        row=dict(node_id=node,source=s,record_id=f['record_id'],section=f.get('section'),section_index=f['section_index'],
            words=len(text.split()),declared_word_count=f.get('word_count'),declared_chunk_words=f.get('chunk_words'),
            word_start=start,word_end=end,source_char_start=a,source_char_end=b,source_slice_verified=matches,
            text_tokens=len(tok.encode(text).ids),title_section_pair_tokens=len(tok.encode(prefix,text).ids),
            source_url_present=bool(f.get('source_url')),text_sha256=sha(text.encode()),mention_scope=f.get('mention_scope'),
            empty=not text.strip(),short_under_20_words=len(text.split())<20,
            preview=text[:220],source_excerpt_exact=source_text[a:b]==text)
        # Heuristics are screening signals, not linguistic/clinical judgments.
        row['starts_after_nonterminal_word']=start>0 and not re.search(r'[.!?][\)\]"\u201d\u2019]*$',words[start-1].group())
        row['ends_before_nonterminal_boundary']=end<len(words) and end>0 and not re.search(r'[.!?][\)\]"\u201d\u2019]*$',words[end-1].group())
        row['boundary_preview']=(source_text[max(0,b-90):b]+' | NEXT: '+source_text[b:b+100]) if end<len(words) else None
        allrows.append(row);groups[k].append(row);source_words[k]=len(words);section_spans[k]=source_text
        duplicates[(s,row['text_sha256'])].append(node)
    labels={node:p for node,p in nodes('ProductLabel')}
    for node,p in nodes('LabelAssertion'):
        if p.get('kind')!='label_statement':continue
        f=p['original_fields'];text=f.get('notes') or '';label=labels[p['snapshot_id']]
        prefix=label['attributes'].get('fullName') or ''
        row=dict(node_id=node,source='dsld',record_id=p['snapshot_id'],section=f.get('type'),words=len(text.split()),
            text_tokens=len(tok.encode(text).ids),title_section_pair_tokens=len(tok.encode(prefix,text).ids),
            text_sha256=sha(text.encode()),empty=not text.strip(),short_under_20_words=len(text.split())<20,preview=text[:220])
        allrows.append(row);duplicates[('dsld',row['text_sha256'])].append(node)
    gaps=[];overlaps=[]
    for k,rows in groups.items():
        cursor=0;missing=overlap=0
        for r in sorted(rows,key=lambda r:r['word_start']):
            missing+=max(0,r['word_start']-cursor);overlap+=max(0,min(cursor,r['word_end'])-r['word_start']);cursor=max(cursor,r['word_end'])
        missing+=max(0,source_words[k]-cursor)
        if missing:gaps.append(dict(source=k[0],record_id=k[1],section_index=k[2],missing_words=missing))
        if overlap:overlaps.append(dict(source=k[0],record_id=k[1],section_index=k[2],overlap_words=overlap))
    absent=[]
    for s,records in raw.items():
        for rid,r in records.items():
            sections=r['sections'] if s=='natmedpro' else [{'text':r['text']}]
            for idx,sec in enumerate(sections):
                if sec['text'].strip() and (s,rid,idx) not in groups:absent.append(dict(source=s,record_id=rid,section_index=idx))
    claim_rows=[]
    for node,p in nodes('ClinicalClaim'):
        span=p['source_span'];f=p['original_fields'];idx=int(span['pointer'].split('/sections/')[1].split('/')[0]);k=('natmedpro',p['record_id'],idx)
        text=section_spans[k];a,b=span['start'],span['end']
        while a<b and text[a].isspace():a+=1
        while b>a and text[b-1].isspace():b-=1
        containing=[r for r in groups[k] if r['source_char_start']<=a and r['source_char_end']>=b]
        anchors=p['field_support_anchors'];all_supported=[]
        for r in containing:
            if all(x['source_span']['file']==span['file'] and x['source_span']['pointer']==span['pointer'] and r['source_char_start']<=x['source_span']['start'] and r['source_char_end']>=x['source_span']['end'] for x in anchors):all_supported.append(r)
        claim_rows.append(dict(node_id=node,ingredient=f['ingredient']['name'],claim_type=f['claim_type'],excerpt_contained_in_one_passage=bool(containing),excerpt_and_all_field_anchors_in_one_passage=bool(all_supported),source_span=span,claim_preview=f['claim_text'][:220]))
    summary={}
    for s in ['natmedpro','reddit','dsld']:
        rs=[r for r in allrows if r['source']==s];dups=[v for (src,h),v in duplicates.items() if src==s and len(v)>1]
        summary[s]=dict(records=len(rs),words=stats([r['words'] for r in rs]),text_tokens=stats([r['text_tokens'] for r in rs]),
            title_section_pair_tokens=stats([r['title_section_pair_tokens'] for r in rs]),text_over_limit=sum(r['text_tokens']>limit for r in rs),
            pair_over_limit=sum(r['title_section_pair_tokens']>limit for r in rs),empty=sum(r['empty'] for r in rs),short_under_20_words=sum(r['short_under_20_words'] for r in rs),
            duplicate_text_groups=len(dups),duplicate_occurrences_beyond_first=sum(len(v)-1 for v in dups),
            sections=dict(Counter(r['section'] for r in rs)))
        if s!='dsld':summary[s].update(source_slice_failures=sum(not r['source_slice_verified'] for r in rs),
            declared_word_count_mismatches=sum(r['words']!=r['declared_word_count'] for r in rs),
            boundary_flags=sum(r['ends_before_nonterminal_boundary'] for r in rs),
            missing_urls=sum(not r['source_url_present'] for r in rs),mention_scopes=dict(Counter(str(r['mention_scope']) for r in rs)))
    report=dict(graph=GRAPH,tokenizer={**metadata,'tokenizers_version':tokenizers.__version__,'limit_from_model_config':limit},
        input_templates=dict(text_only='encode(text), with special tokens',context_pair='encode(title + section, text), with special tokens; DSLD uses product fullName as first sequence. Illustrative retrieval template, not finalized.'),
        sources=summary,word_coverage_gaps=gaps,word_overlaps=overlaps,unrepresented_nonempty_source_sections=absent,
        claims=dict(total=len(claim_rows),not_contained_in_single_passage=sum(not r['excerpt_contained_in_one_passage'] for r in claim_rows),
            not_contained_with_all_field_anchors=sum(not r['excerpt_and_all_field_anchors_in_one_passage'] for r in claim_rows)),
        limitations=['Boundary flags are punctuation-based heuristics, not verified sentence or clinical errors.',
        'Word-slice checks preserve whitespace-normalized text; char bounds refer to original source and are derived for this audit.',
        'Token counts apply to the pinned tokenizer with truncation disabled; no vectors generated.',
        'A claim split across passages may be recoverable via graph/context retrieval; this is not lost source evidence.',
        'Exact duplicate text is not necessarily a duplicate record; preserve all source links.',
        'No chunks, source files or graph were modified.'],inputs=inputs)
    out=root/'reports/retrieval_chunk_audit';out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,rows in [('items',allrows),('claim_context',claim_rows)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    for p,h in inputs.items():assert sha((root/p).read_bytes())==h
    print(json.dumps({k:v for k,v in report.items() if k in ['claims','word_coverage_gaps','unrepresented_nonempty_source_sections']},indent=2))
    for s,r in summary.items():print(s,json.dumps({k:v for k,v in r.items() if k not in ['sections','mention_scopes']}))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer-dir',required=True);args=p.parse_args();run(args.tokenizer_dir)
