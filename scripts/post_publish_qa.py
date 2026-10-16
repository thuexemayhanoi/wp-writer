#!/usr/bin/env python3
"""Read-only public-page SEO verification for posts owned by this factory.

Inspired by /global's deployed-page QA; WordPress-specific and never updates posts.
Run without WordPress credentials. Only verifies VERIFIED *published* campaign rows.
"""
import argparse
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from common import ROOT, SITE, WP, load, norm, topics, visible


class SEOPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self._inside_title = False
        self.canonicals = []
        self.descriptions = []
        self.robots = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == 'title':
            self._inside_title = True
            self.titles.append('')
        if tag == 'link' and (props.get('rel') or '').casefold() == 'canonical':
            self.canonicals.append(props.get('href'))
        if tag == 'meta':
            name = (props.get('name') or '').casefold()
            if name == 'description':
                self.descriptions.append(props.get('content'))
            elif name in ('robots', 'googlebot'):
                self.robots.append((props.get('content') or '').casefold())

    def handle_endtag(self, tag):
        if tag == 'title':
            self._inside_title = False

    def handle_data(self, data):
        if self._inside_title and self.titles:
            self.titles[-1] += data


def check_page(topic, record, page):
    errors = []
    seo = SEOPage()
    seo.feed(page)
    expected_canonical = topic['canonical_target']
    if seo.canonicals != [expected_canonical]:
        errors.append('canonical mismatch or duplicate')
    if seo.titles != [record.get('meta_title')]:
        errors.append('SEO title mismatch or duplicate')
    if seo.descriptions != [record.get('meta_description')]:
        errors.append('meta description mismatch or duplicate')
    if any('noindex' in entry for entry in seo.robots):
        errors.append('public page is noindex')
    if not record.get('first_paragraph') or norm(record['first_paragraph']) not in norm(visible(page)):
        errors.append('first paragraph mismatch')
    return errors


def choose(records, now, limit):
    """Cycle through historical posts while prioritizing recent publications."""
    if limit < 1:
        raise ValueError('limit must be positive')
    records = sorted(records, key=lambda p: p[1].get('verified_at') or '', reverse=True)
    if len(records) <= limit:
        return records
    newest = records[:max(1, limit//2)]
    old = records[len(newest):]
    space = limit-len(newest)
    start = (now.timetuple().tm_yday*space) % len(old)
    rotated = old[start:]+old[:start]
    return newest+rotated[:space]


def run(limit=40):
    now = dt.datetime.now(dt.timezone.utc)
    records = load('data/state/publication-ledger.json', {'posts':{}}).get('posts',{})
    topic_rows = {t['topic_id']:t for t in topics()}
    targets = [(k,v) for k,v in records.items() if k.startswith('NT-')
               and v.get('phase')=='VERIFIED' and v.get('status')=='publish']
    results=[]
    for topic_id,record in choose(targets,now,limit):
        errors=[]
        t=topic_rows.get(topic_id)
        if not t:
            errors.append('Published factory Topic ID missing from manifest')
        elif record.get('url') != t.get('canonical_target'):
            errors.append('ledger URL differs from approved canonical')
        else:
            try:
                page,_=WP().request(record['url'],public=True,page=True)
                errors.extend(check_page(t,record,page))
            except Exception as exc:
                errors.append('Public readback error: '+type(exc).__name__)
        results.append({'topic_id':topic_id,'url':record.get('url'),'status':'FAIL' if errors else 'PASS','errors':errors})
    failed=[r for r in results if r['status']=='FAIL']
    report={'at':now.isoformat(),'mode':'READ_ONLY_PUBLIC_HTTP','site':SITE,
       'total_verified_public':len(targets),'checked':len(results),'failed':len(failed),
       'status':'NO_PUBLISHED_POSTS' if not targets else ('FAIL' if failed else 'PASS'),
       'coverage':'Rotating sample, not whole-site crawl',
       'results':results}
    serialized=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    print(serialized)
    output=os.environ.get('WP_WRITER_POST_QA_OUTPUT')
    if output:
        path=Path(output).resolve()
        if path.is_relative_to(ROOT.resolve()):
            raise ValueError('Post-QA output must be outside tracked repository')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(serialized,encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:
            f.write('## WordPress post-publish QA\n\n')
            f.write('Status: **'+report['status']+'**; '+str(report['checked'])+
                    '/'+str(report['total_verified_public'])+' published campaign posts checked.\n')
    if failed:
        raise SystemExit('POST_PUBLISH_QA_FAIL: '+str(len(failed))+' public posts failed readback')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=40)
    args=parser.parse_args()
    run(args.limit)
