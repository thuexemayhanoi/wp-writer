"""Pre-publication editorial checks for Hà Nội 51 phường batch 04.

These regression tests validate draft shape and originality only.
They DO NOT replace official source-evidence Research QA or authorize publishing.
"""
import json
import re
import sys
import unittest
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from qa import word_count, counted_text, fingerprint, jaccard

NEW=[
    ("Bạch Mai","10-bach-mai.md","bachmai.hanoi.gov.vn"),
    ("Vĩnh Tuy","11-vinh-tuy.md","vinhtuy.hanoi.gov.vn"),
    ("Cầu Giấy","12-cau-giay.md","caugiay.hanoi.gov.vn"),
]
FILES=[
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-01"/f for f in ("01-bo-de.md","02-cua-nam.md","03-hoan-kiem.md")),
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-02"/f for f in ("04-viet-hung.md","05-tay-ho.md","06-dong-da.md")),
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-03"/f for f in ("07-ngoc-ha.md","08-giang-vo.md","09-hai-ba-trung.md")),
    *(ROOT/"editorial"/"seo-51-phuong"/"batch-04"/f for _,f,_ in NEW),
]

def load_article(file):
    raw=file.read_text(encoding="utf-8")
    m=re.match(r"\A---\n(.*?)\n---\n",raw,flags=re.S)
    if m is None:
        raise AssertionError("Missing YAML frontmatter: "+str(file))
    return yaml.safe_load(m.group(1)),raw[m.end():].strip()

class WardBatch04EditorialTests(unittest.TestCase):
    def test_unique_ward_h1_and_safe_editing_metadata(self):
        titles=set()
        slugs=set()
        for ward,file,host in NEW:
            with self.subTest(ward=ward):
                metadata,body=load_article(ROOT/"editorial"/"seo-51-phuong"/"batch-04"/file)
                self.assertEqual(metadata["batch"],"HN-51-WARDS-04")
                self.assertEqual(metadata["ward"],ward)
                self.assertTrue(metadata["editorial_status"].startswith("DRAFT"))
                self.assertIn(ward,metadata["h1"])
                self.assertEqual(re.findall(r"^# (.+)$",body,re.M),[metadata["h1"]])
                self.assertGreaterEqual(len(re.findall(r"^## ",body,re.M)),8)
                self.assertNotIn(metadata["h1"],titles)
                self.assertNotIn(metadata["suggested_slug"],slugs)
                self.assertNotIn("topic_id",metadata)
                self.assertNotIn("writer_slot",metadata)
                self.assertIn(host,metadata["official_locality_source"])
                titles.add(metadata["h1"])
                slugs.add(metadata["suggested_slug"])

    def test_real_qa_word_length_nap_and_two_internal_links(self):
        for ward,file,_ in NEW:
            with self.subTest(ward=ward):
                metadata,body=load_article(ROOT/"editorial"/"seo-51-phuong"/"batch-04"/file)
                words=word_count(body)
                self.assertGreaterEqual(words,1600,(ward,words))
                self.assertLessEqual(words,5000,(ward,words))
                self.assertIn("112 Nguyễn Văn Cừ",body)
                self.assertIn("0942 467 674",body)
                self.assertIn("09:00–21:00",body)
                links=set(re.findall(r"\]\((https://thuexemaynguyentu[.]com/[^)]+)\)",body))
                self.assertGreaterEqual(len(links),2,(ward,links))
                self.assertIn(ward,body)

    def test_non_duplicate_against_all_prior_wards(self):
        sets={}
        for file in FILES:
            _,body=load_article(file)
            sets[file.stem]=fingerprint(counted_text(body))
        ids=list(sets)
        for i in range(len(ids)):
            for j in range(i+1,len(ids)):
                ratio=jaccard(sets[ids[i]],sets[ids[j]])
                self.assertLess(ratio,0.12,(ids[i],ids[j],ratio))

    def test_facts_and_unverified_yamaha_stock_claim(self):
        b=ROOT/"editorial"/"seo-51-phuong"/"batch-04"
        _,bach=load_article(b/"10-bach-mai.md")
        _,vinh=load_article(b/"11-vinh-tuy.md")
        _,cau=load_article(b/"12-cau-giay.md")
        self.assertIn("200.000 đồng/ngày",bach)
        self.assertIn("50cc",bach)
        self.assertIn("giấy tờ",bach.lower())
        self.assertIn("cầu",vinh.lower())
        self.assertIn("Vision",vinh)
        self.assertIn("Air Blade",vinh)
        self.assertIn("Yamaha Janus chưa có giá",cau)
        self.assertIn("không",cau.lower())
        self.assertIn("Dịch Vọng",cau)

    def test_campaign_checkpoint_honors_manual_and_hourly_cadence(self):
        p=json.loads((ROOT/"editorial"/"seo-51-phuong"/"progress.json").read_text(encoding="utf-8"))
        self.assertEqual(p["target_articles"],51)
        self.assertGreaterEqual(p["completed_editorial_drafts"],12)
        self.assertEqual(p["pending_editorial"],51-p["completed_editorial_drafts"])
        self.assertEqual(p["next_review_batch"],p["completed_editorial_drafts"]//3+1)
        self.assertEqual(len(p["completed"]),p["completed_editorial_drafts"])
        self.assertEqual(len(set(x["ward"] for x in p["completed"])),p["completed_editorial_drafts"])
        self.assertEqual([x["ward"] for x in p["completed"][9:12]],
                         [w for w,_,_ in NEW])
        self.assertLessEqual(p["published_new_articles"],p["imported_into_topic_factory"])
        self.assertLessEqual(p["imported_into_topic_factory"],p["completed_editorial_drafts"])


if __name__=="__main__":
    unittest.main()
