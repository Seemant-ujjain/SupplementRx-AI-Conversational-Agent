import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from decide_ingredient_mappings import decide,build
class MappingRules(unittest.TestCase):
    def test_exact_concept_not_material(self):self.assertEqual(decide('rxnorm','Magnesium','magnesium',True,1,{})[:2],('High','denotes_concept'))
    def test_exact_pubchem_still_needs_material_review(self):self.assertEqual(decide('pubchem','Magnesium','Magnesium',True,1,{})[0],'Medium')
    def test_form_conflict(self):self.assertEqual(decide('rxnorm','Creatine HCl','creatine monohydrate',True,1,{})[0],'Low')
    def test_allergenic_preparation(self):self.assertEqual(decide('rxnorm','Broccoli','broccoli allergenic extract',True,1,{})[0],'Low')
    def test_ambiguous_no_auto_high(self):self.assertEqual(decide('rxnorm','Iron','iron',True,2,{})[0],'Medium')
    def test_botanical_preparation_review(self):self.assertEqual(decide('mesh','Ashwagandha','Ashwagandha',True,1,{'category':'botanical'})[0],'Medium')
    def test_inactive_no_auto_high(self):self.assertEqual(decide('mesh','Iron','Iron',False,1,{})[0],'Medium')
class MappingCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tables,cls.report,cls.inputs=build(ROOT)
    def test_pilot_decisions_retained(self):self.assertEqual(self.report['prior_pilot_decisions_preserved'],40)
    def test_prior_subject_links_retained(self):self.assertEqual(self.report['prior_natmed_subject_links_preserved'],4)
    def test_no_target_is_not_low(self):self.assertTrue(all(r['confidence'] is None for r in self.tables['no_candidate_queries']))
    def test_no_new_unreviewed_exact_identity(self):self.assertTrue(all(r['rule']=='M1' for r in self.tables['terminology_decisions'] if r['proposed_relation']=='exact_material_match'))
    def test_no_clinical_propagation(self):self.assertTrue(all(not r['clinical_approval'] for r in self.tables['natmed_subject_decisions']))
    def test_topics_not_identity(self):self.assertTrue(all(not r['identity_mapping'] for r in self.tables['source_topic_context']))
if __name__=='__main__':unittest.main()
