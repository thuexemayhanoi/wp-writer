"""Control workflow must fail on semantic BLOCKED, without changing active leases."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import control_requests


class FakeState:
    def __init__(self):self.persisted=[]
    def remember(self,paths):self.paths=list(paths)
    def persist(self,paths,message=None):self.persisted.append(list(paths))


class RequestStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'data/writer-requests').mkdir(parents=True)
        self.session='session-tester'
        self.registry={'leases':{},'submissions':{},'processed_requests':{}}
        self.ledger={'posts':{}}
        self.rows=[{'topic_id':'NT-000002','topic_qa_status':'PLANNED'},
                   {'topic_id':'NT-000003','topic_qa_status':'PLANNED'}]
        self.state=FakeState()

    def request(self,**kwargs):
        req={'request_id':'test-1','session':self.session,
             'action':'begin','slot':'auto','count':1}
        req.update(kwargs)
        (self.root/'data/writer-requests'/(self.session+'.json')).write_text(json.dumps(req))

    def execute_request(self, selected_paths=None):
        def load(path,default=None):
            return copy.deepcopy(self.registry if path==control_requests.REG else self.ledger)
        def save(path,data):
            if path!=control_requests.REG:raise AssertionError('Unexpected state write')
            self.registry=copy.deepcopy(data)
        with patch.object(control_requests,'ROOT',self.root),\
             patch.object(control_requests,'load',load),\
             patch.object(control_requests,'save',save),\
             patch.object(control_requests,'topics',lambda:self.rows),\
             patch.object(control_requests,'RemoteState',lambda:self.state),\
             patch.object(control_requests,'changed_request_paths',lambda:None):
            # Tests emulate an explicit manual scan. The real push selector is
            # independently tested with mocked event SHA pairs.
            return control_requests.run(selected_paths=selected_paths)

    def test_valid_request_claims_one_topic(self):
        self.request()
        self.execute_request()
        self.assertEqual(self.registry['processed_requests'][self.session]['status'],'CLAIMED')
        self.assertEqual(self.registry['leases']['W1']['topic_ids'],['NT-000002'])
        self.assertEqual(len(self.state.persisted),1)

    def test_auto_claim_uses_w9_after_eight_other_sessions(self):
        for i in range(1,9):
            self.registry['leases'][f'W{i}']={
                'session':f'other-session-{i}',
                'topic_ids':[f'NT-{900000+i:06}'],
                'claimed_at':'2026-10-18T00:00:00+00:00',
                'expires_at':'2099-01-01T00:00:00+00:00'}
        self.request()
        self.execute_request()
        self.assertEqual(self.registry['processed_requests'][self.session]['slot'],'W9')
        self.assertEqual(self.registry['leases']['W9']['topic_ids'],['NT-000002'])

    def test_blocked_request_causes_nonzero_run_and_durable_reason(self):
        self.request(topic_ids=['NT-888888'])
        with self.assertRaisesRegex(SystemExit,'BLOCKED'):
            self.execute_request()
        self.assertEqual(self.registry['leases'],{})
        self.assertEqual(self.registry['processed_requests'][self.session]['status'],'BLOCKED')
        self.assertEqual(len(self.state.persisted),1)

    def test_repeated_blocked_hash_still_fails_not_green(self):
        self.request(topic_ids=['NT-888888'])
        with self.assertRaises(SystemExit):self.execute_request()
        with self.assertRaisesRegex(SystemExit,'BLOCKED'):self.execute_request()
        self.assertEqual(len(self.state.persisted),1)

    def test_failed_reclaim_does_not_mutate_existing_lease(self):
        expires='2099-01-01T00:00:00+00:00'
        self.registry['leases']={'W1':{'session':self.session,'topic_ids':['NT-000002'],
                       'expires_at':expires,'claimed_at':'2026-10-16T00:00:00+00:00'}}
        self.registry['submissions']={'NT-000002':{'session':self.session}}
        self.ledger['posts']['NT-000002']={'phase':'VERIFIED','wp_id':9876}
        self.request(slot='W1',topic_ids=['NT-888888'])
        before=copy.deepcopy(self.registry['leases'])
        with self.assertRaisesRegex(SystemExit,'BLOCKED'):self.execute_request()
        self.assertEqual(self.registry['leases'],before)

    def test_old_blocked_request_does_not_block_another_writer_push(self):
        self.request(topic_ids=['NT-888888'])
        with self.assertRaises(SystemExit):
            self.execute_request()
        other={'request_id':'other-1','session':'session-second',
            'action':'begin','slot':'auto','count':1,
            'topic_ids':['NT-000003']}
        (self.root/'data/writer-requests/session-second.json').write_text(json.dumps(other))
        self.execute_request(selected_paths={'data/writer-requests/session-second.json'})
        self.assertEqual(self.registry['processed_requests'][self.session]['status'],'BLOCKED')
        self.assertEqual(self.registry['processed_requests']['session-second']['status'],'CLAIMED')
        self.assertEqual(self.registry['leases']['W1']['topic_ids'],['NT-000003'])

    def test_changed_push_selector_reads_real_event_sha_pairs(self):
        from unittest.mock import MagicMock
        import os
        event=self.root/'push.json'
        event.write_text(json.dumps({'before':'a'*40,'after':'b'*40}))
        output='data/writer-requests/session-second.json\nREADME.md\n'
        command=MagicMock(returncode=0,stdout=output)
        with patch.dict(os.environ,{'GITHUB_EVENT_NAME':'push','GITHUB_EVENT_PATH':str(event)}),\
             patch.object(control_requests.subprocess,'run',return_value=command):
            self.assertEqual(control_requests.changed_request_paths(),
                             {'data/writer-requests/session-second.json'})

    def test_new_request_can_recover_blocked_session(self):
        self.request(topic_ids=['NT-888888'])
        with self.assertRaises(SystemExit):self.execute_request()
        self.request(topic_ids=['NT-000003'],request_id='test-2')
        self.execute_request()
        self.assertEqual(self.registry['processed_requests'][self.session]['status'],'CLAIMED')
        self.assertEqual(self.registry['leases']['W1']['topic_ids'],['NT-000003'])


if __name__=='__main__':unittest.main()
