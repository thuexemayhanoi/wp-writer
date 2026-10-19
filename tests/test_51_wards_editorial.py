"""Read-only editorial checks for 51 Hà Nội ward content batches.

These are PRE-Research QA checks only. They do not authorize Topic Factory
intake, mint writer receipts, publish WordPress posts, or claim G1-G7 PASS.
"""
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from qa import word_count, counted_text, fingerprint, jaccard


class HanoiWardEditorialTests(unittest.TestCase):
    FILES = {
        "Bồ Đề": "01-bo-de.md",
        "Cửa Nam": "02-cua-nam.md",
        "Hoàn Kiếm": "03-hoan-kiem.md",
    }
    FOLDER = ROOT / "editorial" / "seo-51-phuong" / "batch-01"

    def read(self, ward):
        content = (self.FOLDER / self.FILES[ward]).read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", content, flags=re.S)
        self.assertIsNotNone(match, ward + ": missing editorial metadata")
        meta = yaml.safe_load(match.group(1))
        body = content[match.end():].strip()
        return meta, body

    def test_three_unique_ward_h1_and_metadata(self):
        titles = set()
        slugs = set()
        for ward in self.FILES:
            with self.subTest(ward=ward):
                meta, body = self.read(ward)
                self.assertEqual(meta.get("ward"), ward)
                self.assertEqual(meta.get("batch"), "HN-51-WARDS-01")
                self.assertTrue(str(meta.get("editorial_status", "")).startswith("DRAFT"))
                self.assertIn(ward, meta["h1"])
                self.assertEqual(re.findall(r"^# (.+)$", body, re.M), [meta["h1"]])
                self.assertGreaterEqual(len(re.findall(r"^## .+$", body, re.M)), 6)
                self.assertNotIn(meta["h1"], titles)
                self.assertNotIn(meta["suggested_slug"], slugs)
                self.assertEqual(meta.get("writer_slot"), None)
                self.assertEqual(meta.get("topic_id"), None)
                titles.add(meta["h1"])
                slugs.add(meta["suggested_slug"])

    def test_factory_prose_word_count_and_nap(self):
        for ward in self.FILES:
            with self.subTest(ward=ward):
                _, body = self.read(ward)
                words = word_count(body)
                self.assertGreaterEqual(words, 1600, (ward, words))
                self.assertLessEqual(words, 5000, (ward, words))
                self.assertIn("112 Nguyễn Văn Cừ", body)
                self.assertIn("0942 467 674", body)
                self.assertIn("09:00–21:00", body)
                self.assertGreaterEqual(body.count("https://thuexemaynguyentu.com/"), 2)

    def test_no_near_duplicate_articles(self):
        samples = {ward: fingerprint(counted_text(self.read(ward)[1])) for ward in self.FILES}
        names = list(self.FILES)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ratio = jaccard(samples[names[i]], samples[names[j]])
                self.assertLess(ratio, 0.12, (names[i], names[j], ratio))

    def test_legal_and_business_safeguards(self):
        for ward in self.FILES:
            with self.subTest(ward=ward):
                meta, body = self.read(ward)
                self.assertTrue(meta["official_locality_source"].startswith("https://"))
                self.assertIn("hanoi.gov.vn", meta["official_locality_source"])
                self.assertIn(ward.casefold(), body.casefold())
                self.assertNotIn("giao miễn phí mọi nơi", body.lower())
                self.assertNotIn("chi nhánh của Nguyễn Tú tại", body)
                self.assertNotIn("đã qua QA chính thức", body.lower())


if __name__ == "__main__":
    unittest.main()
