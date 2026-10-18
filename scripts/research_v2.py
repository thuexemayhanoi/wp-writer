"""Crash-safe, source-evidence-gated research batches for external AI sessions.

No LLM/API calls and no WordPress writes. This CLI operates on research/*
branches and emits verifiable 10-topic candidate batches. A trusted main
workflow independently imports green batches into the canonical Topic Factory.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from common import ROOT, digest, load, norm, now, topics
from intent_guard import IntentIndex
from topic_factory import apply_intent_guard, gate, stamp_factory_posts

BRANCH = re.compile(r'^research/([a-z][a-z0-9_-]{3,70})$')
TOPIC = re.compile(r'^NT-[0-9]{6}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
MAX_BATCH_BYTES = 400_000
PEER_MAX_AGE = 6 * 3600  # a pushed batch that intake has not registered after six hours is stale, not pending
CANDIDATE_FILE = re.compile(r'^data/candidates/([a-z][a-z0-9_-]{3,70})-[0-9]{4}\.jsonl$')
MAX_CHECKPOINT_BYTES = 120_000
MAX_SOURCES = 12


def session_name(branch):
    match = BRANCH.fullmatch(branch)
    if not match:
        raise ValueError('Branch must be research/<lowercase-stable-session> (4-71 chars)')
    return match.group(1)


def checkpoint_path(branch):
    return 'data/research/checkpoints/' + session_name(branch) + '.json'


def batch_pattern(branch):
    return re.compile(r'^data/candidates/' + re.escape(session_name(branch)) +
                      r'-([0-9]{4})\.jsonl$')


def git_read(*args):
    proc = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode:
        raise ValueError('Git research command failed: ' + ' '.join(args[:2]))
    # Porcelain status uses leading XY columns (e.g. ' M path'). Stripping
    # whitespace destroys those columns and breaks batch 2+ checkpoints.
    return proc.stdout.rstrip('\n')


def safe_batch_path(branch, path):
    return bool(batch_pattern(branch).fullmatch(path))


def parse_batch(raw, name):
    if len(raw.encode('utf-8')) > MAX_BATCH_BYTES:
        raise ValueError('Research batch exceeds 400 kB: ' + name)
    values = [x for x in raw.splitlines() if x.strip()]
    if not 1 <= len(values) <= 10:
        raise ValueError('Research batch must contain 1–10 real topics: ' + name)
    results = []
    for line in values:
        topic = json.loads(line)
        if not isinstance(topic, dict):
            raise ValueError('Research topic must be a JSON object')
        results.append(topic)
    return results


def validate_sources(research, *, today=None):
    """Verify provenance *metadata*; do not claim network-checked source truth."""
    errors = []
    today = today or dt.date.today()
    refs = research.get('external_sources') if isinstance(research, dict) else None
    if not isinstance(refs, list) or not (1 <= len(refs) <= MAX_SOURCES):
        return ['RESEARCH_SOURCE_COUNT: at least one direct HTTPS reference required']
    hosts, urls = set(), set()
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            errors.append('RESEARCH_SOURCE_SCHEMA:' + str(index))
            continue
        raw_url = str(ref.get('url', ''))
        parsed = urlsplit(raw_url)
        host = (parsed.hostname or '').lower()
        if (parsed.scheme != 'https' or not host or parsed.username or
                parsed.password or parsed.port not in (None, 443) or
                host in ('localhost', '127.0.0.1') or
                host.endswith('.local') or host == 'news.google.com'):
            errors.append('RESEARCH_SOURCE_NOT_DIRECT_HTTPS:' + str(index))
        if raw_url in urls:
            errors.append('RESEARCH_SOURCE_DUPLICATED_URL:' + str(index))
        urls.add(raw_url)
        if host:
            hosts.add(host)
        try:
            checked = dt.date.fromisoformat(str(ref.get('checked_at', '')))
            age = (today - checked).days
            if age < 0 or age > 365:
                raise ValueError('stale/future')
        except ValueError:
            errors.append('RESEARCH_SOURCE_DATE:' + str(index))
        if len(str(ref.get('supports', '')).strip()) < 20:
            errors.append('RESEARCH_SOURCE_CLAIM_UNSPECIFIC:' + str(index))
        if len(str(ref.get('evidence_text', '')).strip()) < 20:
            errors.append('RESEARCH_SOURCE_EXCERPT_MISSING:' + str(index))
        if not SHA.fullmatch(str(ref.get('source_sha256', ''))):
            errors.append('RESEARCH_SOURCE_SNAPSHOT_SHA_MISSING:' + str(index))
    # Independent sources are encouraged, not required for narrowly scoped
    # research backed by a genuine authoritative primary reference.
    return errors


def validate_candidates(rows, *, incumbent=None, inventory=None, taxonomy=None,
                        discovery=None, accepted=None, today=None):
    """Four QA phases: source, intent/collision, content gap, taxonomy/schema.

    Intent collisions are checked against EVERY WordPress item and EVERY topic row in the
    factory (any status except REJECTED), and among the new rows themselves.
    """
    incumbent = topics() if incumbent is None else incumbent
    inventory = (stamp_factory_posts(load('data/existing-content-inventory.json', {}).get('items', []),
                                     load('data/state/publication-ledger.json', {}))
                 if inventory is None else inventory)
    taxonomy = load('data/taxonomy.json', {}).get('items', []) if taxonomy is None else taxonomy
    discovery = load('data/state/topic-discovery-ledger.json', {'proposals': {}}) if discovery is None else discovery
    accepted = load('data/state/research-intake-ledger.json', {'batches': {}}) if accepted is None else accepted
    findings = []
    ids = [t.get('topic_id') for t in rows]
    origins = [t.get('origin_id') for t in rows if str(t.get('origin_id', '')).startswith('NTD-')]
    if len(ids) != len(set(ids)) or len(origins) != len(set(origins)):
        raise ValueError('Duplicate research topic ID or discovery origin in batch')
    current = {t['topic_id'] for t in incumbent}
    if any(not isinstance(t.get('topic_id'), str) or not TOPIC.fullmatch(t['topic_id']) for t in rows):
        raise ValueError('Research must use an unused NT-XXXXXX ID')
    if current.intersection(ids):
        raise ValueError('Research attempted to overwrite a canonical topic ID')
    if len(current) + len(rows) > load('config/production-policy.json')['approved_capacity']:
        raise ValueError('Approved intake capacity reached; research is not a publish authorization')
    already_origin = {str(x.get('origin_id')) for x in incumbent}
    everything = incumbent + rows
    intent_index = IntentIndex(inventory, everything)
    new_ids = set(ids)
    for t in rows:
        errors = []
        review = []
        research = t.get('research') or {}
        if not isinstance(research, dict):
            research = {}
        errors.extend(validate_sources(research, today=today))
        # A researched candidate must already satisfy the immutable Nguyen Tu
        # WordPress writer contract, not just the lighter discovery lead format.
        if t.get('word_target_min') != 1600 or t.get('word_target_max') != 5000:
            errors.append('RESEARCH_WORD_RANGE_MUST_BE_1600_TO_5000')
        if t.get('topic_role') != 'supporting':
            review.append('RESEARCH_NEW_PILLAR_OR_COMMERCIAL_HUB_NEEDS_OWNER_ARCHITECTURE')
        if not all(str(t.get(k) or '').strip() for k in ('pillar', 'hub', 'silo')):
            review.append('RESEARCH_HUB_SILO_ARCHITECTURE_MISSING')
        if (t.get('writer_claim') or t.get('wp_post_id') or
                t.get('wp_permalink') or t.get('source_hash') or
                t.get('publication_status') not in (None, 'NOT_SUBMITTED') or
                t.get('topic_qa_status') not in (None, 'RESEARCH')):
            errors.append('RESEARCH_CANDIDATE_MUST_NOT_IMPERSONATE_PUBLISHED_OR_CLAIMED_POST')
        links = t.get('internal_link_candidates')
        if not isinstance(links, list) or not links:
            review.append('RESEARCH_INTERNAL_LINK_HUB_CANDIDATES_MISSING')
        else:
            published = {p.get('url') for p in inventory if p.get('status') == 'publish'}
            if inventory and not any(url in published for url in links):
                review.append('RESEARCH_INTERNAL_LINK_TARGET_NOT_IN_PUBLIC_WP_INVENTORY')

        origin = str(t.get('origin_id', ''))
        if origin.startswith('NTD-'):
            lead = discovery.get('proposals', {}).get(origin)
            if not lead:
                errors.append('RESEARCH_DISCOVERY_ORIGIN_UNKNOWN')
            elif lead.get('taxonomy_key') != t.get('taxonomy_key'):
                errors.append('RESEARCH_DISCOVERY_TAXONOMY_CONFLICT')
        if origin and origin in already_origin:
            errors.append('RESEARCH_DISCOVERY_ORIGIN_ALREADY_USED')
        if not research.get('reviewer') or not research.get('difference_summary') or not research.get('usefulness'):
            review.append('RESEARCH_EDITORIAL_EVIDENCE_MISSING')
        if not research.get('scope_exclusions') or not t.get('intent_key'):
            review.append('RESEARCH_INTENT_SCOPE_MISSING')
        verdict = apply_intent_guard(gate(t, everything, inventory, taxonomy), t, everything,
                                     inventory, new_ids, intent_index)
        errors.extend(verdict['errors'])
        review.extend(verdict['review'])
        findings.append({'topic_id': t['topic_id'],
            'status': 'FAIL' if errors else 'REVIEW' if review else 'PASS',
            'errors': errors, 'review': review})
    return findings


def read_checkpoint(raw, branch):
    if len(raw.encode('utf-8')) > MAX_CHECKPOINT_BYTES:
        raise ValueError('Research checkpoint too large')
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('version') != 1 or value.get('branch') != branch:
        raise ValueError('Checkpoint version/branch does not match research session')
    batches = value.get('batches')
    if not isinstance(batches, list) or not batches:
        raise ValueError('Checkpoint needs at least one research batch')
    paths = set()
    for number, entry in enumerate(batches, 1):
        path = entry.get('path', '')
        if not safe_batch_path(branch, path) or int(batch_pattern(branch).fullmatch(path).group(1)) != number:
            raise ValueError('Non-contiguous or foreign research batch path')
        if path in paths or not SHA.fullmatch(str(entry.get('sha256', ''))):
            raise ValueError('Duplicate research batch or missing hash')
        if type(entry.get('count')) is not int or not 1 <= entry['count'] <= 10:
            raise ValueError('Invalid checkpoint topic count')
        if entry['count'] != 10 and not (entry.get('final') is True and number == len(batches)):
            raise ValueError('Only explicitly final batch may contain 1–9 topics')
        paths.add(path)
    return value


def verify_files(branch, *, fetch=None, check_topic_qa=True):
    """Validate all checkpointed bytes; accepted old batches must be immutable."""
    cp = checkpoint_path(branch)
    if fetch is None:
        fetch = lambda p: (ROOT / p).read_text(encoding='utf-8')
    obj = read_checkpoint(fetch(cp), branch)
    accepted = load('data/state/research-intake-ledger.json', {'batches': {}})
    new = []
    for b in obj['batches']:
        raw = fetch(b['path'])
        sha = digest(raw)
        if sha != b['sha256']:
            raise ValueError('Research checkpoint hash mismatch: ' + b['path'])
        rows = parse_batch(raw, b['path'])
        if len(rows) != b['count']:
            raise ValueError('Research checkpoint count mismatch: ' + b['path'])
        previous = accepted.get('batches', {}).get(b['path'])
        if previous:
            if previous.get('sha256') != sha:
                raise ValueError('An already-ingested research batch was edited')
        else:
            new.extend(rows)
    blocked = []
    if check_topic_qa and new:
        result = validate_candidates(new)
        blocked = [r for r in result if r['status'] != 'PASS']
        # One failing topic never blocks the passing ones: only a batch with nothing usable is refused.
        # The trusted intake imports PASS topics as PLANNED and registers the others as RESEARCH/REJECTED.
        if len(blocked) == len(result):
            raise ValueError('RESEARCH_QA_BLOCKED: ' + json.dumps(blocked[:5], ensure_ascii=False))
    return {'branch': branch, 'batches': len(obj['batches']), 'new_topics': len(new),
            'accepted_topics': len(new) - len(blocked), 'blocked_topics': blocked,
            'total_topics': sum(b['count'] for b in obj['batches']),
            'batch_paths': [b['path'] for b in obj['batches']],
            'checkpoint_path': cp}


def verify_branch(branch, base='origin/main'):
    """Fail read-only QA when a researcher touches ANY protected project file."""
    session_name(branch)
    changed = git_read('diff', '--name-only', base + '...HEAD').splitlines()
    cp = checkpoint_path(branch)
    if cp not in changed:
        raise ValueError('Research checkpoint missing from changed files')
    if not all(safe_batch_path(branch, p) or p == cp for p in changed):
        raise ValueError('FORBIDDEN_RESEARCH_PATH: research branch changed privileged files')
    for path in changed:
        stat = git_read('diff', '--name-status', base + '...HEAD', '--', path)
        if stat.startswith(('D\t', 'R')):
            raise ValueError('Research batch/checkpoint removal or rename forbidden')
    result = verify_files(branch)
    if not result['new_topics']:
        # A checkpoint-only push may intentionally retrigger a stale ingester.
        result['state'] = 'ALREADY_ACCEPTED_OR_CHECKPOINT_ONLY'
    elif result['blocked_topics']:
        result['state'] = 'RESEARCH_QA_PARTIAL'
    else:
        result['state'] = 'RESEARCH_QA_PASS'
    return result


def checkpoint(branch, final=False):
    """Refresh batch hashes; never auto-generate research text or sources."""
    slug = session_name(branch)
    files = sorted((ROOT / 'data/candidates').glob(slug + '-[0-9][0-9][0-9][0-9].jsonl'))
    if not files:
        raise ValueError('No real research batches saved in this session')
    previous = load(checkpoint_path(branch), {'batches': []})
    locked = {b['path']: b for b in previous.get('batches', [])}
    batches = []
    for i, p in enumerate(files, 1):
        rel = p.relative_to(ROOT).as_posix()
        if not safe_batch_path(branch, rel) or not rel.endswith(f'{i:04d}.jsonl'):
            raise ValueError('Research batches must be sequentially numbered')
        raw = p.read_text(encoding='utf-8')
        sha = digest(raw)
        if rel in locked and locked[rel]['sha256'] != sha:
            raise ValueError('Existing checkpointed batch is immutable')
        rows = parse_batch(raw, rel)
        is_final = bool(locked.get(rel, {}).get('final')) or (final and i == len(files))
        batches.append({'path': rel, 'sha256': sha, 'count': len(rows), 'final': is_final})
    obj = {'version': 1, 'branch': branch, 'session': slug, 'batches': batches,
           'updated_at': now(), 'status': 'RESEARCHED_NOT_INGESTED'}
    read_checkpoint(json.dumps(obj), branch)
    dest = ROOT / checkpoint_path(branch)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return verify_files(branch)


def push(branch):
    """Publish only own research files; fail rather than force-push or fake SAVED."""
    if git_read('branch', '--show-current') != branch:
        raise ValueError('Checkout own research branch before pushing')
    result = verify_files(branch)
    allowed = set(result['batch_paths'] + [result['checkpoint_path']])
    dirty = git_read('status', '--porcelain', '--untracked-files=all').splitlines()
    touched = set()
    for item in dirty:
        name = item[3:]
        if ' -> ' in name or name not in allowed or item[:2].strip() == 'D':
            raise ValueError('Research push attempted to change an unrelated/deleted file')
        touched.add(name)
    if touched:
        git_read('add', '--', *sorted(touched))
        git_read('commit', '-m', 'research: checkpoint validated ten-topic batch')
    head = git_read('rev-parse', 'HEAD')
    git_read('push', 'origin', 'HEAD:refs/heads/' + branch)
    remote = git_read('ls-remote', 'origin', 'refs/heads/' + branch).split()
    if not remote or remote[0] != head:
        raise RuntimeError('NOT_SAVED: remote branch did not verify push commit')
    result['state'] = 'SAVED'
    result['commit_sha'] = head
    return result


def resume(branch, apply=False):
    """Recover only from the remote research branch, never from chat memory."""
    session_name(branch)
    if apply:
        if git_read('status', '--porcelain'):
            raise ValueError('Cannot recover into a dirty repository')
        git_read('fetch', 'origin', 'main', branch)
        exists = subprocess.run(['git', 'show-ref', '--verify', '-q', 'refs/heads/' + branch],
                                cwd=ROOT).returncode == 0
        if exists:
            git_read('switch', branch)
            if git_read('rev-parse', 'HEAD') != git_read('rev-parse', 'refs/remotes/origin/' + branch):
                raise ValueError('Local research branch diverged; do not reset or force-push')
        else:
            git_read('switch', '-c', branch, '--track', 'origin/' + branch)
        return verify_files(branch)
    remote = git_read('ls-remote', 'origin', 'refs/heads/' + branch).split()
    if not remote:
        raise ValueError('Remote session not found: start a new research branch')
    return {'branch': branch, 'remote_sha': remote[0], 'state': 'REMOTE_SESSION_EXISTS',
            'next_step': 'resume --branch ' + branch + ' --apply'}


def research_hints(limit=10):
    """Read-only bounded AI research queue; RSS leads are NOT factual sources."""
    if not 1 <= limit <= 10:
        raise ValueError('Research hints must be 1–10 items')
    consumed = {str(t.get('origin_id')) for t in topics()}
    submissions = set()
    for p in (ROOT / 'data/candidates').glob('*.jsonl'):
        try:
            submissions.update(str(row.get('origin_id')) for row in
                               parse_batch(p.read_text(encoding='utf-8'), p.name))
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    leads = []
    for p in sorted((ROOT / 'data/research/auto').glob('batch-*.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            proposal = json.loads(line)
            origin = str(proposal.get('proposal_id', ''))
            if (not origin.startswith('NTD-') or origin in consumed
                    or origin in submissions):
                continue
            leads.append({
                'origin_id': origin,
                'taxonomy_key': proposal.get('taxonomy_key'),
                'title_hint': proposal.get('title'),
                'questions': proposal.get('research_questions', []),
                'source_signals': proposal.get('source_signals', [])[:2],
                'status': 'NEEDS_EXTERNAL_AI_FACT_RESEARCH_NOT_READY_TO_WRITE',
            })
            if len(leads) >= limit:
                return leads
    return leads


def refill_plan():
    """The open research order, its category quotas and the next batch of ten (read-only, offline)."""
    import datetime
    import refill_controller
    inputs = refill_controller.build_inputs()
    _, request, _ = refill_controller.assess(at=datetime.datetime.now(datetime.timezone.utc), **inputs)
    order = request.get('order') or {}
    return {'state': request['state'], 'ready_stock': request['ready_stock'],
            'trigger_below_ready': request['trigger_below_ready'],
            'capacity_remaining': request['capacity_remaining'],
            'order': {k: order.get(k) for k in ('id', 'round', 'target_min', 'target_max', 'accepted_so_far',
                                                'remaining_to_min', 'batches_still_needed')},
            'next_batch_categories': order.get('next_batch_categories', {}),
            'category_quotas': order.get('category_quotas', []),
            'dedupe_universe': request.get('dedupe_universe'),
            'how_to_research': request.get('how_to_research'),
            'instruction': request.get('instruction')}


def peer_rows(own_session=None, *, clock=None):
    """Rows other researchers pushed to research/* that trusted intake has not registered yet.

    A researcher's local intent-check only sees the registry, so two researchers working in parallel can pick the
    same idea (NT-000287 repeated NT-000226). A pushed row waits for intake as a PEER_PENDING topic that owns its
    intent exactly like an admitted one, so whoever pushes second retitles. Branches whose head is older than
    PEER_MAX_AGE are stale, not pending. Never raises: offline, the check simply runs without peers.
    Returns (rows, {session: row count} or {'unavailable': reason}).
    """
    try:
        git_read('fetch', '--no-tags', '--quiet', 'origin', '+refs/heads/research/*:refs/remotes/origin/research/*')
        refs = git_read('for-each-ref', '--format=%(refname) %(committerdate:unix)',
                        'refs/remotes/origin/research/').splitlines()
    except (ValueError, OSError) as exc:
        return [], {'unavailable': str(exc)[:120]}
    known = {t['topic_id'] for t in topics()}
    now_ts = time.time() if clock is None else clock
    pending, sessions = [], {}
    for line in refs:
        ref, _, stamp = line.partition(' ')
        session = ref.rpartition('refs/remotes/origin/research/')[2]
        if not session or session == own_session or not stamp.isdigit() or now_ts - int(stamp) > PEER_MAX_AGE:
            continue
        try:
            names = git_read('ls-tree', '-r', '--name-only', ref, '--', 'data/candidates').splitlines()
            for name in names:
                match = CANDIDATE_FILE.fullmatch(name)
                if not match or match.group(1) != session:
                    continue
                for row in parse_batch(git_read('show', ref + ':' + name), name):
                    if isinstance(row.get('topic_id'), str) and row['topic_id'] not in known:
                        pending.append(dict(row, topic_qa_status='PEER_PENDING'))
                        sessions[session] = sessions.get(session, 0) + 1
        except (ValueError, OSError):
            continue  # an unreadable peer branch never blocks the check
    return pending, sessions


def intent_check(path, peers=True):
    """Pre-push search-intent screen for a candidate file: no sources needed, any row count."""
    from intent_guard import assess_topic
    raw = (ROOT / path).read_text(encoding='utf-8')
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    incumbent = topics()
    inventory = stamp_factory_posts(load('data/existing-content-inventory.json', {}).get('items', []),
                                    load('data/state/publication-ledger.json', {}))
    own = re.fullmatch(r'(.+)-[0-9]{4}\.jsonl', Path(path).name)
    pending, from_sessions = peer_rows(own.group(1) if own else None) if peers else ([], {'skipped': 'peers off'})
    everything = incumbent + pending + rows
    index = IntentIndex(inventory, everything)
    new_ids = {t['topic_id'] for t in rows}
    report = []
    for t in rows:
        found = assess_topic(t, everything, inventory, new_ids=new_ids, index=index)
        report.append({'topic_id': t['topic_id'], 'title': t.get('title'),
                       'verdict': 'FAIL' if found['errors'] else 'REVIEW' if found['review'] else 'PASS',
                       'errors': found['errors'], 'review': found['review'],
                       'nearest': [{k: m[k] for k in ('id', 'severity', 'title', 'weighted_jaccard', 'shared_terms',
                                                      'only_in_candidate', 'only_in_existing', 'same_question_type')}
                                   for m in found['matches'][:3]]})
    return {'file': path, 'rows': len(rows),
            'fail': sum(r['verdict'] == 'FAIL' for r in report),
            'review': sum(r['verdict'] == 'REVIEW' for r in report), 'topics': report,
            'peers': {'pending_rows': len(pending), 'from': from_sessions},
            'how_to_resolve': ['FAIL: retitle and re-scope; it can never be waived. A collision with a topic of '
                               'another researcher who pushed first (peers) is resolved the same way.',
                               'REVIEW: add research.resolved_intent_collisions = {"<id>": "<why the reader '
                               'question differs, 40+ chars>"}; for a WordPress page (WP<id>) also record its '
                               'current content hash in research.reviewed_content_hashes."']}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('checkpoint', 'check', 'verify-branch', 'push', 'resume', 'hints', 'plan', 'intent-check'):
        p = sub.add_parser(command)
        if command == 'hints':
            p.add_argument('--limit', type=int, default=10)
        elif command == 'plan':
            pass
        elif command == 'intent-check':
            p.add_argument('--file', required=True)
            p.add_argument('--no-peers', action='store_true',
                           help='skip the other researchers\' pushed-but-not-ingested rows')
        else:
            p.add_argument('--branch', required=True)
        if command == 'checkpoint':
            p.add_argument('--final', action='store_true')
        if command == 'verify-branch':
            p.add_argument('--base', default='origin/main')
        if command == 'resume':
            p.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.command == 'hints':
        output = {'research_hints': research_hints(args.limit),
                  'source_verification': 'PENDING_EXTERNAL_AI',
                  'not_approved_topics': True}
    elif args.command == 'plan':
        output = refill_plan()
    elif args.command == 'intent-check':
        output = intent_check(args.file, peers=not args.no_peers)
    elif args.command == 'checkpoint':
        output = checkpoint(args.branch, final=args.final)
    elif args.command == 'verify-branch':
        output = verify_branch(args.branch, args.base)
    elif args.command == 'push':
        output = push(args.branch)
    elif args.command == 'resume':
        output = resume(args.branch, args.apply)
    else:
        output = verify_files(args.branch)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
