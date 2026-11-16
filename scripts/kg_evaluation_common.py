"""Shared identifiers and saved-graph loading, with no expected-answer access."""
from pathlib import Path
from collections import defaultdict
import json,csv,hashlib
ROOT=Path(__file__).resolve().parents[1]
GRAPH='data/graph/full-graph-statements-v1-27c544f4940e7162944c'
def sha(b):return hashlib.sha256(b).hexdigest()
def warning_unit(label,text):return 'warning:'+str(label)+':'+sha(text.encode())
def load_jsonl(p):return [json.loads(l) for l in Path(p).read_text().splitlines()]
class SavedGraph:
 def __init__(self,root=ROOT):
  self.root=Path(root);p=self.root/GRAPH;self.manifest=json.loads((p/'manifest.json').read_bytes());csv.field_size_limit(10000000)
  for f,h in self.manifest['files'].items():assert sha((p/f).read_bytes())==h,f
  self.nodes={};self.edges={};self.out=defaultdict(list);self.inc=defaultdict(list)
  for f in sorted((p/'nodes').glob('*.csv')):
   with f.open() as handle:
    for r in csv.DictReader(handle):r['properties']=json.loads(r.pop('properties_json'));r['evidence_ids']=json.loads(r['evidence_ids']);self.nodes[r['id']]=r
  with (p/'relationships/relationships.csv').open() as handle:
   for e in csv.DictReader(handle):
    e['properties']=json.loads(e.pop('properties_json'));e['evidence_ids']=json.loads(e['evidence_ids']);self.edges[e['id']]=e;self.out[(e['start_id'],e['type'])].append(e);self.inc[(e['end_id'],e['type'])].append(e)
  self.labels={n['properties']['source_record']['native_id']:n['id'] for n in self.nodes.values() if n['type']=='ProductLabel'}
  self.topics={n['properties']['name']:n['id'] for n in self.nodes.values() if n['type']=='SupplementTopic'}
 def occurrences(self,lid,topic):
  allids={e['end_id'] for e in self.out[(lid,'DECLARES_OCCURRENCE')]}
  found={i for i in allids if self.nodes[i]['properties']['role']=='ingredient' and self.nodes[i]['properties']['attributes'].get('ingredientGroup')==topic}
  while True:
   extra={i for i in allids if self.nodes[i]['properties'].get('parent_id') in found}
   if extra<=found:return found
   found|=extra
