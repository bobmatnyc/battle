"""Authored map features and persistent fieldworks; not surveyed historical data."""
from copy import deepcopy
from . import grid,recon


def setup(s,layout):
    """Applies a scenario's authored roads, buildings and works to ``s``.

    ``layout`` holds ``roads``, ``buildings`` and ``works`` lists (scenario
    entry data); each is copied, so the entry stays unchanged.
    """
    roads=deepcopy(list(layout['roads']))
    buildings=deepcopy(list(layout['buildings']))
    works=deepcopy(list(layout['works']))
    s['map_features']=roads+buildings+works
    for f in s['map_features']:f.update(provenance='authored-poc',briefed=True)
    for road in roads:
        route=[]
        for a,b in zip(road['points'],road['points'][1:]):route.extend(grid.line(a,b) if not route else grid.line(a,b)[1:])
        road['hexes']=route
        for a,b in zip(route,route[1:]):
            for origin,dest in ((a,b),(b,a)):
                c=s['cells'][grid.key(origin)];c.setdefault('road_neighbors',[])
                if dest not in c['road_neighbors']:c['road_neighbors'].append(dest)
    for f in buildings:
        c=s['cells'][grid.key(f['pos'])];c.update(cover=max(c['cover'],f['cover']),obstacle_height=f['height'],building=f['id'],move_cost=max(c['move_cost'],140))
    for f in works:
        c=s['cells'][grid.key(f['pos'])];c['cover']=max(c['cover'],f['cover'])
    if any(f.get('openings') for f in buildings):
        from . import gates
        gates.setup(s,buildings)  # poc-10 walls and gates, briefed in their initial state.
    s['briefing_cells']=deepcopy(s['cells'])
    s['feature_reports']={side:{f['id']:dict(deepcopy(f),observed_turn=0,received_turn=0) for f in s['map_features']} for side in s['contacts']}
    s['feature_observations']={}


def known(s,side):
    return deepcopy(list(s['feature_reports'][side].values()))


def receive(s,report):
    for f in report['data']['features']:
        prior=s['feature_reports'][report['side']].get(f['id'])
        if not prior or prior.get('observed_turn',-1)<=report['observed_turn']:
            s['feature_reports'][report['side']][f['id']]=dict(deepcopy(f),observed_turn=report['observed_turn'],received_turn=s['turn'])


def report(s):
    from . import engine
    for u in sorted(s['units'],key=lambda u:u['id']):
        if u['strength']<=0:continue
        memory=s['feature_observations'].setdefault(u['id'],{})
        observed=[]
        for f in s['map_features']:
            # poc-10: gate state is observed like fieldworks; docs/research/53: so is a bridge's.
            gate=bool(f.get('openings')) or f['kind']=='bridge'
            if not gate and (f['kind']!='fortification' or f['briefed']):continue
            # docs/research/53: a night observation_range also limits what is seen.
            if grid.distance(u['pos'],f['pos'])>3 or not recon.sees(s,u,f['pos']):continue
            if memory.get(f['id'],0 if gate else None)==f['updated_turn']:continue
            memory[f['id']]=f['updated_turn'];observed.append(deepcopy(f))
        if observed:
            works=[f for f in observed if not f.get('openings') and f['kind']!='bridge']
            parts=['fieldworks observed at '+', '.join(str(f['pos']) for f in works)] if works else []
            parts+=[f'{f["name"]} gate {o["state"]}' for f in observed if f.get('openings') for o in f['openings']]
            parts+=[f'{f["name"]} {f["state"]}' for f in observed if f['kind']=='bridge']
            engine.enqueue(s,u['side'],f'{u["id"]} to headquarters: '+'; '.join(parts)+'.',
                           data={'features':observed},kind='terrain',sender=u['id'])


def dig(s,u,unsafe):
    from . import engine,orders
    c=s['cells'][grid.key(u['pos'])]
    works=next((f for f in s['map_features'] if f['kind']=='fortification' and f['pos']==u['pos']),None)
    if works and works['progress']==100:
        orders.complete(s,u,'The existing fieldworks are ready; hold this position.');return
    if c.get('building') or c.get('road_neighbors'):
        orders.status(s,u,'failed','The occupied building or road is unsuitable for excavation; choose other ground.')
        u.update(stance='hold',target=None);return
    if u.get('tools',0)<=0:
        orders.status(s,u,'failed','The detachment has no entrenching tools.')
        u.update(stance='hold',target=None);return
    if unsafe:
        orders.status(s,u,'blocked','Work suspended; attend to the enemy and protect the detachment.');return
    if u['fatigue']>=80:
        orders.status(s,u,'blocked','The men are exhausted; rest is required before work can continue.');return
    orders.status(s,u,'active','The men are strengthening the present position.')
    if not works:
        works={'id':'works-'+grid.key(u['pos']),'kind':'fortification','name':'Hasty fieldworks','pos':list(u['pos']),
               'base_cover':c['cover'],'cover':c['cover'],'progress':0,'effort':0,
               'required':800 if c['terrain']=='rocky' else 400,'updated_turn':s['turn'],
               'briefed':False,'provenance':'simulation-built'}
        s['map_features'].append(works)
    before=works['effort'];effort=min(u['strength'],u['tools']*2,works['required']-before)
    works['effort']+=effort;works['progress']=works['effort']*100//works['required'];works['updated_turn']=s['turn']
    works['cover']=max(works['base_cover'],min(70,works['base_cover']+30*works['effort']//works['required']))
    c['cover']=works['cover'];u['fatigue']=min(100,u['fatigue']+2)
    engine.emit(s,'fieldworks_progress',unit_id=u['id'],order_version=u['order_version'],feature_id=works['id'],pos=list(u['pos']),
                labor=effort,effort_before=before,effort_after=works['effort'],progress=works['progress'],cover=works['cover'],fatigue=u['fatigue'])
    if works['progress']==100:orders.complete(s,u,'The fieldworks are ready; we hold the strengthened position.')
