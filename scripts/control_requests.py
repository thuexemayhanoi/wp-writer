"""GitHub-only AI can push a JSON request; Actions claims with no WP secrets."""
import datetime as dt
import copy
import json
import os
import re
import subprocess
from common import ROOT,digest,load,now,save,topics

def changed_request_paths():
    """On push, inspect only request files changed by this precise GitHub event.

    An old BLOCKED request must not fail another writer's later valid push.
    Manual dispatch remains a full diagnostic scan of outstanding requests.
    """
    if os.environ.get('GITHUB_EVENT_NAME')!='push':
        return None
    event_path=os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        raise ValueError('Push event payload missing; cannot safely scope writer requests')
    with open(event_path,encoding='utf-8') as f:
        payload=json.load(f)
    before=payload.get('before','')
    after=payload.get('after','')
    if not all(re.fullmatch('[0-9a-f]{40}',v or '') and v != '0'*40 for v in (before,after)):
        raise ValueError('Push before/after SHAs unavailable for request scope')
    git_run=subprocess.run(['git','diff','--name-only',before,after,'--','data/writer-requests/'],
                          cwd=ROOT,text=True,capture_output=True)
    if git_run.returncode:
        raise RuntimeError('Cannot diff exact pushed writer requests; fail closed')
    return {line.strip() for line in git_run.stdout.splitlines()
            if re.fullmatch(r'data/writer-requests/[A-Za-z0-9_-]+\.json',line.strip())}
from git_state import RemoteState
from writer_session import claim,live_leases,writer_finished,REG

def run(selected_paths=None):
    if selected_paths is None:
        selected_paths=changed_request_paths()
    reg=load(REG);state=RemoteState();state.remember([REG]);rows=topics();changed=False
    blocked=[]
    ledger=load('data/state/publication-ledger.json',{'posts':{}})
    verified={k for k,v in ledger['posts'].items() if v.get('phase')=='VERIFIED'}
    completed=verified|{i for i in reg.get('submissions',{}) if writer_finished(i,reg,ledger,rows)}
    rows=[{**t,'wp_post_id':ledger['posts'][t['topic_id']].get('wp_id')} if t['topic_id'] in verified else t for t in rows]
    for path in sorted((ROOT/'data/writer-requests').glob('*.json')):
        if selected_paths is not None and path.relative_to(ROOT).as_posix() not in selected_paths:
            continue
        raw=path.read_bytes();h=digest(raw);r=json.loads(raw);session=r.get('session','')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{3,79}',session) or path.stem!=session:raise ValueError('Request filename/session invalid')
        previous=reg.get('processed_requests',{}).get(session,{})
        if previous.get('sha256')==h:
            if previous.get('status')=='BLOCKED':blocked.append(session)
            continue
        # A rejected operation must not partially change existing leases.
        candidate=copy.deepcopy(reg)
        action=r.get('action');result={}
        try:
            mine=[(s,v) for s,v in live_leases(candidate).items() if v['session']==session]
            if action=='begin':
                for s,v in mine:
                    v['topic_ids']=[i for i in v['topic_ids'] if i not in completed]
                    if not v['topic_ids']:del candidate['leases'][s]
                slot,candidate=claim(candidate,rows,session,r.get('slot','auto'),int(r.get('count',2)),requested_ids=r.get('topic_ids'),completed_ids=completed)
                result={'status':'CLAIMED','slot':slot,'topic_ids':candidate['leases'][slot]['topic_ids']}
            elif action=='heartbeat':
                if len(mine)!=1:raise ValueError('No owned live slot')
                mine[0][1]['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=12)).isoformat();result={'status':'RENEWED'}
            elif action=='release':
                if len(mine)!=1:raise ValueError('No owned live slot')
                if any(i in reg.get('submissions',{}) and i not in completed for i in mine[0][1]['topic_ids']):raise ValueError('Pending submission needs QA PASS before release')
                del candidate['leases'][mine[0][0]];result={'status':'RELEASED'}
            else:raise ValueError('Unknown request action')
        except ValueError as e:
            result={'status':'BLOCKED','reason':str(e)}
            blocked.append(session)
        else:
            reg=candidate
        reg.setdefault('processed_requests',{})[session]={'sha256':h,'request_id':r.get('request_id'),'at':now(),**result};changed=True
    if changed:
        save(REG,reg);state.persist([REG],'chore: process universal writer requests [skip ci]')
    print(json.dumps(reg.get('processed_requests',{}),ensure_ascii=False))
    if blocked:
        raise SystemExit('BLOCKED: '+', '.join(sorted(set(blocked)))+'; inspect processed_requests reasons')

if __name__=='__main__':run()
