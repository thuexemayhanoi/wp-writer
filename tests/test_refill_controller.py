"""Self-replenishing topic loop: when ready PLANNED stock drops below the trigger, a research
order for 200-300 new topics opens; there is no limit on the number of rounds; the controller
never writes anywhere except its own two files and only from the trusted main workflow.
"""
import datetime as dt
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import refill_controller as controller
import refill_policy
from topic_stock import build_stock

AT = dt.datetime(2026, 10, 18, 9, 0, tzinfo=dt.timezone.utc)
POLICY = refill_policy.policy({'trigger_below_ready': 50, 'round_target_min': 200,
                               'round_target_max': 300, 'research_batch_size': 10, 'max_rounds': None})
TAXONOMY = [{'taxonomy_key': k, 'status': 'ACTIVE', 'wordpress_term_id': 100 + i}
            for i, k in enumerate(['engine-care', 'road-safety', 'battery-charging', 'trip-planning',
                                   'urban-mobility', 'legal'])]
TAXONOMY.append({'taxonomy_key': 'troubleshooting', 'status': 'PLANNED', 'wordpress_term_id': None})
TAXONOMY.append({'taxonomy_key': 'uncategorized', 'status': 'ACTIVE', 'wordpress_term_id': 1})
DOMAINS = [
    {'domain_id': 'D1', 'taxonomy_key': 'engine-care', 'initial_allocation': 50, 'capacity_allocation': 500},
    {'domain_id': 'D2', 'taxonomy_key': 'road-safety', 'initial_allocation': 50, 'capacity_allocation': 500},
    {'domain_id': 'D3', 'taxonomy_key': 'battery-charging', 'initial_allocation': 60, 'capacity_allocation': 600},
    {'domain_id': 'D4', 'taxonomy_key': 'trip-planning', 'initial_allocation': 60, 'capacity_allocation': 600},
    {'domain_id': 'D5', 'taxonomy_key': 'urban-mobility', 'initial_allocation': 80, 'capacity_allocation': 800},
    {'domain_id': 'D6', 'taxonomy_key': 'legal', 'initial_allocation': 40, 'capacity_allocation': 400},
    {'domain_id': 'D7', 'taxonomy_key': 'troubleshooting', 'initial_allocation': 99, 'capacity_allocation': 990},
]


def planned(i, key='engine-care', **extra):
    return {'topic_id': 'NT-%06d' % i, 'topic_qa_status': 'PLANNED', 'taxonomy_key': key,
            'canonical_target': 'https://thuexemaynguyentu.com/t-%d/' % i, **extra}


def stock_of(rows, **kw):
    return build_stock(rows, {}, {}, {}, set(), {}, {'min_claimable_queue': 50, 'max_claimable_queue': 350}, at=AT)


def assess(rows, orders=None, intake=None, capacity=1000, refill=None, inventory=None):
    return controller.assess(refill or POLICY, stock_of(rows), rows, inventory or [], TAXONOMY, DOMAINS,
                             intake or {'batches': {}}, orders or {}, capacity, AT)


def intake_batch(at, ids):
    return {'at': at.isoformat(), 'accepted_ids': ids, 'topic_ids': ids}


