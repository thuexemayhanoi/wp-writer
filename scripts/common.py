"""Shared, create-only factory primitives. No model APIs."""
import base64
import contextlib
import datetime as dt
import functools
import hashlib
import html
import json
import os
import re
import subprocess
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://thuexemaynguyentu.com'
PROTECTED_IDS = {3861}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()

def load(path, default=None):
    p = ROOT / path
    return json.loads(p.read_text()) if p.exists() else default

def save(path, value):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=p.parent, delete=False, encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(f.name, p)

def topics():
    p = ROOT / 'data/topics.jsonl'
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

def write_topics(rows):
    p = ROOT / 'data/topics.jsonl'
    p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.links = []; self.skip = 0; self.anchor = None
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag == 'a':
            url = dict(attrs).get('href', '')
            self.links.append({'url': url, 'anchor': ''})
            self.anchor = len(self.links)-1
        if tag in ('p', 'li', 'br', 'h1', 'h2', 'h3', 'div'): self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
        if tag == 'a': self.anchor = None
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.anchor is not None:self.links[self.anchor]['anchor'] += data

def visible(value):
    p = Text(); p.feed(value)
    return ' '.join(html.unescape(' '.join(p.parts)).split())

@functools.lru_cache(maxsize=100_000)
def norm(value):
    # Pure and called with the same titles and page texts thousands of times per QA run; memoized per process.
    return ' '.join(re.findall(r'[a-z0-9]+', ''.join(c for c in unicodedata.normalize('NFD', visible(value).lower().replace('đ','d')) if unicodedata.category(c) != 'Mn')))

def slugify(value):
    return norm(value).replace(' ', '-')

def git(*args, input=None, env=None):
    p = subprocess.run(['git', *args], cwd=ROOT, input=input, env=env, text=True, capture_output=True)
    if p.returncode: raise RuntimeError('Git operation failed: ' + args[0])
    return p.stdout.strip()

@contextlib.contextmanager
def lock(name='.factory-lock'):
    p = ROOT / name
    fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, now().encode()); yield
    finally:
        os.close(fd); p.unlink()

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc or not newurl.startswith('https://'):
            raise RuntimeError('Cross-origin redirect refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

# HTTP statuses that prove WordPress refused a write before creating anything.
REFUSED_BEFORE_CREATE = (400, 401, 403, 404, 405, 413, 414, 415, 422, 429)

class WPRejected(RuntimeError):
    """A WordPress POST was refused with a definitive 4xx: nothing was created."""
    def __init__(self, status):
        super().__init__(f'WordPress HTTP {status}; POST (refused, nothing created)')
        self.status = status

class WP:
    def __init__(self, authenticated=False):
        configured = os.environ.get('WP_URL', SITE).rstrip('/')
        if configured != SITE: raise ValueError('Wrong WordPress site')
        self.auth = None
        if authenticated:
            user, password = os.environ.get('WP_USERNAME'), os.environ.get('WP_APPLICATION_PASSWORD')
            if not user or not password: raise ValueError('WordPress secrets unavailable')
            self.auth = base64.b64encode((user + ':' + password.replace(' ', '')).encode()).decode()
        self.opener = urllib.request.build_opener(Redirect())

    def request(self, path, payload=None, public=False, page=False, method=None):
        url = path if page else SITE + '/wp-json/' + path
        if urllib.parse.urlsplit(url).netloc != 'thuexemaynguyentu.com' or not url.startswith(SITE + '/'):
            raise ValueError('WordPress origin mismatch')
        headers = {'Accept': 'text/html' if page else 'application/json', 'User-Agent': 'NguyenTu-WPWriter/1.0', 'Cache-Control':'no-cache'}
        if self.auth and not public: headers['Authorization'] = 'Basic ' + self.auth
        if payload is not None: headers['Content-Type'] = 'application/json; charset=utf-8'
        verb = method or ('POST' if payload is not None else 'GET')
        # NEVER retry a WordPress write: the first POST may already have
        # created a post even when its response times out.
        rate_limit_retried = False
        for attempt in range(3 if verb == 'GET' else 1):
            try:
                req = urllib.request.Request(url, data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None, headers=headers, method=verb)
                with self.opener.open(req, timeout=25) as r:
                    raw = r.read(12_000_000)
                    return (raw.decode('utf-8') if page else json.loads(raw)), dict(r.headers)
            except urllib.error.HTTPError as e:
                if verb == 'GET' and e.code == 429:
                    if rate_limit_retried or attempt == 2:
                        raise RuntimeError('WordPress HTTP 429; GET retry exhausted; stop instead of flooding the host') from None
                    delay = 60  # Conservative host cooldown when Retry-After is absent.
                    retry_after = e.headers.get('Retry-After') if e.headers else None
                    if retry_after:
                        try:
                            delay = max(60, int(retry_after))
                        except ValueError:
                            try:
                                import email.utils
                                retry_at = email.utils.parsedate_to_datetime(retry_after)
                                if retry_at.tzinfo is None:
                                    retry_at = retry_at.replace(tzinfo=dt.timezone.utc)
                                delay = max(60, int((retry_at-dt.datetime.now(dt.timezone.utc)).total_seconds())+1)
                            except (TypeError, ValueError, OverflowError):
                                delay = 60
                    if delay > 180:
                        raise RuntimeError('WordPress HTTP 429; server cooldown exceeds 180s; stop safely') from None
                    rate_limit_retried = True
                    time.sleep(delay)
                    continue
                if verb != 'GET' or e.code not in (500,502,503,504) or attempt == 2:
                    if verb == 'POST' and e.code in REFUSED_BEFORE_CREATE:
                        raise WPRejected(e.code) from None
                    raise RuntimeError(f'WordPress HTTP {e.code}; {verb}') from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if verb != 'GET' or attempt == 2:
                    # No tokens or Basic Auth headers in logs. Expose only the
                    # failing endpoint path and exception type for diagnosis.
                    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
                    safe_path = urllib.parse.urlsplit(url).path
                    raise RuntimeError(
                        f'WordPress network error; {verb}; path={safe_path}; '
                        f'reason={type(reason).__name__}; outcome unknown for writes'
                    ) from None
            time.sleep(2 ** attempt)

    def get(self, path, **kwargs): return self.request(path, **kwargs)[0]

    def all(self, resource, **params):
        rows, page = [], 1
        while True:
            data, headers = self.request(resource + '?' + urllib.parse.urlencode({**params, 'per_page':100, 'page':page}))
            if not isinstance(data, list): raise ValueError('Invalid WordPress collection')
            rows.extend(data)
            total = int(next((v for k,v in headers.items() if k.lower() == 'x-wp-totalpages'), page))
            if page >= total: return rows
            page += 1

def title_of(post):
    t = post.get('title', post.get('name',''))
    return html.unescape(t.get('raw', t.get('rendered','')) if isinstance(t,dict) else t)

def inventory(client):
    result = []
    for resource in ('posts','pages'):
        statuses = ('publish','draft','private','pending','future') if client.auth else ('publish',)
        for status in statuses:
            for p in client.all('wp/v2/'+resource, status=status, context='edit' if client.auth else 'view'):
                p['resource'] = resource; result.append(p)
    return result
