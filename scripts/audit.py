"""Read every audit sheet and refresh WordPress without any writes."""
import argparse
import json
from collections import Counter
from pathlib import Path
import openpyxl
from common import ROOT, SITE, WP, Text, digest, inventory, load, now, save, title_of, norm, visible

def read_excel(path):
    w = openpyxl.load_workbook(path, data_only=True, read_only=True)
    return {s.title:[list(row) for row in s.iter_rows(values_only=True)] for s in w}

def run(authenticated=False):
    source = ROOT/'data/source/audit-2026-10-16.xlsx'
    excel = read_excel(source)
    save('data/source/audit-all-sheets.json', excel)
    client = WP(authenticated)
    raw = inventory(client)
    cats = client.all('wp/v2/categories', hide_empty='false')
    failures=[]
    try:
        products = client.all('wc/store/v1/products')
        for p in products:
            p.update(resource='products',status='publish',link=p.get('permalink',''),title=p.get('name',''),content={'rendered':p.get('description','')})
        raw.extend(products)
    except Exception as e:
        failures.append({'resource':'products','error':str(e)})
    rows=[]
    for p in raw:
        content=p.get('content',{}); body=content.get('raw',content.get('rendered',''))
        title=title_of(p); seo=p.get('yoast_head_json',{})
        parser=Text(); parser.feed(body)
        public=p.get('status')=='publish'
        record={'id':p['id'],'type':p['resource'],'status':p['status'],'title':title if public else None,
            'title_hash':digest(norm(title)),'slug':p.get('slug') if public else None,'slug_hash':digest(p.get('slug','')),
            'url':p.get('link') if public else None,'canonical':seo.get('canonical') if public else None,
            'categories':p.get('categories',[]),'content_hash':digest(visible(body)),
            'content_text':visible(body) if public else None,'links':parser.links if public else [],
            'seo_title':seo.get('title') if public else None,'meta_description':seo.get('description') if public else None,
            'robots':seo.get('robots') if public else None,'schema_types':[v.get('@type') for v in seo.get('schema',{}).get('@graph',[])],
            'verified_at':now(),'source':'authenticated REST' if authenticated else 'public REST'}
        rows.append(record)
    # Preserve baseline-only records as unverified exclusions, never silently lose a URL.
    found={p['id'] for p in rows}
    for r in excel['01_URL_Inventory'][1:]:
        if r[0] not in found:
            rows.append({'id':r[0],'type':r[1],'status':r[2],'title':r[3] if r[2]=='publish' else None,'title_hash':digest(norm(r[3])),
                         'slug_hash':digest(r[5] or ''),'url':r[4] if r[2]=='publish' else None,'categories':r[6],
                         'source':'Excel baseline; not live verified','verified_at':None})
    technical={}
    for path in ('/robots.txt','/sitemap_index.xml','/wp-sitemap.xml','/'):
        try:
            text, headers=client.request(SITE+path,public=True,page=True)
            technical[path]={'ok':True,'bytes':len(text),'sha256':digest(text)}
            if path!='/': technical[path]['content']=text
            else:
                import re
                technical[path]['canonical']=re.findall(r'<link[^>]+rel=[\"\']canonical[\"\'][^>]+href=[\"\']([^\"\']+)',text)
                technical[path]['viewport']=bool(re.search('name=[\"\']viewport',text))
        except Exception as e: technical[path]={'ok':False,'error':str(e)}
    save('data/existing-content-inventory.json',{'site':SITE,'updated_at':now(),'authenticated':authenticated,'items':rows})
    save('data/existing-taxonomy.json',{'verified_at':now(),'items':cats})
    protected=[{'id':r['id'],'url':r.get('url'),'slug':r.get('slug'),'title_hash':r.get('title_hash'),'content_hash':r.get('content_hash'),'reason':'Existing URL; immutable'} for r in rows]
    protected.append({'id':None,'url':SITE+'/','reason':'Homepage commercial; immutable'})
    save('data/protected-urls.json',{'site':SITE,'items':protected,'protected_test_ids':[3861]})
    counts=dict(Counter(r['resource'] for r in raw if r.get('status')=='publish'))
    save('reports/audit.json',{'at':now(),'sheets_read':list(excel),'excel_sha256':digest(source.read_bytes()),'counts':counts,
        'authenticated':authenticated,'private_inventory_verified':authenticated,'technical':technical,'failures':failures,
        'limits':['No Google indexing inference','No mobile CWV field data','No edits to existing URLs, taxonomy or theme']})
    print(json.dumps({'sheets':len(excel),'counts':counts,'authenticated':authenticated,'failures':failures},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--authenticated',action='store_true');a=p.parse_args();run(a.authenticated)
