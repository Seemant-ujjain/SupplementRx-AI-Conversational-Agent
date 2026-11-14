import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from assess_identity_rules import route_query


class IdentityRoutingTests(unittest.TestCase):
    def query(self, counts):
        return {'query_key': 'example', 'query': 'Example', '_index': 0,
                'candidate_counts': counts, 'dsld_ingredient_ids': [1],
                'methods': {'rxnorm': 'exact'}}

    def test_no_results_preserves_unresolved_case(self):
        row = route_query(self.query({'pubchem': 0, 'rxnorm': 0, 'mesh': 0}), set())
        self.assertEqual(row['applicable_rules'], ['ID-13'])
        self.assertEqual(row['review_state'], 'needs_review')
        self.assertIsNone(row['proposed_relation'])

    def test_three_single_candidates_do_not_approve_identity(self):
        row = route_query(self.query({'pubchem': 1, 'rxnorm': 1, 'mesh': 1}), set())
        self.assertEqual(row['semantic_assessment'], 'not_performed')
        self.assertEqual(row['review_state'], 'needs_review')
        self.assertIsNone(row['proposed_relation'])

    def test_overlapping_conditions_are_retained(self):
        q = self.query({'pubchem': 2, 'rxnorm': 1, 'mesh': 0})
        q['dsld_ingredient_ids'] = [1, 2]
        q['methods']['rxnorm'] = 'normalized'
        row = route_query(q, {'example'})
        self.assertTrue({'ID-04', 'ID-12', 'ID-13', 'ID-14'}.issubset(row['applicable_rules']))
        self.assertIn('normalized_lookup_is_not_identity_evidence', row['reasons'])
        self.assertEqual(row['coverage_scope'], 'mechanical_routing_only')