class TriggerTests(unittest.TestCase):
    def test_healthy_stock_opens_nothing(self):
        orders, request, actions = assess([planned(i) for i in range(1, 51)])
        self.assertEqual((request['state'], actions, orders), ('HEALTHY', [], {}))
        self.assertNotIn('order', request)

    def test_below_fifty_opens_a_round_for_200_to_300_topics(self):
        orders, request, actions = assess([planned(i) for i in range(1, 50)])
        self.assertEqual((request['state'], actions), ('REFILL_OPENED', ['open']))
        order = request['order']
        self.assertEqual((order['id'], order['round'], order['target_min'], order['target_max']),
                         ('RF-0001', 1, 200, 300))
        self.assertEqual((order['remaining_to_min'], order['remaining_to_max'], order['batches_still_needed']),
                         (200, 300, 20))
        self.assertEqual(orders['RF-0001']['status'], 'OPEN')
        self.assertTrue(request['unlimited_rounds'])

    def test_exactly_fifty_is_not_low(self):
        self.assertEqual(assess([planned(i) for i in range(1, 51)])[1]['state'], 'HEALTHY')
        self.assertEqual(assess([planned(i) for i in range(1, 50)])[1]['state'], 'REFILL_OPENED')

    def test_an_empty_queue_opens_a_round(self):
        self.assertEqual(assess([])[1]['state'], 'REFILL_OPENED')

    def test_only_unreserved_planned_topics_count_as_stock(self):
        rows = [planned(i) for i in range(1, 80)]
        for i in range(60, 80):
            rows[i - 1]['hold'] = 'sources unreadable'
        self.assertEqual(assess(rows)[1]['ready_stock'], 59)
        rows = [planned(i, hold='x') for i in range(1, 80)]
        self.assertEqual(assess(rows)[1]['state'], 'REFILL_OPENED')

    def test_a_disabled_policy_never_opens_a_round(self):
        off = refill_policy.policy({'enabled': False})
        self.assertEqual(assess([], refill=off)[1]['state'], 'DISABLED')


class OrderLifecycleTests(unittest.TestCase):
    def open_order(self, opened_at=AT - dt.timedelta(hours=5), **extra):
        return {'RF-0001': {'round': 1, 'status': 'OPEN', 'opened_at': opened_at.isoformat(), 'closed_at': None,
                            'opened_ready': 3, 'trigger_below_ready': 50, 'target_min': 200, 'target_max': 300,
                            'capacity_limited': False, **extra}}

    def test_progress_counts_only_topics_accepted_after_the_order_opened(self):
        rows = [planned(i, 'trip-planning') for i in range(1, 41)]
        intake = {'batches': {
            'old': intake_batch(AT - dt.timedelta(days=3), ['NT-%06d' % i for i in range(900, 910)]),
            'a': intake_batch(AT - dt.timedelta(hours=2), ['NT-%06d' % i for i in range(1, 11)]),
            'b': intake_batch(AT - dt.timedelta(hours=1), ['NT-%06d' % i for i in range(11, 18)])}}
        orders, request, actions = assess(rows, self.open_order(), intake)
        order = request['order']
        self.assertEqual((request['state'], actions), ('REFILL_IN_PROGRESS', []))
        self.assertEqual((order['accepted_so_far'], order['remaining_to_min'], order['batches_still_needed']),
                         (17, 183, 19))
        self.assertEqual(orders['RF-0001']['status'], 'OPEN')

    def test_the_order_closes_at_the_minimum_and_is_recorded(self):
        ids = ['NT-%06d' % i for i in range(1, 201)]
        rows = [planned(i) for i in range(1, 201)]
        intake = {'batches': {'a': intake_batch(AT - dt.timedelta(hours=1), ids)}}
        orders, request, actions = assess(rows, self.open_order(), intake)
        self.assertEqual((request['state'], actions), ('REFILL_FULFILLED', ['close']))
        self.assertEqual((orders['RF-0001']['status'], orders['RF-0001']['accepted']), ('FULFILLED', 200))
        self.assertNotIn('order', request)

    def test_an_open_order_is_never_duplicated(self):
        orders, request, _ = assess([], self.open_order())
        self.assertEqual(list(orders), ['RF-0001'])
        self.assertEqual(request['order']['id'], 'RF-0001')

    def test_rounds_are_unlimited(self):
        orders = {}
        rows = []
        clock = AT
        for round_number in range(1, 26):
            result, request, actions = controller.assess(
                POLICY, stock_of(rows), rows, [], TAXONOMY, DOMAINS, {'batches': {}}, orders, 100000, clock)
            orders = result
            self.assertEqual(request['state'], 'REFILL_OPENED', round_number)
            self.assertEqual(request['order']['id'], 'RF-%04d' % round_number)
            # Fulfil the round, let the queue drain below the trigger again, move the clock on.
            ids = ['NT-%06d' % (round_number * 1000 + i) for i in range(200)]
            intake = {'batches': {'r%d' % round_number: intake_batch(clock + dt.timedelta(hours=1), ids)}}
            clock += dt.timedelta(hours=2)
            orders, request, actions = controller.assess(
                POLICY, stock_of([planned(i) for i in range(60)]), rows, [], TAXONOMY, DOMAINS, intake, orders,
                100000, clock)
            self.assertEqual(request['state'], 'REFILL_FULFILLED', round_number)
        self.assertEqual(len(orders), 25)
        self.assertTrue(all(o['status'] == 'FULFILLED' for o in orders.values()))

    def test_a_fulfilled_round_followed_by_low_stock_opens_the_next_round_at_once(self):
        ids = ['NT-%06d' % i for i in range(1, 201)]
        intake = {'batches': {'a': intake_batch(AT - dt.timedelta(hours=1), ids)}}
        orders, request, actions = assess([], self.open_order(), intake)
        self.assertEqual(actions, ['close', 'open'])
        self.assertEqual((request['state'], request['order']['id'], request['order']['accepted_so_far']),
                         ('REFILL_OPENED', 'RF-0002', 0))

    def test_an_optional_round_limit_can_be_set_by_the_owner(self):
        limited = refill_policy.policy({'max_rounds': 1})
        orders = {'RF-0001': {**self.open_order()['RF-0001'], 'status': 'FULFILLED'}}
        self.assertEqual(assess([], orders, refill=limited)[1]['state'], 'ROUND_LIMIT_REACHED')

    def test_a_silent_order_is_reported_as_stalled(self):
        quiet = self.open_order(opened_at=AT - dt.timedelta(hours=100))
        self.assertTrue(assess([], quiet)[1]['order']['stalled'])
        active = {'batches': {'a': intake_batch(AT - dt.timedelta(hours=3), ['NT-000001'])}}
        self.assertFalse(assess([planned(1)], quiet, active)[1]['order']['stalled'])


