"""poc-3 physical command and deterministic courier transport.

Travel rates and forwarding are authored abstractions, not historical measures.
Packets navigate terrain to an address; a moved recipient adds another journey.
No enemy truth influences routing. Interception and courier personnel are deferred.
"""
from copy import deepcopy
from . import grid

PROFILE={'id':'civil-war-courier-v1','label':'1863 · voice / foot courier',
         'methods':['voice','courier'],'cost_per_turn':200,'expiry_turns':20}

def command_unit(s,side):
    uid=s['commanders'][side]['unit_id']
    return next((u for u in s['units'] if u['id']==uid),None)

def operational(s,side):
    u=command_unit(s,side)
    return bool(u and u['strength']>0 and u['status'] not in ('lost','routed'))

def sync(s):
    for side in s['commanders']:
        u=command_unit(s,side)
        if u:s['hq'][side]=list(u['pos'])

def location(s,side):
    u=command_unit(s,side)
    return {**deepcopy(s['commanders'][side]),'pos':list(u['pos']) if u else None,
            'status':u['status'] if u else 'lost','operational':operational(s,side),
            'profile':deepcopy(PROFILE)}

def envelope(s,origin,recipient,address,method='courier',handling=0):
    route=grid.path(s['cells'],origin,address)
    previous=origin;cost=0
    for p in route:
        cost+=grid.cost(s['cells'],previous,p);previous=p
    delay=max(1,(cost+PROFILE['cost_per_turn']-1)//PROFILE['cost_per_turn'])+handling
    return {'method':method,'origin':list(origin),'pos':list(origin),'address':list(address),
            'recipient_id':recipient,'credit':0,'sent_turn':s['turn'],
            'ready_turn':s['turn']+1+handling,'last_progress_turn':s['turn'],
            'expected_turn':s['turn']+delay,'expires_turn':s['turn']+PROFILE['expiry_turns']+handling,
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
    if packet['method']=='voice':
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
