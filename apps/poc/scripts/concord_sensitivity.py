"""Print one comparison row per Concord geometry run (docs/research/49).

Why: doc 49 compares the baseline Concord run with each geometry
sensitivity variant; this prints its table from fresh runs.
What: runs the baseline ``concord-north-bridge``, each variant in
``concord_sensitivity.SENSITIVITY`` and, for reference, the doc 43
``british-west-bank`` variant, each headless in its own temporary database.
For each it prints the summary line, then the ring around the bridge (radius 1)
at the start, at the turn the decisive hold began (the capture turn) and at
the end, the losses per side, the historical event checks of doc 48 §6, and
the provincial companies whose approach hex is within musket range of B1's
start hex. Unit positions are rebuilt from ``unit_moved`` events and checked
against the saved final state.
Usage, from apps/poc: ``python3 scripts/concord_sensitivity.py``.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle import grid  # noqa: E402
from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.concord_sensitivity import BASELINE_GEOMETRY, SENSITIVITY, SENSITIVITY_GEOMETRY  # noqa: E402
from battle.scenario_concord import CONCORD_NORTH_BRIDGE, VARIANTS  # noqa: E402
from battle.scenario_entry import build_state  # noqa: E402


def run(entry):
    scenarios = ScenarioRegistry([entry])
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "concord.sqlite"
        result = build_headless(db, scenario_id=entry.id, scenarios=scenarios).run()
        return result, build_replay(db).repository.load(result["game_id"])


def per_turn(entry, final):
    """Turn -> {unit id: (pos, effective)} after that turn's events."""
    units = {u["id"]: [u["pos"], True] for u in build_state(entry)["units"]}
    turns, events = {0: None}, sorted(final["events"], key=lambda e: e["seq"])
    for t in range(final["turn"] + 1):
        for e in (e for e in events if e["turn"] == t):
            if e["kind"] == "unit_moved":
                units[e["unit_id"]][0] = e["destination"]
            elif e["kind"] == "unit_routed" or (e["kind"] == "casualties" and e["remaining"] == 0):
                units[e["unit_id"]][1] = False
        turns[t] = {uid: (list(p), ok) for uid, (p, ok) in units.items()}
    last = turns[final["turn"]]
    assert all(last[u["id"]][0] == u["pos"] for u in final["units"]), "rebuilt positions differ"
    return turns


def ring(snapshot, bridge):
    return sorted(uid for uid, (pos, ok) in snapshot.items() if ok and grid.distance(pos, bridge) <= 1)


def checks(final):
    events = final["events"]
    volleys = [e for e in events if e["kind"] == "volley"]
    side = {u["id"]: u["side"] for u in final["units"]}
    first_prov = next((v for v in volleys if side[v["unit_id"]] == "provincial"), None)
    first_brit = next((v for v in volleys if side[v["unit_id"]] == "british"), None)
    return {
        "british fire first": bool(volleys) and side[volleys[0]["unit_id"]] == "british",
        "provincials fire only when fired upon": first_prov is not None and first_brit is not None
        and first_brit["seq"] < first_prov["seq"] and bool(first_prov.get("returning_fire")),
        "open-fire order set": any(e["kind"] == "fire_posture_set" and side[e["unit_id"]] == "provincial"
                                   for e in events),
        "british withdraw": any(e["kind"] == "local_decision" and side[e["unit_id"]] == "british"
                                and e["action"] == "withdraw" for e in events)
        or any(o["side"] == "british" and o["stance"] == "retreat" for o in final["orders"]),
        "militia hold the bridge": final["winner"] == "provincial" and "held the bridge" in final["reason"],
    }


def report(name, entry, geometry):
    result, final = run(entry)
    print(f"== {name}")
    print({k: v for k, v in result.items() if k not in ("game_id", "run")})
    bridge = list(entry.victory.objective)
    turns = per_turn(entry, final)
    sides = {u["id"]: u["side"] for u in final["units"]}
    capture = None
    if final["winner"] == "provincial" and "held the bridge" in final["reason"]:
        capture = final["turn"] - final["capture"] + 1
    print("ring at start", ring(turns[0], bridge))
    if capture is not None:
        print(f"ring at capture turn {capture}", ring(turns[capture], bridge))
    print(f"ring at end turn {final['turn']}", ring(turns[final['turn']], bridge))
    lost = {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
    initial = {}
    for u in final["units"]:
        initial[u["side"]] = initial.get(u["side"], 0) + u["initial"]
    print("losses", {s: f"{lost[s]}/{initial[s]}" for s in sorted(lost)})
    print("checks", {k: "yes" if v else "no" for k, v in checks(final).items()})
    if geometry is not None:
        b1 = geometry.british["B1"]
        reach = sorted(uid for uid, p in geometry.approach.items() if grid.distance(p, b1) <= 2)
        print("approach hexes within 2 of B1", reach)
    print("end", final["winner"], final["turn"], final["reason"], "sides in ring at end",
          sorted({sides[u] for u in ring(turns[final["turn"]], bridge)}))


def main():
    report("baseline concord-north-bridge", CONCORD_NORTH_BRIDGE, BASELINE_GEOMETRY)
    for name, variant in SENSITIVITY.items():
        report(name, variant.entry, SENSITIVITY_GEOMETRY[name])
    report("british-west-bank (doc 43 variant, reference)", VARIANTS["british-west-bank"].entry, None)


if __name__ == "__main__":
    main()
