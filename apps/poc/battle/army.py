"""Army-scale rules for an entry that declares them (docs/research/63 §10, 68).

Why: the engine was built for companies of tens of men. At Cannae a unit is a
legion of 3,550: a volley that fires every man and spends a round each empties
a shock unit in a few intervals, morale lost at 4 a man routs it at its first
exchange, every unit moves one hex an interval and a blow in the rear counts
as one in front (doc 63 §2.1, gaps 2, 3, 4 and 6).
What: pure functions of the snapshot that ``engine.advance`` calls only when
the snapshot carries ``army_rules`` (``scenario_army.setup``), so every other
battle, and every saved poc-13 game, plays as before:

- ``rate`` / ``max_rate``: a unit's declared ``move_rate`` (hexes an interval);
- ``volley``: fire by the engaged share of a unit, with no ammunition spent
  by a shock class and a flank or rear multiplier on the loss;
- ``morale_loss``: morale lost per per cent of the unit's starting strength;
- ``moved``: a unit's ``front`` follows its movement, except a step back;
- ``doctrine``: the declared ``yield`` and ``wheel`` local doctrines.

Every coefficient is entry data (``ArmyEntry``), authored, not measured.
"""
from . import facing, grid

# Local actions whose move turns the unit's front; a step back keeps it.
TURNING = ('continue', 'route', 'press', 'wheel')
YIELD_REASON = 'Pressed in front; yielding one hex as ordered, keeping the line and contact.'
WHEEL_REASON = 'An enemy is past our front row; wheeling inward to strike his flank.'


def on(s):
    return 'army_rules' in s


def rate(u):
    """Hexes ``u`` may move in one interval: its ``move_rate``, else 1."""
    return u.get('move_rate', 1)


def max_rate(s):
    """The most movement steps any unit takes this interval: 1 without army rules."""
    if not on(s):
        return 1
    return max([rate(u) for u in s['units'] if u['strength'] > 0] + [1])


def aspect(target, pos):
    """Why: an attack on a flank or the rear did more than one in front (S65 III.115-116).
    What: ``front``, ``flank`` or ``rear`` for a blow on ``target`` from hex
    ``pos``: the bearing from the target to ``pos`` against the target's
    ``front``; within 60 degrees is the front, 150 or more the rear, else a flank.
    Test: `test_aspect_reads_the_bearing_against_the_front`."""
    off = abs((facing.bearing(target['pos'], pos) - target['front'] + 180) % 360 - 180)
    return 'front' if off <= 60 else 'rear' if off >= 150 else 'flank'


