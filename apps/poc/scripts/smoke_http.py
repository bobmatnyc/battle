"""Offline HTTP integration check. Starts and cleans up an isolated server/database."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
base=f'http://127.0.0.1:{port}'

def request(path,body=None,headers=None,expected=200):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json',**(headers or {})})
    try:
        with urllib.request.urlopen(req,timeout=5) as response:status,raw=response.status,response.read()
    except urllib.error.HTTPError as exc:status,raw=exc.code,exc.read()
    assert status==expected,(path,status,expected)
    assert b'sk-or-' not in raw,'Secret appeared in a response'
    return json.loads(raw) if raw.startswith((b'{',b'[')) else raw

with tempfile.TemporaryDirectory() as tmp:
    proc=subprocess.Popen([sys.executable,'-m','battle','--offline','--port',str(port),'--db',str(Path(tmp)/'smoke.sqlite')],cwd=ROOT,stdout=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:state=request('/api/state');break
            except urllib.error.URLError:time.sleep(.05)
        else:raise RuntimeError('Server did not start')
        assert b'Little Round Top' in request('/')
        assert len(request('/api/map')['cells'])==504
        assert state['contacts']==[] and len(state['units'])==3
        assert all(u['side']=='union' for u in state['units'])
        assert state['command']['unit_id']=='U2' and state['command']['pos']==[13,15]
        assert state['analysis']['turn']==0 and state['analysis']['summary']['reported_strength']==120
        assert len(state['analysis']['units'])==3
        god=request('/api/state?view=god')
        assert len(god['units'])==6 and god['view_mode']=='god'
        assert 'events' in god and 'reports' in god and len(god['commands'])==2
        normal=request('/api/state')
        assert 'events' not in normal and 'reports' not in normal and len(normal['units'])==3
        assert normal['revision']==god['revision']
        request('/.env.local',expected=404)
        request('/../.env.local',expected=404)
        request('/api/export',expected=403)
        request('/api/state',headers={'Host':'attacker.invalid'},expected=403)
        request('/api/advance',{},headers={'Origin':'https://attacker.invalid'},expected=403)
        request('/api/advance',{'revision':-1,'game_id':state['game_id']},expected=409)
        common={'revision':state['revision'],'game_id':state['game_id']}
        state=request('/api/orders',{**common,'orders':[{'unit_id':'U1','stance':'move','destination':[12,13]}]})
        state=request('/api/advance',{'revision':state['revision'],'game_id':state['game_id']})
        assert state['turn']==1 and state['last_commander_source']=='scripted'
        state=request('/api/chat',{'revision':state['revision'],'game_id':state['game_id'],'text':'Status?'})
        assert len(state['messages'])==2 and state['messages'][-1]['source']=='scripted'
        assert request('/api/replay?revision=0')['turn']==0
        recorded=request('/api/replay?revision=0&view=god')
        assert len(recorded['units'])==6 and recorded['events']==[]
        god=request('/api/state?view=god')
        assert god['events'] and god['decisions']
        assert all(u['side']=='confederate' for u in god['decisions'][0]['observation']['units'])
        assert len(request('/api/history'))==4
        gid=state['game_id']
        assert state['clock']['running'] is False
        request('/api/clock',{'game_id':gid,'command':'speed','speed':60})
        request('/api/clock',{'game_id':gid,'command':'start'})
        request('/api/orders',{'game_id':gid,'revision':state['revision'],'orders':[]},expected=409)
        for _ in range(40):
            time.sleep(.05);state=request('/api/state')
            if state['turn']>=2:break
        assert state['turn']==2
        state=request('/api/clock',{'game_id':gid,'command':'pause'})
        assert not state['clock']['running'] and not state['clock']['inflight']
        saved=state['revision']
        request('/api/replay?game_id='+gid+'&revision=0')
        time.sleep(.6)
        assert request('/api/state')['revision']==saved
        request('/api/clock',{'game_id':gid,'command':'speed','speed':-1},expected=400)
        for bad in ('',0,[],{}):  # Only an absent or null scenario means the default.
            request('/api/new',{'game_id':gid,'revision':saved,'scenario':bad},expected=400)
        assert request('/api/state')['game_id']==gid
        state=request('/api/new',{'game_id':gid,'revision':saved})
        assert state['clock']['speed']==10 and not state['clock']['running']  # Reset restores default pacing.
        state=request('/api/formations',{'game_id':state['game_id'],'revision':state['revision'],
            'instruction':{'kind':'split','unit_id':'U2','count':20,'destination':[14,15]}})
        for _ in range(3):state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
        assert len(state['units'])==4 and state['formation_ops'][0]['status']=='completed'
        state=request('/api/formations',{'game_id':state['game_id'],'revision':state['revision'],
            'instruction':{'kind':'combine','unit_id':'U2','partner_id':'UD1'}})
        for _ in range(3):state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
        assert len(state['units'])==3 and state['formation_ops'][1]['status']=='completed'
        assert next(u for u in state['units'] if u['id']=='U2')['strength']==40
        assert next(u for u in state['units'] if u['id']=='U2')['ammo']==1600
        request('/api/formations',{'game_id':state['game_id'],'revision':state['revision'],
            'instruction':{'kind':'split','unit_id':'C1','count':20,'destination':[5,19]}},expected=400)
        assert [t['id'] for t in state['order_templates']]==['hold','move','rest','retreat','resupply','recon','dig_in']
        assert {f['kind'] for f in state['map_features']}=={'road','building','fortification'}
        assert len(state['supply_sites'])==1 and 'ammo' not in state['supply_sites'][0]
        for stance,dest in [('rest',None),('retreat',[13,15]),('recon',[13,15]),('resupply',None),('dig_in',None)]:
            state=request('/api/orders',{'game_id':state['game_id'],'revision':state['revision'],
                'orders':[{'unit_id':'U2','stance':stance,'destination':dest}]})
            state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
            assert next(u for u in state['units'] if u['id']=='U2')['mission_result']['template']==stance
        request('/api/orders',{'game_id':state['game_id'],'revision':state['revision'],
                'orders':[{'unit_id':'U2','stance':'invent_ammunition','destination':None}]},expected=400)
        state=request('/api/new',{'game_id':state['game_id'],'revision':state['revision']})
        for _ in range(2):state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
        rec=next(r for r in state['recommendations'] if r['unit_id']=='U2' and r['status']=='delivered')
        assert rec['proposal']['stance']=='dig_in'
        state=request('/api/recommendations',{'game_id':state['game_id'],'revision':state['revision'],
            'recommendation_id':rec['id'],'response':'accept'})
        assert next(r for r in state['recommendations'] if r['id']==rec['id'])['status']=='accepted'
        assert next(u for u in state['units'] if u['id']=='U2')['stance']=='hold'
        request('/api/recommendations',{'game_id':state['game_id'],'revision':state['revision'],
            'recommendation_id':rec['id'],'response':'accept'},expected=400)
        state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
        assert next(u for u in state['units'] if u['id']=='U2')['stance']=='dig_in'
        print('Recommendation HTTP smoke passed: receipt, explicit acceptance, duplicate rejection and normal order delivery.')
        print('Order template HTTP smoke passed: shared catalog, legal mission delivery, hidden stocks and invalid template rejection.')
        print('Formation HTTP smoke passed: delivered split/combine, resource conservation, retired unit removal and authority enforcement.')
        print('HTTP smoke passed: explicit God Mode, normal/model isolation, command unit, clock, immutable replay, map, movement, chat, stale revisions, secret/static boundaries.')
        state=request('/api/new',{'game_id':state['game_id'],'revision':state['revision']})
        before=request('/api/history')
        assert request('/api/state')['analysis']['turn']==0
        assert request('/api/state?view=god')['analysis']==state['analysis']
        assert request('/api/history')==before
        state=request('/api/standing-orders',{'game_id':state['game_id'],'revision':state['revision'],
            'instruction':{'unit_id':'U2','profile_id':'firm'}})
        assert state['turn']==0 and next(u for u in state['units'] if u['id']=='U2')['standing_profile']=='balanced'
        request('/api/standing-orders',{'game_id':state['game_id'],'revision':state['revision'],
            'instruction':{'unit_id':'C2','profile_id':'firm'}},expected=400)
        state=request('/api/advance',{'game_id':state['game_id'],'revision':state['revision']})
        assert next(u for u in state['analysis']['units'] if u['id']=='U2')['standing_profile']=='firm'
        assert state['standing_orders'][0]['status']=='delivered'
        assert request('/api/replay?revision=0')['analysis']['turn']==0
        print('Standing orders HTTP passed: read-only prebattle analysis, God knowledge boundary, authority, delivery and replay assessment.')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
