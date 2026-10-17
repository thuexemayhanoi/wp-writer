"""Regression tests: Writer branch input is data, never executable code."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from writer_branch_intake import check_changed_paths, verify_source, ingest


class WriterBranchSecurityTests(unittest.TestCase):
    def test_only_markdown_articles_are_allowed(self):
        self.assertEqual(check_changed_paths([
            "A\tposts/drafts/NT-000111.md",
            "M\tposts/drafts/NT-000112.md"
        ]), ["posts/drafts/NT-000111.md", "posts/drafts/NT-000112.md"])

    def test_reject_privileged_or_unrelated_paths(self):
        forbidden = [
            ".github/workflows/wordpress-publisher.yml",
            "scripts/publisher.py", "config/production-policy.json",
            "tests/test_factory.py", "requirements.txt",
            "data/taxonomy.json", "data/writer-requests/s-test.json",
            "posts/drafts/../../scripts/publisher.py",
            "posts/drafts/NT-000111.md/../../extra",
            "posts/drafts/NT-000111.md.bak"
        ]
        for path in forbidden:
            with self.subTest(path=path), self.assertRaises(ValueError):
                check_changed_paths(["A\t" + path])

    def test_reject_empty_delete_rename_duplicate_and_oversized_batches(self):
        for rows in (
            [],
            ["D\tposts/drafts/NT-000111.md"],
            ["R100\tposts/drafts/NT-000110.md\tposts/drafts/NT-000111.md"],
            ["A\tposts/drafts/NT-000111.md"] * 2,
            ["A\tposts/drafts/NT-%06d.md" % i for i in range(11)]
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                check_changed_paths(rows)

    def test_untrusted_branch_and_commit_cannot_pass_ref_verifier(self):
        sha = "a" * 40
        for name in ("main", "writer/../evil", "writer//evil", "research/s-test", "writer/a", "writer/a b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_source(name, sha)
        with self.assertRaises(ValueError):
            verify_source("writer/s-good", "bad-sha")

    def test_moved_branch_sha_refuses_after_successful_qa(self):
        with patch("writer_branch_intake.git_read", return_value="b" * 40) as git:
            with self.assertRaisesRegex(ValueError, "moved after QA"):
                verify_source("writer/s-good", "a" * 40)
        self.assertTrue(git.called)

    def test_apply_requires_trusted_main_action(self):
        fake = [{"status":"QA_PASS", "path":"posts/drafts/NT-000111.md", "topic_id":"NT-000111"}]
        with patch("writer_branch_intake.prepare", return_value=fake):
            with patch.dict("os.environ", {"GITHUB_ACTIONS":"false",
                                          "GITHUB_REPOSITORY":"thuexemayhanoi/wp-writer",
                                          "GITHUB_REF":"refs/heads/main"}):
                with self.assertRaisesRegex(ValueError, "Trusted main"):
                    ingest("writer/s-good", "a"*40, dry_run=False)

    def test_workflows_never_execute_untrusted_branch_code(self):
        qa = yaml.safe_load((ROOT / ".github/workflows/writer-branch-qa.yml").read_text())
        action = yaml.safe_load((ROOT / ".github/workflows/writer-branch-intake.yml").read_text())
        jqa = qa["jobs"]["trusted-writer-check"]
        jintake = action["jobs"]["import"]
        self.assertEqual(qa["permissions"]["contents"], "read")
        self.assertEqual(action["permissions"]["contents"], "write")
        self.assertNotIn("environment", jqa)
        self.assertNotIn("environment", jintake)
        for job in (jqa, jintake):
            checkout = next(step for step in job["steps"] if step.get("name", "").startswith("Checkout"))
            self.assertEqual(checkout["with"]["ref"], "main")
            self.assertNotIn("secrets.WP_", str(job))
        self.assertIn("--apply", str(jintake["steps"]))
        self.assertIn("head_repository.full_name", jintake["if"])


if __name__ == "__main__":
    unittest.main()
