import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from post_publish_qa import check_page, choose, detect_unexpected_public_drafts
from common import SITE

class PostPublishQATests(unittest.TestCase):
    def setUp(self):
        self.topic={'canonical_target':SITE+'/unique-safe-article/'}
        self.rec={'meta_title':'Mô tả bài thử SEO',
                  'meta_description':'Mô tả ngắn đã xác minh trong WordPress',
                  'first_paragraph':'Nội dung đầu tiên của bài kiểm thử.'}
        self.page='''<!doctype html><html><head>
        <title>Mô tả bài thử SEO</title>
        <link rel="canonical" href="https://thuexemaynguyentu.com/unique-safe-article/">
        <meta name="description" content="Mô tả ngắn đã xác minh trong WordPress">
        <meta name="robots" content="index, follow">
        </head><body><p>Nội dung đầu tiên của bài kiểm thử.</p></body></html>'''

    def test_match_passes(self):
        self.assertEqual(check_page(self.topic,self.rec,self.page),[])

    def test_duplicate_canonical_is_rejected(self):
        bad=self.page.replace('</head>','<link rel="canonical" href="https://example.com/"/> </head>')
        self.assertIn('canonical mismatch or duplicate',check_page(self.topic,self.rec,bad))

    def test_wrong_canonical_is_rejected(self):
        self.assertIn('canonical mismatch or duplicate',
            check_page(self.topic,self.rec,self.page.replace('unique-safe-article','wrong-article')))

    def test_noindex_cannot_pass(self):
        bad=self.page.replace('index, follow','noindex, follow')
        self.assertIn('public page is noindex',check_page(self.topic,self.rec,bad))

    def test_missing_body_fails(self):
        bad=self.page.replace('Nội dung đầu tiên của bài kiểm thử.','Một đoạn hoàn toàn khác.')
        self.assertIn('first paragraph mismatch',check_page(self.topic,self.rec,bad))

    def test_wrong_meta_description_fails(self):
        bad=self.page.replace('Mô tả ngắn đã xác minh trong WordPress','Sai mô tả',1)
        self.assertIn('meta description mismatch or duplicate',check_page(self.topic,self.rec,bad))

    def test_rotating_sampler_limits_and_prioritizes_newest(self):
        rows=[('NT-%06d'%i,{'verified_at':'2026-10-%02dT09:00:00+00:00'%i}) for i in range(1,11)]
        selected=choose(rows,dt.datetime(2026,10,16,tzinfo=dt.timezone.utc),4)
        self.assertEqual(len(selected),4)
        self.assertEqual([x[0] for x in selected[:2]],['NT-000010','NT-000009'])
        self.assertEqual(len(set(x[0] for x in selected)),4)

    def test_empty_batch_does_not_claim_live_qa(self):
        self.assertEqual(choose([],dt.datetime.now(dt.timezone.utc),10),[])

    def test_invalid_limit_fails(self):
        with self.assertRaises(ValueError):
            choose([],dt.datetime.now(dt.timezone.utc),0)

    def test_external_manual_promotion_is_not_silently_accepted(self):
        class PublicClient:
            def get(self, endpoint):
                self.endpoint = endpoint
                return [{'id':3882,'status':'publish','slug':'external-draft','link':SITE+'/external-draft/'}]
        client=PublicClient()
        records={'NT-000079':{'phase':'VERIFIED','status':'draft','wp_id':3882,'slug':'external-draft'}}
        errors=detect_unexpected_public_drafts(records,client)
        self.assertEqual(len(errors),1)
        self.assertEqual(errors[0]['wordpress_status'],'publish')
        self.assertEqual(errors[0]['ledger_status'],'draft')
        self.assertIn('slug=external-draft',client.endpoint)

    def test_private_draft_is_not_falsely_marked_as_public(self):
        class PublicClient:
            def get(self,endpoint):
                return []
        records={'NT-000079':{'phase':'VERIFIED','status':'draft','wp_id':3882,'slug':'external-draft'}}
        self.assertEqual(detect_unexpected_public_drafts(records,PublicClient()),[])

    def test_other_ids_with_same_slug_are_collision_not_adoption(self):
        class PublicClient:
            def get(self,endpoint):
                return [{'id':4001,'status':'publish','slug':'other-slug','link':SITE+'/other-slug/'}]
        records={'NT-000079':{'phase':'VERIFIED','status':'draft','wp_id':3882,'slug':'other-slug'}}
        issues=detect_unexpected_public_drafts(records,PublicClient())
        self.assertEqual(len(issues),1)
        self.assertIn('Another public post',issues[0]['error'])
if __name__=='__main__':unittest.main()
