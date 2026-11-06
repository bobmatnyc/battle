"""Read-only staff assessment of an authorized commander view.

Never accepts a ground-truth state. No inference, mutation, or clock advancement.
"""
from . import standing

VERSION='troop-assessment-v1'

def assess(view):
    if view.get('view_mode')=='god':raise ValueError('Staff assessment requires a commander view.')
    rows=[]
    for u in view['units']:
        if u['side']!=view['side'] or u.get('status')=='merged':continue
        strength=u['strength'];age=max(0,view['turn']-u['observed_turn'])*view['seconds_per_turn']
        concerns=[]
        if u['status'] in ('lost','routed'):concerns.append('Reported unable to carry out fresh orders.')
        if strength*2<u['initial']:concerns.append('Less than half of the formation’s assigned strength remains.')
        if u['ammo']<strength*10:concerns.append('Fewer than ten volleys of ammunition reported.')
        if u['morale']<60:concerns.append('Morale is shaken; heavy pressure may force withdrawal.')
        if u['suppression']>=50:concerns.append('Incoming fire is restricting local action.')
        if u['fatigue']>=55:concerns.append('The men need rest when safely clear of contact.')
        if age:concerns.append(f'This report is {age} seconds old; conditions may have changed.')
        rec=standing.recommend(u)
        rows.append({'id':u['id'],'name':u['name'],'strength':strength,'initial':u['initial'],
                     'ammo':u['ammo'],'volleys':u['ammo']//strength if strength else None,
                     'morale':u['morale'],'suppression':u['suppression'],'fatigue':u['fatigue'],
                     'skill':u.get('skill'),'role':u.get('recon_role'),'weapons':u.get('weapon_class'),
                     'status':u['status'],'observed_turn':u['observed_turn'],'received_turn':u['received_turn'],
                     'age_seconds':age,'mission':u['stance'],'target':u.get('target'),
                     'standing_profile':u.get('standing_profile'),'standing_version':u.get('standing_version'),
                     'concerns':concerns,'recommendation':rec,
                     'pending_standing':[o for o in view.get('standing_orders',[]) if o['unit_id']==u['id'] and o['status']=='awaiting_ack']})
    active=[u for u in rows if u['status'] not in ('lost','routed')]
    return {'version':VERSION,'turn':view['turn'],'revision':view['revision'],'side':view['side'],
            'basis':'Headquarters reports and direct observation of the command detachment. Totals combine reports of different ages; they are not current battlefield truth.',
            'summary':{'formations':len(rows),'available_formations':len(active),'reported_strength':sum(u['strength'] for u in rows),
                       'assigned_strength':sum(u['initial'] for u in rows),'reported_ammo':sum(u['ammo'] for u in rows),
                       'oldest_report_seconds':max((u['age_seconds'] for u in rows),default=0)},
            'contacts':[{'id':c['id'],'strength_range':c.get('strength_range'),'confidence':c.get('confidence'),
                         'age_seconds':c['age']*view['seconds_per_turn']} for c in view['contacts']],
            'units':rows,'standing_templates':standing.catalog(),
            'command_operational':view.get('command',{}).get('operational',False),
            'limitations':'Authored readiness heuristics, not a historical combat rating or victory prediction. Enemy sightings may overlap or be stale; unseen troops are unknown.'}
