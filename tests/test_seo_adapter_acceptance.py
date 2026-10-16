"""Acceptance tests do not call live WordPress."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import seo_adapter_acceptance as x


class AdapterAcceptanceTests(unittest.TestCase):
    def client(self, slug=x.DRAFT_SLUG, status='draft'):
        c=Mock()
        p={'id':x.DRAFT_ID,'slug':slug,'status':status,'meta':{}}
        a={'id':x.DRAFT_ID,'slug':x.DRAFT_SLUG,'status':'draft',
           'meta':{'_yoast_wpseo_title':x.SEO_TITLE,
                   '_yoast_wpseo_metadesc':x.SEO_DESC}}
        c.get.side_effect=[p,a]
        return c

    def test_known_test_draft_only_writes_title_description(self):
        c=self.client()
        with patch.object(x,'seo_adapter_check',return_value=True):
            receipt=x.check(c)
        self.assertEqual(receipt['status'],'PASS')
        self.assertEqual(receipt['wordpress_campaign_posts_published'],0)
        self.assertEqual(c.request.call_count,1)
        self.assertEqual(c.request.call_args.args[0],'wp/v2/posts/'+str(x.DRAFT_ID))
        self.assertEqual(set(c.request.call_args.args[1]['meta']),
                         {'_yoast_wpseo_title','_yoast_wpseo_metadesc'})
        self.assertNotIn('status',c.request.call_args.args[1])

    def test_wrong_post_slug_refuses_all_writes(self):
        c=self.client(slug='some-other-draft')
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            x.check(c)
        c.request.assert_not_called()

    def test_published_test_post_refuses_all_writes(self):
        c=self.client(status='publish')
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            x.check(c)
        c.request.assert_not_called()

    def test_unverified_live_yoast_adapter_refuses_all_writes(self):
        c=self.client()
        with patch.object(x,'seo_adapter_check',return_value=False):
            with self.assertRaisesRegex(ValueError,'Yoast registered'):
                x.check(c)
        c.request.assert_not_called()

    def test_readback_missing_metadata_is_failure(self):
        c=self.client()
        c.get.side_effect=[{'id':x.DRAFT_ID,'slug':x.DRAFT_SLUG,'status':'draft'},
                           {'id':x.DRAFT_ID,'slug':x.DRAFT_SLUG,'status':'draft',
                            'meta':{'_yoast_wpseo_title':x.SEO_TITLE}}]
        with patch.object(x,'seo_adapter_check',return_value=True):
            with self.assertRaisesRegex(ValueError,'readback failed'):
                x.check(c)

if __name__=='__main__':
    unittest.main()
