"""Regression tests for bounded WordPress GET retries and create-only writes."""
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import SITE, WP


def http_error(status, headers=None):
    return urllib.error.HTTPError(SITE + '/wp-json/wp/v2/posts', status,
                                  'simulated response', headers or {}, None)


def json_response():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"ok":true}'
    response.__enter__.return_value.headers = {}
    return response


class WordPressRateLimitTests(unittest.TestCase):
    @patch('common.time.sleep')
    def test_get_waits_at_least_one_minute_then_retries_once(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [http_error(429), json_response()]
        data, _ = client.request('wp/v2/posts')
        self.assertEqual(data, {'ok': True})
        self.assertEqual(client.opener.open.call_count, 2)
        sleep.assert_called_once_with(60)

    @patch('common.time.sleep')
    def test_get_honors_retry_after_header(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [http_error(429, {'Retry-After': '75'}), json_response()]
        data, _ = client.request('wp/v2/posts')
        self.assertEqual(data, {'ok': True})
        sleep.assert_called_once_with(75)

    @patch('common.time.sleep')
    def test_repeated_429_fails_closed_without_flooding(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [http_error(429), http_error(429)]
        with self.assertRaisesRegex(RuntimeError, 'retry exhausted'):
            client.request('wp/v2/posts')
        self.assertEqual(client.opener.open.call_count, 2)
        sleep.assert_called_once_with(60)

    @patch('common.time.sleep')
    def test_unusually_long_retry_after_stops_without_early_retry(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [http_error(429, {'Retry-After': '3600'})]
        with self.assertRaisesRegex(RuntimeError, 'cooldown exceeds'):
            client.request('wp/v2/posts')
        self.assertEqual(client.opener.open.call_count, 1)
        sleep.assert_not_called()

    @patch('common.time.sleep')
    def test_post_is_never_retried_after_429(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [http_error(429)]
        with self.assertRaisesRegex(RuntimeError, 'HTTP 429; POST'):
            client.request('wp/v2/posts', {'title': 'Unsafe second attempt'})
        self.assertEqual(client.opener.open.call_count, 1)
        sleep.assert_not_called()

    @patch('common.time.sleep')
    def test_post_is_never_retried_after_network_timeout(self, sleep):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [urllib.error.URLError('timeout')]
        with self.assertRaisesRegex(RuntimeError, 'outcome unknown'):
            client.request('wp/v2/posts', {'title': 'No duplicate'})
        self.assertEqual(client.opener.open.call_count, 1)
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
