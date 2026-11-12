import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review_terminology_mappings import flags_for,signature

class TerminologyReviewTests(unittest.TestCase):
    def test_single_candidates_do_not_generate_identity_approval(self):
        flags=flags_for({s:[{'id':s}] for s in ['pubchem','rxnorm','mesh']},{'rxnorm':'exact'})
        self.assertEqual(flags,[])
    def test_normalized_multi_candidate_and_no_match_separate(self):
        flags=flags_for({'pubchem':[{}],'rxnorm':[{},{}],'mesh':[]},{'rxnorm':'normalized'})
        self.assertEqual(set(flags),{'rxnorm_multiple_candidates','mesh_no_candidate','rxnorm_normalized_search'})
    def test_occurrence_difference_prevents_inventory_equivalence(self):
        a={'query':'Magnesium','occurrences':[{'dsld_id':'1','kind':'ingredient'}]}
        b={'query':'Magnesium','occurrences':[{'dsld_id':'1','kind':'form'}]}
        self.assertNotEqual(signature(a),signature(b))

if __name__=='__main__':unittest.main()
