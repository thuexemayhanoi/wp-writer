"""No-key autonomous topic discovery: truthful research queue, never fake QA."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import topic_discovery as td


class TopicDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.domains={'domains':[
            {'domain_id':'D01','name':'Thuê xe máy','taxonomy_key':'rental-guide','initial_allocation':40},
            {'domain_id':'D02','name':'Xe điện','taxonomy_key':'electric','initial_allocation':40},
            {'domain_id':'D03','name':'Giao thông','taxonomy_key':'urban-mobility','initial_allocation':40},
        ]}
        self.conf={'enabled':True,'research_ceiling':10000,
            'refill_when_claimable_below':100,
            'max_pending_proposals':300,'max_new_proposals_per_run':20,
            'subjects':{
                'rental-guide':['đặt cọc khi thuê xe máy','thủ tục nhận xe'],
                'electric':['kiểm tra pin xe điện','bảo trì phanh xe điện'],
                'urban-mobility':['phương tiện đô thị','đi lại giờ cao điểm'],
            }}
        self.policy={'approved_capacity':1000,'capacity':10000}
        self.prior={'version':1,'next_batch':1,'proposals':{}}
        self.rows=[]

    def make(self,rows=None,prior=None,policy=None,conf=None):
        with patch.object(td,'load',lambda path,default=None:{}):
            return td.discover(self.domains,conf or self.conf,
                self.rows if rows is None else rows,[],
                self.prior if prior is None else prior,
                self.policy if policy is None else policy,
                conf or self.conf)

    def test_generate_balanced_distinct_topic_research_briefs(self):
        ideas,stats=self.make()
        self.assertEqual(stats['state'],'DISCOVERED')
        self.assertEqual(len(ideas),20)
        self.assertEqual(len(set(p['proposal_id'] for p in ideas)),20)
        self.assertGreaterEqual(len(set(p['domain_id'] for p in ideas)),3)
        self.assertTrue(all(p['status']=='AWAITING_AI_RESEARCH'
                          and p['source_verification']=='PENDING' for p in ideas))
        self.assertTrue(all(p['taxonomy_key'] in ('rental-guide','electric','urban-mobility') for p in ideas))
        self.assertTrue(all(not p.get('topic_qa_status') for p in ideas))
        self.assertTrue(all(len(p['research_questions'])==5 for p in ideas))

    def test_existing_title_and_approved_topics_never_mutate(self):
        first=self.make()[0][0]
        old={'title':first['title'],'topic_id':'NT-000001',
             'origin_id':'IDEA-0001','topic_qa_status':'PLANNED'}
        rows=[old]
        ideas,_=self.make(rows=rows)
        self.assertNotIn(td.norm(first['title']),[td.norm(p['title']) for p in ideas])
        self.assertEqual(old['topic_qa_status'],'PLANNED')
        self.assertEqual(old['origin_id'],'IDEA-0001')

    def test_same_proposal_not_repeated_across_runs(self):
        before,_=self.make()
        prior={'version':1,'next_batch':2,'proposals':{
            p['proposal_id']:{'title':p['title'],'domain_id':p['domain_id']}
            for p in before}}
        after,_=self.make(prior=prior)
        self.assertEqual(len(after),20)
        self.assertFalse(set(p['proposal_id'] for p in before)&set(p['proposal_id'] for p in after))

    def test_limit_twenty_even_if_policy_ceiling_is_ten_thousand(self):
        ideas,_=self.make()
        self.assertEqual(len(ideas),20)

    def test_pending_cap_triggers_idle_and_no_spam(self):
        prior={'proposals':{'NTD-'+str(i):{'domain_id':'D01'} for i in range(300)}}
        items,state=self.make(prior=prior)
        self.assertEqual(items,[])
        self.assertEqual(state['state'],'RESEARCH_BACKLOG_FULL')

    def test_capacity_proposals_remain_bounded_when_almost_full(self):
        prior={'proposals':{'NTD-'+str(i):{'domain_id':'D01'} for i in range(295)}}
        ideas,state=self.make(prior=prior)
        self.assertEqual(len(ideas),5)

    def test_research_can_continue_at_one_thousand_without_publishing(self):
        rows=[{'topic_id':'NT-%06d'%i,'topic_qa_status':'PLANNED'} for i in range(1000)]
        ideas,state=self.make(rows=rows)
        self.assertEqual(len(ideas),20)
        self.assertTrue(state['approved_intake_capacity_reached'])
        self.assertEqual(state['approved_topic_limit'],1000)

    def test_healthy_claimable_queue_suppresses_research(self):
        rows=[{'topic_id':'NT-%06d'%i,'topic_qa_status':'PLANNED'} for i in range(100)]
        ideas,state=self.make(rows=rows)
        self.assertEqual(ideas,[])
        self.assertEqual(state['state'],'QUEUE_HEALTHY')

    def test_research_ceiling_is_independent_but_strict(self):
        prior={'proposals':{'NTD-'+str(i):{'domain_id':'D01'} for i in range(10000)}}
        conf={**self.conf,'max_pending_proposals':300}
        ideas,state=self.make(prior=prior,conf=conf)
        self.assertEqual(ideas,[])
        self.assertIn(state['state'],('RESEARCH_BACKLOG_FULL','RESEARCH_CEILING_REACHED'))

    def test_invalid_capacity_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'Invalid publication'):
            self.make(policy={'approved_capacity':11000,'capacity':10000})

    def test_public_rss_is_only_a_discovery_lead(self):
        xml='''<?xml version="1.0"?><rss><channel>
        <item><title>Tin tức xe máy điện và an toàn giao thông cập nhật</title>
        <link>https://news.google.com/rss/articles/abc</link></item>
        </channel></rss>'''.encode('utf-8')
        items,error=td.rss_public_headlines('xe điện',fetch=lambda u:xml)
        self.assertIsNone(error)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['evidence_level'],'DISCOVERY_LEAD_NOT_FACT_CHECKED')

    def test_malformed_rss_is_not_fake_evidence(self):
        rows,error=td.rss_public_headlines('xe điện',fetch=lambda u:b'invalid')
        self.assertEqual(rows,[])
        self.assertEqual(error,'ParseError')

    def test_live_feed_failure_not_misrepresented(self):
        def bad(u):
            raise OSError('network unavailable')
        leads,errors=td.collect_signals(self.domains['domains'],
            {'max_signal_feeds_per_run':2,'max_headlines_per_feed':5},bad)
        self.assertEqual(len(errors),2)
        self.assertTrue(all(x==[] for x in leads.values()))

    def test_proposal_ids_are_stable(self):
        p=td.proposal(self.domains['domains'][0],'đặt cọc xe',td.ANGLES[0],td.CONTEXTS[0])
        q=td.proposal(self.domains['domains'][0],'đặt cọc xe',td.ANGLES[0],td.CONTEXTS[0])
        self.assertEqual(p['proposal_id'],q['proposal_id'])
        self.assertEqual(p['candidate_contract']['origin_id'],p['proposal_id'])

    def test_external_ai_completion_frees_capacity_only_after_topic_import(self):
        first=self.make()[0][0]
        ledger={'proposals':{first['proposal_id']:{'title':first['title'],'domain_id':first['domain_id']}}}
        no_topic=self.make(prior=ledger)[1]
        self.assertEqual(no_topic['pending_research'],1)
        rows=[{'topic_id':'NT-000081','origin_id':first['proposal_id'],
               'topic_qa_status':'RESEARCH'}]
        yes_topic=self.make(prior=ledger,rows=rows)[1]
        self.assertEqual(yes_topic['pending_research'],0)

    def test_apply_refuses_non_trusted_runtime_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            patch_load=lambda path,default=None:{
                'config/production-policy.json':self.policy,
                'config/topic-discovery.json':self.conf,
                'data/topic-domains.json':self.domains,
                'data/existing-content-inventory.json':{'items':[]},
                td.LEDGER:self.prior,
            }.get(path,default)
            with patch.object(td,'ROOT',root),patch.object(td,'load',patch_load),\
                 patch.object(td,'topics',lambda:[]),\
                 patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
                with self.assertRaisesRegex(ValueError,'Trusted Actions'):
                    td.run(apply=True,live_signals=False)
            self.assertEqual(list(root.iterdir()),[])


if __name__=='__main__':
    unittest.main()
