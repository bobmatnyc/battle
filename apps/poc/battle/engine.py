"""Pure deterministic state transitions. Models never adjudicate effects."""
from copy import deepcopy
from . import grid,recon,tactics,comms,formations,features,gates,recommendations,standing,victory
from . import orders as order_rules
from .scenario import SIDES
from .scenario_entry import LEGACY_ROLES

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

REFUSING_STATUSES=('routed','lost','merged')

def sides(s):
    """Side ids in scenario order: the snapshot's own from poc-9, else Union/Confederate.
    The order fixes event order, so it comes from a list, never from dict keys."""
    return tuple(x['id'] for x in s['sides']) if 'sides' in s else SIDES

def player_side(s):
    """The side the interactive player commands: the snapshot's from poc-9, else Union."""
    return s.get('player_side','union')

def computer_side(s):
    """Why: the clock-driven computer must command the side the player does not.
    What: the one side id other than ``player_side(s)``: Confederate before
    poc-9, the stored opponent from poc-9. Raises ValueError unless exactly
    one such side exists.
    Test: `test_clock_step_gives_renamed_opponent_the_computer_orders`,
    `test_poc8_game_still_commands_the_confederates`."""
    others=[side for side in sides(s) if side!=player_side(s)]
    if len(others)!=1:raise ValueError('The computer commands exactly one opposing side.')
    return others[0]

def role(s,side):
    """``defender`` or ``attacker``: the snapshot's own from poc-9, else the poc-8 roles."""
    if 'sides' not in s:return LEGACY_ROLES[side]
    return next(x['role'] for x in s['sides'] if x['id']==side)

def report_refusal(s,side,unit_id):
    """Why: commanders must see which units will refuse orders before choosing.
    What: the poc-8 reason headquarters' own knowledge bars orders to unit_id,
    or None: 'not_reported' without a delivered report, else 'reported_<status>'
    for a reported routed/lost/merged formation. Reads only delivered reports.
    Test: `test_observation_marks_reported_routed_unit_unable_to_accept_orders`."""
    report=s['friendly_reports'][side].get(unit_id,{})
    if not report:return 'not_reported'
    if report.get('status') in REFUSING_STATUSES:return 'reported_'+report['status']
    return None

def validate_order(s,side,order):
    if s.get('rules')!='poc-13':
        from .engine_v12 import validate_order as legacy_validate
        return legacy_validate(s,side,order)
    if not comms.operational(s,side):
        raise InvalidOrder('Command detachment is disrupted; subordinates continue under standing orders.')
    if not isinstance(order,dict) or set(order)-{'unit_id','destination','stance'}:
        raise InvalidOrder('Order must contain unit_id, destination and stance only.')
    u=find_unit(s,order.get('unit_id'))
    if not u or u['side'] != side:
        raise InvalidOrder('That unit is outside your command.')
    # Use delivered friendly knowledge, avoiding a hidden-state rejection oracle.
    refusal=report_refusal(s,side,u['id'])
    if refusal=='not_reported':raise InvalidOrder('That formation has not reported to headquarters.')
    if refusal:raise InvalidOrder('That unit is reported unable to accept orders.')
    order_rules.validate(s,side,order)
    return u

def issue(s,side,order,source='human'):
    if s.get('rules')!='poc-13':
        from .engine_v12 import issue as legacy_issue
        return legacy_issue(s,side,order,source)
    u=validate_order(s,side,order)
    order=order_rules.prepare(s,side,order)
    commander=comms.command_unit(s,side)
    version=max([o['version'] for o in s['orders'] if o['unit_id']==u['id']]+[u['order_version']])+1
    known=s['friendly_reports'][side][u['id']]['pos']
    method='voice' if u['id']==commander['id'] else 'courier'
    # poc-10: estimate over the gate states headquarters knows, never the true ones.
    # poc-13: always over known terrain, so a recipient beyond water with no
    # crossing gets no estimate rather than a one-interval guess.
    cells=gates.known_cells(s,side)
    packet=comms.envelope(s,commander['pos'],u['id'],known,method,cells=s['cells'] if cells is None else cells)
    oid=f'O{len(s["orders"])+1}'
    packet['id']=oid
    item={'id':oid,'side':side,**deepcopy(order),'source':source,'version':version,
          'sent_turn':s['turn'],'arrival_turn':packet['expected_turn'],'status':'en_route','transport':packet}
    s['orders'].append(item)
    emit(s,'order_sent',order_id=oid,side=side,unit_id=u['id'],destination=order.get('destination'),version=version,arrival_turn=item['arrival_turn'],transport=deepcopy(packet))
    message(s,side,f'{u["id"]}: {order["stance"]} order dispatched by {"voice" if method=="voice" else "runner"}. {estimate(s,item["arrival_turn"])}',kind='order')
    return item

