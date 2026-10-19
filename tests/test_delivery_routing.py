"""WordPress delivery routing checks; no secrets or live WordPress calls."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publisher import delivery_route, draft_staging_allowed, production_allowed, Publisher
from taxonomy_sync import by_key
from test_factory import FakeWP
from common import SITE, digest


class DeliveryRoutingTests(unittest.TestCase):
    def setUp(self):
        self.registry=by_key()
        self.live=[
            {'id':row['wordpress_term_id'],'parent':row['wordpress_parent_id'],
             'slug':row['slug'],'name':row['name']}
            for row in self.registry.values() if row.get('wordpress_term_id')
        ]
        self.staging={'mode':'draft_only','production_enabled':False,
            'draft_staging_enabled':True,'draft_staging_approval_ref':'owner-test',
            'security_controls_verified':True,'on_category_mismatch':'draft',
            'fallback_draft_taxonomy_key':'blog','allow_category_create':False,
            'paused':False,'emergency_stop':False}
        self.production={**self.staging,'mode':'production','production_enabled':True,
            'owner_approval_ref':'owner-test','acceptance_passed':True,
            'seo_adapter_verified':True,'draft_staging_enabled':False}
        self.exact={'topic_id':'NT-000047','taxonomy_key':'reviews',
            'title':'Safe demo article','proposed_slug':'safe-demo-article',
            'canonical_target':SITE+'/safe-demo-article/'}
        # Synthetic missing-term fixture: troubleshooting is deliberately uncreated.
        self.unmapped={**self.exact,'topic_id':'NT-000075','taxonomy_key':'troubleshooting'}

    def test_hanoi_ward_only_publishes_in_single_exact_category_182(self):
        topic={**self.exact,'topic_id':'NT-001771',
               'taxonomy_key':'hanoi-ward-rentals'}
        route=delivery_route(topic,self.production,self.registry,self.live)
        self.assertEqual(route['status'],'publish')
        self.assertEqual(route['category_id'],182)
        self.assertEqual(route['category_resolution'],'EXACT')

    def test_hanoi_ward_never_falls_back_to_wrong_category_or_draft(self):
        topic={**self.exact,'topic_id':'NT-001771',
               'taxonomy_key':'hanoi-ward-rentals'}
        for changes in ({'parent':69},{'slug':'other-slug'},
                        {'name':'Other category'}):
            changed=[dict(x,**changes) if x['id']==182 else x
                     for x in self.live]
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError,'Hanoi ward category blocked'):
                    delivery_route(topic,self.production,self.registry,changed,
                                   create_category=lambda _: self.fail('Must never create ward term'))
        missing=[x for x in self.live if x['id']!=182]
        with self.assertRaisesRegex(ValueError,'Hanoi ward category blocked'):
            delivery_route(topic,{**self.production,'allow_category_create':True},
                           self.registry,missing,create_category=lambda _: self.fail('No new category'))
        with self.assertRaisesRegex(ValueError,'Hanoi ward publication requires'):
            delivery_route(topic,self.staging,self.registry,self.live)
        with self.assertRaisesRegex(ValueError,'Hanoi ward publication requires'):
            delivery_route(topic,self.staging,self.registry,self.live,acceptance_draft=True)

    def test_exact_path_publishes_only_with_full_approval(self):
        self.assertTrue(production_allowed(self.production))
        decision=delivery_route(self.exact,self.production,self.registry,self.live)
        self.assertEqual((decision['status'],decision['category_id'],decision['category_resolution']),
                         ('publish',156,'EXACT'))
        self.assertEqual(decision['intended_taxonomy_key'],'reviews')

    def test_exact_path_publishes_without_acceptance_or_security_flags(self):
        policy={k:v for k,v in self.production.items()
                if k not in ('acceptance_passed','security_controls_verified')}
        self.assertTrue(production_allowed(policy))
        decision=delivery_route(self.exact,policy,self.registry,self.live)
        self.assertEqual((decision['status'],decision['category_resolution']),
                         ('publish','EXACT'))

    def test_missing_category_is_wordpress_draft_not_public(self):
        decision=delivery_route(self.unmapped,self.production,self.registry,self.live)
        self.assertEqual((decision['status'],decision['category_id'],decision['category_resolution']),
                         ('draft',69,'FALLBACK_DRAFT'))
        self.assertEqual(decision['intended_taxonomy_key'],'troubleshooting')
        self.assertTrue(decision['category_warning'])

    def test_draft_staging_keeps_even_exact_mapping_non_public(self):
        self.assertTrue(draft_staging_allowed(self.staging))
        decision=delivery_route(self.exact,self.staging,self.registry,self.live)
        self.assertEqual(decision['status'],'draft')
        self.assertEqual(decision['category_id'],156)

    def test_missing_approval_or_security_blocks_wordpress_writes(self):
        for changes in ({'draft_staging_enabled':False},
                        {'draft_staging_approval_ref':None},
                        {'security_controls_verified':False},
                        {'paused':True}):
            policy={**self.staging,**changes}
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                delivery_route(self.exact,policy,self.registry,self.live)
        with self.assertRaises(ValueError):
            delivery_route(self.exact,{**self.staging,'mode':'dry_run'},
                           self.registry,self.live)
        with self.assertRaises(ValueError):
            delivery_route(self.exact,{**self.production,'seo_adapter_verified':False},
                           self.registry,self.live)

    def test_uncategorized_is_never_a_valid_intended_target(self):
        with self.assertRaisesRegex(ValueError,'Uncategorized'):
            delivery_route({**self.unmapped,'taxonomy_key':'uncategorized'},
                           self.staging,self.registry,self.live)

    def test_no_fallback_when_unapproved(self):
        with self.assertRaisesRegex(ValueError,'Category blocked'):
            delivery_route(self.unmapped,{**self.staging,'on_category_mismatch':'block'},
                           self.registry,self.live)

    def test_category_creation_requires_explicit_permission(self):
        created=[]
        def create(key):
            created.append(key)
            return 9876
        route=delivery_route(self.unmapped,self.production,self.registry,self.live,
                             create_category=create)
        self.assertFalse(created)
        self.assertEqual(route['status'],'draft')
        route=delivery_route(self.unmapped,{**self.production,'allow_category_create':True},
                             self.registry,self.live,create_category=create)
        self.assertEqual((route['status'],route['category_id'],created),
                         ('publish',9876,['troubleshooting']))
        self.assertEqual(route['category_resolution'],'CREATED')

    def test_uncertain_category_creation_must_not_fallback(self):
        def uncertain(_):
            raise ValueError('POST outcome unknown')
        with self.assertRaisesRegex(ValueError,'reconciliation'):
            delivery_route(self.unmapped,{**self.production,'allow_category_create':True},
                           self.registry,self.live,create_category=uncertain)

    def test_legacy_draft_acceptance_remains_explicit(self):
        disabled={**self.staging,'draft_staging_enabled':False,
                  'draft_staging_approval_ref':None,'security_controls_verified':False}
        decision=delivery_route(self.unmapped,disabled,self.registry,self.live,
                                acceptance_draft=True)
        self.assertEqual(decision['status'],'draft')
        with self.assertRaises(ValueError):
            delivery_route(self.unmapped,disabled,self.registry,self.live)

    def test_fallback_receipt_tracks_taxonomy_without_publication(self):
        route=delivery_route(self.unmapped,self.staging,self.registry,self.live)
        client=FakeWP()
        ledger={'posts':{},'categories':{}}
        publisher=Publisher(client,self.staging,ledger,lambda:None)
        record=publisher.create(self.unmapped,'Draft-only test body.',digest('body'),route['category_id'],
                                route['status'],[],route=route)
        self.assertEqual(record['status'],'draft')
        self.assertEqual(record['category_resolution'],'FALLBACK_DRAFT')
        self.assertEqual(record['intended_taxonomy_key'],'troubleshooting')
        self.assertEqual(record['category_id'],69)
        self.assertEqual(len(client.posts),1)
        again=publisher.create(self.unmapped,'Draft-only test body.',digest('body'),69,'draft',[],route=route)
        self.assertEqual(again['wp_id'],record['wp_id'])
        self.assertEqual(len(client.posts),1)

    def test_production_fallback_can_write_only_a_draft(self):
        route=delivery_route(self.unmapped,self.production,self.registry,self.live)
        client=FakeWP()
        ledger={'posts':{},'categories':{}}
        publisher=Publisher(client,self.production,ledger,lambda:None)
        record=publisher.create(self.unmapped,'Draft-only test body.',digest('body'),69,
                                'draft',[],route=route)
        self.assertEqual(record['status'],'draft')
        self.assertEqual(client.posts[0]['status'],'draft')
        with self.assertRaisesRegex(ValueError,'Draft writes not explicitly enabled'):
            publisher.create({**self.unmapped,'topic_id':'NT-000999'},
                             'body',digest('new'),69,'draft',[],route=None)


if __name__=='__main__':
    unittest.main()
