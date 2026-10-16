"""Read-only WordPress reconciliation. Never retries a missing POST."""
from common import WP,inventory,load,now,save
from publisher import Publisher,LEDGER
from taxonomy_sync import by_key
from common import topics

def run():
    client=WP(True);live=inventory(client);ledger=load(LEDGER);pub=Publisher(client,load('config/production-policy.json'),ledger)
    rows={t['topic_id']:t for t in topics()};issues=[]
    for key,r in ledger['posts'].items():
        if key not in rows:continue
        try:pub.reconcile(rows[key],live)
        except Exception as e:issues.append({'topic_id':key,'reason':str(e)})
    cats=client.all('wp/v2/categories',hide_empty='false')
    for key,r in ledger['categories'].items():
        hits=[c for c in cats if c['slug']==r['slug'] and c['parent']==r['parent']]
        if len(hits)==1:
            r['term_id']=hits[0]['id'];r['phase']='ACTIVE' if hits[0]['count']>0 else 'CREATED_PENDING_ARTICLE'
            if hits[0]['count']==0:issues.append({'taxonomy_key':key,'reason':'Empty new category; resume its READY article, no automatic deletion'})
        else:issues.append({'taxonomy_key':key,'reason':'Unresolved category intent; no blind retry'})
    save(LEDGER,ledger);save('reports/reconcile.json',{'at':now(),'issues':issues})

if __name__=='__main__':run()
