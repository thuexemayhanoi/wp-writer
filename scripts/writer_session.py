"""Provider-neutral W1/W2/W3 with CAS, immutable submission receipts."""
import argparse
import datetime as dt
import json
import re
from common import ROOT, digest, git, load, now, save, topics
from git_state import RemoteState

REG='data/state/writer-claims.json'

def live_leases(registry, epoch=None):
    at=epoch or dt.datetime.now(dt.timezone.utc)
    active={k:v for k,v in registry.get('leases',{}).items() if dt.datetime.fromisoformat(v['expires_at'])>at}
    ids=[]; sessions=[]
    for slot,v in active.items():
        if slot not in ('W1','W2','W3'):raise ValueError('Unknown slot')
        ids.extend(v['topic_ids']);sessions.append(v['session'])
    if len(ids)!=len(set(ids)) or len(sessions)!=len(set(sessions)):raise ValueError('Ambiguous live lease registry')
    return active

def claim(registry, rows, session, slot='auto', count=2, epoch=None, requested_ids=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{3,79}',session):raise ValueError('Use a stable public session label, never a credential')
    if not 1<=count<=10:raise ValueError('Lease size 1..10')
    at=epoch or dt.datetime.now(dt.timezone.utc);active=live_leases(registry,at)
    mine=[(k,v) for k,v in active.items() if v['session']==session]
    if mine:
        if slot!='auto' and mine[0][0]!=slot:raise ValueError('Session already owns another slot')
        return mine[0][0],registry
    if slot=='auto':slot=next((s for s in ('W1','W2','W3') if s not in active),None)
    if not slot or slot in active:raise ValueError('Slot has a valid lease')
    used={i for v in active.values() for i in v['topic_ids']}
    submitted=registry.get('submissions',{})
    repairs=[t['topic_id'] for t in rows if t['topic_id'] not in used and not t.get('wp_post_id') and submitted.get(t['topic_id'],{}).get('session')==session]
    eligible=repairs+[t['topic_id'] for t in rows if t['topic_qa_status']=='PLANNED' and t['topic_id'] not in used and t['topic_id'] not in submitted and not t.get('wp_post_id')]
    if requested_ids:
        if len(requested_ids)!=len(set(requested_ids)) or not set(requested_ids)<=set(eligible):raise ValueError('Requested topics not claimable')
        if repairs and not set(repairs)<=set(requested_ids):raise ValueError('Resume owned REPAIR before new IDs')
        eligible=[i for i in eligible if i in requested_ids]
    if not eligible:raise ValueError('No claimable PLANNED topic; research candidates first')
    active[slot]={'session':session,'topic_ids':eligible[:count],'claimed_at':at.isoformat(),'expires_at':(at+dt.timedelta(hours=12)).isoformat()}
    registry['leases']=active
    return slot,registry

def owner(reg,session,topic_id):
    found=[(s,v) for s,v in live_leases(reg).items() if v['session']==session and topic_id in v['topic_ids']]
    if len(found)!=1:raise ValueError('No valid owned lease for '+topic_id)
    return found[0][0]

def remote_snapshot():
    git('fetch','origin','main');base=git('rev-parse','origin/main')
    reg=json.loads(git('show',base+':'+REG));rows=[json.loads(x) for x in git('show',base+':data/topics.jsonl').splitlines() if x]
    return base,reg,rows

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['begin','status','heartbeat','release','check','push','confirm']);p.add_argument('--session',required=True);p.add_argument('--slot',default='auto',choices=['auto','W1','W2','W3']);p.add_argument('--count',type=int,default=2);p.add_argument('--ids',default='');a=p.parse_args()
    for attempt in range(4):
        base,reg,rows=remote_snapshot()
        if a.action in ('status','confirm'):
            print(json.dumps({'leases':reg.get('leases',{}),'submissions':reg.get('submissions',{}),'ledger':json.loads(git('show',base+':data/state/publication-ledger.json'))},ensure_ascii=False));return
        paths=[REG];files={};ids=[x for x in a.ids.split(',') if x]
        if a.action=='begin':
            ledger=json.loads(git('show',base+':data/state/publication-ledger.json'))
            completed={k for k,v in ledger['posts'].items() if v.get('phase')=='VERIFIED'}
            rows=[{**t,'wp_post_id':ledger['posts'][t['topic_id']].get('wp_id')} if t['topic_id'] in completed else t for t in rows]
            # Terminal receipt releases the slot, but immutable submission history stays.
            for s,v in list(reg.get('leases',{}).items()):
                if v['session']==a.session:
                    v['topic_ids']=[i for i in v['topic_ids'] if i not in completed]
                    if not v['topic_ids']:del reg['leases'][s]
            slot,reg=claim(reg,rows,a.session,a.slot,a.count)
        elif a.action in ('heartbeat','release'):
            matches=[(s,v) for s,v in live_leases(reg).items() if v['session']==a.session]
            if len(matches)!=1:raise ValueError('No owned live slot')
            slot,lease=matches[0]
            if a.action=='release':
                ledger=json.loads(git('show',base+':data/state/publication-ledger.json'))
                pending=[i for i in lease['topic_ids'] if i in reg.get('submissions',{}) and ledger['posts'].get(i,{}).get('phase')!='VERIFIED']
                if pending:raise ValueError('Submitted drafts still queued; release after terminal receipt')
                del reg['leases'][slot]
            else:lease['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=12)).isoformat()
        else:
            if not ids:raise ValueError('--ids required')
            from qa import evaluate,read_article
            for topic_id in ids:
                slot=owner(reg,a.session,topic_id)
                path='posts/drafts/'+topic_id+'.md';meta,body,sha=read_article(ROOT/path)
                if meta.get('writer_session')!=a.session or meta.get('writer_slot')!=slot:raise ValueError('Draft owner metadata mismatch')
                t=next(t for t in rows if t['topic_id']==topic_id)
                result=evaluate(ROOT/path,t,rows=rows,check_claim=False)
                if result['status']!='PASS':raise ValueError(json.dumps(result,ensure_ascii=False))
                files[path]=(ROOT/path).read_bytes();paths.append(path)
                reg.setdefault('submissions',{})[topic_id]={'sha256':sha,'session':a.session,'slot':slot,'submitted_at':now(),'lease_expires_at':reg['leases'][slot]['expires_at']}
            if a.action=='check':print('QA PASS');return
        # Snapshot expected blobs from freshly fetched base, never from a stale local branch.
        state=RemoteState()
        import subprocess
        for path in paths:
            r=subprocess.run(['git','rev-parse',base+':'+path],cwd=ROOT,text=True,capture_output=True)
            state.expected[path]=r.stdout.strip() if r.returncode==0 else None
        save(REG,reg)
        try:
            commit=state.persist(paths,'content: '+a.action+' '+a.session)
            print(json.dumps({'commit':commit,'session':a.session,'leases':reg['leases']}));return
        except RuntimeError:
            if attempt==3:raise
    raise RuntimeError('CAS exhausted')

if __name__=='__main__': main()
