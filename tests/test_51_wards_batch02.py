"""Editorial safeguards for second three Hanoi ward manuscripts.

These checks do not constitute official Research QA, Writer lease authorization,
Publisher authorization, or WordPress G7 verification.
"""
from pathlib import Path
import json
import re
import sys
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from qa import word_count,counted_text,fingerprint,jaccard

WARDS=[
    ("Việt Hưng","04-viet-hung.md","viethung.hanoi.gov.vn"),
    ("Tây Hồ","05-tay-ho.md","tayho.hanoi.gov.vn"),
    ("Đống Đa","06-dong-da.md","dongda.hanoi.gov.vn"),
]

class WardBatch02EditorialTests(unittest.TestCase):
    FOLDER=ROOT/"editorial"/"seo-51-phuong"/"batch-02"

    @classmethod
    def load_article(cls,ward,filename):
        raw=(cls.FOLDER/filename).read_text(encoding="utf-8")
        m=re.match(r"\A---\n(.*?)\n---\n",raw,flags=re.S)
        if not m:
            raise AssertionError("YAML editorial metadata missing: "+filename)
        return yaml.safe_load(m.group(1)),raw[m.end():].strip()

    def test_titles_wards_slugs_and_batch_metadata(self):
        titles=set()
        slugs=set()
        for ward,file,official_host in WARDS:
            with self.subTest(ward=ward):
                meta,body=self.load_article(ward,file)
                self.assertEqual(meta.get("ward"),ward)
                self.assertEqual(meta.get("batch"),"HN-51-WARDS-02")
                self.assertTrue(meta.get("editorial_status","").startswith("DRAFT"))
                self.assertIn(ward,meta["h1"])
                self.assertEqual(re.findall(r"^# (.+)$",body,flags=re.M),[meta["h1"]])
                self.assertGreaterEqual(len(re.findall(r"^## .+$",body,flags=re.M)),6)
                self.assertNotIn(meta["h1"],titles)
                self.assertNotIn(meta["suggested_slug"],slugs)
                self.assertIn(official_host,meta["official_locality_source"])
                self.assertNotIn("topic_id",meta)
                self.assertNotIn("writer_slot",meta)
                titles.add(meta["h1"])
                slugs.add(meta["suggested_slug"])

    def test_length_nap_and_internal_link_contract(self):
        for ward,file,_ in WARDS:
            with self.subTest(ward=ward):
                meta,body=self.load_article(ward,file)
                w=word_count(body)
                self.assertGreaterEqual(w,1600,(ward,w))
                self.assertLessEqual(w,5000,(ward,w))
                self.assertIn("112 Nguyễn Văn Cừ",body)
                self.assertIn("0942 467 674",body)
                self.assertIn("09:00–21:00",body)
                links=set(re.findall(r"\]\((https://thuexemaynguyentu[.]com/[^)]+)\)",body))
                self.assertGreaterEqual(len(links),2,(ward,links))
                self.assertIn(ward,body)
                self.assertIn("chưa",body.lower())

    def test_no_near_duplicates_with_prior_batch_or_each_other(self):
        corpus={}
        names=[
            *(("old-"+name,ROOT/"editorial"/"seo-51-phuong"/"batch-01"/file)
              for name,file in [("Bồ Đề","01-bo-de.md"),("Cửa Nam","02-cua-nam.md"),("Hoàn Kiếm","03-hoan-kiem.md")]),
            *((ward,self.FOLDER/file) for ward,file,_ in WARDS),
        ]
        for name,path in names:
            raw=path.read_text(encoding="utf-8")
            m=re.match(r"\A---\n.*?\n---\n",raw,flags=re.S)
            self.assertIsNotNone(m)
            body=raw[m.end():].strip()
            corpus[name]=fingerprint(counted_text(body))
        keys=list(corpus)
        for i in range(len(keys)):
            for j in range(i+1,len(keys)):
                # Editorial 5-gram similarity under 12%; independent intent still
                # must be verified against published WordPress URLs at intake.
                ratio=jaccard(corpus[keys[i]],corpus[keys[j]])
                self.assertLess(ratio,0.12,(keys[i],keys[j],ratio))

    def test_models_and_legal_discussions_are_not_fake_stock_claims(self):
        meta_vi,body_vi=self.load_article(*WARDS[0][:2])
        meta_tay,body_tay=self.load_article(*WARDS[1][:2])
        meta_dong,body_dong=self.load_article(*WARDS[2][:2])
        self.assertIn("không có dữ liệu xác nhận",body_vi.lower())
        self.assertIn("Yamaha Sirius",body_vi)
        self.assertIn("chưa có mức giá",body_tay.lower())
        self.assertIn("xe điện",body_tay.lower())
        self.assertIn("Cub 50",body_dong)
        self.assertIn("SYM 50cc",body_dong)
        self.assertIn("tối thiểu 18 tuổi",body_dong)
        self.assertIn("Luật Trật tự, an toàn giao thông",body_dong)
        self.assertIn("vbpl.vn",meta_dong.get("legal_source",""))

    def test_progress_only_counts_editing_not_wordpress(self):
        progress=json.loads((ROOT/"editorial"/"seo-51-phuong"/"progress.json").read_text(encoding="utf-8"))
        self.assertEqual(progress["target_articles"],51)
        # Batch 02 must remain intact as the 51-ward campaign advances.
        # Do not freeze the *total* at 6, or the next batch's PR will fail.
        self.assertGreaterEqual(progress["completed_editorial_drafts"],6)
        self.assertEqual(progress["published_new_articles"],0)
        self.assertEqual(progress["next_review_batch"],
                         progress["completed_editorial_drafts"]//3+1)
        self.assertEqual(len(progress["completed"]),
                         progress["completed_editorial_drafts"])
        self.assertEqual(len({entry["ward"] for entry in progress["completed"]}),
                         progress["completed_editorial_drafts"])
        self.assertEqual([e["ward"] for e in progress["completed"][3:6]],
                         [ward for ward,_,_ in WARDS])
        policy=json.loads((ROOT/"config"/"production-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["publisher_pilot"]["max_posts"],3)


if __name__=="__main__":
    unittest.main()
