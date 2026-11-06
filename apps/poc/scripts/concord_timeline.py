"""Print the key events of a scripted Concord North Bridge headless run.

Why: docs/research/48 quotes the simulated sequence, objectives and losses;
this prints them from a fresh run so the numbers can be checked.
What: runs ``concord-north-bridge`` (or ``--scenario``) headless in a new
temporary database (``--variant NAME``: that doc 43 variant from
``scenario_concord.VARIANTS``, or that doc 49 variant from
``concord_sensitivity.SENSITIVITY`` or ``RELEASE_SENSITIVITY``, instead; ``--before``: its form before
docs/research/50, ``scenario_concord.before``), prints the run summary, then one line per key event
(orders, fire, casualties, officers, routs, local withdrawals, the end).
The engine draws no random number, so every run prints the same lines.
Usage, from apps/poc: ``python3 scripts/concord_timeline.py``.
"""

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.concord_sensitivity import RELEASE_SENSITIVITY, SENSITIVITY  # noqa: E402
from battle.scenario_concord import CONCORD_NORTH_BRIDGE, VARIANTS, before  # noqa: E402

KEY = ("order_sent", "order_delivered", "order_refused", "fire_posture_set", "volley", "casualties",
       "officer_down", "unit_leaderless", "command_vacant", "command_succeeded", "unit_routed",
       "battle_ended")


def line(e):
    data = {k: v for k, v in e.items() if k not in ("seq", "turn", "kind", "transport")}
    return f"turn {e['turn']:>2}  {e['kind']:<17} {data}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="concord-north-bridge")
    known = {**VARIANTS, **SENSITIVITY, **RELEASE_SENSITIVITY}
    parser.add_argument("--variant", choices=sorted(known))
    parser.add_argument("--before", action="store_true", help="each company releases itself (doc 48)")
    args = parser.parse_args()
    scenarios, scenario_id = None, args.scenario
    if args.variant or args.before:
        entry = known[args.variant].entry if args.variant else CONCORD_NORTH_BRIDGE
        entry = before(entry) if args.before else entry
        scenarios, scenario_id = ScenarioRegistry([entry]), entry.id
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "concord.sqlite"
        result = build_headless(db, scenario_id=scenario_id, scenarios=scenarios).run()
        print(result)
        final = build_replay(db).repository.load(result["game_id"])
    last = {}
    for e in final["events"]:
        if e["kind"] in KEY:
            print(line(e))
        elif e["kind"] == "local_decision":
            # Only changes of a unit's local action, which explain movement.
            if last.get(e["unit_id"]) != e["action"]:
                last[e["unit_id"]] = e["action"]
                print(f"turn {e['turn']:>2}  local_decision    {e['unit_id']} {e['action']}: {e['reason']}")
        elif e["kind"] == "unit_moved":
            print(f"turn {e['turn']:>2}  unit_moved        {e['unit_id']} {e['origin']} -> {e['destination']}")
    print("capture", final["capture"], "reason", final["reason"])


if __name__ == "__main__":
    main()
