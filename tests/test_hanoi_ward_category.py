"""One-and-only Hanoi ward category: WordPress 69 -> 162 -> 182.

These tests are structural/no-secrets. They guarantee exact-category routing
and fail-closed publication; WordPress term readback must be separately checked.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from taxonomy_sync import by_key, resolve, path_for
from publisher import delivery_route

KEY="hanoi-ward-rentals"
def live_categories():
    return [
        {"id":69,"parent":0,"slug":"blog","name":"Blog"},
        {"id":162,"parent":69,"slug":"huong-dan-thue-xe","name":"Hướng dẫn thuê xe"},
        {"id":182,"parent":162,"slug":"thue-xe-may-theo-phuong-ha-noi",
         "name":"Thuê xe máy theo phường Hà Nội"},
    ]

def production():
    return {"mode":"production","production_enabled":True,
      "owner_approval_ref":"owner-ok","seo_adapter_verified":True,
      "paused":False,"emergency_stop":False,
      "allow_category_create":True,"on_category_mismatch":"draft",
      "fallback_draft_taxonomy_key":"blog"}

class HanoiWardCategoryTests(unittest.TestCase):
    def test_registry_contains_one_term_and_correct_ancestry(self):
        registry=by_key()
        matches=[v for v in registry.values()
                 if v.get("wordpress_term_id")==182
                 or v.get("taxonomy_key")==KEY
                 or v.get("slug")=="thue-xe-may-theo-phuong-ha-noi"]
        self.assertEqual(len(matches),1,matches)
        item=matches[0]
        self.assertEqual(item["taxonomy_key"],KEY)
        self.assertEqual(item["name"],"Thuê xe máy theo phường Hà Nội")
        self.assertEqual(item["slug"],"thue-xe-may-theo-phuong-ha-noi")
        self.assertEqual(item["parent_key"],"rental-guide")
        self.assertEqual(item["wordpress_term_id"],182)
        self.assertEqual(item["wordpress_parent_id"],162)
        self.assertEqual([x["wordpress_term_id"] for x in path_for(KEY,registry)],
                         [69,162,182])
        self.assertEqual(resolve(KEY,registry,live_categories()),182)

    def test_qa_pass_delivers_public_to_exact_wordpress_term(self):
        result=delivery_route({"taxonomy_key":KEY},production(),by_key(),
                               live_categories())
        self.assertEqual(result,{"status":"publish","category_id":182,
          "intended_taxonomy_key":KEY,"category_resolution":"EXACT",
          "category_warning":None})

    def test_drift_holds_on_github_no_draft_or_category_creation(self):
        variants=[
            [x for x in live_categories() if x["id"]!=182],
            [{**x,"parent":69} if x["id"]==182 else x for x in live_categories()],
            [{**x,"name":"Thuê xe theo phường khác"} if x["id"]==182 else x
             for x in live_categories()],
            [{**x,"slug":"doi-slug"} if x["id"]==182 else x
             for x in live_categories()],
            [{**x,"parent":0} if x["id"]==162 else x
             for x in live_categories()],
        ]
        for actual in variants:
            called=[]
            with self.subTest(categories=actual):
                with self.assertRaisesRegex(ValueError,"HANOI_WARD_CATEGORY_HOLD"):
                    delivery_route({"taxonomy_key":KEY},production(),by_key(),actual,
                                   create_category=lambda key:called.append(key))
                self.assertEqual(called,[])

    def test_unapproved_or_paused_never_writes_wp(self):
        for change in ({"production_enabled":False},{"paused":True},
                       {"emergency_stop":True}):
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError,"not approved"):
                    delivery_route({"taxonomy_key":KEY},{**production(),**change},
                                   by_key(),live_categories())

if __name__=="__main__":
    unittest.main()
