"""Six independent hard gates. Scores never override FAIL/REVIEW."""
import argparse
import datetime as dt
import functools
import gzip
import io
import html
import json
import http.client
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
import yaml
from common import ROOT, SITE, Text, WP, Redirect, digest, load, norm, now, save, topics, visible
from taxonomy_sync import by_key,path_for
from gate_triage import annotate
from topic_factory import drop_own_post, exempt_factory_posts, gate as topic_gate
from slug_policy import proposed_slug_errors

def read_article(path):
    raw=path.read_text();parts=raw.split('---',2)
    if not raw.startswith('---\n') or len(parts)!=3:raise ValueError('YAML frontmatter required')
    if len(parts[1])>50000:raise ValueError('Frontmatter too large')
    meta=yaml.safe_load(parts[1])
    if not isinstance(meta,dict):raise ValueError('Frontmatter mapping required')
    return meta,parts[2].strip(),digest(raw)

def counted_text(body):
    # Count prose, not YAML, code, markup, URL strings, reference/keyword appendices.
    body=re.sub(r'```.*?```','',body,flags=re.S)
    body=re.split(r'^#{1,3}\s+(?:Nguồn(?: tham khảo)?|Tài liệu tham khảo|Từ khóa|Keywords|References)\b',body,maxsplit=1,flags=re.M|re.I)[0]
    body=re.sub(r'!\[[^\]]*\]\([^)]*\)','',body)
    body=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',body)
    body=re.sub(r'https?://\S+','',body)
    body=re.sub(r'<[^>]*>','',body)
    body=re.sub(r'^\s*(?:primary_keyword|secondary_keywords|keywords|từ khóa)\s*:.*$','',body,flags=re.M|re.I)
    return visible(body)

def word_count(body):return len(re.findall(r"[^\W_]+(?:[’'-][^\W_]+)*",counted_text(body),re.UNICODE))

def shingles(body):
    words=norm(body).split()
    return {tuple(words[i:i+5]) for i in range(max(0,len(words)-4))}

def jaccard(a,b):
    shared=len(a&b)
    return shared/max(1,len(a)+len(b)-shared)

@functools.cache
def fingerprint(text):
    """Hashed 5-word shingles of a text. Equal texts are shingled once per process, so comparing every draft with every
    other draft and every public page costs one pass over each text instead of one per pair (the set-of-tuples
    `shingles` made a 200-draft QA run take close to an hour). Only for comparing two fingerprints with each other."""
    words=norm(text).split()
    return frozenset(hash(tuple(words[i:i+5])) for i in range(max(0,len(words)-4)))

_DRAFT_FINGERPRINTS={}

def draft_fingerprint(path):
    """Fingerprint of another draft's counted text, or None when it cannot be read; re-parsed only when the file changed."""
    raw=path.read_bytes();key=digest(raw);hit=_DRAFT_FINGERPRINTS.get(path)
    if hit and hit[0]==key:return hit[1]
    try:value=fingerprint(counted_text(read_article(path)[1]))
    except Exception:value=None
    _DRAFT_FINGERPRINTS[path]=(key,value)
    return value

def mdlinks(body):return [(a,u) for a,u in re.findall(r'(?<!!)\[([^\]]*)\]\(([^\s)]+)(?:\s+[^)]*)?\)',body)]


# External HTTPS links in the public article body are permitted regardless of
# domain. Factual source credibility is evaluated separately by G3.
# G5 still rejects insecure or deceptive outbound URLs and validates on-site links.
PUBLIC_URL_PATTERN = re.compile(r'(?i)(?<![\w@])(?:https?://|www\.)[^\s<>"\x27\[\]]*')
REDIRECT_QUERY_KEYS = {'url', 'u', 'redirect', 'redirect_url', 'target', 'destination', 'dest', 'next'}


