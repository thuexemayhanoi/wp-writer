import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT,SITE,WP,digest,norm,visible
from topic_factory import gate
from taxonomy_sync import by_key,resolve,materialize
from writer_session import claim,live_leases
from qa import evaluate,word_count,business_errors
from publisher import Publisher,post_html,production_allowed

class TopicTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.reg=by_key();self.live=[{'id':x['wordpress_term_id'],'slug':x['slug'],'name':x['name'],'parent':x['wordpress_parent_id'],'count':1} for x in self.reg.values() if x['wordpress_term_id']]
        self.t={'topic_id':'NT-999999','title':'Bản đồ nhu cầu độc lập','primary_keyword':'nhu cầu độc lập','search_intent':'educational','intent_key':'unique-intent','taxonomy_key':'reviews','proposed_slug':'nhu-cau-doc-lap','canonical_target':SITE+'/nhu-cau-doc-lap/','outline':['a','b','c','d','e'],'research':{'reviewer':'test','difference_summary':'independent','usefulness':'specific','scope_exclusions':['legacy'],'reviewed_content_hashes':{'1':'test'},'reviewed_existing_ids':[]}}
    def test_existing_title_collision(self):
        inv=[{'id':99,'title':self.t['title'],'title_hash':digest(norm(self.t['title'])),'content_hash':'z'}]
        self.assertEqual(gate(self.t,[self.t],inv,list(self.reg.values()))['status'],'FAIL')
    def test_same_intent_different_title_fails(self):
        other={**self.t,'topic_id':'NT-888888','title':'Tên hoàn toàn khác','proposed_slug':'khac'}
        self.assertEqual(gate(self.t,[self.t,other],[],list(self.reg.values()))['status'],'FAIL')
    def test_full_parent_id_resolution(self):self.assertEqual(resolve('reviews',self.reg,self.live),156)
    def test_no_duplicate_category(self):
        live=self.live+[dict(self.live[0])]
        with self.assertRaises(ValueError):resolve('blog',self.reg,live)
    def test_wrong_parent_fails(self):
        self.live[next(i for i,c in enumerate(self.live) if c['id']==156)]['parent']=0
        with self.assertRaises(ValueError):resolve('reviews',self.reg,self.live)
    def test_no_empty_category_bulk_creation(self):
        class NoWrites:
            def request(self,*args):raise AssertionError('No category POST allowed')
        self.assertEqual(materialize('reviews',self.reg,self.live,NoWrites(),{'categories':{}},lambda:None),156)
    def test_uncategorized_forbidden(self):
        with self.assertRaises(ValueError):resolve('uncategorized',self.reg,self.live)
    def test_ambiguous_category_slug_parent(self):
        self.reg['reviews']['wordpress_term_id']=None
        self.live.append({**next(x for x in self.live if x['id']==156),'id':1001})
        with self.assertRaises(ValueError):resolve('reviews',self.reg,self.live)

class WriterTests(unittest.TestCase):
    def setUp(self):self.rows=[{'topic_id':f'NT-{i:06}','topic_qa_status':'PLANNED'} for i in range(1,12)]
    def test_three_slots_disjoint(self):
        r={'leases':{}}
        for i in range(3):_,r=claim(r,self.rows,'session-'+str(i),count=3)
        ids=[x for v in r['leases'].values() for x in v['topic_ids']]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(r['leases']),3)
    def test_no_lease_stealing(self):
        _,r=claim({'leases':{}},self.rows,'session-one','W1')
        with self.assertRaises(ValueError):claim(r,self.rows,'session-two','W1')
    def test_one_session_one_slot(self):
        _,r=claim({'leases':{}},self.rows,'session-one','W1')
        with self.assertRaises(ValueError):claim(r,self.rows,'session-one','W2')
    def test_expired_lease_reclaim(self):
        yesterday=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=2)
        _,r=claim({'leases':{}},self.rows,'session-old','W1',epoch=yesterday)
        _,r=claim(r,self.rows,'session-new','W1');self.assertEqual(r['leases']['W1']['session'],'session-new')
    def test_ambiguous_registry_fail_closed(self):
        _,r=claim({'leases':{}},self.rows,'session-one','W1');r['leases']['W2']=copy.deepcopy(r['leases']['W1'])
        with self.assertRaises(ValueError):live_leases(r)

