"""Regression tests: Writer branch input is data, never executable code."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import writer_branch_intake as intake_module
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


CONFLICT = RuntimeError("State conflict; reconcile before another WordPress write: data/state/writer-claims.json")


class WriterBranchRetryTests(unittest.TestCase):
    """A writer committing to main while the trusted job checks an article must not turn the run red."""

    def run_main(self, outcomes, apply=True):
        self.calls, self.refreshed = [], []

        def fake_ingest(branch, sha, dry_run=True):
            self.calls.append(dry_run)
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        argv = ["writer_branch_intake.py", "--branch", "writer/s-good", "--sha", "a" * 40] + (["--apply"] if apply else [])
        out = io.StringIO()
        with patch.object(intake_module, "ingest", fake_ingest), \
                patch.object(intake_module, "refresh_trusted_main", lambda: self.refreshed.append(1)), \
                patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            intake_module.main()
        return out.getvalue()

    def test_a_race_with_another_commit_is_redone_on_the_newest_main(self):
        printed = self.run_main([CONFLICT, CONFLICT, {"status": "ADMITTED", "count": 1}])
        self.assertEqual((len(self.calls), len(self.refreshed)), (3, 2))
        self.assertIn("ADMITTED", printed)
        self.assertEqual(printed.count("WRITER_BRANCH_INTAKE_RETRY"), 2)

    def test_a_clean_run_never_refreshes(self):
        self.run_main([{"status": "ADMITTED", "count": 1}])
        self.assertEqual((len(self.calls), len(self.refreshed)), (1, 0))

    def test_only_a_state_conflict_is_retried(self):
        with self.assertRaisesRegex(RuntimeError, "source unavailable"):
            self.run_main([RuntimeError("Writer Git source unavailable: fetch")])
        self.assertEqual((len(self.calls), len(self.refreshed)), (1, 0))
        with self.assertRaisesRegex(ValueError, "WRITER_QA_BLOCKED"):
            self.run_main([ValueError("WRITER_QA_BLOCKED NT-000111 REVIEW SEO=70")])
        self.assertEqual((len(self.calls), len(self.refreshed)), (1, 0))

    def test_a_conflict_that_never_clears_stops_after_the_attempt_limit(self):
        with self.assertRaisesRegex(RuntimeError, "State conflict"):
            self.run_main([CONFLICT] * intake_module.ATTEMPTS)
        self.assertEqual((len(self.calls), len(self.refreshed)), (intake_module.ATTEMPTS, intake_module.ATTEMPTS - 1))

    def test_the_read_only_check_is_never_retried(self):
        with self.assertRaisesRegex(RuntimeError, "State conflict"):
            self.run_main([CONFLICT], apply=False)
        self.assertEqual((len(self.calls), len(self.refreshed)), (1, 0))

    def test_the_checkout_is_refreshed_only_inside_trusted_github_actions(self):
        with patch.object(intake_module, "git_read") as git, patch.dict("os.environ", {"GITHUB_ACTIONS": "false"}):
            with self.assertRaisesRegex(ValueError, "Trusted main"):
                intake_module.refresh_trusted_main()
        git.assert_not_called()
        with patch.object(intake_module, "git_read") as git, patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
            intake_module.refresh_trusted_main()
        self.assertEqual([call.args[0] for call in git.call_args_list], ["fetch", "reset", "clean"])
        self.assertIn("origin/main", git.call_args_list[1].args)


if __name__ == "__main__":
    unittest.main()
