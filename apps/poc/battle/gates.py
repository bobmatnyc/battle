"""Gates in walled buildings (poc-10): openings on hex edges and their state.

Why: a walled compound turns on whether its gate is shut (docs/research/37,
Option A). What: a building feature may declare a ``compound`` (its hexes)
and ``openings``, each on the edge between an ``inside`` compound hex (the
gateway) and an ``outside`` neighbour. Every other edge of the compound is a
wall. Movement and couriers cross an opening only while it is ``open``,
``closing`` or ``forced``. The state belongs to the ground, like fieldworks.

Labour, barring and forcing values come from the scenario entry's authored
``gates`` and are stored in the snapshot as ``gate_rules``. They are POC
sensitivity parameters; no source gives them. Design: docs/research/41.
poc-11 adds ``push``, attackers carrying a gateway held by the enemy, with
authored ``push_rules`` (docs/research/44).
"""
from . import grid

STATES = ('open', 'closing', 'closed', 'barred', 'forced')
PASSABLE = ('open', 'closing', 'forced')
CLOSABLE = ('open', 'closing', 'forced')
REFUSING = ('routed', 'lost', 'merged')
TEMPLATE = {
    'id': 'close_gate', 'label': 'Close the gate', 'destination': 'none',
    'intent': 'Shut the gate of the walls you hold, then bar it. Keep the gateway and report when it is secure.',
    'effect': 'Work takes labour and time and continues under fire. The gate cannot shut while the enemy stands in the gateway. Enemy troops already inside are cut off.'}
STANDING = {
    'id': 'close_on_breach', 'label': 'Close the gate on a breach',
    'intent': 'Hold the walls firmly. If the enemy breaks in, close and bar the gate without waiting for orders.',
    'morale_floor': 35, 'suppression_limit': 85, 'enemy_ratio': 3.5, 'reserve_volleys': 1, 'fire_range': 5}


def gated(s):
    """Building features that declare openings (only poc-10 snapshots have any)."""
    return [f for f in s.get('map_features', []) if f.get('openings')]


def present(s):
    """True when the battle has a gate, so the gate order and standing order apply."""
    return bool(gated(s))


def compound_of(s, pos):
    """The gated building whose compound contains ``pos``, or None."""
    return next((f for f in gated(s) if list(pos) in f['compound']), None)


def setup(s, buildings):
    """Prepares the declared openings of ``buildings`` and draws the walls."""
    for f in buildings:
        if not f.get('openings'):continue
        f['compound'] = [list(p) for p in f.get('compound', [f['pos']])]
        f['updated_turn'] = 0
        for o in f['openings']:
            o.update(inside=list(o['inside']), outside=list(o['outside']), effort=0, bar_effort=0, force_effort=0)
    walls(s)


def walls(s):
    """Why: a shut gate must stop troops and couriers alike.
    What: rewrites every cell's ``walls`` (neighbours that cannot be entered
    from it) from the compounds and their opening states; ``grid.path``
    skips those edges. Cells of battles without gates get no ``walls``.
    Test: `test_closed_gate_cuts_off_attackers_inside`."""
    features = gated(s)
    if not features:return
    for c in s['cells'].values():c.pop('walls', None)
    _draw(s['cells'], features)


def _draw(cells, features):
    for f in features:
        inside = {grid.key(p) for p in f['compound']}
        gaps = {(grid.key(o['inside']), grid.key(o['outside'])) for o in f['openings'] if o['state'] in PASSABLE}
        for p in f['compound']:
            for n in grid.neighbors(p):
                if grid.key(n) in inside or (grid.key(p), grid.key(n)) in gaps:continue
                for a, b in ((p, n), (n, p)):
                    c = cells[grid.key(a)]
                    if b not in c.setdefault('walls', []):c['walls'].append(list(b))


