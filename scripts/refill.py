"""Import researched candidate batches when queue is low. No AI in Actions."""
from common import ROOT,digest,load,save,topics,now
from git_state import RemoteState
from topic_factory import run as topic_run

def run():
    policy=load('config/production-policy.json')
    count=sum(t['topic_qa_status']=='PLANNED' for t in topics())
    if count>=policy['min_claimable_queue']:print('Refill not needed');return
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
        save(path,ledger);state.persist(paths,'chore: apply researched topic refill [skip ci]')
    else:print('NEEDS_TOPIC_EXPANSION: external AI must research candidate batch')

if __name__=='__main__':run()
