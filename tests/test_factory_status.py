"""factory_status.py: a research branch is ingested when intake accepted every batch of its checkpoint."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('factory_status', ROOT / 'agent-tools/factory_status.py')
factory_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory_status)

LEDGER = {'data/candidates/s-0001.jsonl': {'sha256': 'a' * 64, 'research_branch': 'research/s', 'research_commit': 'c1'}}


class IngestedTests(unittest.TestCase):
    def test_the_head_that_intake_accepted_is_ingested_without_reading_anything(self):
        def unreachable(*args):
            raise AssertionError('no checkpoint read needed')
        self.assertTrue(factory_status.is_ingested('research/s', 'c1', LEDGER, unreachable))

    def test_a_checkpoint_only_push_after_acceptance_stays_ingested(self):
        checkpoint = {'batches': [{'path': 'data/candidates/s-0001.jsonl', 'sha256': 'a' * 64, 'final': True}]}
        self.assertTrue(factory_status.is_ingested('research/s', 'c2', LEDGER, lambda *a: checkpoint))

    def test_a_new_batch_that_intake_has_not_seen_is_not_ingested(self):
        checkpoint = {'batches': [{'path': 'data/candidates/s-0001.jsonl', 'sha256': 'a' * 64},
                                  {'path': 'data/candidates/s-0002.jsonl', 'sha256': 'b' * 64}]}
        self.assertFalse(factory_status.is_ingested('research/s', 'c2', LEDGER, lambda *a: checkpoint))

    def test_an_edited_batch_is_not_ingested(self):
        checkpoint = {'batches': [{'path': 'data/candidates/s-0001.jsonl', 'sha256': 'f' * 64}]}
        self.assertFalse(factory_status.is_ingested('research/s', 'c2', LEDGER, lambda *a: checkpoint))

    def test_an_unreadable_checkpoint_is_not_ingested(self):
        self.assertFalse(factory_status.is_ingested('research/other', 'c9', LEDGER, lambda *a: None))


if __name__ == '__main__':
    unittest.main()
