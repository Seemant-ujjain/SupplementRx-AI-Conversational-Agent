import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_natmed import validate_support, supported_value, duplicate_groups
from jsonschema import Draft202012Validator, FormatChecker

class NatMedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(__file__).resolve().parents[1]/'data/raw/natmedpro'
        cls.records={r['id']:r for r in map(json.loads,(base/'records.jsonl').read_text().splitlines())}
        cls.claim=json.loads((base/'upstream_derived/pending_clinical/clinical_claims.jsonl').read_text().splitlines()[0])
        cls.schema=json.loads((base/'upstream_derived/pending_clinical/clinical_claim.schema.json').read_text())
    def test_changed_source_span_detected(self):
        c=copy.deepcopy(self.claim);c['source']['start']+=1
        self.assertTrue(any(e['code']=='excerpt_or_bounds_mismatch' for e in validate_support(c,self.records)[0]))
    def test_anchor_value_mismatch_detected(self):
        c=copy.deepcopy(self.claim);c['safety_rating']='UNSUPPORTED'
        self.assertTrue(any(e['code']=='anchor_value_mismatch' for e in validate_support(c,self.records)[0]))
    def test_missing_support_detected(self):
        c=copy.deepcopy(self.claim);c['field_support']={}
        self.assertTrue(any(e['code']=='field_support_key_mismatch' for e in validate_support(c,self.records)[0]))
    def test_source_title_identity_preserved(self):
        c=copy.deepcopy(self.claim);c['ingredient']['name']='Broader topic'
        self.assertTrue(any(e['code']=='ingredient_source_title_mismatch' for e in validate_support(c,self.records)[0]))
    def test_schema_rejects_approval_without_reviewer(self):
        c=copy.deepcopy(self.claim);c['review']['state']='approved'
        self.assertTrue(list(Draft202012Validator(self.schema,format_checker=FormatChecker()).iter_errors(c)))
    def test_decimal_equivalence_not_unit_conversion(self):
        self.assertTrue(supported_value(2.4,'2.40'));self.assertFalse(supported_value(2.4,'2400'))

if __name__=='__main__':unittest.main()
