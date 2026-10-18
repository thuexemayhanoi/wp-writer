"""10 Writer articles: 8 PASS continue immediately, 2 stay in REPAIR."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import qa
from qa_gate import validate_complete
from common import digest
from unittest.mock import patch


class PerArticleEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'posts/drafts').mkdir(parents=True)
        (self.root/'data/qa').mkdir(parents=True)
        (self.root/'reports').mkdir(parents=True)
        self.repair=[]
        for i in range(1,11):
            topic='NT-%06d'%i
            path=self.root/'posts/drafts'/(topic+'.md')
            path.write_text('---\ntopic_id: '+topic+'\n---\nBODY '+str(i),encoding='utf-8')
            status='PASS' if i<=8 else ('REVIEW' if i==9 else 'FAIL')
            res={'topic_id':topic,'status':status,'source_sha256':digest(path.read_bytes()),
                 'word_count':1800,'gates':{'1':{}},'errors':[],
                 'review':[] if status=='PASS' else ['needs source or content repair']}
            (self.root/'data/qa'/(topic+'.json')).write_text(json.dumps(res))
            if status!='PASS':
                self.repair.append(res)
        self.write_repair()

    def write_repair(self):
        (self.root/'reports/repair-queue.json').write_text(json.dumps(self.repair))

    def test_10_articles_8_pass_2_require_repair_but_queue_is_complete(self):
        report=validate_complete(self.root)
        self.assertEqual(report['pass_count'],8)
        self.assertEqual(report['repair_count'],2)
        self.assertEqual(report['draft_count'],10)
        self.assertEqual(report['repair_ids'],['NT-000009','NT-000010'])
        self.assertEqual(report['publish_eligibility'],'PER_ARTICLE_ONLY')

    def test_stale_qa_result_is_infrastructure_failure(self):
        (self.root/'posts/drafts/NT-000001.md').write_text('CHANGED AFTER QA')
        with self.assertRaisesRegex(ValueError,'Stale'):
            validate_complete(self.root)

    def test_missing_qa_receipt_does_not_let_old_posts_through(self):
        (self.root/'data/qa/NT-000001.json').unlink()
        with self.assertRaisesRegex(ValueError,'Missing QA'):
            validate_complete(self.root)

    def test_missing_repair_queue_is_not_green(self):
        (self.root/'reports/repair-queue.json').unlink()
        with self.assertRaisesRegex(ValueError,'repair-queue checkpoint'):
            validate_complete(self.root)

    def test_partial_ticket_list_is_not_green(self):
        self.repair=self.repair[:1]
        self.write_repair()
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            validate_complete(self.root)

    def test_forged_pass_with_errors_is_not_green(self):
        p=self.root/'data/qa/NT-000002.json'
        x=json.loads(p.read_text())
        x['errors']=['spam']
        p.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'PASS has unaddressed'):
            validate_complete(self.root)

    def test_missing_qa_identity_is_not_green(self):
        p=self.root/'data/qa/NT-000002.json'
        x=json.loads(p.read_text())
        x.pop('topic_id')
        p.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            validate_complete(self.root)

    def test_invalid_qa_status_is_not_green(self):
        p=self.root/'data/qa/NT-000002.json'
        x=json.loads(p.read_text())
        x['status']='SKIPPED'
        p.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'Invalid QA result'):
            validate_complete(self.root)

class FingerprintScalingTests(unittest.TestCase):
    """Near-duplicate checks compare every draft with every other draft and public page: shingle each text once."""

    def test_fingerprint_jaccard_equals_the_exact_tuple_jaccard(self):
        a = qa.counted_text('Một hai ba bốn năm sáu bảy tám chín mười mười một mười hai ' * 6)
        b = qa.counted_text('Một hai ba bốn năm sáu bảy tám chín mười đổi khác hoàn toàn sau đó ' * 6)
        self.assertAlmostEqual(qa.jaccard(qa.fingerprint(a), qa.fingerprint(b)),
                               qa.jaccard(qa.shingles(a), qa.shingles(b)))
        self.assertEqual(qa.jaccard(set(), set()), 0)
        self.assertEqual(qa.jaccard({1, 2, 3}, {2, 3, 4}), 0.5)

    def test_equal_texts_are_shingled_once(self):
        qa.fingerprint.cache_clear()
        text = 'xe máy số côn tay ' * 40
        first = qa.fingerprint(text)
        self.assertIs(qa.fingerprint(text), first)
        self.assertEqual(qa.fingerprint.cache_info().hits, 1)

    def test_a_draft_is_re_parsed_only_when_its_content_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'NT-000001.md'
            article = '---\ntitle: x\n---\n' + ' '.join('từ%d' % i for i in range(60))
            path.write_text(article, encoding='utf-8')
            qa._DRAFT_FINGERPRINTS.clear()
            with patch.object(qa, 'read_article', wraps=qa.read_article) as read:
                first = qa.draft_fingerprint(path)
                self.assertIs(qa.draft_fingerprint(path), first)
                self.assertEqual(read.call_count, 1)
                path.write_text(article + ' thêm vài từ mới để đổi nội dung bài viết này', encoding='utf-8')
                self.assertNotEqual(qa.draft_fingerprint(path), first)
                self.assertEqual(read.call_count, 2)

    def test_an_unreadable_draft_has_no_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'NT-000002.md'
            path.write_text('no frontmatter at all', encoding='utf-8')
            qa._DRAFT_FINGERPRINTS.clear()
            self.assertIsNone(qa.draft_fingerprint(path))


if __name__=='__main__':
    unittest.main()
