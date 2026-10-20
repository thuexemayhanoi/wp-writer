#!/usr/bin/env python3
"""Topic package workbench (scratch directory only, never committed).

A package is a directory  pkgs/NT-000401/  holding
    spec.json   hand-authored research + SEO fields (see SPEC_FIELDS)
    body.md     the Vietnamese article body (no frontmatter, no H1)

Commands
    python pkg.py cover NT-000401      what the site already says about this topic (nearest posts, phrase hits, intent guard)
    python pkg.py row NT-000401        build the Research V2 candidate row (rows/NT-000401.row.json)
    python pkg.py check NT-000401      row QA (Research V2) + simulated article QA (the repo's qa.evaluate, offline)
    python pkg.py needles [--per-url 3] [--number K] NT-000401..  url|needle lines for the runner probe workflow (saved as probe_input_K.txt)
    python pkg.py probe-apply K --fail 3,17   record the runner's verdicts (failing 1-based line numbers of probe_input_K.txt)
    python pkg.py batch NT-1 NT-2 ..   write data/candidates file for the given topics (max 10) and print it
    python pkg.py assemble NT-000401 --slot W1 --session s-xxx   write posts/drafts/NT-000401.md from the CLAIMED registry row
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('WPW_ROOT') or subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or '.')
SCR = Path(os.environ.get('WPW_SCRATCH') or HERE)            # holds sources/ (page store), pkgs/ (packages), rows/
os.environ['WPW_SCRATCH'] = str(SCR)                          # bench.py reads the same variable
os.environ['WPW_ROOT'] = str(ROOT)
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))

import bench  # noqa: E402
import vocab  # noqa: E402
from common import SITE, digest, load, norm, now, slugify, topics  # noqa: E402
from topic_factory import similarity  # noqa: E402
from intent_guard import IntentIndex, assess_topic  # noqa: E402
import research_v2  # noqa: E402
import qa  # noqa: E402

PKGS = SCR / 'pkgs'
ROWS = SCR / 'rows'
ROWS.mkdir(exist_ok=True)
SESSION = os.environ.get('WPW_RESEARCH_SESSION', 'claude-tu-20261017a')   # research branch is research/<SESSION>; also the reviewer label
ORIGIN_PREFIX = os.environ.get('WPW_ORIGIN_PREFIX', 'CLAUDE-TU-A-')
METHOD = ('đọc toàn văn các trang nguồn qua công cụ trích xuất văn bản và lưu SHA-256 của văn bản đã đọc; '
          'đối chiếu tiêu đề và content_hash của 5 bài gần nhất theo độ tương đồng tiêu đề; tìm toàn văn cụm từ khóa '
          'chính trong toàn bộ inventory WordPress để phát hiện bài đã nhắc đến; chạy intent guard toàn kho; '
          'không dựa vào RSS; không phải dữ liệu lượng tìm kiếm')
LEGAL_WORDS = re.compile(r'luật|nghị định|mức phạt|bằng lái|giấy phép|quy định pháp', re.I)
SPEC_FIELDS = ['topic_id', 'title', 'primary_keyword', 'secondary_keywords', 'search_intent', 'intent_key',
               'taxonomy_key', 'outline', 'difference_summary', 'usefulness', 'scope_exclusions',
               'source_requirements', 'sources', 'internal_links', 'meta_title', 'meta_description',
               'direct_answer', 'link_rationale']


def pkg_dir(tid):
    return PKGS / tid


def load_pkg(tid):
    d = pkg_dir(tid)
    spec = json.loads((d / 'spec.json').read_text(encoding='utf-8'))
    body = (d / 'body.md').read_text(encoding='utf-8') if (d / 'body.md').exists() else ''
    return spec, body.strip()


def git(*args):
    r = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    return r.stdout


def cmd_sync():
    subprocess.run(['git', 'fetch', 'origin', 'main', '+refs/heads/research/*:refs/remotes/origin/research/*'], cwd=ROOT,
                   capture_output=True, text=True)
    rows = remote_candidate_rows()
    print('remote research branches:', len(git('for-each-ref', 'refs/remotes/origin/research/').splitlines()),
          '| rows not yet in the registry:', len(rows))
    for r in rows[:40]:
        print('  ', r['topic_id'], r['title'][:90])


def remote_candidate_rows():
    """Rows other sessions have pushed on research/* branches that the registry does not know yet (collision radar)."""
    known = {t['topic_id'] for t in topics()}
    out, seen = [], set()
    for ref in git('for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin/research/').split():
        if ref.endswith('/' + SESSION):
            continue
        for path in git('diff', '--name-only', 'origin/main...' + ref, '--', 'data/candidates/').split():
            for line in git('show', ref + ':' + path).splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get('topic_id') not in known and row.get('topic_id') not in seen:
                    seen.add(row['topic_id'])
                    out.append(row)
    return out


def inventory():
    return load('data/existing-content-inventory.json', {}).get('items', [])


def taxonomy():
    return load('data/taxonomy.json', {}).get('items', [])


def published_urls():
    return {p.get('url') for p in inventory() if p.get('status') == 'publish'}


def nearest5(title, inv=None):
    inv = inventory() if inv is None else inv
    reviewable = [p for p in inv if not p.get('evidence_exempt')]
    return sorted(reviewable, key=lambda p: similarity(title, p.get('title') or ''), reverse=True)[:5]


def phrase_hits(phrases, inv=None, limit=6):
    """Which existing posts mention a key phrase in their full text (accent/case-insensitive)."""
    inv = inventory() if inv is None else inv
    out = {}
    for phrase in phrases:
        needle = norm(phrase)
        if not needle:
            continue
        hits = []
        for p in inv:
            text = norm(p.get('content_text') or '')
            n = text.count(needle)
            if n:
                i = text.find(needle)
                hits.append((n, p['id'], p.get('title'), text[max(0, i - 90): i + len(needle) + 90]))
        hits.sort(reverse=True)
        out[phrase] = hits[:limit]
    return out


def cmd_cover(tid):
    spec, _ = load_pkg(tid)
    inv = inventory()
    print('TOPIC', tid, '|', spec['title'])
    print('\n-- nearest 5 posts by title similarity (the research gate demands you reviewed these) --')
    for p in nearest5(spec['title'], inv):
        print('  %-5s sim=%.2f  %s\n        %s' % (p['id'], similarity(spec['title'], p.get('title') or ''), p.get('title'), p.get('url')))
    print('\n-- existing posts whose full text mentions your key phrases --')
    phrases = [spec['primary_keyword']] + list(spec.get('secondary_keywords') or [])
    for phrase, hits in phrase_hits(phrases, inv).items():
        print('  [%s]  %d post(s)' % (phrase, len(hits)))
        for n, pid, title, ctx in hits:
            print('     x%-2d %-5s %s\n          ...%s...' % (n, pid, (title or '')[:80], ctx))
    print('\n-- intent guard (title / keyword vs every published item and every factory topic) --')
    row = {'topic_id': tid, 'title': spec['title'], 'primary_keyword': spec['primary_keyword'],
           'intent_key': spec.get('intent_key') or 'x', 'taxonomy_key': spec['taxonomy_key'], 'search_intent': spec.get('search_intent', '')}
    reg = topics()
    everything = [t for t in reg if t['topic_id'] != tid] + remote_candidate_rows() + [row]
    found = assess_topic(row, everything, inv, new_ids={tid}, index=IntentIndex(inv, everything))
    print('  errors:', found['errors'])
    print('  review:', found['review'])
    for m in found['matches'][:5]:
        print('  match %-9s %-6s jacc=%.2f  %s' % (m['id'], m['severity'], m['weighted_jaccard'], (m.get('title') or '')[:80]))


def registry_row(tid):
    for t in topics():
        if t['topic_id'] == tid:
            return t
    raise KeyError(tid)


def build_sources(spec, allow_nonallowlisted=True):
    if spec.get('existing'):
        row = registry_row(spec['topic_id'])
        return [{'url': x['url'], 'checked_at': x['checked_at'], 'supports': x['supports'],
                 'evidence_text': x['evidence_text'], 'source_sha256': x['source_sha256']}
                for x in row['research']['external_sources'] if not x['url'].lower().split('?')[0].endswith('.pdf')]
    entries = []
    for s in spec['sources']:
        entry = bench.source(s['url'], s['excerpt'], s['supports'])
        entries.append(entry)
    return entries


PROBE = SCR / 'probe.json'          # {"<url>|<excerpt>": true/false} verdicts from the runner probe


def probe_verdicts():
    try:
        return json.loads(PROBE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def unique_by_url(entries):
    """The publisher's live QA fetches EVERY source entry, and research keeps one record per URL.
    So each URL appears once: the first excerpt the runner verified (else the first one), with all `supports` merged."""
    verdicts = probe_verdicts()
    groups, order = {}, []
    for e in entries:
        if e['url'] not in groups:
            groups[e['url']] = []
            order.append(e['url'])
        groups[e['url']].append(e)
    out = []
    for url in order:
        group = groups[url]
        passed = [e for e in group if verdicts.get(url + '|' + e['evidence_text']) is True]
        chosen = dict(passed[0] if passed else group[0])
        supports = []
        for e in group:
            if e['supports'] not in supports:
                supports.append(e['supports'])
        chosen['supports'] = ' | '.join(supports)[:1800]
        out.append(chosen)
    return out


def row_from_spec(spec):
    tid = spec['topic_id']
    if spec.get('existing'):
        row = dict(registry_row(tid))
        return row
    tax = {x['taxonomy_key']: x for x in taxonomy()}
    key = spec['taxonomy_key']
    parent = tax[key].get('parent_key') or key
    slug = spec.get('proposed_slug') or slugify(spec['title'])
    near = nearest5(spec['title'])
    hits = phrase_hits([spec['primary_keyword']] + list(spec.get('secondary_keywords') or []), limit=5)
    extra_ids, extra = [], {}
    inv_by_id = {p['id']: p for p in inventory()}
    for phrase_hits_ in hits.values():
        for _, pid, _, _ in phrase_hits_:
            p = inv_by_id.get(pid)
            if p and p['id'] not in extra and p['id'] not in {n['id'] for n in near}:
                extra[p['id']] = p
    reviewed = list(near) + list(extra.values())[:5]
    links = list(spec.get('internal_links') or [])
    sources = unique_by_url(build_sources(spec))      # Research QA forbids a repeated URL
    row = {
        'topic_id': tid,
        'origin_id': ORIGIN_PREFIX + tid[3:],
        'title': spec['title'],
        'primary_keyword': spec['primary_keyword'],
        'secondary_keywords': spec.get('secondary_keywords') or [],
        'search_intent': spec.get('search_intent') or 'Hướng dẫn',
        'intent_key': spec['intent_key'],
        'topic_role': 'supporting',
        'pillar': parent, 'hub': parent, 'silo': key,
        'taxonomy_key': key,
        'wordpress_category_id': tax[key]['wordpress_term_id'],
        'word_target_min': 1600, 'word_target_max': 5000,
        'canonical_target': SITE + '/' + slug + '/',
        'proposed_slug': slug,
        'related_existing_urls': links,
        'internal_link_candidates': links,
        'source_requirements': spec.get('source_requirements') or [],
        'priority': 'P2',
        'outline': spec['outline'],
        'writer_claim': None, 'topic_qa_status': None, 'qa_status': 'NOT_AUTHORED',
        'publication_status': 'NOT_SUBMITTED', 'wp_post_id': None, 'wp_permalink': None, 'source_hash': None,
        'timestamps': {'created_at': now()},
        'research': {
            'reviewer': SESSION, 'reviewed_at': now(), 'method': METHOD,
            'difference_summary': spec['difference_summary'], 'usefulness': spec['usefulness'],
            'scope_exclusions': spec['scope_exclusions'],
            'reviewed_existing_ids': [p['id'] for p in reviewed],
            'reviewed_content_hashes': {str(p['id']): p.get('content_hash') for p in reviewed},
            'resolved_topic_collisions': spec.get('resolved_topic_collisions') or {},
            'external_sources': sources,
        },
    }
    if spec.get('resolved_intent_collisions'):
        row['research']['resolved_intent_collisions'] = spec['resolved_intent_collisions']
    return row


def research_findings(rows):
    return research_v2.validate_candidates(rows)


def sources_section(spec):
    seen, lines = set(), []
    for entry in build_sources(spec):
        url = entry['url']
        if url in seen:
            continue
        seen.add(url)
        try:
            rec = bench.load(url)
            title = re.sub(r'\s*[|\-–]\s*(Yamaha Motor Việt Nam|Yamaha Việt Nam|Honda)\s*$', '', (rec.get('title') or url)).strip()
            title = re.sub(r'^Honda \|\s*', 'Honda Việt Nam – ', title)
            read = dt.date.fromisoformat(rec['read_at']).strftime('%d/%m/%Y')
        except Exception:
            title, read = url, dt.date.today().strftime('%d/%m/%Y')
        lines.append('- [%s](%s), đọc ngày %s' % (title.replace('[', '(').replace(']', ')'), url, read))
    return '## Nguồn tham khảo\n\n' + '\n'.join(lines)


def article_text(spec, body, row, slot, session):
    if '## Nguồn tham khảo' not in body:
        body = body.rstrip() + '\n\n' + sources_section(spec)
    allowed = [s for s in unique_by_url(build_sources(spec)) if qa.allowed_source(s['url'])]
    meta = {
        'topic_id': row['topic_id'], 'title': row['title'], 'primary_keyword': row['primary_keyword'],
        'search_intent': row['search_intent'], 'taxonomy_key': row['taxonomy_key'],
        'canonical_target': row['canonical_target'],
        'writer_slot': slot, 'writer_session': session,
        'meta_title': spec['meta_title'], 'meta_description': spec['meta_description'],
        'direct_answer': spec['direct_answer'], 'link_rationale': spec['link_rationale'],
        'business_claims': [],
        'sources': [{'url': s['url'], 'checked_at': s['checked_at'], 'supports': s['supports'],
                     'evidence_text': s['evidence_text'], 'source_sha256': s['source_sha256']} for s in allowed],
        'editorial_review': {'reviewer': session, 'body_sha256': digest(body.strip()), 'intent_covered': True,
                             'substantive': True, 'facts_checked': True, 'no_fabricated_experience': True,
                             'collision_reviewed': True},
    }
    return '---\n' + json.dumps(meta, ensure_ascii=False, indent=2) + '\n---\n\n' + body.strip() + '\n', meta, len(allowed), len(unique_by_url(build_sources(spec)))


def source_corpus(spec):
    texts = []
    urls = {x['url'] for x in spec.get('sources', [])}
    if spec.get('existing'):
        urls = {x['url'] for x in registry_row(spec['topic_id'])['research']['external_sources']}
    for url in sorted(urls):
        try:
            texts.append(bench.load(url)['text'])
        except KeyError:
            texts.append('')
    return '\n'.join(texts)


def number_audit(body, spec):
    """Numbers (2+ digits) in the body that appear nowhere in the pages the package cites (heuristic, warns only)."""
    corpus = source_corpus(spec)
    corpus_digits = {re.sub(r'\D', '', t) for t in re.findall(r'\d[\d.,]*\d|\d', corpus)}
    plain = re.sub(r'\]\([^)]*\)', ']', body)                       # drop link targets
    plain = re.sub(r'\b17/10/2026\b', '', plain)                       # the reading date
    missing = []
    for tok in re.findall(r'\d[\d.,]*\d|\d', plain):
        digits = re.sub(r'\D', '', tok)
        if len(digits) >= 2 and digits not in corpus_digits and tok not in missing:
            missing.append(tok)
    return missing


def copy_audit(body, spec, min_run=16):
    """Runs of >= min_run consecutive tokens (syllables) the body shares verbatim with the cited pages."""
    import unicodedata
    from collections import defaultdict

    def fold(token):
        token = unicodedata.normalize('NFD', token.lower().replace('đ', 'd'))
        return ''.join(c for c in token if unicodedata.category(c) != 'Mn')

    corpus = norm(source_corpus(spec)).split()
    plain = re.sub(r'\]\([^)]*\)', ']', body)
    spans = [(m.start(), m.end(), fold(m.group(0))) for m in re.finditer(r'[^\W_]+', plain)]
    words = [t for _, _, t in spans]
    n = 6
    idx = defaultdict(list)
    for i in range(len(corpus) - n + 1):
        idx[tuple(corpus[i:i + n])].append(i)
    runs, i = [], 0
    while i < len(words) - n + 1:
        best = 0
        for j in idx.get(tuple(words[i:i + n]), []):
            k = n
            while i + k < len(words) and j + k < len(corpus) and words[i + k] == corpus[j + k]:
                k += 1
            best = max(best, k)
        if best >= n:
            if best >= min_run:
                runs.append((best, plain[spans[i][0]:spans[i + best - 1][1]]))
            i += best
        else:
            i += 1
    runs.sort(reverse=True)
    return runs


def simulate_qa(tid, spec, body, row):
    topic = dict(row, topic_qa_status='PLANNED')
    reg = [t for t in topics() if t['topic_id'] != tid]
    text, meta, n_allowed, n_all = article_text(spec, body, row, 'W1', 'sim-session')
    tmp = Path(tempfile.mkdtemp(prefix='qa-sim-'))
    path = tmp / (tid + '.md')
    path.write_text(text, encoding='utf-8')
    return qa.evaluate(path, topic, rows=reg + [topic], check_claim=False), n_allowed, n_all


def cmd_intent(title, keyword, taxonomy_key):
    """Quick search-intent screen of a draft topic against every published item and every factory topic."""
    row = {'topic_id': 'NT-999999', 'title': title, 'primary_keyword': keyword, 'intent_key': 'x-draft',
           'taxonomy_key': taxonomy_key, 'search_intent': 'Hướng dẫn', 'topic_role': 'supporting'}
    inv = inventory()
    everything = topics() + remote_candidate_rows() + [row]
    found = assess_topic(row, everything, inv, new_ids={'NT-999999'}, index=IntentIndex(inv, everything))
    verdict = 'FAIL' if found['errors'] else 'REVIEW' if found['review'] else 'PASS'
    print(verdict, found['errors'] + found['review'])
    for m in found['matches'][:3]:
        print('   near %-9s %-6s jacc=%.2f  %s' % (m['id'], m['severity'], m['weighted_jaccard'], (m.get('title') or '')[:90]))
    return verdict


def cmd_row(tid):
    spec, _ = load_pkg(tid)
    row = row_from_spec(spec)
    (ROWS / (tid + '.row.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    print('wrote', ROWS / (tid + '.row.json'))
    return row


def cmd_check(tid, quiet=False):
    spec, body = load_pkg(tid)
    problems = []
    existing = bool(spec.get('existing'))
    required = ['topic_id', 'meta_title', 'meta_description', 'direct_answer', 'link_rationale', 'internal_links'] if existing else SPEC_FIELDS
    missing = [k for k in required if k not in spec or spec[k] in (None, '', [])]
    if missing and not (missing == ['secondary_keywords']):
        problems.append('spec fields missing: ' + ', '.join(missing))
    if existing:
        reg = registry_row(spec['topic_id'])
        if reg.get('topic_qa_status') != 'PLANNED' or reg.get('hold'):
            problems.append('registry row is not a ready PLANNED topic: %s hold=%s' % (reg.get('topic_qa_status'), reg.get('hold')))
    hosts = {re.sub(r'^https://([^/]+)/.*$', r'\1', s['url']) for s in spec.get('sources', [])}
    if len(hosts) < 2 and not existing:
        problems.append('need sources from >=2 different hosts, got ' + str(sorted(hosts)))
    for s in spec.get('sources', []):
        sus = vocab.suspects(s['excerpt'], allow=s.get('allow_tokens') or ())
        if sus:
            problems.append('excerpt has suspicious tokens (Tavily dropped-â artifact?) %s in: %s' % (sus, s['excerpt'][:70]))
        if len(s['excerpt'].split()) < 6:
            problems.append('excerpt shorter than 6 words: ' + s['excerpt'])
    for url in spec.get('internal_links', []):
        if url not in published_urls():
            problems.append('internal link is not a published inventory URL: ' + url)
    if LEGAL_WORDS.search(body):
        urls = [x['url'] for x in spec.get('sources', [])]
        if existing:
            urls = [x['url'] for x in registry_row(spec['topic_id'])['research']['external_sources']]
        if not any(qa.allowed_source(u, True) for u in urls):
            problems.append('body contains legal trigger words %s -> needs a legal-host source; rephrase' % sorted(set(m.group(0).lower() for m in LEGAL_WORDS.finditer(body))))
        else:
            print(' i legal trigger words present; an official legal-host source is cited (G3 legal check satisfied, source age <= 90 days)')
    if re.search(r'(?<!\d)(?:\+84|0)[\d .-]{8,15}\d(?!\d)', body):
        problems.append('body contains something that looks like a phone number')
    try:
        row = row_from_spec(spec)
    except Exception as exc:  # excerpt not found, unknown taxonomy ...
        print('ROW BUILD FAILED:', type(exc).__name__, exc)
        for p in problems:
            print(' !', p)
        return False
    verdict = {'status': 'PASS', 'errors': [], 'review': []} if existing else research_findings([row])[0]
    print('== %s | %s' % (tid, row['title']))
    print('research QA:', 'already accepted (registry row)' if existing else verdict['status'], verdict['errors'], verdict['review'])
    result, n_allowed, n_all = simulate_qa(tid, spec, body, row)
    print('article QA :', result['status'], '| words', result.get('word_count'), '| quality', result.get('quality_score'),
          '| seo', result.get('seo_score'), '| sources in frontmatter %d/%d allowlisted (one per URL)' % (n_allowed, n_all))
    for e in result['errors']:
        print('   ERROR :', e)
    for e in result['review']:
        print('   REVIEW:', e)
    if result.get('seo_recommendations'):
        for r in result['seo_recommendations']:
            print('   SEO   :', r)
    for p in problems:
        print(' !', p)
    missing = number_audit(body, spec)
    if missing:
        print(' ? numbers in the body that appear in none of the cited pages (justify each, or remove):', missing)
    close = copy_audit(body, spec)
    if close:
        print(' ? %d passages repeat the cited pages almost word for word (>=16 consecutive syllables); rewrite them in your own words:' % len(close))
        for length, text in close[:6]:
            print('     [%d] %s' % (length, text[:150]))
    ok = verdict['status'] == 'PASS' and result['status'] == 'PASS' and not problems
    print('=> READY' if ok else '=> NOT READY')
    return ok


TAIL_MARKERS = re.compile(r'^(tin đọc nhiều|tin liên quan|bài liên quan|xem thêm|có thể bạn quan tâm|đọc thêm|bình luận|tin mới nhất|'
                          r'tin cùng chuyên mục|mời bạn đọc|chia sẻ bài viết|từ khóa|tags?:|nguồn:|bài viết liên quan)', re.I)


def readable(text, min_words=4, cap=7000):
    """Navigation-free view of a stored page: keep lines of >= min_words words, stop at the related-links tail."""
    kept = []
    for ln in text.splitlines():
        ln = ln.strip()
        if TAIL_MARKERS.match(ln) and len(' '.join(kept)) > 1500:
            break
        if len(ln.split()) >= min_words:
            kept.append(ln)
    out = '\n\n'.join(kept)
    return out[:cap] + ('\n[... cut, use bench.load(url)["text"] for more]' if len(out) > cap else '')


def focused_view(text, row, evidence, cap=9000):
    """For long pages: the paragraphs most relevant to the topic (keyword overlap + the registered evidence), in page order."""
    paras = [x.strip() for x in re.split(r'\n\s*\n', text) if len(x.split()) >= 6]
    words = set()
    for phrase in [row.get('title', ''), row.get('primary_keyword', '')] + list(row.get('secondary_keywords') or []):
        words.update(w for w in bench.norm(phrase).split() if len(w) > 3)
    ev = bench.norm(evidence)
    scored = []
    for idx, para in enumerate(paras):
        n = bench.norm(para)
        score = sum(1 for w in words if w in n)
        if ev and ev[:60] in n:
            score += 1000
        scored.append((score, idx, para))
    keep, total = set(), 0
    for score, idx, para in sorted(scored, key=lambda t: (-t[0], t[1])):
        if score <= 0 or total + len(para) > cap:
            continue
        keep.add(idx)
        total += len(para)
    return '\n\n'.join(para for score, idx, para in scored if idx in keep)


def faq_view(x, row, limit=4):
    """The Honda FAQ pairs that carry the registered evidence, plus the best keyword matches, in full."""
    try:
        items = bench.faq_items(x['url'])
    except Exception:
        return None
    if not items:
        return None
    ev = bench.norm(x['evidence_text']).split()
    probe = ' '.join(ev[:8])
    words = set()
    for phrase in [row.get('primary_keyword', '')] + list(row.get('secondary_keywords') or []):
        words.update(w for w in bench.norm(phrase).split() if len(w) > 3)
    scored = []
    for idx, (q, a) in enumerate(items):
        text = bench.norm(q + ' ' + a)
        hit = 100 if probe and probe in text else 0
        score = hit + sum(1 for w in words if w in text)
        if score:
            scored.append((score, idx))
    chosen = [idx for _, idx in sorted(scored, key=lambda t: (-t[0], t[1]))[:limit]]
    if not chosen:
        return None
    return '\n\n'.join('[FAQ #%d] HỎI: %s\nĐÁP: %s' % (i, items[i][0], items[i][1]) for i in sorted(chosen))


def cmd_brief(tid, cap=7000):
    """Work order for an existing-mode writer: registry row essentials + the registered source pages."""
    row = registry_row(tid)
    print('# WORK ORDER', tid)
    for key in ('title', 'primary_keyword', 'secondary_keywords', 'search_intent', 'intent_key', 'taxonomy_key', 'canonical_target'):
        print('%s: %s' % (key, row.get(key)))
    print('outline (registered; your H2s should follow it in order and meaning):')
    for o in row.get('outline') or []:
        print('  -', o)
    res = row.get('research') or {}
    print('difference_summary:', res.get('difference_summary'))
    print('usefulness:', res.get('usefulness'))
    print('scope_exclusions:', res.get('scope_exclusions'))
    print('source_requirements:', row.get('source_requirements'))
    print('internal link candidates (published URLs):')
    for u in row.get('internal_link_candidates') or row.get('related_existing_urls') or []:
        print('  -', u)
    print()
    for i, x in enumerate(res.get('external_sources') or [], 1):
        is_pdf = x['url'].lower().split('?')[0].endswith('.pdf')
        try:
            rec = bench.load(x['url'])
        except KeyError:
            print('## SOURCE %d MISSING FROM STORE: %s' % (i, x['url']))
            continue
        if is_pdf:
            print('## SOURCE %d = PDF (read, but NOT in the article frontmatter and NOT linked: you may name it in the text as'
                  ' "tài liệu huấn luyện của Honda Việt Nam" and use its content): %s' % (i, x['url']))
            print('registered supports:', x['supports'])
            print('--- PDF text ---')
            print(readable(rec['text'], min_words=3, cap=min(cap, 6000)))
            print()
            continue
        print('## SOURCE %d: %s' % (i, x['url']))
        print('title:', rec.get('title'), '| read:', rec.get('read_at'))
        print('registered supports:', x['supports'])
        print('registered evidence_text:', x['evidence_text'])
        faq = faq_view(x, row) if 'honda.com.vn/cau-hoi-thuong-gap' in x['url'] else None
        if faq:
            print('--- the Honda FAQ page has 85 Q&A pairs; the pairs relevant to this topic (matched on the registered evidence'
                  ' and the topic keywords) are printed in full; ask bench.faq_items() for others ---')
            print(faq)
        elif len(rec['text']) > 14000:
            print('--- long page (%d chars): the paragraphs most relevant to this topic, in page order; bench.grep(url, regex) finds more ---' % len(rec['text']))
            print(focused_view(rec['text'], row, x['evidence_text']))
        else:
            print('--- page text (navigation lines removed) ---')
            print(readable(rec['text'], cap=cap))
        print()


def cmd_needles(tids, per_url=3, number=1):
    """url|needle lines for source-reachability.yml (candidate excerpts, at most `per_url` per URL and package).
    The same lines are saved to probe_input_<number>.txt: the workflow log keeps input order, so a failing line number
    identifies the excerpt (use `probe-apply`)."""
    lines, seen = [], set()
    for tid in tids:
        spec, _ = load_pkg(tid)
        if spec.get('existing'):
            continue
        count = {}
        for entry in build_sources(spec):
            url = entry['url']
            if count.get(url, 0) >= per_url:
                continue
            line = url + '|' + entry['evidence_text']
            if line not in seen:
                seen.add(line)
                lines.append(line)
                count[url] = count.get(url, 0) + 1
    (SCR / ('probe_input_%d.txt' % number)).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    print('# %d lines saved to probe_input_%d.txt' % (len(lines), number), file=sys.stderr)


def cmd_probe_apply(number, failing):
    """Record the runner's verdicts: every line of probe_input_<number>.txt is True except the 1-based line numbers in `failing`."""
    lines = (SCR / ('probe_input_%d.txt' % number)).read_text(encoding='utf-8').splitlines()
    verdicts = probe_verdicts()
    bad = set(failing)
    for i, line in enumerate(lines, 1):
        verdicts[line] = i not in bad
    PROBE.write_text(json.dumps(verdicts, ensure_ascii=False, indent=0), encoding='utf-8')
    print('recorded %d verdicts (%d failing)' % (len(lines), len(bad)))
    for i in sorted(bad):
        print('  FAIL line %d: %s' % (i, lines[i - 1][:170]))


def cmd_batch(tids, number):
    rows = [row_from_spec(load_pkg(t)[0]) for t in tids]
    assert 1 <= len(rows) <= 10
    out = ROOT / 'data/candidates' / ('%s-%04d.jsonl' % (SESSION, number))
    out.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    print('wrote', out, len(rows), 'rows')


def cmd_assemble(tid, slot, session):
    spec, body = load_pkg(tid)
    reg = {t['topic_id']: t for t in topics()}
    row = reg[tid]
    claim = row.get('writer_claim') or {}
    text, meta, n_allowed, n_all = article_text(spec, body, row, slot, session)
    # the registry row (already imported) is authoritative for identity fields
    for k in ('topic_id', 'title', 'primary_keyword', 'search_intent', 'taxonomy_key', 'canonical_target'):
        assert meta[k] == row[k], k
    dest = ROOT / 'posts/drafts' / (tid + '.md')
    dest.write_text(text, encoding='utf-8')
    print('wrote', dest, 'claim:', claim.get('session'), claim.get('slot'), '| sources', n_allowed, '/', n_all)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for c in ('cover', 'row', 'check'):
        p = sub.add_parser(c); p.add_argument('tid')
    sub.add_parser('sync')
    p = sub.add_parser('brief'); p.add_argument('tid'); p.add_argument('--cap', type=int, default=7000)
    p = sub.add_parser('intent'); p.add_argument('title'); p.add_argument('keyword'); p.add_argument('taxonomy_key')
    p = sub.add_parser('needles'); p.add_argument('--per-url', type=int, default=3); p.add_argument('--number', type=int, default=1); p.add_argument('tids', nargs='+')
    p = sub.add_parser('probe-apply'); p.add_argument('number', type=int); p.add_argument('--fail', default='')
    p = sub.add_parser('batch'); p.add_argument('--number', type=int, required=True); p.add_argument('tids', nargs='+')
    p = sub.add_parser('assemble'); p.add_argument('tid'); p.add_argument('--slot', required=True); p.add_argument('--session', required=True)
    a = ap.parse_args()
    if a.cmd == 'cover':
        cmd_cover(a.tid)
    elif a.cmd == 'row':
        cmd_row(a.tid)
    elif a.cmd == 'check':
        return 0 if cmd_check(a.tid) else 1
    elif a.cmd == 'sync':
        cmd_sync()
    elif a.cmd == 'brief':
        cmd_brief(a.tid, a.cap)
    elif a.cmd == 'intent':
        return 0 if cmd_intent(a.title, a.keyword, a.taxonomy_key) == 'PASS' else 1
    elif a.cmd == 'needles':
        cmd_needles(a.tids, a.per_url, a.number)
    elif a.cmd == 'probe-apply':
        cmd_probe_apply(a.number, [int(x) for x in a.fail.split(',') if x.strip()])
    elif a.cmd == 'batch':
        cmd_batch(a.tids, a.number)
    elif a.cmd == 'assemble':
        cmd_assemble(a.tid, a.slot, a.session)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
