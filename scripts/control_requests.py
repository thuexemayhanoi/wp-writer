"""GitHub-only AI can push a JSON request; Actions claims with no WP secrets."""
import datetime as dt
import json
import re
from common import ROOT,digest,load,now,save,topics
from git_state import RemoteState
from writer_session import claim,live_leases,REG

def run():
    reg=load(REG);state=RemoteState();state.remember([REG]);rows=topics();changed=False
    ledger=load('data/state/publication-ledger.json',{'posts':{}})
    completed={k for k,v in ledger['posts'].items() if v.get('phase')=='VERIFIED'}
    rows=[{**t,'wp_post_id':ledger['posts'][t['topic_id']].get('wp_id')} if t['topic_id'] in completed else t for t in rows]
    for path in sorted((ROOT/'data/writer-requests').glob('*.json')):
        raw=path.read_bytes();h=digest(raw);r=json.loads(raw);session=r.get('session','')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{3,79}',session) or path.stem!=session:raise ValueError('Request filename/session invalid')
        if reg.get('processed_requests',{}).get(session,{}).get('sha256')==h:continue
        action=r.get('action');result={}
        try:
            mine=[(s,v) for s,v in live_leases(reg).items() if v['session']==session]
            if action=='begin':
                for s,v in mine:
                    v['topic_ids']=[i for i in v['topic_ids'] if i not in completed]
                    if not v['topic_ids']:del reg['leases'][s]
                slot,reg=claim(reg,rows,session,r.get('slot','auto'),int(r.get('count',2)),requested_ids=r.get('topic_ids'))
                result={'status':'CLAIMED','slot':slot,'topic_ids':reg['leases'][slot]['topic_ids']}
            elif action=='heartbeat':
                if len(mine)!=1:raise ValueError('No owned live slot')
                mine[0][1]['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=12)).isoformat();result={'status':'RENEWED'}
            elif action=='release':
                if len(mine)!=1:raise ValueError('No owned live slot')
                if any(i in reg.get('submissions',{}) and i not in completed for i in mine[0][1]['topic_ids']):raise ValueError('Pending submission: cannot release')
                del reg['leases'][mine[0][0]];result={'status':'RELEASED'}
            else:raise ValueError('Unknown request action')
        except ValueError as e:result={'status':'BLOCKED','reason':str(e)}
        reg.setdefault('processed_requests',{})[session]={'sha256':h,'request_id':r.get('request_id'),'at':now(),**result};changed=True
    if changed:
        save(REG,reg);state.persist([REG],'chore: process universal writer requests [skip ci]')
    print(json.dumps(reg.get('processed_requests',{}),ensure_ascii=False))

if __name__=='__main__':run()