class CapacityTests(unittest.TestCase):
    def test_no_capacity_left_blocks_the_round_with_a_clear_instruction(self):
        rows = [planned(i) for i in range(1, 6)]
        _, request, actions = assess(rows, capacity=len(rows) + 9)
        self.assertEqual((request['state'], actions), ('CAPACITY_BLOCKED', []))
        self.assertIn('approved_capacity', request['instruction'])

    def test_the_round_shrinks_to_what_capacity_allows(self):
        rows = [planned(i) for i in range(1, 6)]
        orders, request, _ = assess(rows, capacity=len(rows) + 120)
        order = request['order']
        self.assertEqual((order['target_min'], order['target_max'], order['capacity_limited']), (120, 120, True))
        self.assertEqual(request['capacity_remaining'], 120)


class QuotaTests(unittest.TestCase):
    def test_quotas_sum_to_the_round_minimum_and_skip_unmaterialised_categories(self):
        _, request, _ = assess([])
        quotas = request['order']['category_quotas']
        self.assertEqual(sum(q['quota'] for q in quotas), 200)
        keys = {q['taxonomy_key'] for q in quotas}
        self.assertNotIn('troubleshooting', keys)
        self.assertNotIn('uncategorized', keys)
        self.assertLessEqual(max(q['quota'] for q in quotas), 200 * 0.25)

    def test_categories_that_already_have_content_get_smaller_quotas(self):
        crowded = [planned(i, 'engine-care') for i in range(1, 46)]
        _, request, _ = assess(crowded)
        by_key = {q['taxonomy_key']: q for q in request['order']['category_quotas']}
        self.assertEqual(by_key['engine-care']['known_now'], 45)
        self.assertLess(by_key['engine-care']['quota'], by_key['urban-mobility']['quota'])

    def test_published_wordpress_posts_count_as_existing_coverage(self):
        inventory = [{'id': 7000 + i, 'type': 'posts', 'status': 'publish', 'url': 'https://x/%d/' % i,
                      'categories': [TAXONOMY[1]['wordpress_term_id']]} for i in range(30)]
        _, request, _ = assess([], inventory=inventory)
        by_key = {q['taxonomy_key']: q for q in request['order']['category_quotas']}
        self.assertEqual(by_key['road-safety']['known_now'], 30)

    def test_next_batch_is_spread_over_several_categories(self):
        _, request, _ = assess([])
        slots = request['order']['next_batch_categories']
        self.assertEqual(sum(slots.values()), 10)
        self.assertGreaterEqual(len(slots), 4)
        self.assertLessEqual(max(slots.values()), 3)

    def test_spread_is_exact_capped_and_deterministic(self):
        quota = controller.spread(200, {'a': 80, 'b': 60, 'c': 40, 'd': 20, 'e': 10, 'f': 5}, 0.25)
        self.assertEqual(sum(quota.values()), 200)
        self.assertLessEqual(max(quota.values()), 50)
        self.assertEqual(quota, controller.spread(200, {'f': 5, 'e': 10, 'd': 20, 'c': 40, 'b': 60, 'a': 80}, 0.25))

    def test_when_every_category_is_at_budget_the_budget_weights_decide(self):
        waiting = []
        for domain in DOMAINS[:-1]:  # every materialised category already holds its full 10x budget
            for n in range(domain['capacity_allocation']):
                waiting.append({'topic_id': 'NT-%s-%d' % (domain['domain_id'], n), 'topic_qa_status': 'RESEARCH',
                                'taxonomy_key': domain['taxonomy_key'],
                                'canonical_target': 'https://thuexemaynguyentu.com/%s-%d/' % (domain['domain_id'], n)})
        _, request, _ = assess(waiting, capacity=100000)
        quotas = request['order']['category_quotas']
        self.assertEqual(request['state'], 'REFILL_OPENED')
        self.assertEqual(sum(q['quota'] for q in quotas), 200)
        self.assertEqual(request['order']['category_quotas_basis'], 'capacity')
        by_key = {q['taxonomy_key']: q['quota'] for q in quotas}
        self.assertGreater(by_key['urban-mobility'], by_key['legal'])


