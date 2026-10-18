"""One bad article never blocks the publishing queue; no POST is ever retried blindly.

Offline tests only: no WordPress, no secrets. They pin the owner's order to remove
whatever makes posting to WordPress hard, without touching the QA rules.
"""
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import intake
import qa
import qa_gate
from common import SITE, WP, WPRejected, digest
from publisher import Publisher, RunStop, attempt_create
from test_factory import FakeWP

POLICY = {'mode': 'draft_only', 'production_enabled': False, 'paused': False, 'emergency_stop': False}
TOPIC = {'topic_id': 'NT-999999', 'title': 'Isolated unit fixture', 'proposed_slug': 'unit-fixture',
         'canonical_target': SITE + '/unit-fixture/'}


def http_error(status):
    return urllib.error.HTTPError(SITE + '/wp-json/wp/v2/posts', status, 'simulated response', {}, None)


class WithdrawTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeWP()
        self.ledger = {'posts': {}, 'categories': {}}

    def pub(self, client=None, before_post=None):
        return Publisher(client or self.client, POLICY, self.ledger, lambda: None, before_post=before_post)

    def create(self, pub):
        return pub.create(TOPIC, 'Only test fixture prose.', digest('body'), 69, 'draft', [])

    def test_guard_abort_withdraws_intent_and_allows_clean_retry(self):
        def guard(topic, sha):
            raise ValueError('Policy changed; stop before POST')
        with self.assertRaises(RunStop):
            self.create(self.pub(before_post=guard))
        self.assertEqual(self.client.posts, [])
        self.assertNotIn('NT-999999', self.ledger['posts'])
        record = self.create(self.pub())
        self.assertEqual(record['phase'], 'VERIFIED')
        self.assertEqual(len(self.client.posts), 1)

    def test_http_4xx_refusal_withdraws_intent_and_allows_clean_retry(self):
        class Refusing(FakeWP):
            def request(self, path, payload=None, **kwargs):
                if payload:
                    raise WPRejected(429)
                return super().request(path, payload, **kwargs)
        refusing = Refusing()
        with self.assertRaises(WPRejected):
            self.create(self.pub(client=refusing))
        self.assertEqual(refusing.posts, [])
        self.assertNotIn('NT-999999', self.ledger['posts'])
        record = self.create(self.pub())
        self.assertEqual(record['phase'], 'VERIFIED')
        self.assertEqual(len(self.client.posts), 1)

    def test_5xx_stays_uncertain_and_is_never_retried_blindly(self):
        class BadGateway(FakeWP):
            def request(self, path, payload=None, **kwargs):
                if payload:
                    raise RuntimeError('WordPress HTTP 502; POST')
                return super().request(path, payload, **kwargs)
        with self.assertRaises(RuntimeError):
            self.create(self.pub(client=BadGateway()))
        self.assertEqual(self.ledger['posts']['NT-999999']['phase'], 'NEEDS_RECONCILE')
        with self.assertRaisesRegex(ValueError, 'never blindly retry'):
            self.create(self.pub())
        self.assertEqual(self.client.posts, [])

    def test_only_a_bare_intent_can_be_withdrawn(self):
        pub = self.pub()
        self.ledger['posts']['NT-999999'] = {'phase': 'NEEDS_RECONCILE', 'source_hash': digest('body')}
        pub.withdraw('NT-999999')
        self.assertIn('NT-999999', self.ledger['posts'])
        self.ledger['posts']['NT-999999'] = {'phase': 'POST_INTENT', 'wp_id': 5}
        pub.withdraw('NT-999999')
        self.assertIn('NT-999999', self.ledger['posts'])


class AttemptCreateTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeWP()
        self.ledger = {'posts': {}, 'categories': {}}
        self.pub = Publisher(self.client, POLICY, self.ledger, lambda: None)
        self.route = {'category_id': 69, 'status': 'draft'}

    def test_collision_before_intent_skips_only_this_article(self):
        live = [{'id': 5, 'slug': 'unit-fixture', 'title': {'raw': 'Isolated unit fixture'},
                 'link': SITE + '/unit-fixture/', 'content': {'raw': 'legacy'}}]
        results = []
        ok = attempt_create(self.pub, self.ledger, results, TOPIC, 'Only test fixture prose.',
                            digest('body'), self.route, live, None)
        self.assertFalse(ok)
        self.assertEqual(results[0]['status'], 'BLOCKED')
        self.assertEqual(self.client.posts, [])
        other = dict(TOPIC, topic_id='NT-999998', title='Another unit fixture',
                     proposed_slug='another-fixture', canonical_target=SITE + '/another-fixture/')
        ok = attempt_create(self.pub, self.ledger, results, other, 'Other fixture prose.',
                            digest('body2'), self.route, [], None)
        self.assertTrue(ok)
        self.assertEqual(len(self.client.posts), 1)

    def test_uncertain_intent_after_post_still_stops_the_run(self):
        results = []
        with patch('publisher.verify', side_effect=ValueError('readback mismatch')):
            with self.assertRaises(ValueError):
                attempt_create(self.pub, self.ledger, results, TOPIC, 'Only test fixture prose.',
                               digest('body'), self.route, [], None)
        self.assertEqual(self.ledger['posts']['NT-999999']['phase'], 'NEEDS_RECONCILE')
        self.assertEqual(results, [])