def known_cells(s, side):
    """Why: headquarters must not learn a gate's state from its own estimates.
    What: a copy of the cells whose ``walls`` come from the gate states
    ``side`` knows (briefed or reported), not the true ones. None in a battle
    without gates, where the live cells carry no hidden walls.
    Test: `test_delivery_estimate_ignores_a_gate_shut_without_a_report`."""
    if not present(s):return None
    cells = {k: {f: v for f, v in c.items() if f != 'walls'} for k, c in s['cells'].items()}
    _draw(cells, [f for f in s['feature_reports'][side].values() if f.get('openings')])
    return cells


def across_wall(cells, a, b):
    """True when ``cells`` show a wall or shut gate on the edge from ``a`` to ``b``."""
    return list(b) in cells[grid.key(a)].get('walls', ())


def approach(s, pos, target):
    """Why: troops ordered into a shut compound must march to its gate to force it.
    What: for a ``target`` inside a gated compound that ``pos`` lies outside,
    the outside hex of the nearest opening (by distance, then id); else None.
    Test: `test_attackers_march_to_a_closed_gate_and_force_it`."""
    f = compound_of(s, target)
    if not f or list(pos) in f['compound']:return None
    return min(f['openings'], key=lambda o: (grid.distance(pos, o['outside']), o['id']))['outside']


def sealed(f):
    return all(o['state'] not in PASSABLE for o in f['openings'])


def _inside(s, f, side=None):
    keys = {grid.key(p) for p in f['compound']}
    return [u for u in sorted(s['units'], key=lambda x: x['id'])
            if u['strength'] > 0 and grid.key(u['pos']) in keys and (side is None or u['side'] != side)]


def _transition(s, f, o, new, unit, labour, pushers=()):
    from . import engine
    before = o['state']
    o['state'] = new
    o['updated_turn'] = f['updated_turn'] = s['turn']
    if new == 'closing':o['effort'] = 0
    if new == 'closed':o.update(bar_effort=0, force_effort=0)
    walls(s)
    engine.emit(s, 'gate_state', feature_id=f['id'], opening_id=o['id'], before=before, after=new,
                unit_id=unit['id'], order_version=unit.get('order_version'), labour=labour,
                effort=o['effort'], pushers=list(pushers),
                units_inside=[u['id'] for u in _inside(s, f)],
                units_outside=[u['id'] for u in s['units'] if u['strength'] > 0 and u['pos'] == o['outside']])
    if new in ('closed', 'barred') and sealed(f):
        trapped = [u for u in _inside(s, f, side=unit['side']) if not u.get('cut_off')]
        for u in trapped:
            u['cut_off'] = {'feature_id': f['id'], 'opening_id': o['id'], 'turn': s['turn']}
        if trapped:
            engine.emit(s, 'units_cut_off', feature_id=f['id'], opening_id=o['id'], unit_ids=[u['id'] for u in trapped])
            # Physical reports only: the courier must find a way out of the walls.
            for u in trapped:
                engine.enqueue(s, u['side'], f'{u["id"]} to headquarters: the gate has shut behind us; we are cut off inside the walls.',
                               kind='reaction', sender=u['id'])
    if new in PASSABLE:
        freed = [u for u in s['units'] if (u.get('cut_off') or {}).get('feature_id') == f['id']]
        for u in freed:u.pop('cut_off')
        if freed:engine.emit(s, 'units_reconnected', feature_id=f['id'], opening_id=o['id'], unit_ids=[u['id'] for u in freed])


def progress(s):
    """Why: the gate is shut by men, under fire, and forced by men.
    What: once per poc-10 interval, after fire: fires the standing
    close-on-breach instruction, applies closing and barring labour of every
    unit on a ``close_gate`` mission, applies the forcing labour of units at a
    closed gate whose ordered destination lies inside, and fails resupply of
    cut-off units. A no-op without gates.
    Test: `test_gate_opens_to_closing_when_work_starts`,
    `test_contact_in_gateway_stops_completion_until_it_clears`,
    `test_standing_order_closes_the_gate_on_a_breach`."""
    if not present(s):return
    rules = s['gate_rules']
    _standing(s)
    for u in sorted(s['units'], key=lambda x: x['id']):
        mission = u.get('mission_result') or {}
        if (u['stance'] == 'close_gate' and mission.get('status') in ('active', 'blocked')
                and u['strength'] > 0 and u['status'] not in REFUSING):
            _close(s, u, rules)
    _force(s, rules)
    _supply(s)


