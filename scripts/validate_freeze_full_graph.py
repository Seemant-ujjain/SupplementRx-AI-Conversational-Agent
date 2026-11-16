"""Validate saved graph retrieval paths and freeze an explicitly limited POC release."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import csv,json,sys,os,tempfile,shutil
from preprocess_pilot import encode,sha
from export_full_graph import validate,MAPS,DSLD
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/full-graph-v1-2b5f825bd35bf70d7510'
SPEC='schemas/poc_release_validation_v1.json'
csv.field_size_limit(10_000_000)

def pointer(value,path):
    for part in path.strip('/').split('/') if path else []:
        part=part.replace('~1','/').replace('~0','~');value=value[int(part)] if isinstance(value,list) else value[part]
    return value

def load_graph(root=ROOT):
    root=Path(root);p=root/GRAPH;m=json.loads((p/'manifest.json').read_bytes())
    for name,h in m['files'].items():assert sha((p/name).read_bytes())==h,('Graph file changed',name)
    signature=json.loads((p/'input_manifest.json').read_bytes())
    for name,h in signature['inputs'].items():assert sha((root/name).read_bytes())==h,('Input changed',name)
    def convert(r):
        r['properties']=json.loads(r.pop('properties_json'));r['evidence_ids']=json.loads(r['evidence_ids']);return r
    nodes=[]
    for f in sorted((p/'nodes').glob('*.csv')):
        with f.open() as handle:nodes.extend(convert(r) for r in csv.DictReader(handle))
    with (p/'relationships/relationships.csv').open() as handle:edges=[convert(r) for r in csv.DictReader(handle)]
    evidence={r['id']:r for r in map(json.loads,(p/'provenance/evidence.jsonl').read_text().splitlines())}
    assert len(nodes)==m['counts']['nodes'] and len(edges)==m['counts']['edges']
    return nodes,edges,evidence,m

class Graph:
    def __init__(self,nodes,edges):
        self.nodes={n['id']:n for n in nodes};self.out=defaultdict(list);self.inc=defaultdict(list)
        for e in edges:self.out[(e['start_id'],e['type'])].append(e);self.inc[(e['end_id'],e['type'])].append(e)
    def topic(self,topic):
        t=next(n for n in self.nodes.values() if n['type']=='SupplementTopic' and n['properties']['name']==topic);tid=t['id']
        declarations=self.inc[(tid,'HAS_DECLARED_TOPIC')]
        label_edges=[e for d in declarations for e in self.inc[(d['start_id'],'DECLARES_OCCURRENCE')]]
        mono_edges=self.inc[(tid,'HAS_SOURCE_TOPIC')]
        claim_edges=[c for m in mono_edges for c in self.out[(m['start_id'],'HAS_PENDING_CLAIM')]]
        direct=self.inc[(tid,'MENTIONS_TOPIC')];context=self.inc[(tid,'INHERITED_THREAD_TOPIC')]
        kinds=Counter(self.nodes[e['end_id']]['properties']['original_fields']['claim_type'] for e in claim_edges)
        result=dict(topic=topic,labels=len({e['start_id'] for e in label_edges}),ingredient_occurrences=len(declarations),monographs=len(mono_edges),pending_claims=len(claim_edges),claim_types=dict(kinds),reddit_direct_records=len({e['start_id'] for e in direct}),reddit_context_only_records=len({e['start_id'] for e in context}),gaps=[])
        for k in ['labels','monographs','pending_claims','reddit_direct_records']:
            if not result[k]:result['gaps'].append('No '+k+' on these explicit topic paths')
        result['limitations']=['Topic navigation does not establish exact ingredient/formulation applicability.','Pending annotations are source retrieval, not clinical approval.','Reddit records are not verified personal-use or outcome evidence.']
        result['sample_paths']={}
        if declarations and label_edges:
            d=declarations[0];e=self.inc[(d['start_id'],'DECLARES_OCCURRENCE')][0];result['sample_paths']['label']=[e['id'],d['id']]
        if claim_edges:
            c=claim_edges[0];m=next(m for m in mono_edges if m['start_id']==c['start_id']);x=self.out[(c['end_id'],'SUPPORTED_BY_EXCERPT')][0]
            result['sample_paths']['pending_claim']=[m['id'],c['id'],x['id']]
        if direct:result['sample_paths']['reddit_direct']=[direct[0]['id']]
        if context:result['sample_paths']['reddit_context_excluded_from_direct']=[context[0]['id']]
        return result

def check_claim_support(root,nodes):
    cache={};claims=anchors=0
    def span_text(span):
        f=span['file']
        if f not in cache:
            b=(root/f).read_bytes();cache[f]=(sha(b),[json.loads(l) for l in b.splitlines()] if f.endswith('.jsonl') else json.loads(b))
        h,data=cache[f];assert h==span['sha256'];text=pointer(data,span['pointer'])
        assert 0<=span['start']<=span['end']<=len(text)
        return text[span['start']:span['end']]
    for n in nodes:
        if n['type']!='ClinicalClaim':continue
        c=n['properties'];assert span_text(c['source_span'])==c['original_fields']['source']['excerpt']==c['original_fields']['claim_text'];claims+=1
        for a in c['field_support_anchors']:assert span_text(a['source_span'])==a['source_text'];anchors+=1
    return dict(excerpts_verified=claims,field_anchors_verified=anchors)

def build(root=ROOT):
    root=Path(root);nodes,edges,evidence,manifest=load_graph(root);g=Graph(nodes,edges)
    def rows(p):return [json.loads(l) for l in (root/p).read_text().splitlines()]
    decisions={};expected={}
    for table in ['terminology_decisions','natmed_subject_decisions','additional_reviewed_proposals']:
        for d in rows(MAPS+'/'+table+'.jsonl'):
            if d['confidence']!='High':continue
            if table=='natmed_subject_decisions':
                target=next(n['id'] for n in nodes if n['type']=='MonographSubject' and n['properties']['monograph_id']==d['monograph_id'])
            elif table=='additional_reviewed_proposals':
                target=next(n['id'] for n in nodes if n['properties'].get('source')==d['target_source'] and n['properties'].get('native_id')==d['target_native_id'])
            else:target=d['target_record_id']
            expected[d['id']]=dict(start=d['origin_occurrence_id'],end=target,relation=d['proposed_relation'].upper());decisions[d['id']]=d
    checks=validate(nodes,edges,evidence,expected);checks.update(check_claim_support(root,nodes))
    # Independently resolve all exported prepared-row pointers and original DSLD value pointers.
    artifacts={r['id']:r for r in rows(DSLD+'/artifacts.jsonl')};byfile=defaultdict(list)
    for e in evidence.values():
        if 'artifact_id' in e:
            a=artifacts[e['artifact_id']];byfile[a['relative_path']].append((a['sha256'],e['locator']['pointer'],e))
        else:
            l=e['locator'];byfile[l['file']].append((l['sha256'],l['pointer'],e))
    resolved=0
    for f,items in byfile.items():
        b=(root/f).read_bytes();h=sha(b);data=[json.loads(l) for l in b.splitlines()] if f.endswith('.jsonl') else json.loads(b)
        for wanted,path,e in items:
            assert h==wanted;value=pointer(data,path)
            if 'original_value' in e:assert value==e['original_value']
            resolved+=1
    checks['evidence_pointers_verified']=resolved
    coverage=[g.topic(n['properties']['name']) for n in nodes if n['type']=='SupplementTopic'];coverage.sort(key=lambda r:r['topic'])
    assert len(coverage)==10
    cases=[dict(id='topic_'+r['topic'],question='Which saved product labels, NatMed annotations and Reddit discussions are available for '+r['topic']+'?',status='source_separated_retrieval_passed',result=r) for r in coverage]
    # Compare quantities only through actual label -> assertion edges; do not merge products.
    comparison=[]
    for native in ['25731','43261']:
        label=next(n for n in nodes if n['type']=='ProductLabel' and n['properties']['source_record']['native_id']==native)
        candidates=[g.nodes[e['end_id']] for e in g.out[(label['id'],'HAS_ASSERTION')]]
        a=next(n for n in candidates if n['properties']['original_fields'].get('ingredient_name')=='Creatine' and n['properties'].get('quantity_comparison'))
        p=a['properties'];assert p['quantity_comparison']['status']=='eligible_for_scoped_comparison'
        norm=next(t['normalized_value'] for t in p['transformations'] if t['destination_field']=='mass_comparison')
        comparison.append(dict(label_id=native,label_node_id=label['id'],assertion_id=a['id'],original_quantity=p['original_fields']['quantity'],normalized=norm,other_ingredients=[g.nodes[e['end_id']]['properties']['attributes'] for e in g.out[(label['id'],'DECLARES_OCCURRENCE')] if g.nodes[e['end_id']]['properties']['role']=='other_ingredient'],evidence_ids=a['evidence_ids']))
    a,b=comparison
    assert Decimal(a['normalized']['amount'])==Decimal(b['normalized']['amount'])
    assert all(a['normalized'][k]==b['normalized'][k] for k in ['unit','basis_quantity','basis_unit','operator','serving_order'])
    assert a['other_ingredients']!=b['other_ingredients']
    cases.append(dict(id='quantity_comparison',question='Do the two BPI Creatine Alkaline labels declare equivalent creatine amounts and identical formulations?',status='answered_with_limits',records=comparison,outcome='Equivalent declared mass and serving basis; other ingredients differ. No product merge or dose recommendation.'))
    creatine=next(r for r in coverage if r['topic']=='Creatine');assert creatine['claim_types'].get('safety',0)>0
    cases.append(dict(id='creatine_safety',question='What saved Creatine safety statements can be retrieved?',status='pending_source_retrieval_only',pending_safety_claims=creatine['claim_types']['safety'],clinical_approval=False,scope='All saved Creatine annotations of type safety, not a clinical safety determination or proof of complete source coverage.'))
    assert not any(e['type'] in {'MORE_EFFECTIVE_THAN','RECOMMENDED_PRODUCT'} for e in edges)
    cases.append(dict(id='unsupported_product_recommendation',question='Which BPI product is more effective for athletic performance?',status='insufficient_evidence',recommended_product=None,reason='The represented graph has no product-comparative effectiveness assertions. General ingredient claims, label quantities and Reddit discussions cannot establish a product recommendation.'))
    queue_counts={f.stem:len(f.read_text().splitlines()) for f in (root/GRAPH/'review').glob('*.jsonl')}
    unresolved=dict(queue_rows=queue_counts,notes=['Counts describe review rows and can overlap; they are not unique clinical errors.','Medium/Low/no-target mappings remain unresolved or excluded, not promoted by this release.','All 1269 NatMed annotations remain pending clinical review; capture and reference gaps remain.','Product equivalence remains unresolved; exact text reuse is not corroboration.','Missing/outside-sample Reddit references and inherited context remain explicit.','No measured clinical precision/recall or trained model performance is claimed.'])
    report=dict(status='passed_with_documented_limitations',release_scope='Frozen data/graph POC baseline, not a clinically validated system',graph=GRAPH,counts=manifest['counts'],checks=checks,representative_cases=len(cases),case_statuses=dict(Counter(c['status'] for c in cases)),coverage=coverage,unresolved=unresolved,clinical_approvals=0,canonical_merges=0,next_step='Choose the downstream evaluation task and baseline before embeddings or GNN training.')
    return report,cases,manifest

def run(root=ROOT):
    root=Path(root);report,cases,gm=build(root)
    signature=dict(graph=GRAPH,graph_manifest_sha256=sha((root/GRAPH/'manifest.json').read_bytes()),graph_file_hashes=gm['files'],spec_sha256=sha((root/SPEC).read_bytes()),code={p:sha((root/p).read_bytes()) for p in ['scripts/validate_freeze_full_graph.py','scripts/export_full_graph.py','scripts/preprocess_pilot.py','tests/test_validate_freeze_full_graph.py']},python=sys.version.split()[0])
    files={'validation_report.json':(encode(report)+'\n').encode(),'representative_questions.json':(encode(cases)+'\n').encode(),'freeze_manifest.json':(encode(signature)+'\n').encode()}
    files['release_notes.md']=('''# Frozen SupplementRx POC graph baseline

This release pins the existing graph by its manifest and every exported file hash; it does not duplicate or modify that graph. Run `supplementsrx_env/bin/python scripts/validate_freeze_full_graph.py` to verify and reproduce it.

- All ten topics have source-separated coverage checks; fixed question cases are not a general answering system.
- Product labels, clinical annotations and Reddit discussion retain distinct evidence roles.
- Pending clinical claims and unresolved mappings remain explicit. This freeze is not clinical approval.
- Source collection completeness, clinical correctness and end-to-end precision/recall remain unestablished.
- Future additions create a new graph/release version; do not overwrite this baseline.
- Next choose an evaluation task and baseline before embeddings or GNN training.
''').encode()
    release=dict(version='poc-release-v1',status=report['status'],graph=GRAPH,graph_manifest_sha256=signature['graph_manifest_sha256'],files={p:sha(b) for p,b in files.items()})
    files['manifest.json']=(encode(release)+'\n').encode();out=root/'data/graph'/('poc-release-v1-'+sha(files['manifest.json'])[:20])
    if out.exists():
        assert {p.name for p in out.iterdir()}==set(files)
        for p,b in files.items():assert (out/p).read_bytes()==b
    else:
        tmp=Path(tempfile.mkdtemp(prefix='.poc-release-',dir=out.parent))
        try:
            for p,b in files.items():(tmp/p).write_bytes(b)
            os.rename(tmp,out)
        except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise
    print(out.relative_to(root));print(json.dumps(dict(status=report['status'],checks=report['checks'],cases=report['representative_cases']),indent=2));return out,report
if __name__=='__main__':run()
