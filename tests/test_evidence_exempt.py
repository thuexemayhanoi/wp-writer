"""Review evidence covers baseline content; factory-published posts stay under collision gates."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import SITE
from taxonomy_sync import by_key
from topic_factory import gate


class EvidenceExemptTests(unittest.TestCase):
    def setUp(self):
        self.tax = list(by_key().values())
        self.topic = {
            'topic_id': 'NT-999999', 'title': 'Bản đồ nhu cầu độc lập', 'primary_keyword': 'nhu cầu độc lập',
            'search_intent': 'educational', 'intent_key': 'unique-intent', 'taxonomy_key': 'reviews',
            'proposed_slug': 'nhu-cau-doc-lap', 'canonical_target': SITE + '/nhu-cau-doc-lap/',
            'outline': ['a', 'b', 'c', 'd', 'e'],
            'research': {'reviewer': 't', 'difference_summary': 'd', 'usefulness': 'u',
                         'scope_exclusions': ['x'], 'reviewed_content_hashes': {'1': 'h1'},
                         'reviewed_existing_ids': [1]}}
        self.baseline = {'id': 1, 'title': 'Bản đồ nhu cầu khác hẳn', 'slug': 'khac',
                         'content_hash': 'h1', 'title_hash': 'x1'}
        self.factory = {'id': 2, 'title': 'Bản đồ nhu cầu độc lập mở rộng', 'slug': 'mo-rong',
                        'content_hash': 'h2', 'title_hash': 'x2'}

    def gate(self, *inventory):
        return gate(self.topic, [self.topic], list(inventory), self.tax)

    def test_baseline_evidence_passes(self):
        self.assertEqual(self.gate(self.baseline)['status'], 'PASS')

    def test_unreviewed_new_content_still_needs_review(self):
        result = self.gate(self.baseline, self.factory)
        self.assertEqual(result['status'], 'REVIEW')
        self.assertIn('nearest full content not reviewed', result['review'])

    def test_factory_published_content_is_exempt_from_review_evidence(self):
        result = self.gate(self.baseline, {**self.factory, 'evidence_exempt': True})
        self.assertEqual(result['status'], 'PASS')

    def test_exempt_content_still_collides_on_identity(self):
        result = self.gate(self.baseline, {**self.factory, 'evidence_exempt': True, 'slug': 'nhu-cau-doc-lap'})
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any(e.startswith('existing URL collision') for e in result['errors']))

    def test_changed_baseline_content_is_still_stale(self):
        result = self.gate({**self.baseline, 'content_hash': 'edited'})
        self.assertEqual(result['status'], 'REVIEW')
        self.assertIn('reviewed full-content evidence stale or missing: 1=edited', result['review'])


if __name__ == '__main__':
    unittest.main()
