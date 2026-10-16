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
             patch.object(refill,'topics',lambda:[{'topic_qa_status':'PLANNED'}]*100),\
             patch.object(refill,'RemoteState',DummyState):
            self.assertIsNone(refill.run())

if __name__=='__main__':unittest.main()
