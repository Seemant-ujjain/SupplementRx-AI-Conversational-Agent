import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_natmed_reddit_batch import build,literal_hits,topic_status,resolve_reference
class ImportedRules(unittest.TestCase):
    def test_title_and_text_offsets(self):
        hits=literal_hits({'title':'CREATINE','text':'creatinelike creatine'},['creatine'])
        self.assertEqual(len(hits),2);self.assertEqual(hits[1]['start'],13)
    def test_inherited_never_promoted(self):self.assertEqual(topic_status('thread_context',[{'term':'creatine'}]),'inherited_thread_context')
    def test_record_level_own_text_not_every_topic(self):self.assertEqual(topic_status('own_text',[]),'topic_not_verified_in_own_text_record')
    def test_missing_vs_outside(self):
        self.assertEqual(resolve_reference(None,{},'parent_id','comment')[0],'missing_identifier')
        self.assertEqual(resolve_reference('t3_abc',{},'parent_id','comment')[0],'outside_saved_collection')
    def test_post_parent_not_fabricated(self):self.assertEqual(resolve_reference(None,{},'parent_id','post'),('not_applicable',None))
    def test_invalid_thread_target(self):self.assertEqual(resolve_reference('t1_abc',{},'thread_id','comment')[0],'invalid_identifier')
class ImportedBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.outputs,cls.reports,cls.inputs=build(ROOT)
    def test_claims_pending(self):
        claims=self.outputs['natmedpro'][0]['claims'];self.assertEqual(len(claims),1269)
        self.assertTrue(all(c['review_state']=='pending' and c['confidence'] is None and not c['clinical_approval'] for c in claims))
    def test_full_passage_counts(self):
        self.assertEqual(len(self.outputs['natmedpro'][0]['passages']),1179);self.assertEqual(len(self.outputs['reddit'][0]['passages']),5071)
    def test_earlier_headings_explicit(self):self.assertEqual(sum(r['anchor_scope']=='earlier_section_heading' for r in self.outputs['natmedpro'][0]['field_support']),769)
    def test_reddit_not_clinical(self):
        self.assertFalse(self.outputs['reddit'][0]['claims']);self.assertEqual(len(self.outputs['reddit'][0]['records']),4880)
    def test_missing_parents_preserved(self):self.assertEqual(self.reports['reddit']['summary']['missing_parent_ids'],99)
if __name__=='__main__':unittest.main()
