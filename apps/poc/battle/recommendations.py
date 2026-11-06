"""Local commander advice, delivered by existing transport; never automatic orders."""
from copy import deepcopy
from . import grid

POLICY='commander-advice-v1'
LIFETIME=12  # Six minutes of simulation time, including courier travel.
COOLDOWN=16


def current_status(s,r):
    if r['status'] in ('accepted','dismissed'):return r['status']
    if s['turn']>=r['expires_turn']:return 'expired'
    if any(o['unit_id']==r['unit_id'] and o['version']>r['mission_version'] for o in s['orders']):return 'superseded'
    return r['status']


def visible(s,side):
    return [dict(deepcopy(r),status=current_status(s,r)) for r in s.get('recommendations',[])
            if r['side']==side and 'received_turn' in r]


def propose(s,u,contacts):
    nearby=[c for c in contacts if grid.distance(u['pos'],c['pos'])<=5]
    unsafe=bool(nearby) or s['turn']-u.get('last_attacked_turn',-99)<=1
    stance=None;target=None;reason=None
    if u.get('local_action') in ('withdraw','fall_back') and u['stance']!='retreat':
        stance='retreat';target=list(s['rally_points'][u['side']])
        reason='General, I recommend falling back to our rallying ground. The present position is becoming untenable.'
    elif u['ammo']<u['strength']*10 and u['stance']!='resupply':
        stance='resupply';reason='General, our cartridge boxes run low. I recommend replenishing ammunition before further action.'
    elif u['fatigue']>=55 and not unsafe and u['stance']!='rest':
        stance='rest';reason='General, the men are fatigued. I recommend a halt to rest them while keeping watch.'
    elif s['turn']>=2 and u['stance']=='hold' and not unsafe and u['tools']>0 and u['fatigue']<55:
        cell=s['cells'][grid.key(u['pos'])]
        work=next((f for f in s['map_features'] if f['kind']=='fortification' and f['pos']==u['pos']),None)
        if not cell.get('building') and not cell.get('road_neighbors') and (not work or work['progress']<100):
            stance='dig_in';reason='General, while the ground is quiet, I recommend strengthening this position with fieldworks.'
    if not stance:return None
    return {'proposal':{'unit_id':u['id'],'stance':stance,'destination':target},'text':reason,
            'evidence':{'pos':list(u['pos']),'strength':u['strength'],'ammo':u['ammo'],'fatigue':u['fatigue'],
                        'morale':u['morale'],'local_action':u.get('local_action'),'contact_ids':[c['id'] for c in nearby]}}


def generate(s,sightings):
    from . import engine
    for r in s['recommendations']:
        value=current_status(s,r)
        if value!=r['status']:
            r['status']=value
            engine.emit(s,'recommendation_'+value,recommendation_id=r['id'],unit_id=r['unit_id'])
    for u in sorted(s['units'],key=lambda u:u['id']):
        if u['status'] in ('routed','lost','merged'):continue
        # Local commanders know their effective mission, not undelivered HQ instructions.
        prior=[r for r in s['recommendations'] if r['unit_id']==u['id']]
        if prior and s['turn']-prior[-1]['created_turn']<COOLDOWN:continue
        suggestion=propose(s,u,sightings.get(u['id'],[]))
        if not suggestion:continue
        r={'id':f'A{len(s["recommendations"])+1}','unit_id':u['id'],'side':u['side'],
           'created_turn':s['turn'],'expires_turn':s['turn']+LIFETIME,'mission_version':u['order_version'],
           'policy':POLICY,'status':'en_route',**suggestion}
        s['recommendations'].append(r)
        engine.emit(s,'recommendation_created',recommendation=deepcopy(r))
        engine.enqueue(s,u['side'],r['text'],data={'recommendation_id':r['id']},kind='recommendation',sender=u['id'])


def receive(s,report):
    from . import engine
    r=next(r for r in s['recommendations'] if r['id']==report['data']['recommendation_id'])
    r['received_turn']=s['turn']
    status=current_status(s,r)
    r['status']='delivered' if status=='en_route' else status
    engine.emit(s,'recommendation_received',recommendation_id=r['id'],unit_id=r['unit_id'],status=r['status'],observed_turn=r['created_turn'])


def respond(s,side,rid,response):
    from . import engine
    if s.get('rules') not in ('poc-8','poc-9','poc-10','poc-11','poc-12','poc-13'):raise ValueError('Use Reset for commander recommendations.')
    r=next((r for r in s['recommendations'] if r['id']==rid and r['side']==side and 'received_turn' in r),None)
    if not r:raise ValueError('No delivered recommendation with that ID is available.')
    if response not in ('accept','dismiss'):raise ValueError('Choose accept or dismiss.')
    state=current_status(s,r)
    if state in ('accepted','dismissed'):raise ValueError('This recommendation has already been handled.')
    if response=='accept':
        if state!='delivered':raise ValueError('This advice has expired or newer orders have superseded it.')
        ticket=engine.issue(s,side,r['proposal'],'commander-recommendation')
        r.update(status='accepted',order_id=ticket['id'])
    else:r['status']='dismissed'
    r['responded_turn']=s['turn']
    engine.emit(s,'recommendation_'+r['status'],recommendation_id=r['id'],unit_id=r['unit_id'],order_id=r.get('order_id'))
