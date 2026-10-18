"""Deterministic search-intent collision guard for Topic QA.

A candidate topic is compared with EVERY WordPress item on the site (posts, pages,
products) and with EVERY topic that is still inside the factory (PLANNED, claimed,
authored, published, awaiting research). There is no network access, no model and
no randomness: Research QA on a research branch and the trusted intake on main
always reach the same verdict for the same inputs.

The guard is a lexical proxy for "would Google see two URLs competing for the same
question". Tokens are IDF-weighted, so a shared rare entity (a model name, a place,
a regulation number) counts for far more than shared filler such as "xe máy Hà Nội".
Every title / SEO title / keyword is compared on its own, so a long subtitle on an
existing page cannot hide that its headline already answers the candidate's question.
It is intentionally conservative:

* FAIL    near-identical wording once filler words are removed (or the same wording
          plus the same question type). This can never be waived: re-scope or
          retitle the topic.
* REVIEW  substantial overlap. The researcher resolves it only by recording a
          written justification in ``research.resolved_intent_collisions``. A
          post the factory itself published AFTER the research snapshot cannot
          have been read: its REVIEW is not held against the topic (a FAIL still is).
* PASS    no meaningful overlap with any known URL or topic.

Machine similarity is a screen, not proof of a distinct reader question: the
existing full-content review evidence in ``topic_factory.gate`` still applies.
"""
import datetime as dt
import html
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from common import load, norm

# Single filler words (accent-aware: "chợ" is never the filler "cho"). Everything else that is
# frequent but meaningful stays in and is simply down-weighted by IDF; matching is
# accent-aware, so giá (price) never equals gia hạn.
STOPWORDS = frozenset(
    'và là của cho những các một khi nào gì nên về ở để trên với trong không hay như sao '
    'cách được cần biết dùng nếu thì sẽ mà cả cũng rất hơn nhất điều tại theo sau trước '
    'giữa từng mỗi vậy'.split())

# Multi-word question / filler frames (listed WITHOUT diacritics, matched on unaccented words)
# removed before tokenising. The question types they carry are captured as FACETS instead.
FILLER_PHRASES = tuple(sorted((
    'nhu the nao', 'the nao', 'nhu nao', 'khi nao', 'bao lau', 'bao nhieu', 'la gi', 'o dau',
    'co khong', 'hay khong', 'co nen', 'hay la', 'tai sao', 'vi sao', 'do dau', 'lam sao',
    'lam the nao', 'gom nhung gi', 'gom nhung', 'nen lam gi', 'can biet', 'nen biet',
    'can luu y', 'luu y', 'dieu can biet', 'co the', 'co can', 'co phai', 'ra sao', 'nhu the',
    'phu hop', 'kinh nghiem', 'huong dan', 'nhu cau', 'hang ngay', 'thuc te', 'nguoi dung',
    'su dung', 'nhung dieu', 'nhung gi',
), key=len, reverse=True))

# Question types. They explain a match and escalate an already strong one; they never
# excuse an overlap.
FACETS = {
    'price': ('gia', 'chi phi', 'bang gia', 'bao nhieu tien', 'phi', 'dat coc', 'tien coc', 'ngan sach'),
    'howto': ('cach', 'huong dan', 'quy trinh', 'cac buoc', 'lam sao', 'lam the nao', 'checklist', 'meo'),
    'compare': ('so sanh', 'khac nhau', 'nen chon', 'tot hon', 'phan biet', 'hay'),
    'review': ('danh gia', 'uu nhuoc diem', 'co tot khong', 'co dang', 'phu hop voi ai', 'co nen'),
    'legal': ('bang lai', 'giay phep', 'quy dinh', 'nghi dinh', 'luat', 'muc phat', 'thu tuc',
              'dang ky', 'bao hiem', 'co can'),
    'trouble': ('do dau', 'nguyen nhan', 'dau hieu', 'su co', 'khac phuc', 'xu ly', 'bi hong', 'loi'),
    'timing': ('bao lau', 'khi nao', 'thoi gian', 'lich bao duong', 'dinh ky', 'chu ky'),
    'rent': ('thue', 'cho thue'),
    'place': ('o dau', 'dia chi', 'diem den', 'tham quan', 'lo trinh', 'lich trinh', 'gan'),
    'list': ('top', 'danh sach', 'tong hop', 'cac loai', 'cac dong', 'cac mau'),
    'range': ('km', 'quang duong'),
}

