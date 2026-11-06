"""Pure deterministic state transitions. Models never adjudicate effects."""
from copy import deepcopy
from . import grid,recon,tactics,comms
from .scenario import SIDES

from .engine_v2 import InvalidOrder

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
    if s.get('rules')!='poc-3':
        from .engine_v2 import validate_order as legacy_validate
        return legacy_validate(s,side,order)
    if not comms.operational(s,side):
        raise InvalidOrder('Command detachment is disrupted; subordinates continue under standing orders.')
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
    if s.get('rules')!='poc-3':
        from .engine_v2 import issue as legacy_issue
        return legacy_issue(s,side,order,source)
    u=validate_order(s,side,order)
    commander=comms.command_unit(s,side)
    version=max([o['version'] for o in s['orders'] if o['unit_id']==u['id']]+[u['order_version']])+1
    known=s['friendly_reports'][side][u['id']]['pos']
    method='voice' if u['id']==commander['id'] else 'courier'
    packet=comms.envelope(s,commander['pos'],u['id'],known,method)
    delay=packet['expected_turn']-s['turn']
    oid=f'O{len(s["orders"])+1}'
    packet['id']=oid
    item={'id':oid,'side':side,**deepcopy(order),'source':source,'version':version,
          'sent_turn':s['turn'],'arrival_turn':s['turn']+delay,'status':'en_route','transport':packet}
    s['orders'].append(item)
    emit(s,'order_sent',order_id=oid,side=side,unit_id=u['id'],destination=order.get('destination'),version=version,arrival_turn=item['arrival_turn'],transport=deepcopy(packet))
    message(s,side,f'{u["id"]}: {order["stance"]} order dispatched by {"voice" if method=="voice" else "runner"}. Expected delivery in {delay*30} seconds.',kind='order')
    return item

def summary(u):
    result={k:deepcopy(u[k]) for k in ('id','side','name','pos','initial','strength','ammo','morale','suppression','fatigue','status','target','stance','order_version')}
    result.update({k:deepcopy(u[k]) for k in ('recon_role','recon_skill','local_action','local_reason','tactical_target') if k in u})
    return result

def enqueue(s, side, text, data=None, kind='dispatch', delay=1, sender=None):
    if s.get('rules')!='poc-3':
        from .engine_v2 import enqueue as legacy_enqueue
        return legacy_enqueue(s,side,text,data,kind,delay)
    commander=comms.command_unit(s,side)
    sender_id=sender or (data or {}).get('observer_id') or (data or {}).get('id')
    origin=next((u for u in s['units']+s.get('intel_assets',[]) if u['id']==sender_id),None)
    if not origin or not commander:raise ValueError('Reports need a physical sender and command recipient.')
    if origin.get('strength',1)<=0:return  # No ghost reports from destroyed formations.
    method='voice' if sender_id==commander['id'] else 'courier'
    packet=comms.envelope(s,origin['pos'],commander['id'],commander['pos'],method,handling=max(0,delay-1))
    packet['id']=f'R{len(s["events"])+1}'
    # The commander directly observes their own detachment, within this interval.
    if method=='voice':packet.update(ready_turn=s['turn'],last_progress_turn=s['turn']-1,expected_turn=s['turn'])
    report={'side':side,'text':text,'data':data,'kind':kind,'observed_turn':s['turn'],
            'arrival_turn':packet['expected_turn'],'transport':packet}
    s['reports'].append(report)
    emit(s,'report_sent',report_id=packet['id'],side=side,report_kind=kind,arrival_turn=report['arrival_turn'],transport=deepcopy(packet))

def deliver_reports(s):
    if s.get('rules')!='poc-3':
        from .engine_v2 import deliver_reports as legacy_deliver
        return legacy_deliver(s)
    pending=[]
    for report in s['reports']:
        transport_status=comms.progress(s,report['transport'],emit)
        if transport_status=='en_route':
            pending.append(report); continue
        if transport_status=='expired':continue
        if not comms.operational(s,report['side']):
            emit(s,'report_undeliverable',report_id=report['transport']['id'],side=report['side'],report_kind=report['kind'],reason='command_disrupted')
            continue
        side=report['side']; data=report['data']
        if report['kind']=='ack':
            s['acknowledgements'][side][data['order_id']]={'status':data['status'],'received_turn':s['turn']}
        if report['kind']=='friendly' and report['observed_turn']>=s['friendly_reports'][side].get(data['id'],{}).get('observed_turn',-1):
            s['friendly_reports'][side][data['id']]={**data,'observed_turn':report['observed_turn'],'received_turn':s['turn']}
        elif report['kind']=='contact':
            prior=s['contacts'][side].get(data['id'])
            merged,stale=recon.merge_contact(prior,data,report['observed_turn'],s['turn'])
            s['contacts'][side][data['id']]=merged
            if stale:
                emit(s,'report_merged',side=side,report_kind='contact',target_id=data['id'],observed_turn=report['observed_turn'],position_and_strength_preserved=True)
        if report['text']:
            message(s,side,report['text'],report['observed_turn'],report['kind'])
        emit(s,'report_received',report_id=report['transport']['id'],side=side,report_kind=report['kind'],observed_turn=report['observed_turn'])
    s['reports']=pending

