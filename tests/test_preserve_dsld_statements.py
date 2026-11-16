import unittest,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from preserve_dsld_statements import build
class StatementPreservation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.nodes,cls.edges,cls.evidence,cls.inventory,cls.report,cls.inputs,cls.base=build(ROOT)
 def test_all_labels_and_paths(self):self.assertEqual(self.report['labels'],400);self.assertEqual(len(self.inventory),self.report['source_statement_occurrences'])
 def test_general_warning_preserved(self):
  r=next(r for r in self.inventory if r['label_id']=='25731' and r['source_pointer']=='/statements/21');self.assertEqual(r['status'],'added');self.assertEqual(self.evidence[r['evidence_id']]['original_value']['notes'],'Do not exceed recommended dose.')
 def test_instruction_preserved(self):self.assertEqual(next(r for r in self.inventory if r['label_id']=='25731' and r['source_pointer']=='/statements/18')['status'],'added')
 def test_marketing_not_automatically_warning(self):
  n=next(n for n in self.nodes if 'statement_interpretation' in json.loads(n['properties_json']) and json.loads(n['properties_json'])['original_fields'].get('type')=='General Statements: All Other Content');self.assertIn('Unclassified',json.loads(n['properties_json'])['statement_interpretation'])
 def test_no_mapping_added(self):self.assertEqual(sum(bool(e['mapping_id']) for e in self.edges),3039)
if __name__=='__main__':unittest.main()