DEFAULTS = {
    'enabled': True,
    'fail_weighted_jaccard': 0.80,
    'fail_min_coverage': 0.90,
    'same_facet_fail_weighted_jaccard': 0.70,
    'contained_candidate_coverage': 0.97,
    'contained_max_size_ratio': 2.2,
    'contained_same_facet_fail_weighted_jaccard': 0.45,
    'contained_no_facet_fail_weighted_jaccard': 0.75,
    'review_weighted_jaccard': 0.55,
    'review_candidate_coverage': 0.75,
    'min_tokens_for_coverage_rules': 3,
    'min_shared_tokens_for_coverage_review': 3,
    'weight_power': 2.0,
    'max_reported': 10,
    'min_resolution_chars': 40,
}


def settings(override=None):
    """Thresholds come from config/refill-policy.json; code defaults keep tests hermetic."""
    configured = (load('config/refill-policy.json', {}) or {}).get('intent_guard', {})
    merged = {**DEFAULTS, **configured, **(override or {})}
    if not 0 < merged['review_weighted_jaccard'] < merged['fail_weighted_jaccard'] <= 1:
        raise ValueError('intent_guard thresholds must satisfy 0 < review < fail <= 1')
    return merged


@dataclass(frozen=True)
class Profile:
    tokens: frozenset
    facets: frozenset


_TONE_PLACEMENT = {
    'oà': 'òa', 'oá': 'óa', 'oả': 'ỏa', 'oã': 'õa', 'oạ': 'ọa',
    'oè': 'òe', 'oé': 'óe', 'oẻ': 'ỏe', 'oẽ': 'õe', 'oẹ': 'ọe',
    'uý': 'úy', 'uỳ': 'ùy', 'uỷ': 'ủy', 'uỹ': 'ũy', 'uỵ': 'ụy',
}
_FRAMES = tuple(sorted((tuple(p.split()) for p in FILLER_PHRASES), key=len, reverse=True))


