"""Regression: the 10/day owner cap is shared by live posts and fallback drafts.

Production remains disabled; these tests use only synthetic ledger fixtures.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publisher import daily_created_count


class ImmutableDailyCapTests(unittest.TestCase):
    def test_mixed_publish_and_draft_share_daily_budget(self):
        ledger={"posts":{}}
        for i in range(1,8):
            ledger["posts"][f"NT-{i:06}"]={"phase":"VERIFIED","expected_status":"publish","created_at":"2026-10-16T08:00:00+00:00"}
        for i in range(8,11):
            ledger["posts"][f"NT-{i:06}"]={"phase":"VERIFIED","expected_status":"draft","created_at":"2026-10-16T10:00:00+00:00"}
        self.assertEqual(daily_created_count(ledger,"2026-10-16"),10)
        self.assertEqual(daily_created_count(ledger,"2026-10-16",status="publish"),7)
        self.assertEqual(daily_created_count(ledger,"2026-10-16",status="draft"),3)

    def test_reconciliation_must_not_recount_old_post_as_today(self):
        posts={"NT-000015":{"phase":"VERIFIED","expected_status":"publish",
                            "created_at":"2026-10-15T12:00:00+00:00",
                            "verified_at":"2026-10-16T08:10:00+00:00",
                            "updated_at":"2026-10-16T08:11:00+00:00"}}
        self.assertEqual(daily_created_count({"posts":posts},"2026-10-16"),0)
        self.assertEqual(daily_created_count({"posts":posts},"2026-10-15"),1)

    def test_uncertain_post_intent_consumes_capacity(self):
        ledger={"posts":{"NT-000021":{"phase":"NEEDS_RECONCILE",
              "expected_status":"publish","created_at":"2026-10-16T15:00:00+00:00"}}}
        self.assertEqual(daily_created_count(ledger,"2026-10-16"),1)

    def test_smoke_draft_is_not_campaign_post(self):
        ledger={"posts":{"ACCEPTANCE-20261016":{"phase":"VERIFIED",
              "expected_status":"draft","created_at":"2026-10-16T15:00:00+00:00"}}}
        self.assertEqual(daily_created_count(ledger,"2026-10-16"),0)

    def test_legacy_manual_publications_count_from_verified_at(self):
        ledger=json.loads((ROOT/"data/state/publication-ledger.json").read_text())
        self.assertGreaterEqual(daily_created_count(ledger,"2026-10-16"),2)

    def test_bad_day_rejected(self):
        with self.assertRaises(ValueError):
            daily_created_count({"posts":{}},"16-10-2026")


if __name__=="__main__":
    unittest.main()
