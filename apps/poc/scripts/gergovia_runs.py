"""Print one comparison row per Gergovia run (docs/research/62).

Why: doc 62 compares the default with doc 57 §8's named variants, scored by
the doc 57 §5 metrics; this prints its table from fresh runs.
What: runs each named entry (``--only NAME``, repeatable; default all:
``default`` and every ``scenario_gergovia.VARIANTS`` entry) headless in its
own database under ``--dir`` (default: a temporary directory), stored by
``BatchStore`` (start and end snapshots only). For each it prints one JSON
line: the winner, end turn and clock time, the reason, replay status, the
recovered turn, per forward group the recall receipt (turn, reason, obeyed),
the furthest row reached (lowest row number), its end strength, status and
hex, the exploit events, the men recovered within the rally radius at the
end, the spread in turns between the forward groups' first retreat moves,
the Gallic return and push orders' first turns, losses per side, routed
units and the event count. The engine draws no random number.
Usage, from apps/poc: ``python3 scripts/gergovia_runs.py [--only default]``.
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle import grid  # noqa: E402
from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.scenario_gergovia import (  # noqa: E402
    FORWARD, GERGOVIA_RECALL, PUSH_TO, RALLY, RALLY_RADIUS, UNDER_WALL, VARIANTS,
)

ENTRIES = {"default": GERGOVIA_RECALL, **{n: v.entry for n, v in VARIANTS.items()}}


def clock(turn):
    minutes = 12 * 60 + turn // 2
    return f"{minutes // 60:02d}:{minutes % 60:02d}:{30 * (turn % 2):02d}"


def _first_order(final, uid, destination):
    return min((e["turn"] for e in final["events"] if e["kind"] == "order_sent" and e["unit_id"] == uid
                and list(e.get("destination") or ()) == list(destination)), default=None)


def summarise(name, entry, result, final, seconds):
    ev = final["events"]
    units = {u["id"]: u for u in final["units"]}
    start = {u.id: list(u.pos) for u in entry.units}
    lost, initial = {}, {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
        initial[u["side"]] = initial.get(u["side"], 0) + u["initial"]
    receipts = final["broadcasts"][0]["receipts"]
    groups = {}
    for uid in FORWARD:
        rows = [e["destination"][1] for e in ev if e["kind"] == "unit_moved" and e["unit_id"] == uid]
        u = units[uid]
        r = receipts.get(uid)
        groups[uid] = {"recall": r and (r["turn"], r["reason"], r["obeyed"]),
                       "furthest_row": min(rows + [start[uid][1]]), "end": (u["strength"], u["status"], u["pos"]),
                       "leaderless": u.get("leaderless", False)}
    back = [min((e["turn"] for e in ev if e["kind"] == "unit_moved" and e["unit_id"] == uid
                 and grid.distance(e["destination"], RALLY) < grid.distance(e["origin"], RALLY)
                 and e["destination"][1] > e["origin"][1]), default=None) for uid in FORWARD]
    back = [t for t in back if t is not None]
    recovered = sum(u["strength"] for uid, u in units.items() if uid in FORWARD and u["strength"] > 0
                    and u["status"] not in ("lost", "routed", "merged")
                    and grid.distance(u["pos"], RALLY) <= RALLY_RADIUS)
    return {
        "run": name, "entry": entry.id, "winner": final["winner"], "turn": final["turn"],
        "time": clock(final["turn"]), "reason": final["reason"], "replay": result["replay"]["status"],
        "recovered_turn": final["victory"]["recovered_turn"], "recovered_men": recovered,
        "needed": final["victory"]["recover_needed"], "groups": groups,
        "withdraw_spread": (max(back) - min(back)) if len(back) > 1 else None, "withdrawing_groups": len(back),
        "exploit": [(e["unit_id"], e["kind"], e["turn"], e.get("reason")) for e in ev
                    if e["kind"] in ("exploit_started", "exploit_stopped")],
        "gallic_return": {uid: _first_order(final, uid, UNDER_WALL[uid]) for uid in UNDER_WALL},
        "gallic_push": {uid: _first_order(final, uid, PUSH_TO) for uid in UNDER_WALL},
        "sextius_out": _first_order(final, "R13", (6, 19)),
        "losses": {s: f"{lost[s]}/{initial[s]}" for s in sorted(lost)},
        "routed": sorted(e["unit_id"] for e in ev if e["kind"] == "unit_routed"),
        "events": len(ev), "seconds": round(seconds, 1),
    }


def run(name, directory):
    entry = ENTRIES[name]
    db = Path(directory) / f"gergovia-{name}.sqlite"
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
