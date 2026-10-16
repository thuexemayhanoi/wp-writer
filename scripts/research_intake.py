"""Trusted-main intake of QA-verified research/ branch batches.

Triggered only after a successful read-only Research QA *push*, not after a PR.
Untrusted research data is parsed as JSON and validated using TRUSTED main
Python code. Candidate intake never touches WordPress or Production settings.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

from common import ROOT, digest, git, load, now, save, topics
from git_state import RemoteState
from research_v2 import (
    checkpoint_path, parse_batch, read_checkpoint, safe_batch_path,
    session_name, validate_candidates, MAX_BATCH_BYTES
)
from topic_factory import run as promote_candidates


LEDGER = 'data/state/research-intake-ledger.json'
REFILL = 'data/state/refill-ledger.json'
TOUCHED = [
    'data/topics.jsonl',
    'data/taxonomy.json',
    'reports/topic-qa.json',
    'reports/refill-request.json',
    LEDGER,
    REFILL,
]


def git_checked(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, text=True,
                       capture_output=True)
    if p.returncode:
        raise RuntimeError('Trusted research git command failed: ' + args[0])
    return p.stdout.strip()


def blob_at(revision, path):
    p = subprocess.run(['git', 'show', revision + ':' + path],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise ValueError('Research file not present on approved commit: ' + path)
    if len(p.stdout) > MAX_BATCH_BYTES:
        raise ValueError('Untrusted research payload over byte limit')
    return p.stdout.decode('utf-8')


def verify_remote(branch, commit):
    """Do not accept old commits, different repos or modified code."""
    session_name(branch)
    if not (len(commit) == 40 and all(x in '0123456789abcdef' for x in commit)):
        raise ValueError('Expected exact SHA-1 from successful research QA')
    ref = 'refs/heads/' + branch
    git_checked('fetch', '--no-tags', 'origin', ref + ':refs/remotes/origin/' + branch)
    remote = git_checked('rev-parse', 'refs/remotes/origin/' + branch)
    if remote != commit:
        raise ValueError('Research branch moved after green QA; retry on new green SHA')
    changed = git_checked('diff', '--name-only', 'origin/main...' + commit).splitlines()
    cp_path = checkpoint_path(branch)
    if cp_path not in changed:
        raise ValueError('Research checkpoint absent from source diff')
    if not all(path == cp_path or safe_batch_path(branch, path) for path in changed):
        raise ValueError('FORBIDDEN_RESEARCH_PATH: only own research files allowed')
    statuses = git_checked('diff', '--name-status', 'origin/main...' + commit).splitlines()
    if any(line.startswith(('D\t', 'R')) for line in statuses):
        raise ValueError('Research cannot delete or rename existing inputs')
    return changed


def stage_remote_batches(branch, commit):
    changed = verify_remote(branch, commit)
    checkpoint_rel = checkpoint_path(branch)
    checkpoint_raw = blob_at(commit, checkpoint_rel)
    cp = read_checkpoint(checkpoint_raw, branch)
    allowed = {entry['path'] for entry in cp['batches']} | {checkpoint_rel}
    if any(path not in allowed for path in changed):
        raise ValueError('Unexpected uncheckpointed source path')
    researched = []
    for batch in cp['batches']:
        path = batch['path']
        raw = blob_at(commit, path)
        if digest(raw) != batch['sha256']:
            raise ValueError('Research source hash mismatch: ' + path)
        rows = parse_batch(raw, path)
        if len(rows) != batch['count']:
            raise ValueError('Research row count mismatch: ' + path)
        researched.append((path, raw, rows))
    return checkpoint_rel, checkpoint_raw, researched


def ingest(branch, commit, dry_run=False):
    cp_path, cp_raw, researched = stage_remote_batches(branch, commit)
    ledger = load(LEDGER, {'version': 1, 'batches': {}})
    if not isinstance(ledger.get('batches'), dict):
        raise ValueError('Invalid research intake ledger')
    fresh = []
    for path, raw, rows in researched:
        previous = ledger['batches'].get(path)
        if previous:
            if previous['sha256'] != digest(raw):
                raise ValueError('Research session replay tried to edit accepted content')
            continue
        if (ROOT / path).exists():
            if digest((ROOT / path).read_bytes()) != digest(raw):
                raise ValueError('Research candidate path already occupied by other content')
            # State may be partly restored. Do not silently adopt it.
            raise ValueError('Research candidate already exists without accepted receipt')
        fresh.append((path, raw, rows))
    if not fresh:
        return {'status': 'ALREADY_INGESTED', 'new_topics': 0, 'branch': branch}
    all_new = [row for _, _, rows in fresh for row in rows]
    # The paper queue never exceeds the 1,000 topic approved intake ceiling.
    QA = validate_candidates(all_new)
    blocked = [row for row in QA if row['status'] != 'PASS']
    if blocked:
        raise ValueError('TRUSTED_RESEARCH_QA_BLOCKED: ' +
                         json.dumps(blocked[:4], ensure_ascii=False))
    if dry_run:
        return {'status': 'WOULD_INGEST', 'new_topics': len(all_new),
                'new_batches': len(fresh), 'branch': branch}
    # Preserve any changed existing registry state via remote compare-and-swap.
    state = RemoteState()
    paths = TOUCHED + [cp_path] + [path for path, _, _ in fresh]
    state.remember(paths)
    if (ROOT / cp_path).exists():
        previous_cp = read_checkpoint((ROOT / cp_path).read_text(encoding='utf-8'), branch)
        if len(previous_cp['batches']) > len(researched):
            raise ValueError('Research session checkpoint lost already-ingested batches')
    (ROOT / cp_path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / cp_path).write_text(cp_raw, encoding='utf-8')
    refill = load(REFILL, {'batches': {}})
    existing_ids = {row['topic_id'] for row in topics()}
    for path, raw, rows in fresh:
        output = ROOT / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(raw, encoding='utf-8')
        promote_candidates(path)  # Existing canonical Topic QA: no Excel.
        actual = {row['topic_id']: row for row in topics()}
        just_added = [row['topic_id'] for row in rows]
        if any(row_id in existing_ids or
               actual.get(row_id, {}).get('topic_qa_status') != 'PLANNED'
               for row_id in just_added):
            raise ValueError('Research gate failed during canonical Topic QA; no push')
        existing_ids.update(just_added)
        row = {'sha256': digest(raw), 'at': now(), 'state': 'TOPIC_QA_APPLIED',
               'research_branch': branch, 'research_commit': commit,
               'topic_ids': just_added}
        ledger['batches'][path] = row
        refill['batches'][Path(path).name] = {
            'sha256': digest(raw), 'at': row['at'],
            'state': 'TOPIC_QA_APPLIED; see per-topic result'
        }
    save(LEDGER, ledger)
    save(REFILL, refill)
    # Re-run every WordPress taxonomy/canonical/capacity invariant against the
    # just-imported manifest. A green branch QA is never enough by itself.
    from validate import run as validate_invariants
    validate_invariants()
    sha = state.persist(paths, 'research: trusted ten-topic QA intake and refill [skip ci]')
    return {'status': 'RESEARCH_ACCEPTED', 'new_topics': len(all_new),
            'new_batches': len(fresh), 'accepted_ids': [row['topic_id'] for row in all_new],
            'branch': branch, 'main_commit': sha}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--branch', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.dry_run:
        # No local invocation may mutate the project main registry by accident.
        if (os.environ.get('GITHUB_ACTIONS') != 'true' or
                os.environ.get('GITHUB_REPOSITORY') != 'thuexemayhanoi/wp-writer' or
                os.environ.get('GITHUB_REF') != 'refs/heads/main'):
            raise ValueError('Trusted GitHub Actions main required for applying research')
    print(json.dumps(ingest(args.branch, args.sha, args.dry_run),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
