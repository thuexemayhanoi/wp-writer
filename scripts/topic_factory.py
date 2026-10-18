"""Canonical Topic QA and refill. Candidates never auto become PLANNED."""
import argparse
import datetime as dt
import json
import difflib
from urllib.parse import urlsplit
from common import ROOT, SITE, digest, load, norm, now, save, topics, write_topics
from intent_guard import IntentIndex, assess_topic as assess_intent

def validate_discovery_origin(topic, ledger, used_origins):
    """Discovery proposals are traceable but NOT independently QA-approved."""
    origin=str(topic.get('origin_id') or '')
    if not origin.startswith('NTD-'):
        return
    registered=ledger.get('proposals',{}).get(origin)
    if not registered:
        raise ValueError('Unknown autonomous discovery proposal ID')
    if origin in used_origins:
        raise ValueError('Discovery proposal already used by another topic')
    if registered.get('taxonomy_key')!=topic.get('taxonomy_key'):
        raise ValueError('Research category conflicts with original discovery brief')

def valid_research_sources(research):
    sources=research.get('external_sources',[])
    if not isinstance(sources,list) or not sources:
        return False
    for item in sources:
        if not isinstance(item,dict):
            continue
        try:
            u=urlsplit(str(item.get('url','')))
            checked=dt.date.fromisoformat(str(item.get('checked_at','')))
            current=dt.date.today()
            if (u.scheme=='https' and u.hostname and
                u.hostname not in ('localhost','127.0.0.1') and
                not u.username and not u.password and
                checked<=current and (current-checked).days<=365 and
                len(str(item.get('supports','')).strip())>=20):
                return True
        except (ValueError,TypeError):
            continue
    return False

def similarity(a,b):
    a,b=norm(a),norm(b)
    aa,bb=set(a.split()),set(b.split())
    return max(len(aa&bb)/max(1,len(aa|bb)),difflib.SequenceMatcher(None,a,b).ratio())

def exempt_factory_posts(inventory, ledger):
    """Flag posts this factory published itself (WordPress ID in the publication ledger).

    A researcher cannot have reviewed content that did not exist yet, so article QA does not
    demand review evidence for it; slug/URL/title collisions, topic-to-topic checks and the
    Jaccard near-duplicate gate still cover those posts. Research QA does not call this: a
    researcher can read them in the refreshed inventory and has to review them.
    """
    ids={r.get('wp_id') for r in ((ledger or {}).get('posts') or {}).values() if r.get('wp_id')}
    return [dict(p,evidence_exempt=True) if p.get('id') in ids and not p.get('evidence_exempt') else p
            for p in inventory]

def _utc(value):
    try:
        parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except (TypeError,ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)

def stamp_factory_posts(inventory, ledger):
    """Stamp every post this factory published with the time its Publisher verified it (`factory_published_at`).

    Topic QA uses the stamp for one narrow waiver: a researcher cannot have read a post that was published
    after the research was done (`research.reviewed_at`), so that post is not demanded as review evidence.
    Posts that already existed when the researcher read, and every legacy post, are still demanded.
    """
    when={r.get('wp_id'):(r.get('verified_at') or r.get('updated_at')) for r in ((ledger or {}).get('posts') or {}).values() if r.get('wp_id')}
    return [dict(p,factory_published_at=when[p['id']]) if when.get(p.get('id')) else p for p in inventory]

SNAPSHOT_INFERENCE_WINDOW=dt.timedelta(minutes=30)

def with_snapshot(topic, inventory):
    """A registered row that predates `research.inventory_updated_at` gets the snapshot time inferred from what it read.

    The row names the pages it reviewed. The newest factory-published page among them proves the researcher's
    snapshot is no older than that page's verification, and `reviewed_at` (the build) is no earlier than the snapshot,
    so the snapshot lies between the two. Only when the build followed that page within SNAPSHOT_INFERENCE_WINDOW is
    the page's time taken as the snapshot: a sibling article verified after it was not readable yet. A wider gap
    proves nothing, so the row keeps `reviewed_at`. Rows that already carry `inventory_updated_at`, and rows that
    read no factory page, are returned as is. The inferred time is recorded (`inventory_updated_at_inferred`) when a
    re-gated row is promoted.
    """
    research=topic.get('research') or {}
    if research.get('inventory_updated_at'):
        return topic
    read={str(i) for i in research.get('reviewed_existing_ids') or []}|{str(k) for k in research.get('reviewed_content_hashes') or {}}
    seen=[at for at in (_utc(p.get('factory_published_at')) for p in inventory if str(p.get('id')) in read) if at]
    built=_utc(research.get('reviewed_at'))
    if not seen or not built or not dt.timedelta(0)<=built-max(seen)<=SNAPSHOT_INFERENCE_WINDOW:
        return topic
    return dict(topic,research=dict(research,inventory_updated_at=max(seen).isoformat(),inventory_updated_at_inferred=True))

