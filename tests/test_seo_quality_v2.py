"""SEO V2 rubric is auditable, deterministic, and intent-aware.

These are isolated fixtures: no WordPress credentials, network or posts.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from common import SITE, load
from qa import seo_onpage_score


class SeoV2ScoringTests(unittest.TestCase):
    def setUp(self):
        self.rules = load('config/qa-rules.json')
        self.topic = {
            'primary_keyword': 'Chọn nơi sửa xe máy điện',
            'proposed_slug': 'chon-noi-sua-xe-may-dien',
            'canonical_target': SITE + '/chon-noi-sua-xe-may-dien/'
        }
        self.meta = {
            'meta_title': 'Chọn nơi sửa xe máy điện: cách đánh giá uy tín',
            'meta_description': 'Chọn nơi sửa xe máy điện đáng tin cậy cần xem cách chẩn đoán pin, công khai báo giá, điều kiện linh kiện và biên nhận trước khi đồng ý sửa chữa.',
            'canonical_target': self.topic['canonical_target'],
            'direct_answer': 'Chọn nơi sửa xe máy điện cần xem nơi tiếp nhận đúng dòng xe, cách kiểm tra hư hỏng, chi phí chẩn đoán, chất lượng phụ tùng và quy trình giao nhận minh bạch.'
        }
        self.u1 = SITE + '/kiem-tra-phanh-xe-may/'
        self.u2 = SITE + '/kiem-tra-xe-truoc-khi-di/'
        self.body = '\n\n'.join([
            self.meta['direct_answer'],
            '## Chọn nơi sửa xe máy điện có đúng chuyên môn không',
            'Giải thích nguyên tắc xác định năng lực và hỗ trợ của thợ chuyên môn.',
            '## Cách hỏi báo giá trước khi quyết định',
            'Phân tích chi phí và phụ tùng phù hợp với nhu cầu.',
            '## Kiểm tra phụ tùng và hồ sơ bảo dưỡng',
            'Hướng dẫn kiểm tra chứng từ và tình trạng xe sau sửa.',
            '## Theo dõi an toàn trong quá trình sử dụng',
            'Nhắc người dùng không tự tháo pin và nên kiểm tra có chuyên môn.',
            '[Kiểm tra phanh xe máy](' + self.u1 + ')',
            '[Các bước kiểm tra xe trước khi đi](' + self.u2 + ')',
        ])

    def score(self, meta=None, body=None, internal=None):
        return seo_onpage_score(
            meta or self.meta, body if body is not None else self.body,
            self.topic, internal if internal is not None else [self.u1, self.u2],
            self.rules
        )

    def test_hundred_point_rubric_and_seo_76_minimum(self):
        self.assertEqual(self.rules['seo_min'], 76)
        score, breakdown, recommendations = self.score()
        self.assertEqual(sum(item['max'] for item in breakdown.values()), 100)
        self.assertEqual(sum(item['points'] for item in breakdown.values()), score)
        self.assertGreaterEqual(score, self.rules['seo_min'])
        self.assertLessEqual(score, 100)
        self.assertFalse(recommendations)

    def test_irrelevant_seo_title_loses_points(self):
        normal, _, _ = self.score()
        meta = {**self.meta, 'meta_title': 'Khám phá thắng cảnh và du lịch cuối tuần'}
        score, breakdown, recommendations = self.score(meta=meta)
        self.assertLess(score, normal)
        self.assertEqual(breakdown['seo_title_relevance']['points'], 0)
        self.assertTrue(recommendations)

    def test_one_contextual_link_is_allowed_but_not_full_credit(self):
        short = self.body.replace(
            '[Các bước kiểm tra xe trước khi đi](' + self.u2 + ')', ''
        )
        score, breakdown, _ = self.score(body=short, internal=[self.u1])
        self.assertGreaterEqual(score, self.rules['seo_min'])
        self.assertEqual(breakdown['verified_contextual_links']['points'], 10)

    def test_unverified_links_get_no_linking_credit(self):
        score, breakdown, _ = self.score(internal=[])
        self.assertEqual(breakdown['verified_contextual_links']['points'], 0)
        self.assertEqual(breakdown['descriptive_anchor']['points'], 0)
        self.assertEqual(score, 80)  # G5 orphan still blocks even when score passes

    def test_no_forced_photo_faq_or_sales_cta(self):
        self.assertNotIn('![', self.body)
        self.assertNotIn('FAQ', self.body)
        self.assertNotIn('Thuê xe ngay', self.body)
        score, _, _ = self.score()
        self.assertGreaterEqual(score, self.rules['seo_min'])

    def test_wrong_canonical_loses_identity_credit(self):
        meta = {**self.meta, 'canonical_target': SITE + '/some-other-url/'}
        _, breakdown, _ = self.score(meta=meta)
        self.assertEqual(breakdown['canonical_identity']['points'], 0)


if __name__ == '__main__':
    unittest.main()
