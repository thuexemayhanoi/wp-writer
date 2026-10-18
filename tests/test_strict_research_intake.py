"""Only a Research QA PASS may become PLANNED, and Research QA now checks search-intent
collisions against every published item and every topic that is still in the factory.

Synthetic sources only; no network, no WordPress, no real registry is touched.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))

import refill_policy
import research_intake as intake
import research_v2 as research
import validate as repo_invariants
from test_intent_guard import INVENTORY as SITE_POSTS
from test_research_v2 import topic as research_topic

TAXONOMY = [{'taxonomy_key': 'reviews'}]


def candidate(i, title, keyword=None):
    row = research_topic(900000 + i, origin='IDEA-UNIT-%d' % i)
    row.update(title=title, primary_keyword=keyword or title,
               proposed_slug='unit-' + str(i), canonical_target=row['canonical_target'].rsplit('/', 2)[0] + '/unit-%d/' % i,
               intent_key='unit-intent-%d' % i)
    row['research'] = copy.deepcopy(row['research'])
    return row


def run_qa(rows, inventory=None, incumbent=None):
    return research.validate_candidates(rows, incumbent=incumbent or [], inventory=inventory or [],
                                        taxonomy=TAXONOMY, discovery={'proposals': {}})


class ResearchQaIntentTests(unittest.TestCase):
    def test_a_distinct_topic_still_passes(self):
        row = candidate(1, 'Đánh giá nhu cầu di chuyển an toàn theo tình huống riêng')
        self.assertEqual(run_qa([row])[0]['status'], 'PASS')

    def test_a_reworded_copy_of_a_published_post_is_failed(self):
        row = candidate(2, 'Bằng lái xe 50cc: có cần hay không')
        verdict = run_qa([row], inventory=SITE_POSTS)[0]
        self.assertEqual(verdict['status'], 'FAIL')
        self.assertIn('intent collision:WP2556', verdict['errors'])

    def test_a_copy_of_a_topic_already_in_the_factory_is_failed(self):
        factory = candidate(3, 'Bảo quản găng tay đi xe máy mùa mưa')
        factory['topic_qa_status'] = 'PLANNED'
        row = candidate(4, 'Bảo quản găng tay đi xe máy trong mùa mưa')
        verdict = run_qa([row], incumbent=[factory])[0]
        self.assertEqual(verdict['status'], 'FAIL')
        self.assertIn('intent collision:' + factory['topic_id'], verdict['errors'])

    def test_two_new_siblings_keep_the_first_and_flag_only_the_later_one(self):
        first = candidate(5, 'Cách kiểm tra áp suất lốp xe máy bằng đồng hồ')
        second = candidate(6, 'Kiểm tra áp suất lốp xe máy bằng đồng hồ như thế nào')
        verdicts = {v['topic_id']: v for v in run_qa([first, second])}
        self.assertNotIn('intent collision:' + second['topic_id'], verdicts[first['topic_id']]['errors'])
        self.assertIn('intent collision:' + first['topic_id'], verdicts[second['topic_id']]['errors'])

    def test_a_rejected_topic_does_not_own_an_intent(self):
        rejected = candidate(7, 'Bảo quản găng tay đi xe máy mùa mưa')
        rejected['topic_qa_status'] = 'REJECTED'
        row = candidate(8, 'Bảo quản găng tay đi xe máy trong mùa mưa')
        verdict = run_qa([row], incumbent=[rejected])[0]
        self.assertFalse([e for e in verdict['errors'] + verdict['review'] if 'intent' in e], verdict)

    def test_review_overlap_is_resolved_only_by_reason_plus_current_content_hash(self):
        row = candidate(9, 'Cách kiểm tra lốp xe máy trước khi đi xa')
        current = next(p for p in SITE_POSTS if p['id'] == 2521).get('content_hash')
        self.assertIsNone(current)  # the frozen fixture carries titles only
        before = run_qa([row], inventory=SITE_POSTS)[0]
        self.assertEqual(before['status'], 'REVIEW')
        self.assertIn('near intent:WP2521', before['review'])
        row['research']['resolved_intent_collisions'] = {
            'WP2521': 'Chỉ nói về chuẩn bị lốp cho chuyến dài; không hướng dẫn đo độ mòn hay áp suất.'}
        after = run_qa([row], inventory=SITE_POSTS)[0]
        self.assertNotIn('near intent:WP2521', after['review'])


class StrictIntakeTests(unittest.TestCase):
    def test_gate_pass_without_research_qa_pass_never_reaches_planned(self):
        good = candidate(11, 'Đánh giá nhu cầu di chuyển an toàn theo tình huống một')
        weak = candidate(12, 'Đánh giá nhu cầu di chuyển an toàn theo tình huống hai')
        raw = ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in (good, weak))
        batch = 'data/candidates/claude-unit-202610-0001.jsonl'
        registry, seen = [], {}

        def fake_promote(path, verdicts=None):
            seen['verdicts'] = verdicts
            for row in (good, weak):
                status = 'PLANNED' if (verdicts or {}).get(row['topic_id']) == 'PASS' else 'RESEARCH'
                registry.append({'topic_id': row['topic_id'], 'topic_qa_status': status})

        class Cas:
            def remember(self, paths):
                pass

            def persist(self, paths, message=None):
                return 'a' * 40

        with tempfile.TemporaryDirectory() as folder:
            qa = [{'topic_id': good['topic_id'], 'status': 'PASS'},
                  {'topic_id': weak['topic_id'], 'status': 'REVIEW'}]
            with patch.object(intake, 'ROOT', Path(folder)), \
                 patch.object(intake, 'stage_remote_batches',
                              return_value=('data/research/checkpoints/claude-unit-202610.json', '{"version":1}',
                                            [(batch, raw, [good, weak])])), \
                 patch.object(intake, 'load', side_effect=lambda path, default=None: default), \
                 patch.object(intake, 'validate_candidates', return_value=qa), \
                 patch.object(intake, 'promote_candidates', side_effect=fake_promote), \
                 patch.object(intake, 'topics', side_effect=lambda: list(registry)), \
                 patch.object(intake, 'RemoteState', Cas), \
                 patch.object(intake, 'save', lambda *a, **k: None), \
                 patch.object(repo_invariants, 'run', lambda: None):
                result = intake.ingest('research/claude-unit-202610', 'a' * 40)
        self.assertEqual(seen['verdicts'], {good['topic_id']: 'PASS', weak['topic_id']: 'REVIEW'})
        self.assertEqual(result['accepted_ids'], [good['topic_id']])
        self.assertEqual(result['not_accepted'], {weak['topic_id']: 'RESEARCH'})
        self.assertEqual(result['status'], 'RESEARCH_PARTIALLY_ACCEPTED')


if __name__ == '__main__':
    unittest.main()


class ResearcherToolingTests(unittest.TestCase):
    def test_intent_check_screens_a_candidate_file_before_any_push(self):
        rows = [{'topic_id': 'NT-990001', 'title': 'Xe 50cc có cần bằng lái không?',
                 'primary_keyword': 'Xe 50cc có cần bằng lái không', 'proposed_slug': 'a'},
                {'topic_id': 'NT-990002', 'title': 'Cách đọc thông số lốp xe máy 80/90-14',
                 'primary_keyword': 'đọc thông số lốp xe máy', 'proposed_slug': 'b'}]
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'data/candidates').mkdir(parents=True)
            (Path(folder) / 'data/candidates/x-0001.jsonl').write_text(
                ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
            with patch.object(research, 'ROOT', Path(folder)), patch.object(research, 'topics', lambda: []), \
                 patch.object(research, 'load', lambda path, default=None: {'items': SITE_POSTS}):
                report = research.intent_check('data/candidates/x-0001.jsonl')
        verdicts = {t['topic_id']: t['verdict'] for t in report['topics']}
        self.assertEqual(verdicts, {'NT-990001': 'FAIL', 'NT-990002': 'PASS'})
        self.assertEqual((report['fail'], report['review'], report['rows']), (1, 0, 2))
        self.assertEqual(report['topics'][0]['nearest'][0]['id'], 'WP2556')
        self.assertTrue(report['how_to_resolve'])

    def test_a_row_another_researcher_pushed_first_owns_the_intent(self):
        mine = {'topic_id': 'NT-990002', 'title': 'Cách đọc thông số lốp xe máy 80/90-14',
                'primary_keyword': 'đọc thông số lốp xe máy', 'proposed_slug': 'b'}
        theirs = dict(mine, topic_id='NT-980001', title='Đọc thông số lốp xe máy 80/90-14 như thế nào', proposed_slug='c')
        registered = dict(theirs, topic_id='NT-980002', title='Một chủ đề khác hẳn về áo mưa bộ')
        ref = 'refs/remotes/origin/research/'
        branches = {'peer-fresh': ('NT-980001', theirs), 'peer-stale': ('NT-980003', dict(theirs, topic_id='NT-980003')),
                    'peer-registered': ('NT-980002', registered), 'me': ('NT-990002', mine)}
        stamps = {'peer-fresh': 1000, 'peer-stale': 1000 - research.PEER_MAX_AGE - 1, 'peer-registered': 1000, 'me': 1000}

        def fake_git(*args):
            if args[0] == 'fetch':
                return ''
            if args[0] == 'for-each-ref':
                return '\n'.join('%s%s %d' % (ref, name, stamps[name]) for name in branches)
            name = args[3].rpartition('/')[2] if args[0] == 'ls-tree' else args[1].split(':')[0].rpartition('/')[2]
            if args[0] == 'ls-tree':
                return 'data/candidates/%s-0001.jsonl' % name
            return json.dumps(branches[name][1], ensure_ascii=False)

        with patch.object(research, 'git_read', side_effect=fake_git), \
             patch.object(research, 'topics', lambda: [{'topic_id': 'NT-980002'}]):
            rows, sessions = research.peer_rows('me', clock=1000)
        self.assertEqual([r['topic_id'] for r in rows], ['NT-980001'])  # not stale, not registered, not mine
        self.assertEqual(rows[0]['topic_qa_status'], 'PEER_PENDING')
        self.assertEqual(sessions, {'peer-fresh': 1})
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'data/candidates').mkdir(parents=True)
            (Path(folder) / 'data/candidates/me-0001.jsonl').write_text(json.dumps(mine, ensure_ascii=False) + '\n',
                                                                       encoding='utf-8')
            with patch.object(research, 'ROOT', Path(folder)), patch.object(research, 'topics', lambda: []), \
                 patch.object(research, 'load', lambda path, default=None: {'items': SITE_POSTS}), \
                 patch.object(research, 'peer_rows', return_value=(rows, sessions)):
                with_peers = research.intent_check('data/candidates/me-0001.jsonl')
                without = research.intent_check('data/candidates/me-0001.jsonl', peers=False)
        self.assertEqual(with_peers['topics'][0]['errors'], ['intent collision:NT-980001'])
        self.assertEqual(with_peers['peers'], {'pending_rows': 1, 'from': {'peer-fresh': 1}})
        self.assertEqual(without['topics'][0]['verdict'], 'PASS')

    def test_peer_check_degrades_to_the_registry_when_git_is_unreachable(self):
        with patch.object(research, 'git_read', side_effect=ValueError('Git research command failed: fetch origin')):
            rows, note = research.peer_rows('me')
        self.assertEqual(rows, [])
        self.assertIn('unavailable', note)

    def test_plan_reports_the_order_without_touching_anything(self):
        plan = research.refill_plan()
        self.assertIn('state', plan)
        self.assertEqual(plan['trigger_below_ready'], refill_policy.policy()['trigger_below_ready'])
        if plan['order']['id']:
            self.assertGreaterEqual(plan['order']['target_max'], plan['order']['target_min'])
            self.assertLessEqual(sum(plan['next_batch_categories'].values()), 10)


class SweepTests(unittest.TestCase):
    """A workflow_run intake can be cancelled while queued; the sweep ingests what it missed."""

    def test_the_sweep_tries_every_head_and_one_bad_branch_never_hides_another(self):
        heads = {'research/a': 'a' * 40, 'research/b': 'b' * 40, 'research/c': 'c' * 40}

        def fake_ingest(branch, commit, dry_run=False):
            if branch == 'research/b':
                raise ValueError('Research branch moved after green QA; retry on new green SHA')
            status = 'ALREADY_INGESTED' if branch == 'research/a' else 'RESEARCH_ACCEPTED'
            return {'status': status, 'branch': branch}

        with patch.object(intake, 'research_heads', return_value=heads), \
             patch.object(intake, 'ingest', side_effect=fake_ingest):
            out = intake.sweep()
        self.assertEqual(out['research/a']['status'], 'ALREADY_INGESTED')
        self.assertEqual(out['research/b']['status'], 'SKIPPED')
        self.assertIn('moved after green QA', out['research/b']['reason'])
        self.assertEqual(out['research/c']['status'], 'RESEARCH_ACCEPTED')

    def test_research_heads_reads_ls_remote_and_ignores_other_refs(self):
        raw = ('a' * 40 + '\trefs/heads/research/seodev-r5\n' + 'b' * 40 + '\trefs/heads/main\n' +
               'c' * 40 + '\trefs/heads/research/seodev-r8\n')
        with patch.object(intake, 'git_checked', return_value=raw):
            self.assertEqual(intake.research_heads(), {'research/seodev-r5': 'a' * 40,
                                                       'research/seodev-r8': 'c' * 40})

    def test_the_sweep_passes_the_dry_run_flag_through(self):
        seen = []
        with patch.object(intake, 'research_heads', return_value={'research/a': 'a' * 40}), \
             patch.object(intake, 'ingest', side_effect=lambda b, c, d=False: seen.append(d) or {'status': 'WOULD_INGEST'}):
            intake.sweep(dry_run=True)
        self.assertEqual(seen, [True])

    def test_the_intake_workflow_sweeps_on_every_event_and_has_its_own_concurrency_group(self):
        text = (ROOT / '.github/workflows/topic-research-intake.yml').read_text()
        self.assertIn('group: wp-writer-research-intake', text)
        self.assertNotIn('group: wp-writer-state', text)  # a shared group starved the pending intake run
        self.assertIn('python scripts/research_intake.py --sweep', text)
        self.assertIn('if: always() && job.status', text)
        for trigger in ('workflow_run:', 'schedule:', 'workflow_dispatch:'):
            self.assertIn(trigger, text)
