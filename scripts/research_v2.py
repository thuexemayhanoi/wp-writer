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
from pathlib import Path
from urllib.parse import urlsplit

from common import ROOT, digest, load, norm, now, topics
from topic_factory import gate

BRANCH = re.compile(r'^research/([a-z][a-z0-9_-]{3,70})$')
TOPIC = re.compile(r'^NT-[0-9]{6}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
MAX_BATCH_BYTES = 400_000
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
    return proc.stdout.strip()


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
    if not isinstance(refs, list) or not (2 <= len(refs) <= MAX_SOURCES):
        return ['RESEARCH_SOURCE_COUNT: two independent HTTPS references required']
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
    if len(hosts) < 2:
        errors.append('RESEARCH_SOURCE_HOSTS_NOT_INDEPENDENT')
    return errors


def validate_candidates(rows, *, incumbent=None, inventory=None, taxonomy=None,
                        discovery=None, accepted=None, today=None):
    """Four QA phases: source, intent/collision, content gap, taxonomy/schema."""
    incumbent = topics() if incumbent is None else incumbent
    inventory = load('data/existing-content-inventory.json', {}).get('items', []) if inventory is None else inventory
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
    for t in rows:
        errors = []
        review = []
        research = t.get('research') or {}
        if not isinstance(research, dict):
            research = {}
        errors.extend(validate_sources(research, today=today))
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
        verdict = gate(t, incumbent + rows, inventory, taxonomy)
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
    if check_topic_qa and new:
        result = validate_candidates(new)
        blocked = [r for r in result if r['status'] != 'PASS']
        if blocked:
            raise ValueError('RESEARCH_QA_BLOCKED: ' + json.dumps(blocked[:5], ensure_ascii=False))
    return {'branch': branch, 'batches': len(obj['batches']), 'new_topics': len(new),
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
        rows = parse_batch(raw, rel)
        sha = digest(raw)
        if rel in locked and locked[rel]['sha256'] != sha:
            raise ValueError('Existing checkpointed batch is immutable')
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


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('checkpoint', 'check', 'verify-branch', 'push', 'resume'):
        p = sub.add_parser(command)
        p.add_argument('--branch', required=True)
        if command == 'checkpoint':
            p.add_argument('--final', action='store_true')
        if command == 'verify-branch':
            p.add_argument('--base', default='origin/main')
        if command == 'resume':
            p.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.command == 'checkpoint':
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
