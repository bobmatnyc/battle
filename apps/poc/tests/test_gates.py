"""poc-10: gates in walled buildings, the Close the gate order and the
standing close-on-breach order, on the test-only gate fixture.

The fixture's walled farm is a row of three hexes: back room 9,10 (where
B1, the blue command detachment, starts), farm 10,10 and courtyard 11,10,
the gateway, whose gate opens onto 12,10. Design: docs/research/41.
"""

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from battle import engine, grid, runtime, scenario
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import build_headless, build_replay
from battle.scenario import LITTLE_ROUND_TOP
from battle.scenario_entry import build_state, dry_run, validate
from scenario_fixtures import GATE_COMPOUND, GATE_OUTSIDE, GATEWAY, gate_entry
from test_scenario_sides import digest, play

INSIDE = [list(p) for p in GATE_COMPOUND]
FARM = [10, 10]


def battle(**fixture):
    return build_state(dry_run(validate(gate_entry(**fixture))))


def advance(s, n=1):
    for _ in range(n):
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def advance_until(s, done, limit=15):
    for _ in range(limit):
        s = advance(s)
        if done(s):
            break
    return s


def blue_orders(s, *orders):
    return runtime.apply(s, {"type": "orders", "orders": list(orders)})


def grey_orders(s, *orders):
    decision = {"side": "grey", "source": "scripted", "orders": list(orders)}
    return runtime.apply(s, {"type": "decision", "decision": decision})


def close(uid="B1"):
    return {"unit_id": uid, "destination": None, "stance": "close_gate"}


def move(uid, pos, stance="move"):
    return {"unit_id": uid, "destination": list(pos), "stance": stance}


def gate(s):
    return s["map_features"][0]["openings"][0]


def unit(s, uid):
    return engine.find_unit(s, uid)


def events(s, kind):
    return [e for e in s["events"] if e["kind"] == kind]


def transitions(s):
    return [(e["before"], e["after"]) for e in events(s, "gate_state")]


def known_state(s, side):
    return engine.view(s, side)["map_features"][0]["openings"][0]["state"]


class GateTransitionTests(unittest.TestCase):
    """One test per state transition."""

    def test_gate_opens_to_closing_when_work_starts(self):
        s = blue_orders(battle(), close())
        self.assertEqual(gate(s)["state"], "open")  # Dispatch alone changes nothing.
        self.assertEqual(s["orders"][-1]["transport"]["method"], "voice")
        s = advance(s)
        self.assertEqual(transitions(s), [("open", "closing")])
        self.assertEqual(gate(s)["effort"], 20)  # min(strength 40, work_cap 20).

    def test_closing_gate_closes_after_authored_labour(self):
        s = advance(blue_orders(battle(), close()), 2)
        self.assertEqual((gate(s)["state"], gate(s)["effort"]), ("closing", 40))
        self.assertTrue(grid.path(s["cells"], GATEWAY, GATE_OUTSIDE))
        s = advance(s)
        self.assertEqual(transitions(s), [("open", "closing"), ("closing", "closed")])
        self.assertEqual(gate(s)["effort"], 60)
        self.assertEqual(grid.path(s["cells"], GATEWAY, GATE_OUTSIDE), [])  # Sealed.

    def test_closed_gate_is_barred_with_further_labour(self):
        s = advance(blue_orders(battle(state="closed"), close()))
        self.assertEqual((gate(s)["state"], gate(s)["bar_effort"]), ("closed", 20))
        s = advance(s)
        self.assertEqual(transitions(s), [("closed", "barred")])
        self.assertEqual(unit(s, "B1")["mission_result"]["status"], "completed")

    def test_attackers_force_a_closed_gate(self):
        s = battle(state="closed", positions={"G1": (14, 9), "G2": GATE_OUTSIDE}, armed=("G2",))
        s = advance_until(grey_orders(s, move("G2", FARM)), lambda s: gate(s)["state"] != "closed")
        self.assertEqual(transitions(s), [("closed", "forced")])
        self.assertEqual((events(s, "gate_state")[0]["pushers"], gate(s)["force_effort"]), (["G2"], 80))
        work = [e["labor"] for e in events(s, "gate_work") if e["work"] == "force"]
        self.assertEqual(work, [20, 20, 20, 20])
        s = advance(s, 2)
        self.assertIn(unit(s, "G2")["pos"], INSIDE)

    def test_barred_gate_cannot_be_forced(self):
        s = battle(state="barred", positions={"G1": (14, 9), "G2": GATE_OUTSIDE}, armed=("G2",))
        s = advance(grey_orders(s, move("G2", FARM)), 10)
        self.assertEqual((gate(s)["state"], transitions(s)), ("barred", []))
        self.assertEqual(unit(s, "G2")["pos"], GATE_OUTSIDE)

    def test_forced_gate_can_be_closed_again(self):
        s = advance(blue_orders(battle(state="forced"), close()))
        self.assertEqual(transitions(s), [("forced", "closing")])
        self.assertEqual(gate(s)["effort"], 20)


