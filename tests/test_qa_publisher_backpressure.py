"""Regression guards for emergency publisher backpressure and zero-credential QA.

These deliberately verify the public workflow contract, not WordPress runtime state.
"""
import json
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def events(doc):
    # PyYAML 1.1 interprets GitHub's unquoted `on:` as Boolean True.
    return doc.get("on", doc.get(True, {}))


class BackpressureWorkflowTests(unittest.TestCase):
    def test_writer_push_does_not_spawn_one_qa_per_draft(self):
        # Pipeline v3 (2026-10-20): a draft push wakes the sweep, but the concurrency group coalesces it (at most one
        # running + one pending run for main; GitHub drops older pending runs), the sweep checks out the CURRENT main
        # tree and the incremental plan evaluates only new/changed drafts. The cron stays as a fallback because GitHub
        # delivered the */5 schedule only twice in six hours on 2026-10-19/20.
        qa = workflow("writer-qa.yml")
        on = events(qa)
        self.assertEqual(on["schedule"][0]["cron"], "*/5 * * * *")
        self.assertIn("workflow_dispatch", on)
        self.assertIn("pull_request", on)
        self.assertIn("push", on)
        paths = on["push"]["paths"]
        self.assertIn("posts/drafts/**", paths)
        self.assertTrue(any(p.startswith("scripts/") for p in paths))
        self.assertEqual(qa["permissions"]["contents"], "read")
        self.assertIn("wp-writer-qa-", qa["concurrency"]["group"])
        self.assertIs(qa["concurrency"]["cancel-in-progress"], False)
        checkout = qa["jobs"]["tests-and-content"]["steps"][0]
        self.assertIn("'main'", checkout["with"]["ref"])
        self.assertIn("pull_request", checkout["with"]["ref"])

    def test_scheduled_qa_is_cheap_during_owner_pause(self):
        qa = workflow("writer-qa.yml")
        steps = qa["jobs"]["tests-and-content"]["steps"]
        gate = next(i for i, item in enumerate(steps) if item.get("id") == "schedule_gate")
        self.assertIn("GITHUB_EVENT_NAME", steps[gate]["run"])
        self.assertIn("emergency_stop", steps[gate]["run"])
        self.assertIn("paused", steps[gate]["run"])
        for step in steps[gate + 1:]:
            self.assertIn("steps.schedule_gate.outputs.run_qa == 'true'", step.get("if", ""))

    def test_publisher_isolated_and_safe_to_resume_after_sweep(self):
        pub = workflow("wordpress-publisher.yml")
        on = events(pub)
        self.assertIn("workflow_run", on)
        self.assertIn("schedule", on)
        self.assertIn("workflow_dispatch", on)
        self.assertEqual(pub["concurrency"]["group"], "wp-writer-publisher")
        self.assertIs(pub["concurrency"]["cancel-in-progress"], False)
        expr = pub["jobs"]["publisher"]["if"]
        self.assertIn("github.event.workflow_run.event == 'schedule'", expr)
        self.assertIn("github.event.workflow_run.event == 'workflow_dispatch'", expr)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", expr)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", expr)

    def test_emergency_switch_guards_heavy_and_secret_steps(self):
        pub = workflow("wordpress-publisher.yml")
        steps = pub["jobs"]["publisher"]["steps"]
        preflight = next(i for i, s in enumerate(steps) if s.get("id") == "safety_switch")
        self.assertLess(preflight, next(i for i, s in enumerate(steps) if "pip install" in s.get("run", "")))
        self.assertIn("emergency_stop", steps[preflight]["run"])
        self.assertIn("paused", steps[preflight]["run"])
        guarded = ["scripts/intake.py", "scripts/qa_gate.py", "scripts/publisher.py",
                   "scripts/reports.py", "scripts/save_reports.py"]
        for command in guarded:
            matches = [s for s in steps if command in s.get("run", "")]
            self.assertTrue(matches, command)
            for s in matches:
                self.assertIn("steps.safety_switch.outputs.active == 'true'", s.get("if", ""), command)
        for s in steps:
            if "WP_APPLICATION_PASSWORD" in json.dumps(s):
                self.assertIn("steps.safety_switch.outputs.active == 'true'", s.get("if", ""))

    def test_owner_release_keeps_daily_and_serialized_limits_after_pilot(self):
        policy = json.loads((ROOT / "config" / "production-policy.json").read_text(encoding="utf-8"))
        # The 3-post pilot has been explicitly lifted for the next 2,000-topic
        # campaign. Preserve explicit owner permission, daily limits, 2x5 runs
        # and emergency stop rather than silently permitting unlimited writes.
        self.assertIsNone(policy.get("publisher_pilot"))
        self.assertTrue(policy.get("owner_approval_ref"))
        self.assertTrue(policy.get("production_enabled"))
        self.assertEqual(policy.get("approved_capacity"), 2000)
        self.assertEqual(policy.get("batch_size"), 2)
        self.assertEqual(policy.get("max_batches_per_run"), 5)
        self.assertLessEqual(policy.get("max_new_posts_daily"), 1000)
        self.assertIs(type(policy.get("emergency_stop")), bool)
        self.assertIs(type(policy.get("paused")), bool)
        self.assertFalse(policy.get("allow_category_create"))
        self.assertEqual(policy.get("on_category_mismatch"), "draft")


if __name__ == "__main__":
    unittest.main()
