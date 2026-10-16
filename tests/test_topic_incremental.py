"""Regression: a new research candidate cannot revoke an approved SEO topic.

Large-queue benchmark verifies only new ideas get scored during refill; it
does NOT claim full-site topic auditing has become sub-quadratic.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import topic_factory


class IncrementalTopicRefillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'data/candidates').mkdir(parents=True)
        self.old={'topic_id':'NT-000001','title':'Hướng dẫn kiểm tra xe máy khi nhận xe',
            'proposed_slug':'huong-dan-kiem-tra-xe-may-khi-nhan-xe',
            'canonical_target':topic_factory.SITE+'/huong-dan-kiem-tra-xe-may-khi-nhan-xe/',
            'intent_key':'check-rental-handover','topic_qa_status':'PLANNED'}
        self.research={'topic_id':'NT-000002','title':'Vấn đề chưa nghiên cứu',
            'proposed_slug':'van-de-chua-nghien-cuu','intent_key':None,
            'topic_qa_status':'RESEARCH'}
        self.rows=[self.old,self.research]
        self.original_evidence={'NT-000001':{'status':'PASS','at':'2026-10-15',
            'topic_hash':'approved-immutable-evidence'},
            'NT-000002':{'status':'REVIEW','review':['more sources needed']}}
        self.written={}
        self.outputs={}

    def incoming(self, topic):
        path=self.root/'data/candidates/new-batch.jsonl'
        path.write_text(json.dumps(topic,ensure_ascii=False)+'\n',encoding='utf-8')
        return 'data/candidates/new-batch.jsonl'

    def run_refill(self):
        def load(path,default=None):
            if path=='data/existing-content-inventory.json':return {'items':[]}
            if path=='data/taxonomy.json':return {'items':[{'taxonomy_key':'reviews',
                'materialized_topic_count':1}]}
            if path=='config/production-policy.json':return {'approved_capacity':1000}
            if path=='reports/topic-qa.json':return self.original_evidence
            return default
        with patch.object(topic_factory,'ROOT',self.root),\
             patch.object(topic_factory,'topics',lambda: self.rows),\
             patch.object(topic_factory,'load',load),\
             patch.object(topic_factory,'write_topics',lambda r:self.written.update({t['topic_id']:t for t in r})),\
             patch.object(topic_factory,'save',lambda path,value:self.outputs.update({path:value})):
            topic_factory.run('data/candidates/new-batch.jsonl')

    def test_duplicate_new_candidate_is_rejected_but_incumbent_stays_planned(self):
        inc=dict(self.old)
        inc.update(topic_id='NT-000003',topic_qa_status='RESEARCH')
        self.incoming(inc)
        self.run_refill()
        self.assertEqual(self.written['NT-000001']['topic_qa_status'],'PLANNED')
        self.assertEqual(self.written['NT-000003']['topic_qa_status'],'REJECTED')
        self.assertEqual(self.outputs['reports/topic-qa.json']['NT-000001'],
                         self.original_evidence['NT-000001'])
        self.assertTrue(any('topic identity collision:' in e
                            for e in self.outputs['reports/topic-qa.json']['NT-000003']['errors']))
        self.assertEqual(self.written['NT-000002']['topic_qa_status'],'RESEARCH')

    def test_near_duplicate_new_candidate_goes_review_not_demotion(self):
        candidate=dict(self.old)
        candidate.update(topic_id='NT-000004',title='Hướng dẫn kiểm tra xe máy trước khi nhận xe',
            proposed_slug='huong-dan-kiem-tra-xe-may-truoc-khi-nhan-xe',
            canonical_target=topic_factory.SITE+'/huong-dan-kiem-tra-xe-may-truoc-khi-nhan-xe/',
            intent_key='near-but-distinct',taxonomy_key='reviews')
        self.incoming(candidate)
        self.run_refill()
        self.assertEqual(self.written['NT-000001']['topic_qa_status'],'PLANNED')
        self.assertEqual(self.written['NT-000004']['topic_qa_status'],'RESEARCH')

    def test_old_candidate_with_same_id_and_changed_title_is_rejected(self):
        self.incoming({**self.old,'title':'Changed old approved title'})
        with self.assertRaisesRegex(ValueError,'immutable'):
            self.run_refill()
        self.assertEqual(self.written,{})

    def test_only_new_topic_is_rescored_even_at_ten_thousand_incumbents(self):
        self.rows=[{'topic_id':'NT-%06d'%i,'title':'Incumbent %d'%i,
                    'topic_qa_status':'PLANNED','taxonomy_key':'reviews'} for i in range(1,10001)]
        self.original_evidence={}
        inc={'topic_id':'NT-010001','title':'A researched new topic','proposed_slug':'a-researched-new-topic',
             'canonical_target':topic_factory.SITE+'/a-researched-new-topic/',
             'taxonomy_key':'reviews','intent_key':'fresh'}
        self.incoming(inc)
        fake_gate={'status':'REVIEW','errors':[],'review':['requires research']}
        def load(path,default=None):
            if path=='data/existing-content-inventory.json':return {'items':[]}
            if path=='data/taxonomy.json':return {'items':[{'taxonomy_key':'reviews'}]}
            if path=='config/production-policy.json':return {'approved_capacity':20000}
            if path=='reports/topic-qa.json':return {}
            return default
        calls=[]
        with patch.object(topic_factory,'ROOT',self.root),\
             patch.object(topic_factory,'topics',lambda:self.rows),\
             patch.object(topic_factory,'load',load),\
             patch.object(topic_factory,'gate',lambda t,other,inv,tax:(calls.append(t['topic_id']) or fake_gate)),\
             patch.object(topic_factory,'write_topics',lambda rows:None),\
             patch.object(topic_factory,'save',lambda *args:None):
            topic_factory.run('data/candidates/new-batch.jsonl')
        self.assertEqual(calls,['NT-010001'])
        self.assertTrue(all(x['topic_qa_status']=='PLANNED' for x in self.rows))


if __name__=='__main__':unittest.main()
