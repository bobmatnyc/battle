"""Frozen poc-1 transitions for save/replay compatibility. Do not evolve these rules."""
from copy import deepcopy
from . import grid
from .scenario import SIDES

class InvalidOrder(ValueError):
    pass

def emit(s, kind, **data):
    e={'seq':len(s['events'])+1,'turn':s['turn'],'kind':kind,**data}
    s['events'].append(e)
    return e

def message(s, side, text, observed=None, kind='dispatch'):
    s['dispatches'][side].append({'turn':s['turn'],'observed_turn':s['turn'] if observed is None else observed,
                                'text':text,'kind':kind})

def find_unit(s,uid):
    return next((u for u in s['units'] if u['id']==uid),None)

def validate_order(s,side,order):
    if not isinstance(order,dict) or set(order)-{'unit_id','destination','stance'}:
        raise InvalidOrder('Order must contain unit_id, destination and stance only.')
    u=find_unit(s,order.get('unit_id'))
    if not u or u['side'] != side:
        raise InvalidOrder('That unit is outside your command.')
    # Use delivered friendly knowledge, avoiding a hidden-state rejection oracle.
    report=s['friendly_reports'][side].get(u['id'],{})
    if report.get('status') in ('routed','lost'):
        raise InvalidOrder('That unit is reported unable to accept orders.')
    if order.get('stance') not in ('move','hold'):
        raise InvalidOrder('Choose move or hold.')
    if order['stance']=='move' and not grid.valid(order.get('destination')):
        raise InvalidOrder('Choose a hex inside the battlefield.')
    if order['stance']=='hold' and order.get('destination') is not None:
        raise InvalidOrder('Hold orders have no destination.')
    return u

def issue(s,side,order,source='human'):
    u=validate_order(s,side,order)
    version=max([o['version'] for o in s['orders'] if o['unit_id']==u['id']]+[u['order_version']])+1
    known=s['friendly_reports'][side][u['id']]['pos']
    delay=1+grid.distance(s['hq'][side],known)//8
    oid=f'O{len(s["orders"])+1}'
    item={'id':oid,'side':side,**deepcopy(order),'source':source,'version':version,
          'sent_turn':s['turn'],'arrival_turn':s['turn']+delay,'status':'en_route'}
    s['orders'].append(item)
    emit(s,'order_sent',order_id=oid,side=side,unit_id=u['id'],destination=order.get('destination'),version=version,arrival_turn=item['arrival_turn'])
    message(s,side,f'{u["id"]}: {order["stance"]} order dispatched by runner. Expected delivery in {delay*30} seconds.',kind='order')
    return item

def summary(u):
    return {k:deepcopy(u[k]) for k in ('id','side','name','pos','initial','strength','ammo','morale','suppression','fatigue','status','target','stance','order_version')}

def enqueue(s, side, text, data=None, kind='dispatch', delay=1):
    s['reports'].append({'side':side,'text':text,'data':data,'kind':kind,
                         'observed_turn':s['turn'],'arrival_turn':s['turn']+delay})
    emit(s,'report_sent',side=side,report_kind=kind,arrival_turn=s['turn']+delay)

def deliver_reports(s):
    pending=[]
    for report in s['reports']:
        if report['arrival_turn']>s['turn']:
            pending.append(report); continue
        side=report['side']; data=report['data']
        if report['kind']=='friendly':
            s['friendly_reports'][side][data['id']]={**data,'observed_turn':report['observed_turn'],'received_turn':s['turn']}
        elif report['kind']=='contact':
            s['contacts'][side][data['id']]={**data,'observed_turn':report['observed_turn'],'received_turn':s['turn']}
        if report['text']:
            message(s,side,report['text'],report['observed_turn'],report['kind'])
        emit(s,'report_received',side=side,report_kind=report['kind'],observed_turn=report['observed_turn'])
    s['reports']=pending

