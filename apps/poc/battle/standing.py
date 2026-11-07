"""Persistent contact doctrine, delivered independently from mission orders.

Thresholds are transparent POC tuning values, not historical measurements.
"""
from copy import deepcopy
from . import comms,gates

VERSION='standing-orders-v1'
GATE_VERSION='standing-orders-v2'  # v1 plus Close the gate on a breach (poc-10, battles with a gate).
TEMPLATES=[
    {'id':'balanced','label':'Balanced',
     'intent':'Carry out the mission, use cover and fall back when the detachment is in serious danger.',
     'morale_floor':45,'suppression_limit':70,'enemy_ratio':2.5,'reserve_volleys':1,'fire_range':5},
    {'id':'cautious','label':'Preserve the force',
     'intent':'Avoid costly engagements. Fall back earlier when pressed, low on cartridges or shaken.',
     'morale_floor':60,'suppression_limit':50,'enemy_ratio':1.5,'reserve_volleys':3,'fire_range':5},
    {'id':'firm','label':'Hold ground firmly',
     'intent':'Accept greater pressure to hold the ground. Seek cover; withdraw if the formation can no longer stand.',
     'morale_floor':35,'suppression_limit':85,'enemy_ratio':3.5,'reserve_volleys':1,'fire_range':5},
    {'id':'screen','label':'Observe and screen',
     'intent':'Watch and report; avoid equal or stronger opposition. Reserve fire for close threats within three hexes.',
     'morale_floor':60,'suppression_limit':50,'enemy_ratio':1.0,'reserve_volleys':3,'fire_range':3},
]

def templates(s=None):
    """Templates on offer: poc-10 battles with a gate add Close the gate on a breach."""
    return TEMPLATES+([gates.STANDING] if s is not None and gates.present(s) else [])

def catalog(s=None):
    return [dict(deepcopy(t),version=VERSION if t in TEMPLATES else GATE_VERSION,
                 message_key='standing.template.'+t['id']) for t in templates(s)]

def profile(u):
    return next((t for t in TEMPLATES+[gates.STANDING] if t['id']==u.get('standing_profile')),TEMPLATES[0])

def recommend(u):
    # Takes an observer-visible unit report, never a simulation or enemy state.
    if u.get('morale',100)<60 or u.get('fatigue',0)>=55 or u.get('suppression',0)>=50 or u.get('ammo',0)<u.get('strength',0)*10 or u.get('strength',0)*2<u.get('initial',0):
        return {'profile_id':'cautious','reason':'General, the reported condition warrants preserving the detachment until it can recover or replenish.'}
    if u.get('recon_role')=='scout' or u.get('stance')=='recon':
        return {'profile_id':'screen','reason':'General, this detachment is assigned to observation. Let it report the enemy and avoid a costly engagement.'}
    return {'profile_id':'balanced','reason':'General, the reported condition supports ordinary discretion. Reserve a firmer instruction for ground you judge indispensable.'}

def issue(s,side,instruction):
    from . import engine
    if s.get('rules') not in ('poc-8','poc-9','poc-10','poc-11','poc-12','poc-13'):raise ValueError('Reset to enable configurable standing orders in a new battle.')
    if not isinstance(instruction,dict) or set(instruction)!={'unit_id','profile_id'}:raise ValueError('Choose a unit and standing-order template.')
    if instruction['profile_id'] not in [t['id'] for t in templates(s)]:raise ValueError('Unknown standing-order template.')
    u=engine.validate_order(s,side,{'unit_id':instruction['unit_id'],'stance':'hold','destination':None})
    commander=comms.command_unit(s,side)
    packet=comms.envelope(s,commander['pos'],u['id'],s['friendly_reports'][side][u['id']]['pos'],
                          'voice' if commander['id']==u['id'] else 'courier',cells=gates.known_cells(s,side))
    version=max([o['version'] for o in s['standing_orders'] if o['unit_id']==u['id']]+[u['standing_version']])+1
    oid=f'SO{len(s["standing_orders"])+1}';packet['id']=oid
    item={'id':oid,'side':side,**deepcopy(instruction),'version':version,'sent_turn':s['turn'],
          'arrival_turn':packet['expected_turn'],'status':'en_route','transport':packet,'template_version':VERSION}
    s['standing_orders'].append(item)
    engine.emit(s,'standing_order_sent',order=deepcopy(item))
    label=next(t['label'] for t in templates(s) if t['id']==instruction['profile_id'])
    engine.message(s,side,f'General, {label.lower()} instructions dispatched to {u["id"]}. The present mission remains in force.',kind='standing')
    return item

