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
    def go(self, rows, ids, verdicts=None):
        self.rows = copy.deepcopy(rows)
        old = {r['topic_id']: {'status': 'REVIEW', 'errors': [], 'review': ['old evidence']} for r in rows}
        self.saved = {}
        files = {'data/existing-content-inventory.json': {'items': [{'id': 1, 'title': 'Trang cũ hẳn khác', 'slug': 'cu',
                                                                    'content_hash': 'h1', 'title_hash': 'x1'}]},
                 'data/state/publication-ledger.json': {'posts': {}},
                 'data/taxonomy.json': {'items': copy.deepcopy(TAX)}, 'reports/topic-qa.json': old}
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
