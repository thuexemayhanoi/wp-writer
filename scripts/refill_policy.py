"""Single source of truth for the self-replenishing topic loop (config/refill-policy.json).

The numbers live in one file so the stock ladder, the watchdog, the dashboard, the discovery
scheduler and the refill controller can never disagree about "when is the PLANNED stock low".
"""
from common import load

DEFAULTS = {
    'enabled': True,
    'trigger_below_ready': 50,
    'round_target_min': 200,
    'round_target_max': 300,
    'research_batch_size': 10,
    'max_rounds': None,          # None = unlimited rounds
    'max_taxonomy_share': 0.25,  # no single category may take more than this share of a round
    'stalled_after_hours': 72,
}


def policy(override=None):
    merged = {**DEFAULTS, **(load('config/refill-policy.json', {}) or {}), **(override or {})}
    for key in ('trigger_below_ready', 'round_target_min', 'round_target_max', 'research_batch_size',
                'stalled_after_hours'):
        if type(merged[key]) is not int or merged[key] < 1:
            raise ValueError('refill policy %s must be a positive integer' % key)
    if merged['research_batch_size'] > 10:
        raise ValueError('Research V2 accepts at most 10 topics per batch')
    if not merged['research_batch_size'] <= merged['round_target_min'] <= merged['round_target_max']:
        raise ValueError('refill policy needs batch size <= round_target_min <= round_target_max')
    if merged['max_rounds'] is not None and (type(merged['max_rounds']) is not int or merged['max_rounds'] < 1):
        raise ValueError('max_rounds must be null (unlimited) or a positive integer')
    if not 0 < float(merged['max_taxonomy_share']) <= 1:
        raise ValueError('max_taxonomy_share must be in (0, 1]')
    return merged


def stock_policy(production_policy, refill=None):
    """Production policy overlaid with the refill thresholds, for topic_stock.build_stock()."""
    refill = refill or policy()
    return {**(production_policy or {}),
            'min_claimable_queue': refill['trigger_below_ready'],
            'max_claimable_queue': refill['trigger_below_ready'] + refill['round_target_max']}