def deliver(s):
    from . import engine
    for o in s['standing_orders']:
        if o['status']!='en_route':continue
        status=comms.progress(s,o['transport'],engine.emit)
        if status=='en_route':continue
        u=engine.find_unit(s,o['unit_id'])
        if status=='expired':
            o['status']='expired'
        elif o['version']<=u['standing_version']:o['status']='superseded'
        # poc-13B review: a leaderless unit refuses standing instructions too.
        elif u['status'] in ('routed','lost','merged') or u.get('leaderless'):o['status']='refused'
        else:
            o['status']='delivered'
            u.update(standing_profile=o['profile_id'],standing_version=o['version'])
        engine.emit(s,'standing_order_'+o['status'],order_id=o['id'],unit_id=o['unit_id'],version=o['version'],profile_id=o['profile_id'])
        if status!='expired':
            engine.enqueue(s,o['side'],f'{u["id"]} to headquarters: standing instructions {o["id"]} {o["status"]}.',
                           data={'order_id':o['id'],'status':o['status']},kind='ack',sender=u['id'])

def visible(s,side):
    return [{k:deepcopy(v) for k,v in o.items() if k not in ('status','transport')} |
            {'status':s['acknowledgements'][side].get(o['id'],{}).get('status','awaiting_ack')}
            for o in s.get('standing_orders',[]) if o['side']==side]


# docs/research/60 §2: a declared exploit (unit key ``exploit``). Off unless declared.
EXPLOIT_FIELDS=('max_loss_pct','press_to','recall_binding','trigger')
EXPLOIT_TRIGGERS=('arrival','start')
PRESS_REASON='Local success; pressing on toward the declared ground and returning fire.'

def _succeeded(u,rule):
    """The unit's own local success: at the start, or once its move order is completed."""
    mission=u.get('mission_result') or {}
    return rule['trigger']=='start' or (mission.get('template')=='move' and mission.get('status')=='completed')

def _recalled(s,u):
    """True when ``u`` itself heard a recall signal (its own receipt, docs/research/60 §1)."""
    kinds={b['id']:b['kind'] for b in s.get('broadcasts',())}
    return any(kinds.get(i)=='recall' for i in u.get('heard_signals',()))

def _stop(s,u,rule,decision):
    """The reason a pressing unit stops, or None."""
    if list(u['pos'])==list(rule['press_to']):return 'reached'
    if rule['recall_binding'] and _recalled(s,u):return 'recalled'
    if rule['recall_binding'] and u['order_version']>u['exploit_version']:return 'ordered'
    if (u['initial']-u['strength'])*100>=rule['max_loss_pct']*u['initial']:return 'losses'
    if u['status']=='routed' or decision['action'] in ('withdraw','route'):return 'shaken'
    return None

def exploit(s,u,decision):
    """Why: troops that have won a local success may press on beyond their
    orders (docs/research/57, VII.47 and VII.52), which no standing profile did.
    What: for a unit that declares ``exploit``, once its local success is
    made (``trigger`` ``start``, or ``arrival``: its move order completed),
    the local decision becomes ``press`` toward ``press_to`` while it returns
    fire, whatever its mission or contacts, until it stops for good: it
    reaches ``press_to``; with ``recall_binding``, it hears a recall or a
    newer order reaches it; its losses reach ``max_loss_pct`` per cent of its
    initial strength; or its own triggers make it withdraw or rout. A binding
    recall heard before the success also ends it. ``recall_binding`` false is
    the ardour reading: the unit hears the recall, takes it up as its
    mission, and obeys it only once the press stops. Reads only the unit, its
    own signal receipts and the decision from its own observations.
    Events ``exploit_started`` and ``exploit_stopped`` (with ``reason``).
    Test: `test_after_arrival_the_unit_presses_on_to_its_declared_hex`,
    `test_a_heard_binding_recall_stops_the_press`,
    `test_ardour_keeps_pressing_after_a_heard_recall_then_obeys_it`,
    `test_an_enemy_the_unit_cannot_see_does_not_change_the_decision`."""
    from . import engine
    rule=u.get('exploit')
    if not rule or u.get('exploit_state')=='stopped' or u['strength']<=0:return decision
    if u.get('exploit_state') is None:
        if rule['recall_binding'] and _recalled(s,u):
            u['exploit_state']='stopped';engine.emit(s,'exploit_stopped',unit_id=u['id'],reason='recalled')
            return decision
        if not _succeeded(u,rule):return decision
        u.update(exploit_state='pressing',exploit_version=u['order_version'])
        engine.emit(s,'exploit_started',unit_id=u['id'],press_to=list(rule['press_to']))
    reason=_stop(s,u,rule,decision)
    if reason:
        u['exploit_state']='stopped';engine.emit(s,'exploit_stopped',unit_id=u['id'],reason=reason)
        return decision
    decision.update(action='press',target=list(rule['press_to']),reason=PRESS_REASON)
    return decision
