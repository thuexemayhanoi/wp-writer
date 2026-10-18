"""regate: a registered RESEARCH row refused only because the evidence rule moved can be promoted in place;
nothing is ever demoted, rejected or edited."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import topic_factory as tf
from common import SITE

TAX = [{'taxonomy_key': 'reviews', 'status': 'ACTIVE', 'wordpress_term_id': 777, 'materialized_topic_count': 0}]


def row(topic_id, title, status, slug=None, **research):
    slug = slug or 'bai-' + topic_id.lower()
    base = {'reviewer': 'seodev-test', 'difference_summary': 'khác', 'usefulness': 'có ích',
            'scope_exclusions': ['x'], 'reviewed_content_hashes': {'1': 'h1'}, 'reviewed_existing_ids': [1]}
    base.update(research)
    return {'topic_id': topic_id, 'title': title, 'primary_keyword': title, 'search_intent': 'Hướng dẫn',
            'intent_key': 'intent-' + topic_id, 'taxonomy_key': 'reviews', 'proposed_slug': slug,
            'canonical_target': SITE + '/' + slug + '/', 'outline': ['a', 'b', 'c', 'd', 'e'],
            'topic_qa_status': status, 'wordpress_category_id': None, 'research': base}


class RegateTests(unittest.TestCase):
    def go(self, rows, ids, verdicts=None, **overrides):
        self.rows = copy.deepcopy(rows)
        old = {r['topic_id']: {'status': 'REVIEW', 'errors': [], 'review': ['old evidence']} for r in rows}
        self.saved = {}
        files = {'data/existing-content-inventory.json': {'items': [{'id': 1, 'title': 'Trang cũ hẳn khác', 'slug': 'cu',
                                                                    'content_hash': 'h1', 'title_hash': 'x1'}]},
                 'data/state/publication-ledger.json': {'posts': {}},
                 'data/taxonomy.json': {'items': copy.deepcopy(TAX)}, 'reports/topic-qa.json': old}
        files.update(overrides)
        verdicts = verdicts if verdicts is not None else {i: 'PASS' for i in ids}
        with patch.object(tf, 'topics', side_effect=lambda: self.rows), \
             patch.object(tf, 'load', side_effect=lambda path, default=None: files.get(path, default)), \
             patch.object(tf, 'save', side_effect=lambda path, value: self.saved.__setitem__(path, value)), \
             patch.object(tf, 'write_topics', side_effect=lambda rows: setattr(self, 'rows', rows)):
            tf.run(None, verdicts, only_ids=ids)
        return {r['topic_id']: r for r in self.rows}

    def test_a_row_that_passes_is_promoted_and_nothing_else_moves(self):
        stuck = row('NT-1', 'Bản đồ nhu cầu độc lập một', 'RESEARCH')
        planned = row('NT-2', 'Chủ đề đã duyệt khác hẳn hai', 'PLANNED')
        rejected = row('NT-3', 'Chủ đề bị loại ba', 'REJECTED')
        after = self.go([stuck, planned, rejected], ['NT-1'])
        self.assertEqual(after['NT-1']['topic_qa_status'], 'PLANNED')
        self.assertEqual(after['NT-1']['wordpress_category_id'], 777)
        self.assertEqual((after['NT-2']['topic_qa_status'], after['NT-3']['topic_qa_status']), ('PLANNED', 'REJECTED'))
        evidence = self.saved['reports/topic-qa.json']
        self.assertTrue(evidence['NT-1']['regated'])
        self.assertEqual(evidence['NT-2']['review'], ['old evidence'])  # preserved, not recomputed

    def test_a_row_that_still_fails_the_gate_is_left_exactly_as_it_was(self):
        stuck = row('NT-1', 'Bản đồ nhu cầu độc lập một', 'RESEARCH')
        stuck['outline'] = ['chỉ một mục']
        after = self.go([stuck], ['NT-1'])
        self.assertEqual(after['NT-1']['topic_qa_status'], 'RESEARCH')
        self.assertEqual(self.saved['reports/topic-qa.json']['NT-1']['review'], ['old evidence'])

    def test_a_row_without_a_strict_research_qa_pass_is_not_promoted(self):
        stuck = row('NT-1', 'Bản đồ nhu cầu độc lập một', 'RESEARCH')
        after = self.go([stuck], ['NT-1'], verdicts={'NT-1': 'REVIEW'})
        self.assertEqual(after['NT-1']['topic_qa_status'], 'RESEARCH')

    def test_only_research_rows_can_be_regated(self):
        planned = row('NT-2', 'Chủ đề đã duyệt khác hẳn hai', 'PLANNED')
        with self.assertRaisesRegex(ValueError, 'Only RESEARCH rows'):
            self.go([planned], ['NT-2'])

    def legacy_world(self, sibling_verified):
        """A row recorded before `inventory_updated_at` existed: it read pages 1 and 3 (3 is a factory post verified at
        02:03), then built at 02:09; the factory verified page 2 at `sibling_verified`, which it never read."""
        items = [{'id': 1, 'title': 'Trang cũ hẳn khác', 'slug': 'cu', 'content_hash': 'h1', 'title_hash': 'x1'},
                 {'id': 2, 'title': 'Bài anh em mới đăng', 'slug': 'anh-em', 'content_hash': 'h2', 'title_hash': 'x2'},
                 {'id': 3, 'title': 'Bài nhà máy đã đọc', 'slug': 'da-doc', 'content_hash': 'h3', 'title_hash': 'x3'}]
        ledger = {'posts': {'NT-A': {'wp_id': 2, 'verified_at': sibling_verified},
                            'NT-B': {'wp_id': 3, 'verified_at': '2026-10-18T02:03:00+00:00'}}}
        stuck = row('NT-1', 'Bản đồ nhu cầu độc lập một', 'RESEARCH', reviewed_at='2026-10-18T02:09:00+00:00',
                    reviewed_content_hashes={'1': 'h1', '3': 'h3'}, reviewed_existing_ids=[1, 3])
        return stuck, {'data/existing-content-inventory.json': {'items': items},
                       'data/state/publication-ledger.json': ledger}

    def test_a_legacy_row_is_judged_with_the_snapshot_inferred_from_the_factory_pages_it_read(self):
        stuck, files = self.legacy_world('2026-10-18T02:05:00+00:00')
        after = self.go([stuck], ['NT-1'], **files)
        self.assertEqual(after['NT-1']['topic_qa_status'], 'PLANNED')
        research = after['NT-1']['research']
        self.assertEqual(research['inventory_updated_at'], '2026-10-18T02:03:00+00:00')
        self.assertTrue(research['inventory_updated_at_inferred'])

    def test_a_sibling_verified_before_the_inferred_snapshot_is_still_demanded_and_nothing_is_written(self):
        stuck, files = self.legacy_world('2026-10-18T02:02:00+00:00')
        after = self.go([stuck], ['NT-1'], **files)
        self.assertEqual(after['NT-1']['topic_qa_status'], 'RESEARCH')
        self.assertNotIn('inventory_updated_at', after['NT-1']['research'])
        self.assertNotIn('inventory_updated_at_inferred', after['NT-1']['research'])

    def test_with_snapshot_never_overrides_a_recorded_snapshot_or_invents_one(self):
        inventory = [{'id': 3, 'factory_published_at': '2026-10-18T02:03:00+00:00'},
                     {'id': 4, 'factory_published_at': '2026-10-18T02:30:00+00:00'}]
        recorded = {'research': {'inventory_updated_at': '2026-10-18T01:00:00+00:00', 'reviewed_existing_ids': [3]}}
        self.assertIs(tf.with_snapshot(recorded, inventory), recorded)
        read_nothing = {'research': {'reviewed_existing_ids': [99], 'reviewed_content_hashes': {'98': 'x'}}}
        self.assertIs(tf.with_snapshot(read_nothing, inventory), read_nothing)
        by_hash_only = {'research': {'reviewed_content_hashes': {'3': 'h3'}}}
        inferred = tf.with_snapshot(by_hash_only, inventory)
        self.assertEqual(inferred['research']['inventory_updated_at'], '2026-10-18T02:03:00+00:00')
        self.assertNotIn('inventory_updated_at', by_hash_only['research'])  # the input row is never mutated

    def test_regate_computes_the_strict_verdict_against_everyone_but_the_chosen_rows(self):
        stuck = row('NT-1', 'Bản đồ nhu cầu độc lập một', 'RESEARCH')
        other = row('NT-2', 'Chủ đề đã duyệt khác hẳn hai', 'PLANNED')
        seen = {}

        def fake_validate(rows, incumbent=None, **kw):
            seen['rows'] = [r['topic_id'] for r in rows]
            seen['incumbent'] = [r['topic_id'] for r in incumbent]
            return [{'topic_id': r['topic_id'], 'status': 'PASS'} for r in rows]

        with patch.object(tf, 'topics', return_value=[stuck, other]), \
             patch('research_v2.validate_candidates', side_effect=fake_validate), \
             patch.object(tf, 'run') as run:
            with patch.object(tf, 'topics', side_effect=[[stuck, other], [dict(stuck, topic_qa_status='PLANNED'), other]]):
                result = tf.regate(['NT-1'])
        self.assertEqual(seen, {'rows': ['NT-1'], 'incumbent': ['NT-2']})
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs['only_ids'], ['NT-1'])
        self.assertEqual(result, {'NT-1': ('PASS', 'PLANNED')})


if __name__ == '__main__':
    unittest.main()
