"""Admit GitHub-only writer pushes using live lease and exact file hash."""
from common import ROOT,digest,load,now,save,topics
from git_state import RemoteState
from writer_session import owner,REG
from qa import read_article

def run(persist=True):
    reg=load(REG);rows={t['topic_id']:t for t in topics()};changed=False
    ledger=load('data/state/publication-ledger.json',{'posts':{}})
    state=RemoteState();state.remember([REG])
    for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
        meta,body,sha=read_article(path);topic_id=path.stem
        old=reg.get('submissions',{}).get(topic_id,{})
        if old.get('sha256')==sha:continue
        if topic_id in ledger['posts']:raise ValueError('Cannot change uncertain/verified publication source')
        if topic_id not in rows or rows[topic_id]['topic_qa_status']!='PLANNED':raise ValueError('Unplanned topic push')
        slot=owner(reg,meta.get('writer_session'),topic_id)
        if meta.get('writer_slot')!=slot or meta.get('topic_id')!=topic_id:raise ValueError('Draft identity/slot mismatch')
        reg.setdefault('submissions',{})[topic_id]={'sha256':sha,'session':meta['writer_session'],'slot':slot,'submitted_at':now(),'lease_expires_at':reg['leases'][slot]['expires_at']}
        changed=True
    if changed:
        save(REG,reg)
        if persist:state.persist([REG],'chore: admit owned writer draft hashes [skip ci]')
    print('INTAKE: owned draft hashes verified')

if __name__=='__main__':run()
