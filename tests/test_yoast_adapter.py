"""Yoast adapter checks on the actual site's capabilities, without LLM/API keys."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publisher import seo_adapter_check,Publisher,production_allowed
from common import SITE, digest
from test_factory import FakeWP


class SeoAdapterTests(unittest.TestCase):
    def client(self,keys=None,canonical=None,link=None):
        if keys is None:keys=['_yoast_wpseo_title','_yoast_wpseo_metadesc']
        props={k:{'type':'string','readonly':False} for k in keys}
        url=link or SITE+'/public-existing-article/'
        c=Mock()
        c.request.return_value=({'schema':{'properties':{'meta':{'properties':props}}}}, {})
        c.get.return_value=[{'id':24,'link':url,
            'yoast_head_json':{'canonical':canonical if canonical is not None else url}}]
        return c

    def test_current_yoast_canonical_need_not_be_writeable(self):
        c=self.client()
        self.assertTrue(seo_adapter_check(c))
        self.assertEqual(c.get.call_count,1)
        self.assertIn('status=publish',c.get.call_args.args[0])

    def test_registered_seo_meta_keys_required(self):
        for keys in ([],['_yoast_wpseo_title'],['_yoast_wpseo_metadesc']):
            with self.subTest(keys=keys):
                c=self.client(keys=keys)
                self.assertFalse(seo_adapter_check(c))
                self.assertFalse(c.get.called)

    def test_default_yoast_canonical_must_match_permalinks(self):
        self.assertFalse(seo_adapter_check(self.client(canonical=SITE+'/wrong/')))
        self.assertFalse(seo_adapter_check(self.client(link='https://malicious.invalid/test/')))
        c=self.client()
        c.get.return_value=[]
        self.assertFalse(seo_adapter_check(c))

    def test_new_public_post_payload_does_not_write_unregistered_canonical(self):
        cfg={'mode':'production','production_enabled':True,
            'owner_approval_ref':'test','acceptance_passed':True,
            'seo_adapter_verified':True,'security_controls_verified':True,
            'paused':False,'emergency_stop':False}
        recorded=[]
        class CapturingWP:
            def request(self,path,payload=None,**kwargs):
                if path!='wp/v2/posts' or payload is None:
                    raise AssertionError('Unexpected WordPress request')
                recorded.append(payload)
                # Simulated network failure occurs AFTER outgoing payload capture.
                # Publisher must preserve POST_INTENT as NEEDS_RECONCILE.
                raise RuntimeError('simulated POST; no network access')
        ledger={'posts':{},'categories':{}}
        p=Publisher(CapturingWP(),cfg,ledger,lambda:None)
        topic={'topic_id':'NT-000999','title':'Test publication payload',
            'proposed_slug':'test-publication-payload',
            'canonical_target':SITE+'/test-publication-payload/'}
        with self.assertRaisesRegex(RuntimeError,'simulated POST'):
            p.create(topic,'Body for test.',digest('body'),156,'publish',[],
                     {'meta_title':'SEO verified title','meta_description':'SEO verified description'})
        self.assertEqual(len(recorded),1)
        self.assertEqual(recorded[0]['meta'],{
            '_yoast_wpseo_title':'SEO verified title',
            '_yoast_wpseo_metadesc':'SEO verified description'})
        self.assertEqual(ledger['posts'][topic['topic_id']]['phase'],'NEEDS_RECONCILE')


if __name__=='__main__':
    unittest.main()
