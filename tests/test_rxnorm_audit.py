import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_rxnorm import search_issues

class RxNormAuditTests(unittest.TestCase):
    def search(self,mode,ids):return {'mode':mode,'response':{'idGroup':{'rxnormId':ids}}}
    def test_exact_can_be_ambiguous_without_identity_approval(self):
        r={'status':'matched','match_method':'exact','rxcuis':['1','2'],'requires_identity_review':True,'searches':[self.search('exact',['2','1'])]}
        self.assertEqual(search_issues(r),[])
    def test_normalized_fallback_requires_empty_exact(self):
        r={'status':'matched','match_method':'normalized','rxcuis':['2'],'requires_identity_review':True,'searches':[self.search('exact',['1']),self.search('normalized',['2'])]}
        self.assertIn('fallback_after_exact_candidates',search_issues(r))
    def test_selected_candidate_must_match_response(self):
        r={'status':'matched','match_method':'exact','rxcuis':['1'],'requires_identity_review':True,'searches':[self.search('exact',['2'])]}
        self.assertIn('selected_response_mismatch',search_issues(r))
    def test_no_match_distinct_from_matched(self):
        r={'status':'not_found','match_method':None,'rxcuis':[],'searches':[self.search('exact',[]),self.search('normalized',[])]}
        self.assertEqual(search_issues(r),[])

if __name__=='__main__':unittest.main()
