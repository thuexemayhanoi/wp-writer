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


def reconcile(progress, rows, ledger, qa=None, inventory=None, external_evidence=None):
    """Return a new checkpoint using only independently corroborated records."""
    qa = qa or {}
    inventory = inventory or []
    external_evidence = (external_evidence or {}).get("posts") or {}
    out = json.loads(json.dumps(progress, ensure_ascii=False))
    if out.get("campaign") != CAMPAIGN or out.get("taxonomy_key") != KEY:
        raise ValueError("WRONG_WARD_CAMPAIGN_REGISTRY")
    if out.get("wordpress_category_id") != TERM or out.get("wordpress_parent_category_id") != 162:
        raise ValueError("HANOI_WARD_CATEGORY_UNVERIFIED")
    if len(out.get("completed", [])) != out.get("completed_editorial_drafts"):
        raise ValueError("WRONG_EDITORIAL_COUNT")
    known = {t["topic_id"]: t for t in rows}
    # Thresholds come from the one QA configuration (owner order 2026-10-20: 76/100), never a copy of the number.
    rules = load("config/qa-rules.json", {}) or {}
    seo_min = rules.get("seo_min", 85)
    quality_min = rules.get("quality_min", 85)
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
        # A pre-existing WordPress post is a G4 collision, never a new receipt.
        entry.pop("existing_wp_collision", None)
        if entry.get("publication_status") in ("EXISTING_WORDPRESS_NEEDS_RECONCILIATION", "WORDPRESS_EXISTING_LIVE_VERIFIED"):
            entry["publication_status"] = "GITHUB_EDITORIAL_ONLY"
        matches = [post for post in inventory
                   if post.get("status") == "publish" and
                   (post.get("url") == t.get("canonical_target") or
                    (t.get("proposed_slug") and post.get("slug") == t["proposed_slug"])) and
                   post.get("id") != receipt.get("wp_id")]
        qa_pass = (evidence.get("status") == "PASS" and
                   evidence.get("seo_score", -1) >= seo_min and
                   evidence.get("quality_score", -1) >= quality_min and
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
        elif matches:
            proof = external_evidence.get(topic_id) or {}
            candidate = matches[0] if len(matches) == 1 else {}
            # A separately authenticated WP REST proof establishes that the
            # pre-existing post is already published for this ward. This is
            # NOT the factory's G7 receipt and cannot be entered in its ledger.
            verified_external = bool(
                len(matches) == 1 and
                proof.get("verification_method") == "authenticated_wp_rest" and
                proof.get("wp_post_id") == candidate.get("id") and
                proof.get("status") == "publish" and
                proof.get("url") == t.get("canonical_target") and
                proof.get("canonical") == t.get("canonical_target") and
                proof.get("title") == t.get("title") and
                proof.get("category_ids") == [TERM] and
                proof.get("robots_index") == "index" and
                proof.get("public_http") == 200 and
                proof.get("verified_at") and
                candidate.get("url") == t.get("canonical_target") and
                (not candidate.get("categories") or candidate.get("categories") == [TERM])
            )
            if verified_external:
                entry.update(
                    publication_status="WORDPRESS_EXISTING_LIVE_VERIFIED",
                    wp_post_id=proof["wp_post_id"],
                    wp_permalink=proof["url"],
                    existing_live_verified_at=proof["verified_at"],
                )
                continue
            entry["publication_status"] = "EXISTING_WORDPRESS_NEEDS_RECONCILIATION"
            entry["existing_wp_collision"] = {
                "match_count": len(matches),
                "wp_ids": [post["id"] for post in matches],
                "urls": [post.get("url") for post in matches],
                "category_ids": [post.get("categories") for post in matches],
                "warning": "Verify existing post taxonomy and SEO; never duplicate WordPress content or forge a factory G7 receipt.",
            }
    out["imported_into_topic_factory"] = sum(
        bool(x.get("topic_id")) and x.get("research_status") == "PLANNED_RESEARCH_PASS"
        for x in out["completed"])
    out["published_new_articles"] = sum(
        x.get("publication_status") == "WORDPRESS_PUBLISHED_G7_PASS"
        for x in out["completed"])
    out["published_existing_articles"] = sum(
        x.get("publication_status") == "WORDPRESS_EXISTING_LIVE_VERIFIED"
        for x in out["completed"])
    out["published_live_ward_articles"] = (
        out["published_new_articles"] + out["published_existing_articles"])
    out["existing_wordpress_collisions"] = sum(
        x.get("publication_status") == "EXISTING_WORDPRESS_NEEDS_RECONCILIATION"
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
    inventory = load("data/existing-content-inventory.json", {}).get("items", [])
    external_evidence = load("editorial/seo-51-phuong/existing-live-evidence.json", {})
    result = reconcile(before, rows, ledger, qa, inventory, external_evidence)
    changed = any(result.get(k) != before.get(k) for k in
                  ("completed", "imported_into_topic_factory", "published_new_articles", "published_existing_articles", "published_live_ward_articles", "existing_wordpress_collisions"))
    if persist and changed:
        state = RemoteState()
        state.remember([PATH])
        save(PATH, result)
        state.persist([PATH], "chore: reconcile Hanoi ward G7 progress [skip ci]")
    return {"edited": result["completed_editorial_drafts"],
            "imported": result["imported_into_topic_factory"],
            "g7_published": result["published_new_articles"],
            "existing_post_collisions": result["existing_wordpress_collisions"],
            "existing_wp_published": result["published_existing_articles"],
            "published_ward_total": result["published_live_ward_articles"],
            "changed": changed,
            "persisted": bool(persist and changed)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persist-state", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(persist=args.persist_state), ensure_ascii=False))