def estimate(s,arrival_turn):
    """Headquarters' delivery estimate in words; unknown without a known route."""
    if arrival_turn is None:return 'Expected delivery time unknown; no known route.'
    return f'Expected delivery in {(arrival_turn-s["turn"])*30} seconds.'

def summary(u):
    result={k:deepcopy(u[k]) for k in ('id','side','name','pos','initial','strength','ammo','morale','suppression','fatigue','status','target','stance','order_version')}
    result.update({k:deepcopy(u[k]) for k in ('unit_type','weapon_class','skill','recon_role','recon_skill','local_action','local_reason','tactical_target','merged_into','mission_result','supply_site','tools','standing_profile','standing_version','cut_off','fire_posture') if k in u})
    return result

def enqueue(s, side, text, data=None, kind='dispatch', delay=1, sender=None):
    if s.get('rules')!='poc-13':
        from .engine_v12 import enqueue as legacy_enqueue
        return legacy_enqueue(s,side,text,data,kind,delay,sender)
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
    if s.get('rules')!='poc-13':
        from .engine_v12 import deliver_reports as legacy_deliver
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
        if report['kind']=='recommendation':
            recommendations.receive(s,report)
        if report['kind']=='terrain':
            features.receive(s,report)
        if report['kind']=='formation':
            formations.receive(s,report)
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

def contest(s,moves,occupied):
    """Why: two units wanting the same free hex both waited every interval, so
    neither ever moved (docs/research/45).
    What: the proposals of ``moves`` (unit, hex, cost) that may proceed. A move
    into an ``occupied`` hex is refused. Of several units wanting one free hex,
    the one refused most often since it last moved (``contest_wait``) enters,
    lowest id on a tie; each other contender's ``contest_wait`` rises by one.
    The caller clears ``contest_wait`` when a unit moves, so a contender waits
    at most one interval per rival before it has priority. Emits
    ``movement_blocked`` for every refusal, with ``reason`` ``contested``.
    Test: `test_priority_rotates_and_never_starves_a_unit`,
    `test_two_units_contending_for_one_hex_both_move`,
    `test_three_way_contention_lets_every_unit_through`."""
    wanted={}
    for m in moves:wanted.setdefault(grid.key(m[1]),[]).append(m[0])
    # Winners are fixed before any wait changes, so the order of moves cannot matter.
    winners={k:min(rivals,key=lambda r:(-r.get('contest_wait',0),r['id']))['id'] for k,rivals in wanted.items()}
    allowed=[]
    for u,p,cost in moves:
        k=grid.key(p)
        if k in occupied:
            emit(s,'movement_blocked',unit_id=u['id'],destination=p);continue
        if winners[k]!=u['id']:
            u['contest_wait']=u.get('contest_wait',0)+1
            emit(s,'movement_blocked',unit_id=u['id'],destination=p,reason='contested',
                 winner_id=winners[k],contest_wait=u['contest_wait'])
            continue
        allowed.append((u,p,cost))
    return allowed

def fired_upon(s,u,turn):
    """Why: a ``hold_fire`` unit returns fire only on evidence it observes.
    What: True when the events of interval ``turn`` show ``u`` under enemy
    fire that caused it casualties (``casualties``), or under any enemy fire
    (``unit_under_fire``) when the authored ``warning_shots_release`` is on.
    Test: `test_hold_fire_unit_returns_fire_when_fired_upon`,
    `test_warning_shots_release_only_when_authored`."""
    kind='unit_under_fire' if s['fire_rules']['warning_shots_release'] else 'casualties'
    for e in reversed(s['events']):
        if e['turn']<turn:return False
        if e['turn']==turn and e['kind']==kind and e.get('unit_id')==u['id']:return True
    return False

