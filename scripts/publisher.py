"""The ONLY WordPress writer. Create-only, remote write-ahead ledger."""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import markdown
from common import ROOT,SITE,WP,WPRejected,PROTECTED_IDS,digest,git,inventory,load,lock,norm,now,save,title_of,topics,visible
from git_state import RemoteState
from gate_triage import annotate,state_entry
from qa import evaluate,evaluate_safely,read_article
from taxonomy_sync import by_key,resolve,materialize

LEDGER='data/state/publication-ledger.json'

class RunStop(RuntimeError):
    """Nothing was written to WordPress, but this run must stop (policy or draft changed after QA)."""


def production_allowed(policy):
    """Owner switch for QA-PASS -> public WordPress.

    Owner order 2026-10-17: a post that passes the QA gate (SEO/quality >=85,
    duplicate check, exact category) is published immediately. No separate
    acceptance or branch-security flag gates publication; the QA, ledger,
    category and Yoast readback checks below are unchanged. paused and
    emergency_stop remain the owner's instant stop.
    """
    return (policy.get('production_enabled') is True and policy.get('mode')=='production' and
        bool(policy.get('owner_approval_ref')) and policy.get('seo_adapter_verified') is True and
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
    # Owner contract for all 51 Hanoi ward posts: EXACT category 182 or NO WP
    # write. Unlike other silos, ward pages must never create WP drafts, fall
    # back to Blog or auto-create per-ward categories when term 182 drifts.
    ward_public_only=(intended=='hanoi-ward-rentals')
    if ward_public_only and not public:
        raise ValueError('Hanoi ward publication requires QA-approved production')
    try:
        term_id=resolve(intended,registry,categories)
        return {'status':'publish' if public else 'draft','category_id':term_id,
                'intended_taxonomy_key':intended,'category_resolution':'EXACT',
                'category_warning':None}
    except ValueError as exc:
        category_error=str(exc)
    if ward_public_only:
        # Do not publish under a wrong parent and do not create a fallback
        # WordPress draft; keep the article on GitHub until REST reconciliation.
        raise ValueError('Hanoi ward category blocked: '+category_error)
    if public and policy.get('allow_category_create') and create_category:
        # Only the explicitly approved, ledger-protected JIT path may write terms.
        try:
            term_id=create_category(intended)
            return {'status':'publish','category_id':term_id,
                    'intended_taxonomy_key':intended,'category_resolution':'CREATED',
                    'category_warning':None}
        except ValueError as exc:
            # A category POST may have succeeded before the error. Do not silently
            # create a fallback draft after an uncertain taxonomy side effect.
            raise ValueError('Category creation needs reconciliation: '+str(exc)) from exc
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

def confirmed_post_drift(topic, record, live):
    """Report external WordPress status/category changes without touching either side.

    VERIFIED means the factory previously observed an exact state, not that
    other WordPress administrators/plugins cannot subsequently modify it.
    A drift report is NOT permission to overwrite or retry the old Topic ID.
    """
    if record.get('phase') != 'VERIFIED' or not record.get('wp_id'):
        return None
    matches=[p for p in live if p.get('resource','posts')=='posts'
             and p.get('id')==record['wp_id']]
    if len(matches)!=1:
        return {'topic_id':topic['topic_id'],'status':'EXTERNAL_WORDPRESS_DRIFT',
                'wp_id':record['wp_id'],'reason':'verified WordPress post missing or duplicated in live inventory',
                'action':'manual reconciliation; never create/update automatically'}
    post=matches[0]
    expected=record.get('expected_status') or record.get('status')
    differences={}
    if post.get('status') != expected:
        differences['status']={'ledger':expected,'wordpress':post.get('status')}
    if post.get('slug') != topic.get('proposed_slug'):
        differences['slug']={'ledger':topic.get('proposed_slug'),'wordpress':post.get('slug')}
    if post.get('categories') != [record.get('category_id')]:
        differences['categories']={'ledger':[record.get('category_id')],'wordpress':post.get('categories')}
    if expected=='publish' and post.get('link')!=topic.get('canonical_target'):
        differences['permalink']={'ledger':topic.get('canonical_target'),'wordpress':post.get('link')}
    yoast=post.get('yoast_head_json') or {}
    if expected=='publish' and yoast:
        # G7 on the live inventory: SEO meta and indexability of a verified public post, reported, never rewritten.
        if record.get('meta_title') and yoast.get('title')!=record['meta_title']:
            differences['seo_title']={'ledger':record['meta_title'],'wordpress':yoast.get('title')}
        if record.get('meta_description') and yoast.get('description')!=record['meta_description']:
            differences['seo_description']={'ledger':record['meta_description'],'wordpress':yoast.get('description')}
        if yoast.get('canonical') and yoast['canonical']!=topic.get('canonical_target'):
            differences['canonical']={'ledger':topic.get('canonical_target'),'wordpress':yoast.get('canonical')}
        if (yoast.get('robots') or {}).get('index') not in (None,'index'):
            differences['robots']={'ledger':'index','wordpress':yoast['robots'].get('index')}
    if differences:
        return {'topic_id':topic['topic_id'],'status':'EXTERNAL_WORDPRESS_DRIFT',
                'wp_id':record['wp_id'],'differences':differences,
                'action':'manual reconciliation; never create/update automatically'}
    return None


INVENTORY_FIELDS=('id','type','status','title_hash','slug_hash','content_hash','url','canonical','categories','seo_title','meta_description','robots')

def inventory_digest(items):
    """Digest of what matters in the stored inventory, so a refresh is persisted only when WordPress content really changed."""
    rows=sorted(([item.get(k) for k in INVENTORY_FIELDS] for item in items),key=lambda r:(str(r[1]),str(r[0])))
    return digest(json.dumps(rows,ensure_ascii=False,sort_keys=True))

def post_html(topic,body,sha):
    return '<!-- wp-writer:topic='+topic['topic_id']+';sha256='+sha+' -->\n'+markdown.markdown(body,extensions=['tables','sane_lists'])

def verify(client,topic,record,receipt=None):
    """Gate G7, read-only: everything WordPress must show after a write.

    `receipt` (optional dict) collects one boolean per check plus the observed ID, URL, status, canonical, SEO title and
    description, so the ledger holds a structured proof instead of only "VERIFIED". Any failed check raises exactly as before.
    """
    r=receipt if receipt is not None else {}
    r.update({'gate':'G7','status':'FAIL','wp_id':record.get('wp_id'),'checks':{}})
    def need(name,ok,message):
        r['checks'][name]=bool(ok)
        if not ok:
            r['failed']=name
            raise ValueError(message)
    post_id=record['wp_id']
    if post_id in PROTECTED_IDS:raise ValueError('Protected smoke-test post')
    p=client.get('wp/v2/posts/'+str(post_id)+'?context=edit')
    raw=p.get('content',{}).get('raw','')
    marker='wp-writer:topic='+topic['topic_id']+';sha256='+record['source_hash']
    readback='WordPress content/status/category readback mismatch'
    need('wordpress_status',p.get('status')==record['expected_status'],readback)
    need('slug',p.get('slug')==record['slug'],readback)
    need('title',title_of(p)==topic['title'],readback)
    need('category',p.get('categories')==[record['category_id']],readback)
    need('ownership_marker',marker in raw,readback)
    need('content',digest(visible(raw))==record['visible_hash'],readback)
    r.update(wordpress_status=p.get('status'),url=p.get('link'),categories=p.get('categories'))
    if record['expected_status']=='publish':
        need('permalink',p.get('link')==topic['canonical_target'],'Published permalink must match approved canonical')
        page,_=client.request(p['link'],public=True,page=True)
        need('public_page',norm(topic['title']) in norm(page) and norm(record['first_paragraph']) in norm(page),'Public permalink content mismatch')
        need('indexable',not re.search(r'<meta[^>]+(?:noindex|http-equiv=[\"\']refresh)',page,re.I),'New post not indexable')
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
        r.update(canonical=seo.canon[0] if seo.canon else None,seo_title=seo.title,
                 seo_description=seo.description[0] if seo.description else None)
        need('seo_meta',seo.canon==[topic['canonical_target']] and seo.description==[record.get('meta_description')] and seo.title==record.get('meta_title'),'Frontend canonical/title/meta mismatch')
    r['status']='PASS';r['checked_at']=now()
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
        receipt={}
        if rec.get('phase')=='VERIFIED':
            # Read-only verification also detects changes outside the factory.
            verify(self.client,topic,rec);return rec
        if rec.get('wp_id'):
            p=verify(self.client,topic,rec,receipt)
        else:
            hits=duplicate(topic,live)
            if len(hits)!=1:raise ValueError('Unresolved POST intent; never blindly retry')
            hit=hits[0];marker='wp-writer:topic='+topic['topic_id']+';sha256='+rec['source_hash']
            if marker not in hit.get('content',{}).get('raw',''):raise ValueError('Collision lacks ownership marker')
            self.record(topic['topic_id'],phase='VERIFY_PENDING',wp_id=hit['id'])
            p=verify(self.client,topic,self.ledger['posts'][topic['topic_id']],receipt)
        self.record(topic['topic_id'],phase='VERIFIED',wp_id=p['id'],status=p['status'],url=p['link'],verified_at=now(),g7=receipt)
        return self.ledger['posts'][topic['topic_id']]

    def withdraw(self,topic_id):
        """Drop a write-ahead intent whose POST provably never happened or was refused.

        Only a bare POST_INTENT (no WordPress ID) is withdrawn. A timeout, a 5xx or a
        failed readback stays NEEDS_RECONCILE and is never retried blindly.
        """
        rec=self.ledger['posts'].get(topic_id)
        if rec and rec.get('phase')=='POST_INTENT' and not rec.get('wp_id'):
            del self.ledger['posts'][topic_id]
            self.persist()

    def create(self,topic,body,sha,category_id,status,live,meta=None,route=None):
        """No update/delete endpoint exists in this class."""
        if status not in ('draft','publish'):raise ValueError('Invalid status')
        if self.policy.get('paused') or self.policy.get('emergency_stop'):raise ValueError('Publisher paused')
        if status=='publish' and not production_allowed(self.policy):raise ValueError('Production not enabled by owner')
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
        pilot=pilot_settings(self.policy)
        if pilot and pilot_reserved(self.ledger,pilot['id'])>=pilot['max_posts']:
            raise RunStop('Pilot limit reached; no new WordPress POST permitted')
        rendered=post_html(topic,body,sha)
        payload={'title':topic['title'],'slug':topic['proposed_slug'],'content':rendered,'status':status,'categories':[category_id],
                 'excerpt':(meta or {}).get('meta_description','')}
        if status=='publish':
            # Title and description must be REST-writeable. Yoast's canonical
            # is generated from the exact WordPress permalink by default.
            # The deployed HTML MUST read back the exact approved canonical.
            # Do not send _yoast_wpseo_canonical if that REST key is unregistered:
            # WordPress would silently ignore it while appearing to succeed.
            payload['meta']={'_yoast_wpseo_title':meta['meta_title'],
                             '_yoast_wpseo_metadesc':meta['meta_description']}
        self.record(topic['topic_id'],phase='POST_INTENT',created_at=now(),source_hash=sha,slug=topic['proposed_slug'],expected_status=status,
            pilot_id=pilot['id'] if pilot else None,
            category_id=category_id,visible_hash=digest(visible(rendered)),first_paragraph=visible(markdown.markdown(body.split('\n\n')[0])),
            meta_title=(meta or {}).get('meta_title'),meta_description=(meta or {}).get('meta_description'),
            intended_taxonomy_key=(route or {}).get('intended_taxonomy_key'),
            category_resolution=(route or {}).get('category_resolution','EXACT'),
            category_warning=(route or {}).get('category_warning'),
            git_commit=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'))
        # persist() MUST return successfully (remote in Actions) before this POST.
        try:
            self.before_post(topic,sha)
        except Exception as exc:
            # No WordPress request was sent: withdraw the intent so the topic is not
            # stranded as an "uncertain POST", then stop the run (policy/draft changed).
            self.withdraw(topic['topic_id'])
            raise RunStop('Stopped before POST: '+str(exc)) from exc
        receipt={}
        try:
            p=self.client.request('wp/v2/posts',payload)[0]
            if p['id'] in PROTECTED_IDS:raise ValueError('Unexpected protected post ID')
            self.record(topic['topic_id'],phase='VERIFY_PENDING',wp_id=p['id'])
            verified=verify(self.client,topic,self.ledger['posts'][topic['topic_id']],receipt)
            self.record(topic['topic_id'],phase='VERIFIED',wp_id=verified['id'],status=verified['status'],url=verified['link'],verified_at=now(),g7=receipt)
            live.append(verified);return self.ledger['posts'][topic['topic_id']]
        except WPRejected:
            # HTTP 4xx: WordPress refused the write and created nothing. Withdraw the
            # intent so the next run retries cleanly, and stop (do not flood a limiting host).
            self.withdraw(topic['topic_id'])
            raise
        except Exception:
            # Intent already durable, including a crash before this optional checkpoint.
            self.record(topic['topic_id'],phase='NEEDS_RECONCILE',**({'g7':receipt} if receipt else {}))
            raise


def attempt_create(publisher,ledger,results,topic,body,sha,route,live,meta):
    """Create one article without letting a single bad article block the queue.

    A refusal before any write (collision, source changed, protected URL, ...) skips
    only this article. Once a write-ahead intent exists the exception propagates so
    the run stops and an uncertain POST is never retried blindly.
    """
    try:
        publisher.create(topic,body,sha,route['category_id'],route['status'],live,meta,route=route)
    except ValueError as exc:
        if ledger['posts'].get(topic['topic_id']):raise
        results.append({'topic_id':topic['topic_id'],'status':'BLOCKED','errors':[str(exc)]})
        return False
    return True

def seo_adapter_check(client):
    """Fail closed without a real Yoast SEO metadata adapter.

    WordPress normally generates the canonical from the permalink; the
    custom canonical postmeta key need not be REST-writeable. We insist
    that SEO title+description are writeable and that the site's public
    Yoast canonical sample agrees with its own public permalink. Each new
    public post still gets strict frontend canonical/title/description QA.
    """
    response,_=client.request('wp/v2/posts',method='OPTIONS')
    props=response.get('schema',{}).get('properties',{}).get('meta',{}).get('properties',{})
    keys=('_yoast_wpseo_title','_yoast_wpseo_metadesc')
    if not all(k in props and props[k].get('readonly') is not True for k in keys):
        return False
    try:
        posts=client.get('wp/v2/posts?status=publish&per_page=1&_fields=id,link,yoast_head_json')
        if not isinstance(posts,list) or not posts:
            return False
        url=posts[0].get('link')
        canonical=posts[0].get('yoast_head_json',{}).get('canonical')
        return bool(url and url.startswith(SITE+'/') and canonical==url)
    except (RuntimeError,ValueError,KeyError,TypeError):
        return False

def delivery_batch_limit(policy):
    """Drain 2+2+2+2+2 within one serialized execution, never bypass caps.

    A batch remains at most TWO new WordPress POSTs; the number of
    consecutive batches is capped at FIVE. Daily new-post caps still apply
    independently, including draft category fallbacks.
    """
    per_batch=policy.get('batch_size',2)
    batches=policy.get('max_batches_per_run',1)
    if not isinstance(per_batch,int) or isinstance(per_batch,bool) or not 1<=per_batch<=2:
        raise ValueError('batch_size must be 1 or 2')
    if not isinstance(batches,int) or isinstance(batches,bool) or not 1<=batches<=5:
        raise ValueError('max_batches_per_run must be 1..5')
    return per_batch*batches


def pilot_settings(policy):
    """Optional owner-approved global cap across serialized Publisher executions.

    Reserve a slot BEFORE the WordPress POST by tagging the durable POST_INTENT;
    uncertain intents count as used until reconciled. Distinct run IDs/cron
    triggers cannot bypass a shared pilot ID. When absent, normal limits apply.
    """
    value = policy.get('publisher_pilot')
    if value is None:
        return None
    if not isinstance(value,dict):
        raise ValueError('publisher_pilot must be an object')
    key=value.get('id')
    count=value.get('max_posts')
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,63}',key):
        raise ValueError('Invalid publisher pilot ID')
    if type(count) is not int or not 1<=count<=10:
        raise ValueError('publisher_pilot.max_posts must be 1..10')
    return {'id':key,'max_posts':count}


def pilot_reserved(ledger, pilot_id):
    """Count all reserved POST_INTENTs including VERIFY_PENDING/VERIFIED/uncertain.

    A rejected pre-POST request may be withdrawn by the existing safe policy;
    no new POST is attempted for a recorded uncertain prior intent.
    """
    return sum(1 for topic_id,rec in ledger.get('posts',{}).items()
               if topic_id.startswith('NT-') and isinstance(rec,dict)
               and rec.get('pilot_id')==pilot_id)


def daily_created_count(ledger, utc_day, status=None):
    """Count first-create intents for one UTC day, including uncertain POSTs.

    Reconciliation updates updated_at, so it cannot serve as a stable
    publication-day key. Older entries use verified_at/updated_at fallback;
    new POST_INTENT entries carry an immutable created_at from the start.
    """
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', utc_day):
        raise ValueError('UTC day must be YYYY-MM-DD')
    count = 0
    for topic_id, rec in ledger.get('posts', {}).items():
        if not topic_id.startswith('NT-'):
            continue
        state = rec.get('expected_status') or rec.get('status')
        if state not in ('publish', 'draft'):
            continue
        if status is not None and state != status:
            continue
        stamped = (rec.get('created_at') or rec.get('verified_at')
                   or rec.get('updated_at') or '')
        if stamped[:10] == utc_day:
            count += 1
    return count


def run(args):
    base_policy=load('config/production-policy.json');policy=dict(base_policy)
    batch_limit=delivery_batch_limit(policy)
    pilot=pilot_settings(policy)
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
    if pilot and pilot_reserved(load(LEDGER,{'posts':{}}),pilot['id'])>=pilot['max_posts']:
        print('PILOT_FULL: existing durable write intents have consumed the 3-post test budget; no WordPress connection')
        return
    # Without the owner's production switch, return BEFORE reading WP secrets.
    # This is a clean no-op rather than an accidental missing-credentials error.
    if (policy.get('mode') == 'production' and not production_allowed(policy)
            and not args.acceptance_topic and not args.acceptance_draft):
        print('PRODUCTION_NOT_AUTHORIZED: production_enabled, owner_approval_ref or seo_adapter_verified missing; no WordPress writes')
        return
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
        if pilot and pilot_reserved(ledger,pilot['id'])>=pilot['max_posts']:
            print('PILOT_FULL: no new WordPress POST allowed')
            return
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
        stored_inventory=inventory_digest(load('data/existing-content-inventory.json',{}).get('items',[]))
        audit_run(True)
        # G4 self-refresh: when WordPress differs from the stored inventory, the fresh one is persisted (CAS) at the end of the run,
        # so researchers and writers compare against current content instead of a stale snapshot.
        inventory_changed=inventory_digest(load('data/existing-content-inventory.json',{}).get('items',[]))!=stored_inventory
        policy_runtime=load('config/production-policy.json')
        if policy_runtime!=base_policy:raise ValueError('Policy changed during inventory')
        attempted=0
        recheck_state=load('reports/gate-recheck.json',{})
        for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
            if args.acceptance_topic and path.stem!=args.acceptance_topic:continue
            if attempted>=batch_limit:break
            if pilot and pilot_reserved(ledger,pilot['id'])>=pilot['max_posts']:
                print('PILOT_FULL: maximum number of pilot WordPress write intents reached')
                break
            t=next((x for x in rows if x['topic_id']==path.stem),None)
            if t is None:
                results.append({'topic_id':path.stem,'status':'BLOCKED','errors':['Draft has no registered topic']});continue
            prior=ledger['posts'].get(t['topic_id'])
            if prior:
                if prior.get('phase')!='VERIFIED':
                    try:publisher.reconcile(t,live)
                    except ValueError as exc:
                        # An earlier uncertain POST is never retried blindly; it must not
                        # hold back every other article either.
                        results.append({'topic_id':t['topic_id'],'status':'NEEDS_RECONCILE','errors':[str(exc)]})
                else:
                    drift=confirmed_post_drift(t,prior,live)
                    if drift:
                        results.append(drift)
                continue
            ephemeral=[]
            factory_ids={r['wp_id'] for r in ledger['posts'].values() if r.get('wp_id')}
            for p in live:
                ephemeral.append({'id':p['id'],'evidence_exempt':p['id'] in factory_ids,
                    'title':title_of(p),'title_hash':digest(norm(title_of(p))),
                    'slug':p.get('slug'),'url':p.get('link'),'canonical':p.get('yoast_head_json',{}).get('canonical'),
                    'status':p.get('status'),'categories':p.get('categories',[]),
                    'content_text':visible(p.get('content',{}).get('raw',p.get('content',{}).get('rendered',''))),
                    'content_hash':digest(visible(p.get('content',{}).get('raw',p.get('content',{}).get('rendered',''))))})
            # Include public products and baseline exclusions; unpublished content exists only in RAM.
            ephemeral.extend(p for p in load('data/existing-content-inventory.json')['items'] if p['id'] not in {q['id'] for q in ephemeral})
            # One crashing or unreadable article is a FAIL ticket for that article only; the loop goes on.
            result=evaluate_safely(path,t,rows,live=True,inv=ephemeral)
            annotate(result,recheck_state.get(t['topic_id']))
            recheck_state[t['topic_id']]=state_entry(result)
            save('data/qa/'+path.stem+'.json',result)
            if result['status']!='PASS':results.append(result);continue
            meta,body,sha=read_article(path)
            receipt=load('data/state/writer-claims.json',{}).get('submissions',{}).get(t['topic_id'],{})
            if receipt.get('sha256')!=sha or receipt.get('session')!=meta.get('writer_session'):
                results.append({'topic_id':t['topic_id'],'status':'BLOCKED','errors':['Missing valid writer submission receipt']});continue
            try:
                route=delivery_route(t,policy,by_key(),cats,
                    create_category=lambda key:materialize(key,by_key(),cats,client,ledger,persist),
                    acceptance_draft=bool(args.acceptance_topic))
            except ValueError as exc:
                results.append({'topic_id':t['topic_id'],'status':'BLOCKED','errors':[str(exc)]});continue
            # Pilot is a PUBLIC-only smoke test: never create fallback WP drafts.
            if pilot and route['status']!='publish':
                results.append({'topic_id':t['topic_id'],'status':'PILOT_HOLD_CATEGORY',
                    'reason':'Public-only pilot: category mismatch, no WordPress draft created'})
                continue
            # One global owner cap across public posts and fallback drafts.
            # Count uncertain POST_INTENT before any further external write.
            today=now()[:10]
            all_created=daily_created_count(ledger,today)
            drafts_created=daily_created_count(ledger,today,status='draft')
            daily_cap=policy.get('max_new_posts_daily',10)
            draft_cap=policy.get('max_new_drafts_daily',10)
            if all_created>=daily_cap or (route['status']=='draft' and drafts_created>=draft_cap):
                results.append({'topic_id':t['topic_id'],'status':'DAILY_CAP',
                    'mode':route['status'],'today_total':all_created,
                    'daily_limit':daily_cap})
                continue
            if not attempt_create(publisher,ledger,results,t,body,sha,route,live,meta):continue
            attempted+=1
            results.append({'topic_id':t['topic_id'],'status':'WORDPRESS_'+route['status'].upper(),
                'category_id':route['category_id'],'category_resolution':route['category_resolution'],
                'intended_taxonomy_key':route['intended_taxonomy_key'],
                'category_warning':route['category_warning']})
        # Keep the recheck counters only for articles that are still waiting; a published or PASS article starts clean.
        save('reports/gate-recheck.json',{k:v for k,v in recheck_state.items()
            if v.get('status')!='PASS' and (ledger['posts'].get(k) or {}).get('phase')!='VERIFIED'})
        save('reports/publisher-latest.json',{'at':now(),'attempted':attempted,'batch_size':policy['batch_size'],'max_batches_per_run':policy['max_batches_per_run'],'batch_capacity':batch_limit,
            'pilot':({'id':pilot['id'],'max_posts':pilot['max_posts'],
                      'reserved':pilot_reserved(ledger,pilot['id'])} if pilot else None),
            'qa':results,'backlog_drains_on':'successful Writer QA or fallback schedule','production':production_allowed(policy)})
        if inventory_changed and args.persist_state:
            # Never fail a publishing run over the inventory refresh; the next run retries it.
            try:
                from save_audit import run as persist_audit
                persist_audit()
            except Exception as exc:
                print('INVENTORY_PERSIST_SKIPPED: '+type(exc).__name__+': '+str(exc)[:160])
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
