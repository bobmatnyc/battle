"""poc-11: attackers push through a gateway held by the enemy, and poc-10
saves keep their exact behaviour. Design: docs/research/44.

On the gate fixture (see test_gates) the walled farm is back room 9,10, farm
10,10 and courtyard 11,10, the gateway, whose gate opens onto 12,10. B1
commands blue; B2 holds the gateway; G1, grey's commander, stands on the
outside hex, so its orders go by voice.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from battle import engine, engine_v10, runtime, scenario
from battle.bootstrap import build_headless, build_replay
from battle.scenario_entry import build_state, dry_run, validate
from battle.scenario_hougoumont import COMPOUND, HOUGOUMONT_NORTH_GATE as HOUGOUMONT
from scenario_fixtures import GATE_OUTSIDE, GATEWAY, gate_entry
from test_gates import advance_through_service
from test_hougoumont import EngineRun, catalog
from test_scenario_sides import digest, play

FARM, BACK_ROOM, OUTSIDE_WALLS = [10, 10], [9, 10], (9, 13)
KEY = "walled-farm/farm-gate"


def held_gateway(b1=OUTSIDE_WALLS, farm=True, rules="poc-11"):
    """B2 holds the gateway and G1 stands on the outside hex, both armed. B3
    fills the farm (else it is free and B2 takes cover in it); B1 stands at
    ``b1``. By default only the back room is free inside the walls. The
    poc-11 rule is the default here; poc-12 changes it (test_contact)."""
    extra = (("B2", "blue", GATEWAY),) + ((("B3", "blue", FARM),) if farm else ())
    entry = gate_entry(positions={"B1": b1, "G1": GATE_OUTSIDE, "G2": (20, 18)}, extra=extra, armed=("B2", "G1"))
    return build_state(dry_run(validate(entry)), rules)


def push_in(s):
    """Grey's commander orders itself into the farm, by voice."""
    decision = {"side": "grey", "source": "scripted", "orders": [
        {"unit_id": "G1", "destination": FARM, "stance": "move"}]}
    return runtime.apply(s, {"type": "decision", "decision": decision})


def advance(s, n=1):
    for _ in range(n):
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def unit(s, uid):
    return engine.find_unit(s, uid)


def events(s, kind):
    return [e for e in s["events"] if e["kind"] == kind]


def live_hexes(s):
    return [tuple(u["pos"]) for u in s["units"] if u["strength"] > 0]


