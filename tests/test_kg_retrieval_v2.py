import unittest,sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from kg_retrieval_v2 import warning_relevance,clinical_role,retrieve
from kg_evaluation_common import SavedGraph,sha
class RelevanceRulesV2(unittest.TestCase):
 def test_general_content_restriction(self):self.assertEqual(warning_relevance({'type':'General Statements: All Other Content','notes':'Do not exceed recommended dose.'})[0],'primary')
 def test_report_contact_separate(self):self.assertEqual(warning_relevance({'type':'Precautions re: All Other','notes':'To report a serious adverse event or obtain product information, call 123.'})[0],'context')
 def test_precaution_marketing_excluded(self):self.assertEqual(warning_relevance({'type':'Precautions re: All Other','notes':'Supports iron absorption and healthy iron levels.'})[0],'exclude')
 def test_disclaimer_not_warning(self):self.assertEqual(warning_relevance({'type':'FDA Disclaimer Statement','notes':'Not intended for use in diagnosis.'})[0],'exclude')
 def test_general_tolerability_context(self):self.assertEqual(clinical_role({'claim_type':'adverse_effect','adverse_effect_category':'General'})[0],'context')
 def test_rules_still_locked(self):
  lock=json.loads((ROOT/'data/evaluation/retrieval_v2_rule_lock.json').read_bytes());self.assertEqual(sha((ROOT/lock['script']).read_bytes()),lock['sha256'])
class AdditionalEvaluationIntegrity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.package=json.loads((ROOT/'data/evaluation/additional_evaluation_cases_v1.json').read_bytes());cls.selection=json.loads((ROOT/'data/evaluation/additional_case_selection_v1.json').read_bytes())
 def test_distinct_labels(self):
  new={r['label_id'] for r in self.selection['selection']};self.assertEqual(len(new),10);self.assertFalse(new&set(self.selection['original_labels']))
 def test_no_warning_examples_remain_empty(self):
  for q in ['H02','H06']:self.assertEqual(next(c for c in self.package['cases'] if c['question_id']==q)['expected_primary_units'],[])
 def test_overlap_reported(self):self.assertEqual(self.package['overlap']['warning_occurrences_exact_text_overlap'],5)
 def test_locked_failures_not_erased(self):
  report=json.loads((ROOT/'data/evaluation/retrieval_v2_comparison/comparison.json').read_bytes());self.assertLess(report['sets']['additional_diagnostic']['v2']['macro_recall'],report['sets']['additional_diagnostic']['v1']['macro_recall'])
 def test_sources_unchanged(self):
  for p,h in self.package['inputs'].items():self.assertEqual(sha((ROOT/p).read_bytes()),h)
if __name__=='__main__':unittest.main()
