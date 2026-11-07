"""Scripted controls for Hill 223 (docs/research/56 §3, 61).

Why: the comparison with the record needs each side to act as the sources
describe (American, S57 and S40) or doc 56 infers (German), and nothing more;
the engine decides what that leads to, so no winner is forced.
What: almost every historical order is entry data, because the patrol's
intent was set at departure and voice reaches only 1 hex (doc 56 §6): the
patrol's move, hold fire, press and return; the line's hold; the German
posture, facing and surrender. ``AMERICAN_ORDERS`` and ``GERMAN_ORDERS`` list
each with its trigger and source locator, or an ``inferred:`` or
``authored:`` label. ``company_g_actions`` (S1) and ``german_actions`` (G1)
send nothing; ``company_reinforces_actions`` (doc 56 §8) sends A3 after the
patrol at a fixed turn. Orders go through normal delivery.
Test: `test_every_order_carries_a_source_locator_or_a_label`,
`test_only_the_reinforcement_variant_sends_an_order_and_only_once`.
"""

from .scenario_hill223 import (
    AMERICAN_POLICY, GERMAN_POLICY, PATROL_START, PATROL_TARGET, REINFORCE_POLICY, REINFORCE_TURN,
)

AMERICAN_ORDERS = (
    {"id": "encircle", "unit": "A1", "trigger": "the entry's initial move order, given at departure before the "
     "start, not a sent order", "stance": "move", "hex": PATROL_TARGET,
     "source": "S57 p. 60: sent 'to encircle the hill and silence the enemy guns'; S58: ordered by Sgt Parson",
     "provenance": "reconstruction: the ravine hex in the guns' rear is authored; S57 p. 60 gives the route"},
    {"id": "hold-fire", "unit": "A1", "trigger": "the entry's initial posture, not a sent order",
     "stance": "hold_fire", "hex": None, "source": "S40 diary: the German leader 'told us not to shoot'",
     "provenance": "sourced: S40; release on being struck is docs/research/46"},
    {"id": "press-on", "unit": "A1", "trigger": "the entry's press_assault key", "stance": None, "hex": None,
     "source": "S57 p. 60: through the woods on the east crest down to the ravine",
     "provenance": "reconstruction: the patrol keeps its route on contact (docs/research/58 §2)"},
    {"id": "return", "unit": "A1", "trigger": "the entry's exploit doctrine, on arriving in the rear",
     "stance": None, "hex": None,
     "source": "S57 p. 61-62: the prisoners brought to the battalion post; S40 diary",
     "provenance": "reconstruction: docs/research/60 §2 doctrine; the post hex is authored; the return resumes "
                   "after a local withdrawal clears, per D7b ruling 2026-11-07"},
    {"id": "line-holds", "unit": None, "trigger": "the entry's initial hold stance, not a sent order",
     "stance": "hold", "hex": None,
     "source": "S57 p. 59: G Company 'seriously impeded by heavy machine gun fire'",
     "provenance": "inferred: the pinned line holds (doc 56 §2)"},
    {"id": "reinforce", "unit": "A3", "trigger": f"the first decision at or after interval {REINFORCE_TURN}, "
     "company-reinforces variant only", "stance": "move", "hex": PATROL_START,
     "source": "authored: no source (doc 56 §8 company-reinforces)",
     "provenance": "authored: the turn, the party and the hex"},
)
GERMAN_ORDERS = (
    {"id": "stand", "unit": "D1", "trigger": "the entry's hold stance and hold-fire posture, not a sent order",
     "stance": "hold", "source": "S57 p. 60: about 75 round the commander 'receiving final instructions'",
     "provenance": "inferred: the group stands and does not fire"},
    {"id": "guns-on-the-valley", "unit": None, "trigger": "the entry's facing and open fire, not a sent order",
     "stance": "hold", "source": "S40: the guns 'masked and the muzzles pointed down into the valley'; S57 p. 59",
     "provenance": "sourced: the posture; the bearing, arc and hexes are authored"},
    {"id": "turn-the-guns", "unit": None, "trigger": "the entry's reorient_turns rule (docs/research/59 §2)",
     "stance": None, "source": "S57 p. 60: the machine gunners 'quickly reversed their guns'; S40",
     "provenance": "reconstruction: the delay is authored (doc 56 §8 gun-turn-delay)"},
    {"id": "yield", "unit": "D1", "trigger": "the entry's surrender rule (docs/research/59 §1)", "stance": None,
     "source": "S57 p. 60: the group 'supposing' the patrol 'the leading element of a large American force'",
     "provenance": "inferred: G1; reach, odds and support are authored"},
    {"id": "counter-attack", "unit": None, "trigger": "the deadline: the battle ends at the counter-attack hour",
     "stance": None, "source": "S57 p. 60: orders to counter-attack the American left at 10:30",
     "provenance": "authored: modelled as the deadline (doc 56 §2), not as an attack"},
)


def _able(u):
    return (u["status"] not in ("lost", "routed", "merged") and not u.get("leaderless")
            and u.get("accepts_orders", True))


def company_g_actions(observation):
    """Doc 56 §3 S1: the company commander cannot reach the patrol once it has
    left, and the line holds; every order is entry data, so nothing is sent."""
    return [], []


def german_actions(observation):
    """Doc 56 §3 G1: posture, facing and surrender are entry data; nothing is sent."""
    return [], []


def company_reinforces_actions(observation):
    """Why: doc 56 §8 ``company-reinforces`` asks what a second party changes.
    What: at or after ``REINFORCE_TURN``, one ``move`` order to the patrol's
    start hex for A3 while it is able and none has been sent; nothing while
    the command is disrupted.
    Test: `test_only_the_reinforcement_variant_sends_an_order_and_only_once`."""
    if observation.get("command", {}).get("operational") is False or observation["turn"] < REINFORCE_TURN:
        return [], []
    able = any(u["id"] == "A3" and _able(u) for u in observation["units"])
    sent = any(o["unit_id"] == "A3" and o["stance"] == "move" for o in observation.get("orders", ()))
    if not able or sent:
        return [], []
    return [], [{"unit_id": "A3", "stance": "move", "destination": list(PATROL_START)}]


POLICIES = {AMERICAN_POLICY: company_g_actions, GERMAN_POLICY: german_actions,
            REINFORCE_POLICY: company_reinforces_actions}
# Policy id -> the side it fits (command_policy.NAMED_POLICIES).
NEEDS = {AMERICAN_POLICY: "the American side of the Hill 223 scenario",
         GERMAN_POLICY: "the German side of the Hill 223 scenario",
         REINFORCE_POLICY: "the American side of the Hill 223 scenario"}
