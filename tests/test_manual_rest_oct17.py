"""Three explicitly manual WPVibe posts must not be silently queued as new Writer jobs."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import load,topics
from publisher import daily_created_count
from taxonomy_sync import by_key,resolve


class ManualRestCanaryTests(unittest.TestCase):
    def test_three_public_manually_written_posts_are_registered_exactly(self):
        records=load('data/state/publication-ledger.json')['posts']
        rows={t['topic_id']:t for t in topics()}
        registry=by_key()
        live=load('data/existing-taxonomy.json')['items']
        for topic_id,wp_id,term_id in (
            ('NT-000066',3930,175),
            ('NT-000056',3931,176),
            ('NT-000058',3932,172),
        ):
            with self.subTest(topic_id=topic_id):
                rec=records[topic_id]
                topic=rows[topic_id]
                self.assertEqual(rec['phase'],'VERIFIED')
                self.assertEqual(rec['status'],'publish')
                self.assertEqual(rec['expected_status'],'publish')
                self.assertEqual(rec['wp_id'],wp_id)
                self.assertEqual(rec['url'],topic['canonical_target'])
                self.assertEqual(rec['category_id'],term_id)
                self.assertEqual(resolve(topic['taxonomy_key'],registry,live),term_id)
                self.assertEqual(rec['editorial_qa_status'],'NOT_RUN')
                self.assertIn('manual',rec['provenance'].lower())
                self.assertNotIn('github-publisher',rec['run_id'])
                self.assertTrue(rec['first_paragraph'])
                self.assertTrue(rec['meta_title'])
                self.assertTrue(rec['meta_description'])

    def test_manual_posts_count_toward_daily_create_ceiling(self):
        ledger=load('data/state/publication-ledger.json')
        self.assertGreaterEqual(daily_created_count(ledger,'2026-10-17'),3)

    def test_manual_posts_cannot_activate_unattended_publisher(self):
        policy=load('config/production-policy.json')
        self.assertEqual(policy['mode'],'dry_run')
        self.assertIs(policy['production_enabled'],False)
        self.assertIs(policy['acceptance_passed'],False)


if __name__=='__main__':
    unittest.main()
