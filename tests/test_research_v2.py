"""Regression tests for external AI research and trusted checkpoint intake.

All fixture sources are synthetic and NEVER offered to article Writers. Tests
make no internet requests, create no WordPress posts and modify no real repo.
"""
import copy
import datetime as dt
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import research_v2 as research
import research_intake as intake
from common import SITE, digest


def topic(i=900001, origin='IDEA-RESEARCH-UNIT'):
    title = f'Đánh giá nhu cầu di chuyển an toàn theo tình huống {i}'
    sources = [
        {'url': 'https://mps.gov.vn/doc-example', 'checked_at': dt.date.today().isoformat(),
         'supports': 'Chủ đề an toàn cần đối chiếu nguồn cơ quan có thẩm quyền',
         'evidence_text': 'Đoạn bằng chứng kiểm thử nguồn chính thức tối thiểu hai mươi ký tự.',
         'source_sha256': 'a' * 64},
        {'url': 'https://vinfastauto.com/vn_vi/example', 'checked_at': dt.date.today().isoformat(),
         'supports': 'Thông số kỹ thuật thiết bị cần tham khảo tài liệu đúng mẫu xe',
         'evidence_text': 'Đoạn nguồn kỹ thuật thử nghiệm riêng từ hãng sản xuất.',
         'source_sha256': 'b' * 64},
    ]
    return {
        'topic_id': f'NT-{i:06d}', 'origin_id': origin,
        'title': title, 'primary_keyword': 'nhu cầu di chuyển an toàn',
        'search_intent': 'Hướng dẫn', 'intent_key': 'research-safe-' + str(i),
        'topic_role': 'supporting', 'pillar': 'reviews', 'hub': 'reviews', 'silo': 'reviews',
        'word_target_min': 1600, 'word_target_max': 5000,
        'internal_link_candidates': [SITE + '/verified/'],
        'taxonomy_key': 'reviews', 'proposed_slug': 'research-safe-' + str(i),
        'canonical_target': SITE + '/research-safe-' + str(i) + '/',
        'outline': ['Phạm vi người đọc', 'Nguồn và tiêu chuẩn', 'Các rủi ro',
                    'Cách tự kiểm tra', 'Giới hạn và tóm tắt'],
        'research': {
            'reviewer': 'research-unit-test', 'difference_summary': 'Riêng biệt với nội dung thương mại',
            'usefulness': 'Làm rõ câu hỏi trước khi quyết định phương tiện',
            'scope_exclusions': ['Không quảng cáo dịch vụ'],
            'reviewed_content_hashes': {'original-empty-inventory': 'reviewed'},
            'reviewed_existing_ids': [],
            'external_sources': sources,
        }
    }