class DeterminismTests(unittest.TestCase):
    def test_the_request_carries_no_clock_so_an_idle_hour_makes_no_commit(self):
        first = assess([])
        second = controller.assess(POLICY, stock_of([]), [], [], TAXONOMY, DOMAINS, {'batches': {}}, {},
                                   1000, AT + dt.timedelta(minutes=59))
        # the order ledger records opened_at, the request itself must not
        self.assertEqual(json.dumps(first[1], sort_keys=True), json.dumps(second[1], sort_keys=True))
        self.assertNotIn('at', first[1])

    def test_progress_helper_ignores_foreign_or_undated_batches(self):
        found, last = controller.accepted_since({'batches': {'x': {'accepted_ids': ['NT-1']},
                                                              'y': intake_batch(AT, ['NT-2'])}}, AT.isoformat())
        self.assertEqual((found, last), (['NT-2'], AT))


class SafetyTests(unittest.TestCase):
    def test_apply_is_refused_outside_the_trusted_workflow(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': '', 'GITHUB_WORKFLOW': ''}, clear=False):
            with self.assertRaisesRegex(ValueError, 'Trusted Actions main'):
                controller.run(apply=True)

    def test_the_controller_only_writes_its_own_two_files(self):
        self.assertEqual((controller.STATE, controller.REQUEST),
                         ('data/state/refill-orders.json', 'reports/refill-request.json'))
        source = (ROOT / 'scripts/refill_controller.py').read_text()
        for forbidden in ('WP_APPLICATION_PASSWORD', 'urllib', 'requests', 'anthropic', 'openai', 'publisher'):
            self.assertNotIn(forbidden, source)

    def test_workflow_has_no_wordpress_secret_no_ai_and_trusted_main_only(self):
        text = (ROOT / '.github/workflows/topic-refill-controller.yml').read_text()
        self.assertIn('name: ' + controller.TRUSTED_WORKFLOW, text)
        self.assertIn('ref: main', text)
        self.assertIn('group: wp-writer-state', text)
        self.assertIn('cancel-in-progress: false', text)
        for forbidden in ('secrets.', 'WP_APPLICATION_PASSWORD', 'ANTHROPIC', 'OPENAI', 'pull_request'):
            self.assertNotIn(forbidden, text)

    def test_real_repository_state_produces_a_valid_request(self):
        inputs = controller.build_inputs()
        orders, request, _ = controller.assess(at=AT, **inputs)
        self.assertIn(request['state'], {'HEALTHY', 'REFILL_OPENED', 'REFILL_IN_PROGRESS', 'REFILL_FULFILLED',
                                         'CAPACITY_BLOCKED', 'DISABLED', 'ROUND_LIMIT_REACHED'})
        self.assertLess(len(json.dumps(request)), 20000)


class PolicyTests(unittest.TestCase):
    def test_repository_policy_matches_the_owner_order(self):
        # MASTER WORK 1,000 topics: rounds of 100-200 keep opening until the approved capacity is filled.
        policy = refill_policy.policy()
        self.assertEqual((policy['trigger_below_ready'], policy['round_target_min'], policy['round_target_max']),
                         (900, 100, 200))
        self.assertIsNone(policy['max_rounds'])

    def test_repository_policy_keeps_opening_rounds_until_the_approved_capacity_is_used(self):
        live = refill_policy.policy()
        rows = [planned(i) for i in range(1, 401)]  # 400 ready topics: a reserve, but far from 1,000
        self.assertEqual(assess(rows, refill=live)[1]['state'], 'REFILL_OPENED')
        orders, request, _ = assess(rows, capacity=1000, refill=live)
        self.assertEqual((request['order']['target_min'], request['order']['target_max']), (100, 200))
        rows = [planned(i, topic_qa_status='RESEARCH') for i in range(1, 992)]  # 991 rows: 9 slots left, below one batch
        self.assertEqual(assess(rows, capacity=1000, refill=live)[1]['state'], 'CAPACITY_BLOCKED')
        rows = [planned(i, topic_qa_status='RESEARCH') for i in range(1, 986)]  # 985 rows: last round cut to the 15 slots left
        order = assess(rows, capacity=1000, refill=live)[1]['order']
        self.assertEqual((order['target_min'], order['target_max'], order['capacity_limited']), (15, 15, True))

    def test_invalid_policies_are_refused(self):
        for bad in ({'round_target_min': 400}, {'research_batch_size': 11}, {'trigger_below_ready': 0},
                    {'max_rounds': 0}, {'max_taxonomy_share': 1.5}, {'round_target_min': 5}):
            with self.assertRaises(ValueError, msg=str(bad)):
                refill_policy.policy(bad)

    def test_stock_policy_carries_the_trigger_into_the_stock_ladder(self):
        merged = refill_policy.stock_policy({'mode': 'production'}, POLICY)
        self.assertEqual((merged['min_claimable_queue'], merged['max_claimable_queue'], merged['mode']),
                         (50, 350, 'production'))
        stock = build_stock([planned(i) for i in range(1, 40)], {}, {}, {}, set(), {}, merged, at=AT)
        self.assertTrue(stock['needs_research'])
        self.assertEqual(stock['shortfall'], 11)


if __name__ == '__main__':
    unittest.main()
