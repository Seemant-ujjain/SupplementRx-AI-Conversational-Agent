import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_general_concept_mappings import eligible

class GeneralConceptRules(unittest.TestCase):
    def fixture(self):
        return ({'original_name':'Ashwagandha extract','attributes':{'notes':'5% Withanolides KSM-66 PlantPart: root Genus: Withania Species: somnifera'}},
                {'native_id':'1','display_name':'Withania somnifera root extract','original_fields':{'tty':'IN','suppress':'N'}},
                [{'match_method':'exact','original_query':'Ashwagandha Root Extract','candidate_native_ids':['1']}])
    def test_standardization_and_brand_retained(self):
        o,t,q=self.fixture();self.assertTrue(eligible(o,t,'rxnorm',q,'Medium')[0]);self.assertIn('KSM-66',o['attributes']['notes'])
    def test_whole_not_root(self):
        o,t,q=self.fixture();t['display_name']='Withania somnifera whole extract';self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
    def test_no_approximate_bridge(self):
        o,t,q=self.fixture();q[0]['match_method']='approximate';self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
    def test_query_target_membership_required(self):
        o,t,q=self.fixture();q[0]['candidate_native_ids']=['2'];self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
    def test_low_not_overridden(self):
        o,t,q=self.fixture();self.assertFalse(eligible(o,t,'rxnorm',q,'Low')[0])
    def test_no_cross_species_bridge(self):
        o,t,q=self.fixture();t['display_name']='Withania coagulans root extract';self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
    def test_inactive_and_non_ingredient_excluded(self):
        for field,value in [('suppress','Y'),('tty','SCD')]:
            o,t,q=self.fixture();t['original_fields'][field]=value;self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
    def test_other_sources_need_other_rules(self):
        o,t,q=self.fixture()
        for source in ['pubchem','mesh','natmedpro']:self.assertFalse(eligible(o,t,source,q,'Medium')[0])
    def test_missing_part_stays_pending(self):
        o,t,q=self.fixture();o['attributes']['notes']='5% Withanolides';self.assertFalse(eligible(o,t,'rxnorm',q,'Medium')[0])
if __name__=='__main__':unittest.main()
