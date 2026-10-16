import copy
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from watchdog import assess

UTC=dt.timezone.utc
AT=dt.datetime(2026,10,16,14,0,tzinfo=UTC)
EARLY=(AT-dt.timedelta(minutes=15)).isoformat()
OLD=(AT-dt.timedelta(minutes=180)).isoformat()

class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.policy={'mode':'dry_run','production_enabled':False,
          'draft_staging_enabled':False,'paused':False,'emergency_stop':False}
        self.registry={'leases':{},'submissions':{},'processed_requests':{}}
        self.ledger={'posts':{}}
        self.rows=[{'topic_id':'NT-000001','topic_qa_status':'PLANNED'}]
        self.qa={}

    def assess(self):
        return assess(self.policy,self.registry,self.ledger,self.rows,self.qa,AT)

    def enable_production(self):
        self.policy.update(mode='production',production_enabled=True,owner_approval_ref='approved',
            acceptance_passed=True,security_controls_verified=True,seo_adapter_verified=True)

    def admit(self,at=EARLY):
        self.registry['submissions']['NT-000001']={'sha256':'a'*64,'submitted_at':at}
        self.qa['NT-000001']={'status':'PASS','source_sha256':'a'*64}

    def test_dry_run_with_old_qa_pass_does_not_raise_false_stall(self):
        self.admit(OLD)
        self.assertEqual(self.assess()['state'],'SAFE_OFF')
        self.assertEqual(self.assess()['queued_count'],1)
        self.assertTrue(self.assess()['healthy'])

    def test_staging_requires_actual_security_approval(self):
        self.policy['mode']='draft_only'
        self.policy['draft_staging_enabled']=True
        self.assertEqual(self.assess()['state'],'CONFIG_BLOCKED')
        self.policy.update(draft_staging_approval_ref='approval',security_controls_verified=True)
        self.assertEqual(self.assess()['state'],'AWAITING_WRITERS')
        self.assertFalse(self.assess()['production_enabled'])

    def test_active_production_flags_must_be_complete(self):
        self.policy.update(mode='production',production_enabled=True)
        self.assertEqual(self.assess()['state'],'CONFIG_BLOCKED')

    def test_fresh_admitted_qa_pass_waits_inside_grace(self):
        self.enable_production()
        self.admit(EARLY)
        report=self.assess()
        self.assertEqual(report['state'],'DELIVERY_PENDING')
        self.assertTrue(report['healthy'])

    def test_overdue_admitted_qa_pass_fails(self):
        self.enable_production()
        self.admit(OLD)
        report=self.assess()
        self.assertEqual(report['state'],'STALLED')
        self.assertEqual(report['queued_count'],1)
        self.assertFalse(report['healthy'])

    def test_qa_pass_without_matching_immutable_receipt_never_counts_as_ready(self):
        self.enable_production()
        self.admit(OLD)
        self.registry['submissions']['NT-000001']['sha256']='invalid'
        self.assertEqual(self.assess()['queued_count'],0)
        self.assertEqual(self.assess()['state'],'SOURCE_MISMATCH')
        self.assertFalse(self.assess()['healthy'])

    def test_uncertain_post_takes_priority_even_when_production_off(self):
        self.admit(OLD)
        self.ledger['posts']['NT-000001']={'phase':'POST_INTENT','expected_status':'draft'}
        report=self.assess()
        self.assertEqual(report['state'],'NEEDS_RECONCILE')
        self.assertFalse(report['healthy'])

    def test_verified_record_clears_backlog(self):
        self.enable_production()
        self.admit(OLD)
        self.ledger['posts']['NT-000001']={'phase':'VERIFIED','status':'publish',
          'verified_at':EARLY}
        report=self.assess()
        self.assertEqual(report['queued_count'],0)
        self.assertEqual(report['verified_wp_posts'],1)
        self.assertEqual(report['last_verified_at'],EARLY)

    def test_paused_mode_not_marked_stalled(self):
        self.enable_production()
        self.admit(OLD)
        self.policy['emergency_stop']=True
        self.assertEqual(self.assess()['state'],'PAUSED')

    def test_blocked_writer_request_is_visible(self):
        self.enable_production()
        self.registry['processed_requests']={'other-session':{'status':'BLOCKED','reason':'lease'}}
        report=self.assess()
        self.assertEqual(report['state'],'WRITER_REQUEST_BLOCKED')
        self.assertEqual(report['blocked_sessions'],['other-session'])

    def test_missing_topics_without_writers_is_not_successful_progress(self):
        self.enable_production()
        self.rows=[]
        report=self.assess()
        self.assertEqual(report['state'],'NEEDS_TOPIC_EXPANSION')
        self.assertTrue(report['healthy'])

    def test_live_writer_without_waiting_posts_is_running(self):
        self.enable_production()
        self.registry['leases']['W1']={'session':'owner-1','expires_at':EARLY.replace('14:','15:'),'topic_ids':['NT-000001']}
        # Use a reliably future time rather than matching a formatted string.
        self.registry['leases']['W1']['expires_at']=(AT+dt.timedelta(hours=1)).isoformat()
        self.assertEqual(self.assess()['state'],'RUNNING')

    def test_expired_lease_does_not_appear_as_running(self):
        self.enable_production()
        self.registry['leases']['W1']={'session':'owner-1','expires_at':OLD,'topic_ids':['NT-000001']}
        self.assertNotIn('W1',self.assess()['active_writer_slots'])

if __name__=='__main__':
    unittest.main()
