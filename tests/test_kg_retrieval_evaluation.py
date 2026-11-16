import unittest,sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from kg_evaluation_common import SavedGraph
from kg_retrieval_baseline import retrieve
from evaluate_kg_retrieval import evidence_scores,check_response
class EvidenceScoring(unittest.TestCase):
 def test_empty_not_perfect(self):
  r=evidence_scores([],[]);self.assertIsNone(r['precision']);self.assertIsNone(r['recall'])
 def test_duplicate_returns_no_extra_credit(self):self.assertEqual(evidence_scores(['a'],['a','a'])['true_positive'],1)
 def test_false_positive_empty_expected(self):
  r=evidence_scores([],['a']);self.assertEqual(r['precision'],0);self.assertIsNone(r['recall'])
class GraphBaseline(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.g=SavedGraph(ROOT);cls.cases={c['question_id']:c for c in json.loads((ROOT/'data/evaluation/evaluation_cases_v1.json').read_text())['cases']}
 def response(self,q):return retrieve(self.g,self.cases[q]['request'])
 def test_only_request_is_required(self):self.assertEqual(self.response('Q28')['status'],'insufficient_information')
 def test_known_warning_misses_visible(self):
  c=self.cases['Q10'];r=self.response('Q10');self.assertEqual(evidence_scores(c['expected_primary_units'],[p['unit_id'] for p in r['primary']])['false_negative'],2)
 def test_reject_context_promotion(self):
  c=self.cases['Q24'];r=self.response('Q24');r['primary'].append(r['context'].pop());self.assertIn('reddit_context_promoted',check_response(self.g,c,r))
 def test_reject_identity_promotion(self):
  c=self.cases['Q25'];r=self.response('Q25');r['primary'][0]['data']['relation_type']='EXACT_MATERIAL_MATCH';self.assertIn('mapping_scope_promoted',check_response(self.g,c,r))
 def test_reject_null_filling(self):
  c=self.cases['Q26'];r=copy.deepcopy(self.response('Q26'));r['primary'][0]['data']['original_fields']['population']='Adults';self.assertIn('null_changed',check_response(self.g,c,r))
 def test_reject_evidence_replacement(self):
  c=self.cases['Q21'];r=copy.deepcopy(self.response('Q21'));r['primary'][0]['evidence_ids']=['invented'];self.assertIn('evidence_binding_changed',check_response(self.g,c,r))
 def test_comparison_with_abstention(self):
  r=self.response('Q30');self.assertTrue(r['quantity_comparison']['equivalent_declared_mass_and_basis']);self.assertTrue(r['quantity_comparison']['other_ingredient_declarations_differ']);self.assertEqual(r['status'],'partial_answer_comparative_abstention');self.assertIsNone(r['recommended_product'])
 def test_probiotic_labels_deduplicated(self):self.assertEqual(len(self.response('Q29')['primary']),40)
 def test_original_clinical_source_scope(self):self.assertTrue(all(p['extra']['source_title']=='Lactobacillus acidophilus' for p in self.response('Q19')['primary']))
if __name__=='__main__':unittest.main()
