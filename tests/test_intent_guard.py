"""Search-intent collision guard: deterministic, hermetic, no network.

Fixtures reuse the wording patterns of the real site (long "Question? Subtitle" titles,
"Entity: question" families, district landing pages) so the thresholds are exercised on
the shapes that actually occur.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import intent_guard as guard

SITE = 'https://thuexemaynguyentu.com'


def wp(post_id, title, seo_title=None, content_hash=None):
    return {'id': post_id, 'type': 'posts', 'status': 'publish', 'title': title,
            'seo_title': seo_title, 'url': '%s/post-%s/' % (SITE, post_id),
            'content_hash': content_hash}


def topic(topic_id, title, keyword=None, status='PLANNED', **extra):
    return {'topic_id': topic_id, 'title': title, 'primary_keyword': keyword or title,
            'topic_qa_status': status, 'canonical_target': '%s/%s/' % (SITE, topic_id.lower()), **extra}


FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'intent_corpus.json').read_text(encoding='utf-8'))
# A frozen snapshot of the 160 public post titles keeps IDF statistics production-like and stable.
INVENTORY = [dict(wp(item['id'], item['title'], item['seo_title']), url=item['url']) for item in FIXTURE['items']]
BY_ID = {item['id']: item for item in INVENTORY}
ROWS = [
    topic('NT-000002', 'Gia hạn hợp đồng thuê xe máy đang sử dụng: những câu hỏi cần xác nhận', status='RESEARCH'),
    topic('NT-000010', 'Bảo quản găng tay đi xe máy mùa mưa'),
    topic('NT-000011', 'Cách chọn áo mưa bộ khi đi xe máy', status='REJECTED'),
]


def verdicts(title, keyword=None, rows=None, inventory=None, topic_id='NT-999999', **extra):
    candidate = topic(topic_id, title, keyword, status=None, **extra)
    return guard.assess_topic(candidate, (rows if rows is not None else ROWS) + [candidate],
                              inventory if inventory is not None else INVENTORY,
                              new_ids={topic_id})


class TokenizationTests(unittest.TestCase):
    def test_question_frames_and_fillers_are_dropped_but_entities_stay(self):
        a = guard.profile('Kiểm tra lốp xe máy như thế nào?').tokens
        b = guard.profile('Kiểm tra lốp xe máy').tokens
        self.assertEqual(a, b)
        self.assertIn('50cc', guard.profile('Xe 50cc có cần bằng lái không?').tokens)
        self.assertIn('bằng', guard.profile('Xe 50cc có cần bằng lái không?').tokens)

    def test_matching_is_accent_aware(self):
        price = guard.profile('Giá thuê xe máy điện').tokens
        extend = guard.profile('Gia hạn hợp đồng thuê xe máy').tokens
        self.assertNotIn('giá', extend)
        self.assertNotIn('gia', price)
        self.assertEqual(guard.profile('chợ Đồng Xuân').tokens & {'chợ'}, {'chợ'})

    def test_tone_mark_placement_variants_are_equal(self):
        self.assertEqual(guard.profile('hoà bình').tokens, guard.profile('hòa bình').tokens)
        self.assertEqual(guard.profile('thuý').tokens, guard.profile('thúy').tokens)

    def test_facets_describe_the_question_type(self):
        self.assertIn('legal', guard.profile('Xe 50cc có cần bằng lái không?').facets)
        self.assertIn('price', guard.profile('Pin VinFast giá bao nhiêu').facets)
        self.assertIn('timing', guard.profile('Bao lâu nên thay dầu').facets)
        self.assertIn('rent', guard.profile('Thuê xe máy gần Cầu Giấy').facets)
        self.assertNotIn('timing', guard.profile('Du lịch Hà Nội').facets)


class CollisionTests(unittest.TestCase):
    def assertFails(self, title, other, **kw):
        result = verdicts(title, **kw)
        self.assertIn('intent collision:' + other, result['errors'], title)

    def test_reworded_duplicates_of_published_posts_fail(self):
        self.assertFails('Xe 50cc có cần bằng lái không?', 'WP2556')
        self.assertFails('Bằng lái xe 50cc: có cần hay không', 'WP2556')
        self.assertFails('Thủ tục sang tên xe máy cũ', 'WP2550')
        self.assertFails('Bao lâu nên thay dầu xe máy?', 'WP2493')
        self.assertFails('Giá vé Văn Miếu Quốc Tử Giám và giờ mở cửa', 'WP2618')
        self.assertFails('Lịch trình du lịch Hà Nội một ngày', 'WP2607')

    def test_same_headline_with_a_different_subtitle_fails(self):
        self.assertFails('Cách đội mũ bảo hiểm đúng cách', 'WP3948')

    def test_duplicate_of_a_topic_still_in_the_factory_fails(self):
        self.assertFails('Bảo quản găng tay đi xe máy trong mùa mưa', 'NT-000010')
        self.assertFails('Gia hạn hợp đồng thuê xe máy đang sử dụng', 'NT-000002')

    def test_question_type_decides_between_price_and_range(self):
        pin_price = verdicts('Pin xe máy điện VinFast giá bao nhiêu')
        self.assertIn('intent collision:WP2390', pin_price['errors'])
        # Same entities, different question: explain it instead of being banned.
        pin_range = verdicts('Pin xe máy điện VinFast đi được bao nhiêu km')
        self.assertNotIn('intent collision:WP2390', pin_range['errors'])

    def test_a_rental_page_and_an_information_article_may_share_entities(self):
        without_rental_page = [item for item in INVENTORY if item['id'] != 3945]
        result = verdicts('Thuê xe máy và xăng E10: nên hỏi cửa hàng điều gì', inventory=without_rental_page)
        self.assertEqual(result['errors'], [])
        self.assertIn('near intent:WP3940', result['review'])
        # The identical headline is of course a collision.
        self.assertIn('intent collision:WP3945', verdicts('Thuê xe máy và xăng E10: nên hỏi cửa hàng điều gì')['errors'])

    def test_distinct_entities_in_a_template_family_pass(self):
        for title in ('Honda ICON e: pin sạc mất bao lâu và nên sạc ở đâu',
                      'Hoàng thành Thăng Long: cách đi nhanh từ Văn Miếu bằng xe máy',
                      'Thuê xe máy gần Cầu Giấy Hà Nội – Giá & Thủ Tục | Nguyễn Tú',
                      'Nhớt xe tay ga: chọn loại nào cho Honda Vision',
                      'Cách rửa xe máy tại nhà đúng cách'):
            result = verdicts(title)
            self.assertEqual(result['errors'], [], title)

    def test_entity_only_head_clauses_do_not_collide_across_a_family(self):
        family = [wp(1, 'Honda ICON e: có gì đáng chú ý?'), wp(2, 'Honda ICON e: đi được bao nhiêu km?'),
                  wp(3, 'Honda ICON e: có cần bằng lái không?')]
        result = verdicts('Honda ICON e: sạc pin tại nhà cần lưu ý gì', inventory=family, rows=[])
        self.assertEqual(result['errors'], [])

    def test_accent_homographs_do_not_collide(self):
        result = verdicts('Hỏi giá thuê xe máy điện: cần biết thêm chi phí nào?',
                          rows=[topic('NT-000002', 'Gia hạn hợp đồng thuê xe máy đang sử dụng', status='RESEARCH')],
                          inventory=[])
        self.assertEqual((result['errors'], result['review']), ([], []))

    def test_rejected_topics_do_not_own_an_intent(self):
        self.assertEqual(verdicts('Cách chọn áo mưa bộ khi đi xe máy')['errors'], [])

    def test_unrelated_topic_passes_cleanly(self):
        result = verdicts('Đèn xi nhan xe máy nháy nhanh bất thường')
        self.assertEqual((result['errors'], result['review'], result['matches']), ([], [], []))

    def test_published_topic_is_not_counted_twice(self):
        published = wp(3888, 'Chọn nơi sửa xe máy điện: những câu hỏi nên hỏi kỹ thuật viên')
        row = topic('NT-000037', published['title'], canonical_target=published['url'])
        index = guard.IntentIndex([published], [row])
        self.assertEqual(index.size, 1)

    def test_a_candidate_never_collides_with_itself(self):
        row = topic('NT-000010', 'Bảo quản găng tay đi xe máy mùa mưa')
        index = guard.IntentIndex([], [row])
        self.assertEqual(index.matches(row), [])


class PrecedenceTests(unittest.TestCase):
    def test_lowest_new_id_keeps_the_intent_and_the_later_duplicate_is_flagged(self):
        first = topic('NT-000200', 'Cách kiểm tra áp suất lốp xe máy bằng đồng hồ', status=None)
        second = topic('NT-000201', 'Kiểm tra áp suất lốp xe máy bằng đồng hồ như thế nào', status=None)
        rows = [first, second]
        new_ids = {'NT-000200', 'NT-000201'}
        a = guard.assess_topic(first, rows, [], new_ids=new_ids)
        b = guard.assess_topic(second, rows, [], new_ids=new_ids)
        self.assertEqual(a['errors'], [])
        self.assertEqual(b['errors'], ['intent collision:NT-000200'])

    def test_an_admitted_topic_always_wins_even_with_a_higher_id(self):
        admitted = topic('NT-000900', 'Cách kiểm tra áp suất lốp xe máy bằng đồng hồ')
        newcomer = topic('NT-000100', 'Kiểm tra áp suất lốp xe máy bằng đồng hồ', status=None)
        result = guard.assess_topic(newcomer, [admitted, newcomer], [], new_ids={'NT-000100'})
        self.assertEqual(result['errors'], ['intent collision:NT-000900'])


class WaiverTests(unittest.TestCase):
    TITLE = 'Cách kiểm tra lốp xe máy trước khi đi xa'
    INVENTORY = [dict(item, content_hash='h-current') if item['id'] == 2521 else item for item in INVENTORY]

    def result(self, research=None):
        candidate = topic('NT-000300', self.TITLE, status=None, research=research or {})
        return guard.assess_topic(candidate, [candidate], self.INVENTORY, new_ids={'NT-000300'})

    def test_review_needs_a_written_reason_and_the_current_page_hash(self):
        self.assertEqual(self.result()['review'], ['near intent:WP2521'])
        reason = 'Bài này chỉ nói về chuẩn bị lốp cho chuyến đường dài, không hướng dẫn đo độ mòn.'
        only_reason = {'resolved_intent_collisions': {'WP2521': reason}}
        self.assertEqual(self.result(only_reason)['review'], ['near intent:WP2521'])
        stale = {**only_reason, 'reviewed_content_hashes': {'2521': 'h-old'}}
        self.assertEqual(self.result(stale)['review'], ['near intent:WP2521'])
        full = {**only_reason, 'reviewed_content_hashes': {'2521': ['h-old', 'h-current']}}
        self.assertEqual(self.result(full)['review'], [])

    def test_a_short_reason_is_not_a_resolution(self):
        research = {'resolved_intent_collisions': {'WP2521': 'khác'},
                    'reviewed_content_hashes': {'2521': 'h-current'}}
        self.assertEqual(self.result(research)['review'], ['near intent:WP2521'])

    def test_a_fail_can_never_be_waived(self):
        candidate = topic('NT-000301', 'Xe 50cc có cần bằng lái không?', status=None, research={
            'resolved_intent_collisions': {'WP2556': 'Một lời giải thích đủ dài để vượt ngưỡng bốn mươi ký tự.'},
            'reviewed_content_hashes': {'2556': 'x'}})
        result = guard.assess_topic(candidate, [candidate], INVENTORY, new_ids={'NT-000301'})
        self.assertEqual(result['errors'], ['intent collision:WP2556'])


class LatePublicationTests(unittest.TestCase):
    """A post the factory published after the research snapshot cannot have been read: REVIEW is dropped, FAIL never."""
    TITLE = 'Cách kiểm tra lốp xe máy trước khi đi xa'

    def result(self, published, research, title=None, post_id=2521):
        inventory = [dict(item, factory_published_at=published) if item['id'] == post_id and published else item
                     for item in INVENTORY]
        candidate = topic('NT-000300', title or self.TITLE, status=None, research=research)
        return guard.assess_topic(candidate, [candidate], inventory, new_ids={'NT-000300'})

    def test_a_post_published_after_the_research_is_not_held_against_the_topic(self):
        found = self.result('2026-10-18T02:05:00+00:00', {'reviewed_at': '2026-10-18T02:00:00+00:00'})
        self.assertEqual(found['review'], [])
        self.assertEqual(found['matches'][0]['id'], 'WP2521')  # still reported for the audit trail

    def test_a_post_that_existed_when_the_researcher_read_still_needs_a_written_reason(self):
        found = self.result('2026-10-18T01:55:00+00:00', {'reviewed_at': '2026-10-18T02:00:00+00:00'})
        self.assertEqual(found['review'], ['near intent:WP2521'])

    def test_the_snapshot_time_wins_over_the_review_time(self):
        research = {'reviewed_at': '2026-10-18T02:09:00+00:00', 'inventory_updated_at': '2026-10-18T02:04:00+00:00'}
        self.assertEqual(self.result('2026-10-18T02:05:00+00:00', research)['review'], [])
        late_snapshot = dict(research, inventory_updated_at='2026-10-18T02:06:00+00:00')
        self.assertEqual(self.result('2026-10-18T02:05:00+00:00', late_snapshot)['review'], ['near intent:WP2521'])

    def test_a_post_the_factory_did_not_publish_is_never_waived(self):
        found = self.result(None, {'reviewed_at': '2026-10-18T02:00:00+00:00'})
        self.assertEqual(found['review'], ['near intent:WP2521'])

    def test_a_row_without_any_research_time_is_never_waived(self):
        self.assertEqual(self.result('2026-10-18T02:05:00+00:00', {})['review'], ['near intent:WP2521'])

    def test_a_fail_is_never_waived_by_publication_time(self):
        found = self.result('2026-10-18T02:05:00+00:00', {'reviewed_at': '2026-10-18T02:00:00+00:00'},
                            title='Xe 50cc có cần bằng lái không?', post_id=2556)
        self.assertEqual(found['errors'], ['intent collision:WP2556'])

    def test_only_wordpress_posts_can_be_late(self):
        index = guard.IntentIndex([], [])
        index.published_at = {'WP1': '2026-10-18T02:05:00+00:00'}
        research = {'reviewed_at': '2026-10-18T02:00:00+00:00'}
        late = {'kind': 'wordpress', 'id': 'WP1'}
        self.assertTrue(guard._published_after_research(late, {'research': research}, index))
        self.assertFalse(guard._published_after_research(dict(late, kind='topic:PLANNED'), {'research': research}, index))


class CalibrationTests(unittest.TestCase):
    """The thresholds were tuned on the real site: distinct posts pass, true overlaps are flagged."""
    # Overlapping commercial rental guides that the owner already publishes side by side.
    RENTAL_FAMILY = {823, 829, 895, 901, 906, 1060, 1062, 2613}

    def test_real_site_titles_stay_calibrated(self):
        index = guard.IntentIndex(INVENTORY, [])
        counts = {'PASS': 0, 'REVIEW': 0, 'FAIL': 0}
        hard = set()
        for item in INVENTORY:
            found = index.matches({'topic_id': 'WP%d' % item['id'], 'title': item['title'],
                                   'primary_keyword': item['title']})
            counts[found[0]['severity'] if found else 'PASS'] += 1
            hard.update(item['id'] for m in found if m['severity'] == 'FAIL')
            hard.update(int(m['id'][2:]) for m in found if m['severity'] == 'FAIL')
        total = len(INVENTORY)
        self.assertTrue(hard <= self.RENTAL_FAMILY, sorted(hard - self.RENTAL_FAMILY))
        self.assertGreaterEqual(counts['PASS'] / total, 0.75, counts)
        self.assertLessEqual(counts['FAIL'] / total, 0.05, counts)


class SettingsTests(unittest.TestCase):
    def test_thresholds_must_be_ordered(self):
        with self.assertRaises(ValueError):
            guard.settings({'review_weighted_jaccard': 0.9, 'fail_weighted_jaccard': 0.8})

    def test_guard_can_be_disabled_by_config_only(self):
        candidate = topic('NT-000302', 'Xe 50cc có cần bằng lái không?', status=None)
        off = guard.assess_topic(candidate, [candidate], INVENTORY, config={'enabled': False})
        self.assertEqual((off['errors'], off['review'], off['matches']), ([], [], []))

    def test_repository_config_is_valid(self):
        self.assertTrue(guard.settings()['enabled'])


class ScaleTests(unittest.TestCase):
    def test_ten_thousand_known_intents_and_three_hundred_candidates_stay_fast(self):
        rows = [topic('NT-%06d' % i, 'Chủ đề kiểm thử số %d về mục %d' % (i, i % 97)) for i in range(1, 10001)]
        started = time.time()
        index = guard.IntentIndex([], rows)
        candidates = [topic('NT-%06d' % (20000 + i), 'Ứng viên độc lập số %d cho nhóm %d' % (i, i % 31), status=None)
                      for i in range(300)]
        flagged = sum(bool(index.matches(c, {c['topic_id']})) for c in candidates)
        elapsed = time.time() - started
        self.assertEqual(flagged, 0)
        self.assertLess(elapsed, 20)

    def test_the_same_inputs_always_give_the_same_verdict(self):
        first = verdicts('Thủ tục sang tên xe máy cũ')
        second = verdicts('Thủ tục sang tên xe máy cũ')
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