class GatewayPushTests(unittest.TestCase):
    def test_push_effort_accumulates_against_a_held_gateway(self):
        s = advance(push_in(held_gateway()))
        self.assertEqual((unit(s, "G1")["pos"], unit(s, "B2")["pos"]), (GATE_OUTSIDE, GATEWAY))
        self.assertEqual(s["push_effort"][KEY], 20)  # min(strength 40, push_cap 20).
        push = events(s, "gateway_push")[0]
        self.assertEqual((push["holder_id"], push["pushers"], push["labor"], push["required"]),
                         ("B2", ["G1"], 20, 40))
        self.assertTrue(push["under_fire"])  # B2 fires on G1; the push goes on.
        self.assertEqual(events(s, "gateway_carried"), [])

    def test_holder_is_displaced_inside_at_the_threshold(self):
        s = advance(push_in(held_gateway()), 2)
        carried = events(s, "gateway_carried")[0]
        self.assertEqual((carried["unit_id"], carried["holder_id"], carried["outcome"]), ("G1", "B2", "displaced"))
        self.assertEqual((unit(s, "G1")["pos"], unit(s, "B2")["pos"]), (GATEWAY, BACK_ROOM))
        self.assertEqual(s["push_effort"][KEY], 0)
        self.assertEqual(len(live_hexes(s)), len(set(live_hexes(s))))  # Still no stacking.
        self.assertEqual(s["map_features"][0]["openings"][0]["state"], "open")

    def test_holder_is_overrun_when_no_inside_hex_is_free(self):
        s = advance(push_in(held_gateway(b1=BACK_ROOM)), 2)
        carried = events(s, "gateway_carried")[0]
        self.assertEqual(carried["outcome"], "overrun")
        self.assertGreater(carried["losses"], 0)
        self.assertEqual((unit(s, "B2")["strength"], unit(s, "B2")["status"]), (0, "lost"))
        self.assertEqual((unit(s, "G1")["pos"], unit(s, "B3")["pos"], unit(s, "B1")["pos"]), (GATEWAY, FARM, BACK_ROOM))
        self.assertEqual(len(live_hexes(s)), len(set(live_hexes(s))))

    def test_push_resets_when_the_holder_leaves_the_gateway(self):
        # With the farm free, B2 takes cover there in the second interval.
        s = advance(push_in(held_gateway(b1=BACK_ROOM, farm=False)))
        self.assertEqual(s["push_effort"][KEY], 20)
        s = advance(s)
        self.assertEqual((unit(s, "B2")["pos"], unit(s, "G1")["pos"]), (FARM, GATE_OUTSIDE))
        self.assertEqual(s["push_effort"][KEY], 0)
        self.assertEqual(events(s, "gateway_push_interrupted")[0]["effort"], 20)
        self.assertEqual(events(s, "gateway_carried"), [])

    def test_headquarters_learns_of_the_push_only_by_report(self):
        s = advance(push_in(held_gateway()), 2)
        self.assertEqual(unit(s, "B2")["pos"], BACK_ROOM)
        seen = {u["id"]: u["pos"] for u in engine.view(s, "blue")["units"]}
        self.assertEqual(seen["B2"], GATEWAY)  # Blue still holds the old report.
        self.assertFalse(any("pushed through" in d["text"] for d in s["dispatches"]["blue"]))
        self.assertTrue(any("pushed through" in (r["text"] or "") for r in s["reports"] if r["side"] == "blue"))
        view = json.dumps(engine.view(s, "blue"))
        self.assertNotIn("push_effort", view)
        # A blue order is addressed and estimated from the reported hex.
        s = runtime.apply(s, {"type": "orders", "orders": [{"unit_id": "B2", "destination": None, "stance": "hold"}]})
        self.assertEqual(s["orders"][-1]["transport"]["address"], GATEWAY)
        for _ in range(8):
            if any("pushed through" in d["text"] for d in s["dispatches"]["blue"]):
                break
            s = advance(s)
        self.assertTrue(any("pushed through" in d["text"] for d in s["dispatches"]["blue"]))

    def test_push_run_replays_identical(self):
        run = EngineRun(held_gateway())
        run.step({"type": "decision", "decision": {"side": "grey", "source": "scripted", "orders": [
            {"unit_id": "G1", "destination": FARM, "stance": "move"}]}})
        for _ in range(4):
            run.advance()
        self.assertTrue(events(run.state, "gateway_carried"))
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")


def at_the_north_gate(rules):
    """Hougoumont with Legros's party on the gate's outside hex and the
    follow-on companies near it, both ordered into the farm and holding
    firmly; the gate party and A2 have no cartridges and A3 is away."""
    s = build_state(HOUGOUMONT, rules)
    place = {"A1": {"ammo": 0}, "A2": {"ammo": 0}, "A3": {"pos": [11, 3]},
             "F1": {"pos": [11, 8], "stance": "move", "target": [10, 10], "standing_profile": "firm"},
             "F2": {"pos": [9, 7], "stance": "move", "target": [10, 11], "standing_profile": "firm"}}
    for u in s["units"]:
        u.update(place.get(u["id"], {}))
    return s


