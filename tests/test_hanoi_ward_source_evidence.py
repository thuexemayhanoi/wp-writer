"""Regression guard for the three researched Hanoi ward source excerpts.

This checks metadata completeness and consistency only; the Publisher must
still independently fetch official sources and apply the live G3 gate.
"""
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from qa import read_article, source_excerpt_matches


class HanoiWardEvidenceIntegrityTests(unittest.TestCase):
    def test_three_owned_ward_drafts_cite_official_sources_with_complete_excerpt(self):
        for topic_id, ward_host in (
            ("NT-001101", "bode.hanoi.gov.vn"),
            ("NT-001102", "cuanam.hanoi.gov.vn"),
            ("NT-001103", "hoankiem.hanoi.gov.vn"),
        ):
            with self.subTest(topic_id=topic_id):
                path = ROOT / "posts" / "drafts" / (topic_id + ".md")
                if not path.is_file():
                    self.skipTest("Writer has not submitted " + topic_id)
                metadata, body, _ = read_article(path)
                self.assertEqual(metadata["taxonomy_key"], "hanoi-ward-rentals")
                self.assertGreater(len(body), 5000)
                sources = metadata.get("sources", [])
                official_ward = next(
                    source for source in sources
                    if urlsplit(source["url"]).hostname == ward_host
                )
                self.assertGreater(len(official_ward["evidence_text"].split()), 8)
                self.assertEqual(len(official_ward["source_sha256"]), 64)
                law = next(
                    source for source in sources
                    if urlsplit(source["url"]).hostname == "xaydungchinhsach.chinhphu.vn"
                )
                self.assertIn(
                    "Người lái xe tham gia giao thông đường bộ phải đủ tuổi, sức khỏe",
                    law["evidence_text"],
                )
                self.assertGreater(len(law["evidence_text"].split()), 10)
                self.assertEqual(len(law["source_sha256"]), 64)


class VerifiedSourceExcerptMatchingTests(unittest.TestCase):
    def test_complete_citation_still_requires_exact_prose(self):
        actual = (
            "Điều 56. Điều kiện của người điều khiển phương tiện tham gia giao thông đường bộ "
            "1. Người lái xe tham gia giao thông đường bộ phải đủ tuổi, sức khỏe theo quy định "
            "của pháp luật; có giấy phép lái xe đang còn điểm, còn hiệu lực phù hợp với loại xe "
            "đang điều khiển do cơ quan có thẩm quyền cấp."
        )
        self.assertTrue(source_excerpt_matches(actual, actual))

    def test_clipped_final_word_is_accepted_only_with_full_prior_context(self):
        actual = (
            "Điều 56. Điều kiện của người điều khiển phương tiện tham gia giao thông đường bộ "
            "1. Người lái xe tham gia giao thông đường bộ phải đủ tuổi, sức khỏe theo quy định "
            "của pháp luật; có giấy phép lái xe đang còn điểm, còn hiệu lực phù hợp với loại xe "
            "đang điều khiển do cơ quan có thẩm quyền cấp."
        )
        clipped = actual.split("loại xe")[0] + "lo"
        self.assertGreaterEqual(len(clipped), 120)
        self.assertTrue(source_excerpt_matches(clipped, actual))
        self.assertFalse(source_excerpt_matches(clipped, actual.replace("đủ tuổi", "không đủ tuổi")))
        self.assertFalse(source_excerpt_matches(clipped[:-2] + "xa", actual))
        self.assertFalse(source_excerpt_matches("Người lái xe tham gia giao thông đường bộ phải đủ tu", actual))


if __name__ == "__main__":
    unittest.main()
