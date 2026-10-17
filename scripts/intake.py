"""Admit GitHub-only writer pushes using live lease and exact file hash."""
from common import ROOT,digest,load,now,save,topics
from git_state import RemoteState
from writer_session import owner,REG
from qa import read_article

def run(persist=True,strict=True):
    """Record receipts for valid drafts.

    strict=True (branch intake) raises on the first bad draft. strict=False (Publisher)
    quarantines a bad draft with a clear reason and still admits every valid one, so a
    single stray or edited draft can never stop all publishing. A quarantined draft gets
    no receipt, so it fails QA and is never published.
    """
    reg=load(REG);rows={t['topic_id']:t for t in topics()};changed=False;rejected=[]
    ledger=load('data/state/publication-ledger.json',{'posts':{}})
    state=RemoteState();state.remember([REG])
    for path in sorted((ROOT/'posts/drafts').glob('NT-*.md')):
        topic_id=path.stem
        try:
            meta,body,sha=read_article(path)
            old=reg.get('submissions',{}).get(topic_id,{})
            if old.get('sha256')==sha:continue
            if topic_id in ledger['posts']:raise ValueError('Cannot change uncertain/verified publication source')
            if topic_id not in rows or rows[topic_id]['topic_qa_status']!='PLANNED':raise ValueError('Unplanned topic push')
            slot=owner(reg,meta.get('writer_session'),topic_id)
            if meta.get('writer_slot')!=slot or meta.get('topic_id')!=topic_id:raise ValueError('Draft identity/slot mismatch')
        except ValueError as exc:
            if strict:raise
            rejected.append({'topic_id':topic_id,'reason':str(exc)});continue
        reg.setdefault('submissions',{})[topic_id]={'sha256':sha,'session':meta['writer_session'],'slot':slot,'submitted_at':now(),'lease_expires_at':reg['leases'][slot]['expires_at']}
        changed=True
    if changed:
        save(REG,reg)
        if persist:state.persist([REG],'chore: admit owned writer draft hashes [skip ci]')
    for item in rejected:
        print('INTAKE_REJECTED: '+item['topic_id']+': '+item['reason']+' (skipped; other drafts continue)')
    print('INTAKE: owned draft hashes verified'+(('; rejected '+str(len(rejected))) if rejected else ''))
    return rejected

if __name__=='__main__':run(strict=False)