class GateContactTests(unittest.TestCase):
    def test_contact_in_gateway_stops_completion_until_it_clears(self):
        # G2 stands in the gateway; G1 fires on B1 from outside the walls.
        s = battle(positions={"G1": (9, 14), "G2": GATEWAY}, armed=("G1",))
        s = advance(blue_orders(s, close()), 3)
        self.assertEqual((gate(s)["state"], gate(s)["effort"]), ("closing", 60))
        self.assertTrue(any(e["under_fire"] for e in events(s, "gate_work")))  # Work goes on under fire.
        self.assertEqual(events(s, "gate_blocked")[-1]["blockers"], ["G2"])
        self.assertEqual(unit(s, "B1")["mission_result"]["status"], "blocked")
        s = advance_until(grey_orders(s, move("G2", FARM)), lambda s: gate(s)["state"] == "closed")
        self.assertEqual(transitions(s), [("open", "closing"), ("closing", "closed")])
        self.assertEqual(unit(s, "G2")["pos"], FARM)

    def test_closed_gate_cuts_off_attackers_inside(self):
        # G2 has got into the back room; B1 closes from the farm, in cover.
        s = battle(positions={"B1": FARM, "G1": (13, 10), "G2": (9, 10)}, armed=("G2",))
        s = grey_orders(s, {"unit_id": "G2", "destination": None, "stance": "resupply"})
        s = advance(blue_orders(s, close()), 3)
        self.assertEqual(gate(s)["state"], "closed")
        g2 = unit(s, "G2")
        self.assertEqual(g2["cut_off"]["feature_id"], "walled-farm")
        self.assertEqual(events(s, "units_cut_off")[0]["unit_ids"], ["G2"])
        # No route out for troops or couriers; resupply fails locally.
        self.assertEqual(grid.path(s["cells"], g2["pos"], [13, 10]), [])
        self.assertEqual(g2["mission_result"]["status"], "failed")
        self.assertIn("Cut off", g2["mission_result"]["reason"])
        # The cut-off report travels physically and never reaches grey command;
        # a fresh order cannot get in either.
        report = next(r for r in s["reports"] if "cut off" in (r["text"] or ""))
        s = advance(grey_orders(s, move("G2", (14, 10))), 4)
        self.assertIn(unit(s, "G2")["pos"], INSIDE)
        self.assertFalse(any("cut off" in d["text"] for d in s["dispatches"]["grey"]))
        self.assertIn(report["transport"]["pos"], INSIDE)
        self.assertEqual(s["orders"][-1]["status"], "en_route")


class StandingGateTests(unittest.TestCase):
    def test_standing_order_closes_the_gate_on_a_breach(self):
        s = battle(positions={"G1": (15, 9), "G2": (14, 10)}, armed=("G2",))
        s = runtime.apply(s, {"type": "standing", "instruction": {"unit_id": "B1", "profile_id": "close_on_breach"}})
        self.assertEqual(unit(s, "B1")["standing_profile"], "balanced")  # Not applied directly.
        s = advance(s)
        self.assertEqual(unit(s, "B1")["standing_profile"], "close_on_breach")
        s = advance_until(grey_orders(s, move("G2", FARM)), lambda s: gate(s)["state"] == "closed")
        fired = events(s, "standing_gate_close")[0]
        self.assertEqual((fired["unit_id"], fired["breach"]), ("B1", ["G2"]))
        self.assertEqual(transitions(s), [("open", "closing"), ("closing", "closed")])
        self.assertEqual(unit(s, "G2")["cut_off"]["feature_id"], "walled-farm")
        self.assertEqual(engine.view(s, "blue")["standing_templates"][-1]["id"], "close_on_breach")


class GateObservationTests(unittest.TestCase):
    def test_gate_state_reaches_headquarters_only_by_report(self):
        s = advance(blue_orders(battle(), close()), 3)
        self.assertEqual(gate(s)["state"], "closed")
        self.assertEqual(engine.god_view(s)["map_features"][0]["openings"][0]["state"], "closed")
        self.assertEqual(known_state(s, "blue"), "closed")  # Seen by the command detachment.
        self.assertEqual(known_state(s, "grey"), "open")  # No grey observer within three hexes.
        # A grey party moving up sees the gate; its report must still travel.
        s = grey_orders(s, move("G2", GATE_OUTSIDE))
        sent = lambda s: [e for e in events(s, "report_sent") if e["side"] == "grey" and e["report_kind"] == "terrain"]
        s = advance_until(s, lambda s: sent(s))
        seen = s["turn"]
        self.assertTrue(sent(s))
        self.assertEqual(known_state(s, "grey"), "open")
        s = advance_until(s, lambda s: known_state(s, "grey") != "open")
        self.assertIn(known_state(s, "grey"), ("closed", "barred"))
        self.assertGreater(s["turn"], seen)


