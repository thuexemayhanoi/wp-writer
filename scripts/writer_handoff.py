#!/usr/bin/env python3
"""GitHub-only Writer handoff status. Read-only; NEVER queries WordPress.

G1-G6 and the immutable submission receipt belong to Writer/Trusted QA.
G7 live WordPress readback belongs ONLY to the authenticated Publisher.
This command is a status projection, not a new approval or publishing gate.
"""
import argparse
import json
from pathlib import Path

from common import ROOT, digest, load
from qa import read_article


def result_for(topic_id, *, registry, claims, ledger, qa, rules, drafts_dir):
    topics = {row["topic_id"]: row for row in registry}
    topic = topics.get(topic_id)
    receipt = (claims.get("submissions") or {}).get(topic_id) or {}
    published = (ledger.get("posts") or {}).get(topic_id) or {}
    phase = published.get("phase")
    base = {"topic_id": topic_id, "status": None, "writer_done": False,
            "wordpress_verified": False, "publisher_phase": phase,
            "wp_post_id": published.get("wp_id"), "wp_url": published.get("url")}
    if not topic:
        return dict(base, status="UNKNOWN_TOPIC_ID")
    # WordPress states may only be taken from an authentic Publisher ledger.
    if phase == "VERIFIED":
        g7 = published.get("g7") or {}
        verified = (g7.get("status") == "PASS" and published.get("wp_id")
                    and published.get("url"))
        return dict(base, status="WORDPRESS_G7_VERIFIED" if verified
                    else "PUBLISHER_G7_UNCONFIRMED", writer_done=True,
                    wordpress_verified=bool(verified))
    if phase in ("POST_INTENT", "NEEDS_RECONCILE", "CREATED", "VERIFY_PENDING"):
        return dict(base, status="PUBLISHER_RECONCILE_PENDING", writer_done=True)
    article = Path(drafts_dir) / (topic_id + ".md")
    if not article.is_file():
        return dict(base, status="NOT_AUTHORED")
    try:
        metadata, _, actual_sha = read_article(article)
    except (OSError, ValueError, TypeError) as exc:
        return dict(base, status="ARTICLE_INVALID", reason=type(exc).__name__)
    if not receipt:
        return dict(base, status="WRITER_NOT_SUBMITTED")
    if (receipt.get("sha256") != actual_sha or
            receipt.get("session") != metadata.get("writer_session") or
            receipt.get("slot") != metadata.get("writer_slot") or
            topic_id != metadata.get("topic_id")):
        return dict(base, status="WRITER_RECEIPT_MISMATCH")
    verdict = qa.get(topic_id) or {}
    if not verdict or verdict.get("source_sha256") != actual_sha:
        return dict(base, status="GITHUB_QA_PENDING", writer_done=False)
    score_ok = (verdict.get("seo_score", -1) >= rules.get("seo_min", 76) and
                verdict.get("quality_score", -1) >= rules.get("quality_min", 76))
    if (verdict.get("status") != "PASS" or verdict.get("errors") or
            verdict.get("review") or not score_ok):
        return dict(base, status="WRITER_QA_REPAIR", writer_done=False,
                    seo_score=verdict.get("seo_score"),
                    quality_score=verdict.get("quality_score"))
    return dict(base, status="WRITER_QA_PASS_AWAITING_PUBLISHER",
                writer_done=True, wordpress_verified=False,
                seo_score=verdict.get("seo_score"),
                quality_score=verdict.get("quality_score"))


def report(*, ids=None, session=None, limit=20, root=ROOT):
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be 1..100")
    if not ids and not session:
        raise ValueError("Supply --ids or --session; never scan every draft")
    root = Path(root)
    registry = [json.loads(x) for x in (root / "data/topics.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    claims = json.loads((root / "data/state/writer-claims.json").read_text(encoding="utf-8"))
    ledger = json.loads((root / "data/state/publication-ledger.json").read_text(encoding="utf-8"))
    rules = json.loads((root / "config/qa-rules.json").read_text(encoding="utf-8"))
    selected = list(dict.fromkeys(ids or []))
    if session:
        lease_ids = [t for lease in (claims.get("leases") or {}).values()
                     if lease.get("session") == session for t in lease.get("topic_ids", [])]
        submitted_ids = [t for t, receipt in (claims.get("submissions") or {}).items()
                         if receipt.get("session") == session]
        selected = list(dict.fromkeys(selected + lease_ids + submitted_ids))
    selected = selected[:limit]
    results = []
    for topic_id in selected:
        qa_path = root / "data/qa" / (topic_id + ".json")
        record = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.is_file() else {}
        results.append(result_for(topic_id, registry=registry, claims=claims,
            ledger=ledger, qa={topic_id: record}, rules=rules,
            drafts_dir=root / "posts/drafts"))
    return {
        "mode": "GITHUB_WRITER_ONLY",
        "requires_wordpress_credentials": False,
        "writer_handoff_gate": "G1-G6 and immutable GitHub receipt",
        "publisher_verification_gate": "G7 after a real WordPress write",
        "count": len(results),
        "results": results,
        "note": ("Writer may take the next eligible topic after a trusted QA-PASS "
                 "submission, without waiting for WordPress. Only Publisher "
                 "can label G7 VERIFIED; GitHub QA PASS is not publication.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=None)
    parser.add_argument("--ids", default="")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    selected = [x.strip() for x in args.ids.split(",") if x.strip()]
    print(json.dumps(report(ids=selected, session=args.session, limit=args.limit),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
