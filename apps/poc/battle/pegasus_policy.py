"""Scripted controls for Pegasus Bridge (docs/research/52 §3 and §9, 54).

Why: the comparison with the record needs each side to issue the orders the
sources describe (British) or doc 52 infers (German), and nothing more; the
engine decides what they lead to, so no winner is forced.
What: ``coup_de_main_actions`` (British S1), ``guard_actions`` (German G1)
and ``early_alarm_actions`` (German G2) return ``(standing, orders)`` from a
side's own observation: delivered reports, delivered codewords, the briefed
map and the battle clock. ``BRITISH_ORDERS`` and ``GERMAN_ORDERS`` list each
order with its trigger and source locator, or an ``inferred`` label. Orders
go through normal delivery; nothing is applied here.
Test: `test_every_order_carries_a_source_locator_or_an_inferred_label`,
`test_british_platoons_get_their_tasks_then_dig_in_once_ham_arrives`,
`test_reserve_moves_at_the_alarm_turn_and_early_in_the_variant`.
"""

from .scenario_pegasus import (
    BRITISH_POLICY, CANAL, CANAL_WEST, CANAL_WEST_N, EARLY_ALARM_POLICY, GUARD_POLICY, ORNE, ORNE_EAST,
)

BRITISH_ORDERS = (
    {"id": "cross", "unit": "D25", "trigger": "start", "stance": "move", "hex": CANAL_WEST,
     "source": "S51 p. 1 para 3: 25 Pln 'attacked and crossed the Br'",
     "provenance": "sourced: S51; the far-end hex is authored"},
    {"id": "inner-defences", "unit": "D24", "trigger": "start", "stance": "move", "hex": CANAL,
     "source": "S51 p. 1 para 3: 24 Pln 'took on the inner defences'; S52 sheet 2: No. 92 carried Capt "
               "Neilson RE; S51: the sappers 'cut wires and removed charges'",
     "provenance": "reconstruction: the platoon with the sapper officer goes onto the bridge, where the "
                   "charges are cleared; the hex is authored"},
    {"id": "bridgehead", "unit": "B14", "trigger": "start", "stance": "move", "hex": CANAL_WEST_N,
     "source": "S51 p. 1 para 3: 14 Pln 'ordered to reinforce 25 and start to form a small bridgehead'",
     "provenance": "sourced: S51; the hex is authored"},
    {"id": "orne-bridge", "unit": "B17", "trigger": "start", "stance": "move", "hex": ORNE,
     "source": "S51 p. 1 para 3: 17 Pln 'soon had full control'; S52 sheet 3: No. 96 'took it'",
     "provenance": "sourced: S51, S52; the hex is authored"},
    {"id": "orne-reinforce", "unit": "D23", "trigger": "start", "stance": "move", "hex": ORNE_EAST,
     "source": "S51 p. 1 para 3: 17 Pln 'reinforced by 23'; S52 sheet 3: No. 95 landed about 500 yards north",
     "provenance": "sourced: S51, S52; the far-end hex is authored"},
    {"id": "dig-in", "unit": None, "trigger": "headquarters has received the bridge's codeword and the "
     "unit is reported at its post", "stance": "dig_in", "hex": None,
     "source": "S51 p. 1 para 3 (14 Pln, the bridgehead); S52 sheet 3: a platoon dug in",
     "provenance": "reconstruction: the codeword as the trigger is authored"},
)
GERMAN_ORDERS = (
    {"id": "guard", "trigger": "the entry's initial hold stance and open fire, not a sent order",
     "stance": "hold", "source": "inferred: S54 lists the posts; no order to the guard was read (doc 52 §1)",
     "provenance": "inferred: fight from the posts and do not give up the bridge (doc 52 §3)"},
    {"id": "demolish", "trigger": "the entry's demolition rule (contact by default), not a sent order",
     "stance": None, "source": "inferred: S54 (secondary) 'orders to blow up the two bridges'",
     "provenance": "inferred: the trigger and timings are authored (scenario_wwii.DemolitionEntry)"},
    {"id": "alarm-west", "unit": "R1", "trigger": "the first decision at or after the alarm turn",
     "stance": "move", "source": "S54: the 716th orders 21st Panzer to attack at 01:20 and armour attacks "
     "from the west near 02:00; S51: tanks 'within an hour'",
     "provenance": "reconstruction: ordered at turn 170 (01:50) so that the group reaches the bridge near "
                   "S54's 02:00; the march allowance is authored"},
    {"id": "alarm-south", "unit": "R2", "trigger": "the first decision at or after the alarm turn",
     "stance": "move", "source": "S54: infantry and self-propelled guns attack from the south near 03:00",
     "provenance": "reconstruction: ordered at turn 290 (02:50) to arrive near S54's 03:00; authored allowance"},
)
# Bridge id -> the units that dig in once headquarters hears its codeword.
DIG_IN = {"canal-bridge": ("D25", "B14"), "orne-bridge": ("D23",)}
ALARM_TURNS = {"R1": 170, "R2": 290}  # GERMAN_ORDERS alarm-west, alarm-south.
EARLY_ALARM_TURNS = {"R1": 2, "R2": 2}  # Doc 52 §3 G2: touchdown plus one minute.