def volley(s,u,damage,suppression):
    """One unit's volley at the nearest visible enemy in range, from the
    pre-damage snapshot; adds to ``damage`` and ``suppression``. A volley by
    a unit holding fire is marked ``returning_fire`` (poc-13)."""
    enemies=[e for e in s['units'] if e['side']!=u['side'] and e['strength']>0
             and grid.distance(u['pos'],e['pos'])<=5 and grid.visible(s['cells'],u['pos'],e['pos'])]
    enemies=[e for e in enemies if grid.distance(u['pos'],e['pos'])<=standing.profile(u)['fire_range']]
    if not enemies: return
    target=min(enemies,key=lambda e:(grid.distance(u['pos'],e['pos']),e['id']))
    d=grid.distance(u['pos'],target['pos']); cover=s['cells'][grid.key(target['pos'])]['cover']
    rounds=min(u['ammo'],u['strength']); u['ammo']-=rounds
    # Integer exposure accumulation; synthetic POC coefficient, not historical ballistics.
    effect=rounds*(8-d)*(100-cover)*(100-u['suppression']//2)//9000
    effect=max(1,effect)
    damage[target['id']]+=effect
    suppression[target['id']]+=max(2,rounds//4)
    extra={'returning_fire':True} if u.get('fire_posture')=='hold_fire' else {}
    emit(s,'volley',unit_id=u['id'],target_id=target['id'],rounds=rounds,exposure=effect,**extra)

def advance(s):
    """Mutates only supplied state; all fire uses the same pre-damage snapshot."""
    if s.get('rules')=='poc-1':
        from .engine_v1 import advance as legacy_advance
        return legacy_advance(s)
    if s.get('rules')=='poc-2':
        from .engine_v2 import advance as previous_advance
        return previous_advance(s)
    if s.get('rules')=='poc-3':
        from .engine_v3 import advance as prior_advance
        return prior_advance(s)
    if s.get('rules')=='poc-4':
        from .engine_v4 import advance as fourth_advance
        return fourth_advance(s)
    if s.get('rules')=='poc-5':
        from .engine_v5 import advance as fifth_advance
        return fifth_advance(s)
    if s.get('rules')=='poc-6':
        from .engine_v6 import advance as sixth_advance
        return sixth_advance(s)
    if s.get('rules')=='poc-7':
        from .engine_v7 import advance as seventh_advance
        return seventh_advance(s)
    if s.get('rules')=='poc-8':
        from .engine_v8 import advance as eighth_advance
        return eighth_advance(s)
    if s.get('rules')=='poc-9':
        from .engine_v9 import advance as ninth_advance
        return ninth_advance(s)
    if s.get('rules')=='poc-10':
        from .engine_v10 import advance as tenth_advance
        return tenth_advance(s)
    if s.get('rules')=='poc-11':
        from .engine_v11 import advance as eleventh_advance
        return eleventh_advance(s)
    if s.get('rules')=='poc-12':
        from .engine_v12 import advance as twelfth_advance
        return twelfth_advance(s)
    if s.get('rules')!='poc-13':raise ValueError('Unsupported battle rules version.')
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
        # poc-13: a fire-discipline order changes the posture only, never the mission.
        posture=o['stance'] in order_rules.POSTURES
        if o['version']<=(u.get('fire_posture_version',0) if posture else u['order_version']):
            o['status']='superseded'
        elif u['status'] in ('routed','lost','merged'):
            o['status']='refused'
        elif posture:
            o['status']='delivered'; u.update(fire_posture=o['stance'],fire_posture_version=o['version'])
            emit(s,'fire_posture_set',unit_id=u['id'],order_id=o['id'],fire_posture=o['stance'])
        else:
            o['status']='delivered'; u['order_version']=o['version']
            u['target']=deepcopy(o.get('destination')); u['stance']=o['stance']
            order_rules.start(s,u,o)
        emit(s,'order_'+o['status'],order_id=o['id'],unit_id=u['id'],version=o['version'])
        enqueue(s,o['side'],f'{u["id"]}: order {o["id"]} {o["status"]}.',data={'order_id':o['id'],'status':o['status']},kind='ack',sender=u['id'])
    standing.deliver(s)
    formations.progress(s)
    local_sightings=recon.scan(s)
    for contacts in local_sightings.values():
        for contact in contacts:contact['phase']='1_before_actions'
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0:continue
        decision=order_rules.decide(s,u,local_sightings.get(u['id'],[]))
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
            gateway=None if route else gates.approach(s,u['pos'],move_target)
            if gateway and u['pos']!=gateway:
                # poc-10: a shut compound is approached at its gate, which is then forced.
                route=grid.path(s['cells'],u['pos'],gateway,blocked=occupied)
            if route:
                nxt=route[0]; cost=grid.cost(s['cells'],u['pos'],nxt)
                if u['move_credit']>=cost:
                    moves.append((u,nxt,cost))
        elif u['stance'] not in ('rest','dig_in') and u['local_action'] in ('hold','observe') and s['turn']-u.get('last_attacked_turn',-99)>1:
            u['fatigue']=max(0,u['fatigue']-2)
            if u['status']!='routed': u['morale']=min(90,u['morale']+1)
    # A conservative occupancy rule: no swaps or stacking. poc-12: one of the
    # units wanting a free hex enters it (contest); the others wait.
    for u,p,cost in contest(s,moves,occupied):
        u.pop('contest_wait',None)
        old=u['pos']; u['pos']=p; u['move_credit']-=cost; u['fatigue']=min(100,u['fatigue']+3)
        emit(s,'unit_moved',unit_id=u['id'],origin=old,destination=p,decision_seq=u['local_decision_seq'])
        if p==u['target'] and u['stance'] not in ('resupply','recon'):
            order_rules.complete(s,u,'Assigned position reached.')
    damage={u['id']:0 for u in s['units']}; suppression={u['id']:0 for u in s['units']}
    holding=[]
    for u in sorted(s['units'],key=lambda x:x['id']):
        if u['strength']<=0 or u['ammo']<=0 or u['status']=='routed': continue
        # poc-13: a unit holding fire fires only if fired upon in the previous interval ...
        if u.get('fire_posture')=='hold_fire' and not fired_upon(s,u,s['turn']-1):
            holding.append(u);continue
        volley(s,u,damage,suppression)
    # ... or in this one. The released set is fixed before any return volley.
    warning=s['fire_rules']['warning_shots_release']
    released=[u for u in holding if suppression[u['id']]>0
              and (warning or (u['loss_credit']+damage[u['id']])//100>0)]
    for u in released:volley(s,u,damage,suppression)
    for u in s['units']:
        if u['status']=='merged':continue
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
    gates.progress(s)  # poc-10: gate labour continues under fire, adjudicated after it.
    gates.push(s)  # poc-11: attackers push through a held gateway, also under fire.
    order_rules.progress(s)  # Recovery/loading is adjudicated after fire, never during it.
    features.report(s)
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
    for side in sides(s):
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
    recommendations.generate(s,sightings)
    deliver_reports(s)  # Local voice reports arrive now; couriers cannot move twice.
    winner,reason=victory.score(s)  # The scenario's victory kind, stored in the snapshot.
    if winner:
        s['status']='complete'; s['winner']=winner; s['reason']=reason
        emit(s,'battle_ended',winner=winner,reason=reason)
        for side in sides(s): message(s,side,reason,kind='outcome')
    emit(s,'turn_completed',turn_number=s['turn'])
    return s

def view(s,side=None):
    """Why: each side commands from its own delivered reports only.
    What: the commander view for ``side``; None means the snapshot's player
    side (Union before poc-9). Earlier editions use their frozen views.
    Test: `test_renamed_side_duel_runs_headless_and_replays`."""
    if s.get('rules')!='poc-13':
        from .engine_v12 import view as legacy_view
        return legacy_view(s,side)
    side=side or player_side(s)
    units=[deepcopy(u) for u in s['friendly_reports'][side].values() if u.get('status')!='merged']
    commander=comms.command_unit(s,side)
    if commander:
        units=[u for u in units if u['id']!=commander['id']]
        units.append(dict(summary(commander),observed_turn=s['turn'],received_turn=s['turn']))
        units.sort(key=lambda u:u['id'])
    contacts=[dict(deepcopy(c),age=s['turn']-c['observed_turn']) for c in s['contacts'][side].values()
              if s['turn']-c['observed_turn']<=recon.CONTACT_MAX_AGE]
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
            'command':comms.location(s,side),
            'standing_templates':standing.catalog(s),
            'standing_orders':standing.visible(s,side),
            'recommendations':recommendations.visible(s,side),
            'map_features':features.known(s,side),
            'order_templates':order_rules.catalog(s),
            'supply_sites':order_rules.known_sites(s,side),
            'formation_ops':[formations.observed(s,o) for o in s['formation_ops'] if o['side']==side]}


def god_view(s):
    """Explicit local debug observer. Never use this as an agent observation."""
    result=view(s)
    result.update(view_mode='god',units=[dict(deepcopy(u),observed_turn=s['turn'],received_turn=s['turn']) for u in s['units'] if u.get('status')!='merged'],
                  contacts=[],orders=deepcopy(s['orders']),reports=deepcopy(s['reports']),
                  events=deepcopy(s['events']),decisions=deepcopy(s['decisions']),
                  headquarters=deepcopy(s['hq']),
                  commands={side:comms.location(s,side) for side in sides(s)} if s.get('rules') in ('poc-3','poc-4','poc-5','poc-6','poc-7','poc-8','poc-9','poc-10','poc-11','poc-12','poc-13') else {},
                  dispatches=[dict(deepcopy(d),side=side) for side in sides(s) for d in s['dispatches'][side]])
    result.update(standing_orders=deepcopy(s.get('standing_orders',[])),recommendations=deepcopy(s.get('recommendations',[])),map_features=deepcopy(s.get('map_features',[])),supply_sites=deepcopy(s.get('supply_sites',[])),formation_ops=deepcopy(s.get('formation_ops',[])),retired_units=deepcopy(s.get('retired_units',[])))
    return result
