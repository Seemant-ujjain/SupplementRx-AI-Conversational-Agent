import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review_dsld_ingredients import compare

class IngredientReviewTests(unittest.TestCase):
    def label(self):
        return {'id':1,'ingredientRows':[{'name':'Magnesium','forms':[{'name':'Citrate','order':1}],
            'quantity':[{'quantity':100,'unit':'mg','operator':'=','servingSizeQuantity':1,
                         'servingSizeUnit':'Tablet(s)','servingSizeOrder':1,
                         'dailyValueTargetGroup':[{'percent':25}]}], 'nestedRows':[]}],
            'servingSizes':[{'order':1,'minQuantity':1,'maxQuantity':1,'unit':'Tablet(s)'}]}
    def test_daily_value_is_separate_from_amount(self):
        a=self.label();b=copy.deepcopy(a);b['ingredientRows'][0]['quantity'][0]['dailyValueTargetGroup'][0]['percent']=24
        r=compare(a,b);self.assertTrue(r['ingredient_core_equal']);self.assertIn('daily_value_difference',r['flags'])
    def test_serving_basis_never_discarded(self):
        a=self.label();b=copy.deepcopy(a);b['ingredientRows'][0]['quantity'][0]['servingSizeQuantity']=2
        self.assertFalse(compare(a,b)['ingredient_core_equal'])
    def test_units_never_assumed_equivalent(self):
        a=self.label();b=copy.deepcopy(a);b['ingredientRows'][0]['quantity'][0].update(quantity=0.1,unit='g')
        self.assertIn('amount_or_basis_difference',compare(a,b)['flags'])
    def test_order_ignored_but_duplicates_preserved(self):
        a=self.label();extra=copy.deepcopy(a['ingredientRows'][0]);extra['name']='Iron';a['ingredientRows'].append(extra)
        b=copy.deepcopy(a);b['ingredientRows'].reverse();self.assertTrue(compare(a,b)['ingredient_core_equal'])
        b['ingredientRows'].append(extra);self.assertFalse(compare(a,b)['ingredient_core_equal'])
    def test_nested_membership_preserved(self):
        a=self.label();b=copy.deepcopy(a);child={'name':'Blend component','quantity':[],'forms':[],'nestedRows':[]}
        a['ingredientRows'][0]['nestedRows']=[child];b['ingredientRows'].append(child)
        self.assertIn('ingredient_name_or_hierarchy_difference',compare(a,b)['flags'])
    def test_duplicate_paths_not_arbitrarily_aligned(self):
        a=self.label();a['ingredientRows'].append(copy.deepcopy(a['ingredientRows'][0]));b=copy.deepcopy(a)
        self.assertIn('ambiguous_repeated_ingredient_path',compare(a,b)['flags'])

if __name__=='__main__':unittest.main()
