"""Ensure outside AI topic briefs never override the authoritative WP taxonomy."""
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import validate
from common import load, topics


class TopicWordPressCategoryTests(unittest.TestCase):
    def test_all_existing_active_topic_ids_agree_with_verified_registry(self):
        by_key = {t['taxonomy_key']: t for t in load('data/taxonomy.json')['items']}
        seen = 0
        for topic in topics():
            term = by_key[topic['taxonomy_key']]
            if term['status'] == 'ACTIVE' and term['wordpress_term_id']:
                self.assertEqual(topic['wordpress_category_id'],
                                 term['wordpress_term_id'], topic['topic_id'])
                seen += 1
        self.assertEqual(seen, 80)

    def test_untrusted_writer_cannot_supply_wrong_category_id(self):
        topic = deepcopy(next(t for t in topics() if t['topic_qa_status'] == 'PLANNED'))
        topic['wordpress_category_id'] = 999999
        with patch.object(validate, 'topics', return_value=[topic]):
            with self.assertRaisesRegex(ValueError, 'does not match active taxonomy'):
                validate.run()

    def test_approved_topic_cannot_keep_null_category_if_term_exists(self):
        topic = deepcopy(next(t for t in topics() if t['topic_qa_status'] == 'PLANNED'))
        topic['wordpress_category_id'] = None
        with patch.object(validate, 'topics', return_value=[topic]):
            with self.assertRaisesRegex(ValueError, 'PLANNED topic missing verified'):
                validate.run()


if __name__ == '__main__':
    unittest.main()
