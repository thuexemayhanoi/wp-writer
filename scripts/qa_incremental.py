"""Incremental QA plan: evaluate only drafts that are new or really changed; keep every still-valid stored record.

The QA sweep used to re-evaluate every draft on every run, including the hundreds already VERIFIED public on
WordPress. That is O(drafts x (drafts + inventory)) and exceeds the Actions time limit long before 2,000 articles.

A stored record in data/qa/<ID>.json is reused, never re-evaluated, when
  FROZEN  the ledger says the article is VERIFIED on WordPress with exactly this source hash. A published article is
          immutable (no update endpoint exists); re-scoring it changes nothing. The record is kept whatever its age.
  CACHED  the draft bytes, the QA rules and the topic row are the same as when the record was produced (the record
          carries that `incremental_key`), the record is younger than `incremental_max_age_hours`, and it is not a
          transient (INFRA_PENDING) hold that the self-healing gates want to re-check.
Everything else is FRESH: evaluated again by qa.py. The sweep never lowers a threshold: a reused record is the very
record the same code produced earlier, hash-checked by qa_gate.validate_complete exactly like a fresh one. The
Publisher still re-evaluates each unpublished article live (sources, links, current inventory) before any POST, so a
cached offline PASS is never the last word before WordPress.
"""
import datetime as dt
import json

from common import ROOT, digest, load, topics

VALID = ('PASS', 'FAIL', 'REVIEW')
DEFAULT_MAX_AGE_HOURS = 24


def rules_digest(rules):
    return digest(json.dumps(rules, sort_keys=True))


def topic_digest(topic):
    """The part of a topic row that changes a QA verdict; research notes and timestamps do not."""
    keys = ('topic_id', 'title', 'primary_keyword', 'search_intent', 'intent_key', 'taxonomy_key',
            'canonical_target', 'proposed_slug', 'topic_qa_status', 'hold', 'wp_post_id')
    return digest(json.dumps({k: topic.get(k) for k in keys}, ensure_ascii=False, sort_keys=True))


def incremental_key(raw_sha, rules_sha, topic):
    return digest(raw_sha + ':' + rules_sha + ':' + (topic_digest(topic) if topic else 'no-topic'))


def _age_hours(record, at):
    try:
        stamped = dt.datetime.fromisoformat(str(record.get('at')).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    if stamped.tzinfo is None:
        stamped = stamped.replace(tzinfo=dt.timezone.utc)
    return (at - stamped).total_seconds() / 3600


def decide(topic_id, raw_sha, record, topic, ledger_record, rules_sha, max_age_hours, at):
    """Return ('FROZEN'|'CACHED'|'FRESH', reason)."""
    if not isinstance(record, dict) or record.get('topic_id') != topic_id:
        return 'FRESH', 'no stored record'
    if record.get('status') not in VALID or record.get('source_sha256') != raw_sha:
        return 'FRESH', 'stored record is for another draft version'
    if (ledger_record or {}).get('phase') == 'VERIFIED' and ledger_record.get('source_hash') == raw_sha:
        return 'FROZEN', 'VERIFIED on WordPress with this exact source hash'
    if topic is None:
        return 'FRESH', 'draft has no registered topic'
    if record.get('incremental_key') != incremental_key(raw_sha, rules_sha, topic):
        return 'FRESH', 'rules or topic row changed since the stored record'
    if (record.get('triage') or {}).get('hold_class') == 'INFRA_PENDING':
        return 'FRESH', 'transient hold is re-checked by the self-healing gates'
    age = _age_hours(record, at)
    if age is None or age < 0 or age > max_age_hours:
        return 'FRESH', 'stored record older than %s h' % max_age_hours
    return 'CACHED', 'same draft, rules and topic row within %s h' % max_age_hours


def plan(root=None, rows=None, rules=None, ledger=None, at=None):
    """Classify every draft under root/posts/drafts. Returns {'frozen','cached','fresh'} lists plus per-draft detail."""
    root = ROOT if root is None else (root if hasattr(root, 'glob') else ROOT / str(root))
    rows = rows if rows is not None else topics()
    rules = rules if rules is not None else load('config/qa-rules.json')
    ledger = ledger if ledger is not None else (load('data/state/publication-ledger.json', {}) or {})
    at = at or dt.datetime.now(dt.timezone.utc)
    rules_sha = rules_digest(rules)
    max_age = float(rules.get('incremental_max_age_hours', DEFAULT_MAX_AGE_HOURS))
    by_id = {t['topic_id']: t for t in rows}
    posts = ledger.get('posts') or {}
    result = {'frozen': [], 'cached': [], 'fresh': [], 'detail': {}, 'rules_sha256': rules_sha}
    for path in sorted((root / 'posts/drafts').glob('NT-*.md')):
        topic_id = path.stem
        raw_sha = digest(path.read_bytes())
        record_path = root / 'data/qa' / (topic_id + '.json')
        record = None
        if record_path.is_file():
            try:
                record = json.loads(record_path.read_text(encoding='utf-8'))
            except ValueError:
                record = None
        verdict, reason = decide(topic_id, raw_sha, record, by_id.get(topic_id), posts.get(topic_id), rules_sha,
                                 max_age, at)
        result[verdict.lower()].append(topic_id)
        result['detail'][topic_id] = {'verdict': verdict, 'reason': reason}
    return result


def enabled(rules=None):
    rules = rules if rules is not None else load('config/qa-rules.json') or {}
    return rules.get('incremental_sweep') is True


if __name__ == '__main__':
    p = plan()
    print(json.dumps({'frozen': len(p['frozen']), 'cached': len(p['cached']), 'fresh': len(p['fresh']),
                      'fresh_ids': p['fresh'][:20]}, ensure_ascii=False))