def _plain(word):
    stripped = ''.join(c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn')
    return stripped.replace('đ', 'd')


def _words(text):
    """Accent-aware lowercase words with one canonical tone-mark placement (hoà == hòa)."""
    folded = unicodedata.normalize('NFC', html.unescape(str(text or ''))).lower()
    for old, new in _TONE_PLACEMENT.items():
        folded = folded.replace(old, new)
    return re.findall(r'[^\W_]+', folded)


def _kept(plain):
    """Drop multi-word question frames ('như thế nào', 'bao lâu'); they become FACETS."""
    keep = [True] * len(plain)
    for i in range(len(plain)):
        for frame in _FRAMES:
            if tuple(plain[i:i + len(frame)]) == frame:
                for j in range(i, i + len(frame)):
                    keep[j] = False
                break
    return keep


@lru_cache(maxsize=100_000)
def profile(text):
    words = _words(text)
    plain = [_plain(w) for w in words]
    keep = _kept(plain)
    tokens = frozenset(w for w, k in zip(words, keep) if k and w not in STOPWORDS)
    padded = ' ' + norm(str(text or '')) + ' '
    facets = frozenset(name for name, phrases in FACETS.items()
                       if any(' ' + phrase + ' ' in padded for phrase in phrases))
    return Profile(tokens, facets)


HEAD_MIN_TOKENS_WITHOUT_FACET = 5  # a bare entity head (3-4 tokens, no question type) says nothing about intent
_HEAD_SPLIT = re.compile(r'\s*(?:[:|–—?]|\s-\s)\s*')


def _profiles(*texts):
    """One profile per distinct field, plus the head clause of "Head query: elaboration" titles.

    Comparing the head clause alone catches a candidate that repeats an existing headline
    while the existing page only adds a subtitle. Template subtitles are never compared on
    their own, so "Giá vé, giờ mở cửa" cannot make two different attractions collide.
    """
    seen, result = set(), []

    def add(item):
        if item.tokens and item.tokens not in seen:
            seen.add(item.tokens)
            result.append(item)

    for text in texts:
        text = str(text or '')
        add(profile(text))
        head = _HEAD_SPLIT.split(text, maxsplit=1)[0]
        if head != text:
            head_profile = profile(head)
            # "Entity: question" titles (Honda ICON e: ...) keep the entity in the head and the
            # question after it, so a bare entity head says nothing about intent.
            if len(head_profile.tokens) >= 3 and (
                    head_profile.facets or len(head_profile.tokens) >= HEAD_MIN_TOKENS_WITHOUT_FACET):
                add(head_profile)
    return result


def _utc(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def inventory_entry(item):
    """A WordPress item is known by its title and its SEO title."""
    label = item.get('title') or ''
    if not label.strip():
        return None
    return {'id': 'WP' + str(item.get('id')), 'kind': 'wordpress', 'label': label,
            'url': item.get('url'), 'profiles': _profiles(label, item.get('seo_title'))}


def topic_entry(topic):
    status = topic.get('topic_qa_status')
    if status == 'REJECTED' or not topic.get('title'):
        return None  # a rejected idea never became content; it cannot own an intent
    return {'id': topic['topic_id'], 'kind': 'topic:' + str(status or 'UNKNOWN'),
            'label': topic['title'], 'url': topic.get('canonical_target'),
            'profiles': _profiles(topic.get('title'), topic.get('primary_keyword'))}


class IntentIndex:
    """All known intents of the factory: WordPress inventory + every live topic row."""

    def __init__(self, inventory, topic_rows, config=None):
        self.config = settings(config)
        published = {item.get('url') for item in inventory if item.get('url')}
        entries = [e for e in (inventory_entry(i) for i in inventory) if e]
        # A published topic is the same URL as its inventory item: count it once.
        entries += [e for e in (topic_entry(t) for t in topic_rows)
                    if e and e['url'] not in published]
        self.entries = [e for e in entries if e['profiles']]
        self.df = defaultdict(int)
        self.postings = defaultdict(list)
        for position, entry in enumerate(self.entries):
            vocabulary = frozenset().union(*(p.tokens for p in entry['profiles']))
            for token in vocabulary:
                self.df[token] += 1
                self.postings[token].append(position)
        self.size = len(self.entries)
        self._weights = {}
        self.content_hash = {'WP' + str(item.get('id')): item.get('content_hash') for item in inventory}
        # When the factory's own Publisher verified a post (stamped by topic_factory.stamp_factory_posts).
        self.published_at = {'WP' + str(item.get('id')): item['factory_published_at']
                             for item in inventory if item.get('factory_published_at')}

    def weight(self, token):
        value = self._weights.get(token)
        if value is None:
            value = (math.log((self.size + 1) / (self.df.get(token, 0) + 1)) + 1) ** self.config['weight_power']
            self._weights[token] = value
        return value

    def _candidates(self, probes):
        tokens = frozenset().union(*(p.tokens for p in probes))
        rare = [t for t in tokens if self.df.get(t, 0) <= max(3, self.size // 10)]
        found = set()
        for token in rare or tokens:
            found.update(self.postings.get(token, ()))
        return found

    def compare(self, probe, other):
        shared = probe.tokens & other.tokens
        if not shared:
            return None
        w = self.weight
        shared_weight = sum(w(t) for t in shared)
        probe_weight = sum(w(t) for t in probe.tokens)
        other_weight = sum(w(t) for t in other.tokens)
        return {
            'weighted_jaccard': shared_weight / (probe_weight + other_weight - shared_weight),
            'candidate_coverage': shared_weight / probe_weight,
            'existing_coverage': shared_weight / other_weight,
            'shared': sorted(shared, key=lambda t: -w(t)),
            'only_candidate': sorted(probe.tokens - shared, key=lambda t: -w(t)),
            'only_existing': sorted(other.tokens - shared, key=lambda t: -w(t)),
            'same_facets': sorted(probe.facets & other.facets),
            'no_facet_info': not probe.facets and not other.facets,
            'facet_conflict': (('rent' in probe.facets) != ('rent' in other.facets)
                               or bool(probe.facets and other.facets and not probe.facets & other.facets)),
            'identical': probe.tokens == other.tokens,
            'sizes': (len(probe.tokens), len(other.tokens)),
        }

    def severity(self, scores):
        cfg = self.config
        wj = scores['weighted_jaccard']
        cand_cov, existing_cov = scores['candidate_coverage'], scores['existing_coverage']
        probe_size, other_size = scores['sizes']
        big = min(probe_size, other_size) >= cfg['min_tokens_for_coverage_rules']
        same = bool(scores['same_facets'])
        level = None
        if scores['identical'] or wj >= cfg['fail_weighted_jaccard']:
            level = 'FAIL'
        elif big and min(cand_cov, existing_cov) >= cfg['fail_min_coverage']:
            level = 'FAIL'
        elif big and same and wj >= cfg['same_facet_fail_weighted_jaccard']:
            level = 'FAIL'
        elif (big and cand_cov >= cfg['contained_candidate_coverage']
                and other_size <= cfg['contained_max_size_ratio'] * probe_size):
            # The existing wording already contains everything the candidate asks and adds only
            # a frame or subtitle (a much longer page that merely mentions it does not count).
            if same and wj >= cfg['contained_same_facet_fail_weighted_jaccard']:
                level = 'FAIL'
            elif scores['no_facet_info'] and wj >= cfg['contained_no_facet_fail_weighted_jaccard']:
                level = 'FAIL'
        if level == 'FAIL' and scores['facet_conflict'] and not scores['identical']:
            level = 'REVIEW'  # a rental page and an information article (or a price and a range
            # question) can share every entity yet answer different questions: explain, don't ban
        if level:
            return level
        if wj >= cfg['review_weighted_jaccard']:
            return 'REVIEW'
        if (big and cand_cov >= cfg['review_candidate_coverage']
                and len(scores['shared']) >= cfg['min_shared_tokens_for_coverage_review']):
            return 'REVIEW'
        return None

    def verdict(self, probes, entry):
        best = None
        for probe in probes:
            for other in entry['profiles']:
                scores = self.compare(probe, other)
                if scores is None:
                    continue
                level = self.severity(scores)
                if level is None:
                    continue
                rank = (level == 'FAIL', scores['weighted_jaccard'])
                if best is None or rank > best[0]:
                    best = (rank, level, scores)
        if best is None:
            return None
        _, level, scores = best
        return {'id': entry['id'], 'kind': entry['kind'], 'title': entry['label'], 'url': entry['url'],
                'severity': level,
                'weighted_jaccard': round(scores['weighted_jaccard'], 3),
                'candidate_coverage': round(scores['candidate_coverage'], 3),
                'shared_terms': scores['shared'][:8], 'only_in_candidate': scores['only_candidate'][:6],
                'only_in_existing': scores['only_existing'][:6], 'same_question_type': scores['same_facets']}

    def matches(self, topic, new_ids=None):
        """Every known intent that overlaps this candidate, strongest first.

        ``new_ids`` are the topic IDs submitted in the same research run. Admitted topics and
        WordPress items always win; among new rows the lowest ID keeps the intent and later
        duplicates are the ones flagged, so two near-identical siblings never cancel each other.
        """
        probes = _profiles(topic.get('title'), topic.get('primary_keyword'))
        if not probes:
            return []
        own = topic.get('topic_id')
        new_ids = set(new_ids or ())
        found = []
        for position in sorted(self._candidates(probes)):
            entry = self.entries[position]
            if entry['id'] == own:
                continue
            if entry['id'] in new_ids and own in new_ids and entry['id'] > own:
                continue
            verdict = self.verdict(probes, entry)
            if verdict:
                found.append(verdict)
        found.sort(key=lambda v: (v['severity'] != 'FAIL', -v['weighted_jaccard'], v['id']))
        return found


def _resolved(match, topic, index, cfg):
    """A REVIEW overlap is resolved only by a written reason; for a WordPress page the researcher
    must also have read its CURRENT full content (reviewed_content_hashes). FAIL is never waived."""
    research = topic.get('research') or {}
    waived = research.get('resolved_intent_collisions')
    reason = waived.get(match['id']) if isinstance(waived, dict) else None
    if not (isinstance(reason, str) and len(reason.strip()) >= cfg['min_resolution_chars']):
        return False
    if match['kind'] != 'wordpress':
        return True
    current = index.content_hash.get(match['id'])
    if not current:
        return True  # inventory carries no hash to compare against
    seen = (research.get('reviewed_content_hashes') or {}).get(match['id'][2:])
    return current in (seen if isinstance(seen, list) else [seen])


def _published_after_research(match, topic, index):
    """A sibling article the factory published after the researcher read the site cannot have been read.

    Its REVIEW overlap is not held against the topic (article QA still compares the finished text with every
    public post). A FAIL overlap is never waived, and neither is a legacy page or a topic row: only a post
    this factory verified after the research snapshot (`inventory_updated_at`, else `reviewed_at`).
    """
    if match['kind'] != 'wordpress':
        return False
    research = topic.get('research') or {}
    seen = _utc(research.get('inventory_updated_at')) or _utc(research.get('reviewed_at'))
    at = _utc(index.published_at.get(match['id']))
    return bool(seen and at and at > seen)


def assess_topic(topic, topic_rows, inventory, new_ids=None, index=None, config=None):
    """Errors/review findings for Topic QA; ``index`` lets a whole batch share one corpus build."""
    cfg = settings(config)
    if not cfg['enabled']:
        return {'errors': [], 'review': [], 'matches': []}
    index = index or IntentIndex(inventory, topic_rows, cfg)
    found = index.matches(topic, new_ids)
    errors, review = [], []
    for match in found:
        if match['severity'] == 'FAIL':
            errors.append('intent collision:' + match['id'])
        elif not _resolved(match, topic, index, cfg) and not _published_after_research(match, topic, index):
            review.append('near intent:' + match['id'])
    limit = cfg['max_reported']
    return {'errors': errors[:limit], 'review': review[:limit], 'matches': found[:limit]}
