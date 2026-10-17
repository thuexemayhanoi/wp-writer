"""Instant pipeline acceptance: main Writer QA -> Publisher, 2x5 batches.

This is a structural, no-secrets test. It does NOT claim that GitHub branch
protection, Yoast REST writeback, or WordPress publication was verified.
"""
import io
import json
import sys
from pathlib import Path
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publisher import delivery_batch_limit, production_allowed, run


class InstantPublishingTests(unittest.TestCase):
    def test_exact_ten_posts_in_five_groups(self):
        policy={'batch_size':2,'max_batches_per_run':5}
        self.assertEqual(delivery_batch_limit(policy),10)
        groups=[min(2,delivery_batch_limit(policy)-i)
                for i in range(0,delivery_batch_limit(policy),2)]
        self.assertEqual(groups,[2,2,2,2,2])

    def test_per_run_limits_cannot_exceed_safety_contract(self):
        for policy in ({'batch_size':3,'max_batches_per_run':1},
                       {'batch_size':2,'max_batches_per_run':6},
                       {'batch_size':0,'max_batches_per_run':1},
                       {'batch_size':2,'max_batches_per_run':0},
                       {'batch_size':True,'max_batches_per_run':5}):
            with self.subTest(policy=policy),self.assertRaises(ValueError):
                delivery_batch_limit(policy)

    def test_legacy_defaults_still_two(self):
        self.assertEqual(delivery_batch_limit({'batch_size':2}),2)

    def test_requested_production_flag_never_overrides_verified_gates(self):
        p=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(p['batch_size'],2)
        self.assertEqual(p['max_batches_per_run'],5)
        self.assertFalse(production_allowed(p))
        self.assertFalse(p['production_enabled'])
        self.assertFalse(p['security_controls_verified'])
        self.assertTrue(p['seo_adapter_verified'])
        self.assertIn('/actions/runs/38910018718',p['seo_adapter_evidence'])
        self.assertTrue(p.get('owner_publish_request'))

    def test_owner_requested_three_stop_states_are_off_but_no_fake_approval(self):
        p=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(p['mode'], 'production')
        self.assertIs(p['paused'], False)
        self.assertIs(p['emergency_stop'], False)
        self.assertIs(p['production_enabled'], False)
        self.assertIs(p['security_controls_verified'], False)
        self.assertIs(p['acceptance_passed'], False)
        self.assertFalse(production_allowed(p))

    def test_unapproved_production_mode_never_loads_wp_credentials_or_posts(self):
        args=Namespace(persist_state=False, acceptance_topic=None,
                       acceptance_draft=False)
        capture=io.StringIO()
        with patch('publisher.WP', side_effect=AssertionError('WordPress touched')), \\
             patch('publisher.RemoteState', side_effect=AssertionError('Ledger touched')), \\
             redirect_stdout(capture):
            run(args)
        self.assertIn('PRODUCTION_NOT_AUTHORIZED', capture.getvalue())
        self.assertIn('no WordPress writes', capture.getvalue())

    def test_action_waits_for_qa_success_instead_of_parallel_draft_push(self):
        wf=yaml.load((ROOT/'.github/workflows/wordpress-publisher.yml').read_text(),Loader=yaml.BaseLoader)
        triggers=wf['on']
        self.assertIn('workflow_run',triggers)
        self.assertEqual(triggers['workflow_run']['workflows'],
                         ['Universal writer QA (no WordPress credentials)'])
        self.assertEqual(triggers['workflow_run']['types'],['completed'])
        self.assertEqual(triggers['workflow_run']['branches'],['main'])
        self.assertNotIn('posts/drafts/**',triggers['push']['paths'])
        job=wf['jobs']['publisher']
        self.assertIn("workflow_run.conclusion == 'success'",job['if'])
        self.assertIn("workflow_run.event == 'push'",job['if'])
        self.assertIn("workflow_run.head_branch == 'main'",job['if'])
        names=[step.get('name','') for step in job['steps']]
        self.assertTrue(any('trusted main history' in n for n in names))
        self.assertTrue(any('2x5' in n for n in names))
        # Secrets remain exclusive to the approved active delivery step.
        self.assertEqual(sum('WP_APPLICATION_PASSWORD' in
                         json.dumps(s) for s in job['steps']),1)

    def test_failure_cannot_be_marked_publishable_merely_for_owner_consent(self):
        base={'mode':'production','production_enabled':True,
            'owner_approval_ref':'2026-10-16-owner-consent','acceptance_passed':True,
            'security_controls_verified':True,'seo_adapter_verified':True,
            'paused':False,'emergency_stop':False}
        self.assertTrue(production_allowed(base))
        for key in ('security_controls_verified','seo_adapter_verified',
                    'acceptance_passed'):
            self.assertFalse(production_allowed({**base,key:False}))
        self.assertFalse(production_allowed({**base,'emergency_stop':True}))
        self.assertFalse(production_allowed({**base,'paused':True}))


if __name__=='__main__':
    unittest.main()