def _able(u):
    return (u["status"] not in ("lost", "routed", "merged") and not u.get("leaderless")
            and u.get("accepts_orders", True))


def _sent(observation):
    sent = {}
    for o in observation.get("orders", ()):
        sent.setdefault(o["unit_id"], set()).add(o["stance"])
    return sent


def _order(uid, stance, destination=None):
    return {"unit_id": uid, "stance": stance, "destination": list(destination) if destination else None}


def coup_de_main_actions(observation):
    """Why: the platoons must carry out the tasks S51 gives them, then
    consolidate, as doc 52 §3 reconstructs.
    What: ``([], orders)``, at most three, in ``BRITISH_ORDERS`` order: each
    able platoon present gets its task move once; then, for each bridge
    whose codeword headquarters has received (``observation['signals']``),
    each ``DIG_IN`` unit reported at its post gets ``dig_in`` once. The
    headquarters detachment gets no order. Nothing while the command is
    disrupted.
    Test: `test_british_platoons_get_their_tasks_then_dig_in_once_ham_arrives`.
    """
    if observation.get("command", {}).get("operational") is False:
        return [], []
    live = {u["id"]: u for u in observation["units"] if _able(u)}
    sent = _sent(observation)
    tasks = [o for o in BRITISH_ORDERS if o["unit"]]
    orders = [_order(o["unit"], "move", o["hex"]) for o in tasks
              if o["unit"] in live and "move" not in sent.get(o["unit"], ())]
    posts = {o["unit"]: list(o["hex"]) for o in tasks}
    for signal in observation.get("signals", ()):
        for uid in DIG_IN.get(signal["bridge"], ()):
            u = live.get(uid)
            if u and u["pos"] == posts[uid] and "dig_in" not in sent.get(uid, ()):
                orders.append(_order(uid, "dig_in"))
    return [], orders[:3]


def _alarm(observation, turns):
    """The reserve's attack orders: each able group in ``turns`` whose alarm
    turn has come gets one move to the objective's west bank, R1 to the
    west end and R2 to the hex north of it. Nothing while disrupted."""
    if observation.get("command", {}).get("operational") is False:
        return [], []
    c, r = observation["objective"]
    targets = {"R1": (c - 1, r), "R2": (c - 1, r - 1)}
    live = {u["id"] for u in observation["units"] if _able(u)}
    sent = _sent(observation)
    orders = [_order(uid, "move", targets[uid]) for uid, turn in turns.items()
              if uid in live and observation["turn"] >= turn and "move" not in sent.get(uid, ())]
    return [], orders[:3]


def guard_actions(observation):
    """Why: doc 52 §3 G1, the guard holds and its alarm reaches the reserve
    after a delay, so the reserve attacks near the S54 times.
    What: ``_alarm`` at ``ALARM_TURNS``. The guard's hold and the demolition
    are entry data, not orders.
    Test: `test_reserve_moves_at_the_alarm_turn_and_early_in_the_variant`."""
    return _alarm(observation, ALARM_TURNS)


def early_alarm_actions(observation):
    """Doc 52 §3 G2: as ``guard_actions`` with the alarm at touchdown plus one minute."""
    return _alarm(observation, EARLY_ALARM_TURNS)


POLICIES = {BRITISH_POLICY: coup_de_main_actions, GUARD_POLICY: guard_actions,
            EARLY_ALARM_POLICY: early_alarm_actions}
# Policy id -> the side it fits (command_policy.NAMED_POLICIES).
NEEDS = {BRITISH_POLICY: "the British side of the Pegasus scenario",
         GUARD_POLICY: "the German side of the Pegasus scenario",
         EARLY_ALARM_POLICY: "the German side of the Pegasus scenario"}
