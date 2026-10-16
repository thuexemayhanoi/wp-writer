"""Regression gates for the two owner-approved, externally published WP canaries.

The ledger must prevent replay of their Topic IDs, retain source hashes,
and prove that the manually rendered HTML has the same visible text as the
canonical Markdown renderer. No WordPress connection or publishing here.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from common import SITE, digest, load, topics, visible
from publisher import post_html
from qa import read_article
from taxonomy_sync import by_key, resolve


class ManuallyPublishedWordPressCanaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load('data/state/publication-ledger.json')['posts']
        cls.submissions = load('data/state/writer-claims.json')['submissions']
        cls.topics = {t['topic_id']:t for t in topics()}
        cls.registry = by_key()
        cls.live = load('data/existing-taxonomy.json')['items']

    def test_canaries_are_already_verified_not_queued(self):
        for topic_id, wp_id, term_id in (
            ('NT-000037',3888,160),('NT-000047',3890,161)):
            with self.subTest(topic_id=topic_id):
                record = self.ledger[topic_id]
                self.assertEqual(record['phase'], 'VERIFIED')
                self.assertEqual(record['expected_status'], 'publish')
                self.assertEqual(record['status'], 'publish')
                self.assertEqual(record['wp_id'], wp_id)
                self.assertEqual(record['category_id'], term_id)
                self.assertEqual(record['url'], self.topics[topic_id]['canonical_target'])
                self.assertEqual(record['slug'], self.topics[topic_id]['proposed_slug'])
                self.assertEqual(record['category_resolution'], 'EXACT')
                self.assertIn('manual WPVibe', record['provenance'])

    def test_unmodified_source_receipts_and_public_body_identity(self):
        for topic_id in ('NT-000037','NT-000047'):
            with self.subTest(topic_id=topic_id):
                record = self.ledger[topic_id]
                path = ROOT / 'posts/drafts' / (topic_id+'.md')
                meta, body, sha = read_article(path)
                self.assertEqual(sha, record['source_hash'])
                self.assertEqual(sha, self.submissions[topic_id]['sha256'])
                self.assertEqual(meta['topic_id'], topic_id)
                self.assertEqual(meta['taxonomy_key'], self.topics[topic_id]['taxonomy_key'])
                self.assertEqual(record['meta_title'],meta['meta_title'])
                self.assertEqual(record['meta_description'],meta['meta_description'])
                self.assertEqual(record['visible_hash'],
                                 digest(visible(post_html(self.topics[topic_id], body, sha))))
                self.assertEqual(record['first_paragraph'],visible(body.split('\n\n')[0]))

    def test_new_wordpress_categories_are_strictly_resolved(self):
        for topic_id, term_id, parent_id in (
            ('NT-000037',160,157),('NT-000047',161,159)):
            with self.subTest(topic_id=topic_id):
                term_key = self.topics[topic_id]['taxonomy_key']
                record = self.registry[term_key]
                self.assertEqual(record['status'],'ACTIVE')
                self.assertEqual(record['wordpress_term_id'],term_id)
                self.assertEqual(record['wordpress_parent_id'],parent_id)
                self.assertEqual(resolve(term_key,self.registry,self.live),term_id)

    def test_manual_publication_did_not_activate_unattended_production(self):
        policy = load('config/production-policy.json')
        self.assertEqual(policy['mode'],'dry_run')
        self.assertFalse(policy['production_enabled'])


if __name__ == '__main__':
    unittest.main()
