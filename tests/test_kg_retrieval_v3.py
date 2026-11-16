import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from kg_retrieval_v3 import warning_relevance, clinical_role
from kg_evaluation_common import sha

class ConservativeRelevanceTests(unittest.TestCase):
    def test_unrecognized_precaution_retained(self):
        self.assertEqual(warning_relevance({'type': 'Precautions re: All Other', 'notes': 'Use only if safety seal is intact.'})[0], 'primary')

    def test_locator_is_context(self):
        self.assertEqual(warning_relevance({'type': 'Precautions', 'notes': 'Warning: See side panel.'})[0], 'context')

    def test_clear_marketing_excluded(self):
        self.assertEqual(warning_relevance({'type': 'Precautions', 'notes': 'Formulated to support healthy iron levels.'})[0], 'exclude')

    def test_null_numeric_dose_does_not_remove_caution(self):
        self.assertEqual(clinical_role({'claim_type': 'dose', 'dose': {'value': None, 'text': 'Giving one dropperful by mistake can deliver 10,000 IU daily.'}})[0], 'primary')

    def test_general_dose_context(self):
        self.assertEqual(clinical_role({'claim_type': 'dose', 'dose': {'text': 'Dosing recommendations vary.'}})[0], 'context')

    def test_explicit_restriction_overrides_general_context(self):
        self.assertEqual(clinical_role({'claim_type': 'dose', 'dose': {'text': 'Dosing recommendations vary. Do not exceed the prescribed amount.'}})[0], 'primary')

    def test_lock_and_manifest_integrity(self):
        lock = json.loads((ROOT / 'data/evaluation/retrieval_v3_rule_lock.json').read_text())
        self.assertEqual(sha((ROOT / lock['script']).read_bytes()), lock['sha256'])
        folder = ROOT / 'data/evaluation/retrieval_v3_comparison'
        manifest = json.loads((folder / 'manifest.json').read_text())
        for category in ['inputs', 'code', 'files']:
            for path, digest in manifest[category].items():
                self.assertEqual(sha(((folder if category == 'files' else ROOT) / path).read_bytes()), digest)

    def test_new_cases_and_empty_evidence(self):
        package = json.loads((ROOT / 'data/evaluation/additional_evaluation_cases_v2.json').read_text())
        prior = []
        for name in ['evaluation_cases_v1', 'additional_evaluation_cases_v1']:
            prior += json.loads((ROOT / f'data/evaluation/{name}.json').read_text())['cases']
        old_labels = {v for c in prior for v in c['request'].get('label_ids', [])}
        new_labels = {v for c in package['cases'] for v in c['request'].get('label_ids', [])}
        self.assertEqual(len(new_labels), 6)
        self.assertFalse(new_labels & old_labels)
        self.assertEqual(next(c for c in package['cases'] if c['question_id'] == 'J03')['expected_primary_units'], [])
        for path, digest in package['inputs'].items():
            self.assertEqual(sha((ROOT / path).read_bytes()), digest)

if __name__ == '__main__':
    unittest.main()
