"""Guard manually published WPVibe canaries against accidental replay.

External manual HTML is NOT the canonical GitHub Markdown renderer. This
offline test checks the topic/receipt/identity, not fabricated WordPress HTML
equivalence. Live readback remains a separate operational check.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from common import load, topics, visible
from qa import read_article
from taxonomy_sync import by_key, resolve


class ManualPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load('data/state/publication-ledger.json')['posts']
        cls.submissions = load('data/state/writer-claims.json')['submissions']
        cls.topics = {t['topic_id']: t for t in topics()}
        cls.registry = by_key()
        cls.live = load('data/existing-taxonomy.json')['items']

    def test_manual_canaries_are_verified_instead_of_queued(self):
        for topic_id, wp_id, category_id in (
            ('NT-000037', 3888, 160),
            ('NT-000047', 3890, 161),
        ):
            with self.subTest(topic_id=topic_id):
                record = self.ledger[topic_id]
                topic = self.topics[topic_id]
                self.assertEqual(record['phase'], 'VERIFIED')
                self.assertEqual(record['status'], 'publish')
                self.assertEqual(record['expected_status'], 'publish')
                self.assertEqual(record['wp_id'], wp_id)
                self.assertEqual(record['category_id'], category_id)
                self.assertEqual(record['url'], topic['canonical_target'])
                self.assertEqual(record['slug'], topic['proposed_slug'])
                self.assertEqual(record['category_resolution'], 'EXACT')
                self.assertIn('manual WPVibe', record['provenance'])

    def test_writer_receipts_match_unchanged_source(self):
        for topic_id in ('NT-000037', 'NT-000047'):
            with self.subTest(topic_id=topic_id):
                record = self.ledger[topic_id]
                path = ROOT / 'posts/drafts' / (topic_id + '.md')
                meta, body, source_hash = read_article(path)
                self.assertEqual(source_hash, record['source_hash'])
                self.assertEqual(source_hash, self.submissions[topic_id]['sha256'])
                self.assertEqual(meta['topic_id'], topic_id)
                self.assertEqual(meta['taxonomy_key'],
                                 self.topics[topic_id]['taxonomy_key'])
                self.assertEqual(meta['meta_title'], record['meta_title'])
                self.assertEqual(meta['meta_description'], record['meta_description'])
                self.assertEqual(record['first_paragraph'],
                                 visible(body.split('\n\n')[0]))
                self.assertEqual(len(record['visible_hash']), 64)

    def test_wordpress_child_categories_have_real_parent_hierarchy(self):
        for topic_id, category_id, parent_id in (
            ('NT-000037', 160, 157),
            ('NT-000047', 161, 159),
        ):
            with self.subTest(topic_id=topic_id):
                key = self.topics[topic_id]['taxonomy_key']
                term = self.registry[key]
                self.assertEqual(term['status'], 'ACTIVE')
                self.assertEqual(term['wordpress_term_id'], category_id)
                self.assertEqual(term['wordpress_parent_id'], parent_id)
                self.assertEqual(resolve(key, self.registry, self.live), category_id)

    def test_manual_wp_post_did_not_fake_publisher_acceptance(self):
        policy = load('config/production-policy.json')
        self.assertEqual(policy['mode'], 'production')
        self.assertFalse(policy['acceptance_passed'])


if __name__ == '__main__':
    unittest.main()
