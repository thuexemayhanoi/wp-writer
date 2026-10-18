"""Refill may only report success when researched PLANNED topics actually exist."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import refill

class DummyState:
    def remember(self,paths):pass
    def persist(self,paths,message=None):pass

class RefillLivenessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'data/candidates').mkdir(parents=True)

    def test_claimable_count_excludes_leases_submissions_and_wordpress_posts(self):
        rows=[{'topic_id':f'NT-{i:06d}','topic_qa_status':'PLANNED'} for i in range(1,6)]
        registry={'leases':{'W1':{'session':'writer-1','topic_ids':['NT-000001'],
                                   'expires_at':'2099-01-01T00:00:00+00:00'}},
                  'submissions':{'NT-000002':{'sha256':'hash'}}}
        ledger={'posts':{'NT-000003':{'phase':'VERIFIED'}}}
        self.assertEqual(refill.claimable_count(rows,registry,ledger),2)

    def test_expired_unsubmitted_lease_does_not_block_refill(self):
        rows=[{'topic_id':'NT-000001','topic_qa_status':'PLANNED'}]
        registry={'leases':{'W1':{'session':'writer-1','topic_ids':['NT-000001'],
                                   'expires_at':'2000-01-01T00:00:00+00:00'}},
                  'submissions':{}}
        self.assertEqual(refill.claimable_count(rows,registry,{'posts':{}}),1)
        registry['submissions']['NT-000001']={'sha256':'hash'}
        self.assertEqual(refill.claimable_count(rows,registry,{'posts':{}}),0)

    def test_no_candidates_fails_instead_of_green_noop(self):
        with patch.object(refill,'ROOT',self.root),\
             patch.object(refill,'RemoteState',DummyState),\
             patch.object(refill,'load',lambda path,default=None:
                          {'min_claimable_queue':100} if path=='config/production-policy.json' else {'batches':{}}),\
             patch.object(refill,'topics',lambda:[{'topic_qa_status':'PLANNED'}]*8):
            with self.assertRaisesRegex(SystemExit,'NEEDS_TOPIC_EXPANSION'):
                refill.run()

    def test_queue_above_threshold_needs_no_refill(self):
        with patch.object(refill,'ROOT',self.root),\
             patch.object(refill,'load',lambda path,default=None: {'min_claimable_queue':100}),\
             patch.object(refill,'topics',lambda:[{'topic_qa_status':'PLANNED'}]*refill.refill_policy()['trigger_below_ready']),\
             patch.object(refill,'RemoteState',DummyState):
            self.assertIsNone(refill.run())

if __name__=='__main__':unittest.main()
