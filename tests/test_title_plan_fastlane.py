"""Regression coverage for the read-only 1482-title research fast lane."""
import datetime as dt
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from title_plan_fastlane import proposed_id, reusable_sources, build_fastlane


def plan(i=10, title="Đi xe máy ban đêm: chọn vị trí quan sát giao lộ an toàn"):
    return {"plan_id": "TP-%04d" % i, "title": title, "status": "PLANNED",
            "category_id": 161, "taxonomy_key": "road-safety"}


def admitted(status="PLANNED", date=None):
    return {"topic_id": "NT-000123", "topic_qa_status": status,
            "taxonomy_key": "road-safety",
            "title": "Kỹ năng quan sát khi đi xe máy ban đêm",
            "research": {"external_sources": [{
                "url": "https://mps.gov.vn/real-document",
                "checked_at": (date or dt.date.today()).isoformat(),
                "supports": "Tài liệu nêu nguyên tắc quan sát giao thông an toàn",
                "evidence_text": "Trích đoạn đã được người nghiên cứu đọc và lưu trong hồ sơ gốc.",
                "source_sha256": "a" * 64}]}}


class FastlaneTests(unittest.TestCase):
    def test_stable_plan_id_is_never_live_admission(self):
        self.assertEqual(proposed_id("TP-0001"), "NT-090001")
        self.assertEqual(proposed_id("TP-1482"), "NT-091482")
        with self.assertRaises(ValueError):
            proposed_id("TP-9999")

    def test_reuse_admitted_relevant_dated_source_only(self):
        today = dt.date(2026, 10, 21)
        source = admitted(date=today)
        reused = reusable_sources(plan(), [source], today=today)
        self.assertEqual(len(reused), 1)
        self.assertEqual(reused[0]["checked_at"], "2026-10-21")
        self.assertEqual(reused[0]["reused_from_topic_id"], "NT-000123")
        self.assertEqual(reusable_sources(plan(), [admitted("RESEARCH")], today=today), [])
        self.assertEqual(reusable_sources(plan(), [admitted("REJECTED")], today=today), [])
        self.assertEqual(reusable_sources(plan(title="Bảo dưỡng pin xe điện"), [source], today=today), [])
        self.assertEqual(reusable_sources(plan(), [admitted(date=today-dt.timedelta(days=366))], today=today), [])
        damaged = admitted(date=today)
        damaged["research"]["external_sources"][0]["source_sha256"] = "invalid"
        self.assertEqual(reusable_sources(plan(), [damaged], today=today), [])

    def test_excludes_assigned_plan_and_wp_duplicate(self):
        rows = [plan(10),
                plan(11, title="Kỹ năng đi xe máy dưới mưa khi đường ngập"),
                plan(12, title="Thực hành quan sát giao thông tại nút giao đường vòng xuyến")]
        registered = {**admitted(), "topic_id": "NT-090010", "title_plan_id": "TP-0010"}
        wp = [{"id": 4344, "title": rows[1]["title"], "status": "publish",
               "slug": "existing", "url": "https://thuexemaynguyentu.com/existing/"}]
        result = build_fastlane(rows, [registered], wp, limit=2)
        self.assertEqual([r["plan_id"] for r in result["ready_for_research"]], ["TP-0012"])
        self.assertEqual(result["held"][0]["reason"], "WORDPRESS_IDENTITY_COLLISION")
        self.assertFalse(result["ready_for_research"][0]["topic_id_is_reserved"])
        self.assertFalse(result["publication_authorized"])

    def test_occupied_proposed_id_is_held(self):
        result = build_fastlane([plan()], [{**admitted(), "topic_id": "NT-090010",
                    "title_plan_id": "TP-0999"}], [], limit=1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["held"][0]["reason"], "NT_ID_ALREADY_OCCUPIED")

    def test_reject_large_requests(self):
        with self.assertRaises(ValueError):
            build_fastlane([], [], [], limit=11)


if __name__ == "__main__":
    unittest.main()
