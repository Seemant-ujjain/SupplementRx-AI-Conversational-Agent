import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from expand_contextual_mapping_candidates import context, supported_query, assess, family


def occurrence(name='Ashwagandha extract', notes='PlantPart: root Genus: Withania Species: somnifera'):
    return {'original_name': name, 'attributes': {'notes': notes}}


def target(name='Withania somnifera root extract', suppress='N'):
    return {'display_name': name, 'original_fields': {'suppress': suppress}}


class ContextualCandidateRules(unittest.TestCase):
    def test_explicit_root_enables_related_query(self):
        o=occurrence()
        self.assertTrue(supported_query(o, context(o), 'Ashwagandha Root Extract'))
        self.assertEqual(assess(context(o), target(), 'rxnorm', None)[:2], (1, 'Medium'))

    def test_root_not_inferred_from_general_name(self):
        o=occurrence(notes='')
        self.assertFalse(supported_query(o, context(o), 'Ashwagandha Root Extract'))

    def test_leaf_query_not_supported_by_root(self):
        o=occurrence()
        self.assertFalse(supported_query(o, context(o), 'Ashwagandha Leaf Extract'))
        self.assertEqual(assess(context(o), target('Withania somnifera leaf extract'), 'rxnorm', None)[1], 'Low')

    def test_same_rule_works_for_other_botanical(self):
        o=occurrence('Valerian extract', 'PlantPart: root Genus: Valeriana Species: officinalis')
        self.assertTrue(supported_query(o, context(o), 'Valerian root extract'))
        self.assertEqual(assess(context(o), target('Valeriana officinalis root extract'), 'rxnorm', None)[0], 1)

    def test_whole_not_equated_to_root(self):
        self.assertEqual(assess(context(occurrence()), target('Withania somnifera whole extract'), 'rxnorm', None)[0], 2)

    def test_mixed_parts_remain_unresolved(self):
        o=occurrence(notes='PlantPart: root and leaf Genus: Withania Species: somnifera')
        self.assertEqual(assess(context(o), target(), 'rxnorm', None)[0], 2)

    def test_negation_and_blends_not_expanded(self):
        for o in [occurrence(notes='PlantPart: not root'), occurrence('Ashwagandha root and leaf blend')]:
            self.assertFalse(supported_query(o, context(o), 'Ashwagandha root extract'))

    def test_different_species_blocks_preference(self):
        self.assertEqual(assess(context(occurrence()), target('Withania coagulans root extract'), 'rxnorm', None)[1], 'Low')

    def test_chemical_qualifier_not_dropped_for_acceptance(self):
        o=occurrence('Creatine HCl', '')
        self.assertTrue(supported_query(o, context(o), 'Creatine hydrochloride'))
        self.assertFalse(supported_query(o, context(o), 'Creatine monohydrate'))
        self.assertEqual(assess(context(o), target('creatine'), 'rxnorm', None)[0], 2)

    def test_brands_salts_and_strains_preserved(self):
        for a,b in [('KSM-66 Ashwagandha root extract','Ashwagandha extract'),
                    ('Magnesium citrate','Magnesium oxide'),('Lactobacillus GG','Lactobacillus')]:
            self.assertNotEqual(family(a), family(b))

    def test_inactive_target_not_preferred(self):
        self.assertEqual(assess(context(occurrence()), target(suppress='Y'), 'rxnorm', None)[0], 2)

    def test_prior_exclusion_never_overridden(self):
        self.assertEqual(assess(context(occurrence()), target(), 'rxnorm', {'confidence':'Low'})[:2], (3,'Low'))

    def test_allergenic_preparation_not_preferred(self):
        o=occurrence('Black Pepper extract', '')
        self.assertEqual(assess(context(o), target('black pepper allergenic extract'), 'rxnorm', None)[:2], (3, 'Low'))

    def test_pubchem_structure_still_pending(self):
        self.assertEqual(assess(context(occurrence()), target(), 'pubchem', None)[:2], (2,'Medium'))

class SavedCollectionIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from expand_contextual_mapping_candidates import build
        cls.proposals, cls.comparisons, cls.report, cls.inputs = build()

    def test_report_serializes_as_valid_json(self):
        import json
        from preprocess_pilot import encode
        self.assertEqual(json.loads(encode(self.report)),self.report)

    def test_root_candidates_found_without_acceptance(self):
        rows=[p for p in self.proposals if p['original_name']=='Ashwagandha extract' and p['target_native_id']=='1309279']
        self.assertEqual(len(rows),7)
        self.assertTrue(all(p['confidence']=='Medium' and p['review_priority']==1 for p in rows))
        self.assertTrue(all(p['proposed_relation'] is None and not p['graph_applied'] for p in self.proposals))

    def test_all_sources_examined_and_no_candidate_history_retained(self):
        self.assertEqual(set(self.report['by_source']), {'pubchem','rxnorm','mesh'})
        self.assertEqual(self.report['historical_no_candidate_rows_unchanged'],4207)
        self.assertEqual(self.report['existing_terminology_decisions_preserved'],6735)

    def test_every_new_proposal_has_discovery_and_source_evidence(self):
        self.assertTrue(all(p['dsld_evidence_ids'] and p['discovery'] and p['target_provenance'] for p in self.proposals))
        self.assertEqual(len(self.proposals),len({p['id'] for p in self.proposals}))
        self.assertTrue(all(p['review_priority']!=1 for p in self.proposals if 'allergenic' in (p['target_name'] or '').lower()))

if __name__=='__main__':
    unittest.main()
