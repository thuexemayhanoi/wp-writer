"""Import researched candidate batches when queue is low. No AI in Actions."""
from common import ROOT,digest,load,save,topics,now
from git_state import RemoteState
from topic_factory import run as topic_run
from writer_session import live_leases


def claimable_count(rows, registry, publication_ledger):
    """Only unreserved researched topics count toward writer capacity.

    The PLANNED manifest is historical and is not a backlog: topics already
    submitted/verified or held by live Writer leases must not hide low queue.
    Expired leases are reclaimable unless a submission receipt still owns ID.
    """
    busy=set(registry.get('submissions',{}))
    busy.update(publication_ledger.get('posts',{}))
    for lease in live_leases(registry).values():
        busy.update(lease.get('topic_ids',[]))
    return sum(row.get('topic_qa_status')=='PLANNED'
               and row.get('topic_id') not in busy for row in rows)

def run():
    policy=load('config/production-policy.json')
    registry=load('data/state/writer-claims.json',{})
    publication_ledger=load('data/state/publication-ledger.json',{})
    count=claimable_count(topics(),registry,publication_ledger)
    if count>=policy['min_claimable_queue']:
        print('Refill not needed: '+str(count)+' unreserved PLANNED topics available')
        return
    path='data/state/refill-ledger.json';ledger=load(path,{'batches':{}})
    paths=['data/topics.jsonl','data/taxonomy.json',path,'reports/topic-qa.json','reports/refill-request.json']
    state=RemoteState();state.remember(paths);changed=False
    for p in sorted((ROOT/'data/candidates').glob('*.jsonl')):
        sha=digest(p.read_bytes());name=p.name
        if ledger['batches'].get(name,{}).get('sha256')==sha:continue
        if name in ledger['batches']:raise ValueError('Accepted candidate batch immutable; create a new batch')
        topic_run(str(p.relative_to(ROOT)))
        ledger['batches'][name]={'sha256':sha,'at':now(),'state':'TOPIC_QA_APPLIED; see per-topic result'};changed=True
    if changed:
        save(path,ledger)
        # Always preserve reviewed candidate evidence, even if no topic qualifies.
        state.persist(paths,'chore: apply researched topic refill [skip ci]')
        after=claimable_count(topics(),registry,publication_ledger)
        if after<=count:
            raise SystemExit('NEEDS_TOPIC_EXPANSION: batches processed but zero new PLANNED topics; inspect topic QA')
        print('REFILL_PROGRESS: '+str(after-count)+' new researched PLANNED topics')
    else:
        # No synthetic topics: this is not a successful refill.
        raise SystemExit('NEEDS_TOPIC_EXPANSION: no new researched candidate batch; external writer required')

if __name__=='__main__':run()