class HougoumontPushTests(unittest.TestCase):
    def test_scripted_hougoumont_run_on_poc12(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "hougoumont.sqlite"
            result = build_headless(db, scenario_id=HOUGOUMONT.id, scenarios=catalog()).run()
            final = build_replay(db).repository.load(result["game_id"])
        self.assertEqual(result["replay"]["status"], "identical")
        # Both gate-aware controls (docs/research/44): the French halt under fire from
        # the walls before the outside hex, so nobody pushes; the garrison is shot away.
        self.assertEqual(result["run"]["opponent"], "scripted-gate-attacker-v1")
        self.assertEqual((final["rules"], final["winner"], final["turn"]), ("poc-12", "french", 58))
        self.assertEqual(final["reason"], "Allied formations can no longer hold the farm.")
        self.assertEqual((events(final, "gateway_push"), final["push_effort"]), ([], {}))
        farm = next(f for f in final["map_features"] if f["id"] == "hougoumont")
        self.assertEqual(farm["openings"][0]["state"], "open")
        self.assertEqual((events(final, "units_cut_off"), final["capture"]), ([], 0))

    def test_french_carry_the_held_north_gate(self):
        run = EngineRun(at_the_north_gate("poc-11"))
        run.step({"type": "standing", "instruction": {"unit_id": "A1", "profile_id": "close_on_breach"}})
        while run.state["status"] == "active":
            run.advance()
        carried = events(run.state, "gateway_carried")
        self.assertEqual([(e["turn"], e["unit_id"], e["holder_id"], e["outcome"], e["holder_pos"]) for e in carried],
                         [(3, "F1", "A1", "displaced", [11, 10])])
        self.assertIn(list(run.unit("F1")["pos"]), COMPOUND)
        self.assertEqual((run.state["winner"], run.state["turn"], run.state["capture"]), ("french", 15, 6))
        self.assertEqual(run.gate()["state"], "open")  # The gate party broke at turn 3.
        self.assertEqual(events(run.state, "units_cut_off"), [])
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")


# Taken at 2e773e5, before poc-11: the scripted poc-10 Little Round Top run
# (test_scenario_sides.play), and poc-10 saves advanced through BattleService
# (Little Round Top 10 then 30 intervals; Hougoumont 40), and the poc-10 north
# gate arrangement below advanced 15 intervals, as sha256 of the sort-keyed
# JSON state.
POC10_LRT_RUN_SHA256 = "042ef7d02542e1cbfbbe1d9289267651c280788e697a8989619ded817b65de65"
POC10_LRT_SAVE_ADVANCED_SHA256 = "d1a5da1d36004d3ec646e4d35a5c9af2768304ffa969f8dbf5dd8b4b943bcd74"
POC10_HOUGOUMONT_SAVE_ADVANCED_SHA256 = "8e3c56f86394c5d85d37367588d3c796138505ad3d0c0d1d1c754049cd8af0c2"
POC10_AT_THE_NORTH_GATE_SHA256 = "f7f94db46d705f2aabf5f15f141614499a065c4d41814b5ff54eab38476a12cb"


def as_poc10(state):
    """A poc-11 Little Round Top snapshot written in poc-10 terms."""
    text = json.dumps(state, sort_keys=True)
    return json.loads(text.replace('"poc-11"', '"poc-10"').replace("little-round-top-v11", "little-round-top-v10"))


class Poc11EditionTests(unittest.TestCase):
    def test_little_round_top_poc11_plays_identically_to_poc10(self):
        start = scenario.create("poc-11")
        self.assertEqual((start["rules"], start["scenario"]), ("poc-11", "little-round-top-v11"))
        self.assertNotIn("push_rules", start)
        self.assertEqual(as_poc10(start), scenario.create("poc-10"))
        self.assertEqual(digest(as_poc10(play(start))), POC10_LRT_RUN_SHA256)

    def test_poc10_saves_advance_through_the_frozen_engine(self):
        with mock.patch.object(engine_v10, "advance", wraps=engine_v10.advance) as frozen:
            save = advance_through_service(scenario.create("poc-10"), 10)
            final = advance_through_service(json.loads(json.dumps(save, sort_keys=True)), 30)
            hougoumont = advance_through_service(build_state(HOUGOUMONT, "poc-10"), 40, (scenario.LITTLE_ROUND_TOP, HOUGOUMONT))
        self.assertEqual(frozen.call_count, 40 + hougoumont["turn"])
        self.assertEqual((final["rules"], final["turn"]), ("poc-10", 40))
        self.assertEqual(digest(final), POC10_LRT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(hougoumont), POC10_HOUGOUMONT_SAVE_ADVANCED_SHA256)

    def test_poc10_hougoumont_never_pushes(self):
        s = at_the_north_gate("poc-10")
        self.assertNotIn("push_rules", s)
        while s["status"] == "active" and s["turn"] < 15:
            s = runtime.apply(s, {"type": "advance", "decision": None})
        self.assertEqual(events(s, "gateway_push"), [])
        self.assertEqual(digest(s), POC10_AT_THE_NORTH_GATE_SHA256)

    def test_gateway_push_is_authored_and_required_with_openings(self):
        import dataclasses
        with self.assertRaisesRegex(ValueError, "authored gateway push is required"):
            validate(dataclasses.replace(gate_entry(), gateway_push=None))
        s = build_state(HOUGOUMONT)
        self.assertEqual(s["push_rules"], {"push_labour": 60, "push_cap": 20,
                                           "basis": "authored sensitivity parameter; not a historical estimate"})
        self.assertTrue(HOUGOUMONT.provenance["gateway_push"].startswith("authored:"))
