"""Six independent hard gates. Scores never override FAIL/REVIEW."""
import argparse
import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
import yaml
from common import ROOT, SITE, Text, WP, Redirect, digest, load, norm, now, save, topics, visible
from taxonomy_sync import by_key,path_for
from topic_factory import gate as topic_gate

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

def jaccard(a,b):return len(a&b)/max(1,len(a|b))

def mdlinks(body):return [(a,u) for a,u in re.findall(r'(?<!!)\[([^\]]*)\]\(([^\s)]+)(?:\s+[^)]*)?\)',body)]

def seo_onpage_score(meta, body, topic, internal, rules):
    """Deterministic, intent-aware on-page rubric for the main WordPress site.

    Scores are editorial *pre-publication* proxies, not Yoast/Google rankings.
    No mandatory images, FAQs, keyword density, or commercial sales CTAs.
    Other six gates remain authoritative even with a perfect SEO score.
    """
    focus = [token for token in norm(topic.get('primary_keyword', '')).split()
             if token not in {'va', 'la', 'cua', 'cho', 'nhung', 'cac', 'mot',
                              'khi', 'the', 'nao', 'gi', 'co', 'the', 'nen',
                              've', 'o', 'de', 'tren', 'voi', 'trong'}]
    focus = set(focus)
    def coverage(text):
        words = set(norm(str(text or '')).split())
        return len(focus & words) / max(1, len(focus))
    def relevance(text, top=15):
        part = coverage(text)
        if part >= 0.70: return top
        if part >= 0.50: return round(top * 0.70)
        if part >= 0.30: return round(top * 0.35)
        return 0
    sections = [m.strip() for m in re.findall(r'^##\s+(.+)
    u=urllib.parse.urlsplit(url);host=u.hostname or ''
    if u.scheme!='https' or u.username or u.password or u.port not in (None,443):return False
    legal_hosts=load('config/qa-rules.json')['legal_hosts']
    hosts=legal_hosts+['honda.com.vn','yamaha-motor.com.vn','vinfastauto.com','vme.org.vn','hanoimetro.net.vn','vietnam.travel','vietnamtourism.gov.vn']
    return any(host==h or host.endswith('.'+h) for h in (legal_hosts if legal else hosts)) or (not legal and host.endswith('.gov.vn'))

def verify_sources(sources,live=False):
    errors=[];evidence=[]
    for s in sources:
        if not isinstance(s,dict) or not allowed_source(s.get('url','')):errors.append('Source host not allowlisted');continue
        try:
            checked=dt.date.fromisoformat(str(s.get('checked_at',''))[:10])
            age=(dt.date.today()-checked).days
            if age<0 or age>load('config/qa-rules.json')['source_max_age_days']:raise ValueError('Source date stale')
            if not s.get('supports') or not s.get('evidence_text') or len(s['evidence_text'].split())<4:raise ValueError('Source claim/evidence missing')
            if live:
                opener=urllib.request.build_opener(Redirect())
                req=urllib.request.Request(s['url'],headers={'User-Agent':'NguyenTu-WPWriter/1.0'})
                with opener.open(req,timeout=20) as response:raw=response.read(8_000_000).decode('utf-8',errors='replace')
                text=visible(raw)
                if norm(s['evidence_text']) not in norm(text):raise ValueError('Source excerpt not found')
                evidence.append({'url':s['url'],'supports':s['supports'],'sha256':digest(text),'verified_at':now()})
            elif not s.get('source_sha256'):raise ValueError('Unverified source snapshot')
        except Exception as e:errors.append('Source REVIEW: '+type(e).__name__)
    return errors,evidence

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
    gates={str(i):{'errors':[],'review':[]} for i in range(1,7)}
    try:meta,body,sha=read_article(path)
    except Exception as e:return {'topic_id':topic['topic_id'],'status':'FAIL','errors':[str(e)],
        'review':[],'source_sha256':digest(path.read_bytes()),'gates':gates,'at':now()}
    g1=gates['1'];g2=gates['2'];g3=gates['3'];g4=gates['4'];g5=gates['5'];g6=gates['6']
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
    source_errors,source_evidence=verify_sources(sources,live)
    g3['review']+=source_errors
    if re.search(r'\d',body) and not sources and not meta.get('business_claims'):g3['review'].append('Numeric claims need cited evidence')
    if re.search(r'(?i)tôi đã (?:thử|chạy|trải nghiệm)|khách hàng đánh giá 5|100% an toàn',body):g3['review'].append('Unverified experience/review/absolute claim')
    identity=topic_gate(topic,rows,inv,load('data/taxonomy.json')['items'])
    g4['errors']+=identity['errors'];g4['review']+=identity['review']
    body_shingles=shingles(counted_text(body))
    for p in inv:
        if p.get('content_text') and jaccard(body_shingles,shingles(p['content_text']))>=rules['near_duplicate_jaccard']:
            g4['errors'].append('Near duplicate existing:'+str(p['id']))
    for other in (ROOT/'posts/drafts').glob('NT-*.md'):
        if other.resolve()==path.resolve():continue
        try:othermeta,otherbody,_=read_article(other)
        except Exception:continue
        if jaccard(body_shingles,shingles(counted_text(otherbody)))>=rules['near_duplicate_jaccard']:g4['errors'].append('Near duplicate draft:'+other.name)
    public_urls={p.get('url') for p in inv if p.get('status')=='publish'}|{SITE+'/'}
    links=mdlinks(body);internal=[]
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
    if not set(internal)&set(topic.get('internal_link_candidates',[])):g5['review'].append('No cluster link from reviewed candidate list')
    if not meta.get('link_rationale'):g5['review'].append('Contextual link rationale missing')
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
    errors=[e for g in gates.values() for e in g['errors']]
    reviews=[e for g in gates.values() for e in g['review']]
    status='FAIL' if errors or quality < rules['quality_min'] else 'REVIEW' if reviews else 'PASS'
    return {'topic_id':topic['topic_id'],'status':status,'source_sha256':sha,'body_sha256':digest(body),'word_count':wc,
        'quality_score':quality,'seo_score':seo,'seo_min_required':rules['seo_min'],
        'seo_checks':seo_checks,'seo_recommendations':seo_recommendations,
        'gates':gates,'errors':errors,'review':reviews,'source_evidence':source_evidence,
        'at':now(),'live_links_checked':live,'legal_required':legal,'rules_sha256':digest(json.dumps(rules,sort_keys=True)),
        'inventory_sha256':digest(json.dumps(inv,ensure_ascii=False,sort_keys=True))}

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');a=p.parse_args()
    rows=topics();results=[]
    for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
        match=[t for t in rows if t['topic_id']==path.stem]
        if len(match)!=1:raise ValueError('Unknown or ambiguous draft ID')
        r=evaluate(path,match[0],rows=rows,live=a.live);save('data/qa/'+path.stem+'.json',r);results.append(r)
    save('reports/repair-queue.json',[r for r in results if r['status']!='PASS'])
    print(json.dumps({'authored':len(results),'pass':sum(r['status']=='PASS' for r in results),'repair':sum(r['status']!='PASS' for r in results)}))
    return 1 if any(r['status']!='PASS' for r in results) else 0

if __name__=='__main__':raise SystemExit(main())
, body, re.M)]
    informative = [h for h in sections if len(norm(h).split()) >= 4]
    first_paragraph = body.split('\n\n', 1)[0]
    introduction = body[:1800]
    answer = str(meta.get('direct_answer') or '').strip()
    answer_present = bool(answer and norm(answer) in norm(introduction))
    unique_internal = set()
    descriptive_anchors = []
    for anchor, url in mdlinks(body):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme == 'https' and parsed.netloc == 'thuexemaynguyentu.com'
            and url in internal and parsed.path not in ('', '/'):
            unique_internal.add(url)
            a = norm(anchor)
            if len(a.split()) >= 3 and a not in ('xem them', 'tai day', 'bam vao day', 'click here'):
                descriptive_anchors.append(anchor)
    title_points = relevance(meta.get('meta_title'))
    desc_points = relevance(meta.get('meta_description'))
    intro_points = relevance(first_paragraph)
    direct_points = 10 if answer_present and len(norm(answer).split()) >= 18 else 5 if answer_present else 0
    structure_points = 10 if len(set(map(norm, informative))) >= rules['minimum_h2'] else 0
    topical_heading_points = 5 if any(coverage(h) >= 0.35 for h in sections) else 0
    heading_points = structure_points + topical_heading_points
    links_points = 10 if unique_internal else 0
    if len(unique_internal) >= 2: links_points += 5
    anchor_points = 5 if descriptive_anchors else 0
    canonical_points = 10 if (meta.get('canonical_target') == topic.get('canonical_target')
        and topic.get('canonical_target') == SITE + '/' + str(topic.get('proposed_slug', '')) + '/') else 0
    values = {
        'seo_title_relevance': (title_points, 15, 'Make SEO title accurately match the primary search intent'),
        'meta_description_relevance': (desc_points, 15, 'Summarize the exact reader question in the meta description'),
        'opening_intent_focus': (intro_points, 15, 'Address the actual primary question naturally in the opening paragraph'),
        'direct_answer': (direct_points, 10, 'Include a substantive answer at the beginning'),
        'headings_usefulness': (heading_points, 15, 'Use four distinct meaningful H2 sections, including a related subtopic'),
        'verified_contextual_links': (links_points, 15, 'Link to relevant existing public articles; two distinct links when natural'),
        'descriptive_anchor': (anchor_points, 5, 'Use descriptive anchor text, not a generic click-here link'),
        'canonical_identity': (canonical_points, 10, 'Keep canonical exactly aligned with approved WordPress URL'),
    }
    breakdown = {k: {'points': score, 'max': maximum} for k, (score, maximum, _) in values.items()}
    if sum(item['max'] for item in breakdown.values()) != 100:
        raise ValueError('SEO rubric must total exactly 100 points')
    recommendations = [tip for score, maximum, tip in values.values() if score < maximum]
    return sum(item['points'] for item in breakdown.values()), breakdown, recommendations

