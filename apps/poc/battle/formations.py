"""Bounded aggregate reorganization; authored POC rules, no individual roster."""
from copy import deepcopy
from . import grid,comms

MIN_STRENGTH=12
MAX_STRENGTH=80
SETUP_TURNS=2
PROFILE=('unit_type','weapon_class','skill','recon_role','recon_skill')

def compatible(a,b):
    return all(a.get(k)==b.get(k) for k in PROFILE)

def validate(s,side,request):
    from . import engine
    if s.get('rules') not in ('poc-8','poc-9','poc-10'):raise ValueError('Use Reset to start a battle with split/combine rules.')
    if not isinstance(request,dict):raise ValueError('Expected a formation instruction.')
    kind=request.get('kind');allowed={'kind','unit_id','count','destination'} if kind=='split' else {'kind','unit_id','partner_id'}
    if kind not in ('split','combine') or set(request)!=allowed:raise ValueError('Choose split or combine with its required fields.')
    ids=[request['unit_id']]+([request['partner_id']] if kind=='combine' else [])
    if len(set(ids))!=len(ids):raise ValueError('Choose two different formations.')
    known=engine.view(s,side);units={u['id']:u for u in known['units']}
    for uid in ids:
        engine.validate_order(s,side,{'unit_id':uid,'stance':'hold','destination':None})
        if uid not in units:raise ValueError('That formation has not reported to headquarters.')
    a=units[ids[0]]
    if kind=='split':
        n=request['count'];p=request['destination']
        if type(n) is not int or n<MIN_STRENGTH or a['strength']-n<MIN_STRENGTH:
            raise ValueError('Each resulting formation needs at least 12 reported troops.')
        if not grid.valid(p) or grid.distance(a['pos'],p)!=1:raise ValueError('Select an adjacent hex for the detached formation.')
        if any(u['pos']==p and u['status'] not in ('lost','merged') for u in known['units']):raise ValueError('That hex is reported occupied by a friendly formation.')
    else:
        b=units[ids[1]]
        if not compatible(a,b):raise ValueError('Combine requires matching troops, weapons, proficiency and reconnaissance roles.')
        if grid.distance(a['pos'],b['pos'])!=1:raise ValueError('Move the formations into adjacent hexes before combining.')
        if a['strength']+b['strength']>MAX_STRENGTH:raise ValueError('Combined strength may not exceed 80 troops.')
        if b['id']==known['command']['unit_id']:raise ValueError('Select the headquarters unit as the surviving formation.')
    return ids

def request(s,side,instruction):
    from . import engine
    ids=validate(s,side,instruction)
    # Use the ordinary versioned command path for every affected commander.
    tickets=[engine.issue(s,side,{'unit_id':uid,'stance':'hold','destination':None},'formation') for uid in ids]
    op={**deepcopy(instruction),'id':f'F{len(s["formation_ops"])+1}','side':side,
        'order_ids':[o['id'] for o in tickets],'sent_turn':s['turn'],'status':'awaiting_orders','ready_turn':None}
    s['formation_ops'].append(op)
    engine.emit(s,'formation_requested',operation=deepcopy(op))
    engine.message(s,side,f'General, instructions to {op["kind"]} {", ".join(ids)} are dispatched. Regrouping requires sixty seconds after receipt.',kind='formation')
    return op

def observed(s,op):
    result={k:deepcopy(v) for k,v in op.items() if k not in ('status','ready_turn','reason','completed_turn')}
    result.update(s['formation_notices'].get(op['id'],{'status':'awaiting_report'}))
    return result

def receive(s,report):
    data=report['data'];side=report['side'];turn=report['observed_turn']
    s['formation_notices'][data['operation_id']]={'status':data['status'],'reason':data['reason'],
        'observed_turn':turn,'received_turn':s['turn']}
    for u in data['units']:
        prior=s['friendly_reports'][side].get(u['id'],{})
        if prior.get('observed_turn',-1)<=turn:
            s['friendly_reports'][side][u['id']]=dict(deepcopy(u),observed_turn=turn,received_turn=s['turn'])

def finish(s,op,status,reason,units):
    from . import engine
    op.update(status=status,reason=reason,completed_turn=s['turn'])
    engine.emit(s,'formation_'+status,operation_id=op['id'],reason=reason,unit_ids=[u['id'] for u in units])
    sender=next((u for u in units if u['strength']>0 and u['status']!='merged'),None)
    if sender:
        engine.enqueue(s,op['side'],f'{sender["id"]} to headquarters: {op["kind"]} {status}. {reason}',
            data={'operation_id':op['id'],'status':status,'reason':reason,'units':[engine.summary(u) for u in units]},
            kind='formation',sender=sender['id'])

