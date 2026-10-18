"""Guard W1–W9 tool compatibility and active runbooks without touching live writers."""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
TOOL = ROOT / "agent-tools" / "build_article.py"
RUNBOOKS = (
    "README.md", "AGENTS.md",
    "docs/ACTIVATION.md", "docs/AI-START-HERE.md",
    "docs/ARTICLE-CONTRACT.md", "docs/RESEARCH-FACTORY-1000.md",
    "docs/WORDPRESS-AUTO-DELIVERY.md", "docs/WRITER-BRANCH-INTAKE.md",
    "docs/WRITER-QUICKSTART.md", "docs/WRITER-AUTO-REPAIR.md",
    "docs/INSTANT-PUBLISHING.md", "docs/RESEARCH-V2-GLOBAL-ADAPTATION.md",
    "docs/WORKFLOW-COMPARISON-WP-AIWRITER.md",
    "docs/agent-playbook/ROLE-WRITER.md",
    "docs/agent-playbook/AGENT-GUIDE.md",
    "agent-tools/README.md", ".github/workflows/wordpress-publisher.yml",
)


class NineWriterCompatibilityTests(unittest.TestCase):
    def test_nine_slots_are_the_canonical_source(self):
        config = json.loads((ROOT / "config/writer-slots.json").read_text(encoding="utf-8"))
        self.assertEqual(config["slots"], [f"W{i}" for i in range(1, 10)])
        from writer_session import SLOTS
        self.assertEqual(SLOTS, tuple(config["slots"]))

    def test_article_builder_cli_accepts_nine_slot_choices(self):
        result = subprocess.run([sys.executable, str(TOOL), "--help"],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("W9", result.stdout)
        self.assertIn("W1", result.stdout)

    def test_article_builder_cannot_silently_claim_w1(self):
        result = subprocess.run([sys.executable, str(TOOL), "NT-999999", "--no-qa"],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--slot is required", result.stderr)

    def test_article_builder_rejects_w10(self):
        result = subprocess.run([sys.executable, str(TOOL), "NT-999999",
                                 "--slot", "W10", "--no-qa"],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_active_runbooks_do_not_limit_writers_to_three(self):
        stale = re.compile(r"W1\s*/\s*W2\s*/\s*W3|W1[–-]W3\b|<W1\|W2\|W3",
                           re.IGNORECASE)
        for name in RUNBOOKS:
            with self.subTest(runbook=name):
                contents = (ROOT / name).read_text(encoding="utf-8")
                self.assertIsNone(stale.search(contents),
                                  f"Outdated three-writer instructions in {name}")


if __name__ == "__main__":
    unittest.main()
