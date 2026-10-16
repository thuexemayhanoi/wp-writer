"""The ONLY WordPress writer. Create-only, remote write-ahead ledger."""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import markdown
from common import ROOT,SITE,WP,PROTECTED_IDS,digest,git,inventory,load,lock,norm,now,save,title_of,topics,visible
from git_state import RemoteState
from qa import evaluate,read_article
from taxonomy_sync import by_key,resolve,materialize

LEDGER='data/state/publication-ledger.json'

def production_allowed(policy):
    return (policy.get('production_enabled') is True and policy.get('mode')=='production' and
        bool(policy.get('owner_approval_ref')) and policy.get('acceptance_passed') is True and
        policy.get('security_controls_verified') is True and policy.get('seo_adapter_verified') is True and
        not policy.get('paused') and not policy.get('emergency_stop'))

def draft_staging_allowed(policy):
    """Unattended draft writes require independent owner and security approvals."""
    return (policy.get('mode')=='draft_only'
        and policy.get('production_enabled') is False
        and policy.get('draft_staging_enabled') is True
        and bool(policy.get('draft_staging_approval_ref'))
        and policy.get('security_controls_verified') is True
        and not policy.get('paused') and not policy.get('emergency_stop'))


def delivery_route(topic,policy,registry,categories,create_category=None,acceptance_draft=False):
    """Choose public-only on exact taxonomy, otherwise draft at a safe known parent.

    No category is guessed or created silently. Intended category and warning
    are recorded durably so an editor can later finish taxonomy on WordPress.
    """
    if topic['taxonomy_key']=='uncategorized':
        raise ValueError('Uncategorized forbidden as intended taxonomy')
    public=production_allowed(policy)
    staging=draft_staging_allowed(policy)
    if not (public or staging or acceptance_draft):
        raise ValueError('WordPress delivery is not approved')
    intended=topic['taxonomy_key']
    try:
        term_id=resolve(intended,registry,categories)
        return {'status':'publish' if public else 'draft','category_id':term_id,
                'intended_taxonomy_key':intended,'category_resolution':'EXACT',
                'category_warning':None}
    except ValueError as exc:
        category_error=str(exc)
    if public and policy.get('allow_category_create') and create_category:
        # Only the explicitly approved, ledger-protected JIT path may write terms.
        try:
            term_id=create_category(intended)
            return {'status':'publish','category_id':term_id,
                    'intended_taxonomy_key':intended,'category_resolution':'CREATED',
                    'category_warning':None}
        except ValueError as exc:
            category_error=str(exc)
    if policy.get('on_category_mismatch')!='draft':
        raise ValueError('Category blocked: '+category_error)
    fallback=policy.get('fallback_draft_taxonomy_key','blog')
    if fallback==intended:
        raise ValueError('Cannot fallback onto mismatched original category')
    term_id=resolve(fallback,registry,categories)
    return {'status':'draft','category_id':term_id,
            'intended_taxonomy_key':intended,'category_resolution':'FALLBACK_DRAFT',
            'category_warning':category_error}


def duplicate(topic,live):
    marker='wp-writer:topic='+topic['topic_id']+';'
    return [p for p in live if p.get('slug')==topic['proposed_slug'] or
        norm(title_of(p))==norm(topic['title']) or marker in p.get('content',{}).get('raw',p.get('content',{}).get('rendered','')) or
        p.get('yoast_head_json',{}).get('canonical')==topic['canonical_target']]

def post_html(topic,body,sha):
    return '<!-- wp-writer:topic='+topic['topic_id']+';sha256='+sha+' -->\n'+markdown.markdown(body,extensions=['tables','sane_lists'])

