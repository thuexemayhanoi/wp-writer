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

    def test_a_factory_post_published_after_the_research_is_not_demanded_as_evidence(self):
        self.topic['research']['reviewed_at'] = '2026-10-17T19:00:00+00:00'
        late = {**self.factory, 'factory_published_at': '2026-10-17T19:30:00+00:00'}
        self.assertEqual(self.gate(self.baseline, late)['status'], 'PASS')

    def test_a_factory_post_that_existed_when_the_researcher_read_is_still_demanded(self):
        self.topic['research']['reviewed_at'] = '2026-10-17T19:00:00+00:00'
        early = {**self.factory, 'factory_published_at': '2026-10-17T18:00:00+00:00'}
        result = self.gate(self.baseline, early)
        self.assertEqual(result['status'], 'REVIEW')
        self.assertIn('nearest full content not reviewed', result['review'])

    def test_a_page_without_the_factory_stamp_is_never_waived(self):
        self.topic['research']['reviewed_at'] = '2026-10-17T19:00:00+00:00'
        self.assertEqual(self.gate(self.baseline, self.factory)['status'], 'REVIEW')

    def test_without_reviewed_at_nothing_is_waived(self):
        late = {**self.factory, 'factory_published_at': '2026-10-17T19:30:00+00:00'}
        self.assertEqual(self.gate(self.baseline, late)['status'], 'REVIEW')

    def test_the_waiver_does_not_hide_identity_collisions(self):
        self.topic['research']['reviewed_at'] = '2026-10-17T19:00:00+00:00'
        late = {**self.factory, 'factory_published_at': '2026-10-17T19:30:00+00:00', 'slug': 'nhu-cau-doc-lap'}
        result = self.gate(self.baseline, late)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any(e.startswith('existing URL collision') for e in result['errors']))

    def test_stamp_factory_posts_uses_the_ledger_verification_time(self):
        from topic_factory import stamp_factory_posts
        ledger = {'posts': {'NT-1': {'wp_id': 2, 'verified_at': '2026-10-17T19:12:13+00:00'},
                            'NT-2': {'wp_id': None}}}
        out = stamp_factory_posts([self.baseline, self.factory], ledger)
        self.assertNotIn('factory_published_at', out[0])
        self.assertEqual(out[1]['factory_published_at'], '2026-10-17T19:12:13+00:00')

    def test_changed_baseline_content_is_still_stale(self):
        result = self.gate({**self.baseline, 'content_hash': 'edited'})
        self.assertEqual(result['status'], 'REVIEW')
        self.assertIn('reviewed full-content evidence stale or missing: 1=edited', result['review'])

    def test_rereviewed_page_keeps_both_versions_covered(self):
        self.topic['research']['reviewed_content_hashes'] = {'1': ['h1', 'edited']}
        for current in ('h1', 'edited'):
            self.assertEqual(self.gate({**self.baseline, 'content_hash': current})['status'], 'PASS')

    def test_a_third_version_of_the_page_is_still_stale(self):
        self.topic['research']['reviewed_content_hashes'] = {'1': ['h1', 'edited']}
        result = self.gate({**self.baseline, 'content_hash': 'edited-again'})
        self.assertEqual(result['status'], 'REVIEW')
        self.assertIn('reviewed full-content evidence stale or missing: 1=edited-again', result['review'])


if __name__ == '__main__':
    unittest.main()
