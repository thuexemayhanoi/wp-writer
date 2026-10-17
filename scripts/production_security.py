"""Fail-closed inspection of real GitHub ruleset state before using WP secrets.

This is defense-in-depth, NOT a substitute for GitHub-enforced CODEOWNER
reviews and restricted production-environment secrets. No policy flags are
changed and no WordPress writes occur in this preflight.
"""
import json
import os
import sys
from pathlib import Path
import urllib.error
import urllib.request

REPO = "thuexemayhanoi/wp-writer"
BRANCH = "main"
TRUSTED_OWNER = "@thuexemayhanoi"
PRIVILEGED_PATTERNS = (
    "/.github/", "/scripts/", "/tests/", "/config/",
    "/requirements.txt", "/AGENTS.md", "/data/state/",
    "/data/topics.jsonl", "/data/taxonomy.json",
    "/data/business-facts.json", "/data/protected-urls.json",
)


def privileged_codeowners_present(content):
    """Owner must cover workflow/runtime/control state with an exact owner."""
    rows = {}
    for line in content.splitlines():
        part = line.split("#", 1)[0].strip().split()
        if len(part) >= 2:
            rows[part[0]] = set(part[1:])
    return all(TRUSTED_OWNER in rows.get(path, set())
               for path in PRIVILEGED_PATTERNS)


def ruleset_applies_to_main(ruleset):
    refs = ruleset.get("conditions", {}).get("ref_name", {})
    included = refs.get("include", [])
    excluded = refs.get("exclude", [])
    names = {"~DEFAULT_BRANCH", "refs/heads/main", "main"}
    return bool(set(included) & names) and not bool(set(excluded) & names)


def ruleset_protects_privileged_code(ruleset):
    """Require GitHub PR + CODEOWNER review for privileged files, zero bypass.

    GitHub's PR rule permits 0 generic approvals while `require_code_owner_review`
    still requires a code owner's review for files named by CODEOWNERS. This
    lets unowned ARTICLE-ONLY PRs merge without owner reviewing every post.
    """
    if ruleset.get("enforcement") != "active" or not ruleset_applies_to_main(ruleset):
        return False
    if ruleset.get("bypass_actors"):
        return False
    rules = [r for r in ruleset.get("rules", []) if r.get("type") == "pull_request"]
    return any(
        isinstance(r.get("parameters", {}).get("required_approving_review_count"), int)
        and 0 <= r["parameters"]["required_approving_review_count"] <= 10
        and r.get("parameters", {}).get("require_code_owner_review") is True
        for r in rules
    )


def github_json(url, token):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "wp-writer-production-security-preflight",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.load(response)


def check_security(fetch=github_json, token=None):
    """Only report verified facts; GitHub API outage is a blocking failure."""
    token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    base = "https://api.github.com/repos/" + REPO
    reasons = []
    # Local CODEOWNERS must originate from the trusted protected main checkout.
    # This is not proof of enforcement; live GitHub ruleset readback is mandatory.
    codeowners = Path(__file__).resolve().parents[1] / ".github" / "CODEOWNERS"
    try:
        if not privileged_codeowners_present(codeowners.read_text(encoding="utf-8")):
            reasons.append("Privileged CODEOWNERS patterns or owner missing")
    except OSError:
        reasons.append("CODEOWNERS file unavailable")
    try:
        branch = fetch(base + "/branches/" + BRANCH, token)
        if branch.get("protected") is not True:
            reasons.append("main branch is not protected")
        rules = fetch(base + "/rulesets", token)
        active = []
        for row in rules:
            if row.get("enforcement") != "active":
                continue
            item = fetch(base + "/rulesets/" + str(row["id"]), token)
            if ruleset_protects_privileged_code(item):
                active.append(row["id"])
        if not active:
            reasons.append("No active main ruleset enforces reviewed PR + CODEOWNER review with zero bypass actors")
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError) as exc:
        reasons.append("GitHub protection verification unavailable: " + str(exc)[:160])
        active = []
    return {"status": "PASS" if not reasons else "BLOCKED",
            "repo": REPO, "branch": BRANCH,
            "review_rulesets": active, "blockers": reasons,
            "production_flags_modified": False, "wordpress_writes": 0}


def main():
    report = check_security()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
