"""Self-healing gates: transient retries, G4 evidence recheck, crash isolation, G7 receipt, inventory refresh digest."""
import datetime as dt
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import qa
from common import SITE, digest, load
from publisher import Publisher, confirmed_post_drift, inventory_digest
from test_factory import FakeWP
from topic_factory import drop_own_post, exempt_factory_posts

TODAY = dt.date.today().isoformat()
PAGE_TEXT = '<html><body><p>Nội dung chính thức nói rằng bốn từ bằng chứng thật nằm ở đây.</p></body></html>'


def source(url='https://www.honda.com.vn/x'):
    return {'url': url, 'checked_at': TODAY, 'supports': 'một ý được nguồn hỗ trợ',
            'evidence_text': 'bốn từ bằng chứng thật', 'source_sha256': 'a' * 64}


class Response:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=None):
        return self.text.encode('utf-8')


class Opener:
    """Replays a script of outcomes: an exception is raised, a string is served as the page."""
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def open(self, request, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


def timeout():
    return urllib.error.URLError(TimeoutError('timed out'))


def http(code):
    return urllib.error.HTTPError('https://www.honda.com.vn/x', code, 'x', {}, io.BytesIO(b''))


class TransientRetryTests(unittest.TestCase):
    def setUp(self):
        qa.reset_source_host_cache()
        self.addCleanup(qa.reset_source_host_cache)

    def run_sources(self, outcomes):
        opener = Opener(outcomes)
        with patch('qa.urllib.request.build_opener', return_value=opener), patch('qa.time.sleep'):
            errors, evidence = qa.verify_sources([source()], live=True)
        return opener, errors, evidence

    def test_two_timeouts_then_success_is_verified_without_a_human(self):
        opener, errors, evidence = self.run_sources([timeout(), http(503), PAGE_TEXT])
        self.assertEqual((errors, opener.calls), ([], 3))
        self.assertEqual(evidence[0]['attempts'], 3)

    def test_a_persistent_timeout_is_reported_after_exactly_three_reads(self):
        opener, errors, _ = self.run_sources([timeout(), timeout(), timeout()])
        self.assertEqual(opener.calls, 3)
        self.assertEqual(errors, ['Source REVIEW: URLError timed out'])

    def test_a_permanent_refusal_is_not_retried(self):
        opener, errors, _ = self.run_sources([http(403)])
        self.assertEqual((opener.calls, errors), (1, ['Source REVIEW: HTTPError 403']))

    def test_a_missing_excerpt_is_a_real_finding_not_an_infrastructure_problem(self):
        opener, errors, _ = self.run_sources(['<html><body><p>không có đoạn đó</p></body></html>'])
        self.assertEqual(opener.calls, 1)
        self.assertEqual(errors, ['Source REVIEW: ValueError: Source excerpt not found'])


class UnreachableHostTests(unittest.TestCase):
    """A host that timed out on every retry is not contacted again in the same run (saves 3 x 20 s per further source)."""
    def setUp(self):
        qa.reset_source_host_cache()
        self.addCleanup(qa.reset_source_host_cache)

    def test_a_host_that_timed_out_three_times_is_skipped_for_its_other_sources(self):
        opener = Opener([timeout(), timeout(), timeout()])
        with patch('qa.urllib.request.build_opener', return_value=opener), patch('qa.time.sleep'):
            with self.assertRaises(urllib.error.URLError):
                qa.read_source('https://csgt.example.gov.vn/a')
            self.assertEqual(opener.calls, 3)
            with self.assertRaises(urllib.error.URLError) as caught:
                qa.read_source('https://csgt.example.gov.vn/b')
        self.assertEqual(opener.calls, 3)  # no extra network call for the second source
        self.assertTrue(qa.is_transient(caught.exception))  # so the research snapshot fallback still applies
        self.assertIn('timed out', str(caught.exception.reason))

    def test_the_skipped_source_still_passes_through_the_research_snapshot_fallback(self):
        first, second = source('https://csgt.example.gov.vn/a'), source('https://csgt.example.gov.vn/b')
        opener = Opener([timeout(), timeout(), timeout()])
        with patch('qa.urllib.request.build_opener', return_value=opener), patch('qa.time.sleep'):
            errors, evidence = qa.verify_sources([first, second], live=True, trusted_research=[dict(first), dict(second)])
        self.assertEqual((errors, opener.calls), ([], 3))
        self.assertEqual([e['verification_method'] for e in evidence], ['research_snapshot_fallback'] * 2)
        self.assertFalse(any(e['live_checked'] for e in evidence))

    def test_a_server_that_answered_with_5xx_and_other_hosts_are_still_read(self):
        opener = Opener([http(503), http(503), http(503), PAGE_TEXT, PAGE_TEXT])
        with patch('qa.urllib.request.build_opener', return_value=opener), patch('qa.time.sleep'):
            with self.assertRaises(urllib.error.HTTPError):
                qa.read_source('https://www.honda.com.vn/a')
            self.assertEqual(qa.read_source('https://www.honda.com.vn/b')[1], 1)  # same host, it had answered
            self.assertEqual(qa.read_source('https://yamaha-motor.com.vn/c')[1], 1)  # other host
        self.assertEqual(opener.calls, 5)


class EvidenceRecheckTests(unittest.TestCase):
    def setUp(self):
        self.rules = load('config/qa-rules.json')
        self.topic = {'topic_id': 'NT-999001', 'title': 'Mũ bảo hiểm trẻ em: cách chọn cỡ đầu và kiểm tra quai',
                      'primary_keyword': 'Mũ bảo hiểm trẻ em', 'topic_qa_status': 'PLANNED'}
        self.body = ('Chọn mũ bảo hiểm cho trẻ em cần đo vòng đầu của bé rồi thử mũ tại cửa hàng. ' * 20)
        self.shingles = qa.shingles(qa.counted_text(self.body))
        self.unrelated = {'id': 11, 'type': 'posts', 'status': 'publish', 'title': 'Bảo hiểm trách nhiệm dân sự bắt buộc của chủ xe',
                          'content_text': 'Mức phí bảo hiểm bắt buộc theo nghị định và các trường hợp loại trừ trách nhiệm bồi thường.',
                          'content_hash': 'h11'}
        self.identity = {'review': ['reviewed full-content evidence stale or missing: 11=h11'],
                         'evidence_pages': {'stale': [11], 'unreviewed': []}}

    def recheck(self, *pages):
        return qa.evidence_recheck(self.topic, [self.topic], list(pages), self.shingles, self.identity, self.rules)

    def test_an_edited_page_about_something_else_is_independent(self):
        result = self.recheck(self.unrelated)
        self.assertTrue(result['independent'])
        self.assertEqual(result['pages'][0]['verdict'], 'INDEPENDENT')
        self.assertEqual(result['pages'][0]['why'], 'stale')

    def test_a_page_that_repeats_the_article_stays_a_duplicate_risk(self):
        copy = dict(self.unrelated, content_text=self.body, title='Cách chọn gì đó khác')
        result = self.recheck(copy)
        self.assertFalse(result['independent'])
        self.assertEqual(result['pages'][0]['verdict'], 'OVERLAP')
        self.assertGreaterEqual(result['pages'][0]['jaccard'], result['max_jaccard'])

    def test_a_page_with_the_same_search_intent_is_held_even_if_the_text_differs(self):
        same_intent = dict(self.unrelated, title=self.topic['title'], content_text='Văn bản khác hoàn toàn về chủ đề này.')
        self.assertEqual(self.recheck(same_intent)['pages'][0]['verdict'], 'OVERLAP')

    def test_one_overlapping_page_blocks_the_whole_lift(self):
        copy = dict(self.unrelated, id=12, content_text=self.body, title='Trang khác')
        self.identity['evidence_pages'] = {'stale': [11], 'unreviewed': [12]}
        self.assertFalse(self.recheck(self.unrelated, copy)['independent'])

    def test_nothing_to_recheck_returns_none_and_can_be_disabled(self):
        self.identity['evidence_pages'] = {'stale': [], 'unreviewed': []}
        self.assertIsNone(self.recheck(self.unrelated))
        self.identity['evidence_pages'] = {'stale': [11], 'unreviewed': []}
        self.rules['evidence_recheck'] = {'enabled': False}
        self.assertIsNone(self.recheck(self.unrelated))


class CrashIsolationTests(unittest.TestCase):
    def test_a_crashing_evaluation_is_a_fail_ticket_for_that_article_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / 'NT-999002.md'
            draft.write_text('x', encoding='utf-8')
            with patch('qa.evaluate', side_effect=KeyError('boom')):
                result = qa.evaluate_safely(draft, {'topic_id': 'NT-999002'}, [])
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('QA evaluation crashed: KeyError', result['errors'][0])
        self.assertEqual(result['source_sha256'], digest(b'x'))


class LedgerAwareInventoryTests(unittest.TestCase):
    def test_own_published_post_is_dropped_and_other_factory_posts_are_exempt(self):
        ledger = {'posts': {'NT-1': {'wp_id': 10}, 'NT-2': {'wp_id': 20}, 'NT-3': {}}}
        inventory = [{'id': 10}, {'id': 20}, {'id': 30}]
        marked = exempt_factory_posts(inventory, ledger)
        self.assertEqual([bool(p.get('evidence_exempt')) for p in marked], [True, True, False])
        self.assertEqual([p['id'] for p in drop_own_post(marked, ledger, 'NT-1')], [20, 30])
        self.assertEqual(len(drop_own_post(marked, ledger, 'NT-3')), 3)


class InventoryDigestTests(unittest.TestCase):
    def test_timestamps_do_not_count_but_content_does(self):
        a = [{'id': 1, 'type': 'posts', 'status': 'publish', 'content_hash': 'h', 'verified_at': 'now-1'}]
        b = [{'id': 1, 'type': 'posts', 'status': 'publish', 'content_hash': 'h', 'verified_at': 'now-2'}]
        c = [{'id': 1, 'type': 'posts', 'status': 'publish', 'content_hash': 'edited', 'verified_at': 'now-1'}]
        self.assertEqual(inventory_digest(a), inventory_digest(b))
        self.assertNotEqual(inventory_digest(a), inventory_digest(c))
        self.assertEqual(inventory_digest(a + [{'id': 2, 'type': 'pages'}]), inventory_digest([{'id': 2, 'type': 'pages'}] + b))


class PublicWP(FakeWP):
    """FakeWP that also serves the public permalink, so the publish path of G7 can be exercised offline."""
    def __init__(self, page_for=None):
        super().__init__()
        self.page_for = page_for

    def request(self, path, payload=None, **kwargs):
        if kwargs.get('public'):
            post = self.posts[-1]
            return self.page_for(post), {}
        return super().request(path, payload, **kwargs)


def page(post, canonical=None, title='Meta title', description='Meta description', robots=''):
    return ('<html><head><title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s">%s</head>'
            '<body><h1>Isolated unit fixture</h1><p>Only test fixture prose.</p></body></html>'
            % (title, description, canonical or post['link'], robots))


class G7Tests(unittest.TestCase):
    TOPIC = {'topic_id': 'NT-999003', 'title': 'Isolated unit fixture', 'proposed_slug': 'unit-fixture',
             'canonical_target': SITE + '/unit-fixture/'}
    META = {'meta_title': 'Meta title', 'meta_description': 'Meta description'}
    POLICY = {'mode': 'production', 'production_enabled': True, 'owner_approval_ref': 'owner order',
              'seo_adapter_verified': True, 'paused': False, 'emergency_stop': False}

    def create(self, client, ledger):
        publisher = Publisher(client, self.POLICY, ledger, lambda: None)
        return publisher.create(self.TOPIC, 'Only test fixture prose.', digest('body'), 69, 'publish', [], self.META)

    def test_a_published_post_carries_a_structured_post_publication_receipt(self):
        ledger = {'posts': {}, 'categories': {}}
        record = self.create(PublicWP(page), ledger)
        g7 = record['g7']
        self.assertEqual((g7['gate'], g7['status'], record['phase']), ('G7', 'PASS', 'VERIFIED'))
        self.assertEqual(g7['wp_id'], record['wp_id'])
        self.assertEqual(g7['url'], self.TOPIC['canonical_target'])
        self.assertEqual((g7['canonical'], g7['seo_title'], g7['seo_description']),
                         (self.TOPIC['canonical_target'], 'Meta title', 'Meta description'))
        for check in ('wordpress_status', 'slug', 'title', 'category', 'ownership_marker', 'content', 'permalink',
                      'public_page', 'indexable', 'seo_meta'):
            self.assertTrue(g7['checks'][check], check)

    def test_wrong_seo_meta_after_posting_is_never_called_verified(self):
        ledger = {'posts': {}, 'categories': {}}
        client = PublicWP(lambda post: page(post, title='Another title'))
        with self.assertRaisesRegex(ValueError, 'Frontend canonical/title/meta mismatch'):
            self.create(client, ledger)
        record = ledger['posts']['NT-999003']
        self.assertEqual(record['phase'], 'NEEDS_RECONCILE')
        self.assertEqual((record['g7']['status'], record['g7']['failed']), ('FAIL', 'seo_meta'))
        self.assertEqual(len(client.posts), 1)

    def test_a_noindex_page_fails_g7(self):
        ledger = {'posts': {}, 'categories': {}}
        client = PublicWP(lambda post: page(post, robots='<meta name="robots" content="noindex">'))
        with self.assertRaisesRegex(ValueError, 'not indexable'):
            self.create(client, ledger)
        self.assertEqual(ledger['posts']['NT-999003']['g7']['failed'], 'indexable')

    def test_seo_drift_of_a_verified_post_is_reported_never_rewritten(self):
        record = {'phase': 'VERIFIED', 'wp_id': 7, 'expected_status': 'publish', 'category_id': 69,
                  'meta_title': 'Meta title', 'meta_description': 'Meta description'}
        live = [{'id': 7, 'status': 'publish', 'slug': 'unit-fixture', 'categories': [69], 'link': self.TOPIC['canonical_target'],
                 'yoast_head_json': {'title': 'Meta title', 'description': 'Meta description',
                                     'canonical': self.TOPIC['canonical_target'], 'robots': {'index': 'index'}}}]
        self.assertIsNone(confirmed_post_drift(self.TOPIC, record, live))
        live[0]['yoast_head_json'].update(title='Edited', robots={'index': 'noindex'})
        drift = confirmed_post_drift(self.TOPIC, record, live)
        self.assertEqual(drift['status'], 'EXTERNAL_WORDPRESS_DRIFT')
        self.assertEqual(set(drift['differences']), {'seo_title', 'robots'})
        self.assertIn('never create/update', drift['action'])


if __name__ == '__main__':
    unittest.main()
