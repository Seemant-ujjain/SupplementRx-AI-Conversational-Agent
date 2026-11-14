"""Behavioral and integration checks; synthetic fixtures are not collected data."""
import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from preprocess_pilot import (Pilot, CONTRACT, key, load, encode, sha, normalize_mass,
                              reference_states, search_key, validate_tables, pointer, state)


def fixture():
    p=object.__new__(Pilot)
    p.contract=load((ROOT/CONTRACT).read_bytes());p.tables={t:{} for t in p.contract['tables']}
    p.source_targets={};p.snap_data={};p.expected={};p.inputs={};p.data={}
    d={'ingredientRows':[{'name':'Example','ingredientId':1,'quantity':[{'quantity':Decimal('1.5'),'unit':'g','operator':'<','servingSizeQuantity':2,'servingSizeUnit':'Capsule(s)','servingSizeOrder':1}]}]}
    b=encode(d).encode();path='synthetic.json'
    p.inputs[path]={'sha256':sha(b),'bytes':len(b)};p.data[path]=d
    rid,sid=p.source('dsld','label',1,path,{'pointer':''},{'id':1},'label_information',run='fixture-capture')
    return p,rid,sid

class NormalizationFixtures(unittest.TestCase):
    def q(self,amount=Decimal('1.5'),unit='g',operator='=',basis=2):
        return {'quantity':amount,'unit':unit,'operator':operator,'servingSizeQuantity':basis,'servingSizeUnit':'Capsule(s)','servingSizeOrder':1}
    def test_mass_equivalence_without_equivalence_decision(self):
        a=normalize_mass(self.q());b=normalize_mass(self.q(1500,'mg'))
        self.assertEqual(a['normalized_value'],b['normalized_value'])
        self.assertNotIn('accepted',a)
    def test_different_basis_stays_distinct(self):
        a=normalize_mass(self.q(100,'mg',basis=1));b=normalize_mass(self.q(100,'mg',basis=2))
        self.assertNotEqual(a['normalized_value'],b['normalized_value'])
    def test_np_zero_named_zero_and_missing_are_distinct(self):
        a=normalize_mass(self.q(0,'NP'));b=normalize_mass(self.q(0,'mg'));c=normalize_mass(self.q(None,'mg'))
        self.assertIsNone(a['normalized_value']);self.assertEqual(a['value_state'],'explicit_unknown')
        self.assertEqual(b['normalized_value']['amount'],'0');self.assertTrue(b['review_required'])
        self.assertEqual(c['value_state'],'missing')
    def test_bound_and_numeric_precision(self):
        r=normalize_mass(self.q(Decimal('0.000000000000000000000000000001'),'g','<'))
        self.assertEqual(r['normalized_value']['operator'],'<')
        self.assertEqual(Decimal(r['normalized_value']['amount']),Decimal('1e-27'))
    def test_unsupported_units_never_plain_mass(self):
        for u in ['IU','mcg DFE','mcg RAE','mg NE','CFU/g','mL','MG','DU']:
            self.assertIsNone(normalize_mass(self.q(1,u))['normalized_value'])
    def test_conflict_blocks_and_does_not_change_source(self):
        q=self.q();old=copy.deepcopy(q);r=normalize_mass(q,True)
        self.assertIsNone(r['normalized_value']);self.assertEqual(r['value_state'],'conflicting');self.assertEqual(q,old)
    def test_missing_basis_blocks_use_not_independent_mass_conversion(self):
        r=normalize_mass(self.q(basis=None))
        self.assertEqual(r['normalized_value']['amount'],'1500');self.assertTrue(r['review_required'])
        self.assertIsNone(r['normalized_value']['basis_quantity'])
    def test_invalid_numeric_and_operator(self):
        for v in [True,-1,'1,000',Decimal('NaN')]:
            self.assertIsNone(normalize_mass(self.q(v))['normalized_value'])
        self.assertIsNone(normalize_mass(self.q(operator=None))['normalized_value'])
    def test_search_key_keeps_qualifiers_and_hyphen(self):
        self.assertEqual(search_key('  Creatine   HCl  '),'creatine hcl')
        self.assertNotEqual(search_key('LA14'),search_key('LA-14'))
        self.assertNotEqual(search_key('creatine'),search_key('creatine monohydrate'))
    def test_lossless_numeric_output_and_parser_rejects_duplicate_keys(self):
        d=load('{"quantity":1.5000000000000000001,"range":[1,null]}')
        self.assertEqual(load(encode(d)),d)
        with self.assertRaises(ValueError):load('{"id":1,"id":2}')
        with self.assertRaises(ValueError):load('{"x":NaN}')
    def test_keys_not_ambiguous_and_float_keys_rejected(self):
        self.assertNotEqual(key('x','a:b','c'),key('x','a','b:c'))
        with self.assertRaises(TypeError):key('x',1.0)
    def test_absence_null_and_range_not_imputed(self):
        self.assertEqual(state({},'quantity'),'absent')
        self.assertEqual(state({'quantity':None},'quantity'),'null')
        interval={'minimum':1,'maximum':None,'inclusive_min':True}
        q=self.q(interval)
        self.assertIsNone(normalize_mass(q)['normalized_value'])
        self.assertIsNone(q['quantity']['maximum'])

