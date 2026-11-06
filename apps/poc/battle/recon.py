"""Deterministic aggregate observations, not access to enemy inventory.

All coefficients are authored POC choices. Ranges describe observed strength at
collection time, not guaranteed current strength or calibrated probabilities.
"""
from copy import deepcopy
from . import grid

PROFILES={'line':35,'scout':80,'spy':95}

def estimate(enemy, quality, distance):
    quantum=40 if quality<25 else 20 if quality<50 else 10 if quality<80 else 5
    center=(enemy['strength']//quantum)*quantum+quantum//2
    strength=[max(1,center-quantum),center+quantum]
    kind=enemy.get('unit_type','infantry') if quality>=25 else 'unidentified troops'
    weapons=(enemy.get('weapon_class','long arms') if quality>=80 and distance<=2
             else 'long arms' if quality>=50 else 'not established')
    confidence='low' if quality<25 else 'moderate' if quality<50 else 'good' if quality<80 else 'high'
    return {'strength_range':strength,'composition':{'type':kind,'weapons':weapons},
            'confidence':confidence,'quality':quality,
            'estimate':f'{strength[0]}–{strength[1]} troops · {kind}'}

def scan(s):
    """Per-observer evidence. Re-scanning a tick refreshes geometry, not exposure."""
    observers=[u for u in s['units'] if u['strength']>0]
    # Spies are aggregate observation assets, not combatants or omniscient reports.
    observers += [a for a in s.get('intel_assets',[]) if a.get('status')=='observing']
    memory=s.setdefault('recon_memory',{})
    sightings={}
    for observer in sorted(observers,key=lambda u:u['id']):
        role=observer.get('recon_role','line'); skill=observer.get('recon_skill',PROFILES[role])
        own=memory.setdefault(observer['id'],{}); contacts=[]
        for enemy in sorted(s['units'],key=lambda u:u['id']):
            if enemy['side']==observer['side'] or enemy['strength']<=0: continue
            distance=grid.distance(observer['pos'],enemy['pos'])
            if distance>observer.get('observation_range',7) or not grid.visible(s['cells'],observer['pos'],enemy['pos']):continue
            old=own.get(enemy['id']); gap=s['turn']-old['last_seen'] if old else 99
            exposure=(old['exposure'] if old and gap==0 else
                      min(12,old['exposure']+1) if old and gap==1 else 1)
            cover=s['cells'][grid.key(enemy['pos'])]['cover']
            quality=8+skill//3+exposure*(2+skill//15)-distance*2-cover//10-observer.get('suppression',0)//5
            cap=90 if distance<=2 else 75 if distance<=4 else 45
            quality=max(5,min(cap,quality))
            contact={'id':enemy['id'],'pos':deepcopy(enemy['pos']),'side':enemy['side'],'status':'observed',
                     **estimate(enemy,quality,distance),'observer_id':observer['id'],'observer_role':role,
                     'exposure_intervals':exposure,'report_delay':observer.get('report_delay',3 if role=='spy' else 1)}
            own[enemy['id']]={'last_seen':s['turn'],'exposure':exposure}
            contacts.append(contact)
        sightings[observer['id']]=contacts
    return sightings

def reports(s,sightings):
    """Send prompt warning plus the best estimate when it comes through a slower source."""
    observers={u['id']:u for u in s['units']+s.get('intel_assets',[])}
    grouped={}
    for observer_id,contacts in sightings.items():
        side=observers[observer_id]['side']
        for c in contacts:grouped.setdefault((side,c['id']),[]).append(c)
    result=[]
    for (side,_),contacts in sorted(grouped.items()):
        fastest=min(contacts,key=lambda c:(c['report_delay'],-c['quality'],c['observer_id']))
        best=max(contacts,key=lambda c:(c['quality'],-c['report_delay'],c['observer_id']))
        result.append((side,deepcopy(fastest)))
        if best['observer_id']!=fastest['observer_id']:result.append((side,deepcopy(best)))
    return result

def merge_contact(prior, incoming, observed_turn, received_turn):
    """Fresh position/counts, plus separately dated identification evidence.

A slower spy may improve identification without moving a fresh contact backward
or replacing its strength estimate with an older count.
"""
    fresh={**deepcopy(incoming),'observed_turn':observed_turn,'received_turn':received_turn}
    stamp=lambda c:(c['observed_turn'],c.get('phase',''),c.get('quality',0))
    stale=bool(prior and stamp(prior)>stamp(fresh))
    result=deepcopy(prior) if stale else fresh
    evidence=deepcopy(prior.get('identification',{})) if prior else {}
    for field,unknown in (('type','unidentified troops'),('weapons','not established')):
        old=evidence.get(field)
        if old and received_turn-old['observed_turn']>6:old=None
        value=incoming.get('composition',{}).get(field,unknown)
        candidate=None if value==unknown else {'value':value,'quality':incoming.get('quality',0),
            'observed_turn':observed_turn,'observer_id':incoming.get('observer_id'),
            'observer_role':incoming.get('observer_role')}
        if candidate and received_turn-observed_turn>6:candidate=None
        best=max([v for v in (old,candidate) if v],key=lambda v:(v['quality'],v['observed_turn']),default=None)
        if best:evidence[field]=best
        else:evidence.pop(field,None)
        result.setdefault('composition',{})[field]=best['value'] if best else unknown
    result['identification']=evidence
    lo,hi=result['strength_range']
    result['estimate']=f'{lo}–{hi} troops · {result["composition"]["type"]}'
    return result,stale
