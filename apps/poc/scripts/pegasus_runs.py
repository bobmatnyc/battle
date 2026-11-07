"""Print one comparison row per Pegasus Bridge run (docs/research/54).

Why: doc 54 compares the baseline with doc 52's named variants and the
weapon-range sensitivity; this prints its table from fresh runs.
What: runs each named entry (``--only NAME``, repeatable; default all:
``baseline``, every ``scenario_pegasus.VARIANTS``, ``RANGE_SENSITIVITY`` and
``CROSSED_SENSITIVITY`` entry) headless in its own database under ``--dir`` (default: a temporary
directory). For each it prints one JSON line: the winner, end turn and clock
time, the reason, replay status, each bridge's state changes with turn and
cause, the demolition arming turn, the seize/lapse history, each codeword's
sent and delivered turns, losses per side, the turn each reserve group first
fires, and the event count. The engine draws no random number.
Usage, from apps/poc: ``python3 scripts/pegasus_runs.py [--only baseline]``.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.scenario_pegasus import (  # noqa: E402
    CROSSED_SENSITIVITY, PEGASUS_BRIDGE, RANGE_SENSITIVITY, VARIANTS,
)

ENTRIES = {"baseline": PEGASUS_BRIDGE, **{n: v.entry for n, v in VARIANTS.items()},
           **{n: v.entry for n, v in RANGE_SENSITIVITY.items()},
           **{n: v.entry for n, v in CROSSED_SENSITIVITY.items()}}


def clock(turn):
    minutes = 25 + turn // 2
    return f"{minutes // 60:02d}:{minutes % 60:02d}:{30 * (turn % 2):02d}"


def summarise(name, entry, result, final):
    ev = final["events"]
    side = {u["id"]: u["side"] for u in final["units"]}
    lost, initial = {}, {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
        initial[u["side"]] = initial.get(u["side"], 0) + u["initial"]
    first_fire = {}
    for e in ev:
        if e["kind"] == "volley" and e["unit_id"] in ("R1", "R2"):
            first_fire.setdefault(e["unit_id"], e["turn"])
    return {
        "run": name, "entry": entry.id, "winner": final["winner"], "turn": final["turn"],
        "time": clock(final["turn"]), "reason": final["reason"], "replay": result["replay"]["status"],
        "bridge": [(e["bridge_id"], e["turn"], e["to_state"], e["cause"]) for e in ev
                   if e["kind"] == "bridge_state_changed"],
        "armed": [(e["bridge_id"], e["turn"], e["trigger"]) for e in ev if e["kind"] == "demolition_armed"],
        "seizure": final["victory"].get("history"),
        "signals_sent": [(e["codeword"], e["sender_id"], e["turn"]) for e in ev if e["kind"] == "signal_sent"],
        "signals_received": [(x["codeword"], x["sent_turn"], x["delivered_turn"])
                             for x in final.get("signals_received", {}).get("british", [])],
        "losses": {s: f"{lost[s]}/{initial[s]}" for s in sorted(lost)},
        "routed": sorted(e["unit_id"] for e in ev if e["kind"] == "unit_routed"),
        "reserve_first_fire": first_fire,
        "events": len(ev),
        "sides": sorted(set(side.values())),
    }


def run(name, directory):
    entry = ENTRIES[name]
    db = Path(directory) / f"pegasus-{name}.sqlite"
    result = build_headless(db, scenario_id=entry.id, scenarios=ScenarioRegistry([entry])).run()
    final = build_replay(db).repository.load(result["game_id"])
    return summarise(name, entry, result, final)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=sorted(ENTRIES))
    parser.add_argument("--dir", help="keep the databases here (default: a temporary directory)")
    args = parser.parse_args()
    names = args.only or list(ENTRIES)
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            print(json.dumps(run(name, args.dir or tmp), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
