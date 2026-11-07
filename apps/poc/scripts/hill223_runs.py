"""Print one comparison row per Hill 223 run (docs/research/61).

Why: doc 61 compares the default with doc 56 §8's named variants; this prints
its table from fresh runs.
What: runs each named entry (``--only NAME``, repeatable; default all:
``default`` and every ``scenario_hill223.VARIANTS`` entry) headless in its own
database under ``--dir`` (default: a temporary directory), stored by
``BatchStore`` (start and end snapshots only). For each it prints one JSON
line: the winner, end turn and clock time, the reason, replay status, the
raid turn, each surrender (turn, unit, holder, count), the captives held at
the end, each gun turn (unit, start and ready turn), the patrol's first
volley and whether it was return fire, the last German gun volley, the
patrol's strength and position at the end, whether the return leg kept to
the approach route on the German hill, losses per side and the event count.
The engine draws no random number.
Usage, from apps/poc: ``python3 scripts/hill223_runs.py [--only default]``.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.scenario_hill223 import GERMAN_HILL_COLS, HILL_223_PATROL, VARIANTS  # noqa: E402

ENTRIES = {"default": HILL_223_PATROL, **{n: v.entry for n, v in VARIANTS.items()}}
GUNS = ("D2", "D3", "D4")


def clock(turn):
    minutes = 6 * 60 + 45 + turn // 2
    return f"{minutes // 60:02d}:{minutes % 60:02d}:{30 * (turn % 2):02d}"


def legs(events):
    """The patrol's hexes on the German hill before and after its press began."""
    start = next((e["turn"] for e in events if e["kind"] == "exploit_started" and e["unit_id"] == "A1"), None)
    out, back = set(), set()
    for e in events:
        if e["kind"] == "unit_moved" and e["unit_id"] == "A1" and e["destination"][0] < GERMAN_HILL_COLS:
            (back if start is not None and e["turn"] >= start else out).add(tuple(e["destination"]))
    return out, back


def summarise(name, entry, result, final):
    ev = final["events"]
    lost, initial = {}, {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
        initial[u["side"]] = initial.get(u["side"], 0) + u["initial"]
    patrol = next(u for u in final["units"] if u["id"] == "A1")
    first = next((e for e in ev if e["kind"] == "volley" and e["unit_id"] == "A1"), None)
    out, back = legs(ev)
    return {
        "run": name, "entry": entry.id, "winner": final["winner"], "turn": final["turn"],
        "time": clock(final["turn"]), "reason": final["reason"], "replay": result["replay"]["status"],
        "raided_turn": final["victory"]["raided_turn"],
        "surrenders": [(e["turn"], e["unit_id"], e["holder_id"], e["count"]) for e in ev
                       if e["kind"] == "unit_surrendered"],
        "escaped": [(e["turn"], e["holder_id"], e["count"]) for e in ev if e["kind"] == "captives_escaped"],
        "captives_held": sum(k["count"] for k in final.get("captives", ()) if k["status"] == "held"),
        "gun_turns": [(e["unit_id"], e["turn"], e["ready_turn"]) for e in ev if e["kind"] == "gun_reorienting"],
        "patrol_first_volley": first and (first["turn"], first.get("returning_fire", False)),
        "patrol_fired_upon_first": next((e["turn"] for e in ev if e["kind"] == "casualties"
                                         and e["unit_id"] == "A1"), None),
        "last_gun_volley": max((e["turn"] for e in ev if e["kind"] == "volley" and e["unit_id"] in GUNS),
                               default=None),
        "exploit": [(e["kind"], e["turn"], e.get("reason")) for e in ev
                    if e["kind"] in ("exploit_started", "exploit_stopped")],
        "patrol_end": {"strength": patrol["strength"], "status": patrol["status"], "pos": patrol["pos"],
                       "leaderless": patrol.get("leaderless", False)},
        "return_on_approach_route": bool(back) and back <= out,
        "losses": {s: f"{lost[s]}/{initial[s]}" for s in sorted(lost)},
        "routed": sorted(e["unit_id"] for e in ev if e["kind"] == "unit_routed"),
        "events": len(ev),
    }


def run(name, directory):
    entry = ENTRIES[name]
    db = Path(directory) / f"hill223-{name}.sqlite"
    result = build_headless(db, scenario_id=entry.id, scenarios=ScenarioRegistry([entry]), keyframe_every=0).run()
    final = build_replay(db).repository.load(result["game_id"])
    return summarise(name, entry, result, final)


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
