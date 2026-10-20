"""Trusted-main, no-WordPress intake for article-only writer/* branches.

This script never executes files from the writer branch and never accepts
workflow/config/registry modifications. Read-only mode validates without writes;
apply mode can run ONLY from the trusted main workflow after green branch QA.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from common import ROOT, digest, load, now, topics
from git_state import RemoteState
from qa import read_article, evaluate, counted_text, shingles, jaccard
from writer_session import REG, owner
from intake import run as admit_submissions

REPO = "thuexemayhanoi/wp-writer"
LEDGER = "data/state/publication-ledger.json"
MAX_ARTICLES = 10
ATTEMPTS = 4  # admissions per run when main moves underneath it
MAX_ARTICLE_BYTES = 400_000
BRANCH_RE = re.compile(r"writer/[a-zA-Z0-9][a-zA-Z0-9_./-]{2,75}$")
SHA_RE = re.compile(r"[0-9a-f]{40}$")
DRAFT_RE = re.compile(r"posts/drafts/NT-[0-9]{6}\.md$")


def check_changed_paths(lines):
    """Only A/M for article markdown; no deletions, rename or privileged files."""
    if not lines:
        raise ValueError("WRITER_BRANCH_NO_ARTICLES")
    paths = []
    for line in lines:
        pieces = line.split("\t")
        if len(pieces) != 2 or pieces[0] not in ("A", "M"):
            raise ValueError("FORBIDDEN_WRITER_CHANGE: not a plain add/modify")
        path = pieces[1]
        if not DRAFT_RE.fullmatch(path) or path in paths:
            raise ValueError("FORBIDDEN_WRITER_PATH: " + path[:160])
        paths.append(path)
    if len(paths) > MAX_ARTICLES:
        raise ValueError("WRITER_BRANCH_BATCH_TOO_LARGE")
    return paths


def git_read(*args, binary=False):
    proc = subprocess.run(["git", *args], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise RuntimeError("Writer Git source unavailable: " + args[0])
    return proc.stdout if binary else proc.stdout.decode("utf-8").strip()


def verify_source(branch, sha):
    if not BRANCH_RE.fullmatch(branch) or ".." in branch or "//" in branch:
        raise ValueError("Invalid writer branch")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("Invalid green Writer QA SHA")
    git_read("fetch", "--no-tags", "origin", "refs/heads/" + branch +
             ":refs/remotes/origin/" + branch)
    current = git_read("rev-parse", "refs/remotes/origin/" + branch)
    if current != sha:
        raise ValueError("Writer branch moved after QA; wait for fresh QA")
    git_read("fetch", "--no-tags", "origin", "main")
    ancestor = git_read("merge-base", "origin/main", sha)
    if not ancestor:
        raise ValueError("No common trusted-main commit")
    changed = git_read("diff", "--name-status", "--no-renames",
                       ancestor, sha).splitlines()
    return check_changed_paths(changed)


def blob_at(sha, path):
    raw = git_read("show", sha + ":" + path, binary=True)
    if not raw or len(raw) > MAX_ARTICLE_BYTES or b"\x00" in raw:
        raise ValueError("Invalid/oversized writer article: " + path)
    return raw.decode("utf-8")


def prepare(branch, sha):
    paths = verify_source(branch, sha)
    registry = load(REG)
    ledger = load(LEDGER, {"posts": {}})
    rows = topics()
    row_by_id = {row["topic_id"]: row for row in rows}
    prepared = []
    with tempfile.TemporaryDirectory(prefix="writer-qa-") as temp:
        # The trusted QA must compare against all other main drafts, but MUST NOT
        # compare a repaired article against its own outdated main revision.
        scan_root = Path(temp) / "scan"
        scan_dir = scan_root / "posts" / "drafts"
        scan_dir.mkdir(parents=True)
        new_names = {Path(path).name for path in paths}
        for old_file in (ROOT / "posts" / "drafts").glob("NT-*.md"):
            if old_file.name not in new_names:
                (scan_dir / old_file.name).write_bytes(old_file.read_bytes())
        for path in paths:
            raw = blob_at(sha, path)
            tmp = scan_dir / Path(path).name
            tmp.write_text(raw, encoding="utf-8")
        for path in paths:
            tmp = scan_dir / Path(path).name
            raw = tmp.read_text(encoding="utf-8")
            meta, body, hash_value = read_article(tmp)
            topic_id = tmp.stem
            if topic_id not in row_by_id or meta.get("topic_id") != topic_id:
                raise ValueError("Unrecognized Writer topic ID: " + topic_id)
            existing = ROOT / path
            if existing.exists() and existing.read_text(encoding="utf-8") == raw:
                receipt = registry.get("submissions", {}).get(topic_id, {})
                if receipt.get("sha256") == hash_value:
                    prepared.append({"path": path, "raw": raw, "topic_id": topic_id,
                                     "hash": hash_value, "status": "ALREADY_ADMITTED",
                                     "body": body})
                    continue
            if topic_id in ledger["posts"]:
                raise ValueError("Already registered WordPress publication ID: " + topic_id)
            slot = owner(registry, meta.get("writer_session"), topic_id)
            if meta.get("writer_slot") != slot:
                raise ValueError("Writer session slot mismatch: " + topic_id)
            # qa.ROOT controls draft duplicate enumeration only; factual/taxonomy
            # registries remain the trusted main data from common.load().
            from unittest.mock import patch
            with patch("qa.ROOT", scan_root):
                qa = evaluate(tmp, row_by_id[topic_id], rows=rows, check_claim=False)
            if qa["status"] != "PASS" or qa["seo_score"] < load("config/qa-rules.json")["seo_min"]:
                raise ValueError("WRITER_QA_BLOCKED " + topic_id + " " +
                                 qa["status"] + " SEO=" + str(qa.get("seo_score")) +
                                 " QUALITY=" + str(qa.get("quality_score")) +
                                 " ERRORS=" + json.dumps(qa.get("errors", []), ensure_ascii=False) +
                                 " REVIEW=" + json.dumps(qa.get("review", []), ensure_ascii=False))
            prepared.append({"path": path, "raw": raw, "topic_id": topic_id,
                             "hash": hash_value, "status": "QA_PASS", "body": body})
        # Compare the whole incoming batch, not just each article against main.
        min_distinct = load("config/qa-rules.json")["near_duplicate_jaccard"]
        for i, left in enumerate(prepared):
            for right in prepared[i+1:]:
                similarity = jaccard(shingles(counted_text(left["body"])),
                                     shingles(counted_text(right["body"])))
                if similarity >= min_distinct:
                    raise ValueError("Near duplicate articles in writer batch")
    return prepared


def ingest(branch, sha, dry_run=True):
    prepared = prepare(branch, sha)
    fresh = [p for p in prepared if p["status"] == "QA_PASS"]
    if not fresh:
        return {"status": "ALREADY_ADMITTED", "count": 0, "branch": branch}
    if dry_run:
        return {"status": "QA_PASS_READ_ONLY", "count": len(fresh),
                "topic_ids": [p["topic_id"] for p in fresh], "branch": branch}
    # GitHub workflow_run must check out TRUSTED main, never writer source code.
    if (os.getenv("GITHUB_ACTIONS") != "true" or
        os.getenv("GITHUB_REPOSITORY") != REPO or
        os.getenv("GITHUB_REF") != "refs/heads/main"):
        raise ValueError("Trusted main GitHub Actions required for Writer intake")
    paths = [p["path"] for p in fresh] + [REG]
    state = RemoteState()
    state.remember(paths)
    for item in fresh:
        file = ROOT / item["path"]
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(item["raw"], encoding="utf-8")
    # Reuse unchanged main intake for immutable SHA + active lease verification.
    admit_submissions(persist=False)
    receipts = load(REG).get("submissions", {})
    for item in fresh:
        if receipts.get(item["topic_id"], {}).get("sha256") != item["hash"]:
            raise ValueError("Trusted Writer intake receipt mismatch")
    committed = state.persist(paths, "writer: trusted branch QA article intake")
    return {"status": "ADMITTED", "count": len(fresh),
            "topic_ids": [p["topic_id"] for p in fresh],
            "main_commit": committed, "branch": branch, "at": now()}


def refresh_trusted_main():
    """Move the throw-away Actions checkout to the newest main before a retry (never a developer's working tree)."""
    if os.getenv("GITHUB_ACTIONS") != "true":
        raise ValueError("Trusted main GitHub Actions required to refresh the checkout")
    git_read("fetch", "--no-tags", "origin", "main")
    git_read("reset", "--hard", "origin/main")
    git_read("clean", "-fdq", "--", "posts/drafts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    # Writers commit to main all day and the registry is in almost every commit, so the compare-and-swap in
    # RemoteState.persist can lose a race with a commit that landed while this run was checking the article. Nothing
    # was pushed in that case: take the newest main and redo the whole admission (QA included) instead of failing.
    attempts = ATTEMPTS if args.apply else 1
    for attempt in range(attempts):
        try:
            result = ingest(args.branch, args.sha, dry_run=not args.apply)
            break
        except RuntimeError as exc:
            if "State conflict" not in str(exc) or attempt == attempts - 1:
                raise
            print("WRITER_BRANCH_INTAKE_RETRY: main moved during admission (%s); attempt %d of %d"
                  % (exc, attempt + 2, attempts))
            refresh_trusted_main()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