def drop_own_post(inventory, ledger, topic_id):
    """A draft never collides with its own already published WordPress post."""
    own=(((ledger or {}).get('posts') or {}).get(topic_id) or {}).get('wp_id')
    return [p for p in inventory if own is None or p.get('id')!=own]

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
    # Evidence of full-content review covers the baseline content a researcher can read.
    # Content this factory published itself is flagged evidence_exempt by the Publisher:
    # it cannot have been reviewed before it existed, and it stays covered by the
    # collision checks below, the topic-to-topic checks above and the Jaccard
    # near-duplicate gate in qa.evaluate.
    reviewable=[p for p in inventory if not p.get('evidence_exempt')]
    nearest=sorted(reviewable,key=lambda p:similarity(topic['title'],p.get('title') or ''),reverse=True)[:5]
    for p in inventory:
        if (p.get('slug')==topic.get('proposed_slug') or p.get('canonical')==topic.get('canonical_target') or
            p.get('url')==topic.get('canonical_target') or p.get('title_hash')==digest(norm(topic['title']))): errors.append('existing URL collision:'+str(p['id']))
    research=topic.get('research') or {}
    if str(topic.get('origin_id','')).startswith('NTD-'):
        if not valid_research_sources(research):
            review.append('Autonomous discovery needs independently researched and dated external source evidence')
        # Research V2 is stricter than legacy standalone source checks: raw RSS
        # discoveries cannot become PLANNED with one unverified source link.
        from research_v2 import validate_sources
        review.extend('Research V2: '+issue for issue in validate_sources(research))
    if not research.get('reviewer') or not research.get('difference_summary') or not topic.get('intent_key'):
        review.append('full-content semantic review missing')
    checked_hashes=research.get('reviewed_content_hashes',{})
    # The researcher's view of the site: the inventory snapshot used when recorded, else the review time.
    reviewed_at=_utc(research.get('inventory_updated_at')) or _utc(research.get('reviewed_at'))
    def published_after_review(p):
        # Sibling articles the factory itself publishes while a batch waits for intake cannot have been read yet.
        at=_utc(p.get('factory_published_at'))
        return bool(at and reviewed_at and at>reviewed_at)
    def covered(p):
        # One hash per page; a list when a reviewer re-read the page after it was edited.
        seen=checked_hashes.get(str(p['id']))
        return p.get('content_hash') in (seen if isinstance(seen,list) else [seen])
    stale=[p for p in nearest if not covered(p) and not published_after_review(p)]
    if not checked_hashes or stale:
        # Name the pages and their current hash so the reviewer re-reads exactly those.
        review.append('reviewed full-content evidence stale or missing'+
                      (': '+', '.join('%s=%s'%(p['id'],p.get('content_hash')) for p in stale) if stale else ''))
    reviewed=set(research.get('reviewed_existing_ids',[]))
    unreviewed=[p['id'] for p in nearest if p['id'] not in reviewed and not published_after_review(p)]
    if unreviewed: review.append('nearest full content not reviewed')
    if len(topic.get('outline',[]))<5 or not research.get('usefulness') or not research.get('scope_exclusions'):
        review.append('usefulness/outline/scope evidence incomplete')
    for reason in list(review):
        if reason.startswith('near topic:') and reason.split(':',1)[1] in research.get('resolved_topic_collisions',{}): review.remove(reason)
    return {'status':'FAIL' if errors else 'REVIEW' if review else 'PASS','errors':errors,'review':review,
            'evidence_pages':{'stale':[p['id'] for p in stale],'unreviewed':unreviewed},
            'nearest':[{'id':p['id'],'title':p.get('title'),'similarity':round(similarity(topic['title'],p.get('title') or ''),3)} for p in nearest],
            'at':now(),'topic_hash':digest(json.dumps(topic,ensure_ascii=False,sort_keys=True))}