def outbound_link_errors(body, rules):
    """Permit external HTTPS citations while rejecting unsafe outbound URLs.

    Do not require websites to be in a social/media domain allowlist. Retain
    the same API used by G5; internal links undergo separate publication checks.
    """
    own_host = urllib.parse.urlsplit(SITE).hostname
    violations = set()
    for match in PUBLIC_URL_PATTERN.finditer(html.unescape(body)):
        raw = match.group(0).rstrip('.,;:!?)]}')
        url = ('https://' + raw) if raw.lower().startswith('www.') else raw
        try:
            parsed = urllib.parse.urlsplit(url)
            host = (parsed.hostname or '').lower().rstrip('.')
            if host == own_host:
                continue
            safe = (parsed.scheme == 'https' and bool(host)
                    and not parsed.username and not parsed.password
                    and parsed.port in (None, 443))
            # A platform redirect link can conceal an unrelated destination.
            if any(key.lower() in REDIRECT_QUERY_KEYS
                   for key, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)):
                safe = False
        except ValueError:
            host, safe = 'invalid-url', False
        if not safe:
            violations.add('UNSAFE_OUTBOUND_URL:' + (host or 'invalid-url'))
    return sorted(violations)


def seo_onpage_score(meta, body, topic, internal, rules):
    """Intent-aware deterministic on-page checks, not a Google or Yoast score.

    Publication still requires every independently verified six-gate condition;
    a numerical score never overrides a hard FAIL/REVIEW. Do not mandate
    unnatural keyword density, a photo, a FAQ or a commercial rental CTA.
    """
    focus = {
        token for token in norm(topic.get('primary_keyword', '')).split()
        if token not in {
            'va', 'la', 'cua', 'cho', 'nhung', 'cac', 'mot', 'khi', 'the',
            'nao', 'gi', 'co', 'nen', 've', 'o', 'de', 'tren', 'voi', 'trong'
        }
    }

    def coverage(text):
        tokens = set(norm(str(text or '')).split())
        return len(focus & tokens) / max(1, len(focus))

    def relevance(text):
        ratio = coverage(text)
        if ratio >= 0.70:
            return 15
        if ratio >= 0.50:
            return 10
        if ratio >= 0.30:
            return 5
        return 0

    headings = re.findall(r'^##\s+(.+)$', body, re.M)
    useful_headings = {
        norm(heading) for heading in headings
        if len(norm(heading).split()) >= 4
    }
    introduction = body[:1800]
    opening = body.split('\n\n', 1)[0]
    answer = str(meta.get('direct_answer') or '').strip()
    answer_present = bool(answer and norm(answer) in norm(introduction))
    internal_targets = set()
    descriptive_anchors = set()
    for anchor, url in mdlinks(body):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme == 'https'
                and parsed.hostname == 'thuexemaynguyentu.com'
                and parsed.path not in ('', '/')
                and url in internal):
            internal_targets.add(url)
            anchor_normalized = norm(anchor)
            if (len(anchor_normalized.split()) >= 3
                    and anchor_normalized not in (
                        'xem them', 'tai day', 'bam vao day', 'click here'
                    )):
                descriptive_anchors.add(anchor_normalized)

    title_points = relevance(meta.get('meta_title'))
    description_points = relevance(meta.get('meta_description'))
    opening_points = relevance(opening)
    answer_points = (
        10 if answer_present and len(norm(answer).split()) >= 18
        else 5 if answer_present else 0
    )
    headings_points = (
        10 if len(useful_headings) >= rules['minimum_h2'] else 0
    ) + (5 if any(coverage(heading) >= 0.35 for heading in headings) else 0)
    links_points = (10 if internal_targets else 0) + (
        5 if len(internal_targets) >= 2 else 0
    )
    anchor_points = 5 if descriptive_anchors else 0
    canonical_points = (
        10 if (
            meta.get('canonical_target') == topic.get('canonical_target')
            and topic.get('canonical_target')
            == SITE + '/' + str(topic.get('proposed_slug', '')) + '/'
        ) else 0
    )
    scoring = {
        'seo_title_relevance': (
            title_points, 15, 'Align SEO title with real search intent'
        ),
        'meta_description_relevance': (
            description_points, 15, 'Summarize the reader question in the meta description'
        ),
        'opening_intent_focus': (
            opening_points, 15, 'Address the intended search in the opening paragraph'
        ),
        'direct_answer': (
            answer_points, 10, 'Add a substantive direct answer near the beginning'
        ),
        'headings_usefulness': (
            headings_points, 15, 'Use distinct descriptive H2s covering related subtopics'
        ),
        'verified_contextual_links': (
            links_points, 15, 'Add contextual links to real published related articles'
        ),
        'descriptive_anchor': (
            anchor_points, 5, 'Use descriptive internal anchor text'
        ),
        'canonical_identity': (
            canonical_points, 10, 'Keep WordPress canonical aligned with approved slug'
        ),
    }
    breakdown = {
        name: {'points': earned, 'max': maximum}
        for name, (earned, maximum, _) in scoring.items()
    }
    if sum(item['max'] for item in breakdown.values()) != 100:
        raise ValueError('SEO V2 rubric must total 100 points')
    recommendations = [
        advice for points, maximum, advice in scoring.values()
        if points < maximum
    ]
    return sum(item['points'] for item in breakdown.values()), breakdown, recommendations


