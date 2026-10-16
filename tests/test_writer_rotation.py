"""Lease rotation must not wait for WordPress when a draft is admitted and QA-PASS."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import writer_session
from common import digest


class WriterRotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        folder=self.root/'posts/drafts'
        folder.mkdir(parents=True)
        self.topic_id='NT-000075'
        self.meta={'topic_id':self.topic_id,'writer_slot':'W2','writer_session':'s-gpt6-w2-20261016'}
        self.path=folder/(self.topic_id+'.md')
        self.content='---\n'+json.dumps(self.meta)+'\n---\n\nA harmless draft for the test.'
        self.path.write_text(self.content)
        self.registry={'submissions':{self.topic_id:{
            'sha256':digest(self.content),'session':self.meta['writer_session'],'slot':'W2'}}}
        self.rows=[{'topic_id':self.topic_id,'topic_qa_status':'PLANNED'},
                   {'topic_id':'NT-000047','topic_qa_status':'PLANNED'}]
        self.ledger={'posts':{}}

    def tearDown(self):
        self.tmp.cleanup()

    def finished(self,status='PASS'):
        with patch.object(writer_session,'ROOT',self.root),patch('qa.evaluate',return_value={'status':status}):
            return writer_session.writer_finished(self.topic_id,self.registry,self.ledger,self.rows)

    def test_immutable_qa_pass_releases_without_wordpress_post(self):
        self.assertTrue(self.finished())
        slot,registry=writer_session.claim(
            {'submissions':self.registry['submissions'],'leases':{}},
            self.rows,self.meta['writer_session'],slot='W2',count=1,
            completed_ids={self.topic_id})
        self.assertEqual(slot,'W2')
        self.assertEqual(registry['leases']['W2']['topic_ids'],['NT-000047'])

    def test_qa_review_or_fail_stays_with_writer(self):
        self.assertFalse(self.finished('REVIEW'))
        self.assertFalse(self.finished('FAIL'))
        slot,registry=writer_session.claim(
            {'submissions':self.registry['submissions'],'leases':{}},
            self.rows,self.meta['writer_session'],slot='W2',count=1)
        self.assertEqual(registry['leases'][slot]['topic_ids'],[self.topic_id])

    def test_tampered_draft_does_not_release(self):
        self.path.write_text(self.content+'\nAn unauthorized change.')
        self.assertFalse(self.finished())

    def test_wrong_owner_metadata_does_not_release(self):
        self.meta['writer_session']='different-session'
        self.path.write_text('---\n'+json.dumps(self.meta)+'\n---\n\nA harmless draft for the test.')
        self.registry['submissions'][self.topic_id]['sha256']=digest(self.path.read_text())
        self.assertFalse(self.finished())

    def test_missing_receipt_never_releases(self):
        self.registry['submissions'].clear()
        self.assertFalse(self.finished())

    def test_wp_verified_is_always_terminal(self):
        self.ledger['posts'][self.topic_id]={'phase':'VERIFIED','wp_id':3882}
        self.assertTrue(self.finished('REVIEW'))

    def test_uncertain_post_with_mismatched_source_is_blocked(self):
        self.ledger['posts'][self.topic_id]={'phase':'NEEDS_RECONCILE','source_hash':'other-source'}
        self.assertFalse(self.finished())


if __name__=='__main__':
    unittest.main()
