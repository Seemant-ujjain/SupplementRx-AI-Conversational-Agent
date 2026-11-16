"""Batch-scope and comparison eligibility regression checks."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from normalize_dsld_batch import build,comparison_status
class EligibilityTests(unittest.TestCase):
    def t(self):return {'normalized_value':{'amount':'1'},'reason_codes':[]}
    def test_range_mismatch_not_unqualified(self):
        self.assertEqual(comparison_status(self.t(),['quantity_basis_outside_serving_range'],True)[0],'pending_review')
    def test_inequality_keeps_operator_not_blocked_by_itself(self):
        self.assertEqual(comparison_status(self.t(),['inequality_amount'],True)[0],'eligible_for_scoped_comparison')
    def test_unresolved_serving_held(self):
        self.assertEqual(comparison_status(self.t(),[],False)[0],'pending_review')
    def test_unknown_cannot_be_eligible(self):
        self.assertEqual(comparison_status({'normalized_value':None,'reason_codes':['unsupported_source_amount']},[],True)[0],'blocked')
    def test_missing_basis_held(self):
        t=self.t();t['reason_codes']=['missing_or_invalid_basis']
        self.assertEqual(comparison_status(t,[],True)[0],'pending_review')
class FullCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p,cls.reviews,cls.findings,cls.report=build(ROOT)
    def test_all_labels_and_quantity_entries(self):
        self.assertEqual(self.report['labels'],400);self.assertEqual(self.report['quantity_entries'],2392)
        self.assertEqual(len(self.p.tables['snapshots']),400)
    def test_no_identity_promotion(self):
        self.assertFalse(self.p.tables['mapping_assertions']);self.assertFalse(self.p.tables['canonical_identities'])
    def test_all_findings_preserved(self):
        self.assertEqual(len(self.findings),872)
        self.assertEqual(self.report['audit_findings_by_code']['missing_quantity_serving_basis'],8)
    def test_serving_level_audit_present(self):
        self.assertTrue(any(f['code']=='incomplete_daily_serving_range' for f in self.findings))
    def test_references_use_collection_scope(self):
        for r in self.p.tables['source_references'].values():
            if r['target_key']:self.assertEqual(r['target_key']['availability_scope'],'selected_dsld_collection')
if __name__=='__main__':unittest.main()