def _standing(s):
    from . import engine
    for u in sorted(s['units'], key=lambda x: x['id']):
        if u.get('standing_profile') != STANDING['id'] or u['strength'] <= 0 or u['status'] in REFUSING:continue
        f = compound_of(s, u['pos'])
        if not f or not any(o['state'] in CLOSABLE for o in f['openings']):continue
        if u['stance'] == 'close_gate' and (u.get('mission_result') or {}).get('status') in ('active', 'blocked'):continue
        breach = _inside(s, f, side=u['side'])
        if not breach:continue
        reason = 'Standing instructions: the enemy is inside the walls; closing the gate.'
        u.update(stance='close_gate', target=None)
        u['mission_result'] = {'template': 'close_gate', 'status': 'active', 'order_version': u['order_version'],
                               'started_turn': s['turn'], 'updated_turn': s['turn'], 'reason': reason,
                               'standing_version': u['standing_version']}
        engine.emit(s, 'standing_gate_close', unit_id=u['id'], standing_version=u['standing_version'],
                    feature_id=f['id'], breach=[e['id'] for e in breach])
        engine.enqueue(s, u['side'], f'{u["id"]} to headquarters: {reason}', kind='mission', sender=u['id'])


def _close(s, u, rules):
    from . import engine, orders
    f = compound_of(s, u['pos'])
    if not f:
        orders.status(s, u, 'failed', 'There is no gate within these walls to close.')
        u.update(stance='hold', target=None);return
    nearest = lambda options: min(options, key=lambda o: (grid.distance(u['pos'], o['inside']), o['id']))
    open_ = [o for o in f['openings'] if o['state'] in CLOSABLE]
    shut = [o for o in f['openings'] if o['state'] == 'closed']
    if not open_ and not shut:
        orders.complete(s, u, 'The gate is shut and barred; holding the gateway.');return
    labour = min(u['strength'], rules['work_cap'])
    if open_:
        o = nearest(open_)
        if o['state'] != 'closing':_transition(s, f, o, 'closing', u, 0)
        applied = min(labour, rules['close_labour'] - o['effort'])
        o['effort'] += applied
        engine.emit(s, 'gate_work', unit_id=u['id'], order_version=u['order_version'], feature_id=f['id'],
                    opening_id=o['id'], work='close', labor=applied, effort=o['effort'], required=rules['close_labour'],
                    under_fire=s['turn'] - u.get('last_attacked_turn', -99) <= 1)
        if o['effort'] < rules['close_labour']:
            orders.status(s, u, 'active', 'The men are closing the gate.');return
        blockers = [e['id'] for e in s['units'] if e['side'] != u['side'] and e['strength'] > 0 and e['pos'] == o['inside']]
        if blockers:
            engine.emit(s, 'gate_blocked', unit_id=u['id'], feature_id=f['id'], opening_id=o['id'], blockers=blockers)
            orders.status(s, u, 'blocked', 'The gate cannot be shut while the enemy stands in the gateway.');return
        _transition(s, f, o, 'closed', u, applied)
        orders.status(s, u, 'active', 'The gate is shut; the men are barring it.');return
    o = nearest(shut)
    applied = min(labour, rules['bar_labour'] - o['bar_effort'])
    o['bar_effort'] += applied
    engine.emit(s, 'gate_work', unit_id=u['id'], order_version=u['order_version'], feature_id=f['id'],
                opening_id=o['id'], work='bar', labor=applied, effort=o['bar_effort'], required=rules['bar_labour'],
                under_fire=s['turn'] - u.get('last_attacked_turn', -99) <= 1)
    if o['bar_effort'] < rules['bar_labour']:
        orders.status(s, u, 'active', 'The gate is shut; the men are barring it.');return
    _transition(s, f, o, 'barred', u, applied)
    if not any(x['state'] in CLOSABLE + ('closed',) for x in f['openings']):
        orders.complete(s, u, 'The gate is shut and barred; holding the gateway.')


