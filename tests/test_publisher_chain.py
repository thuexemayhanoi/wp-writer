"""Publisher self-continuation: bounded, serialized, only after a run that really posted and only while READY remains."""
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from publisher import pacing  # noqa: E402
from publisher_chain import DEFAULTS, decision, settings  # noqa: E402

ACTIVE = {'paused': False, 'emergency_stop': False, 'publisher_chain': {'enabled': True, 'max_depth': 3, 'pause_seconds': 0}}
POSTED = {'production': True, 'attempted': 4}


class DecisionTests(unittest.TestCase):
    def test_continues_after_a_posting_run_with_backlog(self):
        go, reason = decision(ACTIVE, POSTED, 0, 7)
        self.assertTrue(go, reason)

    def test_never_continues_when_nothing_was_posted(self):
        self.assertFalse(decision(ACTIVE, dict(POSTED, attempted=0), 0, 7)[0])

    def test_never_continues_without_backlog(self):
        self.assertFalse(decision(ACTIVE, POSTED, 0, 0)[0])

    def test_stop_switches_win(self):
        self.assertFalse(decision(dict(ACTIVE, emergency_stop=True), POSTED, 0, 7)[0])
        self.assertFalse(decision(dict(ACTIVE, paused=True), POSTED, 0, 7)[0])

    def test_depth_is_bounded(self):
        self.assertTrue(decision(ACTIVE, POSTED, 2, 7)[0])
        self.assertFalse(decision(ACTIVE, POSTED, 3, 7)[0])

    def test_disabled_chain_or_missing_result_never_continues(self):
        self.assertFalse(decision(dict(ACTIVE, publisher_chain={'enabled': False}), POSTED, 0, 7)[0])
        self.assertFalse(decision(ACTIVE, None, 0, 7)[0])
        self.assertFalse(decision(ACTIVE, dict(POSTED, production=False), 0, 7)[0])

    def test_settings_defaults_and_bounds(self):
        self.assertEqual(settings({}), DEFAULTS)
        self.assertEqual(settings({'publisher_chain': {'max_depth': 5}})['max_depth'], 5)
        for bad in ({'max_depth': 101}, {'max_depth': '3'}, {'pause_seconds': 601}, {'max_depth': True}, 'x'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                settings({'publisher_chain': bad})


class PacingTests(unittest.TestCase):
    def test_defaults_are_zero_and_bounds_hold(self):
        self.assertEqual(pacing({}), {'post': 0, 'batch': 0})
        self.assertEqual(pacing({'post_interval_seconds': 3, 'batch_pause_seconds': 20}), {'post': 3, 'batch': 20})
        for bad in ({'post_interval_seconds': 121}, {'batch_pause_seconds': -1}, {'post_interval_seconds': '3'},
                    {'batch_pause_seconds': True}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pacing(bad)

    def test_production_policy_paces_the_host(self):
        policy = json.loads((ROOT / 'config/production-policy.json').read_text(encoding='utf-8'))
        pace = pacing(policy)
        self.assertGreaterEqual(pace['post'], 1)
        self.assertGreaterEqual(pace['batch'], 10)
        chain = settings(policy)
        self.assertTrue(chain['enabled'])
        self.assertLessEqual(chain['max_depth'], 100)


class WorkflowTests(unittest.TestCase):
    def test_publisher_workflow_chains_only_after_the_safety_switch_and_success(self):
        doc = yaml.safe_load((ROOT / '.github/workflows/wordpress-publisher.yml').read_text(encoding='utf-8'))
        on = doc.get('on', doc.get(True, {}))
        self.assertIn('chain_depth', on['workflow_dispatch']['inputs'])
        self.assertEqual(doc['permissions']['actions'], 'write')
        self.assertEqual(doc['concurrency']['group'], 'wp-writer-publisher')
        steps = doc['jobs']['publisher']['steps']
        chain = [s for s in steps if 'publisher_chain.py' in s.get('run', '')]
        self.assertEqual(len(chain), 1)
        self.assertIn("steps.safety_switch.outputs.active == 'true'", chain[0]['if'])
        self.assertIn('success()', chain[0]['if'])
        self.assertEqual(steps[-1], chain[0])  # the chain decision is the very last step
        self.assertIn('CHAIN_DEPTH', chain[0]['env'])


if __name__ == '__main__':
    unittest.main()
