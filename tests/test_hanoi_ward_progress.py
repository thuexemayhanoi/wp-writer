"""Only verified, exact-category G7 WordPress posts increment Hanoi campaign."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from hanoi_ward_progress import reconcile

FILE="editorial/seo-51-phuong/batch-01/01-bo-de.md"
URL="https://thuexemaynguyentu.com/thue-xe-may-phuong-bo-de-chon-honda-vision-hay-wave/"
REQUIRED=["wordpress_status","slug","title","category","ownership_marker","content",
          "permalink","public_page","indexable","seo_meta"]

def progress():
    return {"campaign":"HN-51-WARDS","taxonomy_key":"hanoi-ward-rentals",
      "wordpress_category_id":182,"wordpress_parent_category_id":162,
      "completed_editorial_drafts":1,"completed":[{
        "ward":"Bồ Đề","file":FILE,"topic_id":None,
        "writer_qa_status":"NOT_SUBMITTED","publication_status":"GITHUB_EDITORIAL_ONLY"}],
      "imported_into_topic_factory":0,"published_new_articles":0}

def topic(key="hanoi-ward-rentals"):
    return {"topic_id":"NT-001234","campaign_id":"HN-51-WARDS",
      "campaign_editorial_file":FILE,"taxonomy_key":key,"topic_qa_status":"PLANNED",
      "canonical_target":URL}

def qa(status="PASS",source="sha-one"):
    return {"NT-001234":{"status":status,"seo_score":91,"quality_score":92,
                          "source_sha256":source,"errors":[],"review":[]}}

def ledger(g7=True,category=182):
    return {"posts":{"NT-001234":{
      "phase":"VERIFIED","expected_status":"publish","status":"publish",
      "category_id":category,"intended_taxonomy_key":"hanoi-ward-rentals",
      "source_hash":"sha-one","url":URL,"wp_id":5123,"verified_at":"2026-10-20T03:00:00Z",
      "g7":{"status":"PASS" if g7 else "FAIL","url":URL,"categories":[category],
            "checks":{k:True for k in REQUIRED if g7 or k!="seo_meta"}}}}}

class WardProgressTests(unittest.TestCase):
    def test_no_topic_or_receipt_is_just_editorial(self):
        p=reconcile(progress(),[],{"posts":{}}, {})
        self.assertEqual((p["imported_into_topic_factory"],p["published_new_articles"]),(0,0))
        self.assertIsNone(p["completed"][0]["topic_id"])

    def test_planned_is_imported_but_no_wp_count_without_proof(self):
        for record,evidence in (
            ({"posts":{}},qa()),
            (ledger(g7=False),qa()),
            (ledger(category=69),qa()),
            (ledger(),qa(status="REVIEW")),
            (ledger(),qa(source="wrong-hash")),
        ):
            with self.subTest(record=record,evidence=evidence):
                p=reconcile(progress(),[topic()],record,evidence)
                self.assertEqual(p["imported_into_topic_factory"],1)
                self.assertEqual(p["published_new_articles"],0)

    def test_g7_complete_exact_182_counts_once(self):
        p=reconcile(progress(),[topic()],ledger(),qa())
        self.assertEqual(p["imported_into_topic_factory"],1)
        self.assertEqual(p["published_new_articles"],1)
        r=p["completed"][0]
        self.assertEqual(r["topic_id"],"NT-001234")
        self.assertEqual(r["wp_post_id"],5123)
        self.assertEqual(r["wp_permalink"],URL)
        self.assertEqual(r["publication_status"],"WORDPRESS_PUBLISHED_G7_PASS")
        again=reconcile(p,[topic()],ledger(),qa())
        self.assertEqual(again["published_new_articles"],1)

    def test_threshold_follows_the_qa_configuration(self):
        """A 78/80 article is QA PASS under the owner's 76 threshold; below the configured minimum it never counts."""
        def scored(seo, quality):
            e = qa()
            e["NT-001234"].update({"seo_score": seo, "quality_score": quality})
            return e
        with patch("hanoi_ward_progress.load", return_value={"seo_min": 76, "quality_min": 76}):
            ok = reconcile(progress(), [topic()], ledger(), scored(78, 80))
            low = reconcile(progress(), [topic()], ledger(), scored(75, 90))
        self.assertEqual(ok["published_new_articles"], 1)
        self.assertEqual(low["published_new_articles"], 0)
        with patch("hanoi_ward_progress.load", return_value={"seo_min": 85, "quality_min": 85}):
            strict = reconcile(progress(), [topic()], ledger(), scored(78, 80))
        self.assertEqual(strict["published_new_articles"], 0)

    def test_wrong_taxonomy_does_not_count(self):
        p=reconcile(progress(),[topic("rental-guide")],ledger(),qa())
        self.assertEqual(p["imported_into_topic_factory"],0)
        self.assertEqual(p["published_new_articles"],0)

    def test_duplicate_topic_for_one_manuscript_is_rejected(self):
        other={**topic(),"topic_id":"NT-001235"}
        with self.assertRaisesRegex(ValueError,"MULTIPLE_TOPICS_FOR_WARD"):
            reconcile(progress(),[topic(),other],{"posts":{}}, {})

    def test_registry_mutation_fails_closed(self):
        changed={**progress(),"wordpress_category_id":69}
        with self.assertRaisesRegex(ValueError,"HANOI_WARD_CATEGORY_UNVERIFIED"):
            reconcile(changed,[],{"posts":{}},{})

    def test_existing_live_ward_article_is_a_hold_not_a_new_publication(self):
        existing = [{"id": 4344, "url": URL,
                     "slug": "thue-xe-may-phuong-bo-de-chon-honda-vision-hay-wave",
                     "status": "publish", "categories": [182]}]
        p = reconcile(progress(), [topic()], {"posts": {}},
                      qa(status="FAIL"), existing)
        self.assertEqual(p["published_new_articles"], 0)
        self.assertEqual(p["existing_wordpress_collisions"], 1)
        r = p["completed"][0]
        self.assertEqual(r["publication_status"], "EXISTING_WORDPRESS_NEEDS_RECONCILIATION")
        self.assertEqual(r["existing_wp_collision"]["wp_ids"], [4344])
        self.assertIsNone(r.get("wp_post_id"))
        good = reconcile(progress(), [topic()], ledger(), qa(), existing)
        self.assertEqual(good["published_new_articles"], 1)
        self.assertEqual(good["existing_wordpress_collisions"], 0)

    def test_unpublished_collision_is_not_wrongly_credited(self):
        draft = [{"id": 4344, "url": URL, "status": "draft", "categories": [182]}]
        p = reconcile(progress(), [topic()], {"posts": {}}, qa(status="FAIL"), draft)
        self.assertEqual(p["existing_wordpress_collisions"], 0)
        self.assertEqual(p["published_new_articles"], 0)


    def test_externally_verified_live_ward_counts_separately_from_factory_g7(self):
        existing = [{"id": 4344, "url": URL,
                     "slug": "thue-xe-may-phuong-bo-de-chon-honda-vision-hay-wave",
                     "status": "publish", "categories": [182]}]
        proof = {"verification_method": "authenticated_wp_rest",
                 "wp_post_id": 4344, "status": "publish", "url": URL,
                 "canonical": URL, "title": topic()["title"],
                 "category_ids": [182], "robots_index": "index",
                 "public_http": 200, "verified_at": "2026-10-21T16:57:00Z"}
        p = reconcile(progress(), [topic()], {"posts": {}}, qa(status="FAIL"),
                      existing, {"posts": {"NT-001234": proof}})
        self.assertEqual(p["published_new_articles"], 0)
        self.assertEqual(p["published_existing_articles"], 1)
        self.assertEqual(p["published_live_ward_articles"], 1)
        row = p["completed"][0]
        self.assertEqual(row["publication_status"], "WORDPRESS_EXISTING_LIVE_VERIFIED")
        self.assertEqual(row["wp_post_id"], 4344)
        self.assertEqual(row["wp_permalink"], URL)
        # Never transform an external live proof into a fabricated factory G7.
        for key, value in (("robots_index", "noindex"), ("category_ids", [69]),
                           ("canonical", URL + "wrong"), ("wp_post_id", 9999),
                           ("public_http", 404)):
            bad = dict(proof, **{key: value})
            unsafe = reconcile(progress(), [topic()], {"posts": {}}, qa(status="FAIL"),
                               existing, {"posts": {"NT-001234": bad}})
            self.assertEqual(unsafe["published_existing_articles"], 0, key)
            self.assertEqual(unsafe["existing_wordpress_collisions"], 1, key)

if __name__=="__main__":
    unittest.main()