class ResearchEvidenceTests(unittest.TestCase):
    def test_one_genuine_source_is_enough_to_research_a_narrow_topic(self):
        self.assertEqual(research.validate_sources(topic()['research']), [])
        one = copy.deepcopy(topic()['research'])
        one['external_sources'] = one['external_sources'][:1]
        self.assertEqual(research.validate_sources(one), [])
        one['external_sources'] = []
        self.assertTrue(any('SOURCE_COUNT' in e for e in research.validate_sources(one)))

    def test_fake_google_news_signal_is_not_primary_evidence(self):
        research_data = copy.deepcopy(topic()['research'])
        research_data['external_sources'][0]['url'] = 'https://news.google.com/rss/articles/fake'
        self.assertTrue(any('NOT_DIRECT_HTTPS' in e for e in research.validate_sources(research_data)))

    def test_duplicate_reference_rejected_but_same_host_can_be_independent_documents(self):
        research_data = copy.deepcopy(topic()['research'])
        research_data['external_sources'][1]['url'] = research_data['external_sources'][0]['url']
        problems = research.validate_sources(research_data)
        self.assertTrue(any('DUPLICATED_URL' in e for e in problems))
        research_data['external_sources'][1]['url'] = 'https://mps.gov.vn/other-original-report'
        self.assertEqual(research.validate_sources(research_data), [])

    def test_stale_and_fabricated_snapshot_fields_rejected(self):
        research_data = copy.deepcopy(topic()['research'])
        research_data['external_sources'][0]['checked_at'] = '2021-01-01'
        research_data['external_sources'][0]['source_sha256'] = 'fake-snapshot'
        problems = research.validate_sources(research_data)
        self.assertTrue(any('SOURCE_DATE' in e for e in problems))
        self.assertTrue(any('SNAPSHOT_SHA' in e for e in problems))

    def test_topic_gate_reuses_existing_cannibalization_checks(self):
        taxonomy = [{'taxonomy_key': 'reviews'}]
        verdict = research.validate_candidates([topic()], incumbent=[],
            inventory=[], taxonomy=taxonomy, discovery={'proposals': {}})
        self.assertEqual(verdict[0]['status'], 'PASS')

    def test_duplicate_intent_with_different_title_rejected(self):
        other = topic(900002)
        other['intent_key'] = topic()['intent_key']
        result = research.validate_candidates([topic(), other], incumbent=[],
            inventory=[], taxonomy=[{'taxonomy_key': 'reviews'}],
            discovery={'proposals': {}})
        self.assertTrue(any(r['status'] == 'FAIL' for r in result))

    def test_discovery_origin_not_allowed_to_switch_category(self):
        t = topic(origin='NTD-unit-origin')
        result = research.validate_candidates([t], incumbent=[],
            inventory=[], taxonomy=[{'taxonomy_key': 'reviews'}],
            discovery={'proposals': {'NTD-unit-origin': {'taxonomy_key': 'electric'}}})
        self.assertEqual(result[0]['status'], 'FAIL')
        self.assertIn('RESEARCH_DISCOVERY_TAXONOMY_CONFLICT', result[0]['errors'])

    def test_research_must_match_article_contract_before_planned(self):
        t = topic()
        t.pop('word_target_min')
        results = research.validate_candidates([t], incumbent=[], inventory=[],
            taxonomy=[{'taxonomy_key': 'reviews'}], discovery={'proposals': {}})
        self.assertEqual(results[0]['status'], 'FAIL')
        self.assertIn('RESEARCH_WORD_RANGE_MUST_BE_1600_TO_5000', results[0]['errors'])

    def test_cannot_fake_published_wordpress_post_or_claim(self):
        t = topic()
        t['wp_post_id'] = 3888
        results = research.validate_candidates([t], incumbent=[], inventory=[],
            taxonomy=[{'taxonomy_key': 'reviews'}], discovery={'proposals': {}})
        self.assertEqual(results[0]['status'], 'FAIL')
        self.assertIn('RESEARCH_CANDIDATE_MUST_NOT_IMPERSONATE_PUBLISHED_OR_CLAIMED_POST',
                      results[0]['errors'])

    def test_cannot_overwrite_existing_topic_id(self):
        t = topic()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            research.validate_candidates([t], incumbent=[copy.deepcopy(t)],
                inventory=[], taxonomy=[{'taxonomy_key': 'reviews'}],
                discovery={'proposals': {}})


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.branch = 'research/claude-unit-202610'
        self.batch = 'data/candidates/claude-unit-202610-0001.jsonl'
        self.cp = research.checkpoint_path(self.branch)
        file = self.root / self.batch
        file.parent.mkdir(parents=True)
        file.write_text(''.join(json.dumps(topic(i), ensure_ascii=False) + '\n'
            for i in range(900001, 900011)), encoding='utf-8')
        self.patch_root = patch.object(research, 'ROOT', self.root)
        self.patch_root.start()
        self.mock_load = patch.object(research, 'load', side_effect=self.load)
        self.mock_load.start()
        self.mock_qa = patch.object(research, 'validate_candidates',
            side_effect=lambda candidates: [{'topic_id': x['topic_id'], 'status': 'PASS'}
                for x in candidates])
        self.mock_qa.start()

    def tearDown(self):
        self.mock_qa.stop()
        self.mock_load.stop()
        self.patch_root.stop()
        self.folder.cleanup()

    def load(self, path, default=None):
        p = self.root / path
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

    def test_ten_topic_session_checkpoint_and_resume_bytes(self):
        created = research.checkpoint(self.branch)
        self.assertEqual(created['new_topics'], 10)
        self.assertEqual(created['batches'], 1)
        self.assertEqual(research.verify_files(self.branch)['total_topics'], 10)
        cp = json.loads((self.root / self.cp).read_text())
        self.assertEqual(cp['batches'][0]['sha256'],
            digest((self.root / self.batch).read_bytes()))

    def test_one_failing_topic_never_blocks_the_passing_ones(self):
        def verdicts(candidates):
            return [{'topic_id': x['topic_id'], 'status': 'FAIL' if x['topic_id'] == 'NT-900003' else 'PASS',
                     'errors': ['collision'] if x['topic_id'] == 'NT-900003' else [], 'review': []}
                    for x in candidates]
        self.mock_qa.stop()
        with patch.object(research, 'validate_candidates', side_effect=verdicts):
            result = research.checkpoint(self.branch)
        self.mock_qa.start()
        self.assertEqual(result['accepted_topics'], 9)
        self.assertEqual([b['topic_id'] for b in result['blocked_topics']], ['NT-900003'])

    def test_a_batch_with_nothing_usable_is_still_refused(self):
        self.mock_qa.stop()
        with patch.object(research, 'validate_candidates', side_effect=lambda candidates: [
                {'topic_id': x['topic_id'], 'status': 'FAIL', 'errors': ['x'], 'review': []} for x in candidates]):
            with self.assertRaisesRegex(ValueError, 'RESEARCH_QA_BLOCKED'):
                research.checkpoint(self.branch)
        self.mock_qa.start()

    def test_mutating_checkpointed_batch_fails_closed(self):
        research.checkpoint(self.branch)
        with (self.root / self.batch).open('a') as f:
            f.write(json.dumps(topic(900012), ensure_ascii=False) + '\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            research.verify_files(self.branch)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            research.checkpoint(self.branch)

    def test_short_batch_needs_explicit_final(self):
        path = self.root / self.batch
        rows = path.read_text().splitlines()
        path.write_text('\n'.join(rows[:3]) + '\n')
        with self.assertRaisesRegex(ValueError, 'Only explicitly final'):
            research.checkpoint(self.branch)
        allowed = research.checkpoint(self.branch, final=True)
        self.assertEqual(allowed['new_topics'], 3)

    def test_foreign_paths_are_not_valid_own_session_inputs(self):
        self.assertFalse(research.safe_batch_path(
            self.branch, 'data/candidates/mistral-other-0001.jsonl'))
        self.assertFalse(research.safe_batch_path(
            self.branch, 'scripts/publisher.py'))
        with self.assertRaises(ValueError):
            research.session_name('research/../../admin')

    def test_git_porcelain_leading_columns_survive_cli_reader(self):
        class Result:
            returncode = 0
            stdout = ' M data/research/checkpoints/claude-unit-202610.json\n'
            stderr = ''
        with patch.object(research.subprocess, 'run', return_value=Result()):
            self.assertEqual(research.git_read('status', '--porcelain'),
                             ' M data/research/checkpoints/claude-unit-202610.json')

    def test_second_batch_can_push_modified_checkpoint_and_new_batch(self):
        cp = self.cp
        batch = self.batch
        observed = {'files': None}
        def git_stub(*args):
            command = args[0]
            if command == 'branch':
                return self.branch
            if command == 'status':
                return ' M ' + cp + '\n?? ' + batch
            if command == 'add':
                observed['files'] = set(args[2:])
                return ''
            if command == 'rev-parse':
                return 'a' * 40
            if command == 'ls-remote':
                return 'a' * 40 + '\trefs/heads/' + self.branch
            return ''
        verified = {'batch_paths':[batch], 'checkpoint_path':cp}
        with patch.object(research, 'verify_files', return_value=verified), \
             patch.object(research, 'git_read', side_effect=git_stub):
            result = research.push(self.branch)
        self.assertEqual(observed['files'], {batch, cp})
        self.assertEqual(result['state'], 'SAVED')


    def test_scope_gate_blocks_privileged_changes(self):
        research.checkpoint(self.branch)
        with patch.object(research, 'git_read',
                side_effect=['\n'.join([self.cp, self.batch, 'config/production-policy.json'])]):
            with self.assertRaisesRegex(ValueError, 'FORBIDDEN_RESEARCH_PATH'):
                research.verify_branch(self.branch)


class IntakeTests(unittest.TestCase):
    def test_intake_rejects_malformed_sha_before_git_fetch(self):
        with self.assertRaisesRegex(ValueError, 'Expected exact SHA'):
            intake.verify_remote('research/claude-unit-202610', 'fake-SHA')

    def test_intake_readonly_mode_does_not_mutate_repo(self):
        t = topic()
        raw = json.dumps(t, ensure_ascii=False) + '\n'
        fake = ('data/research/checkpoints/claude-unit-202610.json',
                '{"version":1}', [
                    ('data/candidates/claude-unit-202610-0001.jsonl', raw, [t])
                ])
        with patch.object(intake, 'stage_remote_batches', return_value=fake), \
             patch.object(intake, 'validate_candidates',
                 return_value=[{'topic_id': t['topic_id'], 'status': 'PASS'}]):
            result = intake.ingest('research/claude-unit-202610', 'a' * 40,
                                   dry_run=True)
        self.assertEqual(result['status'], 'WOULD_INGEST')
        self.assertEqual(result['new_topics'], 1)


class ResearchWorkflowSafetyTests(unittest.TestCase):
    def test_branch_qa_has_no_wordpress_secrets(self):
        text = (ROOT / '.github/workflows/topic-research-qa.yml').read_text()
        self.assertIn('contents: read', text)
        self.assertNotIn('WP_APPLICATION_PASSWORD', text)
        self.assertIn('verify-branch', text)
        self.assertIn('research/**', text)

    def test_intake_runs_only_after_green_push_and_on_trusted_main(self):
        text = (ROOT / '.github/workflows/topic-research-intake.yml').read_text()
        self.assertIn("workflow_run.event == 'push'", text)
        self.assertIn("workflow_run.conclusion == 'success'", text)
        self.assertIn('ref: main', text)
        self.assertNotIn('WP_APPLICATION_PASSWORD', text)
        self.assertNotIn('mode=production', text)


if __name__ == '__main__':
    unittest.main()
