"""Publisher owner canary: reserve at most three fresh WordPress POSTs globally.

Checks are local and do not connect to WordPress or alter the factory ledger.
"""
import json
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publisher import Publisher,RunStop,pilot_settings,pilot_reserved,production_allowed


class PilotBudgetTests(TestCase):
    @staticmethod
    def active_policy():
        return {'mode':'production','production_enabled':True,
                'seo_adapter_verified':True,'owner_approval_ref':'owner-approved',
                'paused':False,'emergency_stop':False,
                'publisher_pilot':{'id':'pilot-three-20261019','max_posts':3}}

    @staticmethod
    def fixture(topic_id='NT-000711'):
        topic={'topic_id':topic_id,'title':'QA tested sample title',
               'proposed_slug':'qa-tested-sample-title',
               'canonical_target':'https://thuexemaynguyentu.com/qa-tested-sample-title/'}
        return topic

    def test_invalid_pilot_must_fail_closed(self):
        invalid=[None,False,{}, {'id':'x','max_posts':3},
                 {'id':'three-test','max_posts':0},
                 {'id':'three-test','max_posts':True},
                 {'id':'three-test','max_posts':11},
                 {'id':'three-test','max_posts':'3'}]
        for config in invalid:
            with self.subTest(config=config),self.assertRaises(ValueError):
                pilot_settings({'publisher_pilot':config if config is not None else False})
        self.assertIsNone(pilot_settings({}))

    def test_reservation_count_includes_uncertain_posts(self):
        ledger={'posts':{
            'NT-000001':{'pilot_id':'pilot-three-20261019','phase':'POST_INTENT'},
            'NT-000002':{'pilot_id':'pilot-three-20261019','phase':'VERIFY_PENDING'},
            'NT-000003':{'pilot_id':'pilot-three-20261019','phase':'NEEDS_RECONCILE'},
            'NT-000004':{'pilot_id':'other-pilot','phase':'VERIFIED'},
            'NT-000005':{'phase':'VERIFIED'}}}
        self.assertEqual(pilot_reserved(ledger,'pilot-three-20261019'),3)

    def test_full_pilot_refuses_post_without_client_interaction(self):
        policy=self.active_policy()
        ledger={'posts':{f'NT-{i:06d}':{'pilot_id':'pilot-three-20261019',
                           'phase':'POST_INTENT'} for i in range(1,4)}}
        calls=[]
        class NoWP:
            def request(self,*a,**k):
                calls.append(a)
                raise AssertionError('WordPress must not be contacted')
        instance=Publisher(NoWP(),policy,ledger=ledger,
                           persist=lambda:None,before_post=lambda t,h:None)
        self.assertTrue(production_allowed(policy))
        with self.assertRaisesRegex(RunStop,'Pilot limit reached'):
            instance.create(self.fixture(),'Sample article text','hash-source',1,'publish',
                            [],meta={'meta_title':'SEO title','meta_description':'SEO text'})
        self.assertEqual(calls,[])
        self.assertEqual(len(ledger['posts']),3)

    def test_successful_post_reserves_before_network_call(self):
        policy=self.active_policy()
        ledger={'posts':{}}
        seen=[]
        class MockWP:
            def request(self,path,payload=None):
                seen.append(('network',path,ledger['posts']['NT-000711']['phase'],
                             ledger['posts']['NT-000711']['pilot_id']))
                return ({'id':55999,'status':'publish','link':'https://thuexemaynguyentu.com/qa-tested-sample-title/'}, {})
        publisher=Publisher(MockWP(),policy,ledger=ledger,persist=lambda:seen.append(('persist',)),before_post=lambda t,h:None)
        topic=self.fixture()
        with patch('publisher.verify',return_value={'id':55999,'status':'publish',
                'link':topic['canonical_target']}):
            result=publisher.create(topic,'Sample article text','hash-source',1,'publish',[],
                         meta={'meta_title':'SEO title','meta_description':'SEO text'},
                         route={'intended_taxonomy_key':'blog','category_resolution':'EXACT'})
        self.assertEqual(result['phase'],'VERIFIED')
        self.assertEqual(result['pilot_id'],'pilot-three-20261019')
        self.assertEqual(pilot_reserved(ledger,'pilot-three-20261019'),1)
        self.assertEqual(seen[0],('persist',))
        self.assertEqual(seen[1],('network','wp/v2/posts','POST_INTENT','pilot-three-20261019'))

    def test_live_policy_cannot_run_without_emergency_stop_or_pilot_cap(self):
        policy=json.loads((ROOT/'config/production-policy.json').read_text(encoding='utf-8'))
        # Owner can release emergency_stop only while strict pilot cap is active.
        self.assertTrue(policy['emergency_stop'] or pilot_settings(policy) is not None)


if __name__=='__main__':
    main()