def _force(s, rules):
    """Units at a closed gate whose ordered destination lies inside push on it.
    A barred gate cannot be forced in the POC."""
    from . import engine
    for f in gated(s):
        for o in f['openings']:
            if o['state'] != 'closed':continue
            pushers = [u for u in sorted(s['units'], key=lambda x: x['id'])
                       if u['pos'] == o['outside'] and u['strength'] > 0 and u['status'] not in REFUSING
                       and u.get('target') is not None and list(u['target']) in f['compound']]
            if not pushers:continue
            labour = sum(min(p['strength'], rules['work_cap']) for p in pushers)
            applied = min(labour, rules['force_labour'] - o['force_effort'])
            o['force_effort'] += applied
            engine.emit(s, 'gate_work', unit_id=pushers[0]['id'], order_version=pushers[0]['order_version'],
                        feature_id=f['id'], opening_id=o['id'], work='force', labor=applied,
                        effort=o['force_effort'], required=rules['force_labour'])
            if o['force_effort'] >= rules['force_labour']:
                _transition(s, f, o, 'forced', pushers[0], applied, pushers=[p['id'] for p in pushers])


def push(s):
    """Why: one defender standing in an open gateway would otherwise keep every
    attacker out, because units cannot share a hex (docs/research/44).
    What: once per poc-11 interval, after fire and gate labour. Units on the
    outside hex of a passable opening, whose ordered destination lies in the
    compound, push on an enemy holding the gateway hex: each adds
    ``min(strength, push_cap)`` to the opening's effort in ``push_effort``. An
    interval with no pusher resets the effort. At ``push_labour`` the holder
    is displaced to the nearest free compound hex (by distance, then hex), or
    overrun to strength 0 when none is free, and the lead pusher steps into
    the gateway. Both report by normal transport. A no-op without
    ``push_rules``, which only poc-11 and later snapshots carry.
    poc-12 (docs/research/45): the holder steps back only to a free compound
    hex beside the gateway (``step_back``). With none free the push stalls at
    the threshold, nobody moves or loses strength, and ``gateway_push_stalled``
    records why; it carries in the first interval such a hex is free.
    Test: `test_push_effort_accumulates_against_a_held_gateway`,
    `test_holder_is_displaced_inside_at_the_threshold`,
    `test_holder_is_overrun_when_no_inside_hex_is_free`,
    `test_push_resets_when_the_holder_leaves_the_gateway`,
    `test_crowded_courtyard_stalls_the_push_and_conserves_strength`,
    `test_one_free_hex_beside_the_gateway_takes_the_holder`."""
    rules = s.get('push_rules')
    if not rules:return
    from . import engine
    for f in gated(s):
        for o in f['openings']:
            k = f['id'] + '/' + o['id']
            holder = next((u for u in s['units'] if u['strength'] > 0 and u['pos'] == o['inside']), None)
            pushers = [] if not holder or o['state'] not in PASSABLE else [
                u for u in sorted(s['units'], key=lambda x: x['id'])
                if u['pos'] == o['outside'] and u['strength'] > 0 and u['status'] not in REFUSING
                and u['side'] != holder['side'] and u.get('target') is not None and list(u['target']) in f['compound']]
            before = s['push_effort'].get(k, 0)
            if not pushers:
                if before:
                    s['push_effort'][k] = 0
                    engine.emit(s, 'gateway_push_interrupted', feature_id=f['id'], opening_id=o['id'], effort=before)
                continue
            labour = sum(min(p['strength'], rules['push_cap']) for p in pushers)
            effort = min(rules['push_labour'], before + labour)
            s['push_effort'][k] = effort
            engine.emit(s, 'gateway_push', feature_id=f['id'], opening_id=o['id'], holder_id=holder['id'],
                        pushers=[p['id'] for p in pushers], labor=effort - before, effort=effort,
                        required=rules['push_labour'],
                        under_fire=any(s['turn'] - p.get('last_attacked_turn', -99) <= 1 for p in pushers))
            if effort < rules['push_labour']:continue
            if s['rules'] == 'poc-11':  # Frozen poc-11 rule: anywhere free in the compound, else overrun.
                s['push_effort'][k] = 0
                _carry(s, f, o, holder, pushers[0], _nearest_free(s, f, o))
                continue
            room = step_back(s, f, o)
            if room is None:
                # poc-12: grid capacity alone never destroys a formation.
                engine.emit(s, 'gateway_push_stalled', feature_id=f['id'], opening_id=o['id'], holder_id=holder['id'],
                            pushers=[p['id'] for p in pushers], effort=effort, reason='no_free_hex_beside_gateway')
                continue
            s['push_effort'][k] = 0
            _carry(s, f, o, holder, pushers[0], room)


