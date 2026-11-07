"""Scripted controls for Gergovia (docs/research/57 §3, 62).

Why: the comparison with the record needs each side to act as Caesar
describes (Roman, S60) or as Caesar describes the Gauls (Gallic G1), and
nothing more; the engine decides what that leads to, so no winner is forced.
What: the recall is entry data (a broadcast at a fixed interval), as are the
forward groups' pursuit (exploit, recall-binding in S1, not in ardour) and the
wall garrison's hold.
``ROMAN_ORDERS`` and ``GALLIC_ORDERS`` list each order with its trigger and
source locator, or an ``inferred:`` or ``authored:`` label. The sent orders:
Sextius's cohorts go out at a fixed interval (Roman S1; not in ``no-cover``);
in ``recall-by-runner`` each forward group also gets a retreat order at the
recall; the Gallic masses come back beneath the wall at a fixed interval and
push down once the Romans are reported at the wall. Orders go through normal
delivery; nothing is applied here.
Test: `test_every_order_carries_a_source_locator_or_a_label`,
`test_roman_policies_send_sextius_and_the_runner_recall_once`,
`test_the_gallic_masses_return_at_their_turn_then_push_only_once_romans_reach_the_wall`.
"""

from .scenario_gergovia import (
    BELOW_GATE, FORWARD, GALLIC_DELAYS, GALLIC_POLICY, PUSH_TO, RALLY, RECALL_TURN, RETURN_TURN, ROMAN_NO_COVER_POLICY,
    ROMAN_POLICY, ROMAN_RUNNER_POLICY, SEXTIUS_POST, SEXTIUS_TURN, TOWN_WALL_ROW, UNDER_WALL, gallic_delay_policy,
)

ROMAN_ORDERS = (
    {"id": "take-the-camps", "unit": None, "trigger": "before the start: the camps are taken at 12:00",
     "stance": None, "hex": None, "source": "S60 VII.45, VII.46: the signal for action; the camps are taken",
     "provenance": "authored: the battle opens after the success (doc 57 §2)"},
    {"id": "pursue", "unit": FORWARD, "trigger": "the entry's exploit doctrine from the start (recall_binding "
     "true), not a sent order", "stance": None, "hex": BELOW_GATE,
     "source": "S60 VII.47: the legions across the valley pursued to the wall and gates of the town",
     "provenance": "reconstruction: Roman S1 (doc 57 §3); a heard recall stops the pursuit (docs/research/60 §2)"},
    {"id": "recall", "unit": None, "trigger": f"the entry's broadcast at interval {RECALL_TURN}, not a sent order",
     "stance": "retreat", "hex": RALLY, "source": "S60 VII.47: Caesar orders the retreat sounded",
     # D85 (Bob 2026-11-07 13:10Z): earlier recall; the interval follows VII.47, the camps taken at the start.
     "provenance": "inferred: the interval, sounded once the camps are taken (S60 VII.47; D85 ruling "
                   "2026-11-07); authored: the reach and block (doc 57 §8)"},
    {"id": "runner-recall", "unit": FORWARD, "trigger": f"the first decisions at or after interval "
     f"{RECALL_TURN}, recall-by-runner only", "stance": "retreat", "hex": RALLY,
     "source": "S60 VII.47: the legions 'were kept back by the tribunes of the soldiers and the lieutenants'",
     "provenance": "reconstruction: the tribunes' word as a delivered order, sent with the recall (D85)"},
    {"id": "sextius-out", "unit": "R13", "trigger": f"the first decision at or after interval {SEXTIUS_TURN}, not "
     "in no-cover", "stance": "move", "hex": SEXTIUS_POST,
     "source": "S60 VII.49: Sextius to bring his cohorts out to the foot of the hill on the enemy's right",
     "provenance": "sourced: the order; the interval and hex are authored (doc 57 §8 sextius-cover)"},
    {"id": "tenth-advances", "unit": "RX", "trigger": "not sent", "stance": None, "hex": None,
     "source": "S60 VII.49: Caesar 'advanced a little' with the legion by him",
     "provenance": "authored: not modelled; the Tenth's line stays the rally hex (docs/research/62 §6)"},
)
GALLIC_ORDERS = (
    {"id": "hold-the-wall", "unit": ("G1", "G2", "G3", "G4"), "trigger": "the entry's initial hold stance, not a "
     "sent order", "stance": "hold", "hex": None, "source": "S60 VII.46, VII.48: the wall and the camps by it held; "
     "S61 Dio 40.36.3: stones and javelins",
     "provenance": "inferred: Gallic G1 (doc 57 §3)"},
    {"id": "return", "unit": ("GR", "GC"), "trigger": f"the first decision at or after interval {RETURN_TURN} "
     "(later by 10, 20 or 40 in gallic-delay)", "stance": "move", "hex": UNDER_WALL,
     "source": "S60 VII.48: from the other part of the town they gather beneath the wall, cavalry first",
     "provenance": "authored: the interval and the hexes (doc 57 §3 G1, §8 gallic-delay)"},
    {"id": "push-down", "unit": ("GR", "GC"), "trigger": "after the return order, a fresh contact reported "
     f"within 2 rows of the town wall (row {TOWN_WALL_ROW})", "stance": "move", "hex": PUSH_TO,
     "source": "S60 VII.50, VII.51: the Romans are driven down; Vercingetorix leads his men back within the "
               "fortifications", "provenance": "inferred: G1, the mass pushes down only once the Romans are at "
                                              "the wall (doc 57 §3); the hex is authored"},
)
FRESH = 2  # Intervals: a contact this old or newer counts as present (authored).
AT_WALL_ROWS = 2  # Rows below the town wall that count as "at the wall" (authored).


