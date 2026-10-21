#!/usr/bin/env python3
"""Read-only fast lane for Excel topics. A proposed NT ID is never an admitted lease."""
import datetime as dt
import re
from common import norm
from research_v2 import validate_sources
from slug_policy import suggested_slug

TOPIC_ID = re.compile(r"^TP-(\d{4})$")
IGNORED = frozenset("xe may dien dap ha noi thue cho theo va cua cac nhu the can duoc khi nao mot hai ba de trong tai voi nhung gi ve gia chi tren".split())
ADMITTED = frozenset(("PLANNED", "PUBLISHED"))


def proposed_id(plan_id):
    match = TOPIC_ID.fullmatch(str(plan_id))
    if not match or not 1 <= int(match.group(1)) <= 1482:
        raise ValueError("Unknown 1482-title plan ID")
    return "NT-09" + match.group(1)


def normalized_tokens(value):
    return {word for word in norm(value).split() if word not in IGNORED and len(word) >= 3}


def reusable_sources(row, registry, *, today=None, limit=3):
    """Only suggest existing, immutable source snapshots; do not invent a new check date."""
    today = today or dt.date.today()
    wanted = normalized_tokens(row.get("title", ""))
    matches = {}
    for topic in registry:
        if topic.get("topic_qa_status") not in ADMITTED or topic.get("taxonomy_key") != row.get("taxonomy_key"):
            continue
        overlap = wanted & normalized_tokens(topic.get("title", ""))
        if not overlap:
            continue
        research = topic.get("research") or {}
        for reference in research.get("external_sources") or []:
            if not isinstance(reference, dict) or validate_sources({"external_sources": [reference]}, today=today):
                continue
            checked = dt.date.fromisoformat(reference["checked_at"])
            if row.get("taxonomy_key") in ("traffic-law", "driving-licence", "legal", "road-law") and (today - checked).days > 90:
                continue
            url = reference["url"]
            candidate = {key: reference[key] for key in (
                "url", "checked_at", "supports", "evidence_text", "source_sha256")}
            candidate["reused_from_topic_id"] = topic["topic_id"]
            score = len(overlap)
            if url not in matches or score > matches[url][0]:
                matches[url] = (score, candidate)
    return [item for _, item in sorted(matches.values(),
              key=lambda pair: (-pair[0], pair[1]["url"]))[:limit]]


def existing_collisions(row, inventory):
    slug = suggested_slug(row["title"])
    title = norm(row["title"])
    return [{key: post.get(key) for key in ("id", "title", "slug", "url", "status")}
            for post in inventory if post.get("slug") == slug or norm(post.get("title") or "") == title][:5]


def build_fastlane(plan_rows, registry, inventory, *, limit=3, today=None):
    """Selection is read-only. Research QA and trusted intake reserve IDs separately."""
    if not 1 <= limit <= 10:
        raise ValueError("Select 1..10 at most")
    by_plan = {}
    by_id = {}
    for topic in registry:
        by_id[topic.get("topic_id")] = topic
        origin = topic.get("title_plan_id") or topic.get("origin_id")
        if origin:
            by_plan.setdefault(str(origin), topic)
    selected, held = [], []
    for row in plan_rows:
        if row.get("status") != "PLANNED" or row["plan_id"] in by_plan:
            continue
        topic_id = proposed_id(row["plan_id"])
        if topic_id in by_id:
            held.append({"plan_id": row["plan_id"], "reason": "NT_ID_ALREADY_OCCUPIED",
                         "proposed_topic_id": topic_id})
            continue
        collisions = existing_collisions(row, inventory)
        if collisions:
            held.append({"plan_id": row["plan_id"], "reason": "WORDPRESS_IDENTITY_COLLISION",
                         "existing_posts": collisions})
            continue
        selected.append({
            "plan_id": row["plan_id"], "title": row["title"],
            "category_id": row["category_id"], "taxonomy_key": row["taxonomy_key"],
            "proposed_topic_id": topic_id, "topic_id_is_reserved": False,
            "research_source_suggestions": reusable_sources(row, registry, today=today),
            "next_action": "Confirm prior source applicability and WordPress intent; submit Research V2 candidate with stable NT ID; Trusted Intake must PASS before Writer claim. Never re-date reused evidence.",
        })
        if len(selected) >= limit:
            break
    return {"count": len(selected), "ready_for_research": selected, "held": held[:limit],
            "publication_authorized": False, "note": "Research suggestions are not approved new claims or live Topic IDs."}
