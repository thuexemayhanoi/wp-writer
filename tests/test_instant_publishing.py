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
import publisher
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

    def test_owner_switch_enables_production_without_extra_flags(self):
        p=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(p['batch_size'],2)
        self.assertEqual(p['max_batches_per_run'],5)
        # Owner allows continuous QA-gated publication after the short pilot.
        # The per-run, daily, taxonomy, and emergency stop guards remain active.
        self.assertEqual(production_allowed(p), not (p['paused'] or p['emergency_stop']))
        self.assertTrue(production_allowed({**p,'emergency_stop':False,'paused':False}))
        self.assertIs(p['production_enabled'],True)
        self.assertTrue(p['owner_approval_ref'])
        self.assertTrue(p['seo_adapter_verified'])
        self.assertIn('/actions/runs/38910018718',p['seo_adapter_evidence'])
        self.assertTrue(p.get('owner_publish_request'))

    def test_owner_order_does_not_fake_unperformed_verifications(self):
        p=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        self.assertEqual(p['mode'], 'production')
        self.assertIs(p['paused'], False)
        self.assertIs(type(p['emergency_stop']), bool)
        # Pilot complete by owner order: release pilot only; keep normal 2x5
        # serial publishing, daily cap and exact-category guardrails.
        from publisher import pilot_settings
        self.assertIsNone(pilot_settings(p))
        self.assertEqual(delivery_batch_limit(p),10)
        self.assertEqual(p['approved_capacity'],2000)
        self.assertFalse(p['allow_category_create'])
        self.assertEqual(p['on_category_mismatch'],'draft')
        # Never performed, so never marked true; they no longer gate publication.
        self.assertIs(p['security_controls_verified'], False)
        self.assertIs(p['acceptance_passed'], False)
        self.assertEqual(production_allowed(p), not p['emergency_stop'])
        self.assertTrue(production_allowed({**p,'emergency_stop':False}))

    def test_unapproved_production_mode_never_loads_wp_credentials_or_posts(self):
        args=Namespace(persist_state=False, acceptance_topic=None,
                       acceptance_draft=False)
        real_load=publisher.load
        def switched_off(path,*a,**k):
            data=real_load(path,*a,**k)
            if path=='config/production-policy.json':
                # Isolate the unapproved-production gate from the independent
                # owner emergency stop, without mutating the stored policy.
                data={**data,'production_enabled':False,'emergency_stop':False,'publisher_pilot':None}
            return data
        capture=io.StringIO()
        with (patch('publisher.load', side_effect=switched_off),
              patch('publisher.WP', side_effect=AssertionError('WordPress touched')),
              patch('publisher.RemoteState', side_effect=AssertionError('Ledger touched')),
              redirect_stdout(capture)):
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

    def test_publish_gate_is_owner_switch_plus_stop_controls(self):
        base={'mode':'production','production_enabled':True,
            'owner_approval_ref':'2026-10-17-owner-order','seo_adapter_verified':True,
            'paused':False,'emergency_stop':False}
        self.assertTrue(production_allowed(base))
        # Unperformed acceptance / branch-security checks must not hold back QA-PASS posts.
        self.assertTrue(production_allowed({**base,'acceptance_passed':False,
                                            'security_controls_verified':False}))
        for changes in ({'production_enabled':False},{'owner_approval_ref':None},
                        {'owner_approval_ref':''},{'seo_adapter_verified':False},
                        {'mode':'dry_run'},{'mode':'draft_only'},
                        {'emergency_stop':True},{'paused':True}):
            with self.subTest(changes=changes):
                self.assertFalse(production_allowed({**base,**changes}))

    def test_publisher_job_has_no_extra_blocking_steps(self):
        wf=yaml.load((ROOT/'.github/workflows/wordpress-publisher.yml').read_text(),Loader=yaml.BaseLoader)
        steps=wf['jobs']['publisher']['steps']
        text=json.dumps(steps)
        # QA stays in the Writer QA workflow that triggers this job and in
        # publisher.py; no ruleset check or repeated unit-test run may block publishing.
        self.assertNotIn('production_security',text)
        self.assertNotIn('unittest',text)
        inspect=next(s for s in steps if s.get('id')=='mode')
        self.assertIn('production_allowed',inspect['run'])
        self.assertNotIn('acceptance_passed',inspect['run'])
        self.assertNotIn('security_controls_verified',inspect['run'])


if __name__=='__main__':
    unittest.main()