def allowed_source(url, legal=False):
    """Accept safe public HTTPS sources from any relevant website.

    Source trust is editorial (G3), never determined by a manufacturer/news/
    competitor hostname list. Legal claims still need an official source.
    """
    import ipaddress
    try:
        u = urllib.parse.urlsplit(str(url))
        host = (u.hostname or '').lower().rstrip('.')
        if (u.scheme != 'https' or not host or u.username or u.password or
                u.port not in (None, 443) or
                host in ('localhost', 'news.google.com') or
                host.endswith(('.local', '.internal', '.test', '.invalid', '.onion'))):
            return False
        try:
            ipaddress.ip_address(host)
            return False  # Do not fetch direct IP or private network hosts.
        except ValueError:
            pass
        if not legal:
            return True
        official = load('config/qa-rules.json')['legal_hosts']
        return (host.endswith(('.gov.vn', '.gov')) or
                any(host == h or host.endswith('.' + h) for h in official))
    except (ValueError, TypeError):
        return False


def _reviewed_source_snapshot(source, trusted_research):
    """Fallback only to evidence captured when this topic was researched."""
    if not isinstance(source, dict) or not isinstance(trusted_research, list):
        return False
    sha = str(source.get('source_sha256', ''))
    if not re.fullmatch(r'[0-9a-f]{64}', sha):
        return False
    return any(isinstance(record, dict) and
               record.get('url') == source.get('url') and
               record.get('source_sha256') == sha and
               norm(record.get('evidence_text', '')) == norm(source.get('evidence_text', ''))
               for record in trusted_research)


TRANSIENT_HTTP=(408,425,429,500,502,503,504)
RETRY_DELAYS=(1,3)
EVIDENCE_REASONS=('reviewed full-content evidence stale or missing','nearest full content not reviewed')

def is_transient(exc):
    """Only a failure that can disappear by itself is worth another read; 403, 404, TLS and redirects are not."""
    if isinstance(exc,urllib.error.HTTPError):return exc.code in TRANSIENT_HTTP
    if isinstance(exc,urllib.error.URLError):
        return isinstance(exc.reason,(TimeoutError,ConnectionResetError,ConnectionAbortedError,ConnectionRefusedError)) or 'timed out' in str(exc.reason).lower()
    return isinstance(exc,(TimeoutError,ConnectionResetError,ConnectionAbortedError,http.client.RemoteDisconnected,http.client.IncompleteRead))

def failure_label(exc):
    name=type(exc).__name__
    if isinstance(exc,urllib.error.HTTPError):return name+' '+str(exc.code)
    if isinstance(exc,urllib.error.URLError):return name+' '+str(exc.reason)
    if isinstance(exc,(ValueError,RuntimeError)):return name+': '+str(exc)
    return name

# A host whose connection failed on every retry (typically a .gov.vn site that blocks or times out GitHub's runners) is
# not contacted again in this process: each further source on it would only burn another 3 x 20 s. The research
# snapshot fallback still applies, because the skipped read raises the same kind of transient URLError.
SOURCE_HOSTS_DOWN={}

def reset_source_host_cache():
    SOURCE_HOSTS_DOWN.clear()

SOURCE_BODY_MAX_BYTES = 8_000_000


def decode_source_body(raw, content_encoding=''):
    """Bounded decoding for compressed government pages, fail closed on bad input.

    Some official websites send GZIP bytes even when the client did not
    request compression. Decoding those bytes as UTF-8 destroys all text
    evidence and gives a false G3 REVIEW.
    """
    if not isinstance(raw, bytes) or len(raw) > SOURCE_BODY_MAX_BYTES:
        raise ValueError('Source body exceeds size limit')
    gzip_payload = raw.startswith(b'\x1f\x8b') or 'gzip' in content_encoding.lower()
    if gzip_payload:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(SOURCE_BODY_MAX_BYTES + 1)
        if len(raw) > SOURCE_BODY_MAX_BYTES:
            raise ValueError('Decompressed source exceeds size limit')
    return raw.decode('utf-8', errors='replace')


