"""Common mission templates. All rates are authored, uncalibrated POC rules."""
from copy import deepcopy
from . import grid,features,gates,recon
from . import tactics_v8 as tactics,tactics_v9,tactics_v10
from .engine_v2 import InvalidOrder

VERSION='common-orders-v3'
GATE_VERSION='common-orders-v4'  # v3 plus Close the gate (poc-10, battles with a gate).
# poc-13: Hold fire and Open fire, in every battle (docs/research/46).
FIRE_VERSION,FIRE_GATE_VERSION='common-orders-v5','common-orders-v6'
ROUNDS_PER_TROOP=40
LOAD_ROUNDS_PER_TROOP=5
REST_RECOVERY=6
TEMPLATES=[
    {'id':'hold','label':'Hold and defend','destination':'none',
     'intent':'Hold your present ground; defend the position and report enemy contact.',
     'effect':'Maintain position until relieved. Local commanders may seek cover or withdraw if overwhelmed.'},
    {'id':'move','label':'Move to position','destination':'hex',
     'intent':'Proceed to the appointed map reference, then hold and report your arrival.',
     'effect':'Travel over terrain. Contact can interrupt movement; the destination remains your mission.'},
    {'id':'rest','label':'Rest and recover','destination':'none',
     'intent':'Halt the detachment and rest the men. Keep watch; defend yourselves if attacked.',
     'effect':'Recover fatigue while clear of contact. Finish at zero fatigue. No replacement troops or ammunition.'},
    {'id':'retreat','label':'Retreat to position','destination':'hex',
     'intent':'Fall back to the appointed position, preserving the detachment; report when established.',
     'effect':'Withdraw toward the selected hex. Avoid closing with observed threats; defend if the way is blocked.'},
    {'id':'resupply','label':'Replenish ammunition','destination':'supply',
     'intent':'Proceed to our ammunition point and replenish your cartridge boxes. Report shortages.',
     'effect':'Use the nearest friendly ammunition point. Load from finite stocks only while adjacent and clear of contact.'},
    {'id':'recon','label':'Reconnoiter position','destination':'hex',
     'intent':'Examine the appointed ground, observe the enemy and send word. Avoid a close engagement.',
     'effect':'Move cautiously to the selected hex, then maintain observation. Does not confer scout skill or reveal hidden troops.'},
    {'id':'dig_in','label':'Dig in','destination':'none',
     'intent':'Strengthen your present position with hasty fieldworks. Keep watch and report when ready.',
     'effect':'Work takes time and increases fatigue. Tools and ground determine progress; fire interrupts construction. Cover remains on this hex when the unit leaves.'},
]

# poc-13 fire discipline: these set the unit's fire posture and leave its mission alone.
FIRE_TEMPLATES=[
    {'id':'hold_fire','label':'Hold fire','destination':'none',
     'intent':'Do not fire unless fired upon. Keep your present instructions.',
     'effect':'The detachment does not open fire; it returns fire once enemy fire strikes it. Its mission is unchanged.'},
    {'id':'open_fire','label':'Open fire','destination':'none',
     'intent':'Engage the enemy within range. Keep your present instructions.',
     'effect':'The detachment fires on the nearest enemy in range. Its mission is unchanged.'},
]
POSTURES=tuple(t['id'] for t in FIRE_TEMPLATES)

def catalog(s):
    if s.get('rules')=='poc-7':
        from .orders_v7 import catalog as seventh_catalog
        return seventh_catalog(s)
    if s.get('rules')=='poc-6':
        from .orders_v6 import catalog as sixth_catalog
        return sixth_catalog(s)
    if s.get('rules')=='poc-5':
        from .orders_v5 import catalog as previous_catalog
        return previous_catalog(s)
    entries=TEMPLATES if s.get('rules') in ('poc-8','poc-9','poc-10','poc-11','poc-12','poc-13') else TEMPLATES[:2]
    version=VERSION
    if gates.present(s):entries,version=entries+[gates.TEMPLATE],GATE_VERSION
    if s.get('rules')=='poc-13':
        entries,version=entries+FIRE_TEMPLATES,FIRE_GATE_VERSION if gates.present(s) else FIRE_VERSION
    return [dict(deepcopy(t),message_key='order.template.'+t['id'],version=version) for t in entries]

def available(s):
    """Templates an order may name: poc-10 battles with a gate add Close the
    gate; poc-13 adds Hold fire and Open fire."""
    return TEMPLATES+([gates.TEMPLATE] if gates.present(s) else [])+(FIRE_TEMPLATES if s.get('rules')=='poc-13' else [])

