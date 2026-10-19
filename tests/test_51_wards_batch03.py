"""Pre-Research editorial QA for Hanoi's third batch of three wards.

This test never grants official Research QA, writer lease, publication approval,
or a G7 verification receipt. Only checks draft fitness.
"""
import json
import re
import sys
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from qa import word_count,counted_text,fingerprint,jaccard

NEW=[
    ("Ngọc Hà","07-ngoc-ha.md","ngocha.hanoi.gov.vn"),
    ("Giảng Võ","08-giang-vo.md","giangvo.hanoi.gov.vn"),
    ("Hai Bà Trưng","09-hai-ba-trung.md","haibatrung.hanoi.gov.vn"),
]
ALL_FILES=[
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-01"/s for s in ("01-bo-de.md","02-cua-nam.md","03-hoan-kiem.md")),
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-02"/s for s in ("04-viet-hung.md","05-tay-ho.md","06-dong-da.md")),
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-03"/s for _,s,_ in NEW),
]

def parse(path):
    source=path.read_text(encoding="utf-8")
    match=re.match(r"\A---\n(.*?)\n---\n",source,flags=re.S)
    if not match:
        raise AssertionError("Editorial frontmatter required: "+str(path))
    return yaml.safe_load(match.group(1)),source[match.end():].strip()

class WardBatch03EditorialTests(unittest.TestCase):
    def test_correct_wards_unique_h1_and_usable_lengths(self):
        titles=set()
        slugs=set()
        for ward,filename,domain in NEW:
            with self.subTest(ward=ward):
                meta,body=parse(ROOT/"editorial"/"seo-51-phuong"/"batch-03"/filename)
                self.assertEqual(meta["ward"],ward)
                self.assertEqual(meta["batch"],"HN-51-WARDS-03")
                self.assertTrue(meta["editorial_status"].startswith("DRAFT"))
                self.assertIn(ward,meta["h1"])
                self.assertEqual(re.findall(r"^# (.+)$",body,flags=re.M),[meta["h1"]])
                self.assertNotIn(meta["h1"],titles)
                self.assertNotIn(meta["suggested_slug"],slugs)
                self.assertNotIn("topic_id",meta)
                self.assertNotIn("writer_slot",meta)
                self.assertGreaterEqual(len(re.findall(r"^## ",body,flags=re.M)),8)
                words=word_count(body)
                self.assertGreaterEqual(words,1600,(ward,words))
                self.assertLessEqual(words,5000,(ward,words))
                self.assertIn(domain,meta["official_locality_source"])
                titles.add(meta["h1"])
                slugs.add(meta["suggested_slug"])

    def test_verified_nap_pricing_provenance_and_internal_links(self):
        for ward,filename,_ in NEW:
            with self.subTest(ward=ward):
                meta,body=parse(ROOT/"editorial"/"seo-51-phuong"/"batch-03"/filename)
                self.assertIn("112 Nguyễn Văn Cừ",body)
                self.assertIn("0942 467 674",body)
                self.assertIn("09:00–21:00",body)
                links=set(re.findall(r"\]\((https://thuexemaynguyentu[.]com/[^)]+)\)",body))
                self.assertGreaterEqual(len(links),2,(ward,links))
                self.assertIn("data/business-facts.json",
                              (ROOT/"editorial"/"seo-51-phuong"/"README.md").read_text(encoding="utf-8"))
                self.assertNotIn("đã qua QA chính thức",body.lower())

    def test_no_near_duplicate_earlier_or_current_ward_drafts(self):
        sets={}
        for file in ALL_FILES:
            _,body=parse(file)
            sets[file.stem]=fingerprint(counted_text(body))
        names=list(sets)
        for i in range(len(names)):
            for j in range(i+1,len(names)):
                ratio=jaccard(sets[names[i]],sets[names[j]])
                self.assertLess(ratio,0.12,(names[i],names[j],ratio))

    def test_editorial_progress_and_owner_pilot_unchanged(self):
        p=json.loads((ROOT/"editorial"/"seo-51-phuong"/"progress.json").read_text(encoding="utf-8"))
        self.assertEqual(p["completed_editorial_drafts"],9)
        self.assertEqual(p["target_articles"],51)
        self.assertEqual(p["pending_editorial"],42)
        self.assertEqual(p["next_review_batch"],4)
        self.assertEqual(p["published_new_articles"],0)
        self.assertEqual(p["imported_into_topic_factory"],0)
        self.assertEqual(len(p["completed"]),9)
        self.assertEqual(len({x["ward"] for x in p["completed"]}),9)
        self.assertEqual([x["ward"] for x in p["completed"][-3:]],[x[0] for x in NEW])
        production=json.loads((ROOT/"config"/"production-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(production["publisher_pilot"]["id"],"pilot-three-20261019")
        self.assertEqual(production["publisher_pilot"]["max_posts"],3)

if __name__=="__main__":
    unittest.main()
