"""Print the before/after rows of the Concord command fire release (docs/research/50).

Why: doc 50 judges the ``release_by`` ``command`` change on the baseline,
the doc 43 variants and the doc 49 geometry variants, not on one run, and
separates its two effects: who releases the front company (attribution) and
the other hold-fire companies an earshot order would open (extra release).
What: for each case runs, each headless in its own temporary database:
``before`` (``scenario_concord.before``: each company releases itself),
``after`` (the v2 entry: the command releases the company hit), and
``earshot`` (``concord_sensitivity.earshot``: the unsourced sensitivity in
which the order opens every company in voice reach). Prints one JSON object
per run: winner, end turn, who released P1 and when, the first provincial
volley, losses and the historical event checks; then the companies the
earshot order opened before their release in ``after``, with their volleys.
Usage, from apps/poc: ``python3 scripts/concord_fire_release.py``.
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.bootstrap import build_headless, build_replay  # noqa: E402
from battle.concord_sensitivity import SENSITIVITY, earshot  # noqa: E402
from battle.scenario_concord import CONCORD_NORTH_BRIDGE, VARIANTS, before  # noqa: E402

CASES = {"baseline": CONCORD_NORTH_BRIDGE,
         **{name: VARIANTS[name].entry for name in ("british-west-bank", "planks-lifted", "two-companies")},
         **{name: variant.entry for name, variant in SENSITIVITY.items()}}


def run(entry):
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "concord.sqlite"
        result = build_headless(db, scenario_id=entry.id, scenarios=ScenarioRegistry([entry])).run()
        return result, build_replay(db).repository.load(result["game_id"])


def clock(entry, turn):
    start = datetime.fromisoformat(entry.start_local)
    return (start + timedelta(seconds=turn * entry.seconds_per_turn)).strftime("%H:%M:%S")


def releases(final):
    """Provincial unit id -> (turn, how) of its first release: a delivered
    open-fire order (with its source) or its own ``returning_fire`` volley."""
    side = {u["id"]: u["side"] for u in final["units"]}
    orders = {o["id"]: o for o in final["orders"]}
    found = {}
    for e in final["events"]:
        uid = e.get("unit_id")
        if side.get(uid) != "provincial" or uid in found:
            continue
        if e["kind"] == "fire_posture_set" and e["fire_posture"] == "open_fire":
            source = orders[e["order_id"]]["source"]
            found[uid] = (e["turn"], f"{e['order_id']} ({'command order under fire' if source == 'command_release' else 'policy order'})")
        elif e["kind"] == "volley" and e.get("returning_fire"):
            found[uid] = (e["turn"], "own release (returning_fire)")
    return found


def checks(final):
    """Doc 48 §6 event checks the engine can show, plus the event label of the
    first provincial fire (a label, not evidence of historical causation)."""
    events, side = final["events"], {u["id"]: u["side"] for u in final["units"]}
    volleys = [e for e in events if e["kind"] == "volley"]
    first_prov = next((v for v in volleys if side[v["unit_id"]] == "provincial"), None)
    first_brit = next((v for v in volleys if side[v["unit_id"]] == "british"), None)
    hit = next((e for e in events if e["kind"] == "casualties" and side[e["unit_id"]] == "provincial"), None)
    posture = first_prov and next((e for e in events if e["kind"] == "fire_posture_set"
                                   and e["unit_id"] == first_prov["unit_id"] and e["seq"] < first_prov["seq"]), None)
    return {
        "british fire first": bool(volleys) and side[volleys[0]["unit_id"]] == "british",
        "provincials fire only after provincial losses": bool(first_prov and first_brit and hit)
        and first_brit["seq"] < first_prov["seq"] and hit["turn"] <= first_prov["turn"],
        # Shows only which event label the first fire carries, not historical causation (doc 50).
        "event label only: the first provincial fire follows a delivered order": bool(posture),
        "british withdraw": any(e["kind"] == "local_decision" and side[e["unit_id"]] == "british"
                                and e["action"] == "withdraw" for e in events)
        or any(o["side"] == "british" and o["stance"] == "retreat" for o in final["orders"]),
        "militia hold the bridge": final["winner"] == "provincial" and "held the bridge" in final["reason"],
    }


def row(entry, result, final):
    side = {u["id"]: u["side"] for u in final["units"]}
    lost, total = {}, {}
    for u in final["units"]:
        lost[u["side"]] = lost.get(u["side"], 0) + u["initial"] - u["strength"]
        total[u["side"]] = total.get(u["side"], 0) + u["initial"]
    first = next((e for e in final["events"] if e["kind"] == "volley" and side[e["unit_id"]] == "provincial"), None)
    rel = releases(final)
    volleys = {}
    for e in final["events"]:
        if e["kind"] == "volley" and side[e["unit_id"]] == "provincial":
            volleys.setdefault(e["unit_id"], []).append(e["turn"])
    return {
        "winner": final["winner"] or "none", "end_turn": final["turn"], "reason": final["reason"],
        "P1_released": rel.get("P1"), "releases": rel, "volleys": volleys,
        "first_provincial_volley": first and [first["turn"], clock(entry, first["turn"]), first["unit_id"]],
        "losses": {s: f"{lost[s]}/{total[s]}" for s in ("british", "provincial")},
        "checks": {k: "yes" if v else "no" for k, v in checks(final).items()},
        "replay": result["replay"]["status"],
    }


def extra(wide, alone):
    """Companies the earshot order opened before their release in the
    hit-scope run, and their volleys before that turn."""
    found = {}
    for uid, (turn, how) in wide["releases"].items():
        if uid == "P1" or "command" not in how:
            continue
        own = alone["releases"].get(uid)
        if own is None or own[0] > turn:
            early = [t for t in wide["volleys"].get(uid, []) if own is None or t < own[0]]
            found[uid] = {"opened": turn, "own_release": own, "volleys_before_own": len(early)}
    return found


def main():
    for name, entry in CASES.items():
        rows = {"before": row(entry, *run(before(entry))), "after": row(entry, *run(entry)),
                "earshot": row(entry, *run(earshot(entry)))}
        rows["extra_release"] = extra(rows["earshot"], rows["after"])
        print(f"== {name}")
        for key, value in rows.items():
            print(key, json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
