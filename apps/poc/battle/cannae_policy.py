"""Scripted controls for Cannae (docs/research/63 §3, 68).

Why: the D86 ruling (Bob 2026-11-07 13:10Z) accepts doc 63's default of
scripted controls issuing each sector's orders before sector commanders
exist (doc 63 §9 q10, gap 5). Each side acts as Polybius and Livy describe
(Roman R1, Carthaginian C1) and nothing more; the engine decides what that
leads to, so no winner is forced.
What: ``ROMAN_ORDERS`` and ``CARTHAGINIAN_ORDERS`` list each order with its
trigger and source locator, or an ``inferred:``, ``reconstruction:`` or
``authored:`` label. Entry data carries the yield, the wheel, the Roman
press and the cavalry's opening moves. The sent orders: both sides' light
troops fall back at ``LIGHT_TURN``; the Roman heavy infantry is then ordered
one row forward, which starts its press (exploit trigger ``arrival``), once
headquarters has the light troops reported behind the block, or
``ADVANCE_WAIT`` intervals later; Hasdrubal's horse rides behind the Roman
line once the Roman right cavalry has dropped out of the Carthaginian view
(routed away or lost) and, once it is reported there, charges the
rearmost Roman heavy units it knows of. Each trigger reads only the side's
own delivered view. Orders go through normal delivery, at most three a
decision, and each order is sent once.
Test: `test_every_order_carries_a_source_locator_or_a_label`,
`test_the_light_troops_fall_back_then_the_heavy_infantry_advances_once`,
`test_hasdrubal_rides_only_after_the_roman_right_cavalry_leaves_the_view`,
`test_the_charge_follows_a_reported_arrival_and_targets_the_roman_rear`,
`test_a_cavalry_delay_holds_the_ride_for_its_intervals`.
"""

from . import grid
from .recon import CONTACT_MAX_AGE
from .scenario_cannae import (
    ADVANCE_WAIT, ALA_ROW, CARTHAGINIAN_POLICY, CAVALRY_DELAYS, DESERTER_TURN, DESERTERS_POLICY, HASDRUBAL, HEAVY,
    LEGIONS, LANE_END, LIGHT_TROOPS, LIGHT_TURN, RESERVE, RIDE, ROMAN_POLICY, ROMAN_RESERVE_POLICY, VELITES,
    cavalry_delay_policy,
)

BACK_ROW = {"roman": 15, "carthaginian": 3}  # Where the light troops fall back to; authored.

