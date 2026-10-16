"""Read-only drift/SEO adapter checks; never exposes credential values."""
import json
from common import WP,SITE,load,save,now
from publisher import seo_adapter_check
from taxonomy_sync import by_key,resolve

def run():
    c=WP(True);c.get('wp/v2/users/me?context=edit&_fields=id')
    cats=c.all('wp/v2/categories',hide_empty='false');errors=[]
    for key,r in by_key().items():
        if r['existing_or_planned']=='existing' and key!='uncategorized':
            try:resolve(key,by_key(),cats)
            except ValueError as e:errors.append(str(e))
    p=c.get('wp/v2/posts/3861?context=edit')
    if p['status']!='draft' or p['slug']!='wp-writer-connection-test-20261016':errors.append('Protected smoke draft drift')
    page,_=c.request(SITE+'/',public=True,page=True)
    report={'at':now(),'authenticated':True,'homepage_http_ok':bool(page),'protected_3861_status':p['status'],
            'existing_term_mapping_ok':not errors,'yoast_meta_rest_writeable':seo_adapter_check(c),'errors':errors}
    save('reports/health.json',report);print(json.dumps(report))
    if errors:raise ValueError('Health drift detected')

if __name__=='__main__':run()
