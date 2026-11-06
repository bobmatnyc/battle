"""Scripted historical-order controls for Concord North Bridge (doc 43 §5 S1).

Why: the comparison with the record (docs/research/48) needs each side to
issue the orders the sources describe, and nothing more; the engine decides
what they lead to, so no winner is forced.
What: ``militia_actions`` and ``regulars_actions`` return ``(standing,
orders)`` from a side's own observation (delivered reports, delivered
contacts, the briefed map). ``MILITIA_ORDERS`` and ``REGULARS_ORDERS`` list
each order with its trigger and source locator; the code cites them by id.
Orders go through normal delivery; nothing is applied here.
"""

from . import grid
from .scenario_concord import APPROACH, BRIDGE, EAST_END, TOWN

MILITIA_POLICY = "scripted-concord-militia-v1"
REGULARS_POLICY = "scripted-concord-regulars-v1"

MILITIA_ORDERS = (
    {"id": "hold-fire", "trigger": "before the advance; the entry's initial fire posture, not a sent order",
     "stance": "hold_fire", "source": "S47: Barrett, 'Do not fire unless first fired upon'",
     "provenance": "sourced: S47"},
    {"id": "advance", "trigger": "start; once per company", "stance": "move",
     "source": "S47: the militia advanced from the ridge to the bridge (09:00 to 09:30); S48: Davis's "
               "Acton company at the head of the column",
     "provenance": "sourced: the advance and the Acton lead (S47, S48); the approach hexes are authored"},
    {"id": "follow", "trigger": "start; the companies behind Acton", "stance": "move",
     "source": "doc 43 §5 S1: 'the rest follow'",
     "provenance": "reconstruction: no source read gives the column's order or frontage"},
    {"id": "fire", "trigger": "headquarters knows a provincial company has taken losses",
     "stance": "open_fire", "source": "S47: Buttrick, 'Fire, for god's sake fire!', after the British volley",
     # docs/research/50: in v2 entries the command release models the recorded order.
     "provenance": "authored: in v2 entries a follow-up to the companies still holding fire; the recorded order "
                   "is the command release (fire.release_by, docs/research/50). In v1 entries this order stood "
                   "for it, its trigger a delivered loss report (reconstruction, doc 48)"},
    {"id": "cross", "trigger": "fire released and no fresh British contact within 2 hexes of the far end",
     "stance": "move", "source": "doc 43 §5 S1: 'cross when the guard is broken'; S47: the militia held the bridge",
     "provenance": "reconstruction: no crossing order was read"},
)
REGULARS_ORDERS = (
    {"id": "open-fire", "trigger": "the entry's initial fire posture, not a sent order", "stance": "open_fire",
     "source": "S47: the British fired into the column 'without an order to fire'",
     "provenance": "sourced: S47"},
    {"id": "guard", "trigger": "start; once per company", "stance": "hold",
     "source": "S47: Laurie's companies guarded the bridge; doc 43 §1: no order to Laurie was read",
     "provenance": "reconstruction: inferred from the post"},
    {"id": "fall-back", "trigger": "two of three companies routed, lost or below half strength",
     "stance": "retreat", "source": "doc 43 §5 S1; S47: the British withdrew toward the town",
     "provenance": "reconstruction: the trigger and the half-strength floor are authored"},
)
FRESH = 1  # A contact older than this many intervals no longer shows the far end held.
CLEAR_RADIUS = 2  # Hexes around the far end that must be clear: the smoothbore range.


def _able(u):
    return (u["status"] not in ("lost", "routed", "merged") and not u.get("leaderless")
            and u.get("accepts_orders", True))


def _sent(observation):
    """Unit id -> the (stance, destination) pairs this side has already sent."""
    sent = {}
    for o in observation.get("orders", ()):
        sent.setdefault(o["unit_id"], set()).add((o["stance"], tuple(o["destination"] or ()) or None))
    return sent


