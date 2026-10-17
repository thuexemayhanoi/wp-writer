"""Real local git fixtures: audit checkpoint CAS must not overwrite Writer."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import common
import git_state
import save_audit


class AuditCASRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.remote = base / "remote.git"
        self.owner = base / "owner"
        self.writer = base / "writer"
        self.cmd("git", "init", "--bare", "--initial-branch=main", str(self.remote))
        self.cmd("git", "clone", str(self.remote), str(self.owner))
        for checkout in (self.owner,):
            self.cmd("git", "config", "user.name", "Audit Tester", cwd=checkout)
            self.cmd("git", "config", "user.email", "audit@example.invalid", cwd=checkout)
        for rel in save_audit.AUDIT_PATHS:
            target = self.owner / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{"snapshot":"old"}\n')
        self.cmd("git", "add", ".", cwd=self.owner)
        self.cmd("git", "commit", "-m", "seed", cwd=self.owner)
        self.cmd("git", "push", "origin", "main", cwd=self.owner)
        self.cmd("git", "clone", str(self.remote), str(self.writer))
        self.cmd("git", "config", "user.name", "Writer Tester", cwd=self.writer)
        self.cmd("git", "config", "user.email", "writer@example.invalid", cwd=self.writer)

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, *args, **kwargs):
        return subprocess.check_output(args, text=True,
                                       stderr=subprocess.DEVNULL, **kwargs).strip()

    def test_audit_cas_preserves_simultaneous_writer_post(self):
        target = self.owner / save_audit.AUDIT_PATHS[0]
        target.write_text('{"snapshot":"new"}\n')
        post = self.writer / "posts" / "drafts" / "NT-999999.md"
        post.parent.mkdir(parents=True)
        post.write_text("A fake Writer article for git-only testing.\n")
        self.cmd("git", "add", ".", cwd=self.writer)
        self.cmd("git", "commit", "-m", "writer post", cwd=self.writer)
        self.cmd("git", "push", "origin", "main", cwd=self.writer)
        with (patch.object(common, "ROOT", self.owner),
              patch.object(git_state, "ROOT", self.owner),
              patch.object(save_audit, "ROOT", self.owner)):
            save_audit.run()
        self.assertIn("new", self.cmd("git", "show",
            "origin/main:" + save_audit.AUDIT_PATHS[0], cwd=self.owner))
        self.assertIn("fake Writer", self.cmd("git", "show",
            "origin/main:posts/drafts/NT-999999.md", cwd=self.owner))

    def test_conflicting_audit_update_is_rejected(self):
        rel = save_audit.AUDIT_PATHS[0]
        (self.owner / rel).write_text('{"snapshot":"owner-update"}\n')
        (self.writer / rel).write_text('{"snapshot":"other-update"}\n')
        self.cmd("git", "add", ".", cwd=self.writer)
        self.cmd("git", "commit", "-m", "other audit snapshot", cwd=self.writer)
        self.cmd("git", "push", "origin", "main", cwd=self.writer)
        with (patch.object(common, "ROOT", self.owner),
              patch.object(git_state, "ROOT", self.owner),
              patch.object(save_audit, "ROOT", self.owner)):
            with self.assertRaisesRegex(RuntimeError, "State conflict"):
                save_audit.run()
        self.assertIn("other-update", self.cmd("git", "show",
            "origin/main:" + rel, cwd=self.owner))

    def test_audit_workflow_has_only_cas_writer(self):
        source = (ROOT / ".github/workflows/factory-audit.yml").read_text()
        self.assertIn("environment: wordpress-production", source)
        self.assertIn("python scripts/save_audit.py", source)
        self.assertNotIn("git push origin HEAD:main", source)
        self.assertNotIn("git pull --rebase origin main", source)


if __name__ == "__main__":
    unittest.main()
