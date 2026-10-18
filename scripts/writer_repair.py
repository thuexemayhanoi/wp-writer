#!/usr/bin/env python3
"""Claude-side QA repair journal. No AI API, WordPress calls, or privileged main writes.

Usage:
  python scripts/writer-repair.py save --session s-name --id NT-000101 --note "fixed ..."
  python scripts/writer-repair.py resume --session s-name --id NT-000101

Each Topic ID has an isolated non-publishing repair/<session>/<id> Git ref.
Only a *live* owner may save/restore. SHA-256 and non-fast-forward push
protect cross-machine sessions; the normal writer-session push gate is the
only route from an actual PASS to main and then the Publisher.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from common import ROOT, digest, git, load, now
from gate_triage import triage
from qa import evaluate_safely, read_article
from writer_session import owner, remote_snapshot

SESSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{3,79}\Z")
TOPIC_RE = re.compile(r"NT-[0-9]{6}\Z")


def paths(session, topic_id):
    if not SESSION_RE.fullmatch(session) or not TOPIC_RE.fullmatch(topic_id):
        raise ValueError("Invalid session or Topic ID")
    return (
        "repair/" + session + "/" + topic_id,
        "data/repair-checkpoints/" + session + "/" + topic_id + ".json",
        "posts/drafts/" + topic_id + ".md",
    )


def enforce_owner(session, topic_id, metadata=None):
    _, registry, rows = remote_snapshot()
    slot = owner(registry, session, topic_id)
    topic = next((row for row in rows if row["topic_id"] == topic_id), None)
    if topic is None:
        raise ValueError("Topic ID missing from approved manifest")
    if metadata is not None and (
        metadata.get("writer_session") != session
        or metadata.get("writer_slot") != slot
        or metadata.get("topic_id") != topic_id
    ):
        raise ValueError("Draft metadata differs from live lease owner")
    return slot, topic, rows


def remote_repair(ref, checkpoint_path, draft_path):
    """Read ONLY the exact per-topic branch. Never reset another writer."""
    p = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", "refs/heads/" + ref],
        cwd=ROOT, text=True, capture_output=True,
    )
    if p.returncode:
        raise RuntimeError("Cannot verify remote repair ref")
    if not p.stdout.strip():
        return None, None, None
    git("fetch", "--no-tags", "origin",
        "refs/heads/" + ref + ":refs/remotes/origin/" + ref)
    head = git("rev-parse", "refs/remotes/origin/" + ref)

    def read_at(path):
        z = subprocess.run(
            ["git", "show", head + ":" + path], cwd=ROOT,
            text=True, capture_output=True,
        )
        if z.returncode:
            raise RuntimeError("Incomplete checkpoint branch: " + path)
        return z.stdout

    checkpoint = json.loads(read_at(checkpoint_path))
    draft = read_at(draft_path)
    if digest(draft.encode("utf-8")) != checkpoint.get("source_sha256"):
        raise ValueError("Checkpoint draft SHA-256 does not match branch content")
    return head, checkpoint, draft


def qa_defects(qa):
    reasons = list(qa.get("errors", [])) + list(qa.get("review", []))
    for gate, info in sorted((qa.get("gates") or {}).items()):
        reasons += ["G" + str(gate) + ": " + str(e)
                    for e in info.get("errors", []) + info.get("review", [])]
    return list(dict.fromkeys(reasons))


def advance(previous, *, session, slot, topic_id, sha, qa, note, timestamp, max_repairs=10):
    """Deterministic 10-content-revision counter; QA status is never forged."""
    if max_repairs < 1:
        raise ValueError("Invalid repair limit")
    if previous and (
        previous["session_id"] != session or previous["writer"] != slot
        or previous["topic_id"] != topic_id
    ):
        raise ValueError("Checkpoint ownership conflict")
    if qa.get("source_sha256") != sha:
        raise ValueError("QA evaluated a different draft revision")
    is_new = previous is None or previous["source_sha256"] != sha
    if previous and previous["qa_status"] == "PASS" and is_new:
        raise ValueError("Cannot rewrite an already QA-PASS checkpoint")
    if previous and is_new and not note.strip():
        raise ValueError("Describe the concrete editing changes in --note")
    count = int(previous["repair_attempts"]) if previous else 0
    if previous and is_new:
        if count >= max_repairs:
            raise ValueError("Ten content repairs exhausted; hold for review")
        count += 1
    if previous and not is_new and previous["qa_status"] == qa["status"]:
        # A retry of identical bytes is not a new content-repair attempt.
        history = list(previous["history"])
    else:
        history = list(previous["history"]) if previous else []
        history.append({
            "revision": len(history) + 1,
            "repair_attempt": count,
            "source_sha256": sha,
            "qa_status": qa["status"],
            "seo_score": qa.get("seo_score"),
            "quality_score": qa.get("quality_score"),
            "errors": qa_defects(qa),
            "edit_note": note.strip() or "Initial QA assessment",
            "evaluated_at": timestamp,
        })
    classification = triage(qa)["hold_class"]
    action = ("SUBMIT_BY_WRITER_SESSION" if qa["status"] == "PASS"
              else "HOLD_FOR_REVIEW" if classification == "REAL_RISK"
              else "HOLD_REPAIR_LIMIT" if count >= max_repairs
              else "WAIT_FOR_INFRA_RECHECK" if classification == "INFRA_PENDING"
              else "CLAUDE_FIX_REMAINING_ERRORS")
    return {
        "schema_version": 1, "topic_id": topic_id, "writer": slot,
        "session_id": session, "source_sha256": sha,
        "repair_attempts": count, "repair_limit": max_repairs,
        "qa_status": qa["status"], "seo_score": qa.get("seo_score"),
        "quality_score": qa.get("quality_score"),
        "hold_class": classification, "remaining_errors": qa_defects(qa),
        "completed_edits": [h["edit_note"] for h in history if h["repair_attempt"] > 0],
        "history": history, "next_action": action, "updated_at": timestamp,
    }


def persist(ref, checkpoint_path, draft_path, checkpoint, draft, existing_head):
    """No checkout or shared index, no force push, and no changes to main."""
    base = existing_head or git("rev-parse", "origin/main")
    checkpoint_text = json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n"
    with tempfile.TemporaryDirectory(prefix="writer-repair-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        git("read-tree", base, env=env)
        for path, raw in ((checkpoint_path, checkpoint_text), (draft_path, draft)):
            blob = git("hash-object", "-w", "--stdin", input=raw)
            git("update-index", "--add", "--cacheinfo",
                "100644," + blob + "," + path, env=env)
        tree = git("write-tree", env=env)
        commit = git(
            "-c", "user.name=wp-writer-repair",
            "-c", "user.email=wp-writer-bot@users.noreply.github.com",
            "commit-tree", tree, "-p", base,
            input="repair: checkpoint " + checkpoint["topic_id"] + " attempt "
                  + str(checkpoint["repair_attempts"]) + "\n",
        )
    push = subprocess.run(
        ["git", "push", "origin", commit + ":refs/heads/" + ref],
        cwd=ROOT, text=True, capture_output=True,
    )
    if push.returncode:
        raise RuntimeError(
            "Repair branch advanced or push was rejected; fetch and reconcile. "
            "Never force push or overwrite another session."
        )
    return commit


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["save", "resume", "status"])
    parser.add_argument("--session", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--no-submit", action="store_true",
                        help="Keep a true QA PASS in checkpoint for explicit submission")
    args = parser.parse_args(argv)
    ref, ckpt_path, draft_path = paths(args.session, args.id)
    slot, topic, rows = enforce_owner(args.session, args.id)
    head, previous, remote_draft = remote_repair(ref, ckpt_path, draft_path)
    if args.action == "status":
        print(json.dumps(previous or {
            "topic_id": args.id, "writer": slot, "session_id": args.session,
            "repair_attempts": 0, "next_action": "INITIAL_DRAFT_THEN_SAVE",
        }, ensure_ascii=False, indent=2))
        return
    local_path = ROOT / draft_path
    if args.action == "resume":
        if remote_draft is None:
            raise ValueError("No remote repair checkpoint yet")
        if local_path.is_file() and digest(local_path.read_bytes()) != previous["source_sha256"]:
            raise ValueError("Local draft diverges; reconcile before restore, no overwrite")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if not local_path.exists():
            local_path.write_text(remote_draft, encoding="utf-8")
        read_meta, _, sha = read_article(local_path)
        enforce_owner(args.session, args.id, read_meta)
        if sha != previous["source_sha256"]:
            raise ValueError("Restored draft SHA mismatch")
        print(json.dumps(previous, ensure_ascii=False, indent=2))
        return
    if not local_path.is_file() or local_path.is_symlink():
        raise ValueError("Owned local draft not found or unsafe")
    meta, _, _ = read_article(local_path)
    enforce_owner(args.session, args.id, meta)
    sha = digest(local_path.read_bytes())
    qa = evaluate_safely(local_path, topic, rows)
    rules = load("config/qa-rules.json")
    if (qa.get("status") == "PASS"
            and (qa.get("seo_score", -1) < rules["seo_min"]
                 or qa.get("quality_score", -1) < rules["quality_min"])):
        raise ValueError("QA PASS conflicts with unchanged numeric thresholds")
    checkpoint = advance(
        previous, session=args.session, slot=slot, topic_id=args.id,
        sha=sha, qa=qa, note=args.note, timestamp=now(),
        max_repairs=load("config/writer-repair.json")["content_repair_max"],
    )
    commit = persist(
        ref, ckpt_path, draft_path, checkpoint,
        local_path.read_text(encoding="utf-8"), head,
    )
    print(json.dumps({
        "checkpoint_commit": commit, "branch": ref,
        "attempt": checkpoint["repair_attempts"],
        "status": qa["status"], "seo": qa.get("seo_score"),
        "quality": qa.get("quality_score"),
        "next_action": checkpoint["next_action"],
        "remaining_errors": checkpoint["remaining_errors"],
    }, ensure_ascii=False))
    if qa["status"] == "PASS" and not args.no_submit:
        # The existing trusted main path independently re-runs all QA gates.
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/writer-session.py"),
             "push", "--ids", args.id, "--session", args.session],
            cwd=ROOT, check=True,
        )


if __name__ == "__main__":
    main()