class QATests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'posts/drafts').mkdir(parents=True)
        self.path=self.root/'posts/drafts/NT-999999.md'
        self.t=TopicTaxonomyTests();self.t.setUp();self.topic=self.t.t
        self.topic['topic_qa_status']='PLANNED'
        self.inv=[{'id':1,'title':'An unrelated topic','title_hash':'x','content_hash':'test','status':'publish','url':SITE+'/verified/','content_text':'short older article'}]
        self.topic['research']['reviewed_existing_ids']=[1]
        self.topic['internal_link_candidates']=[SITE+'/verified/']
        self.meta={k:self.topic[k] for k in ['topic_id','title','primary_keyword','search_intent','taxonomy_key','canonical_target']}
        self.meta.update(meta_title='Một nội dung đủ dài để kiểm tra',meta_description='Mô tả thử nghiệm cho bộ kiểm tra nội dung và điều kiện xuất bản, chỉ được sử dụng trong automated tests và không phải bài viết công khai.',direct_answer='Câu trả lời trực tiếp dùng riêng trong kiểm thử.',link_rationale='Same reviewed cluster',writer_session='test-session',writer_slot='W1')
    def tearDown(self):self.tmp.cleanup()
    def body(self,count=1750):
        # Synthetic boundary fixture: NEVER stored in campaign posts or sent to WordPress.
        def token(n):
            s=''
            while n:n,r=divmod(n,26);s+=chr(97+r)
            return 'kiểm'+s
        words=[token(i+1) for i in range(count)]
        return self.meta['direct_answer']+'\n\n'+'\n\n'.join('## Phần '+chr(65+i)+'\n\n'+' '.join(words[i*count//4:(i+1)*count//4]) for i in range(4))+'\n\n[Xem hướng dẫn]('+SITE+'/verified/)'
    def runqa(self,body=None,changes=None,**kwargs):
        body=body or self.body();meta=copy.deepcopy(self.meta);meta.update(changes or {})
        meta['editorial_review']={'reviewer':'fixture-only','body_sha256':digest(body),'intent_covered':True,'substantive':True,'facts_checked':True,'no_fabricated_experience':True,'collision_reviewed':True}
        self.path.write_text('---\n'+json.dumps(meta,ensure_ascii=False)+'\n---\n\n'+body)
        with patch('qa.ROOT',self.root):return evaluate(self.path,self.topic,rows=[self.topic],inv=self.inv,check_claim=False,**kwargs)
    def test_valid_technical_fixture_passes(self):self.assertEqual(self.runqa()['status'],'PASS')
    def test_below_1600_fails(self):self.assertEqual(self.runqa(self.body(1000))['status'],'FAIL')
    def test_above_5000_fails(self):self.assertEqual(self.runqa(self.body(5100))['status'],'FAIL')
    def test_markup_frontmatter_keywords_not_counted(self):
        body='## Từ khóa\n'+'keyword '*2000
        self.assertEqual(word_count(body),0)
    def test_duplicate_content_fails(self):
        body=self.body();self.inv.append({'id':2,'title':'Other','content_hash':'other','content_text':visible(body),'status':'publish'})
        result=self.runqa(body);self.assertTrue(any('duplicate existing' in e for e in result['errors']))
    def test_wrong_business_fact_fails(self):
        body=self.body()+'\n\nNguyễn Tú cho thuê Honda Vision 100.000đ/ngày.'
        self.assertTrue(any('rental rate' in e for e in self.runqa(body)['errors']))
    def test_legal_without_evidence_review(self):
        result=self.runqa(self.body()+'\n\nThông tin về giấy phép lái xe cần được xác minh.')
        self.assertEqual(result['status'],'REVIEW');self.assertTrue(result['legal_required'])
    def test_broken_internal_link_fails(self):self.assertEqual(self.runqa(link_checker=lambda u:False)['status'],'FAIL')
    def test_draft_link_fails(self):self.assertEqual(self.runqa(self.body()+'\n\n[Draft]('+SITE+'/?p=3861)')['status'],'FAIL')
    def test_unsafe_html_fails(self):self.assertEqual(self.runqa(self.body()+'<script>bad()</script>')['status'],'FAIL')
    def test_wrong_taxonomy_fails(self):self.assertEqual(self.runqa(changes={'taxonomy_key':'uncategorized'})['status'],'FAIL')
    def test_editorial_hash_is_required(self):
        result=self.runqa();text=self.path.read_text().replace('fixture-only','')
        self.path.write_text(text)
        with patch('qa.ROOT',self.root):result=evaluate(self.path,self.topic,rows=[self.topic],inv=self.inv,check_claim=False)
        self.assertEqual(result['status'],'REVIEW')

class FakeWP:
    def __init__(self,timeout=False):self.posts=[];self.calls=[];self.timeout=timeout
    def request(self,path,payload=None,**kwargs):
        self.calls.append((path,payload))
        if payload:
            if path!='wp/v2/posts':raise AssertionError('Only create endpoint permitted')
            p={**payload,'id':9001+len(self.posts),'content':{'raw':payload['content']},'link':SITE+'/'+payload['slug']+'/','title':{'raw':payload['title']}}
            self.posts.append(p)
            if self.timeout:self.timeout=False;raise TimeoutError('after committed POST')
            return p,{}
        return self.get(path),{}
    def get(self,path,**kwargs):return next(x for x in self.posts if str(x['id'])==path.split('/')[-1].split('?')[0])

class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.client=FakeWP();self.events=[];self.ledger={'posts':{},'categories':{}}
        self.policy={'mode':'draft_only','production_enabled':False,'paused':False,'emergency_stop':False}
        self.topic={'topic_id':'NT-999999','title':'Isolated unit fixture','proposed_slug':'unit-fixture','canonical_target':SITE+'/unit-fixture/'}
        self.pub=Publisher(self.client,self.policy,self.ledger,lambda:self.events.append(copy.deepcopy(self.ledger)))
    def create(self):return self.pub.create(self.topic,'Only test fixture prose.',digest('body'),69,'draft',list(self.client.posts))
    def test_rerun_no_duplicate(self):
        a=self.create();b=self.create();self.assertEqual(a['wp_id'],b['wp_id']);self.assertEqual(len(self.client.posts),1)
    def test_timeout_post_reconciled_no_duplicate(self):
        self.client.timeout=True
        with self.assertRaises(TimeoutError):self.create()
        self.assertEqual(self.ledger['posts']['NT-999999']['phase'],'NEEDS_RECONCILE')
        self.create();self.assertEqual(len(self.client.posts),1);self.assertEqual(self.ledger['posts']['NT-999999']['phase'],'VERIFIED')
    def test_uncertain_missing_post_never_retried(self):
        self.ledger['posts']['NT-999999']={'phase':'POST_INTENT','source_hash':digest('body')}
        with self.assertRaises(ValueError):self.create()
        self.assertEqual(self.client.posts,[])
    def test_production_disabled(self):
        with self.assertRaises(ValueError):self.pub.create(self.topic,'body','hash',69,'publish',[])
        self.assertFalse(production_allowed(self.policy));self.assertEqual(self.client.posts,[])
    def test_remote_intent_required_before_post(self):
        def unavailable():raise RuntimeError('remote unavailable')
        self.pub.persist=unavailable
        with self.assertRaises(RuntimeError):self.create()
        self.assertEqual(self.client.posts,[])
    def test_ledger_receipt_is_precise(self):
        r=self.create();self.assertEqual(r['phase'],'VERIFIED');self.assertEqual(r['category_id'],69)
        self.assertEqual(r['source_hash'],digest('body'));self.assertEqual(self.events[0]['posts']['NT-999999']['phase'],'POST_INTENT')
    def test_never_updates_existing_post(self):
        self.client.posts.append({'id':9,'slug':'unit-fixture','title':{'raw':self.topic['title']},'content':{'raw':'legacy'}})
        with self.assertRaises(ValueError):self.create()
        self.assertEqual(self.client.calls,[])
    def test_category_mismatch_blocks_readback(self):
        self.create();self.client.posts[0]['categories']=[1]
        with self.assertRaises(ValueError):self.create()
        self.assertEqual(len(self.client.posts),1)
    def test_source_change_cannot_overwrite(self):
        self.create()
        with self.assertRaises(ValueError):self.pub.create(self.topic,'changed','changed-hash',69,'draft',self.client.posts)
    def test_wrong_site_refused(self):
        with patch.dict(os.environ,{'WP_URL':'https://blog.rentbikehanoi.com'}):
            with self.assertRaises(ValueError):WP()
    def test_smoke_workflow_preserved(self):
        import subprocess
        old=subprocess.check_output(['git','show','3f13faa11201a25bd12a2f2e7ce8adb5fb89ac36:.github/workflows/wp-connection-smoke.yml'],cwd=ROOT)
        self.assertEqual((ROOT/'.github/workflows/wp-connection-smoke.yml').read_bytes(),old)

if __name__=='__main__':unittest.main()