def known_sites(s,side):
    # Positions are in the initial briefing. Remaining stocks require a local report.
    return [{k:deepcopy(d[k]) for k in ('id','side','name','pos','weapon_class')}
            for d in s.get('supply_sites',[]) if d['side']==side]

def validate(s,side,order):
    template=next((t for t in available(s) if t['id']==order.get('stance')),None)
    if not template:raise InvalidOrder('Choose an available order template.')
    if template['destination']=='hex':
        if not grid.valid(order.get('destination')):raise InvalidOrder('Choose a destination hex inside the battlefield.')
        # poc-13: the briefed map shows the water; earlier maps have none.
        if not grid.passable(s['cells'][grid.key(order['destination'])]):raise InvalidOrder('That hex is impassable water; choose a bank, bridge or ford.')
    elif order.get('destination') is not None:
        raise InvalidOrder('This template selects its own position; omit the destination.')
    if template['id']=='resupply' and not known_sites(s,side):
        raise InvalidOrder('No friendly ammunition point is recorded in the briefing.')

def prepare(s,side,order):
    result=deepcopy(order)
    if order['stance']=='resupply':
        known=s['friendly_reports'][side][order['unit_id']]
        sites=[d for d in known_sites(s,side) if d['weapon_class']==known.get('weapon_class')]
        if not sites:raise InvalidOrder('No compatible ammunition point is recorded.')
        depot=min(sites,key=lambda d:(grid.distance(known['pos'],d['pos']),d['id']))
        result.update(destination=list(depot['pos']),supply_id=depot['id'])
    return result

def start(s,u,order):
    from . import engine
    previous=u.get('mission_result')
    if previous and previous['status'] in ('active','blocked'):
        engine.emit(s,'mission_superseded',unit_id=u['id'],order_version=previous['order_version'],replaced_by=order['version'])
    u['supply_site']=order.get('supply_id')
    u['mission_result']={'template':order['stance'],'status':'active','order_version':order['version'],
                         'started_turn':s['turn'],'updated_turn':s['turn'],'reason':'Instructions received.'}
    engine.emit(s,'mission_started',unit_id=u['id'],order_id=order['id'],template=order['stance'],order_version=order['version'])

def status(s,u,value,reason):
    from . import engine
    mission=u.get('mission_result')
    if not mission or (mission['status']==value and mission['reason']==reason):return
    mission.update(status=value,reason=reason,updated_turn=s['turn'])
    engine.emit(s,'mission_'+value,unit_id=u['id'],template=mission['template'],order_version=mission['order_version'],reason=reason)
    engine.enqueue(s,u['side'],f'{u["id"]} to headquarters: {reason}',kind='mission',sender=u['id'])

def complete(s,u,reason):
    status(s,u,'completed',reason)
    u.update(target=None,stance='hold')

def decide(s,u,contacts):
    # poc-12: assaults on a gated compound press on within 5 hexes (tactics_v9).
    # poc-13: tactics_v10 also ages out stale contacts and keeps off water.
    policy={'poc-12':tactics_v9,'poc-13':tactics_v10}.get(s.get('rules'),tactics)
    decision=policy.decide(s,u,contacts)
    decision['policy']=VERSION
    stance=u['stance']
    if u['status']=='routed':return decision
    if stance=='close_gate':  # poc-10: the gate party stays at its work under fire.
        decision.update(action='hold',target=None,reason='Closing the gate; the party holds at its work under fire.')
        return decision
    threats=[c['pos'] for c in contacts if grid.distance(u['pos'],c['pos'])<=5]
    # A commanded withdrawal is distinct from panic. Recon avoids closing on contact.
    if stance=='retreat' or (stance=='recon' and (threats or decision['under_fire'])):
        target=u.get('target')
        if target is not None and (u['pos']!=target or (stance=='recon' and threats)):
            if threats:
                occupied={grid.key(f['pos']) for f in s['units'] if f['side']==u['side'] and f['id']!=u['id'] and f['strength']>0 and grid.visible(s['cells'],u['pos'],f['pos'])}
                distance=lambda p:min(grid.distance(p,t) for t in threats)
                candidates=[p for p in grid.neighbors(u['pos']) if grid.key(p) not in occupied
                            and distance(p)>=distance(u['pos']) and p not in threats
                            and grid.passable(s['cells'][grid.key(p)])]  # poc-13 water; none earlier.
                step=min(candidates,key=lambda p:((-distance(p),grid.distance(p,target)) if stance=='recon' else (grid.distance(p,target),-distance(p)))+(-s['cells'][grid.key(p)]['cover'],p)) if candidates else None
                decision.update(action='fall_back',target=step,reason='Fall back without closing upon the observed enemy.' if step else 'No safe withdrawal step is known; defend while seeking a way out.')
            else:
                decision.update(action='continue',target=None,reason='Carry out the ordered withdrawal toward the appointed position.')
        else:decision.update(action='hold',target=None,reason='The withdrawal position has been reached.')
    elif stance=='rest' and decision['action'] in ('hold','observe'):
        decision['reason']='Rest the men and keep watch; suspend recovery if danger approaches.'
    elif stance=='resupply' and decision['action'] in ('continue','hold','observe'):
        depot=next((d for d in s['supply_sites'] if d['id']==u.get('supply_site')),None)
        if depot and grid.distance(u['pos'],depot['pos'])<=1:
            decision.update(action='hold',target=None,reason='At the ammunition point; replenish only while clear of enemy contact.')
    return decision

