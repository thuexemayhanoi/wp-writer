"""G3 relaxed references: old or changed snippets do not block, unsafe URLs do."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import qa
from common import load


class AdvisoryPolicyTests(unittest.TestCase):
    def test_owner_76_point_threshold(self):
        rules = load("config/qa-rules.json")
        self.assertEqual((rules["seo_min"], rules["quality_min"]), (76, 76))
        self.assertEqual(rules["source_policy"], "reference_advisory")
        self.assertFalse(rules["source_live_probe_enabled"])

    def test_aged_source_is_logged_not_blocked(self):
        source = {"url": "https://bode.hanoi.gov.vn/old-page", "checked_at": "2020-01-01",
                  "supports": "nguồn tham khảo", "evidence_text": "trích đoạn cũ", "source_sha256": "a" * 64}
        with patch("qa.read_source", side_effect=AssertionError("no live check")):
            errors, evidence = qa.verify_sources([source], live=False, advisory=True)
        self.assertEqual(errors, [])
        self.assertFalse(evidence[0]["live_checked"])
        self.assertIn("SOURCE_DATE_RECHECK_DUE", evidence[0]["warnings"])
        self.assertIn("SOURCE_NOT_PROBED_AT_PUBLISH", evidence[0]["warnings"])

    def test_changed_excerpt_is_warned_in_optional_live_audit(self):
        source = {"url": "https://xaydungchinhsach.chinhphu.vn/law", "checked_at": date.today().isoformat(),
                  "supports": "luật", "evidence_text": "văn bản cũ", "source_sha256": "a" * 64}
        with patch("qa.read_source", return_value=("<p>Văn bản pháp luật mới</p>", 1)):
            errors, evidence = qa.verify_sources([source], live=True, legal=True, advisory=True)
        self.assertEqual(errors, [])
        self.assertIn("SOURCE_EXCERPT_CHANGED_REVIEW_LATER", evidence[0]["warnings"])
        self.assertTrue(evidence[0]["live_checked"])

    def test_timeout_has_no_fake_live_pass(self):
        with patch("qa.read_source", side_effect=TimeoutError("network")):
            errors, evidence = qa.verify_sources([{"url":"https://bode.hanoi.gov.vn/a"}],live=True,advisory=True)
        self.assertEqual(errors, [])
        self.assertFalse(evidence[0]["live_checked"])
        self.assertTrue(any("SOURCE_NOT_REACHABLE" in x for x in evidence[0]["warnings"]))

    def test_unsafe_source_url_still_requires_review(self):
        errors, evidence = qa.verify_sources([{"url":"http://127.0.0.1/secret"}],advisory=True)
        self.assertEqual(errors, ["Source URL is not safe public HTTPS"])
        self.assertEqual(evidence, [])

    def test_strict_optional_audit_is_unchanged(self):
        source = {"url":"https://bode.hanoi.gov.vn/a", "checked_at":"2020-01-01",
                  "supports":"nguồn", "evidence_text":"trích đoạn có thật", "source_sha256":"a"*64}
        errors, _ = qa.verify_sources([source],advisory=False)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