ROMAN_ORDERS = (
    {"id": "signal-for-battle", "unit": None, "trigger": "before the start: Varro shows the signal and crosses",
     "stance": None, "hex": None, "source": "S66 XXII.45: Varro 'exhibited the signal for battle'; S65 III.113",
     "provenance": "authored: before the 08:00 start; the 6-hex reach is recorded, not sounded (docs/research/68)"},
    {"id": "light-troops-fall-back", "unit": VELITES, "trigger": f"the first decisions at or after interval "
     f"{LIGHT_TURN}", "stance": "retreat", "hex": f"row {BACK_ROW['roman']}, own column",
     "source": "S65 III.115: the light troops skirmish, neither side gaining",
     "provenance": "reconstruction: R1, the light troops fall back through the intervals, approximated as moving to "
                   "the rear rows (doc 63 §3); the interval and row are authored"},
    {"id": "advance", "unit": HEAVY, "trigger": "after the light-troops order, once every reported light unit "
     f"stands behind row {ALA_ROW}, or {ADVANCE_WAIT} intervals later; not to the R2 reserve",
     "stance": "move", "hex": "one row forward, own column",
     "source": "S65 III.115: the legions press the centre 'by the weight of the legions'; S66 XXII.47",
     "provenance": "reconstruction: R1; the arrival starts the press (exploit trigger arrival, docs/research/60 §2)"},
    {"id": "press", "unit": HEAVY, "trigger": "the entry's exploit doctrine, on the advance arriving",
     "stance": None, "hex": "the Carthaginian rear row (row 0), own column",
     "source": "S65 III.115: 'pursuing them furiously' into the centre",
     "provenance": "reconstruction: R1, recall_binding false, max_loss_pct 50 (doc 63 §8 row 21)"},
    {"id": "cavalry-hold", "unit": ("EQ", "SC1", "SC2"), "trigger": "the entry's hold stance, not a sent order",
     "stance": "hold", "hex": None, "source": "S65 III.113: cavalry on both wings",
     "provenance": "reconstruction: R1, the cavalry holds its wings (doc 63 §3)"},
    {"id": "reserve-holds", "unit": tuple(RESERVE), "trigger": "roman-reserve only: the entry's hold stance on the "
     "lane", "stance": "hold", "hex": None, "source": "authored: no source (doc 63 §3 R2, doc 36)",
     "provenance": "authored: the two alae and their hexes"},
)
CARTHAGINIAN_ORDERS = (
    {"id": "crescent", "unit": ("C3", "C4", "C5", "C6"), "trigger": "the entry's deployment, before the start",
     "stance": "hold", "hex": None, "source": "S65 III.113: the central companies advanced in a crescent",
     "provenance": "authored: the 1-hex offset (doc 63 §8 row 9)"},
    {"id": "yield", "unit": "C1-C8", "trigger": "the entry's yield doctrine (docs/research/68), not a sent order",
     "stance": None, "hex": None, "source": "S65 III.115: the centre gives way; S67 p. 24: a fighting withdrawal "
     "'likely' ordered beforehand", "provenance": "reconstruction: C1, up to 3 hexes (doc 63 §8 row 18)"},
    {"id": "wheel", "unit": ("AF1", "AF2"), "trigger": "the entry's wheel doctrine, not a sent order",
     "stance": None, "hex": None, "source": "S65 III.115: 'the situation itself indicating to them how to act'",
     "provenance": "reconstruction: C1 (doc 63 §8 row 19)"},
    {"id": "horse-by-the-river", "unit": HASDRUBAL, "trigger": "the entry's opening charge down the river "
     "lane past the Roman right cavalry, given before the start", "stance": "move", "hex": LANE_END,
     "source": "S65 III.115: the Spanish and Celtic horse meet the Roman cavalry by the river",
     "provenance": "reconstruction: C1; press_assault keeps the horse to its move on contact (authored)"},
    {"id": "numidians-pin", "unit": ("NU1", "NU2"), "trigger": "the entry's opening move to the allied cavalry, "
     "given before the start", "stance": "move", "hex": "SC1's and SC2's starting hexes",
     "source": "S65 III.116: the Numidians' way of fighting holds the allied horse",
     "provenance": "reconstruction: C1, the Numidians skirmish and pin; they halt at first contact"},
    {"id": "light-troops-fall-back", "unit": LIGHT_TROOPS, "trigger": f"the first decisions at or after interval "
     f"{LIGHT_TURN}", "stance": "retreat", "hex": f"row {BACK_ROW['carthaginian']}, own column",
     "source": "S65 III.115: the light troops skirmish, neither side gaining",
     "provenance": "authored: as the Roman light troops; the interval and row are authored"},
    {"id": "ride", "unit": HASDRUBAL, "trigger": f"after interval {CONTACT_MAX_AGE + 1}, no contact of EQ in the "
     "view (it routed out of sight or was lost); later by 10, 20 or 40 in cavalry-delayed", "stance": "move",
     "hex": RIDE, "source": "S65 III.116: having cut up the Roman horse, Hasdrubal rides to the Numidians",
     "provenance": "reconstruction: C1's trigger, the Roman right cavalry routed or lost (doc 63 §8 row 20), read "
                   "from the delivered view; the hexes behind the Roman left are authored"},
    {"id": "charge", "unit": HASDRUBAL, "trigger": "after the ride order, a report of one of the horse within 1 hex "
     "of its ride hex", "stance": "move", "hex": "the three rearmost Roman heavy contacts",
     "source": "S65 III.116: he charges the legions' rear 'at various points all at once'",
     "provenance": "reconstruction: C1; the choice of targets is authored"},
    {"id": "deserters", "unit": "ND", "trigger": f"deserters only: open fire at interval {DESERTER_TURN}, then move "
     "on the rearmost Roman heavy contact", "stance": "open_fire, move", "hex": "the rearmost Roman heavy contact",
     "source": "S66 XXII.48: the feigned deserters attack the Roman rear", "provenance": "authored: the interval"},
)


def _able(u):
    return (u["status"] not in ("lost", "routed", "merged") and not u.get("leaderless")
            and u.get("accepts_orders", True))


def _sent(observation):
    """Unit id -> the orders sent to it (stance, destination tuple or None, sent turn)."""
    sent = {}
    for o in observation.get("orders", ()):
        dest = None if o.get("destination") is None else tuple(o["destination"])
        sent.setdefault(o["unit_id"], []).append((o["stance"], dest, o["sent_turn"]))
    return sent


def _has(sent, uid, stance, dest=None, any_dest=False):
    return any(s == stance and (any_dest or d == dest) for s, d, _ in sent.get(uid, ()))


def _once(observation, wanted):
    """The orders of ``wanted`` ((unit, stance, hex or None)) for able units not
    yet sent that stance, at most three, in the order given."""
    live = {u["id"] for u in observation["units"] if _able(u)}
    sent, chosen, units = _sent(observation), [], set()
    for uid, stance, hex_ in wanted:
        if uid in live and uid not in units and not _has(sent, uid, stance, any_dest=True):
            chosen.append({"unit_id": uid, "stance": stance, "destination": None if hex_ is None else list(hex_)})
            units.add(uid)
    return chosen[:3]


def _operational(observation):
    return observation.get("command", {}).get("operational") is not False


def _units(observation):
    return {u["id"]: u for u in observation["units"]}


def _fall_back(observation, ids, side):
    units = _units(observation)
    return [(uid, "retreat", (units[uid]["pos"][0], BACK_ROW[side])) for uid in ids if uid in units]