def progress(s):
    from . import engine
    for u in sorted(s['units'],key=lambda x:x['id']):
        mission=u.get('mission_result')
        if not mission or mission['status'] not in ('active','blocked'):continue
        if u['status'] in ('routed','lost','merged'):
            status(s,u,'failed','The formation can no longer carry out these instructions.');continue
        stance=u['stance']
        if stance in ('move','retreat') and u['pos']==u.get('target'):
            complete(s,u,'Assigned position reached.');continue
        if stance=='recon' and u['pos']==u.get('target'):
            status(s,u,'active','At the appointed ground; maintaining observation and sending reports.')
        if stance not in ('rest','resupply','dig_in'):continue
        # Re-evaluate after simultaneous fire: no same-interval rest/loading under attack.
        unsafe=(s['turn']-u.get('last_attacked_turn',-99)<=1 or u['suppression']>20
                or u.get('local_action') not in ('hold','observe')
                or any(e['side']!=u['side'] and e['strength']>0 and grid.distance(u['pos'],e['pos'])<=5
                       and recon.sees(s,u,e['pos']) for e in s['units']))  # docs/research/53: night range.
        if stance=='dig_in':
            features.dig(s,u,unsafe)
        elif stance=='rest':
            if unsafe:status(s,u,'blocked','Rest suspended; the detachment must attend to its safety.');continue
            status(s,u,'active','The men are resting under a watch.')
            before=u['fatigue'];u['fatigue']=max(0,before-REST_RECOVERY)
            if before!=u['fatigue']:engine.emit(s,'unit_rested',unit_id=u['id'],order_version=u['order_version'],fatigue_before=before,fatigue_after=u['fatigue'])
            if u['fatigue']==0:complete(s,u,'The men have rested; holding the present position.')
        else:
            depot=next((d for d in s['supply_sites'] if d['id']==u.get('supply_site') and d['side']==u['side'] and d['weapon_class']==u['weapon_class']),None)
            if not depot:status(s,u,'failed','The assigned ammunition point is unavailable.');u.update(stance='hold',target=None);continue
            if grid.distance(u['pos'],depot['pos'])>1:
                status(s,u,'active','Proceeding to the assigned ammunition point.');continue
            if unsafe:status(s,u,'blocked','Ammunition loading suspended; enemy contact makes the position unsafe.');continue
            needed=max(0,u['strength']*ROUNDS_PER_TROOP-u['ammo'])
            if not needed:complete(s,u,'Cartridge boxes are replenished; holding at the ammunition point.');continue
            if depot['ammo']<=0:
                status(s,u,'failed','The ammunition point is exhausted; no further cartridges are available.')
                u.update(stance='hold',target=None);continue
            status(s,u,'active','Replenishing cartridge boxes from the ammunition point.')
            amount=min(needed,depot['ammo'],u['strength']*LOAD_ROUNDS_PER_TROOP)
            depot['ammo']-=amount;u['ammo']+=amount
            engine.emit(s,'ammunition_transferred',unit_id=u['id'],supply_id=depot['id'],order_version=u['order_version'],rounds=amount,depot_remaining=depot['ammo'],unit_ammo=u['ammo'])
            if u['ammo']>=u['strength']*ROUNDS_PER_TROOP:complete(s,u,'Cartridge boxes are replenished; holding at the ammunition point.')
