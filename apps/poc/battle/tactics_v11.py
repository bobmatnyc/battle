"""Bounded standing commander policy: local evidence, mission, self-preservation.

docs/research/55: as tactics_v10, except that a contact makes a unit halt and
react within the longer of the unit's own weapon range and the contact's
range, read from what the unit observes (``recon.estimate``), so a short-range
unit no longer walks into a longer-range enemy it can see. docs/research/58:
a unit that declares ``press_assault`` keeps to its move order in open ground
as an assault on walls does. Served only to a
``poc-13`` snapshot whose entry selects it (``s['tactics']``); tactics_v10
stays frozen for every other ``poc-13`` battle.
"""
from . import gates,grid,recon,standing

POLICY='standing-contact-v4'


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

def presses(u):
    """Why: an attack in open ground halted at its first unidentified contact,
    which tactics_v11 counts at the table's longest range (docs/research/58).
    What: True when ``u`` declares ``press_assault`` and is on a ``move`` order
    with a destination. Reads only the unit, never enemy truth or contacts.
    Test: `test_with_the_key_the_unit_presses_toward_its_objective`,
    `test_the_key_needs_a_move_order`."""
    return u.get('press_assault') is True and u.get('stance')=='move' and u.get('target') is not None

def own_range(s,u):
    """The farthest hex ``u`` fires at: its class's ``range_hexes`` in the
    snapshot's weapon table, else 5 (the rifle baseline, as tactics_v10)."""
    weapon=s.get('weapon_rules',{}).get(u.get('weapon_class'))
    return weapon['range_hexes'] if weapon else 5

def contact_range(s,c):
    """Why: an observer knows a contact's weapon only as far as it has made it
    out, never from the enemy's true inventory.
    What: the range of the class ``c['composition']['weapons']`` names when the
    weapon table lists it; for an unidentified contact ('long arms', 'not
    established') the longest range in the table, the worst case the briefed
    rules allow. Reads nothing but the contact and the table.
    Test: `test_an_unidentified_contact_counts_at_the_longest_range_in_the_table`."""
    table=s['weapon_rules']
    named=table.get(c.get('composition',{}).get('weapons'))
    return named['range_hexes'] if named else max(w['range_hexes'] for w in table.values())

def threat_range(s,u,contacts):
    """Why: with mixed weapon tables a short-range unit judged danger by its own
    range and closed into a longer-range enemy's fire (docs/research/48 §1).
    What: the distance at which ``contacts`` (the enemies ``u`` itself observes
    this interval) make it halt and react: 5 hexes without a weapon table;
    otherwise the longer of ``u``'s own range and the longest
    ``contact_range`` among them. An enemy ``u`` cannot observe is not in
    ``contacts`` and so never changes the result.
    Test: `test_a_short_range_unit_uses_an_identified_enemys_longer_range`,
    `test_the_units_own_longer_range_is_kept`,
    `test_without_weapon_rules_the_threat_range_stays_five`,
    `test_a_hidden_longer_range_enemy_does_not_change_the_decision`."""
    if not s.get('weapon_rules'):return 5
    return max([own_range(s,u)]+[contact_range(s,c) for c in contacts])

def decide(s,u,contacts):
    doctrine=standing.profile(u)
    # docs/research/55: each observed contact counts within the longer of the
    # unit's own range and that contact's range; without weapon_rules, 5 hexes.
    nearby=[c for c in contacts if grid.distance(u['pos'],c['pos'])<=threat_range(s,u,[c])]
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
        walls=not triggers and assault(s,u)
        pressing=walls or (not triggers and presses(u))  # docs/research/58: declared only.
        action='withdraw' if triggers else 'continue' if pressing else 'defend'
        reason=('We are withdrawing because '+ '; '.join(triggers)+'.' if triggers
                else 'Enemy within effective range; pressing the assault on the walls and returning fire.' if walls
                else 'Enemy within effective range; pressing the assault toward the objective and returning fire.' if pressing
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
