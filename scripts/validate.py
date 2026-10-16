"""Repository-wide invariants; no network or mutations."""
from common import ROOT,SITE,load,topics
from taxonomy_sync import by_key,path_for,resolve
from writer_session import live_leases

def run():
    rows=topics();ids=[t['topic_id'] for t in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate Topic ID')
    regs=load('data/taxonomy.json')['items'];keys=[t['taxonomy_key'] for t in regs]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate taxonomy key')
    mapped=[r['wordpress_term_id'] for r in regs if r['wordpress_term_id']]
    if len(mapped)!=len(set(mapped)):raise ValueError('Duplicate WordPress term mapping')
    registry=by_key();live=load('data/existing-taxonomy.json')['items']
    for r in regs:
        path_for(r['taxonomy_key'],registry)
        if r['status']=='ACTIVE' and r['taxonomy_key']!='uncategorized':resolve(r['taxonomy_key'],registry,live)
    for t in rows:
        if t['taxonomy_key'] not in registry:raise ValueError('Unknown topic category')
        if t['canonical_target']!=SITE+'/'+t['proposed_slug']+'/':raise ValueError('Topic canonical drift')
        if t['word_target_min']!=1600 or t['word_target_max']!=5000:raise ValueError('Campaign word-count drift')
    live_leases(load('data/state/writer-claims.json'))
    if sum(d['initial_allocation'] for d in load('data/topic-domains.json')['domains'])!=1000:raise ValueError('Allocation drift')
    print('INVARIANTS PASS')

if __name__=='__main__':run()