def _able(u):
    return (u["status"] not in ("lost", "routed", "merged") and not u.get("leaderless")
            and u.get("accepts_orders", True))


def _sent(observation):
    sent = {}
    for o in observation.get("orders", ()):
        sent.setdefault(o["unit_id"], set()).add((o["stance"], tuple(o["destination"] or ())))
    return sent


def _order(uid, stance, destination):
    return {"unit_id": uid, "stance": stance, "destination": list(destination)}


def _once(observation, wanted):
    """The orders of ``wanted`` ((unit, stance, hex)) for able units not yet sent, at most three."""
    live = {u["id"] for u in observation["units"] if _able(u)}
    sent = _sent(observation)
    return [_order(uid, stance, hex_) for uid, stance, hex_ in wanted
            if uid in live and (stance, tuple(hex_)) not in sent.get(uid, ())][:3]


def _roman(observation, *, cover=True, runner=False):
    if observation.get("command", {}).get("operational") is False:
        return [], []
    turn, wanted = observation["turn"], []
    if runner and turn >= RECALL_TURN:
        wanted += [(uid, "retreat", RALLY) for uid in FORWARD]
    if cover and turn >= SEXTIUS_TURN:
        wanted.append(("R13", "move", SEXTIUS_POST))
    return [], _once(observation, wanted)


def roman_actions(observation):
    """Doc 57 §3 Roman S1: the recall is entry data; Sextius goes out at ``SEXTIUS_TURN``."""
    return _roman(observation)


def roman_no_cover_actions(observation):
    """Doc 57 §8 no-cover: as ``roman_actions`` without Sextius."""
    return _roman(observation, cover=False)


def roman_runner_actions(observation):
    """Doc 57 §8 recall-by-runner: as ``roman_actions``, and each forward
    group also gets a retreat order to the Tenth's line from ``RECALL_TURN``."""
    return _roman(observation, runner=True)


def _at_wall(observation):
    # A contact with no age is stale, not fresh.
    return any(c.get("age") is not None and c["age"] <= FRESH and c["pos"][1] <= TOWN_WALL_ROW + AT_WALL_ROWS
               for c in observation.get("contacts", ()))


def _gallic(observation, return_turn):
    """Why: doc 57 §3 G1, the wall holds, the masses come back at a fixed
    interval and push down only after the Romans reach the wall.
    What: from ``return_turn``, GR and GC each get one move beneath the wall;
    once both return orders are sent and a fresh contact is reported within
    ``AT_WALL_ROWS`` rows of the town wall, each gets one move down to
    ``PUSH_TO``. Nothing while the command is disrupted."""
    if observation.get("command", {}).get("operational") is False or observation["turn"] < return_turn:
        return [], []
    sent = _sent(observation)
    returned = all(("move", tuple(UNDER_WALL[uid])) in sent.get(uid, ()) for uid in UNDER_WALL)
    if not returned:
        return [], _once(observation, [(uid, "move", hex_) for uid, hex_ in UNDER_WALL.items()])
    if _at_wall(observation) or any(("move", tuple(PUSH_TO)) in sent.get(uid, ()) for uid in UNDER_WALL):
        return [], _once(observation, [(uid, "move", PUSH_TO) for uid in UNDER_WALL])
    return [], []


def gallic_actions(observation):
    """Doc 57 §3 Gallic G1 at ``RETURN_TURN``."""
    return _gallic(observation, RETURN_TURN)


def _delayed(delay):
    def actions(observation):
        return _gallic(observation, RETURN_TURN + delay)
    actions.__doc__ = f"Doc 57 §8 gallic-delay: G1 with the return {delay} intervals later."
    return actions


POLICIES = {ROMAN_POLICY: roman_actions, ROMAN_NO_COVER_POLICY: roman_no_cover_actions,
            ROMAN_RUNNER_POLICY: roman_runner_actions, GALLIC_POLICY: gallic_actions,
            **{gallic_delay_policy(d): _delayed(d) for d in GALLIC_DELAYS}}
# Policy id -> the side it fits (command_policy.NAMED_POLICIES).
NEEDS = {p: f"the {'Roman' if 'roman' in p else 'Gallic'} side of the Gergovia scenario" for p in POLICIES}