def read_source(url,attempts=3):
    """One live read exactly like the Publisher's; transient failures are retried up to `attempts` times."""
    host=(urllib.parse.urlsplit(url).hostname or '').lower()
    if host in SOURCE_HOSTS_DOWN:
        raise urllib.error.URLError(TimeoutError('timed out (host already unreachable in this run)'))
    for attempt in range(1,max(1,attempts)+1):
        try:
            opener=urllib.request.build_opener(Redirect())
            req=urllib.request.Request(url,headers={'User-Agent':'NguyenTu-WPWriter/1.0'})
            with opener.open(req,timeout=20) as response:
                raw = response.read(SOURCE_BODY_MAX_BYTES + 1)
                headers = getattr(response, 'headers', None)
                encoding = headers.get('Content-Encoding', '') if headers else ''
                return decode_source_body(raw, encoding),attempt
        except Exception as exc:
            if attempt>=attempts or not is_transient(exc):
                if host and is_transient(exc) and not isinstance(exc,urllib.error.HTTPError):
                    SOURCE_HOSTS_DOWN[host]=failure_label(exc)  # a server that answered (5xx/429) is not "down"
                raise
            time.sleep(RETRY_DELAYS[min(attempt-1,len(RETRY_DELAYS)-1)])


def source_excerpt_matches(excerpt, source_text):
    """Match real source prose, including a long excerpt clipped mid-final-word.

    Research snapshots sometimes end at an arbitrary character limit (for
    example a law excerpt ending at "lo" instead of "loại"). Require the
    entire preceding sequence of words to occur in the actual fetched page
    and the final fragment to prefix the immediately following source word.
    Short excerpts, missing words, and non-prefix substitutions remain REVIEW.
    """
    needle = norm(excerpt)
    page = norm(source_text)
    # The normal case must end at a source word boundary. Plain substring
    # matching incorrectly accepted tiny snippets such as "...đủ tu"
    # against a page containing "...đủ tuổi".
    if needle and (' ' + needle + ' ') in (' ' + page + ' '):
        return True
    parts = needle.split()
    if len(parts) < 24 or len(excerpt.strip()) < 120:
        return False
    final_fragment = parts[-1]
    if len(final_fragment) < 2 or not excerpt.strip()[-1].isalnum():
        return False
    complete_prefix = ' '.join(parts[:-1]) + ' '
    offset = 0
    while True:
        pos = page.find(complete_prefix, offset)
        if pos < 0:
            return False
        remainder = page[pos + len(complete_prefix):]
        next_word = remainder.split(' ', 1)[0]
        if len(next_word) > len(final_fragment) and next_word.startswith(final_fragment):
            return True
        offset = pos + 1


def verify_sources(sources, live=False, trusted_research=None, legal=False):
    """Live-check when possible; preserve a clearly marked researched snapshot
    on transient network errors. An unreachable source is not a fake live check.
    Missing, altered or unsupported evidence still requires review.
    """
    import urllib.error
    errors = []
    evidence = []
    rules = load('config/qa-rules.json')
    for s in sources:
        if not isinstance(s, dict) or not allowed_source(s.get('url', '')):
            errors.append('Source URL is not safe public HTTPS')
            continue
        try:
            checked = dt.date.fromisoformat(str(s.get('checked_at', ''))[:10])
            age = (dt.date.today() - checked).days
            maximum = rules.get('legal_source_max_age_days', 90) if legal and allowed_source(s.get('url',''), True) else rules['source_max_age_days']
            if age < 0 or age > maximum:
                raise ValueError('Source checked_at stale or future')
            if (not s.get('supports') or not s.get('evidence_text') or
                    len(str(s['evidence_text']).split()) < 4):
                raise ValueError('Source claim/evidence missing')
            if not re.fullmatch(r'[a-f0-9]{64}', str(s.get('source_sha256', ''))):
                raise ValueError('Unverified source snapshot hash')
            if not live:
                continue
            try:
                # Transient failures are re-read up to live_retry_attempts times before the snapshot fallback is considered.
                raw, attempt = read_source(s['url'], rules.get('live_retry_attempts', 3))
                text = visible(raw)
                if not source_excerpt_matches(s['evidence_text'], text):
                    raise ValueError('Source excerpt not found')
                evidence.append({'url': s['url'], 'supports': s['supports'],
                                 'sha256': digest(text), 'verified_at': now(),
                                 'verification_method': 'live', 'live_checked': True,
                                 **({'attempts': attempt} if attempt > 1 else {})})
            except (OSError, urllib.error.URLError) as exc:
                transient = not isinstance(exc, urllib.error.HTTPError) or exc.code in (403, 429, 500, 502, 503, 504)
                if transient and _reviewed_source_snapshot(s, trusted_research):
                    evidence.append({'url': s['url'], 'supports': s['supports'],
                                     'sha256': s['source_sha256'],
                                     'research_checked_at': s['checked_at'],
                                     'verification_method': 'research_snapshot_fallback',
                                     'live_checked': False,
                                     'network_error': type(exc).__name__})
                else:
                    raise
        except Exception as exc:
            errors.append('Source REVIEW: ' + failure_label(exc))
    return errors, evidence