def volley(s, u, target, distance, cover, weapon, damage, suppression, strain, emit):
    """Why: a legion fights with its front ranks, not every man at once, and a
    shock class throws nothing that runs out (doc 63 gap 3).
    What: ``u`` fires ``engaged_pct`` per cent of its strength (at least 1)
    at ``target``; a class outside ``shock_classes`` spends that many rounds
    and fires no more than it holds. The effect is the engine's exposure
    formula times the class's ``effect_pct``, times ``flank_pct`` or
    ``rear_pct`` by ``aspect``; ``strain`` gets the extra share for morale.
    Suppression grows with the engaged men as a share of the target's
    strength. Emits ``volley`` with the ``aspect``.
    Test: `test_a_shock_volley_fires_the_engaged_share_and_spends_nothing`,
    `test_a_rear_blow_costs_more_men_and_morale_than_a_frontal_one`."""
    r = s['army_rules']
    rounds = max(1, u['strength'] * r['engaged_pct'] // 100)
    if u.get('weapon_class') not in r['shock_classes']:
        rounds = min(u['ammo'], rounds)
        u['ammo'] -= rounds
    exposure = (weapon['range_hexes'] + 1 - distance) * 7 // weapon['range_hexes']
    effect = rounds * exposure * (100 - cover) * (100 - u['suppression'] // 2) // 9000
    effect = effect * weapon['effect_pct'] // 100
    side = aspect(target, u['pos'])
    multiplier = {'front': 100, 'flank': r['flank_pct'], 'rear': r['rear_pct']}[side]
    effect = max(1, effect * multiplier // 100)
    damage[target['id']] += effect
    strain[target['id']] += effect * (multiplier - 100) // 100
    suppression[target['id']] += max(2, rounds * 25 // max(1, target['strength']))
    extra = {'returning_fire': True} if u.get('fire_posture') == 'hold_fire' else {}
    emit(s, 'volley', unit_id=u['id'], target_id=target['id'], rounds=rounds, exposure=effect, aspect=side, **extra)


def morale_loss(s, u, damage, strain):
    """Morale points ``u`` loses this interval: ``morale_per_pct`` per per cent
    of its starting strength in this interval's loss (``damage``, in hundredths
    of a man) plus the flank and rear ``strain``.
    Test: `test_morale_falls_by_share_of_strength_not_by_man`."""
    return (damage + strain) * s['army_rules']['morale_per_pct'] // max(1, u['initial'])


def moved(s, u, origin, destination, emit):
    """After ``u`` moves: a step forward, an attack or a flight turns its
    ``front`` to the move's bearing; a yield counts toward its limit and keeps
    the front (``unit_yielded``); any other step back keeps it too.
    Test: `test_the_front_follows_movement_but_not_a_step_back`."""
    action = u.get('local_action')
    if action == 'yield':
        u['yielded'] = u.get('yielded', 0) + 1
        emit(s, 'unit_yielded', unit_id=u['id'], yielded=u['yielded'], limit=u['yield']['limit'])
    elif action in TURNING:
        u['front'] = facing.bearing(origin, destination)


def _past(rule, pos):
    return (pos[1] - rule['front_row']) * rule['rear_step'] > 0


def _wheel(s, u, decision, contacts, emit):
    rule = u['wheel']
    past = [c for c in contacts if _past(rule, c['pos']) and grid.distance(u['pos'], c['pos']) <= rule['reach']]
    if not past:
        return False
    enemy = min(past, key=lambda c: (grid.distance(u['pos'], c['pos']), c['id']))
    if u.get('wheeled_turn') is None:
        u['wheeled_turn'] = s['turn']
        emit(s, 'unit_wheeled', unit_id=u['id'], toward_id=enemy['id'], pos=list(enemy['pos']))
    u['front'] = facing.bearing(u['pos'], enemy['pos'])  # Faces inward at once (S65 III.115).
    adjacent = grid.distance(u['pos'], enemy['pos']) <= 1
    decision.update(action='wheel', target=None if adjacent else list(enemy['pos']), reason=WHEEL_REASON)
    return True


def _yield(s, u, decision, contacts):
    rule = u['yield']
    if u.get('yielded', 0) >= rule['limit'] or not decision['under_fire']:
        return False
    threats = [c['pos'] for c in contacts if grid.distance(u['pos'], c['pos']) <= 1]
    if not threats:
        return False
    taken = {grid.key(x['pos']) for x in s['units'] if x['strength'] > 0 and x['id'] != u['id']
             and grid.distance(x['pos'], u['pos']) <= 1}  # Adjacent hexes are always in sight (grid.visible).
    steps = [p for p in grid.neighbors(u['pos']) if p[1] - u['pos'][1] == rule['rear_step']
             and grid.key(p) not in taken and grid.passable(s['cells'][grid.key(p)])]
    if not steps:
        return False
    away = lambda p: min(grid.distance(p, t) for t in threats)
    step = max(steps, key=lambda p: (away(p), -abs(p[0] - u['pos'][0]), -p[0]))
    decision.update(action='yield', target=step, reason=YIELD_REASON)
    return True


def doctrine(s, u, decision, contacts, emit):
    """Why: Polybius's crescent gives way under the legions' weight while the
    Africans, on the situation alone, turn on the flanks (S65 III.113-115;
    S67 p. 24 on an ordered fighting withdrawal). Neither is an order sent
    in the battle, so each is a unit's own doctrine (doc 63 gap 6).
    What: for a unit that is not routed:

    - ``wheel`` {``reach``, ``front_row``, ``rear_step``}: an enemy the unit
      sees within ``reach`` hexes whose row lies beyond ``front_row`` on the
      unit's own side (``rear_step`` -1: lower rows) makes it face that enemy
      (the nearest, lowest id) and move to it, or stand and fight once
      adjacent (action ``wheel``; ``unit_wheeled`` the first time);
    - ``yield`` {``limit``, ``rear_step``}: under fire last interval with an
      enemy it sees adjacent, it steps one row back (``rear_step``) to a free
      hex, the one farthest from those enemies, nearest its column (action
      ``yield``), until it has yielded ``limit`` hexes; the step is not a
      rout and keeps the front. After the limit the ordinary decision stands.

    A wheel takes precedence over a yield. Reads only the unit's own
    sightings (``contacts``) and its adjacent hexes.
    Test: `test_a_pressed_centre_unit_yields_up_to_its_limit_without_routing`,
    `test_an_unpressed_unit_does_not_yield`,
    `test_an_african_wheels_on_an_enemy_past_its_front_row`,
    `test_an_enemy_level_with_the_front_row_does_not_trigger_the_wheel`."""
    if u['status'] == 'routed' or u['strength'] <= 0:
        return decision
    if u.get('wheel') and _wheel(s, u, decision, contacts, emit):
        return decision
    if u.get('yield'):
        _yield(s, u, decision, contacts)
    return decision