class WriteRefusalTests(unittest.TestCase):
    def client(self, error):
        client = WP()
        client.opener = Mock()
        client.opener.open.side_effect = [error]
        return client

    def test_post_4xx_is_a_definitive_refusal(self):
        for code in (400, 401, 403, 422, 429):
            with self.subTest(code=code):
                with self.assertRaises(WPRejected) as caught:
                    self.client(http_error(code)).request('wp/v2/posts', {'title': 'x'})
                self.assertEqual(caught.exception.status, code)
                self.assertIn('POST', str(caught.exception))

    def test_5xx_and_network_errors_stay_uncertain(self):
        for error in (http_error(500), http_error(502), http_error(504), urllib.error.URLError('timeout')):
            with self.subTest(error=str(error)):
                with self.assertRaises(RuntimeError) as caught:
                    self.client(error).request('wp/v2/posts', {'title': 'x'})
                self.assertNotIsInstance(caught.exception, WPRejected)


class IntakeQuarantineTests(unittest.TestCase):
    def run_intake(self, strict):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'posts/drafts').mkdir(parents=True)
            for name in ('NT-000001', 'NT-000002', 'NT-000003'):
                (root / 'posts/drafts' / (name + '.md')).write_text('x', encoding='utf-8')
            registry = {'leases': {'W1': {'expires_at': '2999-01-01T00:00:00+00:00'}}, 'submissions': {}}
            rows = [{'topic_id': 'NT-000001', 'topic_qa_status': 'PLANNED'},
                    {'topic_id': 'NT-000003', 'topic_qa_status': 'PLANNED'}]  # NT-000002 is not registered
            saved = {}

            def fake_read(path):
                return ({'topic_id': path.stem, 'writer_session': 's1', 'writer_slot': 'W1'}, 'body', 'sha-' + path.stem)

            def fake_load(path, default=None):
                return registry if path == intake.REG else {'posts': {}}

            with patch('intake.ROOT', root), patch('intake.load', side_effect=fake_load), \
                    patch('intake.topics', return_value=rows), patch('intake.RemoteState'), \
                    patch('intake.read_article', side_effect=fake_read), patch('intake.owner', return_value='W1'), \
                    patch('intake.save', side_effect=lambda p, v: saved.update({p: v})):
                rejected = intake.run(persist=False, strict=strict)
        return rejected, saved

    def test_publisher_mode_quarantines_a_stray_draft_and_admits_the_rest(self):
        rejected, saved = self.run_intake(False)
        self.assertEqual([r['topic_id'] for r in rejected], ['NT-000002'])
        self.assertEqual(sorted(saved[intake.REG]['submissions']), ['NT-000001', 'NT-000003'])

    def test_branch_intake_stays_strict(self):
        with self.assertRaisesRegex(ValueError, 'Unplanned topic push'):
            self.run_intake(True)


class StrayDraftQATests(unittest.TestCase):
    def test_unknown_draft_is_a_fail_ticket_and_the_qa_gate_stays_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'posts/drafts').mkdir(parents=True)
            (root / 'data/qa').mkdir(parents=True)
            (root / 'reports').mkdir(parents=True)
            (root / 'posts/drafts/NT-000001.md').write_text('good draft', encoding='utf-8')
            (root / 'posts/drafts/NT-000777.md').write_text('stray draft', encoding='utf-8')
            saved = {}

            def fake_eval(path, topic, rows=None, live=False, inv=None):
                return {'topic_id': topic['topic_id'], 'status': 'PASS', 'errors': [], 'review': [],
                        'source_sha256': digest(path.read_bytes()), 'word_count': 1700, 'gates': {}}

            with patch('qa.ROOT', root), patch('qa.topics', return_value=[{'topic_id': 'NT-000001'}]), \
                    patch('qa.evaluate', side_effect=fake_eval), \
                    patch('qa.save', side_effect=lambda p, v: saved.update({p: v})), \
                    patch.object(sys, 'argv', ['qa.py']):
                code = qa.main()
            self.assertEqual(code, 1)
            self.assertEqual(saved['data/qa/NT-000001.json']['status'], 'PASS')
            self.assertEqual(saved['data/qa/NT-000777.json']['status'], 'FAIL')
            self.assertEqual([r['topic_id'] for r in saved['reports/repair-queue.json']], ['NT-000777'])
            import json
            for name, value in saved.items():
                (root / name).write_text(json.dumps(value), encoding='utf-8')
            receipt = qa_gate.validate_complete(root)
            self.assertEqual((receipt['pass_count'], receipt['repair_ids']), (1, ['NT-000777']))


if __name__ == '__main__':
    unittest.main()
