import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from expand_topic_navigation import mentions,build,validate_extension
class TopicNavigation(unittest.TestCase):
    def test_no_substring(self):self.assertEqual(mentions('environment',['iron']),[]);self.assertEqual(mentions('prebiotic',['probiotic']),[])
    def test_longest_alias_and_offsets(self):self.assertEqual(mentions('Vitamin D3',['vitamin d','vitamin d3']),[dict(start=0,end=10,text='Vitamin D3')])
    def test_species_not_automatic(self):self.assertEqual(mentions('Lactobacillus acidophilus',['probiotic','probiotics']),[])
    @classmethod
    def setUpClass(cls):cls.nodes,cls.edges,cls.added,cls.report,cls.base=build(ROOT)
    def test_probiotics_gap_closed_by_explicit_names(self):
        r=next(r for r in self.report['after'] if r['topic']=='Probiotics');self.assertEqual(r['ingredient_name_labels'],38);self.assertEqual(r['title_labels'],40);self.assertEqual(r['all_navigation_labels'],40)
    def test_existing_counts_preserved(self):
        self.assertEqual(self.report['source_audit']['reddit']['direct_mentions'],1672);self.assertEqual(self.report['source_audit']['reddit']['inherited_context'],6310);self.assertEqual(self.report['source_audit']['natmed']['pending_claim_links'],1269)
    def test_all_topics_audited(self):self.assertEqual(len(self.report['after']),10)
    def test_no_identity_or_clinical_promotion(self):self.assertTrue(all(not e['mapping_id'] and not e['properties']['clinical_approval'] for e in self.added))
if __name__=='__main__':unittest.main()