def apply_intent_guard(result, topic, others, inventory, new_ids=None, index=None):
    """Add the full-corpus search-intent verdict to a gate() result; it never lowers a severity."""
    guard=assess_intent(topic,others,inventory,new_ids=new_ids,index=index)
    errors=list(result['errors'])+guard['errors']
    review=list(result['review'])+guard['review']
    merged=dict(result,errors=errors,review=review,
                status='FAIL' if errors else 'REVIEW' if review else 'PASS')
    if guard['matches']:
        merged['intent_matches']=[{'id':m['id'],'severity':m['severity'],
            'weighted_jaccard':m['weighted_jaccard']} for m in guard['matches'][:3]]
    return merged

def research_qa_verdicts(candidate_path):
    """Research QA status of every NEW row of a candidate file; only PASS may become PLANNED."""
    from research_v2 import validate_candidates
    known={t['topic_id'] for t in topics()}
    rows=[json.loads(line) for line in (ROOT/candidate_path).read_text().splitlines() if line.strip()]
    fresh=[t for t in rows if t.get('topic_id') not in known]
    if not fresh:return {}
    return {r['topic_id']:r['status'] for r in validate_candidates(fresh)}

def run(candidate_path=None, verdicts=None, only_ids=None):
    rows=topics(); inv=stamp_factory_posts(load('data/existing-content-inventory.json',{}).get('items',[]),load('data/state/publication-ledger.json',{})); tax=load('data/taxonomy.json')['items']
    # Refill is incremental: a later candidate must never revoke an approved
    # incumbent topic or silently invalidate an already-submitted article.
    # The new batch is still checked against ALL incumbents and its own peers.
    # `only_ids` re-gates registered RESEARCH rows in place and can only PROMOTE them (see regate()): every
    # other row, and any such row that does not pass, keeps its status and evidence untouched.
    only=set(only_ids or ())
    incumbent_ids={t['topic_id'] for t in rows}-only
    incumbent_evidence=load('reports/topic-qa.json',{}) if (candidate_path or only) else {}
    new_ids=set(only)
    if only and any(t['topic_id'] in only and t.get('topic_qa_status')!='RESEARCH' for t in rows):
        raise ValueError('Only RESEARCH rows can be re-gated')
    if only and not only<={t['topic_id'] for t in rows}:
        raise ValueError('Unknown topic ID to re-gate')
    if candidate_path:
        discovery=load('data/state/topic-discovery-ledger.json',{'proposals':{}})
        used_origins={str(t.get('origin_id')) for t in rows if str(t.get('origin_id','')).startswith('NTD-')}
        p=ROOT/candidate_path
        if not p.resolve().is_relative_to((ROOT/'data/candidates').resolve()):raise ValueError('Candidate path must be under data/candidates')
        incoming=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        known={t['topic_id']:t for t in rows}
        for t in incoming:
            if t['topic_id'] in known:
                if t!=known[t['topic_id']]:raise ValueError('Existing topic immutable; coordinator review required')
                continue
            validate_discovery_origin(t,discovery,used_origins)
            if len(rows)>=load('config/production-policy.json')['approved_capacity']:raise ValueError('Approved topic capacity reached')
            if not __import__('re').fullmatch(r'NT-\d{6}',t.get('topic_id','')):raise ValueError('Topic ID must be NT-XXXXXX')
            t['topic_qa_status']='RESEARCH';rows.append(t);known[t['topic_id']]=t;new_ids.add(t['topic_id'])
            if str(t.get('origin_id','')).startswith('NTD-'):
                used_origins.add(str(t['origin_id']))
    if len({t['topic_id'] for t in rows})!=len(rows):raise ValueError('Duplicate topic ID')
    evidence={}
    # One corpus build serves the whole batch: every WordPress item plus every live topic row.
    index=IntentIndex(inv,rows) if new_ids else None
    for t in rows:
        if (candidate_path or only) and t['topic_id'] in incumbent_ids:
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
        # A re-gated row is judged with the snapshot time inferred from its own evidence; the inference is kept
        # only when the row is promoted.
        probe=with_snapshot(t,inv) if t['topic_id'] in only else t
        result=gate(probe,rows,inv,tax)
        if t['topic_id'] in new_ids:
            result=apply_intent_guard(result,probe,rows,inv,new_ids,index)
            if verdicts is not None:
                # Only a Research QA PASS may become PLANNED; a missing verdict never passes.
                strict=verdicts.get(t['topic_id'])
                if strict!='PASS' and result['status']=='PASS':
                    result=dict(result,status='FAIL' if strict=='FAIL' else 'REVIEW',
                                research_qa=strict or 'MISSING')
        if t['topic_id'] in only:
            if result['status']!='PASS':
                evidence[t['topic_id']]=incumbent_evidence.get(t['topic_id']) or result  # not promoted: nothing changes
                continue
            result=dict(result,regated=True)
            t['research']=probe['research']
        evidence[t['topic_id']]=result
        t['topic_qa_status']='PLANNED' if result['status']=='PASS' else 'REJECTED' if result['status']=='FAIL' else 'RESEARCH'
        # Populate a verified REST category ID only after Topic QA has approved
        # the topic. Unmaterialized/planned terms deliberately remain null.
        if t['topic_qa_status']=='PLANNED':
            term=next(x for x in tax if x['taxonomy_key']==t['taxonomy_key'])
            if term['status']=='ACTIVE' and term.get('wordpress_term_id'):
                t['wordpress_category_id']=term['wordpress_term_id']
    write_topics(rows)
    for c in tax:
        c['materialized_topic_count']=sum(t['taxonomy_key']==c['taxonomy_key'] and t['topic_qa_status']=='PLANNED' for t in rows)
    save('data/taxonomy.json',{'version':1,'owner':'coordinator','items':tax})
    save('reports/topic-qa.json',evidence)
    # reports/refill-request.json belongs to scripts/refill_controller.py (ready stock, not lifetime PLANNED).
    print(json.dumps({k:sum(x['status']==k for x in evidence.values()) for k in ('PASS','REVIEW','FAIL')}))