def obstruction(s,units):
    for u in units:
        if u['status'] in ('lost','routed','merged') or u['strength']<MIN_STRENGTH:return 'A formation is no longer fit to reorganize.'
        if u['suppression']>20 or s['turn']-u.get('last_attacked_turn',-99)<=2:return 'Incoming fire prevents regrouping.'
        if u.get('withdraw_until',0)>s['turn']:return 'A withdrawal is still in progress.'
        if any(e['side']!=u['side'] and e['strength']>0 and grid.distance(u['pos'],e['pos'])<=5
               and grid.visible(s['cells'],u['pos'],e['pos']) for e in s['units']):return 'Enemy contact prevents regrouping.'
    return None

def progress(s):
    from . import engine
    for op in s['formation_ops']:
        if op['status'] in ('completed','refused'):continue
        orders=[next(o for o in s['orders'] if o['id']==oid) for oid in op['order_ids']]
        units=[engine.find_unit(s,o['unit_id']) for o in orders]
        if any(o['status'] in ('expired','refused','superseded') or u['order_version']>o['version'] for o,u in zip(orders,units)):
            finish(s,op,'refused','The instructions expired, were refused, or were superseded.',units);continue
        if any(o['status']!='delivered' for o in orders):continue
        reason=obstruction(s,units)
        if reason:finish(s,op,'refused',reason,units);continue
        if op['ready_turn'] is None:
            op.update(status='regrouping',ready_turn=s['turn']+SETUP_TURNS)
            engine.emit(s,'formation_regrouping',operation_id=op['id'],ready_turn=op['ready_turn'])
        if s['turn']<op['ready_turn']:continue
        a=units[0]
        if op['kind']=='split':
            n=op['count'];p=op['destination']
            if a['strength']-n<MIN_STRENGTH or grid.distance(a['pos'],p)!=1:
                finish(s,op,'refused','Strength or position changed before the split.',units);continue
            if any(u['strength']>0 and u['pos']==p for u in s['units']):
                finish(s,op,'refused','The detachment could not occupy the assigned hex.',units);continue
            before=deepcopy(a);child=deepcopy(a)
            # Identity uses the operation sequence, not current roster length.
            uid=f'{a["side"][0].upper()}D{op["id"][1:]}'
            child.update(id=uid,name=a['name']+' · detached',pos=list(p),strength=n,order_version=0,target=None,stance='hold',
                         local_action='hold',local_reason='Detachment formed; await orders.',tactical_target=None)
            child['standing_version']=0  # Inherit doctrine, start the new command scope at version zero.
            child.pop('mission_result',None);child.pop('supply_site',None)
            for field in ('initial','ammo','loss_credit','move_credit','tools'):
                child[field]=a[field]*n//a['strength'];a[field]-=child[field]
            a['strength']-=n
            s['units'].append(child)
            # Only the parent's own local evidence is inherited, never HQ/other-side truth.
            s['recon_memory'][uid]=deepcopy(s['recon_memory'].get(a['id'],{}))
            engine.emit(s,'unit_split',operation_id=op['id'],before=before,after=[deepcopy(a),deepcopy(child)])
            finish(s,op,'completed',f'{n} troops detached as {uid}; ammunition apportioned.',[a,child])
        else:
            b=units[1]
            if grid.distance(a['pos'],b['pos'])!=1 or not compatible(a,b) or a['strength']+b['strength']>MAX_STRENGTH:
                finish(s,op,'refused','Position, strength or compatibility changed before assembly.',units);continue
            before=[deepcopy(a),deepcopy(b)]
            for field in ('strength','initial','ammo','loss_credit','tools'):a[field]+=b[field]
            a['morale']=min(a['morale'],b['morale'])
            for field in ('suppression','fatigue','last_attacked_turn','withdraw_until'):a[field]=max(a[field],b[field])
            a['move_credit']=min(a['move_credit'],b['move_credit'])
            s['retired_units'].append(dict(deepcopy(b),retired_turn=s['turn'],merged_into=a['id']))
            b.update(strength=0,initial=0,ammo=0,tools=0,loss_credit=0,move_credit=0,status='merged',merged_into=a['id'],target=None)
            engine.emit(s,'units_combined',operation_id=op['id'],before=before,after=[deepcopy(a),deepcopy(b)])
            finish(s,op,'completed',f'{b["id"]} joined {a["id"]}; predecessor retired.',units)
