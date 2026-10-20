"""Incremental QA sweep: only new or changed drafts are evaluated; stored records stay hash-checked."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import qa  # noqa: E402
import qa_gate  # noqa: E402
import qa_incremental as inc  # noqa: E402
from common import digest  # noqa: E402

RULES = {'seo_min': 85, 'quality_min': 85, 'incremental_sweep': True, 'incremental_max_age_hours': 24}
NOW = dt.datetime(2026, 10, 20, 3, 0, tzinfo=dt.timezone.utc)


def topic(tid):
    return {'topic_id': tid, 'title': 'T ' + tid, 'primary_keyword': 'k', 'search_intent': 'i', 'taxonomy_key': 'blog',
            'canonical_target': 'https://thuexemaynguyentu.com/' + tid.lower() + '/', 'proposed_slug': tid.lower(),
            'topic_qa_status': 'PLANNED'}


class DecideTests(unittest.TestCase):
    def setUp(self):
        self.rules_sha = inc.rules_digest(RULES)
        self.sha = 'a' * 64
        self.t = topic('NT-000001')
        self.record = {'topic_id': 'NT-000001', 'status': 'PASS', 'source_sha256': self.sha, 'word_count': 1700,
                       'gates': {'1': {}}, 'errors': [], 'review': [], 'at': (NOW - dt.timedelta(hours=2)).isoformat(),
                       'incremental_key': inc.incremental_key(self.sha, self.rules_sha, self.t)}

    def decide(self, **changes):
        kw = {'topic_id': 'NT-000001', 'raw_sha': self.sha, 'record': self.record, 'topic': self.t,
              'ledger_record': None, 'rules_sha': self.rules_sha, 'max_age_hours': 24, 'at': NOW}
        kw.update(changes)
        return inc.decide(**kw)

    def test_unchanged_draft_rules_and_topic_is_cached(self):
        self.assertEqual(self.decide()[0], 'CACHED')

    def test_verified_publication_with_same_hash_is_frozen_whatever_its_age(self):
        old = dict(self.record, at='2026-01-01T00:00:00+00:00', incremental_key=None)
        verdict, _ = self.decide(record=old, ledger_record={'phase': 'VERIFIED', 'source_hash': self.sha})
        self.assertEqual(verdict, 'FROZEN')

    def test_verified_publication_with_another_hash_is_not_frozen(self):
        verdict, _ = self.decide(ledger_record={'phase': 'VERIFIED', 'source_hash': 'b' * 64})
        self.assertEqual(verdict, 'CACHED')  # falls through to the ordinary cache rules

    def test_changed_draft_is_fresh(self):
        self.assertEqual(self.decide(raw_sha='c' * 64)[0], 'FRESH')

    def test_changed_rules_are_fresh(self):
        self.assertEqual(self.decide(rules_sha='d' * 64)[0], 'FRESH')

    def test_changed_topic_row_is_fresh(self):
        self.assertEqual(self.decide(topic=dict(self.t, title='renamed'))[0], 'FRESH')

    def test_old_record_is_fresh(self):
        stale = dict(self.record, at=(NOW - dt.timedelta(hours=30)).isoformat())
        self.assertEqual(self.decide(record=stale)[0], 'FRESH')

    def test_transient_hold_is_rechecked(self):
        held = dict(self.record, status='REVIEW', triage={'hold_class': 'INFRA_PENDING'})
        self.assertEqual(self.decide(record=held)[0], 'FRESH')

    def test_writer_repair_fail_stays_cached_until_the_draft_changes(self):
        held = dict(self.record, status='FAIL', triage={'hold_class': 'WRITER_REPAIR'})
        self.assertEqual(self.decide(record=held)[0], 'CACHED')

    def test_missing_or_foreign_record_is_fresh(self):
        self.assertEqual(self.decide(record=None)[0], 'FRESH')
        self.assertEqual(self.decide(record=dict(self.record, topic_id='NT-000009'))[0], 'FRESH')
        self.assertEqual(self.decide(record=dict(self.record, status='SKIPPED'))[0], 'FRESH')

    def test_draft_without_topic_is_fresh(self):
        self.assertEqual(self.decide(topic=None)[0], 'FRESH')


class SweepTests(unittest.TestCase):
    """qa.main --incremental evaluates only the FRESH drafts and keeps every record hash-valid for qa_gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for sub in ('posts/drafts', 'data/qa', 'reports', 'data/state', 'config'):
            (self.root / sub).mkdir(parents=True)
        self.rows = [topic('NT-000001'), topic('NT-000002'), topic('NT-000003')]
        for t in self.rows:
            (self.root / 'posts/drafts' / (t['topic_id'] + '.md')).write_text('draft ' + t['topic_id'], encoding='utf-8')
        rules_sha = inc.rules_digest(RULES)
        # 000001: VERIFIED on WordPress -> frozen. 000002: cached record. 000003: no record -> fresh.
        sha1 = digest((self.root / 'posts/drafts/NT-000001.md').read_bytes())
        sha2 = digest((self.root / 'posts/drafts/NT-000002.md').read_bytes())
        self.ledger = {'posts': {'NT-000001': {'phase': 'VERIFIED', 'source_hash': sha1}}}
        self.records = {
            'NT-000001': {'topic_id': 'NT-000001', 'status': 'PASS', 'source_sha256': sha1, 'word_count': 1700,
                          'gates': {'1': {}}, 'errors': [], 'review': [], 'at': '2026-01-01T00:00:00+00:00'},
            'NT-000002': {'topic_id': 'NT-000002', 'status': 'PASS', 'source_sha256': sha2, 'word_count': 1700,
                          'gates': {'1': {}}, 'errors': [], 'review': [], 'at': dt.datetime.now(dt.timezone.utc).isoformat(),
                          'incremental_key': inc.incremental_key(sha2, rules_sha, self.rows[1])}}
        for tid, rec in self.records.items():
            (self.root / 'data/qa' / (tid + '.json')).write_text(json.dumps(rec), encoding='utf-8')

    def fake_load(self, path, default=None):
        if path == 'config/qa-rules.json':
            return RULES
        if path == 'data/state/publication-ledger.json':
            return self.ledger
        if path == 'data/existing-content-inventory.json':
            return {'items': []}
        p = self.root / path
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

    def test_only_fresh_drafts_are_evaluated_and_the_gate_stays_complete(self):
        evaluated = []
        saved = {}

        def fake_eval(path, t, rows=None, live=False, inv=None):
            evaluated.append(t['topic_id'])
            return {'topic_id': t['topic_id'], 'status': 'PASS', 'errors': [], 'review': [],
                    'source_sha256': digest(path.read_bytes()), 'word_count': 1700, 'gates': {'1': {}}}

        def fake_save(path, value):
            saved[path] = value
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(json.dumps(value), encoding='utf-8')

        with patch('qa.ROOT', self.root), patch('qa_incremental.ROOT', self.root), \
                patch('qa.topics', return_value=self.rows), patch('qa_incremental.topics', return_value=self.rows), \
                patch('qa.load', side_effect=self.fake_load), patch('qa_incremental.load', side_effect=self.fake_load), \
                patch('qa.evaluate', side_effect=fake_eval), patch('qa.save', side_effect=fake_save), \
                patch('gate_triage.load', return_value={'content_repair_max': 10}), \
                patch.object(sys, 'argv', ['qa.py', '--incremental']):
            code = qa.main()
        self.assertEqual(code, 0)
        self.assertEqual(evaluated, ['NT-000003'])
        self.assertIn('incremental_key', saved['data/qa/NT-000003.json'])
        self.assertEqual(saved['reports/repair-queue.json'], [])
        receipt = qa_gate.validate_complete(self.root)
        self.assertEqual((receipt['draft_count'], receipt['pass_count'], receipt['repair_count']), (3, 3, 0))

    def test_stale_cached_record_is_still_caught_by_the_gate(self):
        # A record that does not match its draft bytes is never reused: it is re-evaluated or fails the gate.
        (self.root / 'posts/drafts/NT-000002.md').write_text('edited after QA', encoding='utf-8')
        with patch('qa_incremental.ROOT', self.root), patch('qa_incremental.topics', return_value=self.rows), \
                patch('qa_incremental.load', side_effect=self.fake_load):
            plan = inc.plan(root=self.root, rows=self.rows, rules=RULES, ledger=self.ledger)
        self.assertEqual(plan['frozen'], ['NT-000001'])
        self.assertEqual(sorted(plan['fresh']), ['NT-000002', 'NT-000003'])
        self.assertEqual(plan['cached'], [])
        (self.root / 'reports/repair-queue.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            qa_gate.validate_complete(self.root)

    def test_full_mode_without_flag_still_evaluates_everything(self):
        evaluated = []

        def fake_eval(path, t, rows=None, live=False, inv=None):
            evaluated.append(t['topic_id'])
            return {'topic_id': t['topic_id'], 'status': 'PASS', 'errors': [], 'review': [],
                    'source_sha256': digest(path.read_bytes()), 'word_count': 1700, 'gates': {'1': {}}}

        with patch('qa.ROOT', self.root), patch('qa.topics', return_value=self.rows), \
                patch('qa.load', side_effect=self.fake_load), patch('qa.evaluate', side_effect=fake_eval), \
                patch('qa.save', side_effect=lambda p, v: None), \
                patch('gate_triage.load', return_value={'content_repair_max': 10}), \
                patch.object(sys, 'argv', ['qa.py']):
            qa.main()
        self.assertEqual(evaluated, ['NT-000001', 'NT-000002', 'NT-000003'])


class RuleTests(unittest.TestCase):
    def test_incremental_sweep_is_enabled_in_the_repository_rules(self):
        rules = json.loads((ROOT / 'config/qa-rules.json').read_text(encoding='utf-8'))
        self.assertIs(rules.get('incremental_sweep'), True)
        self.assertEqual(rules.get('incremental_max_age_hours'), 24)
        # Thresholds are untouched by the incremental sweep.
        self.assertEqual((rules['seo_min'], rules['quality_min'], rules['word_min'], rules['word_max']), (85, 85, 1600, 5000))


if __name__ == '__main__':
    unittest.main()
