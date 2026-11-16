"""Add explicit DSLD navigation mentions; preserve all six sources' existing semantics."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,io,json,re,sys,os,tempfile,shutil
from preprocess_pilot import sha,encode,key
from validate_freeze_full_graph import load_graph,Graph,GRAPH,check_claim_support
ROOT=Path(__file__).resolve().parents[1]
SPEC='schemas/topic_navigation_v1.json'

def mentions(text,aliases):
    pattern=r'(?<!\w)(?:'+'|'.join(re.escape(a) for a in sorted(aliases,key=len,reverse=True))+r')(?!\w)'
    return [dict(start=m.start(),end=m.end(),text=m.group()) for m in re.finditer(pattern,text,re.I)]

def coverage(nodes,edges):
    g=Graph(nodes,edges);out=[]
    for n in nodes:
        if n['type']!='SupplementTopic':continue
        tid=n['id'];row=g.topic(n['properties']['name']);group=set();ingredient=set();title=set()
        for relation,dest in [('HAS_DECLARED_TOPIC',group),('INGREDIENT_NAME_MENTIONS_TOPIC',ingredient)]:
            for e in g.inc[(tid,relation)]:
                dest.update(x['start_id'] for x in g.inc[(e['start_id'],'DECLARES_OCCURRENCE')])
        title.update(e['start_id'] for e in g.inc[(tid,'LABEL_TITLE_MENTIONS_TOPIC')])
        row.update(group_labels=len(group),ingredient_name_labels=len(ingredient),title_labels=len(title),all_navigation_labels=len(group|ingredient|title),newly_reachable_labels=len((ingredient|title)-group))
        row['gaps']=[gap for gap in row['gaps'] if not (gap.startswith('No labels') and row['all_navigation_labels'])]
        out.append(row)
    return sorted(out,key=lambda r:r['topic'])

def validate_extension(nodes,old_edges,new_edges,added,aliases):
    assert len({e['id'] for e in new_edges})==len(new_edges)
    assert new_edges[:len(old_edges)]==old_edges,'Existing relationship modified'
    assert len(new_edges)==len(old_edges)+len(added)
    byid={n['id']:n for n in nodes};triples=set()
    for e in added:
        assert e['start_id'] in byid and e['end_id'] in byid
        triple=(e['start_id'],e['end_id'],e['type']);assert triple not in triples;triples.add(triple)
        assert not e['mapping_id'] and e['confidence']=='High'
        p=e['properties'];n=byid[e['start_id']];topic=byid[e['end_id']]['properties']['name']
        if e['type']=='LABEL_TITLE_MENTIONS_TOPIC':
            assert n['type']=='ProductLabel';actual=n['properties']['attributes']['fullName']
        else:
            assert e['type']=='INGREDIENT_NAME_MENTIONS_TOPIC' and n['type']=='IngredientOccurrence';actual=n['properties']['original_name']
        assert p['source_text']==actual and p['matches']==mentions(actual,aliases[topic]) and p['matches']
        assert p['identity_mapping'] is False and p['clinical_approval'] is False
        assert e['evidence_ids']==n['evidence_ids']
    return dict(existing_edges_unchanged=True,new_links_have_verified_literal_spans=True,no_identity_mapping_added=True,no_clinical_approval=True,unique_navigation_edges=True)

def build(root=ROOT):
    root=Path(root);nodes,old_edges,evidence,manifest=load_graph(root);spec=json.loads((root/SPEC).read_bytes());aliases=spec['aliases']
    topics={n['properties']['name']:n['id'] for n in nodes if n['type']=='SupplementTopic'};assert set(topics)==set(aliases)
    added=[];before=coverage(nodes,old_edges)
    for n in nodes:
        p=n['properties']
        if n['type']=='ProductLabel':text=p['attributes'].get('fullName','');field='attributes.fullName';relation='LABEL_TITLE_MENTIONS_TOPIC';role='product_title'
        elif n['type']=='IngredientOccurrence':text=p['original_name'];field='original_name';relation='INGREDIENT_NAME_MENTIONS_TOPIC';role=p['role']
        else:continue
        for topic,terms in aliases.items():
            hits=mentions(text,terms)
            if not hits:continue
            added.append(dict(id=key('topic_mention_edge',n['id'],topics[topic],relation),start_id=n['id'],end_id=topics[topic],type=relation,mapping_id='',confidence='High',evidence_ids=n['evidence_ids'],properties=dict(rule='explicit-source-name-v1',source_field=field,source_role=role,source_text=text,matches=hits,identity_mapping=False,clinical_approval=False,scope='Literal source text navigation only; does not verify material content, equivalence, viability, strain, dose or efficacy')))
    added.sort(key=lambda e:e['id']);edges=old_edges+added;checks=validate_extension(nodes,old_edges,edges,added,aliases)
    after=coverage(nodes,edges)
    counts=Counter(e['type'] for e in edges)
    audits=dict(dsld=dict(added_title_mentions=sum(e['type']=='LABEL_TITLE_MENTIONS_TOPIC' for e in added),added_ingredient_mentions=sum(e['type']=='INGREDIENT_NAME_MENTIONS_TOPIC' for e in added)),natmed=dict(source_topic_links=counts['HAS_SOURCE_TOPIC'],pending_claim_links=counts['HAS_PENDING_CLAIM'],changed=0),reddit=dict(direct_mentions=counts['MENTIONS_TOPIC'],inherited_context=counts['INHERITED_THREAD_TOPIC'],changed=0),terminology=dict(by_source=dict(Counter(e['properties']['decision'].get('target_source') for e in old_edges if e['mapping_id'] and e['properties']['decision'].get('target_source'))),changed=0))
    # Prove full-graph expansion did not alter source support, status or ingredient identity.
    checks.update(check_claim_support(root,nodes))
    report=dict(status='passed_with_documented_limitations',base_graph=GRAPH,new_edges=len(added),nodes=len(nodes),edges=len(edges),checks=checks,source_audit=audits,before=before,after=after,limitations=['High confidence means literal text match only. Qualifying statements such as iron-free remain in the original text; this is not a contains-ingredient assertion.','Aliases are bounded explicit names, not a taxonomy or exhaustive synonym list.','Species-only probiotic inference remains unapproved.','Existing pending/Low/no-candidate mappings and all clinical review restrictions remain unchanged.','Existing frozen baseline remains intact; this is a separate navigation revision.'])
    return nodes,edges,added,report,manifest

def run(root=ROOT):
    root=Path(root);nodes,edges,added,report,base=build(root)
    stream=io.StringIO(newline='');fields=['id','start_id','end_id','type','mapping_id','confidence','evidence_ids','properties_json'];w=csv.DictWriter(stream,fieldnames=fields);w.writeheader()
    for e in sorted(edges,key=lambda e:e['id']):w.writerow({**{k:e[k] for k in fields if k not in {'evidence_ids','properties_json'}},'evidence_ids':encode(e['evidence_ids']),'properties_json':encode(e['properties'])})
    # All old node/provenance/review files are copied byte-for-byte into the new standalone graph.
    files={p:(root/GRAPH/p).read_bytes() for p in base['files'] if p not in {'relationships/relationships.csv','input_manifest.json','validation_report.json'}}
    files['relationships/relationships.csv']=stream.getvalue().encode()
    files['review/topic_navigation_decisions.jsonl']=(''.join(encode(e)+'\n' for e in added)).encode()
    files['validation_report.json']=(encode(report)+'\n').encode()
    inputs=json.loads((root/GRAPH/'input_manifest.json').read_bytes())['inputs'];inputs=dict(inputs)
    inputs[GRAPH+'/manifest.json']=sha((root/GRAPH/'manifest.json').read_bytes());inputs[SPEC]=sha((root/SPEC).read_bytes())
    for name,h in base['files'].items():inputs[GRAPH+'/'+name]=h
    signature=dict(inputs=inputs,code={p:sha((root/p).read_bytes()) for p in ['scripts/expand_topic_navigation.py','scripts/validate_freeze_full_graph.py','scripts/preprocess_pilot.py','tests/test_expand_topic_navigation.py']},python=sys.version.split()[0])
    files['input_manifest.json']=(encode(signature)+'\n').encode()
    meta=dict(version='full-graph-navigation-v1',base_graph=GRAPH,counts={**base['counts'],'edges':len(edges),'navigation_edges_added':len(added)},node_types=base['node_types'],edge_types=dict(Counter(e['type'] for e in edges)),validation=report['checks'],files={p:sha(b) for p,b in sorted(files.items())})
    files['manifest.json']=(encode(meta)+'\n').encode();out=root/'data/graph'/('full-graph-navigation-v1-'+sha(files['manifest.json'])[:20])
    write_immutable(out,files)
    # Freeze the navigation revision by pinning every output file, with the source audit and coverage report.
    freeze=dict(graph=str(out.relative_to(root)),graph_manifest_sha256=sha(files['manifest.json']),graph_files=meta['files'],status=report['status'],clinical_approval=False,scope='Navigation revision of the frozen POC data baseline; not clinical validation')
    release_files={'freeze_manifest.json':(encode(freeze)+'\n').encode(),'validation_report.json':files['validation_report.json']}
    release=root/'data/graph'/('poc-navigation-release-v1-'+sha(release_files['freeze_manifest.json'])[:20]);write_immutable(release,release_files)
    for name,h in inputs.items():assert sha((root/name).read_bytes())==h,name
    print(out.relative_to(root));print(release.relative_to(root));print(json.dumps(dict(added=report['new_edges'],sources=report['source_audit']),indent=2));return out,release,report

def write_immutable(out,files):
    if out.exists():
        assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}==set(files)
        for p,b in files.items():assert (out/p).read_bytes()==b
        return
    tmp=Path(tempfile.mkdtemp(prefix='.navigation-',dir=out.parent))
    try:
        for p,b in files.items():(tmp/p).parent.mkdir(parents=True,exist_ok=True);(tmp/p).write_bytes(b)
        os.rename(tmp,out)
    except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
if __name__=='__main__':run()