def regate(ids):
    """Re-gate registered RESEARCH rows with today's rules and promote the ones that pass strict Research QA.

    For rows that were refused only because the evidence rule moved under them (a sibling article went live
    after the researcher read, or the intake ran late): registered rows are immutable and still own their search
    intent, so a new ID for the same idea would collide with the stuck row. Nothing is ever demoted or rejected.
    A row recorded before `research.inventory_updated_at` existed is judged with a snapshot time inferred from the
    factory pages it read, when it was built soon after the newest of them (`with_snapshot`); the inference is
    written into the row only when it is promoted.
    """
    from research_v2 import validate_candidates
    ids=list(dict.fromkeys(i.strip() for i in ids if i.strip()))
    rows=topics(); chosen=[t for t in rows if t['topic_id'] in ids]
    if len(chosen)!=len(ids):raise ValueError('Unknown topic ID to re-gate')
    inv=stamp_factory_posts(load('data/existing-content-inventory.json',{}).get('items',[]),load('data/state/publication-ledger.json',{}))
    verdicts={r['topic_id']:r['status'] for r in validate_candidates([with_snapshot(t,inv) for t in chosen],incumbent=[t for t in rows if t['topic_id'] not in ids])}
    run(None,verdicts,only_ids=ids)
    after={t['topic_id']:t['topic_qa_status'] for t in topics()}
    return {i:(verdicts.get(i),after[i]) for i in ids}

def main():
    p=argparse.ArgumentParser();p.add_argument('--import-candidates');p.add_argument('--regate',help='comma-separated RESEARCH topic IDs to re-gate and promote when they pass');a=p.parse_args()
    if a.regate:
        print(json.dumps(regate(a.regate.split(',')),ensure_ascii=False));return
    # Importing candidates always requires Research QA; only a full manual re-audit skips it.
    run(a.import_candidates,research_qa_verdicts(a.import_candidates) if a.import_candidates else None)

if __name__=='__main__':main()
