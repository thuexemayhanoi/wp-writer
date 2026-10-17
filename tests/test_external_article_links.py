"""Normal HTTPS source citations allowed; reject unsafe outbound URLs."""
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

    def test_external_manufacturer_legal_and_research_sources_allowed(self):
        for url in (
            'https://honda.com.vn/motorbikes',
            'https://yamaha-motor.com.vn/',
            'https://vinfastauto.com/xe-dien',
            'https://csgt.bocongan.gov.vn/tintuc/',
            'https://vbpl.vn/',
            'https://example.org/research',
            'https://www.facebook.com/page/posts/123',
            'https://www.google.com/maps/place/Ha+Noi',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.check('[Nguồn liên quan](' + url + ')'), [])

    def test_plain_urls_and_reference_sources_allowed(self):
        self.assertEqual(self.check('Nguồn kỹ thuật: https://honda.com.vn/motorbikes'), [])
        self.assertEqual(self.check('[Nguồn][vinfast]\n[vinfast]: https://vinfastauto.com/'), [])
        self.assertEqual(self.check('Nguồn: www.honda.com.vn'), [])

    def test_external_image_urls_are_not_domain_blocked(self):
        self.assertEqual(self.check('![Ảnh xe](https://images.example.org/xe.jpg)'), [])

    def test_plain_http_and_malformed_https_urls_rejected(self):
        self.assertIn('UNSAFE_OUTBOUND_URL:honda.com.vn',
                      self.check('http://honda.com.vn/motorbikes'))
        self.assertIn('UNSAFE_OUTBOUND_URL:invalid-url',
                      self.check('Nguồn: https://'))

    def test_credentials_or_unusual_ports_rejected(self):
        self.assertIn('UNSAFE_OUTBOUND_URL:example.org',
                      self.check('https://user:pass@example.org/path'))
        self.assertIn('UNSAFE_OUTBOUND_URL:example.org',
                      self.check('https://example.org:8080/path'))

    def test_disguised_platform_redirects_rejected(self):
        self.assertIn('UNSAFE_OUTBOUND_URL:www.google.com',
                      self.check('[Nguồn](https://www.google.com/url?url=https%3A%2F%2Fexample.org)'))
        self.assertIn('UNSAFE_OUTBOUND_URL:l.facebook.com',
                      self.check('[Nguồn](https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.org)'))

    def test_duplicate_violations_are_deduplicated(self):
        self.assertEqual(self.check('http://example.org/a http://example.org/b'),
                         ['UNSAFE_OUTBOUND_URL:example.org'])

    def test_no_external_links_is_allowed(self):
        self.assertEqual(self.check('Nội dung đã được kiểm chứng.'), [])


if __name__ == '__main__':
    unittest.main()
