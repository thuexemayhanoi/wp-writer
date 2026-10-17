"""Gate triage: what a QA verdict means for the queue. QA thresholds are not touched."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gate_triage import annotate, classify, state_entry, triage


def result(status, **gates):
    return {'status': status, 'source_sha256': 'sha-1',
            'gates': {g: {'errors': e, 'review': r} for g, (e, r) in gates.items()}}


class ClassifyTests(unittest.TestCase):
    def test_transient_source_failures_are_machine_rechecks(self):
        for reason in ('Source REVIEW: URLError timed out', 'Source REVIEW: HTTPError 503',
                       'Source REVIEW: HTTPError 429', 'Source REVIEW: TimeoutError',
                       'Source REVIEW: URLError [Errno 104] Connection reset by peer'):
            self.assertEqual(classify('3', reason), 'INFRA_PENDING', reason)

    def test_unverifiable_sources_and_wrong_facts_are_real_risks(self):
        for reason in ('Source REVIEW: HTTPError 403', 'Source REVIEW: HTTPError 404',
                       'Source REVIEW: ValueError: Source excerpt not found',
                       'Source REVIEW: URLError [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed',
                       'Source REVIEW: RuntimeError: Cross-origin redirect refused', 'Source host not allowlisted',
                       'Source URL is not safe public HTTPS',
                       'Legal claim needs current official source', 'Wrong rental rate:Honda Wave',
                       'Business price mismatch', 'Unverified phone number', 'Unverified experience/review/absolute claim'):
            self.assertEqual(classify('3', reason), 'REAL_RISK', reason)

    def test_authoring_defects_go_back_to_the_writer(self):
        self.assertEqual(classify('2', 'SEO_SCORE_BELOW_MIN:70/85'), 'WRITER_REPAIR')
        self.assertEqual(classify('2', 'Word count outside 1600..5000:1500'), 'WRITER_REPAIR')
        self.assertEqual(classify('1', 'Manifest mismatch:title'), 'WRITER_REPAIR')
        self.assertEqual(classify('3', 'External writer editorial/factual evidence missing or stale'), 'WRITER_REPAIR')
        self.assertEqual(classify('3', 'Source REVIEW: ValueError: Source date stale'), 'WRITER_REPAIR')
        self.assertEqual(classify('3', 'Source REVIEW: ValueError: Source checked_at stale or future'), 'WRITER_REPAIR')
        self.assertEqual(classify('5', 'Orphan: no public internal link'), 'WRITER_REPAIR')

    def test_a_possibly_transient_broken_link_is_rechecked(self):
        self.assertEqual(classify('5', 'Broken internal link:https://thuexemaynguyentu.com/x/'), 'INFRA_PENDING')

    def test_duplicates_categories_and_unknown_reasons_fail_closed(self):
        for gate, reason in (('4', 'existing URL collision:12'), ('4', 'Near duplicate existing:12'),
                             ('4', 'near topic:NT-000002'), ('4', 'reviewed full-content evidence stale or missing: 1=x'),
                             ('6', 'Category blocked'), ('6', 'anything'), ('9', 'unknown reason')):
            self.assertEqual(classify(gate, reason), 'REAL_RISK', (gate, reason))


class TriageTests(unittest.TestCase):
    def test_pass_has_no_hold(self):
        self.assertEqual(triage(result('PASS'))['hold_class'], 'NONE')

    def test_the_strongest_class_wins(self):
        mixed = result('FAIL', **{'2': (['SEO_SCORE_BELOW_MIN:70/85'], []), '3': ([], ['Source REVIEW: HTTPError 503']),
                                  '4': (['Near duplicate existing:7'], [])})
        info = triage(mixed)
        self.assertEqual(info['hold_class'], 'REAL_RISK')
        self.assertEqual(len(info['writer_repair']), 1)
        self.assertEqual(len(info['infra_pending']), 1)
        only_infra = triage(result('REVIEW', **{'3': ([], ['Source REVIEW: URLError timed out'])}))
        self.assertEqual(only_infra['hold_class'], 'INFRA_PENDING')

    def test_a_crashed_evaluation_is_held_for_the_owner(self):
        info = triage({'status': 'FAIL', 'errors': ['QA evaluation crashed: KeyError: x'], 'review': []})
        self.assertEqual(info['hold_class'], 'REAL_RISK')


class RecheckCounterTests(unittest.TestCase):
    def infra(self, sha='sha-1'):
        r = result('REVIEW', **{'3': ([], ['Source REVIEW: HTTPError 503'])})
        r['source_sha256'] = sha
        return r

    def test_a_transient_failure_is_rechecked_three_times_then_held_as_unverifiable(self):
        state = None
        for expected in (1, 2):
            annotate(current := self.infra(), state)
            self.assertEqual((current['recheck']['attempts'], current['triage']['hold_class']), (expected, 'INFRA_PENDING'))
            state = state_entry(current)
        annotate(current := self.infra(), state)
        self.assertEqual(current['recheck']['attempts'], 3)
        self.assertTrue(current['recheck']['exhausted'])
        self.assertEqual(current['triage']['hold_class'], 'REAL_RISK')
        self.assertTrue(current['recheck']['needs_owner'])
        self.assertIn('persisted for 3 evaluations', current['triage']['real_risk'][-1])

    def test_pass_resets_the_counter(self):
        state = state_entry(annotate(self.infra()))
        passed = annotate(result('PASS'), state)
        self.assertEqual(passed['recheck']['attempts'], 0)
        self.assertFalse(passed['recheck']['exhausted'])

    def test_writer_repair_counts_one_attempt_per_new_draft_version(self):
        def failing(sha):
            r = result('FAIL', **{'2': (['SEO_SCORE_BELOW_MIN:70/85'], [])})
            r['source_sha256'] = sha
            return r
        state = None
        for sha, expected in (('a', 1), ('a', 1), ('b', 2), ('b', 2), ('c', 3)):
            annotate(current := failing(sha), state)
            self.assertEqual(current['recheck']['attempts'], expected, sha)
            state = state_entry(current)
        self.assertTrue(current['recheck']['needs_owner'])
        self.assertEqual(current['triage']['hold_class'], 'WRITER_REPAIR')

    def test_a_different_hold_class_restarts_the_count(self):
        state = state_entry(annotate(self.infra()))
        changed = annotate(result('FAIL', **{'4': (['existing URL collision:9'], [])}), state)
        self.assertEqual(changed['recheck']['attempts'], 1)


if __name__ == '__main__':
    unittest.main()
