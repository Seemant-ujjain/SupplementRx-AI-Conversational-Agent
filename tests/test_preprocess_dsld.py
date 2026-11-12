import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('preprocess_dsld',Path(__file__).resolve().parents[1]/'scripts/preprocess_dsld.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LabelInventoryTests(unittest.TestCase):
    def test_preserves_same_name_versions_and_ingredient_payload(self):
        labels=[{'id':2,'brandName':'Brand','fullName':'Magnesium','offMarket':1,
                 'ingredientRows':[{'name':'Magnesium','quantity':[{'quantity':400,'unit':'mg'}]}]},
                {'id':1,'brandName':'Brand','fullName':'Magnesium','offMarket':0}]
        rows,groups=module.build_label_inventory(labels,{'1':['Magnesium']},{'1':'a','2':'b'})
        self.assertEqual(len(rows),2)
        self.assertEqual(len(groups),1)
        self.assertEqual(rows[1]['raw_label'],labels[0])
        self.assertEqual(rows[0]['market_status'],'on_market_in_source')
        self.assertEqual(rows[1]['market_status'],'off_market_in_source')
        self.assertEqual(rows[0]['search_categories'],['Magnesium'])

    def test_unknown_status_never_becomes_current(self):
        for value in (None,'0',False,2):
            rows,_=module.build_label_inventory([{'id':1,'offMarket':value}],{}, {'1':'hash'})
            self.assertEqual(rows[0]['market_status'],'unknown')

    def test_duplicate_source_ids_rejected(self):
        with self.assertRaises(ValueError):
            module.build_label_inventory([{'id':1},{'id':1}],{}, {'1':'hash'})

    def test_missing_names_do_not_create_duplicate_group(self):
        _,groups=module.build_label_inventory([{'id':1},{'id':2}],{}, {'1':'a','2':'b'})
        self.assertEqual(groups,[])

if __name__=='__main__':unittest.main()