def advance(s):
    """Mutates only supplied state; all fire uses the same pre-damage snapshot."""
    if s['status']!='active':
        raise ValueError('This battle has ended. Start a new battle.')
    s['turn']+=1
    deliver_reports(s)
    for o in s['orders']:
        if o['status']!='en_route' or o['arrival_turn']>s['turn']:
            continue
        u=find_unit(s,o['unit_id'])
        if o['version']<=u['order_version']:
            o['status']='superseded'
        elif u['status'] in ('routed','lost'):
            o['status']='refused'
        else:
            o['status']='delivered'; u['order_version']=o['version']
            u['target']=deepcopy(o.get('destination')); u['stance']=o['stance']
        emit(s,'order_'+o['status'],order_id=o['id'],unit_id=u['id'],version=o['version'])
        enqueue(s,o['side'],f'{u["id"]}: order {o["id"]} {o["status"]}.',kind='ack')
    # Compute all movement proposals from a shared pre-movement state.
    moves=[]
    occupied={grid.key(u['pos']):u for u in s['units'] if u['strength']>0}
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0: continue
        u['suppression']=max(0,u['suppression']-8)
        if u['status']=='routed': u['target']=s['hq'][u['side']]
        if u['target'] is not None and u['pos']!=u['target']:
            u['move_credit']=min(400,u['move_credit']+max(45,115-u['fatigue']//3-u['suppression']//2))
            route=grid.path(s['cells'],u['pos'],u['target'],blocked=occupied)
            if route:
                nxt=route[0]; cost=grid.cost(s['cells'],u['pos'],nxt)
                if u['move_credit']>=cost:
                    moves.append((u,nxt,cost))
        else:
            u['fatigue']=max(0,u['fatigue']-2)
            if u['status']!='routed': u['morale']=min(90,u['morale']+1)
    # A conservative occupancy rule: no swaps or stacking; collisions wait.
    counts={grid.key(p):sum(p==other[1] for other in moves) for _,p,_ in moves}
    for u,p,cost in moves:
        if grid.key(p) in occupied or counts[grid.key(p)]>1:
            emit(s,'movement_blocked',unit_id=u['id'],destination=p); continue
        old=u['pos']; u['pos']=p; u['move_credit']-=cost; u['fatigue']=min(100,u['fatigue']+3)
        emit(s,'unit_moved',unit_id=u['id'],origin=old,destination=p)
        if p==u['target']:
            u['target']=None; u['stance']='hold'
            enqueue(s,u['side'],f'{u["id"]}: reached assigned position.',kind='movement')
    damage={u['id']:0 for u in s['units']}; suppression={u['id']:0 for u in s['units']}
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0 or u['ammo']<=0 or u['status']=='routed': continue
        enemies=[e for e in s['units'] if e['side']!=u['side'] and e['strength']>0
                 and grid.distance(u['pos'],e['pos'])<=5 and grid.visible(s['cells'],u['pos'],e['pos'])]
        if not enemies: continue
        target=min(enemies,key=lambda e:(grid.distance(u['pos'],e['pos']),e['id']))
        d=grid.distance(u['pos'],target['pos']); cover=s['cells'][grid.key(target['pos'])]['cover']
        rounds=min(u['ammo'],u['strength']); u['ammo']-=rounds
        # Integer exposure accumulation; synthetic POC coefficient, not historical ballistics.
        effect=rounds*(8-d)*(100-cover)*(100-u['suppression']//2)//9000
        effect=max(1,effect)
        damage[target['id']]+=effect
        suppression[target['id']]+=max(2,rounds//4)
        emit(s,'volley',unit_id=u['id'],target_id=target['id'],rounds=rounds,exposure=effect)
    for u in s['units']:
        old=u['strength']; u['loss_credit']+=damage[u['id']]
        losses=min(old,u['loss_credit']//100); u['loss_credit']%=100
        u['strength']-=losses
        u['suppression']=min(100,u['suppression']+suppression[u['id']])
        u['morale']=max(0,u['morale']-losses*4-(2 if u['suppression']>65 else 0))
        if losses: emit(s,'casualties',unit_id=u['id'],count=losses,remaining=u['strength'])
        if u['strength']==0: u['status']='lost'
        elif (u['morale']<28 or u['strength']<12) and u['status']!='routed':
            u['status']='routed'; emit(s,'unit_routed',unit_id=u['id'])
            enqueue(s,u['side'],f'{u["id"]}: formation breaking; withdrawing toward headquarters.',kind='morale')
    # Local sensors produce reports; HQ and agents only receive them next turn.
    for side in SIDES:
        friends=[u for u in s['units'] if u['side']==side]
        for u in friends:
            enqueue(s,side,None,summary(u),kind='friendly')
        for e in s['units']:
            if e['side']==side or e['strength']==0: continue
            if any(u['strength']>0 and grid.visible(s['cells'],u['pos'],e['pos']) for u in friends):
                known=s['contacts'][side].get(e['id'])
                first=not known
                contact={'id':e['id'],'pos':deepcopy(e['pos']),'side':e['side'],
                         'estimate':'platoon-sized formation','status':'observed'}
                enqueue(s,side,f'Enemy formation reported near hex {e["pos"][0]},{e["pos"][1]}.' if first else None,contact,kind='contact')
    defenders=[u for u in s['units'] if u['status'] not in ('routed','lost') and grid.distance(u['pos'],s['objective'])<=1]
    occupied_sides={u['side'] for u in defenders}
    s['capture']=s['capture']+1 if occupied_sides=={'confederate'} else 0
    active={side:any(u['side']==side and u['status'] not in ('routed','lost') for u in s['units']) for side in SIDES}
    winner=None; reason=None
    if not any(active.values()): winner='draw'; reason='Both commands lost combat effectiveness.'
    elif not active['union']: winner='confederate'; reason='Union formations can no longer hold the position.'
    elif not active['confederate']: winner='union'; reason='The attacking formations have broken.'
    elif s['capture']>=3: winner='confederate'; reason='The attackers held the summit uncontested for 90 seconds.'
    elif s['turn']>=s['max_turns']: winner='union'; reason='The Union held out until the scenario deadline.'
    if winner:
        s['status']='complete'; s['winner']=winner; s['reason']=reason
        emit(s,'battle_ended',winner=winner,reason=reason)
        for side in SIDES: message(s,side,reason,kind='outcome')
    emit(s,'turn_completed',turn_number=s['turn'])
    return s

def view(s,side='union'):
    units=[deepcopy(u) for u in s['friendly_reports'][side].values()]
    contacts=[dict(deepcopy(c),age=s['turn']-c['observed_turn']) for c in s['contacts'][side].values()
              if s['turn']-c['observed_turn']<=6]
    # Do not disclose delivery before an acknowledgement reaches HQ.
    orders=[]
    for o in s['orders']:
        if o['side']!=side: continue
        orders.append({k:deepcopy(v) for k,v in o.items() if k!='status'} | {
            'status':'awaiting_ack' if s['turn']<=o['arrival_turn'] else o['status']})
    return {'turn':s['turn'],'revision':s['revision'],'status':s['status'],'winner':s['winner'],
            'reason':s['reason'],'objective':s['objective'],'max_turns':s['max_turns'],
            'seconds_per_turn':s['seconds_per_turn'],'units':units,'contacts':contacts,
            'orders':orders,'dispatches':deepcopy(s['dispatches'][side][-60:]),'side':side,
            'weather':s['weather'],'hq':s['hq'][side]}
