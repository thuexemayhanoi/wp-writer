#!/usr/bin/env python3
"""Automatic topic DISCOVERY, not automatic AI research or publishing.

Collects public RSS signals and maps verified local topical gaps to unique
research briefs. No AI token/API key; no fake "facts_checked", no PLANNED
promotion. External AI sessions must finish source review and Topic QA.
"""
import argparse
from collections import Counter
import datetime as dt
import json
from pathlib import Path
import re
import os
from urllib.parse import urlencode, urlsplit
from urllib.request import Request
from xml.etree import ElementTree

from common import ROOT, SITE, Redirect, digest, load, norm, now, topics
from refill import claimable_count
from git_state import RemoteState

LEDGER = 'data/state/topic-discovery-ledger.json'
REPORT = 'reports/topic-discovery.json'
DOMAIN_PATH = 'data/topic-domains.json'
CONFIG = 'config/topic-discovery.json'
BATCH_DIR = 'data/research/auto'
ANGLES = (
    ('check', 'Những bước kiểm tra {focus} trước khi quyết định', 'checklist'),
    ('compare', 'Cách so sánh các lựa chọn về {focus} theo nhu cầu thực tế', 'comparison'),
    ('cost', 'Chi phí và rủi ro cần tính khi tìm hiểu {focus}', 'cost'),
    ('errors', 'Sai lầm thường gặp khi tìm hiểu {focus} và cách tránh', 'troubleshooting'),
    ('questions', 'Những câu hỏi nên xác minh về {focus} trước khi sử dụng', 'questions'),
    ('plan', 'Lập kế hoạch tìm hiểu {focus} theo từng bước', 'how-to'),
)
CONTEXTS = (
    ('daily', 'dành cho nhu cầu hằng ngày'),
    ('beginner', 'cho người mới tìm hiểu'),
    ('trip', 'khi chuẩn bị di chuyển hoặc du lịch'),
    ('long-term', 'trong kế hoạch sử dụng dài hạn'),
)


def cleaned(value):
    return ' '.join(str(value or '').split())[:180]


def rss_public_headlines(domain_name, fetch=None, maximum=8):
    """Public RSS discovery leads; never present these as verified factual sources."""
    query = cleaned(domain_name)+' (xe máy OR xe điện OR du lịch OR giao thông)'
    url = 'https://news.google.com/rss/search?'+urlencode(
        {'q':query,'hl':'vi','gl':'VN','ceid':'VN:vi'})
    def default_fetch(link):
        req=Request(link,headers={'User-Agent':'NguyenTu-TopicDiscovery/1.0','Accept':'application/rss+xml'})
        from urllib.request import build_opener
        with build_opener(Redirect()).open(req,timeout=8) as response:
            if urlsplit(response.geturl()).hostname != 'news.google.com':
                raise ValueError('RSS redirect escaped allowlisted feed host')
            return response.read(750_000)
    try:
        blob=(fetch or default_fetch)(url)
        if len(blob)>750_000:
            raise ValueError('RSS response too large')
        root=ElementTree.fromstring(blob)
        leads=[]
        for item in root.findall('./channel/item')[:maximum]:
            title=cleaned(item.findtext('title'))
            link=cleaned(item.findtext('link'))
            if len(title)<20 or urlsplit(link).scheme!='https':
                continue
            leads.append({'title':title,'url':link,'source':'Google News public RSS',
                'evidence_level':'DISCOVERY_LEAD_NOT_FACT_CHECKED'})
        return leads, None
    except (ValueError, OSError, ElementTree.ParseError, TimeoutError) as exc:
        return [],type(exc).__name__


def identity_key(title):
    return norm(title)


