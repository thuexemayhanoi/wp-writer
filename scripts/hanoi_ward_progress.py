"""Reconcile the Hanoi 51-ward editorial checkpoint with FACTORY + G7 receipts.

Read-only unless --persist-state is passed by the trusted main Publisher.
Never invent topic IDs, QA scores, post IDs or publication evidence.
Never update legacy WordPress content or modify submission/writer leases.
"""
import argparse
import json
from pathlib import Path

from common import ROOT, load, now, save, topics
from git_state import RemoteState

PATH = "editorial/seo-51-phuong/progress.json"
KEY = "hanoi-ward-rentals"
CAMPAIGN = "HN-51-WARDS"
TERM = 182


def reconcile(progress, rows, ledger, qa=None):
    """Return a new checkpoint using only independently corroborated records."""
    qa = qa or {}
    out = json.loads(json.dumps(progress, ensure_ascii=False))
    if out.get("campaign") != CAMPAIGN or out.get("taxonomy_key") != KEY:
        raise ValueError("WRONG_WARD_CAMPAIGN_REGISTRY")
    if out.get("wordpress_category_id") != TERM or out.get("wordpress_parent_category_id") != 162:
        raise ValueError("HANOI_WARD_CATEGORY_UNVERIFIED")
    if len(out.get("completed", [])) != out.get("completed_editorial_drafts"):
        raise ValueError("WRONG_EDITORIAL_COUNT")
    known = {t["topic_id"]: t for t in rows}
    attached = set()
    for entry in out["completed"]:
        matching = []
        for t in rows:
            if t.get("campaign_id") != CAMPAIGN:
                continue
            if t.get("taxonomy_key") != KEY:
                # Never credit a campaign topic under a wrong category.
                continue
            source = t.get("campaign_editorial_file") or t.get("editorial_source")
            if source == entry.get("file") or (entry.get("topic_id") and
                                               entry["topic_id"] == t.get("topic_id")):
                matching.append(t)
        if len(matching) > 1:
            raise ValueError("MULTIPLE_TOPICS_FOR_WARD:"+entry["ward"])
        if not matching:
            continue  # Still an editorial manuscript; NEVER count as imported.
        t = matching[0]
        topic_id = t["topic_id"]
        if topic_id in attached:
            raise ValueError("TOPIC_ASSIGNED_TO_MULTIPLE_WARDS:"+topic_id)
        attached.add(topic_id)
        if t.get("topic_qa_status") != "PLANNED":
            entry["research_status"] = t.get("topic_qa_status", "RESEARCH")
            continue
        entry["topic_id"] = topic_id
        entry["research_status"] = "PLANNED_RESEARCH_PASS"
        evidence = qa.get(topic_id) or {}
        receipt = (ledger.get("posts") or {}).get(topic_id) or {}
        qa_pass = (evidence.get("status") == "PASS" and
                   evidence.get("seo_score", -1) >= 85 and
                   evidence.get("quality_score", -1) >= 85 and
                   evidence.get("source_sha256") == receipt.get("source_hash") and
                   not evidence.get("errors") and not evidence.get("review"))
        entry["writer_qa_status"] = ("PASS" if qa_pass else
            evidence.get("status") if evidence.get("status") in ("REVIEW", "FAIL")
            else "NOT_VERIFIED_CURRENT_RUN")
        g7 = receipt.get("g7") or {}
        required_g7 = {"wordpress_status","slug","title","category",
                       "ownership_marker","content","permalink",
                       "public_page","indexable","seo_meta"}
        if (entry["writer_qa_status"] == "PASS" and
            receipt.get("phase") == "VERIFIED" and
            receipt.get("expected_status") == "publish" and
            receipt.get("status") == "publish" and
            receipt.get("category_id") == TERM and
            receipt.get("intended_taxonomy_key") == KEY and
            receipt.get("url") == t.get("canonical_target") and
            g7.get("status") == "PASS" and
            g7.get("categories") == [TERM] and
            g7.get("url") == t.get("canonical_target") and
            all(g7.get("checks", {}).get(key) is True for key in required_g7)):
            entry.update(
                publication_status="WORDPRESS_PUBLISHED_G7_PASS",
                wp_post_id=receipt["wp_id"],
                wp_permalink=receipt["url"],
                g7_verified_at=receipt.get("verified_at") or g7.get("checked_at"),
            )
    out["imported_into_topic_factory"] = sum(
        bool(x.get("topic_id")) and x.get("research_status") == "PLANNED_RESEARCH_PASS"
        for x in out["completed"])
    out["published_new_articles"] = sum(
        x.get("publication_status") == "WORDPRESS_PUBLISHED_G7_PASS"
        for x in out["completed"])
    if out["published_new_articles"] > out["imported_into_topic_factory"]:
        raise ValueError("PUBLISHED_EXCEEDS_ADMITTED")
    out["last_reconciled_at"] = now()
    return out


def run(*, persist=False):
    before = load(PATH)
    rows = topics()
    ledger = load("data/state/publication-ledger.json", {"posts": {}})
    qa = {}
    for row in rows:
        if row.get("campaign_id") == CAMPAIGN:
            path = ROOT / "data" / "qa" / (row["topic_id"] + ".json")
            if path.is_file():
                qa[row["topic_id"]] = json.loads(path.read_text(encoding="utf-8"))
    result = reconcile(before, rows, ledger, qa)
    changed = any(result.get(k) != before.get(k) for k in
                  ("completed", "imported_into_topic_factory", "published_new_articles"))
    if persist and changed:
        state = RemoteState()
        state.remember([PATH])
        save(PATH, result)
        state.persist([PATH], "chore: reconcile Hanoi ward G7 progress [skip ci]")
    return {"edited": result["completed_editorial_drafts"],
            "imported": result["imported_into_topic_factory"],
            "g7_published": result["published_new_articles"],
            "changed": changed,
            "persisted": bool(persist and changed)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persist-state", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(persist=args.persist_state), ensure_ascii=False))
