"""GitHub-only status projection must never require or fake WordPress G7."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from common import digest
from writer_handoff import result_for, report

TOPIC="NT-000201"
ARTICLE="""---
topic_id: NT-000201
writer_session: s-test-claude
writer_slot: W2
---
This is a test-only draft.
"""
TOPICS=[{"topic_id":TOPIC,"topic_qa_status":"PLANNED"}]
RULES={"seo_min":76,"quality_min":76}

def details(root):
    path=root/(TOPIC+".md")
    path.write_text(ARTICLE,encoding="utf-8")
    sha=digest(path.read_bytes())
    claims={"submissions":{TOPIC:{"sha256":sha,"session":"s-test-claude","slot":"W2"}}}
    qa={TOPIC:{"topic_id":TOPIC,"status":"PASS","seo_score":79,
               "quality_score":78,"errors":[],"review":[],"source_sha256":sha}}
    return path,sha,claims,qa

class GitHubOnlyHandoffTests(unittest.TestCase):
    def test_unpublished_qa_pass_does_not_require_live_wordpress(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            _,sha,claims,qa=details(root)
            with patch("writer_handoff.read_article",return_value=({"topic_id":TOPIC,"writer_session":"s-test-claude","writer_slot":"W2"},"body",sha)):
                out=result_for(TOPIC,registry=TOPICS,claims=claims,ledger={},qa=qa,rules=RULES,drafts_dir=root)
            self.assertEqual(out["status"],"WRITER_QA_PASS_AWAITING_PUBLISHER")
            self.assertTrue(out["writer_done"])
            self.assertFalse(out["wordpress_verified"])

    def test_stale_qa_or_unsubmitted_never_is_ready(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            _,sha,claims,qa=details(root)
            with patch("writer_handoff.read_article",return_value=({"topic_id":TOPIC,"writer_session":"s-test-claude","writer_slot":"W2"},"body",sha)):
                missing=result_for(TOPIC,registry=TOPICS,claims={},ledger={},qa=qa,rules=RULES,drafts_dir=root)
                outdated=result_for(TOPIC,registry=TOPICS,claims=claims,ledger={},qa={TOPIC:{**qa[TOPIC],"source_sha256":"old"}},rules=RULES,drafts_dir=root)
            self.assertEqual(missing["status"],"WRITER_NOT_SUBMITTED")
            self.assertEqual(outdated["status"],"GITHUB_QA_PENDING")
            self.assertFalse(outdated["writer_done"])

    def test_repair_for_low_score_and_receipt_collision(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            _,sha,claims,qa=details(root)
            with patch("writer_handoff.read_article",return_value=({"topic_id":TOPIC,"writer_session":"s-test-claude","writer_slot":"W2"},"body",sha)):
                low=result_for(TOPIC,registry=TOPICS,claims=claims,ledger={},qa={TOPIC:{**qa[TOPIC],"seo_score":75}},rules=RULES,drafts_dir=root)
                bad=result_for(TOPIC,registry=TOPICS,claims={"submissions":{TOPIC:{"sha256":"wrong"}}},ledger={},qa=qa,rules=RULES,drafts_dir=root)
            self.assertEqual(low["status"],"WRITER_QA_REPAIR")
            self.assertEqual(bad["status"],"WRITER_RECEIPT_MISMATCH")

    def test_publisher_g7_only_with_authentic_ledger(self):
        for phase, g7, expected in (
                ("VERIFIED",{"status":"PASS"},"WORDPRESS_G7_VERIFIED"),
                ("VERIFIED",{"status":"FAIL"},"PUBLISHER_G7_UNCONFIRMED"),
                ("NEEDS_RECONCILE",None,"PUBLISHER_RECONCILE_PENDING")):
            ledger={"posts":{TOPIC:{"phase":phase,"wp_id":4151,
                    "url":"https://thuexemaynguyentu.com/example/","g7":g7}}}
            output=result_for(TOPIC,registry=TOPICS,claims={},ledger=ledger,qa={},rules=RULES,drafts_dir=ROOT/"posts/drafts")
            self.assertEqual(output["status"],expected)
            self.assertEqual(output["wordpress_verified"],expected=="WORDPRESS_G7_VERIFIED")

    def test_no_wordpress_access_in_report(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            for folder in ("data/state","data/qa","config","posts/drafts"):
                (root/folder).mkdir(parents=True,exist_ok=True)
            (root/"data/topics.jsonl").write_text(json.dumps(TOPICS[0])+"\n")
            (root/"data/state/writer-claims.json").write_text(json.dumps({"leases":{"W2":{"session":"s-test-claude","topic_ids":[TOPIC]}},"submissions":{}}))
            (root/"data/state/publication-ledger.json").write_text('{"posts":{}}')
            (root/"config/qa-rules.json").write_text(json.dumps(RULES))
            out=report(root=root,session="s-test-claude")
            self.assertFalse(out["requires_wordpress_credentials"])
            self.assertEqual(out["results"][0]["status"],"NOT_AUTHORED")
            self.assertEqual(out["count"],1)
            with self.assertRaisesRegex(ValueError,"Supply"):
                report(root=root)

if __name__=="__main__":
    unittest.main()
