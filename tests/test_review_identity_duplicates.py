import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_identity_duplicates import compare_labels,content_decision,build,direct_links
class IdentityRules(unittest.TestCase):
    def test_matching_core_other_ingredients_differ(self):
        a=dict(id=1,ingredientRows=['creatine'],otheringredients=['gelatin']);b=dict(id=2,ingredientRows=['creatine'],otheringredients=['cellulose'])
        r=compare_labels(a,b);self.assertFalse(r['canonical_merge']);self.assertIn('otheringredients',r['differing_fields'])
    def test_no_transitive_source_link(self):
        a=dict(id=1,labelRelationships=[dict(labelId=2,type='image')]);c=dict(id=3,labelRelationships=[dict(labelId=2,type='image')])
        self.assertEqual(direct_links(a,c),[])
    def test_direct_link_keeps_source_type_and_separate_ids(self):
        r=compare_labels(dict(id=1,labelRelationships=[dict(labelId=2,type='package')]),dict(id=2))
        self.assertEqual(r['direct_source_relationships'][0]['source_type'],'package');self.assertFalse(r['canonical_merge'])
    def test_same_text_different_dose_kept(self):
        members=[dict(id=str(i),original_fields=dict(claim_text='same',dose=d),provenance={}) for i,d in enumerate(['loading','maintenance'])]
        r=content_decision('natmedpro','claim_text',members);self.assertIn('dose',r['context_difference_fields']);self.assertEqual(r['action'],'retain_distinct_claims')
    def test_same_reddit_text_different_context_kept(self):
        members=[dict(id=str(i),original_fields=dict(text='same',thread_id=i,source_created_at=str(i)),provenance={}) for i in range(2)]
        r=content_decision('reddit','record_text',members);self.assertIn('thread_id',r['context_difference_fields']);self.assertFalse(r['canonical_merge'])
class IdentityCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tables,cls.report,cls.inputs=build(ROOT)
    def test_all_existing_groups(self):self.assertEqual((self.report['dsld_groups'],self.report['dsld_pairs']),(70,304))
    def test_no_payload_duplicates_or_merges(self):self.assertEqual(self.report['dsld_payload_duplicate_pairs'],0);self.assertEqual(self.report['entity_merges'],0)
    def test_claim_payloads_distinct(self):self.assertEqual(self.report['duplicate_groups']['natmedpro']['claim_payload_except_id'],0)
    def test_all_text_bindings_resolve(self):
        blobs={r['id'] for r in self.tables['exact_text_blobs']}
        self.assertTrue(all(r['text_id'] in blobs for r in self.tables['exact_text_bindings']))
    def test_all_claims_retained(self):
        r=next(r for r in self.tables['source_identity_inventory'] if r['source']=='natmedpro' and r['table']=='claims');self.assertEqual(r['unique_ids'],1269)
if __name__=='__main__':unittest.main()
