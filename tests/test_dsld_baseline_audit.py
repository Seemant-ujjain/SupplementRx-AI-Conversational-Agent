import sys
import unittest
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_dsld_baseline import value_state, profile, collect_objects, duplicate_candidates, normalized_name, ingredient_occurrences

class BaselineAuditTests(unittest.TestCase):
    def test_missing_empty_placeholder_and_zero_separate(self):
        rows=[{}, {'a':None},{'a':''},{'a':'NP'},{'a':0},{'a':False}]
        p=profile({'x':rows})['x']['a']
        self.assertEqual(p['missing_key'],1)
        self.assertEqual(p['states'],{'null':1,'empty_string':1,'placeholder_token_candidate':1,'populated':2})
    def test_empty_parents_do_not_inflate_child_denominator(self):
        objects=defaultdict(list)
        for obj in [{'rows':[]},{'rows':[{'name':'a'}]}]:collect_objects(obj,'label',objects)
        self.assertEqual(profile(objects)['label/rows[]']['name']['parent_objects'],1)
    def test_name_normalization_preserves_strength_and_punctuation(self):
        self.assertEqual(normalized_name('  Vitamin   D '),'vitamin d')
        self.assertNotEqual(normalized_name('Vitamin D 1000'),normalized_name('Vitamin D 2000'))
        self.assertNotEqual(normalized_name('B-12'),normalized_name('B12'))
    def test_candidate_does_not_merge_records(self):
        rows=[{'id':1,'brandName':'Brand','fullName':'Vitamin D'}, {'id':2,'brandName':'brand','fullName':'Vitamin  D'}]
        groups=duplicate_candidates(rows,lambda r:(normalized_name(r['brandName']),normalized_name(r['fullName'])))
        self.assertTrue(groups[0]['crosses_exact_name_groups']);self.assertEqual(len(rows),2)
    def test_other_ingredients_forms_keep_distinct_paths(self):
        label={'id':1,'otheringredients':{'ingredients':[{'ingredientId':2,'name':'Blend','forms':[{'ingredientId':3,'name':'Salt'}]}]}}
        occ=list(ingredient_occurrences(label))
        self.assertEqual(occ[1]['pointer'],'/otheringredients/ingredients/0/forms/0')
        self.assertEqual(occ[1]['role'],'other_ingredient_form')

if __name__=='__main__':unittest.main()
