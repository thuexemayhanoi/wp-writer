"""Canonical Topic QA and refill. Candidates never auto become PLANNED."""
import argparse
import json
import difflib
from common import ROOT, SITE, digest, load, norm, now, save, topics, write_topics

def similarity(a,b):
    a,b=norm(a),norm(b)
    aa,bb=set(a.split()),set(b.split())
    return max(len(aa&bb)/max(1,len(aa|bb)),difflib.SequenceMatcher(None,a,b).ratio())

def gate(topic, others, inventory, taxonomy):
    errors=[]; review=[]
    required=['topic_id','title','primary_keyword','search_intent','taxonomy_key','proposed_slug','canonical_target']
    errors += ['missing:'+k for k in required if not topic.get(k)]
    if topic.get('taxonomy_key') not in {x['taxonomy_key'] for x in taxonomy}: errors.append('unknown taxonomy key')
    if topic.get('taxonomy_key')=='uncategorized': errors.append('Uncategorized forbidden')
    if topic.get('canonical_target')!=SITE+'/'+topic.get('proposed_slug','')+'/': errors.append('canonical mismatch')
    for other in others:
        if other['topic_id']==topic['topic_id']: continue
        if (other.get('proposed_slug')==topic.get('proposed_slug') or
            norm(other['title'])==norm(topic['title']) or
            (topic.get('intent_key') and topic.get('intent_key')==other.get('intent_key'))):
            errors.append('topic identity collision:'+other['topic_id'])
        elif similarity(topic['title'],other['title'])>=0.73: review.append('near topic:'+other['topic_id'])
    nearest=sorted(inventory,key=lambda p:similarity(topic['title'],p.get('title') or ''),reverse=True)[:5]
    for p in inventory:
        if (p.get('slug')==topic.get('proposed_slug') or p.get('canonical')==topic.get('canonical_target') or
            p.get('url')==topic.get('canonical_target') or p.get('title_hash')==digest(norm(topic['title']))): errors.append('existing URL collision:'+str(p['id']))
    research=topic.get('research') or {}
    if not research.get('reviewer') or not research.get('difference_summary') or not topic.get('intent_key'):
        review.append('full-content semantic review missing')
    checked_hashes=research.get('reviewed_content_hashes',{})
    if not checked_hashes or any(checked_hashes.get(str(p['id']))!=p.get('content_hash') for p in nearest):
        review.append('reviewed full-content evidence stale or missing')
    reviewed=set(research.get('reviewed_existing_ids',[]))
    if any(p['id'] not in reviewed for p in nearest): review.append('nearest full content not reviewed')
    if len(topic.get('outline',[]))<5 or not research.get('usefulness') or not research.get('scope_exclusions'):
        review.append('usefulness/outline/scope evidence incomplete')
    for reason in list(review):
        if reason.startswith('near topic:') and reason.split(':',1)[1] in research.get('resolved_topic_collisions',{}): review.remove(reason)
    return {'status':'FAIL' if errors else 'REVIEW' if review else 'PASS','errors':errors,'review':review,
            'nearest':[{'id':p['id'],'title':p.get('title'),'similarity':round(similarity(topic['title'],p.get('title') or ''),3)} for p in nearest],
            'at':now(),'topic_hash':digest(json.dumps(topic,ensure_ascii=False,sort_keys=True))}

def run(candidate_path=None):
    rows=topics(); inv=load('data/existing-content-inventory.json',{}).get('items',[]); tax=load('data/taxonomy.json')['items']
    # Refill is incremental: a later candidate must never revoke an approved
    # incumbent topic or silently invalidate an already-submitted article.
    # The new batch is still checked against ALL incumbents and its own peers.
    incumbent_ids={t['topic_id'] for t in rows}
    incumbent_evidence=load('reports/topic-qa.json',{}) if candidate_path else {}
    if candidate_path:
        p=ROOT/candidate_path
        if not p.resolve().is_relative_to((ROOT/'data/candidates').resolve()):raise ValueError('Candidate path must be under data/candidates')
        incoming=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        known={t['topic_id']:t for t in rows}
        for t in incoming:
            if t['topic_id'] in known:
                if t!=known[t['topic_id']]:raise ValueError('Existing topic immutable; coordinator review required')
                continue
            if len(rows)>=load('config/production-policy.json')['approved_capacity']:raise ValueError('Approved topic capacity reached')
            if not __import__('re').fullmatch(r'NT-\d{6}',t.get('topic_id','')):raise ValueError('Topic ID must be NT-XXXXXX')
            t['topic_qa_status']='RESEARCH';rows.append(t);known[t['topic_id']]=t
    if len({t['topic_id'] for t in rows})!=len(rows):raise ValueError('Duplicate topic ID')
    evidence={}
    for t in rows:
        if candidate_path and t['topic_id'] in incumbent_ids:
            # Keep original verdict, research state, and immutable identity.
            # A malicious/duplicate new idea must be rejected on its own merits,
            # never by demoting an existing PLANNED or already-authored topic.
            old=incumbent_evidence.get(t['topic_id'])
            if old:
                evidence[t['topic_id']]=old
            else:
                old_status=t.get('topic_qa_status')
                evidence[t['topic_id']]={'status':{'PLANNED':'PASS','REJECTED':'FAIL'}.get(old_status,'REVIEW'),
                    'errors':[],'review':['Original topic evidence unavailable; preserve incumbent status'],
                    'topic_hash':digest(json.dumps(t,ensure_ascii=False,sort_keys=True)),
                    'preserved_incumbent':True}
            continue
        result=gate(t,rows,inv,tax); evidence[t['topic_id']]=result
        t['topic_qa_status']='PLANNED' if result['status']=='PASS' else 'REJECTED' if result['status']=='FAIL' else 'RESEARCH'
    write_topics(rows)
    for c in tax:
        c['materialized_topic_count']=sum(t['taxonomy_key']==c['taxonomy_key'] and t['topic_qa_status']=='PLANNED' for t in rows)
    save('data/taxonomy.json',{'version':1,'owner':'coordinator','items':tax})
    save('reports/topic-qa.json',evidence)
    save('reports/refill-request.json',{'claimable':sum(t['topic_qa_status']=='PLANNED' for t in rows),'target':1000,
        'needs_external_research':sum(t['topic_qa_status']=='PLANNED' for t in rows)<100,'instruction':'External coordinator researches candidates; no model runs in Actions.'})
    print(json.dumps({k:sum(x['status']==k for x in evidence.values()) for k in ('PASS','REVIEW','FAIL')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--import-candidates');a=p.parse_args();run(a.import_candidates)
