"""Isolated factory-state CAS exercises real local bare Git repositories.

No GitHub network, WordPress credentials or WP POST. The production adapter
is opt-in: legacy main writer flows remain unchanged until full cutover.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import common
import git_state
from git_state import FactoryStateCAS, _validate_state_paths


class IsolatedStateCASTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bare = self.root / "remote.git"
        self.main = self.root / "main-checkout"
        self.other = self.root / "other-checkout"
        self.run_git(None, "init", "--bare", "--initial-branch=main", str(self.bare))
        self.run_git(None, "clone", str(self.bare), str(self.main))
        self.run_git(self.main, "config", "user.name", "Factory Tester")
        self.run_git(self.main, "config", "user.email", "factory@example.invalid")
        for name, text in (
            ("data/state/publication-ledger.json", '{"phase":"OLD"}\n'),
            ("data/state/writer-claims.json", '{"leases":{}}\n'),
            ("data/qa/NT-000101.json", '{"status":"PASS"}\n'),
            ("reports/dashboard.json", '{"checked":true}\n'),
            ("scripts/publisher.py", "# trusted main code\n"),
            ("posts/drafts/NT-000101.md", "Writer content\n"),
        ):
            f = self.main / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        self.run_git(self.main, "add", ".")
        self.run_git(self.main, "commit", "-m", "seed")
        self.run_git(self.main, "push", "origin", "main")
        self.run_git(self.main, "push", "origin", "HEAD:refs/heads/factory-state")
        self.run_git(None, "clone", str(self.bare), str(self.other))
        self.run_git(self.other, "config", "user.name", "Other Writer")
        self.run_git(self.other, "config", "user.email", "other@example.invalid")
        self.root_patch = patch.object(common, "ROOT", self.main)
        self.git_patch = patch.object(git_state, "ROOT", self.main)
        self.root_patch.start()
        self.git_patch.start()

    def tearDown(self):
        self.git_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    @staticmethod
    def run_git(directory, *args):
        return subprocess.check_output(
            ["git", *args], cwd=directory, text=True,
            stderr=subprocess.DEVNULL
        ).strip()

    def remote_file(self, branch, path):
        return self.run_git(self.main, "show", "refs/remotes/origin/" +
                            branch + ":" + path)

    def test_isolated_ledger_commit_does_not_touch_main(self):
        store = FactoryStateCAS()
        store.remember(["data/state/publication-ledger.json"])
        (self.main / "data/state/publication-ledger.json").write_text(
            '{"phase":"POST_INTENT"}\n')
        original_main = self.run_git(self.main, "rev-parse", "origin/main")
        result = store.persist(["data/state/publication-ledger.json"])
        self.run_git(self.main, "fetch", "origin", "factory-state")
        self.assertEqual(self.run_git(self.main, "rev-parse", "origin/main"),
                         original_main)
        self.assertIn("POST_INTENT", self.remote_file(
            "factory-state", "data/state/publication-ledger.json"))
        self.assertEqual(self.remote_file("main", "data/state/publication-ledger.json"),
                         '{"phase":"OLD"}')
        self.assertEqual(self.remote_file("factory-state", "scripts/publisher.py"),
                         "# trusted main code")
        self.assertEqual(self.run_git(self.main, "rev-parse", "origin/factory-state"),
                         result)

    def test_cas_refuses_stale_conflicting_intent(self):
        first, second = FactoryStateCAS(), FactoryStateCAS()
        path = "data/state/publication-ledger.json"
        first.remember([path])
        second.remember([path])
        (self.main / path).write_text('{"phase":"POST_INTENT","writer":1}\n')
        first.persist([path])
        (self.main / path).write_text('{"phase":"POST_INTENT","writer":2}\n')
        with self.assertRaisesRegex(RuntimeError, "CAS CONFLICT"):
            second.persist([path])
        self.run_git(self.main, "fetch", "origin", "factory-state")
        self.assertIn('"writer":1', self.remote_file("factory-state", path))

    def test_state_and_writer_posts_can_commit_concurrently_to_separate_refs(self):
        store = FactoryStateCAS()
        path = "data/state/writer-claims.json"
        store.remember([path])
        writer = self.other / "posts/drafts/NT-000102.md"
        writer.write_text("Another Writer's article\n")
        self.run_git(self.other, "add", ".")
        self.run_git(self.other, "commit", "-m", "post by Writer")
        self.run_git(self.other, "push", "origin", "HEAD:refs/heads/main")
        (self.main / path).write_text('{"leases":{"W1":"active"}}\n')
        store.persist([path])
        self.run_git(self.main, "fetch", "origin")
        self.assertIn("active", self.remote_file("factory-state", path))
        self.assertEqual(self.remote_file("main", "posts/drafts/NT-000102.md"),
                         "Another Writer's article")
        self.assertEqual(self.remote_file("factory-state", "posts/drafts/NT-000101.md"),
                         "Writer content")

    def test_cannot_write_code_or_content_on_state_ref(self):
        for path in (
            "scripts/publisher.py", ".github/workflows/wordpress-publisher.yml",
            "posts/drafts/NT-000101.md", "config/production-policy.json",
            "data/taxonomy.json", "data/topics.jsonl",
            "data/state/../config/production-policy.json",
            "reports/.private", "data/qa/NT-abc.json",
            "/data/state/publication-ledger.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _validate_state_paths([path])
        with self.assertRaises(ValueError):
            _validate_state_paths(["data/state/writer-claims.json"] * 2)
        with self.assertRaises(ValueError):
            _validate_state_paths([])

    def test_read_branch_snapshot_and_require_remember(self):
        store = FactoryStateCAS()
        self.assertIn(b'"phase":"OLD"', store.read_bytes(
            "data/state/publication-ledger.json"))
        with self.assertRaises(FileNotFoundError):
            store.read_bytes("data/state/missing.json")
        with self.assertRaisesRegex(RuntimeError, "remember"):
            store.persist(["data/state/publication-ledger.json"])

    def test_noop_does_not_create_new_commit(self):
        store = FactoryStateCAS()
        before = store.remember(["reports/dashboard.json"])
        result = store.persist(["reports/dashboard.json"])
        self.assertEqual(result, before)


if __name__ == "__main__":
    unittest.main()
