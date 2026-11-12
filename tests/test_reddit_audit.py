import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_reddit import passage_valid,groups
from review_dsld_name_groups import sha

class RedditAuditTests(unittest.TestCase):
    def pair(self):
        r={'text':'one two three','content_hash':sha(b'one two three'),'source':'reddit','evidence_role':'user_report','source_url':'https://old.reddit.com/x','record_type':'comment','mention_scope':'thread_context','thread_id':'t3_a','parent_id':'t3_a','supplements':[]}
        p={k:v for k,v in r.items() if k not in ['text','content_hash']}
        p.update(text='two three',word_start=1,word_count=2,section_index=0,section='discussion',source_content_hash=r['content_hash'])
        return p,r
    def test_source_window_binding(self):
        p,r=self.pair();self.assertTrue(passage_valid(p,r));p['word_start']=0;self.assertFalse(passage_valid(p,r))
    def test_inherited_scope_not_promoted_to_own_text(self):
        p,r=self.pair();p['mention_scope']='own_text';self.assertFalse(passage_valid(p,r))
    def test_user_report_not_promoted_to_clinical(self):
        p,r=self.pair();p['evidence_role']='clinical_reference';self.assertFalse(passage_valid(p,r))
    def test_duplicate_text_does_not_remove_records(self):
        rows=[{'id':'a','text':'same'},{'id':'b','text':'same'}]
        self.assertEqual(groups(rows,lambda r:r['text']),[['a','b']]);self.assertEqual(len(rows),2)

if __name__=='__main__':unittest.main()
