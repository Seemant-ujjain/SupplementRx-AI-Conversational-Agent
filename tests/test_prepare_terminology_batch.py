import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_terminology_batch import build,outcome,rdf_key
class TerminologyRules(unittest.TestCase):
    def test_error_not_no_match(self):
        with self.assertRaises(ValueError):outcome('error',[])
    def test_empty_success_not_no_match(self):
        with self.assertRaises(ValueError):outcome('ok',[])
    def test_conflicting_result_rejected(self):
        with self.assertRaises(ValueError):outcome('not_found',['123'])
    def test_typed_literals_not_collapsed(self):
        a={'subject':{'value':'s'},'predicate':{'value':'p'},'object':{'type':'literal','value':'1','xml:lang':'en'}}
        b=dict(a,object={'type':'literal','value':'1','xml:lang':'fr'})
        self.assertNotEqual(rdf_key(a),rdf_key(b))
class FullTerminologyBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.outputs,cls.reports,cls.inputs=build(ROOT)
    def test_counts_and_query_linkage(self):
        for s,(t,_) in self.outputs.items():self.assertEqual(len(t['query_origins']),3391);self.assertEqual(len(t['queries']),739)
    def test_all_candidates_pending(self):
        for t,_ in self.outputs.values():
            for r in t['candidates']:self.assertIsNone(r['confidence']);self.assertEqual(r['review_state'],'needs_review')
    def test_rxnorm_form_ambiguity_preserved(self):
        t=self.outputs['rxnorm'][0];q=next(q for q in t['queries'] if q['original_query']=='Creatine HCl')
        self.assertEqual(set(q['candidate_native_ids']),{'2907','1310467'});self.assertEqual(q['match_method'],'normalized')
    def test_missing_iupac_not_invented(self):
        t=self.outputs['pubchem'][0];self.assertEqual(sum(r['field_states']['IUPACName']!='present' for r in t['records']),3)
    def test_mesh_statements_keep_provenance(self):
        t=self.outputs['mesh'][0];self.assertEqual(len(t['rdf_statements']),24792)
        self.assertTrue(all(r['provenance'] for r in t['rdf_statements']))
if __name__=='__main__':unittest.main()
