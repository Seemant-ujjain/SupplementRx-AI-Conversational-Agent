from pathlib import Path
import json,hashlib,re
root=Path.cwd();q=json.load(open('data/evaluation/evaluation_cases_v1.json'));known={i for c in q['cases'] for i in c['request']['label_ids']};known.add('43261')
raw={p.stem.removeprefix('label_'):json.loads(p.read_bytes()) for p in Path('data/raw/dsld/labels').glob('label_*.json')};adj={i:set() for i in raw};families={}
for i,r in raw.items():
 family=(r.get('brandName','').casefold(),r.get('fullName','').casefold());families.setdefault(family,[]).append(i)
 for link in r.get('labelRelationships') or []:
  target=str(link['labelId'])
  if target in raw:adj[i].add(target);adj[target].add(i)
for ids in families.values():
 for i in ids:adj[i].update(ids)
blocked=set(known);front=list(known)
while front:
 for neighbor in adj.get(front.pop(),[]):
  if neighbor not in blocked:blocked.add(neighbor);front.append(neighbor)
aliases=json.load(open('schemas/topic_navigation_v1.json'))['aliases'];selection=[];used=set()
for topic,names in aliases.items():
 candidates=[i for i,r in raw.items() if i not in blocked|used and any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',r.get('fullName',''),re.I) for name in names)]
 assert candidates,topic
 chosen=min(candidates,key=lambda i:hashlib.sha256(('warning-expansion-v1|'+topic+'|'+i).encode()).hexdigest());used.add(chosen)
 # Exclude this family too so the additional set has no within-set related label pairs.
 front=[chosen]
 while front:
  for neighbor in adj[front.pop()]:
   if neighbor not in blocked:blocked.add(neighbor);front.append(neighbor)
 r=raw[chosen];selection.append(dict(id='H'+str(len(selection)+1).zfill(2),topic=topic,label_id=chosen,brand=r['brandName'],product=r['fullName']))
manifest=dict(rule_lock=json.load(open('data/evaluation/retrieval_v2_rule_lock.json')),selection=selection,original_labels=sorted(known),excluded_by_family_or_source_relation_count=len(blocked),method='One per topic using deterministic hash order; exclude original labels and connected source relationships/exact brand-product families. No warning-text or classifier-output selection.',limits='Same captured collection and same assistant reviewer; existing shared boilerplate will be measured, not hidden.')
Path('data/evaluation/additional_case_selection_v1.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for s in selection:
 print('\n',s)
 for i,x in enumerate(raw[s['label_id']]['statements']):print(i,x['type'],repr(x['notes']))
