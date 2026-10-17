"""Fail-closed inspection of real GitHub ruleset state before using WP secrets.

This is defense-in-depth, NOT a substitute for GitHub-enforced CODEOWNER
reviews and restricted production-environment secrets. No policy flags are
changed and no WordPress writes occur in this preflight.
"""
import json
import os
import sys
import urllib.error
import urllib.request

REPO = "thuexemayhanoi/wp-writer"
BRANCH = "main"


def ruleset_applies_to_main(ruleset):
    refs = ruleset.get("conditions", {}).get("ref_name", {})
    included = refs.get("include", [])
    excluded = refs.get("exclude", [])
    names = {"~DEFAULT_BRANCH", "refs/heads/main", "main"}
    return bool(set(included) & names) and not bool(set(excluded) & names)


def ruleset_protects_privileged_code(ruleset):
    """Require real reviewed PRs, code-owner approval and no bypass."""
    if ruleset.get("enforcement") != "active" or not ruleset_applies_to_main(ruleset):
        return False
    if ruleset.get("bypass_actors"):
        return False
    rules = [r for r in ruleset.get("rules", []) if r.get("type") == "pull_request"]
    return any(
        r.get("parameters", {}).get("required_approving_review_count", 0) >= 1
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