class GateEditionTests(unittest.TestCase):
    def test_gates_need_poc10_and_authored_labour(self):
        with self.assertRaisesRegex(ValueError, "need poc-10"):
            build_state(dataclasses.replace(gate_entry(), labels={"poc-9": "x", "poc-10": "y"}), "poc-9")
        with self.assertRaisesRegex(ValueError, "authored gate labour"):
            validate(dataclasses.replace(gate_entry(), gates=None))
        s = battle()
        self.assertEqual(s["gate_rules"]["basis"], "authored POC sensitivity parameter; not a historical estimate")
        templates = engine.view(s)["order_templates"]
        self.assertEqual((templates[-1]["id"], templates[-1]["version"]), ("close_gate", "common-orders-v4"))

    def test_gate_fixture_runs_headless_and_replays(self):
        catalog = ScenarioRegistry([LITTLE_ROUND_TOP, gate_entry(armed=("B1", "G1", "G2"))])
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "gate.sqlite"
            result = build_headless(db, scenario_id="test-gate", scenarios=catalog).run()
            self.assertEqual(result["replay"]["status"], "identical")
            self.assertEqual(build_replay(db).verify(result["game_id"]), result["replay"])
            self.assertEqual(build_replay(db).repository.load(result["game_id"])["rules"], "poc-10")


# Taken at cb7faa0, before poc-10: the scripted poc-9 Little Round Top run
# (test_scenario_sides.play), and a poc-9 save advanced 10 then 30 intervals
# through BattleService, as sha256 of the sort-keyed JSON state.
POC9_LRT_RUN_SHA256 = "0a062def4388366816ea5d205faff9a263e1fe2f4a7cd5f659a101c7b038d785"
POC9_SAVE_ADVANCED_SHA256 = "ee1358d0f48cc28bf21a8675d3b87676b7828ac19417c6b3de917fb4060c522a"


def as_poc9(state):
    """A poc-10 Little Round Top snapshot written in poc-9 terms."""
    text = json.dumps(state, sort_keys=True)
    return json.loads(text.replace('"poc-10"', '"poc-9"').replace("little-round-top-v10", "little-round-top-v9"))


def advance_through_service(state, steps):
    from battle import analysis
    from battle.adapters.openrouter import DisabledProvider
    from battle.adapters.rules import RulesSimulation
    from battle.presentation import present_view
    from battle.services.battle import BattleService
    from battle.services.commander import CommanderService
    from battle.services.queries import BattleQueries
    from battle.services.replay import ReplayService
    from test_services import ManualClock, MemoryRepository

    repository, sim = MemoryRepository(), RulesSimulation()
    repository.create(state)
    app = BattleService(
        repository, sim, CommanderService(sim, DisabledProvider()), ScenarioRegistry([LITTLE_ROUND_TOP]),
        BattleQueries(repository, sim, ReplayService(repository, sim), assess=analysis.assess, present=present_view),
        ManualClock, mode="scripted",
    )
    for _ in range(steps):
        app.clock_step()
    return repository.load(app.game_id)


class Poc10EditionTests(unittest.TestCase):
    def test_little_round_top_poc10_plays_identically_to_poc9(self):
        start = scenario.create()
        self.assertEqual((start["rules"], start["scenario"]), ("poc-10", "little-round-top-v10"))
        self.assertNotIn("gate_rules", start)
        self.assertEqual(as_poc9(start), scenario.create("poc-9"))
        self.assertEqual(digest(as_poc9(play(start))), POC9_LRT_RUN_SHA256)

    def test_poc9_save_advances_through_battle_service_as_before(self):
        # Preservation pin: passes at cb7faa0 by construction, and must keep passing.
        self.assertEqual(digest(play(scenario.create("poc-9"))), POC9_LRT_RUN_SHA256)
        save = advance_through_service(scenario.create("poc-9"), 10)
        final = advance_through_service(json.loads(json.dumps(save, sort_keys=True)), 30)
        self.assertEqual((final["rules"], final["turn"]), ("poc-9", 40))
        self.assertEqual(digest(final), POC9_SAVE_ADVANCED_SHA256)