def _order(uid, stance, destination=None):
    return {"unit_id": uid, "stance": stance, "destination": list(destination) if destination else None}


def militia_actions(observation):
    """Why: the provincial side must advance under Barrett's instruction and
    open fire once fired upon (S47), as doc 43 §5 S1 reconstructs. In v2
    entries Buttrick's order is the command release (docs/research/50) and
    the ``fire`` order here is authored follow-up.
    What: ``([], orders)``, at most three orders, in this priority: the
    ``advance`` and ``follow`` moves to ``APPROACH`` once per company; the
    ``fire`` order to every company reported holding fire once headquarters
    knows of a provincial loss; then the ``cross`` moves (lead company to the
    far end, the next onto the bridge) once every company has its fire order
    and no contact at most ``FRESH`` intervals old stands within
    ``CLEAR_RADIUS`` of the far end. No order is sent twice. Nothing while
    the command is disrupted.
    Test: `test_militia_advance_with_the_acton_company_leading`,
    `test_militia_give_buttricks_fire_order_once_fired_upon`,
    `test_militia_cross_once_no_fresh_british_contact_holds_the_far_end`.
    """
    if observation.get("command", {}).get("operational") is False:
        return [], []
    live = sorted((u for u in observation["units"] if _able(u)), key=lambda u: u["id"])
    sent = _sent(observation)
    orders = []
    for u in live:  # MILITIA_ORDERS advance (P1) and follow (the rest).
        if u["id"] in APPROACH and not any(s == "move" for s, _ in sent.get(u["id"], ())):
            orders.append(_order(u["id"], "move", APPROACH[u["id"]]))
    fired_upon = any(u["strength"] < u["initial"] for u in observation["units"])
    owed = [u for u in live if u.get("fire_posture") == "hold_fire"
            and ("open_fire", None) not in sent.get(u["id"], ())]
    if fired_upon:  # MILITIA_ORDERS fire.
        orders.extend(_order(u["id"], "open_fire") for u in owed)
    held = any(c.get("age", 0) <= FRESH and grid.distance(c["pos"], EAST_END) <= CLEAR_RADIUS
               for c in observation.get("contacts", ()))
    if fired_upon and not owed and not held:  # MILITIA_ORDERS cross.
        for u, target in zip(live, (EAST_END, BRIDGE)):
            if u["pos"] != list(target) and ("move", tuple(target)) not in sent.get(u["id"], ()):
                orders.append(_order(u["id"], "move", target))
    return [], orders[:3]


def regulars_actions(observation):
    """Why: the British guard must hold the crossing and give way as doc 43
    §5 S1 reconstructs; no order to Laurie was read (doc 43 §1).
    What: ``([], orders)``, at most three. While fewer than two thirds of the
    companies are routed, lost or below half strength, each able company not
    yet ordered gets the ``guard`` hold once. From then on, each able
    company gets the ``fall-back`` retreat to ``TOWN`` once. The British fire
    without an order (the entry's open-fire posture). Nothing while the
    command is disrupted.
    Test: `test_regulars_guard_the_crossing_then_fall_back_to_the_town`.
    """
    if observation.get("command", {}).get("operational") is False:
        return [], []
    units = observation["units"]
    live = sorted((u for u in units if _able(u)), key=lambda u: u["id"])
    sent = _sent(observation)
    broken = [u for u in units if u["status"] in ("routed", "lost") or u["strength"] * 2 < u["initial"]]
    orders = []
    if len(broken) * 3 >= len(units) * 2:  # REGULARS_ORDERS fall-back.
        orders = [_order(u["id"], "retreat", TOWN) for u in live
                  if ("retreat", tuple(TOWN)) not in sent.get(u["id"], ())]
    else:  # REGULARS_ORDERS guard.
        orders = [_order(u["id"], "hold") for u in live if not sent.get(u["id"])]
    return [], orders[:3]
