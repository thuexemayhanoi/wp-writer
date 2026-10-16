"""Verified full parent-path mapping; just-in-time creation is opt-in."""
import html
from common import load, now, save

def by_key(): return {x['taxonomy_key']:x for x in load('data/taxonomy.json')['items']}

def path_for(key, registry):
    result=[];seen=set()
    while key:
        if key in seen or key not in registry: raise ValueError('Taxonomy cycle or missing parent')
        seen.add(key); result.append(registry[key]);key=registry[key]['parent_key']
    return list(reversed(result))

def resolve(key, registry, live):
    if key=='uncategorized': raise ValueError('Uncategorized forbidden')
    parent=0
    for item in path_for(key,registry):
        if item.get('wordpress_term_id'):
            matches=[c for c in live if c['id']==item['wordpress_term_id']]
        else:
            matches=[c for c in live if c['slug']==item['slug'] and c['parent']==parent]
        if len(matches)!=1: raise ValueError('Missing/ambiguous term:'+item['taxonomy_key'])
        term=matches[0]
        if term['parent']!=parent or term['slug']!=item['slug'] or html.unescape(term['name'])!=item['name']:
            raise ValueError('Term ancestry/name/slug drift:'+item['taxonomy_key'])
        parent=term['id']
    return parent

def materialize(key, registry, live, client, ledger, persist):
    """Never called for unapproved article. Record category intent BEFORE POST."""
    parent=0
    for item in path_for(key,registry):
        try:
            parent=resolve(item['taxonomy_key'],registry,live);continue
        except ValueError:
            if item['existing_or_planned']=='existing': raise
        old=ledger['categories'].get(item['taxonomy_key'])
        if old and old['phase'] in ('POST_INTENT','UNKNOWN'):
            raise ValueError('Uncertain category creation; reconcile first')
        # Slug is globally unique in WP; refuse a term under a different parent.
        if any(c['slug']==item['slug'] for c in live): raise ValueError('Category slug collision')
        ledger['categories'][item['taxonomy_key']]={'phase':'POST_INTENT','slug':item['slug'],'parent':parent,'at':now()};persist()
        term=client.request('wp/v2/categories',{'name':item['name'],'slug':item['slug'],'parent':parent,'description':item['description']})[0]
        if term['parent']!=parent or term['slug']!=item['slug']: raise ValueError('Category readback mismatch')
        live.append(term);parent=term['id']
        ledger['categories'][item['taxonomy_key']].update(phase='CREATED_PENDING_ARTICLE',term_id=parent);persist()
    return resolve(key,registry,live)
