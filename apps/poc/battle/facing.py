"""Gun facing and a reorientation delay (docs/research/59 §2).

Why: ``engine.volley`` fires at the nearest visible enemy from any side. Hill
223 (docs/research/56 §10, gap 3) needs gun groups laid on one front that must
be turned before they can fire on a party in their rear. The keys are unit
overrides that only a declaring entry writes, so every other unit fires as
before.
What: a unit that declares ``facing`` (a bearing in whole degrees, clockwise
from map north), ``arc`` (the arc's full width in degrees) and
``reorient_turns`` fires only at enemies whose bearing lies inside its arc.
When it sees enemies within reach and none inside the arc, it begins to turn
toward the nearest of them and fires at nothing until ``reorient_turns``
intervals have passed; its facing then becomes that bearing. The choice reads
only the enemies the unit sees (``engine.volley`` filters by ``recon.sees``).
"""
import math
from . import grid

KEYS=('facing','arc','reorient_turns')


def bearing(a,b):
    """Whole degrees clockwise from map north (up the map) from hex ``a`` to ``b``."""
    ax,ay=grid.center(a); bx,by=grid.center(b)
    return round(math.degrees(math.atan2(bx-ax,ay-by)))%360


def within(u,pos):
    """True when ``pos`` lies inside the arc of facing unit ``u``, edges included."""
    off=(bearing(u['pos'],pos)-u['facing']+180)%360-180
    return 2*abs(off)<=u['arc']


def targets(s,u,enemies,emit):
    """Why: a masked gun group cannot fire behind it until it is turned.
    What: the enemies of ``enemies`` (seen and within reach) that ``u`` may fire
    at this interval. Undeclared units get all of them. A unit still turning
    gets none until ``ready_turn``, when it takes its new facing
    (``gun_reoriented``). A unit with enemies but none inside its arc starts to
    turn toward the nearest (``gun_reorienting``); with a delay of 0 it turns
    and fires at once.
    Test: `test_a_gun_turns_for_its_delay_before_firing_into_its_rear`,
    `test_a_zero_delay_turns_and_fires_in_the_same_interval`,
    `test_an_undeclared_gun_fires_at_an_enemy_on_any_side`."""
    if 'facing' not in u:return enemies
    turning=u.get('reorienting')
    if turning:
        if s['turn']<turning['ready_turn']:return []
        u['facing']=turning['bearing']; del u['reorienting']
        emit(s,'gun_reoriented',unit_id=u['id'],facing=u['facing'])
    inside=[e for e in enemies if within(u,e['pos'])]
    if inside or not enemies:return inside
    nearest=min(enemies,key=lambda e:(grid.distance(u['pos'],e['pos']),e['id']))
    u['reorienting']={'bearing':bearing(u['pos'],nearest['pos']),'ready_turn':s['turn']+u['reorient_turns']}
    emit(s,'gun_reorienting',unit_id=u['id'],from_facing=u['facing'],toward_id=nearest['id'],
         **u['reorienting'])
    return targets(s,u,enemies,emit)