def evidence_recheck(topic,rows,inv,body_shingles,identity,rules,page_shingles=shingles):
    """G4 found nearest pages without review evidence (new, or edited after the research): re-read them against THIS article.

    Not a bypass: a page is lifted only when its text overlap with the article stays under `max_jaccard` AND the
    full-corpus intent guard finds no search-intent match with it. Any overlap keeps the evidence reasons (the article
    stays held as a duplicate-intent risk). The measurement is stored in the QA record.
    """
    pages=identity.get('evidence_pages') or {}
    ids=sorted(set(pages.get('stale',[]))|set(pages.get('unreviewed',[])))
    cfg=rules.get('evidence_recheck') or {}
    if not ids or cfg.get('enabled',True) is False:return None
    from intent_guard import IntentIndex
    limit=float(cfg.get('max_jaccard',0.25))
    matched={m['id']:m['severity'] for m in IntentIndex(inv,rows).matches(topic)}
    by={p['id']:p for p in inv}
    checked=[]
    for pid in ids:
        page=by.get(pid) or {}
        overlap=jaccard(body_shingles,page_shingles(page['content_text'])) if page.get('content_text') else None
        hit=matched.get('WP'+str(pid))
        checked.append({'id':pid,'title':page.get('title'),'why':'stale' if pid in pages.get('stale',[]) else 'unreviewed',
            'content_hash':page.get('content_hash'),'jaccard':None if overlap is None else round(overlap,3),'intent_match':hit,
            'verdict':'OVERLAP' if hit or (overlap is not None and overlap>=limit) else 'INDEPENDENT'})
    return {'pages':checked,'independent':all(c['verdict']=='INDEPENDENT' for c in checked),'max_jaccard':limit,
            'method':'text overlap with this article + full-corpus intent guard; evidence reasons lifted only when every page is independent'}

def business_errors(body,meta):
    facts=load('data/business-facts.json');errors=[]
    for phone in re.findall(r'(?<!\d)(?:\+84|0)[\d .-]{8,15}\d(?!\d)',body):
        value=re.sub(r'\D','',phone)
        if len(value) in (10,11) and value not in ('0942467674','84942467674'):errors.append('Unverified phone number')
    n=norm(body)
    if 'nguyen tu' in n:
        for bad in ('mien coc','khong can dat coc','mien phi giao xe','24/7','24 gio'):
            if bad in n:errors.append('Unverified business offer:'+bad)
        for match in re.finditer(r'\b(\d+)\s+nguyen van cu',n):
            if match.group(1)!='112':errors.append('Business address mismatch')
    flat={'phone':facts['phone'],'address':facts['address'],'hours':facts['hours'],'deposit_vnd':facts['deposit_vnd']}
    for claim in meta.get('business_claims',[]):
        if claim.get('key') in flat:
            if claim.get('value')!=flat[claim['key']]:errors.append('Business fact mismatch:'+claim['key'])
        elif claim.get('key','').startswith('price:'):
            _,model,period=claim['key'].split(':')
            found=[p for p in facts['prices'] if p['model']==model]
            if not found or found[0].get(period)!=claim.get('value'):errors.append('Business price mismatch')
        else:errors.append('Unknown business fact key')
    # Explicit rental price claims must match the central rate for the period.
    for p in facts['prices']:
        short=norm(p['model'].replace('Honda ',''))
        for line in body.splitlines():
            if short in norm(line) and re.search(r'thuê|Nguyễn Tú',line,re.I):
                for amount,period in re.findall(r'(\d[\d.,]*)\s*(?:đ|đồng|vnd)\s*/?\s*(ngày|tuần|tháng)',line,re.I):
                    value=int(re.sub(r'\D','',amount));expected=p[{'ngày':'day_vnd','tuần':'week_vnd','tháng':'month_vnd'}[period.lower()]]
                    if expected is None or (isinstance(expected,list) and not expected[0]<=value<=expected[-1]) or (isinstance(expected,int) and value!=expected):errors.append('Wrong rental rate:'+p['model'])
    return errors

