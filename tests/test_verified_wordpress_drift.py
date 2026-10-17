"""Read-only external status drift guard for previously VERIFIED WordPress posts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import load, topics
from publisher import confirmed_post_drift


class ConfirmedWordPressDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows={x['topic_id']: x for x in topics()}
        cls.ledger=load('data/state/publication-ledger.json')['posts']

    def test_externally_promoted_legacy_draft_is_not_silent(self):
        topic=self.rows['NT-000079']
        # Simulate the original draft snapshot before explicit reconciliation.
        old={**self.ledger['NT-000079'], 'status':'draft', 'expected_status':'draft'}
        # Real REST readback: WordPress #3882 was made public externally.
        live=[{'resource':'posts','id':3882,'status':'publish',
               'slug':topic['proposed_slug'],'categories':[159],
               'link':topic['canonical_target']}]
        issue=confirmed_post_drift(topic,old,live)
        self.assertEqual(issue['status'],'EXTERNAL_WORDPRESS_DRIFT')
        self.assertEqual(issue['wp_id'],3882)
        self.assertEqual(issue['differences']['status'],
                         {'ledger':'draft','wordpress':'publish'})
        self.assertIn('never create/update',issue['action'])

    def test_owner_reconciled_promotion_matches_verified_live_state(self):
        topic=self.rows['NT-000079']
        record=self.ledger['NT-000079']
        self.assertTrue(record['external_promotion_not_via_qa'])
        # Draft meta was repaired on 2026-10-17 (SEO 75 -> 95); the live Yoast
        # meta still has to be set by the owner, which the provenance records.
        self.assertEqual(record['editorial_qa_status'], 'PASS')
        self.assertEqual(record['editorial_qa_seo_score'], 95)
        self.assertIn('LIVE #3882', record['provenance'])
        self.assertEqual(record['wp_id'], 3882)
        live=[{'resource':'posts','id':3882,'status':'publish',
               'slug':topic['proposed_slug'],'categories':[159],
               'link':topic['canonical_target']}]
        self.assertIsNone(confirmed_post_drift(topic, record, live))

    def test_verified_published_post_matches_readback(self):
        topic=self.rows['NT-000037']
        old=self.ledger['NT-000037']
        live=[{'resource':'posts','id':3888,'status':'publish',
               'slug':topic['proposed_slug'],'categories':[160],
               'link':topic['canonical_target']}]
        self.assertIsNone(confirmed_post_drift(topic,old,live))

    def test_wrong_category_is_reported_without_writing(self):
        topic=self.rows['NT-000047']
        old=self.ledger['NT-000047']
        live=[{'resource':'posts','id':3890,'status':'publish',
               'slug':topic['proposed_slug'],'categories':[69],
               'link':topic['canonical_target']}]
        issue=confirmed_post_drift(topic,old,live)
        self.assertEqual(issue['differences']['categories'],
                         {'ledger':[161],'wordpress':[69]})

    def test_unknown_wordpress_post_is_reported_not_recreated(self):
        topic=self.rows['NT-000037']
        old=self.ledger['NT-000037']
        issue=confirmed_post_drift(topic,old,[])
        self.assertEqual(issue['status'],'EXTERNAL_WORDPRESS_DRIFT')
        self.assertIn('missing',issue['reason'])

    def test_unverified_receipts_are_not_treated_as_confirmed(self):
        topic=self.rows['NT-000037']
        old={**self.ledger['NT-000037'],'phase':'POST_INTENT'}
        self.assertIsNone(confirmed_post_drift(topic,old,[]))


if __name__=='__main__':
    unittest.main()