def _taken(s):
    return {grid.key(u['pos']) for u in s['units'] if u['strength'] > 0}


def _nearest_free(s, f, o):
    """poc-11: the free compound hex nearest the gateway, at any distance, or None."""
    taken = _taken(s)
    free = sorted((p for p in f['compound'] if grid.key(p) not in taken),
                  key=lambda p: (grid.distance(o['inside'], p), p))
    return free[0] if free else None


def step_back(s, f, o):
    """Why: a displaced holder gives ground one step, as any move does; it
    cannot pass through or stack with the units behind it (docs/research/45).
    What: the free compound hex beside the gateway ``o['inside']``, not across
    a wall, lowest hex first; None when every such hex is taken.
    Test: `test_displacement_is_one_step_to_the_nearest_legal_hex`."""
    taken = _taken(s)
    gateway = s['cells'][grid.key(o['inside'])]
    room = sorted(p for p in grid.neighbors(o['inside'])
                  if p in f['compound'] and grid.key(p) not in taken and p not in gateway.get('walls', ()))
    return room[0] if room else None


def _carry(s, f, o, holder, lead, room):
    """The lead pusher takes the gateway; the holder moves to ``room``, or is
    overrun when ``room`` is None (poc-11 only)."""
    from . import engine, orders
    if room:
        holder['pos'] = list(room)
        outcome, losses = 'displaced', 0
    else:
        losses = holder['strength']
        holder.update(strength=0, status='lost')
        outcome = 'overrun'
        engine.emit(s, 'casualties', unit_id=holder['id'], count=losses, remaining=0)
    origin = lead['pos']
    lead['pos'] = list(o['inside'])
    lead['fatigue'] = min(100, lead['fatigue'] + 3)
    engine.emit(s, 'gateway_carried', feature_id=f['id'], opening_id=o['id'], unit_id=lead['id'],
                holder_id=holder['id'], outcome=outcome, holder_pos=list(holder['pos']), losses=losses)
    engine.emit(s, 'unit_moved', unit_id=lead['id'], origin=origin, destination=lead['pos'],
                decision_seq=lead.get('local_decision_seq'))
    if lead['pos'] == lead['target'] and lead['stance'] not in ('resupply', 'recon'):
        orders.complete(s, lead, 'Assigned position reached.')
    # Physical reports only: headquarters learns of the push when they arrive.
    engine.enqueue(s, lead['side'], f'{lead["id"]} to headquarters: we have pushed through the {o["name"].lower()} '
                   'and stand in the gateway.', kind='reaction', sender=lead['id'])
    engine.enqueue(s, holder['side'], f'{holder["id"]} to headquarters: the enemy has pushed through the '
                   f'{o["name"].lower()}; we are forced back inside the walls.', kind='reaction', sender=holder['id'])


def _supply(s):
    from . import orders
    for u in sorted(s['units'], key=lambda x: x['id']):
        if not u.get('cut_off') or u['stance'] != 'resupply':continue
        if (u.get('mission_result') or {}).get('status') not in ('active', 'blocked'):continue
        depot = next((d for d in s.get('supply_sites', []) if d['id'] == u.get('supply_site')), None)
        if depot and (compound_of(s, depot['pos']) or {}).get('id') == u['cut_off']['feature_id']:continue
        orders.status(s, u, 'failed', 'Cut off inside the walls; the ammunition point cannot be reached.')
        u.update(stance='hold', target=None)