def evaluate(path,topic,rows=None,inv=None,link_checker=None,live=False,check_claim=True):
    rules=load('config/qa-rules.json');rows=rows if rows is not None else topics()
    inv=inv if inv is not None else load('data/existing-content-inventory.json',{}).get('items',[])
    ledger=load('data/state/publication-ledger.json',{})
    inv=drop_own_post(exempt_factory_posts(inv,ledger),ledger,topic['topic_id'])
    gates={str(i):{'errors':[],'review':[]} for i in range(1,7)}
    try:meta,body,sha=read_article(path)
    except Exception as e:return {'topic_id':topic['topic_id'],'status':'FAIL','errors':[str(e)],
        'review':[],'source_sha256':digest(path.read_bytes()),'gates':gates,'at':now()}
    g1=gates['1'];g2=gates['2'];g3=gates['3'];g4=gates['4'];g5=gates['5'];g6=gates['6']
    g1['errors'].extend(proposed_slug_errors(topic))
    if topic.get('campaign_id') == 'HN-51-WARDS' or str(topic.get('proposed_slug', '')).startswith('thue-xe-may-phuong-'):
        if topic.get('taxonomy_key') != 'hanoi-ward-rentals':
            g6['errors'].append('HANOI_WARD_CATEGORY_MISMATCH: must use hanoi-ward-rentals')
        if meta.get('taxonomy_key') != 'hanoi-ward-rentals':
            g6['errors'].append('HANOI_WARD_ARTICLE_CATEGORY_MISMATCH')
    for k in ('topic_id','title','primary_keyword','search_intent','taxonomy_key','canonical_target'):
        if meta.get(k)!=topic.get(k):g1['errors'].append('Manifest mismatch:'+k)
    if path.name!=topic['topic_id']+'.md':g1['errors'].append('Wrong draft path')
    if topic.get('topic_qa_status')!='PLANNED':g1['errors'].append('Topic not PLANNED')
    wc=word_count(body)
    if not rules['word_min']<=wc<=rules['word_max']:g2['errors'].append('Word count outside 1600..5000:'+str(wc))
    if re.search(r'<[!/]?[A-Za-z][^>]*>|javascript:|data:|vbscript:',html.unescape(body),re.I):g2['errors'].append('Raw HTML/unsafe URL forbidden')
    if re.search(r'(?i)\b(TODO|TBD|lorem ipsum|placeholder)\b|\[chèn',body):g2['errors'].append('Placeholder')
    if len(re.findall(r'^##\s',body,re.M))<rules['minimum_h2']:g2['errors'].append('Insufficient H2 sections')
    if re.search(r'^#\s',body,re.M):g2['errors'].append('Duplicate H1; WP title owns H1')
    if not 15<=len(str(meta.get('meta_title','')))<=rules['seo_meta_title_max']:g2['errors'].append('Meta title length')
    if not rules['seo_meta_description_min']<=len(str(meta.get('meta_description','')))<=rules['seo_meta_description_max']:g2['errors'].append('Meta description length')
    paragraphs=[norm(p) for p in body.split('\n\n') if len(norm(p).split())>15]
    if len(paragraphs)!=len(set(paragraphs)):g2['errors'].append('Repeated paragraph')
    sentences=[norm(s) for s in re.split(r'[.!?\n]+',body) if len(norm(s).split())>10]
    if sentences and max(Counter(sentences).values())>=3:g2['errors'].append('Repeated sentence')
    key=norm(topic['primary_keyword']);total=norm(body)
    if key and total.count(key)*max(1,len(key.split()))/max(1,wc)>0.07:g2['errors'].append('Keyword stuffing')
    if not meta.get('direct_answer') or norm(meta['direct_answer']) not in norm(body[:1800]):g2['review'].append('Direct answer not evidenced')
    for alt,url in re.findall(r'!\[([^\]]*)\]\(([^)]+)\)',body):
        if not alt.strip():g2['errors'].append('Image alt missing')
    review=meta.get('editorial_review',{})
    if (not review.get('reviewer') or review.get('body_sha256')!=digest(body) or
        not all(review.get(k) is True for k in ('intent_covered','substantive','facts_checked','no_fabricated_experience','collision_reviewed'))):
        g3['review'].append('External writer editorial/factual evidence missing or stale')
    g3['errors']+=business_errors(body,meta)
    legal=bool(re.search(r'luật|nghị định|mức phạt|bằng lái|giấy phép|quy định pháp',body,re.I))
    sources=meta.get('sources',[])
    if legal and not any(allowed_source(s.get('url',''),True) for s in sources):g3['review'].append('Legal claim needs current official source')
    source_errors,source_evidence=verify_sources(
        sources,live,trusted_research=(topic.get('research') or {}).get('external_sources',[]),
        legal=legal)
    g3['review']+=source_errors
    if re.search(r'\d',body) and not sources and not meta.get('business_claims'):g3['review'].append('Numeric claims need cited evidence')
    if re.search(r'(?i)tôi đã (?:thử|chạy|trải nghiệm)|khách hàng đánh giá 5|100% an toàn',body):g3['review'].append('Unverified experience/review/absolute claim')
    identity=topic_gate(topic,rows,inv,load('data/taxonomy.json')['items'])
    g4['errors']+=identity['errors'];g4['review']+=identity['review']
    body_shingles=fingerprint(counted_text(body))
    for p in inv:
        if p.get('content_text') and jaccard(body_shingles,fingerprint(p['content_text']))>=rules['near_duplicate_jaccard']:
            g4['errors'].append('Near duplicate existing:'+str(p['id']))
    for other in (ROOT/'posts/drafts').glob('NT-*.md'):
        if other.resolve()==path.resolve():continue
        other_shingles=draft_fingerprint(other)
        if other_shingles is None:continue
        if jaccard(body_shingles,other_shingles)>=rules['near_duplicate_jaccard']:g4['errors'].append('Near duplicate draft:'+other.name)
    recheck=evidence_recheck(topic,rows,inv,body_shingles,identity,rules,page_shingles=fingerprint)
    if recheck and recheck['independent']:
        g4['review']=[r for r in g4['review'] if not r.startswith(EVIDENCE_REASONS)]
    public_urls={p.get('url') for p in inv if p.get('status')=='publish'}|{SITE+'/'}
    links=mdlinks(body);internal=[]
    g5['errors'].extend(outbound_link_errors(body,rules))
    for anchor,url in links:
        parsed=urllib.parse.urlsplit(url)
        if not anchor.strip():g5['errors'].append('Empty anchor')
        if parsed.scheme not in ('http','https') or parsed.username:g5['errors'].append('Invalid URL');continue
        if parsed.hostname=='thuexemaynguyentu.com':
            internal.append(url)
            if parsed.query:g5['errors'].append('Query/draft internal URL forbidden:'+url)
            clean=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))
            if clean not in public_urls:g5['errors'].append('Internal target not verified public:'+clean)
            elif live:
                try:
                    page,_=WP().request(clean,public=True,page=True)
                    if re.search(r'<meta[^>]+(?:noindex|http-equiv=[\"\']refresh)',page,re.I):g5['errors'].append('Link target not indexable')
                except Exception:g5['errors'].append('Broken internal link:'+clean)
            elif link_checker and not link_checker(clean):g5['errors'].append('Broken internal link:'+clean)
    if not internal:g5['errors'].append('Orphan: no public internal link')
    if internal.count(SITE+'/')>1:g5['errors'].append('Homepage link repetition')
    # Internal URLs still must exist. The candidate list is editorial guidance,
    # not an immutable whitelist that blocks newly relevant published pages.
    # Link rationale is recommended, not an article-publication hard gate.
    try:path_for(topic['taxonomy_key'],by_key())
    except ValueError as e:g6['errors'].append(str(e))
    if topic.get('wp_post_id') in load('data/protected-urls.json',{}).get('protected_test_ids',[3861]):g6['errors'].append('Protected legacy post')
    if check_claim:
        receipt=load('data/state/writer-claims.json',{}).get('submissions',{}).get(topic['topic_id'],{})
        if receipt and (receipt.get('sha256')!=sha or receipt.get('session')!=meta.get('writer_session')):g6['errors'].append('Submission owner/hash mismatch')
    quality=max(0,100-len(g2['errors'])*15-len(g3['review'])*15-len(g3['errors'])*25)
    seo, seo_checks, seo_recommendations = seo_onpage_score(meta,body,topic,internal,rules)
    if seo < rules['seo_min']:
        g2['errors'].append('SEO_SCORE_BELOW_MIN:'+str(seo)+'/'+str(rules['seo_min']))
    errors=[e for gate in gates.values() for e in gate['errors']]
    reviews=[e for gate in gates.values() for e in gate['review']]
    status='FAIL' if errors or quality < rules['quality_min'] else 'REVIEW' if reviews else 'PASS'
    return {'topic_id':topic['topic_id'],'status':status,'source_sha256':sha,'body_sha256':digest(body),'word_count':wc,
        'quality_score':quality,'seo_score':seo,'seo_min_required':rules['seo_min'],
        'seo_checks':seo_checks,'seo_recommendations':seo_recommendations,
        'gates':gates,'errors':errors,'review':reviews,'source_evidence':source_evidence,
        'evidence_recheck':recheck,
        'at':now(),'live_links_checked':live,'legal_required':legal,'rules_sha256':digest(json.dumps(rules,sort_keys=True)),
        'inventory_sha256':digest(json.dumps(inv,ensure_ascii=False,sort_keys=True))}


