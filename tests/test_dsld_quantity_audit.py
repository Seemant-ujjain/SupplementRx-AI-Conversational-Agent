import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_dsld_quantities import audit_label

class QuantityAuditTests(unittest.TestCase):
    def label(self):
        return {'id':1,'servingSizes':[{'order':1,'minQuantity':2,'maxQuantity':2,
            'minDailyServings':3,'maxDailyServings':3,'unit':'Capsule(s)'}],
            'ingredientRows':[{'name':'Magnesium','quantity':[{'quantity':100,'unit':'mg','operator':'=',
            'servingSizeOrder':1,'servingSizeQuantity':2,'servingSizeUnit':'Capsule(s)'}]}]}
    def codes(self,l):return [f['code'] for f in audit_label(l)[0]]
    def test_np_zero_not_interpreted_as_numeric_zero_dose(self):
        l=self.label();l['ingredientRows'][0]['quantity'][0].update(quantity=0,unit='NP')
        self.assertEqual(self.codes(l),['np_unit_unresolved'])
    def test_daily_total_candidate_not_automatically_corrected(self):
        l=self.label();l['ingredientRows'][0]['quantity'][0]['servingSizeQuantity']=6
        before=copy.deepcopy(l);f=audit_label(l)[0][0]
        self.assertTrue(f['context']['basis_within_computed_daily_range']);self.assertEqual(f['severity'],'review');self.assertEqual(l,before)
    def test_null_daily_max_is_incomplete_not_invalid(self):
        l=self.label();l['servingSizes'][0]['maxDailyServings']=None
        self.assertEqual(self.codes(l),['incomplete_daily_serving_range'])
    def test_missing_basis_not_imputed(self):
        l=self.label();l['ingredientRows'][0]['quantity'][0]['servingSizeQuantity']=None
        self.assertIn('missing_quantity_serving_basis',self.codes(l))
    def test_broken_reference_is_error(self):
        l=self.label();l['ingredientRows'][0]['quantity'][0]['servingSizeOrder']=9
        self.assertIn('unresolved_serving_reference',self.codes(l))
    def test_ml_note_conflict_and_alternative_units(self):
        l=self.label();l['servingSizes'][0].update(unit='mL',minQuantity=52,maxQuantity=52,notes='4 sprays (approx 0.02 fl. oz [0.52 ml])')
        self.assertIn('ml_note_numeric_disagreement',self.codes(l))
        l['servingSizes'][0].update(minQuantity=0.52,maxQuantity=0.52)
        self.assertNotIn('ml_note_numeric_disagreement',self.codes(l))
    def test_inequality_and_zero_are_information(self):
        l=self.label();l['ingredientRows'][0]['quantity'][0].update(quantity=0,operator='<')
        self.assertEqual({f['severity'] for f in audit_label(l)[0]},{'info'})
    def test_nested_rows_audited(self):
        l=self.label();child=copy.deepcopy(l['ingredientRows'][0]);child['quantity'][0]['quantity']=-1
        l['ingredientRows'][0]['nestedRows']=[child]
        findings,counts,_,_=audit_label(l)
        self.assertEqual(counts['ingredient_rows'],2)
        self.assertEqual(findings[0]['pointer'],'/ingredientRows/0/nestedRows/0/quantity/0')

if __name__=='__main__':unittest.main()
