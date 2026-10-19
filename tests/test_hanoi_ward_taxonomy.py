"""Regression guard for the ONE approved Hanoi-ward rental category.

WordPress GET /wp/v2/categories/182 verified on 2026-10-20:
Blog 69 -> Hướng dẫn thuê xe 162 -> Thuê xe máy theo phường Hà Nội 182.
These tests do not fabricate a live REST readback or authorize publishing.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from taxonomy_sync import path_for,resolve

class HanoiWardTaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=json.loads((ROOT/"data"/"taxonomy.json").read_text(encoding="utf-8"))
        cls.registry={row["taxonomy_key"]:row for row in data["items"]}
        cls.items=data["items"]

    def test_one_category_and_exact_parent_path(self):
        key="hanoi-ward-rentals"
        self.assertIn(key,self.registry)
        row=self.registry[key]
        self.assertEqual(row["name"],"Thuê xe máy theo phường Hà Nội")
        self.assertEqual(row["slug"],"thue-xe-may-theo-phuong-ha-noi")
        self.assertEqual(row["wordpress_term_id"],182)
        self.assertEqual(row["wordpress_parent_id"],162)
        self.assertEqual(row["parent_key"],"rental-guide")
        self.assertEqual(row["existing_or_planned"],"existing")
        self.assertEqual([node["wordpress_term_id"] for node in path_for(key,self.registry)],[69,162,182])
        self.assertEqual([node["taxonomy_key"] for node in path_for(key,self.registry)],["blog","rental-guide",key])
        self.assertEqual(sum(item["wordpress_term_id"]==182 for item in self.items),1)
        self.assertEqual(sum(item["slug"]==row["slug"] for item in self.items),1)
        self.assertEqual(sum(item["taxonomy_key"]==key for item in self.items),1)

    def test_rest_snapshot_matches_verified_wordpress_term(self):
        snapshot=json.loads((ROOT/"data"/"existing-taxonomy.json").read_text(encoding="utf-8"))
        matches=[t for t in snapshot["items"] if t["id"]==182]
        self.assertEqual(len(matches),1)
        term=matches[0]
        self.assertEqual(term["parent"],162)
        self.assertEqual(term["slug"],"thue-xe-may-theo-phuong-ha-noi")
        self.assertEqual(term["name"],"Thuê xe máy theo phường Hà Nội")
        self.assertEqual(term["link"],"https://thuexemaynguyentu.com/blog/huong-dan-thue-xe/thue-xe-may-theo-phuong-ha-noi/")

    def test_existing_ancestor_terms_unchanged(self):
        self.assertEqual(self.registry["blog"]["wordpress_term_id"],69)
        self.assertEqual(self.registry["blog"]["wordpress_parent_id"],0)
        self.assertEqual(self.registry["rental-guide"]["wordpress_term_id"],162)
        self.assertEqual(self.registry["rental-guide"]["wordpress_parent_id"],69)

    def test_publisher_category_resolver_fails_closed_on_drift(self):
        live=[
            {"id":69,"parent":0,"slug":"blog","name":"Blog"},
            {"id":162,"parent":69,"slug":"huong-dan-thue-xe","name":"Hướng dẫn thuê xe"},
            {"id":182,"parent":162,"slug":"thue-xe-may-theo-phuong-ha-noi","name":"Thuê xe máy theo phường Hà Nội"},
        ]
        key="hanoi-ward-rentals"
        self.assertEqual(resolve(key,self.registry,live),182)
        wrong_parent=[dict(x,parent=69) if x["id"]==182 else x for x in live]
        with self.assertRaises(ValueError):
            resolve(key,self.registry,wrong_parent)
        wrong_slug=[dict(x,slug="thue-xe-may-phuong-khac") if x["id"]==182 else x for x in live]
        with self.assertRaises(ValueError):
            resolve(key,self.registry,wrong_slug)
        wrong_name=[dict(x,name="Thuê xe máy theo quận") if x["id"]==182 else x for x in live]
        with self.assertRaises(ValueError):
            resolve(key,self.registry,wrong_name)

    def test_editorial_drafts_not_mistaken_for_factory_posts(self):
        campaign=json.loads((ROOT/"editorial"/"seo-51-phuong"/"progress.json").read_text(encoding="utf-8"))
        self.assertEqual(campaign["target_articles"],51)
        self.assertLessEqual(campaign["imported_into_topic_factory"],campaign["completed_editorial_drafts"])
        self.assertLessEqual(campaign["published_new_articles"],campaign["imported_into_topic_factory"])

if __name__=="__main__":
    unittest.main()
