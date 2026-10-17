"""Decide what a QA verdict means for the queue: publish, retry by machine, return to the writer, or hold for a real risk.

Pure functions, no network and no WordPress. QA thresholds are untouched: this only classifies the reasons
`qa.evaluate` already produced, so one held article is described precisely and never blocks another.

Classes
  REAL_RISK      duplicate URL/intent, wrong category, unverifiable source, wrong legal/price/business fact, fabricated
                 experience, or anything this module does not recognise (fail closed). Never auto-healed.
  WRITER_REPAIR  an authoring defect only the writer session can fix (SEO score, length, structure, meta, links, editorial
                 evidence). Counted per draft version; after `max_attempts` versions it needs the owner.
  INFRA_PENDING  a transient failure (source or link fetch timed out, 5xx, 429). Re-checked by the machine; after
                 `max_attempts` consecutive evaluations of the same draft it becomes REAL_RISK (source stays unverifiable).
  NONE           PASS.
"""
import re

CLASSES = ('REAL_RISK', 'WRITER_REPAIR', 'INFRA_PENDING')
MAX_ATTEMPTS = 3

# (gate, regex on the reason, class). First match wins; order matters.
RULES = (
    ('3', r'^Source REVIEW: (?:HTTPError (?:408|425|429|5\d\d)|URLError .*(?:timed out|reset|refused|aborted)|'
          r'TimeoutError|timeout|ConnectionResetError|ConnectionAbortedError|RemoteDisconnected|IncompleteRead)', 'INFRA_PENDING'),
    ('3', r'^Source REVIEW: ValueError: (?:Source (?:date stale|checked_at stale or future|claim/evidence missing)|'
          r'Unverified source snapshot)', 'WRITER_REPAIR'),
    ('3', r'^Source REVIEW', 'REAL_RISK'),
    ('3', r'^Source (?:host not allowlisted|URL is not safe public HTTPS)', 'REAL_RISK'),
    ('3', r'^(Unverified phone number|Unverified business offer|Business address mismatch|Business fact mismatch|'
          r'Business price mismatch|Unknown business fact key|Wrong rental rate|Legal claim needs|'
          r'Unverified experience|Numeric claims need)', 'REAL_RISK'),
    ('3', r'^External writer editorial', 'WRITER_REPAIR'),
    ('5', r'^Broken internal link', 'INFRA_PENDING'),
    ('5', r'.*', 'WRITER_REPAIR'),
    ('1', r'.*', 'WRITER_REPAIR'),
    ('2', r'.*', 'WRITER_REPAIR'),
)


def classify(gate, reason):
    for rule_gate, pattern, label in RULES:
        if str(gate) == rule_gate and re.match(pattern, str(reason)):
            return label
    return 'REAL_RISK'  # gates 4 and 6, and every reason nobody described: hold, never guess


def triage(result):
    """Split every reason of a QA result by class and name the overall hold class."""
    buckets = {label: [] for label in CLASSES}
    for gate, info in sorted((result.get('gates') or {}).items()):
        for reason in list(info.get('errors', [])) + list(info.get('review', [])):
            buckets[classify(gate, reason)].append('G' + str(gate) + ': ' + str(reason))
    if not result.get('gates'):
        # A crashed or unreadable draft has no per-gate detail: it is the writer's (or the owner's) to look at.
        for reason in list(result.get('errors', [])) + list(result.get('review', [])):
            buckets['REAL_RISK' if 'crashed' in str(reason) else 'WRITER_REPAIR'].append(str(reason))
    if result.get('status') == 'PASS':
        hold = 'NONE'
    else:
        hold = next((label for label in CLASSES if buckets[label]), 'REAL_RISK')
    return {'hold_class': hold, 'real_risk': buckets['REAL_RISK'], 'writer_repair': buckets['WRITER_REPAIR'],
            'infra_pending': buckets['INFRA_PENDING']}


def annotate(result, previous=None, max_attempts=MAX_ATTEMPTS):
    """Attach `triage` and the bounded `recheck` counter to a fresh QA result (mutates and returns it).

    previous = the last stored QA record of the same topic. The counter is carried only across consecutive
    non-PASS evaluations: a PASS resets it, a different hold class restarts it.
    """
    info = triage(result)
    prev = previous or {}
    prev_check = prev.get('recheck') or {}
    same_sha = prev.get('source_sha256') == result.get('source_sha256')
    carried = (prev.get('status') not in (None, 'PASS')
               and (prev.get('triage') or {}).get('hold_class') == info['hold_class'])
    if result.get('status') == 'PASS':
        attempts = 0
    elif carried and info['hold_class'] == 'INFRA_PENDING':
        attempts = int(prev_check.get('attempts', 0)) + 1  # another machine recheck of the same failure
    elif carried and info['hold_class'] == 'WRITER_REPAIR':
        attempts = int(prev_check.get('attempts', 0)) + (0 if same_sha else 1)  # one per new draft version
    else:
        attempts = 1
    exhausted = attempts >= max_attempts and result.get('status') != 'PASS'
    if exhausted and info['hold_class'] == 'INFRA_PENDING':
        info['infra_pending'], info['real_risk'] = [], info['real_risk'] + [
            'Transient failure persisted for %d evaluations: ' % attempts + '; '.join(info['infra_pending'])]
        info['hold_class'] = 'REAL_RISK'
    result['triage'] = info
    result['recheck'] = {'attempts': attempts, 'max': max_attempts, 'exhausted': exhausted,
                         'needs_owner': bool(exhausted and info['hold_class'] in ('REAL_RISK', 'WRITER_REPAIR'))}
    return result


def state_entry(result):
    """The small record the Publisher keeps between runs (reports/gate-recheck.json) so attempts survive the next QA rewrite."""
    return {'status': result.get('status'), 'source_sha256': result.get('source_sha256'),
            'triage': {'hold_class': (result.get('triage') or {}).get('hold_class')},
            'recheck': result.get('recheck'), 'at': result.get('at')}
