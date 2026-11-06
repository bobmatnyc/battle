"""Bounded standing commander policy: local evidence, mission, self-preservation.

poc-12 (docs/research/45): as tactics_v8, except that an assault on a gated
compound (``assault``) does not halt for an enemy within 5 hexes. Withdrawal
on the unit's own condition and rout are unchanged. tactics_v8 serves earlier
editions.
"""
from . import gates,grid,standing

POLICY='standing-contact-v3'


def assault(s,u):
    """Why: an attack on walls must close with the defenders it can see.
    What: True when ``u`` is on a ``move`` order whose destination lies in a
    gated compound and that it has not reached, whatever its side.
    Test: `test_assault_into_the_compound_continues_within_five_hexes`."""
    target=u.get('target')
    return (u.get('stance')=='move' and target is not None and list(u['pos'])!=list(target)
            and gates.compound_of(s,target) is not None)

def decide(s,u,contacts):
    doctrine=standing.profile(u)
    nearby=[c for c in contacts if grid.distance(u['pos'],c['pos'])<=5]
    attacked=s['turn']-u.get('last_attacked_turn',-99)<=1
    reason='No enemy within effective range; maintain the assigned mission.'
    action='continue' if u.get('target') is not None else 'hold'
    target=None
    if u['status']=='routed':
        action='route';reason='Formation broken; fall back toward headquarters.'
    elif nearby or attacked or (u.get('local_action')=='withdraw' and s['turn']<u.get('withdraw_until',0)):
        reliable=[c for c in nearby if c['quality']>=25]
        enemy_strength=sum(sum(c['strength_range'])/2 for c in reliable)
        depleted=attacked and u['strength']*2<u['initial']
        triggers=[]
        if u['morale']<doctrine['morale_floor']:triggers.append('morale is failing')
        if u['suppression']>=doctrine['suppression_limit']:triggers.append('incoming fire is pinning the detachment')
        if u['ammo']<u['strength']*doctrine['reserve_volleys']:triggers.append('ammunition is below the standing reserve')
        if depleted:triggers.append('recent fire has found a depleted formation')
        if enemy_strength>u['strength']*doctrine['enemy_ratio'] or (doctrine['id']=='screen' and enemy_strength>=u['strength']):triggers.append('credible sightings indicate a much stronger enemy')
        if u.get('recon_role')=='scout' and enemy_strength>=u['strength'] and any(grid.distance(u['pos'],c['pos'])<=3 for c in nearby):triggers.append('the scouting mission calls for avoiding a close, costly engagement')
        if u.get('local_action')=='withdraw' and s['turn']<u.get('withdraw_until',0):triggers.append('the withdrawal must be completed before reconsidering the mission')
        pressing=not triggers and assault(s,u)
        action='withdraw' if triggers else 'continue' if pressing else 'defend'
        reason=('We are withdrawing because '+ '; '.join(triggers)+'.' if triggers
                else 'Enemy within effective range; pressing the assault on the walls and returning fire.' if pressing
                else 'Enemy within effective range; halt locally, use cover and return fire.')
        # Movement orders remain the mission. A local reaction temporarily overrides
        # execution without erasing the destination or issuing a fictitious HQ order.
        visible_friends={grid.key(f['pos']) for f in s['units'] if f['side']==u['side'] and f['id']!=u['id'] and f['strength']>0 and grid.visible(s['cells'],u['pos'],f['pos'])}
        visible_enemies={grid.key(c['pos']) for c in contacts}
        candidates=[p for p in grid.neighbors(u['pos']) if grid.key(p) not in visible_friends|visible_enemies]
        threats=[c['pos'] for c in nearby]
        distance=lambda p:min((grid.distance(p,e) for e in threats),default=0)
        cover=lambda p:s['cells'][grid.key(p)]['cover']
        if action=='withdraw':
            if threats:
                candidates=[p for p in candidates if distance(p)>distance(u['pos']) or (distance(p)==distance(u['pos']) and cover(p)>cover(u['pos']))]
                score=lambda p:(distance(p),cover(p),-grid.distance(p,s['hq'][u['side']]),-p[1],-p[0])
            else:
                # Fire without a located shooter: fall toward known HQ, never infer the attacker location.
                candidates=[p for p in candidates if grid.distance(p,s['hq'][u['side']])<grid.distance(u['pos'],s['hq'][u['side']])]
                score=lambda p:(cover(p),-grid.distance(p,s['hq'][u['side']]),-p[1],-p[0])
            if candidates:target=max(candidates,key=score)
            else:reason+=' No safer adjacent ground is known; defend while seeking a way out.'
        elif nearby and not pressing:
            candidates=[p for p in candidates if cover(p)>=cover(u['pos'])+15 and distance(p)>=distance(u['pos'])]
            if candidates:
                action='take_cover';target=max(candidates,key=lambda p:(cover(p),distance(p),-p[1],-p[0]))
                reason='Nearby cover is better and does not close with the observed enemy.'
    elif contacts:
        reason='Enemy sighted beyond effective range; observe, report and maintain mission.'
        if action=='hold':action='observe'
    return {'policy':POLICY,'action':action,'reason':reason,'target':target,
            'under_fire':attacked,'contacts':[{'id':c['id'],'pos':c['pos'],'strength_range':c['strength_range'],'quality':c['quality']} for c in contacts],
            'mission_version':u['order_version'],'standing_profile':doctrine['id'],'standing_version':u.get('standing_version',0)}