class ReferenceAndVersionFixtures(unittest.TestCase):
    def test_missing_and_known_absent_are_not_same(self):
        a=reference_states(None);b=reference_states('t3_known')
        self.assertEqual(a['target_availability'],'not_assessable')
        self.assertEqual(b['target_availability'],'not_collected')
        self.assertIsNone(a['target_snapshot_id']);self.assertIsNone(b['target_snapshot_id'])
    def test_collected_reference_can_be_resolved_with_content_unassessed(self):
        a=reference_states('t3_known',('record','snapshot'))
        self.assertEqual(a['resolution_state'],'resolved');self.assertEqual(a['content_status'],'not_assessed')
    def test_capture_replay_and_new_capture_reuse_snapshot(self):
        p,r,s=fixture()
        r2,s2=p.source('dsld','label',1,'synthetic.json',{'pointer':''},{'id':1},'label_information',run='fixture-capture')
        self.assertEqual((r,s),(r2,s2));self.assertEqual(len(p.tables['capture_events']),1)
        _,s3=p.source('dsld','label',1,'synthetic.json',{'pointer':''},{'id':1},'label_information',run='second-real-capture')
        self.assertEqual(s,s3);self.assertEqual(len(p.tables['capture_events']),2)
    def test_changed_payload_creates_new_snapshot_same_record(self):
        p,r,s=fixture();b=b'{"changed":true}';p.inputs['updated.json']={'sha256':sha(b),'bytes':len(b)}
        r2,s2=p.source('dsld','label',1,'updated.json',{'pointer':''},{'changed':True},'label_information',run='new-capture')
        self.assertEqual(r,r2);self.assertNotEqual(s,s2);self.assertIn(s,p.tables['snapshots'])
    def test_different_native_id_never_merged_by_content(self):
        p,r,s=fixture();r2,s2=p.source('dsld','label',2,'synthetic.json',{'pointer':''},{'id':2},'label_information',run='fixture-capture')
        self.assertNotEqual(r,r2);self.assertNotEqual(s,s2)
    def test_same_key_conflicting_row_fails(self):
        p,r,s=fixture();row=copy.deepcopy(p.tables['source_records'][r]);row['source_role']='changed'
        row.pop('id');row.pop('contract_version')
        with self.assertRaises(ValueError):p.add('source_records',r,**row)
    def test_validator_rejects_broken_fk_and_extra_fields(self):
        p,r,s=fixture();validate_tables(p.tables,p.contract)
        p.tables['snapshots'][s]['record_id']='absent'
        with self.assertRaises(ValueError):validate_tables(p.tables,p.contract)
        p.tables['snapshots'][s]['record_id']=r;p.tables['snapshots'][s]['invented']=True
        with self.assertRaises(ValueError):validate_tables(p.tables,p.contract)
    def test_pointer_distinguishes_typed_locator_and_escapes(self):
        self.assertEqual(pointer({'a/b':[{'~x':None}]},'/a~1b/0/~0x'),None)

class ActualPilotIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=Pilot(ROOT).build()
    def test_all_sources_preserved_no_approvals(self):
        p=self.p
        self.assertEqual({r['source_system'] for r in p.tables['source_records'].values()},{'dsld','pubchem','rxnorm','mesh','natmedpro','reddit'})
        self.assertFalse(p.tables['canonical_identities']);self.assertFalse(p.tables['comparison_groups'])
        self.assertTrue(all(r['review_state']=='needs_review' for r in p.tables['mapping_assertions'].values()))
    def test_full_build_replay_is_byte_identical(self):
        repeated=Pilot(ROOT).build()
        for table in self.p.tables:
            self.assertEqual(encode(self.p.tables[table]),encode(repeated.tables[table]),table)
    def test_clinical_fields_pending_and_no_invented_dose(self):
        c=next(r for r in self.p.tables['assertions'].values() if r['kind']=='clinical')
        self.assertEqual(c['source_review']['state'],'pending');self.assertIsNone(c['original_fields']['dose']['value'])
        self.assertIsNone(c['original_fields']['dose']['route'])
    def test_evidence_mutation_and_parent_amount_guard(self):
        p=self.p;tables=copy.deepcopy(p.tables)
        a=next(r for r in tables['assertions'].values() if r['kind']=='composition')
        f=next(r for r in tables['occurrences'].values() if r['role']=='form' and r['snapshot_id']==a['snapshot_id'])
        a['occurrence_id']=f['id']
        with self.assertRaises(ValueError):validate_tables(tables,p.contract)
    def test_reference_approval_and_topic_mutations_rejected(self):
        p=self.p;tables=copy.deepcopy(p.tables)
        r=next(r for r in tables['source_references'].values() if r['identifier_state']=='missing')
        r['resolution_state']='resolved'
        with self.assertRaises(ValueError):validate_tables(tables,p.contract)
        tables=copy.deepcopy(p.tables);m=next(iter(tables['mapping_assertions'].values()));m['review_state']='accepted'
        with self.assertRaises(ValueError):validate_tables(tables,p.contract)
        tables=copy.deepcopy(p.tables);t=next(r for r in tables['topic_associations'].values() if r['mention_scope']=='thread_context');t['mention_scope']='own_text'
        with self.assertRaises(ValueError):validate_tables(tables,p.contract)
    def test_no_form_quantity_transformations(self):
        for a in self.p.tables['assertions'].values():
            if a['occurrence_id'] and self.p.tables['occurrences'][a['occurrence_id']]['role'] in ['form','other_form']:
                self.assertEqual(a['kind'],'presence')

if __name__=='__main__':unittest.main()
