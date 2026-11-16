import sys,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from export_full_graph import build,validate,parent_relation
class FullGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes,cls.edges,cls.evidence,cls.review,cls.files,cls.report,cls.inputs,cls.expected=build(ROOT)
        cls.byid={n['id']:n for n in cls.nodes}
    def test_coverage(self):
        t=self.report['node_types']
        for typ,count in [('ProductLabel',400),('IngredientOccurrence',5438),('Monograph',10),('ClinicalClaim',1269),('RedditPost',287),('RedditComment',4593),('SourcePassage',6250)]:self.assertEqual(t[typ],count)
    def test_mapping_gates(self):
        self.assertEqual(self.report['counts']['terminology_mapping_edges'],2684)
        self.assertEqual(self.report['counts']['natmed_subject_mapping_edges'],353)
        self.assertEqual(sum(e['type']=='EXACT_MATERIAL_MATCH' for e in self.edges),7)
    def test_medium_low_do_not_leak(self):
        pending={r['id'] for r in self.review['mapping_pending_excluded']}
        self.assertFalse(pending & {e['mapping_id'] for e in self.edges})
    def test_reddit_context_separate(self):
        self.assertEqual(sum(e['type']=='MENTIONS_TOPIC' for e in self.edges),1672)
        self.assertEqual(sum(e['type']=='INHERITED_THREAD_TOPIC' for e in self.edges),6310)
    def test_clinical_unknowns_and_status_preserved(self):
        for n in self.nodes:
            if n['type']=='ClinicalClaim':
                self.assertFalse(n['properties']['clinical_approval']);self.assertEqual(n['properties']['original_fields']['review']['state'],'pending')
    def test_quantity_conflicts_still_blocked(self):
        self.assertTrue(any('numeric_text_serving_conflict' in r['reason_codes'] for r in self.review['dsld_issues']))
        self.assertTrue(any(r['status']=='blocked' for r in self.review['dsld_quantity']))
    def test_no_dangling_or_missing_evidence(self):validate(self.nodes,self.edges,self.evidence,self.expected)
    def test_reject_dangling(self):
        altered=[dict(self.edges[0],end_id='missing')]+self.edges[1:]
        with self.assertRaisesRegex(AssertionError,'Dangling'):validate(self.nodes,altered,self.evidence,self.expected)
    def test_reject_relation_promotion(self):
        altered=[dict(e,type='EXACT_MATERIAL_MATCH') if e['mapping_id'] and e['type']=='DENOTES_CONCEPT' else e for e in self.edges]
        with self.assertRaisesRegex(AssertionError,'promotion'):validate(self.nodes,altered,self.evidence,self.expected)
    def test_reject_missing_mapping(self):
        altered=[e for e in self.edges if not e['mapping_id']]
        with self.assertRaisesRegex(AssertionError,'eligibility'):validate(self.nodes,altered,self.evidence,self.expected)
    def test_mesh_types_retained(self):
        self.assertEqual(sum(e['type']=='MESH_RELATION' for e in self.edges),10892)
        self.assertEqual(sum(len(n['properties'].get('rdf_literals',[])) for n in self.nodes),13900)
    def test_nested_components_not_forms(self):
        self.assertEqual(parent_relation('ingredient'),'HAS_DECLARED_COMPONENT')
        self.assertEqual(parent_relation('form'),'HAS_DECLARED_FORM')
    def test_external_targets_have_no_loaded_content(self):
        self.assertTrue(all(n['properties']['content_loaded'] is False for n in self.nodes if n['type']=='ExternalRecordReference'))
if __name__=='__main__':unittest.main()
