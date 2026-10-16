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
        # Use the existing fake client and only check outbound create payload,
        # never write to a real WordPress instance.
        from test_delivery_routing import DeliveryRoutingTests
        cfg=DeliveryRoutingTests().production
        wp=FakeWP()
        recorded=[]
        original=wp.request
        def captured(path,*args,**kwargs):
            if path=='wp/v2/posts' and args:
                recorded.append(args[0])
            return original(path,*args,**kwargs)
        wp.request=captured
        # FakeWP returns a simulated post whose public SEO is incomplete.
        # That may raise on frontend check; still assert the exact outgoing payload.
        p=Publisher(wp,cfg,{'posts':{},'categories':{}},lambda:None)
        topic={'topic_id':'NT-000999','title':'Test publication payload',
            'proposed_slug':'test-publication-payload',
            'canonical_target':SITE+'/test-publication-payload/'}
        try:
            p.create(topic,'Body for test.',digest('body'),156,'publish',[],
                     {'meta_title':'SEO verified title','meta_description':'SEO verified description'})
        except (ValueError,KeyError,TypeError,AttributeError,RuntimeError):
            pass
        self.assertEqual(len(recorded),1)
        self.assertEqual(recorded[0]['meta'],{
            '_yoast_wpseo_title':'SEO verified title',
            '_yoast_wpseo_metadesc':'SEO verified description'})


if __name__=='__main__':
    unittest.main()
