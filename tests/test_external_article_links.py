"""No third-party source citations in public article bodies; preserve platforms."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import SITE, load
from qa import outbound_link_errors


class ExternalArticleLinkPolicyTests(unittest.TestCase):
    def setUp(self):
        self.rules = load('config/qa-rules.json')

    def check(self, markdown):
        return outbound_link_errors(markdown, self.rules)

    def test_internal_links_are_not_rejected(self):
        self.assertEqual(self.check('[Bảng giá](' + SITE + '/bang-gia/)'), [])

    def test_popular_social_and_map_platforms_allowed(self):
        for url in (
            'https://www.google.com/maps/place/Ha+Noi',
            'https://maps.app.goo.gl/abc',
            'https://www.google.com/search?q=xe+may',
            'https://www.facebook.com/page/posts/123',
            'https://m.facebook.com/profile.php?id=123',
            'https://youtube.com/watch?v=test',
            'https://youtu.be/test',
            'https://www.tiktok.com/@business',
            'https://www.instagram.com/rentbikehanoi/',
            'https://zalo.me/0942467674',
            'https://wa.me/84942467674',
            'https://maps.apple.com/?q=Hanoi',
            'https://www.openstreetmap.org/#map=15/21.0/105.8',
            'https://x.com/example',
            'https://www.linkedin.com/company/example',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.check('[Xem nền tảng](' + url + ')'), [])

    def test_external_manufacturer_sources_blocked(self):
        for url, host in (
            ('https://datbike.vn/quantum', 'datbike.vn'),
            ('https://vinfastauto.com/xe-dien', 'vinfastauto.com'),
            ('https://honda.com.vn/motorbikes', 'honda.com.vn'),
            ('https://example.com/research', 'example.com'),
        ):
            with self.subTest(url=url):
                self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:' + host,
                              self.check('[Nguồn kỹ thuật](' + url + ')'))

    def test_plain_urls_and_markdown_reference_sources_blocked(self):
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:datbike.vn',
                      self.check('Nguồn kỹ thuật: https://datbike.vn/quantum'))
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:vinfastauto.com',
                      self.check('[Nguồn][vinfast]\n[vinfast]: https://vinfastauto.com/'))
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:honda.com.vn',
                      self.check('Nguồn: www.honda.com.vn'))

    def test_external_images_also_blocked(self):
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:example.com',
                      self.check('![Ảnh xe](https://example.com/xe.jpg)'))

    def test_not_fooled_by_fake_google_host(self):
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:google.com.attacker.test',
                      self.check('[Google giả](https://google.com.attacker.test/x)'))

    def test_no_plain_http_or_platform_redirects(self):
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:facebook.com',
                      self.check('http://facebook.com/page'))
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:www.google.com',
                      self.check('[Nguồn](https://www.google.com/url?url=https%3A%2F%2Fdatbike.vn)'))
        self.assertIn('EXTERNAL_SOURCE_LINK_FORBIDDEN:l.facebook.com',
                      self.check('[Nguồn](https://l.facebook.com/l.php?u=https%3A%2F%2Fdatbike.vn)'))

    def test_duplicate_violations_are_deduplicated(self):
        self.assertEqual(self.check('https://datbike.vn/a https://datbike.vn/b'),
                         ['EXTERNAL_SOURCE_LINK_FORBIDDEN:datbike.vn'])

    def test_research_sources_are_outside_article_body(self):
        self.assertEqual(self.check('Thông số phải được kiểm chứng trước khi đăng.'), [])


if __name__ == '__main__':
    unittest.main()
