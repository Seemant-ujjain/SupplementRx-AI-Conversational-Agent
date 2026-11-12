import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_pubchem import resolve_path,collisions

class PubChemAuditTests(unittest.TestCase):
    def test_nested_source_path(self):
        raw={'ingredientRows':[{'nestedRows':[{'forms':[{'ingredientId':7,'name':'form'}]}]}]}
        self.assertEqual(resolve_path(raw,'ingredientRows[0].nestedRows[0].forms[0]')['ingredientId'],7)
    def test_invalid_path_rejected(self):
        with self.assertRaises(ValueError):resolve_path({},'ingredientRows[-1]')
    def test_shared_structure_is_reported_without_merging_cids(self):
        records={'1':{'properties':{'InChIKey':'same'}},'2':{'properties':{'InChIKey':'same'}},'3':{'properties':{}}}
        groups=collisions(records,'InChIKey')
        self.assertEqual(groups,[{'value':'same','cids':['1','2']}]);self.assertEqual(len(records),3)

if __name__=='__main__':unittest.main()