def verify(client,topic,record):
    post_id=record['wp_id']
    if post_id in PROTECTED_IDS:raise ValueError('Protected smoke-test post')
    p=client.get('wp/v2/posts/'+str(post_id)+'?context=edit')
    raw=p.get('content',{}).get('raw','')
    marker='wp-writer:topic='+topic['topic_id']+';sha256='+record['source_hash']
    if (p.get('status')!=record['expected_status'] or p.get('slug')!=record['slug'] or
        title_of(p)!=topic['title'] or p.get('categories')!=[record['category_id']] or
        marker not in raw or digest(visible(raw))!=record['visible_hash']):
        raise ValueError('WordPress content/status/category readback mismatch')
    if record['expected_status']=='publish':
        page,_=client.request(p['link'],public=True,page=True)
        if norm(topic['title']) not in norm(page) or norm(record['first_paragraph']) not in norm(page):
            raise ValueError('Public permalink content mismatch')
        if re.search(r'<meta[^>]+(?:noindex|http-equiv=[\"\']refresh)',page,re.I):raise ValueError('New post not indexable')
        from html.parser import HTMLParser
        class SEO(HTMLParser):
            def __init__(self):super().__init__();self.canon=[];self.description=[];self.in_title=False;self.title=''
            def handle_starttag(self,tag,attrs):
                d=dict(attrs)
                if tag=='link' and d.get('rel')=='canonical':self.canon.append(d.get('href'))
                if tag=='meta' and d.get('name')=='description':self.description.append(d.get('content'))
                if tag=='title':self.in_title=True
            def handle_endtag(self,tag):
                if tag=='title':self.in_title=False
            def handle_data(self,d):
                if self.in_title:self.title+=d
        seo=SEO();seo.feed(page)
        if seo.canon!=[topic['canonical_target']] or seo.description!=[record.get('meta_description')] or seo.title!=record.get('meta_title'):
            raise ValueError('Frontend canonical/title/meta mismatch')
    return p