def advance(s):
    """Mutates only supplied state; all fire uses the same pre-damage snapshot."""
    if s.get('rules')=='poc-1':
        from .engine_v1 import advance as legacy_advance
        return legacy_advance(s)
    if s.get('rules')=='poc-2':
        from .engine_v2 import advance as previous_advance
        return previous_advance(s)
    if s.get('rules')!='poc-3':raise ValueError('Unsupported battle rules version.')
    if s['status']!='active':
        raise ValueError('This battle has ended. Start a new battle.')
    s['turn']+=1
    comms.sync(s)
    deliver_reports(s)
    for o in s['orders']:
        if o['status']!='en_route':continue
        transport_status=comms.progress(s,o['transport'],emit)
        if transport_status=='en_route':continue
        if transport_status=='expired':
            o['status']='expired';emit(s,'order_expired',order_id=o['id']);continue
        u=find_unit(s,o['unit_id'])
        if o['version']<=u['order_version']:
            o['status']='superseded'
        elif u['status'] in ('routed','lost'):
            o['status']='refused'
        else:
            o['status']='delivered'; u['order_version']=o['version']
            u['target']=deepcopy(o.get('destination')); u['stance']=o['stance']
        emit(s,'order_'+o['status'],order_id=o['id'],unit_id=u['id'],version=o['version'])
        enqueue(s,o['side'],f'{u["id"]}: order {o["id"]} {o["status"]}.',data={'order_id':o['id'],'status':o['status']},kind='ack',sender=u['id'])
    local_sightings=recon.scan(s)
    for contacts in local_sightings.values():
        for contact in contacts:contact['phase']='1_before_actions'
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0:continue
        decision=tactics.decide(s,u,local_sightings.get(u['id'],[]))
        changed=(u.get('local_action'),u.get('local_reason'))!=(decision['action'],decision['reason'])
        if decision['action']=='withdraw' and u.get('local_action')!='withdraw':u['withdraw_until']=s['turn']+3
        u.update(local_action=decision['action'],local_reason=decision['reason'],tactical_target=decision['target'])
        event=emit(s,'local_decision',unit_id=u['id'],**decision)
        u['local_decision_seq']=event['seq']
        if changed and (decision['contacts'] or decision['under_fire']):
            enqueue(s,u['side'],f'{u["id"]} to headquarters: {decision["reason"]}',kind='reaction',sender=u['id'])
    # Compute all movement proposals from a shared pre-movement state.
    moves=[]
    occupied={grid.key(u['pos']):u for u in s['units'] if u['strength']>0}
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0: continue
        u['suppression']=max(0,u['suppression']-8)
        if u['status']=='routed': u['target']=s['rally_points'][u['side']]
        move_target=(u['target'] if u['local_action'] in ('continue','route') else u.get('tactical_target'))
        if move_target is not None and u['pos']!=move_target:
            u['move_credit']=min(400,u['move_credit']+max(45,115-u['fatigue']//3-u['suppression']//2))
            route=grid.path(s['cells'],u['pos'],move_target,blocked=occupied)
            if route:
                nxt=route[0]; cost=grid.cost(s['cells'],u['pos'],nxt)
                if u['move_credit']>=cost:
                    moves.append((u,nxt,cost))
        elif u['local_action'] in ('hold','observe') and s['turn']-u.get('last_attacked_turn',-99)>1:
            u['fatigue']=max(0,u['fatigue']-2)
            if u['status']!='routed': u['morale']=min(90,u['morale']+1)
    # A conservative occupancy rule: no swaps or stacking; collisions wait.
    counts={grid.key(p):sum(p==other[1] for other in moves) for _,p,_ in moves}
    for u,p,cost in moves:
        if grid.key(p) in occupied or counts[grid.key(p)]>1:
            emit(s,'movement_blocked',unit_id=u['id'],destination=p); continue
        old=u['pos']; u['pos']=p; u['move_credit']-=cost; u['fatigue']=min(100,u['fatigue']+3)
        emit(s,'unit_moved',unit_id=u['id'],origin=old,destination=p,decision_seq=u['local_decision_seq'])
        if p==u['target']:
            u['target']=None; u['stance']='hold'
            enqueue(s,u['side'],f'{u["id"]}: reached assigned position.',kind='movement',sender=u['id'])
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
        if suppression[u['id']]>0:
            u['last_attacked_turn']=s['turn']
            emit(s,'unit_under_fire',unit_id=u['id'])
        old=u['strength']; u['loss_credit']+=damage[u['id']]
        losses=min(old,u['loss_credit']//100); u['loss_credit']%=100
        u['strength']-=losses
        u['suppression']=min(100,u['suppression']+suppression[u['id']])
        u['morale']=max(0,u['morale']-losses*4-(2 if u['suppression']>65 else 0))
        if losses: emit(s,'casualties',unit_id=u['id'],count=losses,remaining=u['strength'])
        if u['strength']==0: u['status']='lost'
        elif (u['morale']<28 or u['strength']<12) and u['status']!='routed':
            u['status']='routed'; emit(s,'unit_routed',unit_id=u['id'])
            enqueue(s,u['side'],f'{u["id"]}: formation breaking; withdrawing toward headquarters.',kind='morale',sender=u['id'])
    comms.sync(s)
    # Post-action observations update local evidence, but HQ must await delivery.
    sightings=recon.scan(s)
    for observer,contacts in sightings.items():
        for contact in contacts:contact['phase']='2_after_actions'
        # A fleeting contact still produces a report if it leaves sight during this interval.
        combined={c['id']:c for c in local_sightings.get(observer,[])}
        combined.update({c['id']:c for c in contacts})
        sightings[observer]=list(combined.values())
    for u in sorted(s['units'],key=lambda x:x['id']):
        enqueue(s,u['side'],None,summary(u),kind='friendly')
    outgoing=recon.reports(s,sightings)
    # Direct observations at the player's detachment cannot be displaced by a
    # better but distant scout's report, which still has to travel to command.
    outgoing=list(outgoing)
    chosen={(side,c['observer_id'],c['id']) for side,c in outgoing}
    for side in SIDES:
        commander=comms.command_unit(s,side)
        if commander:
            outgoing.extend((side,deepcopy(c)) for c in sightings.get(commander['id'],[])
                            if (side,commander['id'],c['id']) not in chosen)
    for side,contact in outgoing:
        known=s['contacts'][side].get(contact['id'])
        identified=any(value not in ('unidentified troops','not established') and value!=(known or {}).get('composition',{}).get(field) for field,value in contact['composition'].items())
        improved=not known or contact['confidence']!=known.get('confidence') or identified
        text=(f'General, enemy near map reference {contact["pos"][0]},{contact["pos"][1]}: '
              f'{contact["estimate"]}; {contact["confidence"]} confidence. '
              f'Report from {contact["observer_id"]} ({contact["observer_role"]}).') if improved else None
        emit(s,'contact_observed',side=side,contact=deepcopy(contact))
        delay=contact.pop('report_delay')
        enqueue(s,side,text,contact,kind='contact',delay=delay)
    deliver_reports(s)  # Local voice reports arrive now; couriers cannot move twice.
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
    if s.get('rules')!='poc-3':
        from .engine_v2 import view as legacy_view
        return legacy_view(s,side)
    units=[deepcopy(u) for u in s['friendly_reports'][side].values()]
    commander=comms.command_unit(s,side)
    if commander:
        units=[u for u in units if u['id']!=commander['id']]
        units.append(dict(summary(commander),observed_turn=s['turn'],received_turn=s['turn']))
        units.sort(key=lambda u:u['id'])
    contacts=[dict(deepcopy(c),age=s['turn']-c['observed_turn']) for c in s['contacts'][side].values()
              if s['turn']-c['observed_turn']<=6]
    # Do not disclose delivery before an acknowledgement reaches HQ.
    orders=[]
    for o in s['orders']:
        if o['side']!=side: continue
        orders.append({k:deepcopy(v) for k,v in o.items() if k not in ('status','transport')} | {
            'status':s['acknowledgements'][side].get(o['id'],{}).get('status','awaiting_ack')})
    return {'rules':s.get('rules','poc-1'),'turn':s['turn'],'revision':s['revision'],'status':s['status'],'winner':s['winner'],
            'reason':s['reason'],'objective':s['objective'],'max_turns':s['max_turns'],
            'seconds_per_turn':s['seconds_per_turn'],'units':units,'contacts':contacts,
            'orders':orders,'dispatches':deepcopy(s['dispatches'][side][-60:]),'side':side,
            'weather':deepcopy(s['weather']),'hq':list(commander['pos']) if commander else s['hq'][side],
            'command':comms.location(s,side)}


def god_view(s):
    """Explicit local debug observer. Never use this as an agent observation."""
    result=view(s)
    result.update(view_mode='god',units=[dict(deepcopy(u),observed_turn=s['turn'],received_turn=s['turn']) for u in s['units']],
                  contacts=[],orders=deepcopy(s['orders']),reports=deepcopy(s['reports']),
                  events=deepcopy(s['events']),decisions=deepcopy(s['decisions']),
                  headquarters=deepcopy(s['hq']),
                  commands={side:comms.location(s,side) for side in SIDES} if s.get('rules')=='poc-3' else {},
                  dispatches=[dict(deepcopy(d),side=side) for side in SIDES for d in s['dispatches'][side]])
    return result
