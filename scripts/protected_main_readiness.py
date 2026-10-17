"""Read-only evidence of direct-to-main state writes incompatible with strict PR protection.

Never edits GitHub, production-policy, WordPress, or secrets. The workflow
must NOT mark security_controls_verified while these routes still push main.
"""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_STATE = (
    "data/state/publication-ledger.json",
    "data/state/writer-claims.json",
    "data/state/refill-ledger.json",
    "data/state/research-intake-ledger.json",
    "data/state/topic-discovery-ledger.json",
)
STATE_WRITERS = (
    "scripts/publisher.py",
    "scripts/intake.py",
    "scripts/control_requests.py",
    "scripts/writer_session.py",
    "scripts/refill.py",
    "scripts/research_intake.py",
    "scripts/topic_discovery.py",
    "scripts/save_reports.py",
    "scripts/writer_branch_intake.py",
)
TRANSPORT = "scripts/git_state.py"
AUDIT_WORKFLOW = ".github/workflows/factory-audit.yml"


def inspect(root=ROOT):
    """Fail closed on unknown source; never accept a green QA badge as proof."""
    root = Path(root)
    diagnostics = []
    cas_path = root / TRANSPORT
    try:
        content = cas_path.read_text(encoding="utf-8")
    except OSError:
        diagnostics.append({"code": "CAS_SOURCE_UNAVAILABLE", "path": TRANSPORT})
        content = None
    if content is not None:
        # Detect the current protected-main-incompatible write-ahead CAS.
        direct = "refs/heads/main" in content and bool(
            re.search(r"['\"]push['\"]", content))
        if direct:
            diagnostics.append({
                "code": "DIRECT_MAIN_CAS_INCOMPATIBLE_WITH_REQUIRED_PR",
                "path": TRANSPORT,
                "detail": "RemoteState.persist pushes commits to refs/heads/main; a required-PR ruleset rejects the push before the WordPress POST.",
            })
    audit = root / AUDIT_WORKFLOW
    try:
        data = audit.read_text(encoding="utf-8")
    except OSError:
        diagnostics.append({"code": "AUDIT_WORKFLOW_UNAVAILABLE", "path": AUDIT_WORKFLOW})
    else:
        if re.search(r"\bgit\s+push\s+origin\s+HEAD:main\b", data):
            diagnostics.append({
                "code": "AUDIT_WORKFLOW_DIRECT_MAIN_PUSH",
                "path": AUDIT_WORKFLOW,
                "detail": "Authenticated inventory still uses git push origin HEAD:main.",
            })
    active_writers = []
    for name in STATE_WRITERS:
        path = root / name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            diagnostics.append({"code": "STATE_WRITER_UNAVAILABLE", "path": name})
            continue
        if "RemoteState" in text or "state.persist(" in text:
            active_writers.append(name)
    if not active_writers:
        diagnostics.append({"code": "STATE_WRITER_VERIFICATION_UNAVAILABLE", "path": "scripts/"})
    writer_branch = root / "scripts/writer_branch_intake.py"
    workflow = root / ".github/workflows/writer-branch-intake.yml"
    lane_present = writer_branch.is_file() and workflow.is_file()
    return {
        "status": "BLOCKED" if diagnostics else "READY_FOR_REVIEW",
        "main_protection_migration_ready": not diagnostics,
        "direct_main_write_blockers": diagnostics,
        "existing_state_writers": active_writers,
        "sensitive_state_files": list(SENSITIVE_STATE),
        "writer_branch_lane_present": lane_present,
        "github_ruleset_mutations": 0,
        "wordpress_writes": 0,
        "production_flags_modified": False,
        "note": "READY_FOR_REVIEW is only a source inspection; NOT evidence that protected-main commits, live CODEOWNERS or production E2E are verified.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None)
    parser.add_argument("--enforce", action="store_true",
                        help="Exit nonzero if incompatible with protected main")
    args = parser.parse_args()
    result = inspect()
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    print(serialized)
    if args.output:
        path = Path(args.output).resolve()
        if path.is_relative_to(ROOT.resolve()):
            raise ValueError("Diagnostic must not modify tracked repository")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Protected main migration: " + result["status"] + "\n\n")
            f.write("Direct-main write blockers: " +
                    str(len(result["direct_main_write_blockers"])) +
                    ". This is a safe audit only; WordPress publishing remains unchanged.\n")
            for issue in result["direct_main_write_blockers"]:
                f.write("- " + issue["code"] + ": `" + issue["path"] + "`\n")
    return int(args.enforce and result["status"] != "READY_FOR_REVIEW")


if __name__ == "__main__":
    raise SystemExit(main())