def _cleared(observation):
    """Every reported, able light unit stands behind the heavy block's rear row."""
    units = _units(observation)
    return all(units[v]["pos"][1] > ALA_ROW for v in VELITES if v in units and _able(units[v]))


def _roman(observation, *, reserve=False):
    if not _operational(observation):
        return [], []
    turn, wanted = observation["turn"], []
    if turn >= LIGHT_TURN:
        wanted += _fall_back(observation, VELITES, "roman")
        if _cleared(observation) or turn >= LIGHT_TURN + ADVANCE_WAIT:
            units = _units(observation)
            heavy = [u for u in HEAVY if u in units and not (reserve and u in RESERVE)]
            wanted += [(uid, "move", (units[uid]["pos"][0], units[uid]["pos"][1] - 1))
                       for uid in sorted(heavy, key=lambda u: (u not in LEGIONS, u))]
    return [], _once(observation, wanted)


def roman_actions(observation):
    """Doc 63 §3 Roman R1: the light troops fall back, then the heavy infantry advances."""
    return _roman(observation)


def roman_reserve_actions(observation):
    """Doc 63 §3 Roman R2: as ``roman_actions``, without advancing the reserve alae."""
    return _roman(observation, reserve=True)


def _horse_gone(observation):
    """The Roman right cavalry is reported routed, or no contact of it is left in the view (lost or long unseen)."""
    eq = [c for c in observation["contacts"] if c["id"] == "EQ"]
    return any(c.get("routed") for c in eq) or (observation["turn"] > CONTACT_MAX_AGE + 1 and not eq)


def _rear(observation, n):
    """The ``n`` rearmost Roman heavy contacts' hexes (highest row, then lowest column)."""
    heavy = sorted((c for c in observation["contacts"] if c["id"] in HEAVY), key=lambda c: (-c["pos"][1], c["pos"][0]))
    return [tuple(c["pos"]) for c in heavy[:n]]


def _carthaginian(observation, *, delay=0, deserters=False):
    if not _operational(observation):
        return [], []
    turn, sent, units, wanted = observation["turn"], _sent(observation), _units(observation), []
    if turn >= LIGHT_TURN:
        wanted += _fall_back(observation, LIGHT_TROOPS, "carthaginian")
    rode = any(_has(sent, uid, "move", RIDE[uid]) for uid in HASDRUBAL)
    if not rode and _horse_gone(observation):
        marker = [t for s, d, t in sent.get("HC1", ()) if s == "hold"]
        if delay and not marker:
            wanted.append(("HC1", "hold", None))  # The horse halts: the start of the delay.
        elif not delay or turn >= marker[0] + delay:
            wanted += [(uid, "move", RIDE[uid]) for uid in HASDRUBAL]
    charged = any(_rear_sent(sent, uid) for uid in HASDRUBAL)
    arrived = any(uid in units and grid.distance(units[uid]["pos"], RIDE[uid]) <= 1 for uid in HASDRUBAL)
    if rode and arrived and not charged:  # The charge goes alone: it is the one order the horse needs now.
        orders = [{"unit_id": uid, "stance": "move", "destination": list(hex_)}
                  for uid, hex_ in zip(HASDRUBAL, _rear(observation, len(HASDRUBAL)))
                  if uid in units and _able(units[uid])]
        if orders:
            return [], orders
    if deserters and turn >= DESERTER_TURN:
        if not _has(sent, "ND", "open_fire"):
            wanted.insert(0, ("ND", "open_fire", None))
        else:
            rear = _rear(observation, 1)
            if rear:
                wanted.insert(0, ("ND", "move", rear[0]))
    return [], _once(observation, wanted)


def _rear_sent(sent, uid):
    """Destinations of ``uid``'s move orders other than its ride hex: its charge."""
    return [d for s, d, _ in sent.get(uid, ()) if s == "move" and d != tuple(RIDE[uid])]


def carthaginian_actions(observation):
    """Doc 63 §3 Carthaginian C1: the light troops fall back; Hasdrubal rides, then charges."""
    return _carthaginian(observation)


def deserters_actions(observation):
    """Doc 63 §8 deserters: as ``carthaginian_actions``, and the deserters attack at ``DESERTER_TURN``."""
    return _carthaginian(observation, deserters=True)


def _delayed(delay):
    def actions(observation):
        return _carthaginian(observation, delay=delay)
    actions.__doc__ = f"Doc 63 §8 cavalry-delayed: C1 with the ride {delay} intervals after its trigger."
    return actions


POLICIES = {ROMAN_POLICY: roman_actions, ROMAN_RESERVE_POLICY: roman_reserve_actions,
            CARTHAGINIAN_POLICY: carthaginian_actions, DESERTERS_POLICY: deserters_actions,
            **{cavalry_delay_policy(d): _delayed(d) for d in CAVALRY_DELAYS}}
# Policy id -> the side it fits (command_policy.NAMED_POLICIES).
NEEDS = {p: f"the {'Roman' if 'roman' in p else 'Carthaginian'} side of the Cannae scenario" for p in POLICIES}
