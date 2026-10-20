"""Claude repair checkpoints: 10 content revisions, lease isolation and nonpublishing branches."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common
import writer_repair as repair


def qa(sha, status="FAIL", reason="SEO_SCORE_BELOW_MIN:70/76", seo=70):
    return {
        "status": status, "source_sha256": sha, "seo_score": seo,
        "quality_score": 88, "errors": ([] if status == "PASS" else [reason]),
        "review": [], "gates": ({"2": {"errors": [reason], "review": []}}
                               if status != "PASS" else {}),
    }


def advance(prev, sha, status="FAIL", session="claude_A", slot="W1",
            topic="NT-000101", note="Improved title, opening and source evidence"):
    return repair.advance(
        prev, session=session, slot=slot, topic_id=topic, sha=sha,
        qa=qa(sha, status=status, seo=90 if status == "PASS" else 70),
        note=note, timestamp="2026-10-18T00:00:00Z",
    )


class CheckpointTests(unittest.TestCase):
    def test_first_failed_draft_is_baseline_zero(self):
        x = advance(None, "hash0")
        self.assertEqual(x["repair_attempts"], 0)
        self.assertEqual(x["next_action"], "CLAUDE_FIX_REMAINING_ERRORS")
        self.assertEqual(x["qa_status"], "FAIL")

    def test_real_revision_increments_and_preserves_error_history(self):
        first = advance(None, "hash0")
        next_one = advance(first, "hash1")
        self.assertEqual(next_one["repair_attempts"], 1)
        self.assertEqual(next_one["history"][0]["source_sha256"], "hash0")
        self.assertEqual(next_one["history"][1]["source_sha256"], "hash1")
        self.assertIn("SEO_SCORE_BELOW_MIN", next_one["remaining_errors"][0])

    def test_same_sha_recheck_does_not_waste_repair_attempt(self):
        x = advance(None, "hash0")
        y = advance(x, "hash0")
        self.assertEqual(y["repair_attempts"], 0)
        self.assertEqual(len(y["history"]), 1)

    def test_ten_content_revisions_max_and_eleventh_rejected(self):
        x = advance(None, "hash0")
        for i in range(1, 11):
            x = advance(x, "hash" + str(i))
        self.assertEqual(x["repair_attempts"], 10)
        self.assertEqual(x["next_action"], "HOLD_REPAIR_LIMIT")
        with self.assertRaisesRegex(ValueError, "exhausted"):
            advance(x, "hash11")

    def test_resume_after_fifth_keeps_same_session_counter(self):
        x = advance(None, "hash0")
        for i in range(1, 6):
            x = advance(x, "hash" + str(i))
        restored = json.loads(json.dumps(x))
        y = advance(restored, "hash6")
        self.assertEqual(y["repair_attempts"], 6)
        self.assertEqual(y["session_id"], "claude_A")
        self.assertEqual(len(y["history"]), 7)

    def test_pass_after_repairs_ready_for_trusted_writer_submission(self):
        x = advance(advance(None, "a"), "b", status="PASS")
        self.assertEqual(x["qa_status"], "PASS")
        self.assertEqual(x["next_action"], "SUBMIT_BY_WRITER_SESSION")
        self.assertEqual(x["repair_attempts"], 1)
        with self.assertRaisesRegex(ValueError, "already QA-PASS"):
            advance(x, "c")

    def test_ownership_and_topic_guard(self):
        x = advance(None, "a")
        for overrides in (
            dict(session="claude_B"), dict(slot="W2"), dict(topic="NT-000102")
        ):
            with self.assertRaisesRegex(ValueError, "ownership"):
                advance(x, "b", **overrides)
        with self.assertRaises(ValueError):
            repair.paths("../other", "NT-000101")

    def test_unverified_duplicate_never_fakes_pass(self):
        x = repair.advance(
            None, session="claude_A", slot="W1", topic_id="NT-000101",
            sha="a", qa={
                "status": "REVIEW", "source_sha256": "a", "seo_score": 99,
                "quality_score": 99, "gates": {
                    "4": {"errors": ["Near duplicate existing:12"], "review": []}
                },
            }, note="", timestamp="now",
        )
        self.assertNotEqual(x["qa_status"], "PASS")
        self.assertEqual(x["next_action"], "HOLD_FOR_REVIEW")

    def test_two_articles_have_distinct_checkpoint_paths(self):
        a = repair.paths("claude_A", "NT-000101")
        b = repair.paths("claude_B", "NT-000102")
        self.assertNotEqual(a[0], b[0])
        self.assertNotEqual(a[1], b[1])
        self.assertNotEqual(a[2], b[2])

    def test_owner_qa_rules_are_consistent(self):
        rules = common.load("config/qa-rules.json")
        self.assertEqual(rules["seo_min"], 76)
        self.assertEqual(rules["quality_min"], 76)


class GitBranchPersistenceTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, text=True,
                              capture_output=True, check=True).stdout.strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        subprocess.run(["git", "init", "--bare", str(home / "remote.git")],
                       capture_output=True, check=True)
        self.root = home / "writer"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "QA")
        self.git("config", "user.email", "qa@example.invalid")
        self.git("remote", "add", "origin", str(home / "remote.git"))
        (self.root / "README.md").write_text("base\n")
        self.git("add", "README.md")
        self.git("commit", "-m", "base")
        self.git("push", "-u", "origin", "main")
        self.patch_root = patch.object(repair, "ROOT", self.root)
        self.patch_common_root = patch.object(common, "ROOT", self.root)
        self.patch_root.start()
        self.patch_common_root.start()

    def tearDown(self):
        self.patch_common_root.stop()
        self.patch_root.stop()
        self.temp.cleanup()

    def test_two_claudes_commit_distinct_branches_and_no_main_changes(self):
        for session, slot, ident in (("claude_A", "W1", "NT-000101"),
                                      ("claude_B", "W2", "NT-000102")):
            ref, check_path, draft_path = repair.paths(session, ident)
            record = advance(None, ident + "_sha", session=session, slot=slot, topic=ident)
            draft = "owned sample draft " + ident
            record["source_sha256"] = common.digest(draft)
            record["history"][0]["source_sha256"] = record["source_sha256"]
            repair.persist(ref, check_path, draft_path, record, draft, None)
            self.assertNotEqual(self.git("ls-remote", "--heads", "origin",
                                         "refs/heads/" + ref), "")
            _, stored, source = repair.remote_repair(ref, check_path, draft_path)
            self.assertEqual(source, draft)
            self.assertEqual(stored["topic_id"], ident)
        self.assertEqual(self.git("ls-tree", "-r", "--name-only", "origin/main"),
                         "README.md")


if __name__ == "__main__":
    unittest.main()
