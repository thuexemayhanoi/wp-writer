"""Pipeline board: every in-flight article sits in exactly one state WRITING -> QA -> READY -> PUBLISHING -> VERIFIED."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from pipeline_board import STATES, classify, markdown  # noqa: E402

SHA = 'a' * 64
LEASED = {'NT-000001': {'slot': 'W1', 'session': 's-x'}}


class ClassifyTests(unittest.TestCase):
    def test_leased_without_draft_is_writing(self):
        self.assertEqual(classify('NT-000001', None, None, None, None, LEASED)[0], 'WRITING')

    def test_not_leased_without_draft_is_not_in_flight(self):
        self.assertEqual(classify('NT-000002', None, None, None, None, LEASED)[0], None)

    def test_draft_without_record_is_qa(self):
        self.assertEqual(classify('NT-000001', SHA, None, None, None, LEASED)[0], 'QA')
        stale = {'status': 'PASS', 'source_sha256': 'b' * 64}
        self.assertEqual(classify('NT-000001', SHA, stale, None, None, LEASED)[0], 'QA')

    def test_pass_with_receipt_is_ready(self):
        qa = {'status': 'PASS', 'source_sha256': SHA}
        self.assertEqual(classify('NT-000001', SHA, qa, {'sha256': SHA}, None, LEASED)[0], 'READY')

    def test_pass_without_receipt_is_held(self):
        qa = {'status': 'PASS', 'source_sha256': SHA}
        self.assertEqual(classify('NT-000001', SHA, qa, {'sha256': 'b' * 64}, None, LEASED)[0], 'HELD')

    def test_fail_is_repair_or_held_by_triage_class(self):
        for hold, state in (('WRITER_REPAIR', 'REPAIR'), ('INFRA_PENDING', 'REPAIR'), ('REAL_RISK', 'HELD'), (None, 'HELD')):
            qa = {'status': 'FAIL', 'source_sha256': SHA, 'errors': ['x'], 'triage': {'hold_class': hold}}
            self.assertEqual(classify('NT-000001', SHA, qa, {'sha256': SHA}, None, LEASED)[0], state, hold)

    def test_ledger_phases(self):
        for phase, state in (('POST_INTENT', 'PUBLISHING'), ('VERIFY_PENDING', 'PUBLISHING'),
                             ('NEEDS_RECONCILE', 'PUBLISHING'), ('VERIFIED', 'VERIFIED')):
            self.assertEqual(classify('NT-000001', SHA, None, None, {'phase': phase, 'status': 'publish'}, {})[0], state)

    def test_markdown_lists_counts_and_unverified_items(self):
        board = {'at': 'now', 'counts': {s: 0 for s in STATES}, 'ready_backlog': 1,
                 'items': [{'topic_id': 'NT-000001', 'state': 'READY', 'slot': 'W1', 'session': 's', 'reason': 'ok | fine'},
                           {'topic_id': 'NT-000002', 'state': 'VERIFIED', 'reason': 'publish'}]}
        board['counts']['READY'] = 1
        text = markdown(board)
        self.assertIn('| READY | 1 |', text)
        self.assertIn('NT-000001 | READY | W1', text)
        self.assertNotIn('NT-000002 | VERIFIED', text)
        self.assertIn('ok / fine', text)


if __name__ == '__main__':
    unittest.main()
