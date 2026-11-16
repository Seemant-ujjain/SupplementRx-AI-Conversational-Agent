import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_natmed_relevance import build,relevance
class NatmedRelevance(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report,cls.questions=build(ROOT)
 def test_coverage(self):self.assertEqual(self.report['summary']['candidate_annotations_reviewed'],260);self.assertEqual(self.report['summary']['questions_reviewed'],10)
 def test_optional_context_not_primary(self):self.assertEqual(self.report['summary']['supporting_context_units'],2);self.assertEqual(self.report['summary']['primary_units'],258)
 def test_probiotic_scope(self):
  q=self.questions['questions'][18];self.assertEqual(q['source_monograph_title'],'Lactobacillus acidophilus');self.assertTrue(any('all probiotics' in s for s in q['required_qualifications']))
 def test_fish_oil_scope(self):self.assertEqual(self.questions['questions'][14]['source_monograph_title'],'Fish Oil')
 def test_dose_shared_excerpts_kept_separate(self):
  d=[r for r in self.report['decisions'] if r['question_id']=='Q12'];self.assertEqual(len(d),18);self.assertEqual(len({r['source_excerpt']['pointer']+str(r['source_excerpt']['start']) for r in d}),2)
 def test_rating_heading_support_retained(self):self.assertGreater(self.report['summary']['earlier_section_heading_anchors'],0)
 def test_lab_interactions_separate(self):self.assertEqual(sum(r['source_subtype']=='laboratory_test_interference' for r in self.report['decisions']),2)
 def test_no_clinical_approval(self):self.assertTrue(all(r['clinical_approval'] is False and r['original_structured_fields']['review']['state']=='pending' for r in self.report['decisions']))
 def test_ten_questions_still_pending(self):self.assertTrue(all(q['expected_relevant_evidence_ids'] is None for q in self.questions['questions'][20:]))
if __name__=='__main__':unittest.main()
