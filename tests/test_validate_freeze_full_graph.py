import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from validate_freeze_full_graph import build,Graph,pointer
class FreezeValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report,cls.cases,cls.manifest=build(ROOT)
    def test_all_ten_topics(self):self.assertEqual(len(self.report['coverage']),10)
    def test_all_claim_spans(self):self.assertEqual(self.report['checks']['excerpts_verified'],1269);self.assertEqual(self.report['checks']['field_anchors_verified'],2923)
    def test_supported_and_abstention_cases(self):
        c=next(c for c in self.cases if c['id']=='unsupported_product_recommendation');self.assertIsNone(c['recommended_product']);self.assertEqual(c['status'],'insufficient_evidence')
    def test_context_not_direct(self):
        nodes=[dict(id='t',type='SupplementTopic',properties={'name':'Test'}),dict(id='r',type='RedditComment',properties={})]
        edges=[dict(id='e',start_id='r',end_id='t',type='INHERITED_THREAD_TOPIC')]
        r=Graph(nodes,edges).topic('Test');self.assertEqual(r['reddit_direct_records'],0);self.assertEqual(r['reddit_context_only_records'],1)
    def test_missing_label_path_reports_gap(self):
        r=Graph([dict(id='t',type='SupplementTopic',properties={'name':'Test'})],[]).topic('Test')
        self.assertIn('No labels on these explicit topic paths',r['gaps'])
    def test_json_pointer_escaping(self):self.assertEqual(pointer({'a/b':{'~x':[4]}},'/a~1b/~0x/0'),4)
if __name__=='__main__':unittest.main()
