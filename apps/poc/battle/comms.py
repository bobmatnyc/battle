"""poc-3 physical command and deterministic courier transport.

Travel rates and forwarding are authored abstractions, not historical measures.
Packets navigate terrain to an address; a moved recipient adds another journey.
No enemy truth influences routing. Interception and courier personnel are deferred.
"""
from copy import deepcopy
from . import grid

PROFILE={'id':'civil-war-courier-v1','label':'1863 · voice / foot courier',
         'methods':['voice','courier'],'cost_per_turn':200,'expiry_turns':20}
# Hougoumont (docs/research/42): the 1863 transport rates under an 1815 label.
# Period rates (gallopers, aides-de-camp) are deferred; transport reads PROFILE.
# poc-13B (docs/research/47): 1775 speech carries ``voice_reach`` hexes from the
# command detachment; farther units get a runner at the 1863 rates. The reach
# is an assumption, not a measured earshot.
COLONIAL={**PROFILE,'id':'colonial-1775-voice-v1','label':'1775 · voice / runner','voice_reach':2}
# docs/research/53: 1944 company radio. A unit within ``radio_range`` hexes of
# the command detachment gets orders, and sends reports, by radio in one
# interval; voice and runner remain. Both reaches are assumptions.
WWII={**PROFILE,'id':'wwii-1944-radio-v1','label':'1944 · radio / voice / runner',
      'methods':['voice','radio','courier'],'voice_reach':2,'radio_range':10}
PROFILES={p['id']:p for p in (PROFILE,{**PROFILE,'id':'napoleonic-courier-v1','label':'1815 · voice / foot runner'},COLONIAL,WWII)}

def command_unit(s,side):
    uid=s['commanders'][side]['unit_id']
    return next((u for u in s['units'] if u['id']==uid),None)

def operational(s,side):
    u=command_unit(s,side)
    # poc-13B: a leaderless detachment cannot command; no earlier unit has the flag.
    return bool(u and u['strength']>0 and u['status'] not in ('lost','routed') and not u.get('leaderless'))

def sync(s):
    for side in s['commanders']:
        u=command_unit(s,side)
        if u:s['hq'][side]=list(u['pos'])

def location(s,side):
    u=command_unit(s,side)
    return {**deepcopy(s['commanders'][side]),'pos':list(u['pos']) if u else None,
            'status':u['status'] if u else 'lost','operational':operational(s,side),
            'profile':deepcopy(PROFILES[s['commanders'][side]['communications']])}

def envelope(s,origin,recipient,address,method='courier',handling=0,cells=None):
    """A packet from origin to address. Its ``expected_turn`` is planned over
    ``cells``, the sender's knowledge (poc-10 gates), else the live cells.
    Over known cells with no known route, the expected turn is None (unknown)."""
    plan=s['cells'] if cells is None else cells
    route=grid.path(plan,origin,address)
    previous=origin;cost=0
    for p in route:
        cost+=grid.cost(plan,previous,p);previous=p
    delay=max(1,(cost+PROFILE['cost_per_turn']-1)//PROFILE['cost_per_turn'])+handling
    if cells is not None and not route and list(origin)!=list(address):delay=None
    return {'method':method,'origin':list(origin),'pos':list(origin),'address':list(address),
            'recipient_id':recipient,'credit':0,'sent_turn':s['turn'],
            'ready_turn':s['turn']+1+handling,'last_progress_turn':s['turn'],
            'expected_turn':None if delay is None else s['turn']+delay,'expires_turn':s['turn']+PROFILE['expiry_turns']+handling,
            'status':'en_route','forwardings':0}

def progress(s,packet,emit):
    """At most one transport step per simulation interval. Never teleport payloads."""
    if packet['status']!='en_route':return packet['status']
    if s['turn']<packet['ready_turn'] or packet['last_progress_turn']==s['turn']:return 'en_route'
    packet['last_progress_turn']=s['turn']
    if s['turn']>=packet['expires_turn']:
        packet['status']='expired'
        emit(s,'communication_expired',packet=deepcopy(packet))
        return 'expired'
    # Voice applies only to the detachment carrying the commander.
    target=next((u for u in s['units'] if u['id']==packet['recipient_id']),None)
    # docs/research/53: a radio packet arrives in one step, as speech does.
    spoken=packet['method'] in ('voice','radio')
    if spoken and 'speaker_id' in packet:
        # poc-13B: a spoken order to a unit now out of earshot goes on by runner.
        from .command import relay
        if relay(s,packet,target,emit):return 'en_route'
    if spoken:
        packet['pos']=list(target['pos']) if target else packet['pos']
    else:
        packet['credit']=min(400,packet['credit']+PROFILE['cost_per_turn'])
        for p in grid.path(s['cells'],packet['pos'],packet['address']):
            cost=grid.cost(s['cells'],packet['pos'],p)
            if cost>packet['credit']:break
            packet['credit']-=cost;packet['pos']=p
        if packet['pos']!=packet['address']:return 'en_route'
        if target and target['pos']!=packet['address']:
            # Friendly forwarding is abstracted, but costs a fresh physical trip.
            packet['address']=list(target['pos']);packet['credit']=0;packet['forwardings']+=1
            emit(s,'communication_forwarded',packet=deepcopy(packet))
            return 'en_route'
    packet['status']='arrived'
    return 'arrived'
