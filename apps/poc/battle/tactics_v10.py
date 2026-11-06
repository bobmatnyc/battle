"""Bounded standing commander policy: local evidence, mission, self-preservation.

poc-13 (docs/research/46): as tactics_v9, except that the assault check reads
only contacts young enough for the commander view (``recon.CONTACT_MAX_AGE``),
and a unit never seeks cover or withdraws onto impassable water. tactics_v9
serves poc-12; tactics_v8 earlier editions.
"""
from . import gates,grid,recon,standing

POLICY='standing-contact-v3'


def assault(s,u):
    """Why: an attack on walls must close with the defenders it can see; a
    defender moving about its own walls must not.
    What: True when ``u`` is on a ``move`` order whose destination lies in a
    gated compound that ``u`` stands outside, and that compound either holds
    its side's attack objective or holds an enemy its headquarters knows of
    (``s['contacts']``, never ground truth) observed at most
    ``recon.CONTACT_MAX_AGE`` intervals ago, the age the commander view shows.
    Test: `test_seven_turn_old_contact_no_longer_triggers_the_assault_exemption`,
    `test_fresh_contact_still_makes_an_assault`."""
    target=u.get('target')
    if u.get('stance')!='move' or target is None:return False
    f=gates.compound_of(s,target)
    if f is None or list(u['pos']) in f['compound']:return False
    attacker=any(x['id']==u['side'] and x.get('role')=='attacker' for x in s.get('sides',()))
    if attacker and list(s['objective']) in f['compound']:return True
    inside={grid.key(p) for p in f['compound']}
    return any(grid.key(c['pos']) in inside for c in s['contacts'].get(u['side'],{}).values()
               if s['turn']-c['observed_turn']<=recon.CONTACT_MAX_AGE)

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
        candidates=[p for p in grid.neighbors(u['pos']) if grid.key(p) not in visible_friends|visible_enemies
                    and grid.passable(s['cells'][grid.key(p)])]
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
