import csv
import json
from collections import Counter
from common import ROOT,load,now,save,topics
from writer_session import live_leases
from internal_linking import build
from taxonomy_sync import by_key,resolve
from refill_policy import policy as refill_policy, stock_policy
from topic_stock import build_stock

def table_file(path,fields,rows):
    with (ROOT/path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items() if k in fields})

def run():
    rows=topics();inventory=load('data/existing-content-inventory.json',{});items=inventory.get('items',[])
    ledger=load('data/state/publication-ledger.json',{'posts':{},'categories':{}});policy=load('config/production-policy.json')
    claims=load('data/state/writer-claims.json',{'leases':{}});active=live_leases(claims)
    used={i for v in active.values() for i in v['topic_ids']}
    authored=list((ROOT/'posts/drafts').glob('NT-*.md'));qa=[load('data/qa/'+p.stem+'.json',{}) for p in authored]
    campaign={k:v for k,v in ledger['posts'].items() if k.startswith('NT-')}
    mapping_errors=[];cats=load('data/existing-taxonomy.json',{}).get('items',[])
    for key,r in by_key().items():
        if r['status']=='ACTIVE' and key!='uncategorized':
            try:resolve(key,by_key(),cats)
            except Exception as e:mapping_errors.append({'key':key,'error':str(e)})
    empty=[k for k,v in ledger['categories'].items() if v.get('phase')=='CREATED_PENDING_ARTICLE']
    planned=sum(t['topic_qa_status']=='PLANNED' for t in rows)
    stock=build_stock(rows,claims,ledger,{p.stem:q for p,q in zip(authored,qa)},{p.stem for p in authored},
        load('data/state/topic-discovery-ledger.json',{'proposals':{}}),stock_policy(policy))
    save('reports/topic-stock.json',stock)
    refill=refill_policy();refill_request=load('reports/refill-request.json',{}) or {};order=refill_request.get('order') or {}
    uncertain=[k for k,v in campaign.items()
               if v.get('phase') in ('POST_INTENT','VERIFY_PENDING','NEEDS_RECONCILE')]
    completed={k for k,v in campaign.items() if v.get('phase')=='VERIFIED'}
    waiting=[p.stem for p,q in zip(authored,qa) if q.get('status')=='PASS'
             and p.stem not in completed and p.stem not in uncertain
             and claims.get('submissions',{}).get(p.stem,{}).get('sha256')==q.get('source_sha256')]
    blocked=[s for s,v in claims.get('processed_requests',{}).items() if v.get('status')=='BLOCKED']
    recent=[v.get('verified_at') for v in campaign.values() if v.get('verified_at')]
    dashboard={'at':now(),'existing_published_posts':sum(p.get('type')=='posts' and p.get('status')=='publish' for p in items),
        'existing_pages':sum(p.get('type')=='pages' and p.get('status')=='publish' for p in items),
        'existing_products':sum(p.get('type')=='products' and p.get('status')=='publish' for p in items),
        'candidate_topics':len(rows),'planned_topics':planned,'claimable_topics':sum(t['topic_qa_status']=='PLANNED' and t['topic_id'] not in used and t['topic_id'] not in claims.get('submissions',{}) for t in rows),
        'ready_stock':stock['ready'],'stock_stages':stock['stages'],'needs_research':stock['needs_research'],
        'research_shortfall':stock['shortfall'],
        'refill_trigger_below_ready':refill['trigger_below_ready'],
        'refill_round_target':str(refill['round_target_min'])+'-'+str(refill['round_target_max']),
        'refill_state':refill_request.get('state','UNKNOWN'),'refill_order':order.get('id'),
        'refill_accepted_so_far':order.get('accepted_so_far'),
        'writing':len(used),'draft_authored':len(authored),'qa_pass':sum(q.get('status')=='PASS' for q in qa),
        'qa_fail':sum(q.get('status')=='FAIL' for q in qa),'qa_review':sum(q.get('status')=='REVIEW' for q in qa),
        'repair_queue':sum(q.get('status') in ('FAIL','REVIEW') for q in qa),
        'held_by_class':dict(Counter((q.get('triage') or {}).get('hold_class','UNCLASSIFIED') for q in qa if q.get('status') in ('FAIL','REVIEW'))),
        'g7_pass':sum((v.get('g7') or {}).get('status')=='PASS' for v in campaign.values()),
        'g7_not_recorded':sum(v.get('phase')=='VERIFIED' and not v.get('g7') for v in campaign.values()),
        'wordpress_draft':sum(v.get('phase')=='VERIFIED' and v.get('status')=='draft' for v in campaign.values()),
        'wordpress_published':sum(v.get('status')=='publish' for v in campaign.values()),
        'verified_public':sum(v.get('status')=='publish' and v.get('phase')=='VERIFIED' for v in campaign.values()),
        'indexed':None,'topic_collisions':sum(t['topic_qa_status']=='REJECTED' for t in rows),
        'category_mapping_errors':len(mapping_errors),'empty_category_violations':len(empty),
        'broken_links':None,'broken_links_note':'No full HTTP crawl yet; inventory graph is not a broken-link proof',
        'remaining_topic_target':max(0,1000-planned),'remaining_candidate_target':max(0,1000-len(rows)),
        'delivery_mode':policy.get('mode','dry_run'),
        'production_enabled':policy['production_enabled'],'draft_staging_enabled':policy.get('draft_staging_enabled',False),
        'qa_pass_live_checked':sum(q.get('status')=='PASS' and q.get('live_links_checked') is True for q in qa),
        'qa_pass_awaiting_wordpress':len(waiting),'queued_topic_ids':waiting,
        'pending_wordpress_intents':uncertain,'blocked_writer_sessions':blocked,
        'last_wordpress_verified_at':max(recent) if recent else None,
        'capacity':policy['capacity'],'authenticated_inventory':inventory.get('authenticated',False),
        'test_drafts_excluded':sum(not k.startswith('NT-') for k in ledger['posts'])+1}
    save('reports/dashboard.json',dashboard)
    save('data/state/checkpoint.json',{'at':now(),'phase':'implemented; acceptance and activation gates','dashboard':dashboard,
        'next':['Complete topic research toward 1000','Resolve production security controls','Verify SEO REST metadata adapter','Owner production approval'],
        'never_reset':['POST_INTENT','NEEDS_RECONCILE','VERIFY_PENDING'],'ledger':'data/state/publication-ledger.json'})
    table_file('reports/existing-url-inventory.csv',['id','type','status','title','slug','url','canonical','categories','seo_title','meta_description','source','verified_at'],items)
    table_file('reports/existing-taxonomy-matrix.csv',['taxonomy_key','name','slug','parent_key','wordpress_term_id','wordpress_parent_id','existing_or_planned','status'],list(by_key().values()))
    table_file('reports/search-intent-matrix.csv',['topic_id','title','primary_keyword','search_intent','intent_key','taxonomy_key','topic_qa_status'],rows)
    table_file('reports/new-content-eligibility.csv',['topic_id','title','topic_qa_status','research','source_requirements'],rows)
    save('reports/content-gap-report.json',{'domains':load('data/topic-domains.json')['domains'],'qualified':planned,'shortfall':1000-planned,'unresearched_candidates':len(rows)-planned,'search_volume_verified':False})
    audit=load('data/source/audit-all-sheets.json')
    if audit is None:
        from audit import read_excel
        audit=read_excel(ROOT/'data/source/audit-2026-10-16.xlsx')
    save('reports/cannibalization-risk-matrix.json',{'baseline_pairs':audit['06_Similar_Old_URLs'],'new_topic_qa':load('reports/topic-qa.json',{}),'note':'Heuristic flags require full-content intent review. No legacy edits.'})
    save('reports/category-mapping-errors.json',mapping_errors)
    build()
    # Per-article pipeline board (WRITING -> QA -> READY -> PUBLISHING -> VERIFIED, REPAIR/HELD): reports/pipeline-board.{json,md}
    from pipeline_board import run as board_run
    board_run()
    md='# Factory dashboard\n\nGenerated from manifest, lease registry, QA evidence and publication ledger.\n\n| Metric | Value |\n|---|---|\n'
    md+=''.join('| '+k+' | '+str(v)+' |\n' for k,v in dashboard.items())
    md+=('\nDelivery mode: '+str(policy.get('mode','dry_run'))+
         '; production_enabled='+str(policy.get('production_enabled',False))+
         '; draft_staging_enabled='+str(policy.get('draft_staging_enabled',False))+
         '. A candidate is not a planned topic; a published URL is not evidence of Google indexing. '
         'See docs/IMPLEMENTATION-CHECKPOINT.md and docs/ACTIVATION.md.\n')
    (ROOT/'reports/latest.md').write_text(md)
    print(json.dumps(dashboard,ensure_ascii=False))

if __name__=='__main__':run()