class Publisher:
    def __init__(self,client,policy,ledger=None,persist=None,before_post=None):
        self.client=client;self.policy=policy;self.ledger=ledger if ledger is not None else load(LEDGER,{'version':1,'posts':{},'categories':{}})
        self.persist=persist or (lambda:save(LEDGER,self.ledger))
        self.before_post=before_post or (lambda topic,sha:None)
    def record(self,topic_id,**fields):
        self.ledger['posts'][topic_id]={**self.ledger['posts'].get(topic_id,{}),**fields,'updated_at':now()};self.persist()

    def reconcile(self,topic,live):
        rec=self.ledger['posts'].get(topic['topic_id'])
        if not rec:return None
        if rec.get('phase')=='VERIFIED':
            # Read-only verification also detects changes outside the factory.
            verify(self.client,topic,rec);return rec
        if rec.get('wp_id'):
            p=verify(self.client,topic,rec)
        else:
            hits=duplicate(topic,live)
            if len(hits)!=1:raise ValueError('Unresolved POST intent; never blindly retry')
            hit=hits[0];marker='wp-writer:topic='+topic['topic_id']+';sha256='+rec['source_hash']
            if marker not in hit.get('content',{}).get('raw',''):raise ValueError('Collision lacks ownership marker')
            self.record(topic['topic_id'],phase='VERIFY_PENDING',wp_id=hit['id'])
            p=verify(self.client,topic,self.ledger['posts'][topic['topic_id']])
        self.record(topic['topic_id'],phase='VERIFIED',wp_id=p['id'],status=p['status'],url=p['link'],verified_at=now())
        return self.ledger['posts'][topic['topic_id']]

    def create(self,topic,body,sha,category_id,status,live,meta=None,route=None):
        """No update/delete endpoint exists in this class."""
        if status not in ('draft','publish'):raise ValueError('Invalid status')
        if self.policy.get('paused') or self.policy.get('emergency_stop'):raise ValueError('Publisher paused')
        if status=='publish' and not production_allowed(self.policy):raise ValueError('Production disabled or acceptance incomplete')
        if status=='draft' and self.policy.get('mode')!='draft_only' and not (
                production_allowed(self.policy) and self.policy.get('on_category_mismatch')=='draft'
                and (route or {}).get('category_resolution')=='FALLBACK_DRAFT'):
            raise ValueError('Draft writes not explicitly enabled')
        prior=self.ledger['posts'].get(topic['topic_id'])
        if prior:
            if prior.get('source_hash')!=sha:raise ValueError('Published/uncertain topic source changed; review, never overwrite')
            return self.reconcile(topic,live)
        if duplicate(topic,live):raise ValueError('Existing WordPress content collision')
        if topic['canonical_target'] in {r.get('url') for r in load('data/protected-urls.json',{}).get('items',[])}:raise ValueError('Protected existing URL')
        rendered=post_html(topic,body,sha)
        payload={'title':topic['title'],'slug':topic['proposed_slug'],'content':rendered,'status':status,'categories':[category_id],
                 'excerpt':(meta or {}).get('meta_description','')}
        if status=='publish':
            # Adapter keys must be explicitly registered REST-writeable by the live site.
            payload['meta']={'_yoast_wpseo_title':meta['meta_title'],'_yoast_wpseo_metadesc':meta['meta_description'],'_yoast_wpseo_canonical':topic['canonical_target']}
        self.record(topic['topic_id'],phase='POST_INTENT',source_hash=sha,slug=topic['proposed_slug'],expected_status=status,
            category_id=category_id,visible_hash=digest(visible(rendered)),first_paragraph=visible(markdown.markdown(body.split('\n\n')[0])),
            meta_title=(meta or {}).get('meta_title'),meta_description=(meta or {}).get('meta_description'),
            intended_taxonomy_key=(route or {}).get('intended_taxonomy_key'),
            category_resolution=(route or {}).get('category_resolution','EXACT'),
            category_warning=(route or {}).get('category_warning'),
            git_commit=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'))
        # persist() MUST return successfully (remote in Actions) before this POST.
        try:
            self.before_post(topic,sha)
            p=self.client.request('wp/v2/posts',payload)[0]
            if p['id'] in PROTECTED_IDS:raise ValueError('Unexpected protected post ID')
            self.record(topic['topic_id'],phase='VERIFY_PENDING',wp_id=p['id'])
            verified=verify(self.client,topic,self.ledger['posts'][topic['topic_id']])
            self.record(topic['topic_id'],phase='VERIFIED',wp_id=verified['id'],status=verified['status'],url=verified['link'],verified_at=now())
            live.append(verified);return self.ledger['posts'][topic['topic_id']]
        except Exception:
            # Intent already durable, including a crash before this optional checkpoint.
            self.record(topic['topic_id'],phase='NEEDS_RECONCILE')
            raise

def seo_adapter_check(client):
    response,_=client.request('wp/v2/posts',method='OPTIONS')
    props=response.get('schema',{}).get('properties',{}).get('meta',{}).get('properties',{})
    return all(k in props and props[k].get('readonly') is not True for k in ('_yoast_wpseo_title','_yoast_wpseo_metadesc','_yoast_wpseo_canonical'))

def run(args):
    base_policy=load('config/production-policy.json');policy=dict(base_policy)
    if args.acceptance_topic:
        if not args.persist_state or policy['production_enabled']:raise ValueError('Article draft acceptance requires production OFF and remote ledger')
        if not re.fullmatch(r'NT-\d{6}',args.acceptance_topic):raise ValueError('Invalid acceptance Topic ID')
        policy['mode']='draft_only'
    if args.acceptance_draft:
        if not args.persist_state:raise ValueError('Acceptance requires remote durable ledger')
        if policy['production_enabled']:raise ValueError('Acceptance only while production OFF')
        # Explicit isolated TEST DRAFT, not a campaign article, never promotes to public.
        policy={**policy,'mode':'draft_only'}
    if policy['paused'] or policy['emergency_stop']:print('PAUSED');return
    if policy.get('mode')=='draft_only' and not (
            draft_staging_allowed(policy) or args.acceptance_topic or args.acceptance_draft):
        raise ValueError('Unattended WordPress draft staging requires verified security and owner approval')
    rows=topics();results=[]
    if policy['mode']=='dry_run' and not args.acceptance_draft:
        for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
            matches=[t for t in rows if t['topic_id']==path.stem]
            if len(matches)!=1:raise ValueError('Unknown draft')
            result=evaluate(path,matches[0],rows=rows,live=False);save('data/qa/'+path.stem+'.json',result);results.append(result)
        save('reports/publisher-preview.json',{'mode':'dry_run','wordpress_writes':0,'qa':results,'at':now()});print('DRY_RUN: no WordPress writes');return
    with lock():
        client=WP(authenticated=True);client.get('wp/v2/users/me?context=edit&_fields=id')
        live=inventory(client);cats=client.all('wp/v2/categories',hide_empty='false')
        ledger=load(LEDGER,{'version':1,'posts':{},'categories':{}})
        state=RemoteState();state.remember([LEDGER])
        def persist():
            save(LEDGER,ledger)
            if args.persist_state:state.persist([LEDGER])
        def fresh_guard(topic,sha):
            if not args.persist_state:return
            git('fetch','origin','main');ref=git('rev-parse','origin/main')
            newest=json.loads(git('show',ref+':config/production-policy.json'))
            original=load('config/production-policy.json')
            if newest!=original or newest.get('paused') or newest.get('emergency_stop'):raise ValueError('Policy changed; stop before POST')
            if topic['topic_id'].startswith('NT-'):
                raw=subprocess.check_output(['git','show',ref+':posts/drafts/'+topic['topic_id']+'.md'],cwd=ROOT)
                if digest(raw)!=sha:raise ValueError('Remote draft changed after QA; stop before POST')
        publisher=Publisher(client,policy,ledger,persist,before_post=fresh_guard)
        if args.acceptance_draft:
            t={'topic_id':'ACCEPTANCE-20261016','title':'[KIỂM THỬ] Universal Factory draft-only acceptance','proposed_slug':'wp-writer-factory-acceptance-20261016','canonical_target':SITE+'/wp-writer-factory-acceptance-20261016/'}
            body='Bài nháp kiểm thử giao dịch của Universal Content Factory. Chỉ kiểm tra REST, danh mục Blog, ledger và khả năng chạy lại không tạo trùng. Không phải bài SEO, không thuộc chỉ tiêu 1.000 bài và không được xuất bản công khai. Bài nháp kết nối cũ 3861 được giữ nguyên.'
            category=resolve('blog',by_key(),cats)
            rec=publisher.create(t,body,digest(body),category,'draft',live)
            # Second call is the real idempotency acceptance check; must reuse the ID.
            again=publisher.create(t,body,digest(body),category,'draft',live)
            if rec['wp_id']!=again['wp_id']:raise ValueError('Idempotency acceptance failed')
            save('reports/acceptance-rest.json',{'status':'PASS','wp_id':rec['wp_id'],'wordpress_status':'draft','category_id':category,'rerun_same_id':True,'legacy_3861_unchanged':client.get('wp/v2/posts/3861?context=edit').get('status')=='draft','at':now()})
            print('ACCEPTANCE_DRAFT_VERIFIED: id='+str(rec['wp_id']));return
        if not production_allowed(policy) and not (
                draft_staging_allowed(policy) or args.acceptance_topic or args.acceptance_draft):
            raise ValueError('WordPress activation prerequisites incomplete')
        if production_allowed(policy) and not seo_adapter_check(client):raise ValueError('Yoast metadata REST adapter unavailable; production blocked')
        # Current public and non-public WordPress content used in collision/factual review.
        from audit import run as audit_run
        audit_run(True)
        policy_runtime=load('config/production-policy.json')
        if policy_runtime!=base_policy:raise ValueError('Policy changed during inventory')
        attempted=0
        for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
            if args.acceptance_topic and path.stem!=args.acceptance_topic:continue
            if attempted>=min(2,policy['batch_size']):break
            t=next(t for t in rows if t['topic_id']==path.stem)
            prior=ledger['posts'].get(t['topic_id'])
            if prior:
                if prior.get('phase')!='VERIFIED':publisher.reconcile(t,live)
                continue
            ephemeral=[]
            for p in live:
                ephemeral.append({'id':p['id'],'title':title_of(p),'title_hash':digest(norm(title_of(p))),
                    'slug':p.get('slug'),'url':p.get('link'),'canonical':p.get('yoast_head_json',{}).get('canonical'),
                    'status':p.get('status'),'categories':p.get('categories',[]),
                    'content_text':visible(p.get('content',{}).get('raw',p.get('content',{}).get('rendered',''))),
                    'content_hash':digest(visible(p.get('content',{}).get('raw',p.get('content',{}).get('rendered',''))))})
            # Include public products and baseline exclusions; unpublished content exists only in RAM.
            ephemeral.extend(p for p in load('data/existing-content-inventory.json')['items'] if p['id'] not in {q['id'] for q in ephemeral})
            result=evaluate(path,t,rows=rows,inv=ephemeral,live=True);save('data/qa/'+path.stem+'.json',result)
            if result['status']!='PASS':results.append(result);continue
            meta,body,sha=read_article(path)
            receipt=load('data/state/writer-claims.json',{}).get('submissions',{}).get(t['topic_id'],{})
            if receipt.get('sha256')!=sha or receipt.get('session')!=meta.get('writer_session'):raise ValueError('Missing valid writer submission receipt')
            try:
                route=delivery_route(t,policy,by_key(),cats,
                    create_category=lambda key:materialize(key,by_key(),cats,client,ledger,persist),
                    acceptance_draft=bool(args.acceptance_topic))
            except ValueError as exc:
                results.append({'topic_id':t['topic_id'],'status':'BLOCKED','errors':[str(exc)]});continue
            daily=sum(k.startswith('NT-') and rec.get('expected_status')==route['status']
                and rec.get('updated_at','')[:10]==now()[:10]
                for k,rec in ledger['posts'].items())
            limit=policy.get('max_new_posts_daily',10) if route['status']=='publish' else policy.get('max_new_drafts_daily',10)
            if daily>=limit:
                results.append({'topic_id':t['topic_id'],'status':'DAILY_CAP','mode':route['status']})
                continue
            attempted+=1
            publisher.create(t,body,sha,route['category_id'],route['status'],live,meta,route=route)
            results.append({'topic_id':t['topic_id'],'status':'WORDPRESS_'+route['status'].upper(),
                'category_id':route['category_id'],'category_resolution':route['category_resolution'],
                'intended_taxonomy_key':route['intended_taxonomy_key'],
                'category_warning':route['category_warning']})
        save('reports/publisher-latest.json',{'at':now(),'attempted':attempted,'qa':results,'backlog_drains_on':'next schedule or push','production':production_allowed(policy)})
        if args.acceptance_topic:
            rec=ledger['posts'].get(args.acceptance_topic,{})
            if rec.get('phase')!='VERIFIED' or rec.get('status')!='draft':raise ValueError('Article acceptance blocked; inspect QA/taxonomy report')
            t=next(t for t in rows if t['topic_id']==args.acceptance_topic)
            verify(client,t,rec)
            save('reports/article-acceptance.json',{'at':now(),'topic_id':t['topic_id'],'wp_id':rec['wp_id'],'status':'draft',
                'category_id':rec['category_id'],'qa_status':load('data/qa/'+t['topic_id']+'.json')['status'],
                'source_hash':rec['source_hash'],'public_posts_created':0,'production_enabled':False})

def main():
    p=argparse.ArgumentParser();p.add_argument('--persist-state',action='store_true');p.add_argument('--acceptance-draft',action='store_true');p.add_argument('--acceptance-topic');a=p.parse_args();run(a)

if __name__=='__main__':main()