def evaluate_safely(path,topic,rows,live=False,inv=None):
    """evaluate() that turns an unexpected crash into a FAIL ticket for this article only."""
    kwargs={'rows':rows,'live':live}
    if inv is not None:kwargs['inv']=inv
    try:return evaluate(path,topic,**kwargs)
    except Exception as exc:
        return {'topic_id':topic['topic_id'],'status':'FAIL','source_sha256':digest(path.read_bytes()),
                'errors':['QA evaluation crashed: '+type(exc).__name__+': '+str(exc)[:160]],'review':[],'at':now()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true')
    p.add_argument('--incremental',action='store_true',help='reuse hash-valid stored records (frozen published, cached unchanged); evaluate only new/changed drafts')
    a=p.parse_args()
    rows=topics();results=[];reused=0
    inv=load('data/existing-content-inventory.json',{}).get('items',[])  # read once, not once per draft
    # Incremental sweep: a VERIFIED article with the same source hash, or an unchanged draft with the same rules and
    # topic row, keeps its stored record; qa_gate.validate_complete still hash-checks every record afterwards.
    keep={}
    if a.incremental:
        from qa_incremental import plan,incremental_key,rules_digest
        p_=plan(rows=rows)
        keep={i:'FROZEN' for i in p_['frozen']};keep.update({i:'CACHED' for i in p_['cached']})
        rules_sha=rules_digest(load('config/qa-rules.json'))
    for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
        match=[t for t in rows if t['topic_id']==path.stem]
        if path.stem in keep:
            stored=load('data/qa/'+path.stem+'.json')
            if isinstance(stored,dict) and stored.get('source_sha256')==digest(path.read_bytes()):
                results.append(stored);reused+=1;continue
        if len(match)!=1:
            # A stray draft is a FAIL ticket for that file only; it must not stop QA for every other article.
            r={'topic_id':path.stem,'status':'FAIL','source_sha256':digest(path.read_bytes()),
               'errors':['Unknown or ambiguous draft ID'],'review':[],'at':now()}
        else:
            r=evaluate_safely(path,match[0],rows,live=a.live,inv=inv)
            if a.incremental:r['incremental_key']=incremental_key(r['source_sha256'],rules_sha,match[0])
        previous=load('data/qa/'+path.stem+'.json') if a.incremental else None
        annotate(r,previous if isinstance(previous,dict) else None)
        save('data/qa/'+path.stem+'.json',r);results.append(r)
    save('reports/repair-queue.json',[r for r in results if r['status']!='PASS'])
    print(json.dumps({'authored':len(results),'pass':sum(r['status']=='PASS' for r in results),'repair':sum(r['status']!='PASS' for r in results),'reused':reused,'evaluated':len(results)-reused}))
    return 1 if any(r['status']!='PASS' for r in results) else 0

if __name__=='__main__':raise SystemExit(main())