def allowed_source(url, legal=False):
    u=urllib.parse.urlsplit(url);host=u.hostname or ''
    if u.scheme!='https' or u.username or u.password or u.port not in (None,443):return False
    legal_hosts=load('config/qa-rules.json')['legal_hosts']
    hosts=legal_hosts+['honda.com.vn','yamaha-motor.com.vn','vinfastauto.com','vme.org.vn','hanoimetro.net.vn','vietnam.travel','vietnamtourism.gov.vn']
    return any(host==h or host.endswith('.'+h) for h in (legal_hosts if legal else hosts)) or (not legal and host.endswith('.gov.vn'))

def verify_sources(sources,live=False):
    errors=[];evidence=[]
    for s in sources:
        if not isinstance(s,dict) or not allowed_source(s.get('url','')):errors.append('Source host not allowlisted');continue
        try:
            checked=dt.date.fromisoformat(str(s.get('checked_at',''))[:10])
            age=(dt.date.today()-checked).days
            if age<0 or age>load('config/qa-rules.json')['source_max_age_days']:raise ValueError('Source date stale')
            if not s.get('supports') or not s.get('evidence_text') or len(s['evidence_text'].split())<4:raise ValueError('Source claim/evidence missing')
            if live:
                opener=urllib.request.build_opener(Redirect())
                req=urllib.request.Request(s['url'],headers={'User-Agent':'NguyenTu-WPWriter/1.0'})
                with opener.open(req,timeout=20) as response:raw=response.read(8_000_000).decode('utf-8',errors='replace')
                text=visible(raw)
                if norm(s['evidence_text']) not in norm(text):raise ValueError('Source excerpt not found')
                evidence.append({'url':s['url'],'supports':s['supports'],'sha256':digest(text),'verified_at':now()})
            elif not s.get('source_sha256'):raise ValueError('Unverified source snapshot')
        except Exception as e:errors.append('Source REVIEW: '+type(e).__name__)
    return errors,evidence

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
    gates={str(i):{'errors':[],'review':[]} for i in range(1,7)}
    try:meta,body,sha=read_article(path)
    except Exception as e:return {'topic_id':topic['topic_id'],'status':'FAIL','errors':[str(e)],
        'review':[],'source_sha256':digest(path.read_bytes()),'gates':gates,'at':now()}
    g1=gates['1'];g2=gates['2'];g3=gates['3'];g4=gates['4'];g5=gates['5'];g6=gates['6']
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
    source_errors,source_evidence=verify_sources(sources,live)
    g3['review']+=source_errors
    if re.search(r'\d',body) and not sources and not meta.get('business_claims'):g3['review'].append('Numeric claims need cited evidence')
    if re.search(r'(?i)tôi đã (?:thử|chạy|trải nghiệm)|khách hàng đánh giá 5|100% an toàn',body):g3['review'].append('Unverified experience/review/absolute claim')
    identity=topic_gate(topic,rows,inv,load('data/taxonomy.json')['items'])
    g4['errors']+=identity['errors'];g4['review']+=identity['review']
    body_shingles=shingles(counted_text(body))
    for p in inv:
        if p.get('content_text') and jaccard(body_shingles,shingles(p['content_text']))>=rules['near_duplicate_jaccard']:
            g4['errors'].append('Near duplicate existing:'+str(p['id']))
    for other in (ROOT/'posts/drafts').glob('NT-*.md'):
        if other.resolve()==path.resolve():continue
        try:othermeta,otherbody,_=read_article(other)
        except Exception:continue
        if jaccard(body_shingles,shingles(counted_text(otherbody)))>=rules['near_duplicate_jaccard']:g4['errors'].append('Near duplicate draft:'+other.name)
    public_urls={p.get('url') for p in inv if p.get('status')=='publish'}|{SITE+'/'}
    links=mdlinks(body);internal=[]
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
    if not set(internal)&set(topic.get('internal_link_candidates',[])):g5['review'].append('No cluster link from reviewed candidate list')
    if not meta.get('link_rationale'):g5['review'].append('Contextual link rationale missing')
    try:path_for(topic['taxonomy_key'],by_key())
    except ValueError as e:g6['errors'].append(str(e))
    if topic.get('wp_post_id') in load('data/protected-urls.json',{}).get('protected_test_ids',[3861]):g6['errors'].append('Protected legacy post')
    if check_claim:
        receipt=load('data/state/writer-claims.json',{}).get('submissions',{}).get(topic['topic_id'],{})
        if receipt and (receipt.get('sha256')!=sha or receipt.get('session')!=meta.get('writer_session')):g6['errors'].append('Submission owner/hash mismatch')
    errors=[e for g in gates.values() for e in g['errors']];reviews=[e for g in gates.values() for e in g['review']]
    quality=max(0,100-len(g2['errors'])*15-len(g3['review'])*15-len(g3['errors'])*25)
    seo=max(0,100-len(g1['errors'])*20-len(g5['errors'])*20-len(g5['review'])*10)
    status='FAIL' if errors else 'REVIEW' if reviews else 'PASS'
    if quality<75 or seo<70:status='FAIL'
    return {'topic_id':topic['topic_id'],'status':status,'source_sha256':sha,'body_sha256':digest(body),'word_count':wc,
        'quality_score':quality,'seo_score':seo,'gates':gates,'errors':errors,'review':reviews,'source_evidence':source_evidence,
        'at':now(),'live_links_checked':live,'legal_required':legal,'rules_sha256':digest(json.dumps(rules,sort_keys=True)),
        'inventory_sha256':digest(json.dumps(inv,ensure_ascii=False,sort_keys=True))}

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');a=p.parse_args()
    rows=topics();results=[]
    for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
        match=[t for t in rows if t['topic_id']==path.stem]
        if len(match)!=1:raise ValueError('Unknown or ambiguous draft ID')
        r=evaluate(path,match[0],rows=rows,live=a.live);save('data/qa/'+path.stem+'.json',r);results.append(r)
    save('reports/repair-queue.json',[r for r in results if r['status']!='PASS'])
    print(json.dumps({'authored':len(results),'pass':sum(r['status']=='PASS' for r in results),'repair':sum(r['status']!='PASS' for r in results)}))
    return 1 if any(r['status']!='PASS' for r in results) else 0

if __name__=='__main__':raise SystemExit(main())
