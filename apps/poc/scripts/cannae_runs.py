"""Print one comparison row per Cannae run (docs/research/68).

Why: doc 68 compares the default with doc 63 §8's named variants, scored by
the ``encircle`` kind and the doc 63 §5 records; this prints its table from
fresh runs.
What: runs each named entry (``--only NAME``, repeatable; default all:
``default`` and every ``scenario_cannae.VARIANTS`` entry) headless in its own
database under ``--dir`` (default: a temporary directory), stored by
``BatchStore`` (start and end snapshots only), with the closing replay check.
For each it prints one JSON line: the winner, end turn and clock time, the
reason, replay status, the pocket's closing interval on the ground and in each
headquarters' delivered reports, the most units and men enclosed at any
interval and when, the last ``record`` row, the attacker units that reached an
exit (interval and men), per unit the end strength, status, hex and front,
the yields, wheels and exploit events, each cavalry unit's first fight and the
interval it left it, Hasdrubal's pursuit (D34), ride and charge order turns, delivered orders
and their mean delay per side, losses per side against the sources' order of
magnitude, routed and lost units and the event count. The engine draws no
random number.
Usage, from apps/poc: ``python3 scripts/cannae_runs.py [--only default]``.
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.scenario_cannae import (  # noqa: E402
    CANNAE_ENVELOPMENT, HASDRUBAL, RIDE, SECONDS_PER_TURN, VARIANTS,
)

ENTRIES = {"default": CANNAE_ENVELOPMENT, **{n: v.entry for n, v in VARIANTS.items()}}
CAVALRY = ("EQ", "SC1", "SC2") + HASDRUBAL + ("NU1", "NU2")
# Order-of-magnitude checks only (doc 63 §5): S65 III.117, S66 XXII.49.
SOURCES = {"roman_dead": {"S65": 70000, "S66": 47200}, "carthaginian_dead": {"S65": 5700}}


def clock(turn):
    seconds = 8 * 3600 + turn * SECONDS_PER_TURN
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _first_fight(events, uid):
    """The first interval ``uid`` fired or was hit, and the first interval after it with neither."""
    turns = sorted({e["turn"] for e in events if (e["kind"] == "volley" and uid in (e["unit_id"], e["target_id"]))
                    or (e["kind"] == "casualties" and e["unit_id"] == uid)})
    if not turns:
        return None
    end = turns[0]
    for t in turns[1:]:
        if t > end + 1:
            break
        end = t
    return {"first": turns[0], "left": end + 1}


def summarise(name, entry, result, final, seconds):
    ev = final["events"]
    v = final["victory"]
    lost, initial = {}, {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
        initial[u["side"]] = initial.get(u["side"], 0) + u["initial"]
    peak = max(v["record"], key=lambda r: (r[2], -r[0]), default=None)
    orders = {}
    for o in final["orders"]:
        if o["status"] == "delivered":
            orders.setdefault(o["side"], []).append(o["arrival_turn"] - o["sent_turn"] if o["arrival_turn"] else 0)
    first_order = lambda uid, dest: min((e["turn"] for e in ev if e["kind"] == "order_sent" and e["unit_id"] == uid
                                         and (dest is None or list(e.get("destination") or ()) == list(dest))),
                                        default=None)
    ride = {uid: first_order(uid, RIDE[uid]) for uid in HASDRUBAL}
    rode = min((t for t in ride.values() if t is not None), default=None)
    # D34: a move off the ride hex before the ride is a pursuit of EQ; from the ride on, the charge.
    other = {uid: [e["turn"] for e in ev if e["kind"] == "order_sent" and e["unit_id"] == uid
                   and e.get("destination") and list(e["destination"]) != list(RIDE[uid])] for uid in HASDRUBAL}
    return {
        "run": name, "entry": entry.id, "winner": final["winner"], "turn": final["turn"],
        "time": clock(final["turn"]), "reason": final["reason"], "replay": result["replay"]["status"],
        "closed_turn": v["closed_turn"], "known_closed_turn": v["known_closed_turn"],
        "peak_enclosed": peak and {"turn": peak[0], "units": peak[1], "men": peak[2]},
        "last_record": v["record"][-1] if v["record"] else None, "exited": v["exited"],
        "units": {u["id"]: [u["strength"], u["status"], u["pos"], u.get("front")] for u in final["units"]},
        "yields": {u["id"]: u["yielded"] for u in final["units"] if u.get("yielded")},
        "wheels": {e["unit_id"]: e["turn"] for e in ev if e["kind"] == "unit_wheeled"},
        "exploit": [(e["unit_id"], e["kind"], e["turn"], e.get("reason")) for e in ev
                    if e["kind"] in ("exploit_started", "exploit_stopped")],
        "cavalry_fight": {uid: _first_fight(ev, uid) for uid in CAVALRY if any(u["id"] == uid for u in final["units"])},
        "pursue": {uid: [t for t in other[uid] if rode is None or t < rode] for uid in HASDRUBAL},
        "ride": ride,
        "charge": {uid: min((t for t in other[uid] if rode is not None and t >= rode), default=None)
                   for uid in HASDRUBAL},
        "orders_delivered": {side: [len(d), round(sum(d) / len(d), 1) if d else None] for side, d in orders.items()},
        "losses": {s: f"{lost[s]}/{initial[s]}" for s in sorted(lost)}, "sources": SOURCES,
        "routed": sorted({e["unit_id"] for e in ev if e["kind"] == "unit_routed"}),
        "lost_units": sorted(u["id"] for u in final["units"] if u["status"] == "lost"),
        "events": len(ev), "seconds": round(seconds, 1),
    }


def run(name, directory):
    entry = ENTRIES[name]
    db = Path(directory) / f"cannae-{name}.sqlite"
    began = time.monotonic()
    result = build_headless(db, scenario_id=entry.id, scenarios=ScenarioRegistry([entry]), keyframe_every=0).run()
    final = build_replay(db).repository.load(result["game_id"])
    return summarise(name, entry, result, final, time.monotonic() - began)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=sorted(ENTRIES))
    parser.add_argument("--dir", help="keep the databases here (default: a temporary directory)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        for name in args.only or list(ENTRIES):
            print(json.dumps(run(name, args.dir or tmp), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
