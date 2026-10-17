"""The stock ladder counts every topic row in exactly one stage and never adds history to the reserve."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from topic_stock import ROW_STAGES, build_stock

AT = dt.datetime(2026, 10, 17, 15, 0, tzinfo=dt.timezone.utc)
FUTURE = (AT + dt.timedelta(hours=6)).isoformat()
PAST = (AT - dt.timedelta(hours=6)).isoformat()


def row(topic_id, status='PLANNED', **extra):
    return {'topic_id': topic_id, 'topic_qa_status': status, 'origin_id': 'ORIGIN-' + topic_id, **extra}


class StockTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row('NT-1', 'RESEARCH'), row('NT-2', 'REJECTED'), row('NT-3'), row('NT-4'),
                     row('NT-5', hold='sources unreadable'), row('NT-6'), row('NT-7'), row('NT-8'),
                     row('NT-9'), row('NT-10')]
        self.registry = {'leases': {'W1': {'session': 's', 'topic_ids': ['NT-6'], 'expires_at': FUTURE},
                                    'W2': {'session': 'old', 'topic_ids': ['NT-4'], 'expires_at': PAST}},
                         'submissions': {'NT-8': {'sha256': 'a'}}}
        self.ledger = {'posts': {'NT-9': {'phase': 'VERIFIED', 'status': 'publish'},
                                 'NT-10': {'phase': 'VERIFIED', 'status': 'draft'}}}
        self.qa = {'NT-7': {'status': 'REVIEW'}, 'NT-8': {'status': 'PASS'}}
        self.discovery = {'proposals': {'NTD-a': {}, 'NTD-b': {}, 'ORIGIN-NT-1': {}}}

    def stock(self, **override):
        args = dict(rows=self.rows, registry=self.registry, ledger=self.ledger, qa_by_id=self.qa,
                    draft_ids={'NT-7', 'NT-8'}, discovery=self.discovery,
                    policy={'min_claimable_queue': 100}, at=AT)
        args.update(override)
        return build_stock(**args)

    def test_every_row_is_in_exactly_one_stage(self):
        stock = self.stock()
        self.assertEqual(sum(stock['stages'][name] for name in ROW_STAGES), len(self.rows))
        self.assertEqual(stock['stages'], {'IDEA': 2, 'RESEARCH': 1, 'REJECTED': 1, 'PLANNED': 2,
            'PLANNED_HOLD': 1, 'CLAIMED': 1, 'AUTHORED': 1, 'QA_PASS': 1, 'PUBLISHED': 1, 'WP_DRAFT': 1})

    def test_ready_stock_excludes_everything_a_writer_cannot_take(self):
        stock = self.stock()
        self.assertEqual(stock['ready_ids'], ['NT-3', 'NT-4'])  # the expired lease frees NT-4; NT-6 is leased
        self.assertEqual(stock['on_hold'], {'NT-5': 'sources unreadable'})
        self.assertEqual(stock['lifetime_planned'], 8)

    def test_research_is_needed_below_the_reserve_and_the_shortfall_is_exact(self):
        stock = self.stock()
        self.assertTrue(stock['needs_research'])
        self.assertEqual(stock['shortfall'], 98)
        full = self.stock(rows=[row('NT-%d' % i) for i in range(120)], registry={}, ledger={}, qa_by_id={},
                          draft_ids=set(), discovery={})
        self.assertFalse(full['needs_research'])
        self.assertEqual(full['shortfall'], 0)
        self.assertEqual(full['room_to_target_max'], 80)

    def test_unknown_status_is_never_ready(self):
        stock = self.stock(rows=[row('NT-1', 'WEIRD')], registry={}, ledger={}, qa_by_id={}, draft_ids=set())
        self.assertEqual(stock['ready'], 0)
        self.assertEqual(stock['stages']['RESEARCH'], 1)

    def test_an_unverified_post_intent_is_not_claimable(self):
        stock = self.stock(rows=[row('NT-1')], registry={}, qa_by_id={}, draft_ids=set(),
                           ledger={'posts': {'NT-1': {'phase': 'POST_INTENT'}}})
        self.assertEqual((stock['ready'], stock['stages']['QA_PASS']), (0, 1))


if __name__ == '__main__':
    unittest.main()
