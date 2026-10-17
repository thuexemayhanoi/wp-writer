"""Protected-main migration scanner: no GitHub or WordPress side effects."""
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from protected_main_readiness import inspect


def create_fixture(root, cas, audit="name: safe audit", writer="from git_state import RemoteState"):
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".github/workflows").mkdir(parents=True, exist_ok=True)
    (root / "scripts/git_state.py").write_text(cas)
    (root / ".github/workflows/factory-audit.yml").write_text(audit)
    (root / "scripts/publisher.py").write_text(writer)


class ProtectedMainMigrationTests(unittest.TestCase):
    def test_real_repository_currently_blocked_and_reports_exact_paths(self):
        actual = inspect(ROOT)
        self.assertEqual(actual["status"], "BLOCKED")
        codes = {x["code"] for x in actual["direct_main_write_blockers"]}
        self.assertIn("DIRECT_MAIN_CAS_INCOMPATIBLE_WITH_REQUIRED_PR", codes)
        self.assertIn("AUDIT_WORKFLOW_DIRECT_MAIN_PUSH", codes)
        self.assertTrue(actual["writer_branch_lane_present"])
        self.assertEqual(actual["wordpress_writes"], 0)
        self.assertFalse(actual["production_flags_modified"])

    def test_state_push_to_main_is_rejected_even_if_actions_tests_green(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            create_fixture(root,
                "subprocess.run(['git','push','origin','commit:refs/heads/main'])",
                audit="git push origin HEAD:main")
            result = inspect(root)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(len(result["direct_main_write_blockers"]), 2)

    def test_missing_state_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = inspect(Path(folder))
            self.assertEqual(result["status"], "BLOCKED")
            codes = [x["code"] for x in result["direct_main_write_blockers"]]
            self.assertIn("CAS_SOURCE_UNAVAILABLE", codes)
            self.assertIn("AUDIT_WORKFLOW_UNAVAILABLE", codes)
            self.assertIn("STATE_WRITER_VERIFICATION_UNAVAILABLE", codes)

    def test_new_transport_needs_no_direct_main_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            create_fixture(root,
                "def persist(data):\n  return 'read-only future transport'\n",
                audit="name: read-only audit")
            result = inspect(root)
            self.assertEqual(result["status"], "READY_FOR_REVIEW")
            self.assertTrue(result["main_protection_migration_ready"])
            self.assertEqual(result["existing_state_writers"], ["scripts/publisher.py"])
            self.assertEqual(result["wordpress_writes"], 0)
            self.assertNotIn("PASS", result["status"])

    def test_no_fatal_stdout_secret_or_fake_production_activation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            create_fixture(root,
                "subprocess.run(['git','push','origin','head:refs/heads/main'])")
            result = inspect(root)
            self.assertFalse(result["production_flags_modified"])
            self.assertEqual(result["github_ruleset_mutations"], 0)
            self.assertEqual(result["wordpress_writes"], 0)


if __name__ == "__main__":
    unittest.main()
