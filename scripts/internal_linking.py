import csv
import urllib.parse
from common import ROOT,SITE,load,save,now,norm

def catids(p):
    return {x.get('id') if isinstance(x,dict) else x for x in p.get('categories',[]) if isinstance(p.get('categories'),list)}

def build():
    items=load('data/existing-content-inventory.json',{}).get('items',[])
    public={p['url']:p for p in items if p.get('url') and p.get('status')=='publish'}
    edges=[];incoming={u:[] for u in public};unknown=[]
    for url,p in public.items():
        for link in p.get('links',[]):
            target=urllib.parse.urljoin(url,link['url']);parsed=urllib.parse.urlsplit(target)
            if parsed.hostname!='thuexemaynguyentu.com':continue
            clean=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))
            edge={'source':url,'target':clean,'anchor':link.get('anchor','').strip(),'cluster':str(p.get('categories',[])),
                'verified_in_inventory':clean in public,'http_checked':False}
            edges.append(edge)
            if clean in incoming:incoming[clean].append(url)
            elif clean!=SITE+'/':unknown.append(edge)
    graph=[]
    for url,p in public.items():
        same=[q['url'] for q in public.values() if q['url']!=url and catids(q)&catids(p)]
        graph.append({'url':url,'outgoing':[e for e in edges if e['source']==url],'incoming':incoming[url],
            'cluster':p.get('categories',[]),'recommended_links':same[:3],'recommendation_status':'Same-category candidates; contextual editorial review required'})
    save('reports/internal-linking-graph.json',{'at':now(),'nodes':graph,'unchecked_targets':unknown,'legacy_edits':0})
    with (ROOT/'reports/internal-links.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=['source','target','anchor','cluster','verified_in_inventory','http_checked']);writer.writeheader();writer.writerows(edges)
    return graph

if __name__=='__main__':build()
