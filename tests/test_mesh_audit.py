import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_mesh import triple_key

class MeshAuditTests(unittest.TestCase):
    def triple(self,obj):return {'record':{'value':'record1'},'subject':{'type':'uri','value':'s'},'predicate':{'type':'uri','value':'p'},'object':obj}
    def test_literal_language_preserved(self):
        self.assertNotEqual(triple_key(self.triple({'type':'literal','value':'same','xml:lang':'en'})),triple_key(self.triple({'type':'literal','value':'same','xml:lang':'fr'})))
    def test_uri_not_literal(self):
        self.assertNotEqual(triple_key(self.triple({'type':'uri','value':'x'})),triple_key(self.triple({'type':'literal','value':'x'})))
    def test_batch_record_context_not_part_of_triple_identity(self):
        a=self.triple({'type':'literal','value':'x'});b={**a,'record':{'value':'record2'}}
        self.assertEqual(triple_key(a),triple_key(b))

if __name__=='__main__':unittest.main()