def is_overlap(title, other_titles):
    """Cheap fail-closed overlap filter for discovery proposals, not Topic QA."""
    from difflib import SequenceMatcher
    candidate=norm(title)
    if not candidate:
        return True
    if candidate in other_titles:
        return True
    words=set(candidate.split())
    for old in other_titles:
        if abs(len(old)-len(candidate))>max(45,len(candidate)//2):
            continue
        common=len(words & set(old.split()))
        if common>=4 and common/max(1,len(words | set(old.split())))>=0.68:
            return True
        if SequenceMatcher(None,candidate,old).ratio()>=0.88:
            return True
    return False


def research_questions(focus,domain):
    return [
        'Người tìm kiếm muốn giải quyết vấn đề cụ thể nào về '+focus+'?',
        'URL/bài hiện có của '+SITE+' đã giải đáp phần nào, còn thiếu gì?',
        'Cần nguồn chính thức hoặc tài liệu kỹ thuật nào để kiểm chứng các thông tin?',
        'Có dữ kiện thay đổi theo thời gian (giá, luật, địa điểm) cần xác minh lại không?',
        'Nên liên kết về trang Hub/Pillar nào trong nhóm '+domain['name']+'?'
    ]


def proposal(domain,focus,angle,context):
    angle_id,title_template,intent=angle
    context_id,context_label=context
    title=cleaned(title_template.format(focus=focus)+': '+context_label)
    fingerprint=digest(norm(domain['domain_id']+' '+focus+' '+angle_id+' '+context_id))[:16]
    return {
        'proposal_id':'NTD-'+fingerprint,
        'status':'AWAITING_AI_RESEARCH',
        'domain_id':domain['domain_id'],
        'domain':domain['name'],
        'taxonomy_key':domain['taxonomy_key'],
        'title':title,
        'primary_keyword_suggestion':cleaned(focus),
        'intent_hint':intent,
        'intent_key_suggestion':domain['domain_id']+'-'+fingerprint,
        'research_questions':research_questions(focus,domain),
        'origin':'TOPICAL_GAP_HEURISTIC',
        'source_verification':'PENDING',
        'review_required':'AI external research + original full-content and source review; Topic QA must pass before PLANNED',
        'candidate_contract':{'origin_id':'NTD-'+fingerprint,'topic_qa_status':'RESEARCH'},
    }


def consumed_ids(topic_rows):
    # The coordinator imports fully researched ideas with origin_id equal to
    # the discovery proposal ID. Proposals still queued in candidate files
    # remain visible until admitted to the canonical topic manifest.
    return {str(t.get('origin_id')) for t in topic_rows if str(t.get('origin_id','')).startswith('NTD-')}


def discover(domain_data,subject_config,topic_rows,inventory,prior,policy,config,public_signals=None):
    if not config.get('enabled'):
        return [], {'state':'DISABLED'}
    allowed=int(policy.get('approved_capacity',1000))
    research_ceiling=min(int(config.get('research_ceiling',10000)),int(policy.get('capacity',10000)))
    if not 0<allowed<=research_ceiling<=10000:
        raise ValueError('Invalid publication or research capacity')
    registry=load('data/state/writer-claims.json',{})
    publication=load('data/state/publication-ledger.json',{})
    claimable=claimable_count(topic_rows,registry,publication)
    resolved=consumed_ids(topic_rows)
    prior_items=prior.get('proposals',{})
    pending=[k for k in prior_items if k not in resolved]
    cap=int(config.get('max_pending_proposals',300))
    batch_size=int(config.get('max_new_proposals_per_run',20))
    if not (1<=batch_size<=50 and 1<=cap<=500 and batch_size<=cap):
        raise ValueError('Invalid discovery batch/pending limits')
    stats={'claimable_topics':claimable,'approved_topic_limit':allowed,
           'research_ceiling':research_ceiling,'total_topics':len(topic_rows),
           'all_discovered':len(prior_items),'pending_research':len(pending),
           'resolved_topic_ids':len(resolved)}
    if claimable>=int(config.get('refill_when_claimable_below',100)):
        return [],{**stats,'state':'QUEUE_HEALTHY'}
    # Continue researching up to the 10k discovery ceiling even when the
    # separately approved canonical topic intake limit is still only 1,000.
    # This does not grant permission to import or publish anything over cap.
    stats['approved_intake_capacity_reached']=len(topic_rows)>=allowed
    if len(pending)>=cap:
        return [],{**stats,'state':'RESEARCH_BACKLOG_FULL'}
    if len(prior_items)>=research_ceiling:
        return [],{**stats,'state':'RESEARCH_CEILING_REACHED'}
    limit=min(batch_size,cap-len(pending),research_ceiling-len(prior_items))
    existing_titles={identity_key(t.get('title')) for t in topic_rows if t.get('title')}
    existing_titles.update(identity_key(x.get('title')) for x in inventory if x.get('title'))
    existing_titles.update(identity_key(x.get('title')) for x in prior_items.values() if x.get('title'))
    active=Counter(t.get('taxonomy_key') for t in topic_rows)
    created=Counter(x.get('domain_id') for x in prior_items.values())
    domain_rows=sorted(domain_data['domains'],key=lambda d:
        (created[d['domain_id']]/max(1,d['initial_allocation']),active[d['taxonomy_key']],d['domain_id']))
    result=[]
    signals=public_signals or {}
    seen_ids=set(prior_items)
    # Round-robin ensures a 20-topic batch covers more than one of the 35
    # topical domains rather than filling one silo with near-duplicate briefs.
    by_domain={}
    for domain in domain_rows:
        focuses=subject_config.get('subjects',{}).get(domain['taxonomy_key'],[])
        if not focuses:
            focuses=[domain['name']]
        by_domain[domain['domain_id']]=(
            proposal(domain,focus,angle,context)
            for focus in focuses for angle in ANGLES for context in CONTEXTS)
    while len(result)<limit and by_domain:
        progress=False
        for domain in domain_rows:
            generator=by_domain.get(domain['domain_id'])
            if generator is None:
                continue
            item=None
            while True:
                try:
                    candidate=next(generator)
                except StopIteration:
                    del by_domain[domain['domain_id']]
                    break
                if candidate['proposal_id'] not in seen_ids and not is_overlap(candidate['title'],existing_titles):
                    item=candidate
                    break
            if item is None:
                continue
            leads=signals.get(domain['domain_id'],[])
            item['source_signals']=leads[:3]
            item['public_signal_count']=len(leads)
            item['research_priority']='SOURCE_SIGNAL' if leads else 'TOPICAL_GAP'
            result.append(item)
            seen_ids.add(item['proposal_id'])
            existing_titles.add(identity_key(item['title']))
            progress=True
            if len(result)>=limit:
                break
        if not progress:
            break
    return result,{**stats,'state':'DISCOVERED' if result else 'NEEDS_EXTERNAL_RESEARCH',
                   'new_proposals':len(result)}


def collect_signals(domains,config,fetch=None):
    """Keep network discovery optional; unreachable RSS must never fabricate source verification."""
    out={}; failures={}
    max_feeds=min(3,max(0,int(config.get('max_signal_feeds_per_run',3))))
    for d in domains[:max_feeds]:
        items,error=rss_public_headlines(d['name'],fetch,int(config.get('max_headlines_per_feed',10)))
        out[d['domain_id']]=items
        if error:
            failures[d['domain_id']]=error
    return out,failures


def run(apply=False,live_signals=True):
    policy=load('config/production-policy.json')
    config=load(CONFIG)
    existing=load('data/existing-content-inventory.json',{}).get('items',[])
    domains=load(DOMAIN_PATH)['domains']
    topic_rows=topics()
    prior=load(LEDGER,{'version':1,'next_batch':1,'proposals':{}})
    if any(not k.startswith('NTD-') for k in prior.get('proposals',{})):
        raise ValueError('Invalid discovery ledger IDs')
    # Only gather source signals when the queue is genuinely low.
    leads={};failures={}
    candidates,stats=discover({'domains':domains},config,topic_rows,existing,prior,policy,config)
    if candidates and live_signals:
        top=[d for d in domains if d['domain_id'] in {p['domain_id'] for p in candidates}]
        leads,failures=collect_signals(top,config)
        for p in candidates:
            p['source_signals']=leads.get(p['domain_id'],[])[:3]
            p['public_signal_count']=len(leads.get(p['domain_id'],[]))
            p['research_priority']='SOURCE_SIGNAL' if p['public_signal_count'] else 'TOPICAL_GAP'
    report={'at':now(),'mode':'PUBLIC_RSS_AND_LOCAL_GAP_DISCOVERY',
            'ai_model_executed':False,'ai_api_keys_used':False,
            'proposal_status':'AWAITING_AI_RESEARCH','website':SITE,
            **stats,'public_feeds_checked':len(leads)+len(failures),
            'rss_errors':failures,'publication_writes':0,'wordpress_writes':0}
    if not apply:
        print(json.dumps({'report':report,'sample':candidates[:3]},ensure_ascii=False,indent=2))
        return report
    # A background task is allowed only from its trusted owner/repo/main workflow.
    if not (os.environ.get('GITHUB_ACTIONS')=='true' and
            os.environ.get('GITHUB_WORKFLOW')=='Universal Topic Discovery' and
            os.environ.get('GITHUB_REPOSITORY')=='thuexemayhanoi/wp-writer' and
            os.environ.get('GITHUB_REF')=='refs/heads/main'):
        raise ValueError('Trusted Actions main required for applying discovery')
    if not candidates:
        print(json.dumps(report,ensure_ascii=False))
        return report
    batch=int(prior.get('next_batch',1))
    rel=f'{BATCH_DIR}/batch-{batch:06d}.jsonl'
    path=ROOT/rel
    if path.exists():
        raise ValueError('Batch path already exists; refuse overwrite')
    state=RemoteState()
    state.remember([LEDGER,REPORT,rel])
    for p in candidates:
        if p['proposal_id'] in prior['proposals']:
            raise ValueError('Research proposal collision; no commit')
        prior['proposals'][p['proposal_id']]={'title':p['title'],
             'domain_id':p['domain_id'],'taxonomy_key':p['taxonomy_key'],
             'batch':batch,'proposed_at':report['at']}
    prior['next_batch']=batch+1
    report['batch_path']=rel
    report['pending_research_after']=report['pending_research']+len(candidates)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in candidates),encoding='utf-8')
    from common import save
    save(LEDGER,prior)
    save(REPORT,report)
    state.persist([LEDGER,REPORT,rel],'research: discover bounded SEO topic briefs [skip ci]')
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--apply',action='store_true')
    modes.add_argument('--dry-run',action='store_true')
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    run(apply=args.apply,live_signals=not args.offline)
