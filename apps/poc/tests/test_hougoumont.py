"""Hougoumont north gate (poc-10): the catalog entry, its hold-compound
victory kind, the Napoleonic voice and the service paths. Design:
docs/research/42-hougoumont-scenario.md.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from battle import engine, victory
from battle.adapters.openrouter import DisabledProvider
from battle.adapters.rules import RulesSimulation, ScenarioRegistry
from battle.bootstrap import build_headless, build_replay, build_scenarios
from battle.command_policy import system_prompt
from battle.scenario import LITTLE_ROUND_TOP
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate
from battle.scenario_hougoumont import (
    ALLIED_MISSION, COMPOUND, FRENCH_MISSION, HOUGOUMONT_NORTH_GATE as ENTRY,
)
from battle.services.commander import CommanderService
from scenario_fixtures import DUEL, gate_entry


def catalog():
    return ScenarioRegistry([LITTLE_ROUND_TOP, ENTRY])


class HougoumontEntryTests(unittest.TestCase):
    def test_entry_registers_in_the_player_catalog_after_a_dry_run(self):
        self.assertEqual(build_scenarios().resolve("hougoumont-north-gate"), ENTRY)
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        self.assertEqual((s["rules"], s["scenario"]), ("poc-12", "hougoumont-north-gate-v3"))
        self.assertEqual(s["sides"], [{"id": "allied", "name": "Allied", "role": "defender"},
                                      {"id": "french", "name": "French", "role": "attacker"}])
        self.assertEqual(s["player_side"], "allied")
        self.assertEqual(ENTRY.start_local, "1815-06-18T11:20:00")
        self.assertIn("Hougoumont", ENTRY.location)
        self.assertIn("Waterloo", ENTRY.location)
        self.assertIn("reconstruction", ENTRY.time_basis)

    def test_map_is_authored_with_a_walled_compound_and_open_north_gate(self):
        s = build_state(ENTRY)
        self.assertTrue(ENTRY.map.source.startswith("Authored, not surveyed"))
        farm = next(f for f in s["map_features"] if f["id"] == "hougoumont")
        self.assertEqual(farm["compound"], COMPOUND)
        self.assertEqual([(o["id"], o["state"]) for o in farm["openings"]], [("north-gate", "open")])
        areas = {c["area"] for c in s["cells"].values()}
        self.assertTrue({"farm-courtyard", "walled-garden", "orchard", "great-wood"} <= areas)
        self.assertEqual({r["id"] for r in s["map_features"] if r["kind"] == "road"},
                         {"north-lane", "west-lane", "wood-ride"})
        self.assertEqual(s["gate_rules"]["basis"], "authored POC sensitivity parameter; not a historical estimate")

    def test_every_field_basis_is_labelled_and_missions_are_reconstructions(self):
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        for field in ("allied.mission", "french.mission", "start_time"):
            self.assertTrue(ENTRY.provenance[field].startswith("reconstruction:"), field)
        for field in ("map", "units.skill", "gates", "victory"):
            self.assertTrue(ENTRY.provenance[field].startswith("authored:"), field)
        with self.assertRaisesRegex(ValueError, "provenance of map must start with"):
            validate(dataclasses.replace(ENTRY, provenance={"map": "illustrative"}))

    def test_each_side_prompt_carries_only_its_own_mission_in_an_1815_voice(self):
        allied, french = system_prompt("allied", ENTRY), system_prompt("french", ENTRY)
        self.assertIn(ALLIED_MISSION, allied)
        self.assertNotIn(FRENCH_MISSION, allied)
        self.assertIn(FRENCH_MISSION, french)
        self.assertNotIn(ALLIED_MISSION, french)
        for prompt in (allied, french):
            self.assertIn("Napoleonic Wars in 1815", prompt)
            self.assertNotIn("1863", prompt)

    def test_command_profile_label_is_1815_and_unknown_profiles_are_refused(self):
        s = build_state(ENTRY)
        self.assertEqual(engine.view(s, "allied")["command"]["profile"]["label"], "1815 · voice / foot runner")
        with self.assertRaisesRegex(ValueError, "voice profile must be one of"):
            validate(dataclasses.replace(ENTRY, voice_profile="unknown-voice-v1"))
        with self.assertRaisesRegex(ValueError, "communications must be one of"):
            validate(dataclasses.replace(ENTRY, communications="unknown-courier-v1"))


class HoldCompoundTests(unittest.TestCase):
    def test_hold_compound_refuses_entries_without_a_walled_objective(self):
        no_walls = dataclasses.replace(DUEL.victory, kind="hold-compound")
        with self.assertRaisesRegex(ValueError, "objective must lie in a building compound with openings"):
            validate(dataclasses.replace(DUEL, victory=no_walls))
        bad = dataclasses.replace(ENTRY.victory, hold_turns=0, objective_name="")
        with self.assertRaisesRegex(ValueError, "hold_turns must be a positive integer.*objective_name"):
            validate(dataclasses.replace(ENTRY, victory=bad))
        outside = dataclasses.replace(ENTRY.victory, objective=(11, 8))
        with self.assertRaisesRegex(ValueError, "building compound with openings"):
            validate(dataclasses.replace(ENTRY, victory=outside))

    def test_hold_compound_fails_closed_on_missing_snapshot_data(self):
        for field, value in (("compound", None), ("compound", []), ("hold_turns", 0),
                             ("hold_turns", "6"), ("feature_id", None), ("compound", [[99, 99]])):
            with self.subTest(field=field, value=value):
                s = build_state(ENTRY)
                s["victory"][field] = value
                with self.assertRaisesRegex(ValueError, "hold-compound victory data"):
                    victory.score(s)
        s = build_state(ENTRY)
        del s["victory"]["compound"]
        with self.assertRaisesRegex(ValueError, "hold-compound victory data"):
            victory.score(s)

    def test_hold_compound_attacker_wins_by_uncontested_possession(self):
        s = build_state(ENTRY)
        s["turn"] = 1
        french = [u for u in s["units"] if u["side"] == "french"]
        french[0]["pos"] = [11, 9]
        # Contested: Allied formations are still effective inside.
        self.assertEqual(victory.score(s), (None, None))
        self.assertEqual(s["capture"], 0)
        for u in s["units"]:
            if u["side"] == "allied":
                u["pos"] = [11, 2 + int(u["id"][1])]
        for turn in range(1, 7):
            s["turn"] = turn
            result = victory.score(s)
        self.assertEqual(result, ("french", "The attackers held the inside of the farm for 180 seconds "
                                            "with no effective defender within the walls."))

    def test_hold_compound_defender_wins_at_the_deadline(self):
        s = build_state(ENTRY)
        s["turn"] = s["max_turns"]
        self.assertEqual(victory.score(s), ("allied", "The Allied garrison held the farm until the scenario deadline."))

    def test_gate_fixture_can_use_hold_compound(self):
        entry = gate_entry()
        entry = dataclasses.replace(entry, victory=dataclasses.replace(entry.victory, kind="hold-compound"))
        self.assertEqual(build_state(dry_run(validate(entry)))["victory"]["feature_id"], "walled-farm")


class HougoumontServiceTests(unittest.TestCase):
    def test_scripted_headless_run_completes_and_replays_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "hougoumont.sqlite"
            result = build_headless(db, scenario_id=ENTRY.id, scenarios=catalog()).run()
            self.assertEqual(result["replay"]["status"], "identical")
            self.assertIn(result["winner"], ("allied", "french", "draw"))
            self.assertEqual(build_replay(db).verify(result["game_id"]), result["replay"])
            final = build_replay(db).repository.load(result["game_id"])
            self.assertEqual((final["rules"], final["status"]), ("poc-12", "complete"))
            self.assertEqual({d["side"] for d in final["decisions"]}, {"french"})

    def test_clock_step_with_the_allied_player_commands_the_french(self):
        from battle import analysis
        from battle.presentation import present_view
        from battle.services.battle import BattleService
        from battle.services.queries import BattleQueries
        from battle.services.replay import ReplayService
        from test_services import ManualClock, MemoryRepository

        scenarios, repository, sim = catalog(), MemoryRepository(), RulesSimulation()
        app = BattleService(
            repository, sim, CommanderService(sim, DisabledProvider(), scenarios=scenarios), scenarios,
            BattleQueries(repository, sim, ReplayService(repository, sim), assess=analysis.assess, present=present_view),
            ManualClock, scenario_id=ENTRY.id,
        )
        try:
            self.assertTrue(app.clock_step())
            state = repository.load(app.game_id)
            self.assertEqual(state["player_side"], "allied")
            self.assertEqual(sim.computer_side(state), "french")
            self.assertEqual([(d["side"], d["voice_profile"]) for d in state["decisions"]],
                             [("french", "napoleonic-en-v1")])
            self.assertEqual({o["side"] for o in state["orders"]}, {"french"})
            self.assertEqual(app.queries.replay_service.verify(app.game_id)["status"], "identical")
        finally:
            app.close()


class EngineRun:
    """A stored game driven by recorded actions through ``RulesSimulation``,
    so every test below can check its replay."""

    def __init__(self, state):
        from battle.services.replay import ReplayService
        from test_services import MemoryRepository

        self.repository, self.sim = MemoryRepository(), RulesSimulation()
        self.state = state
        self.game_id = self.repository.create(state)
        self.replay = ReplayService(self.repository, self.sim)

    def step(self, action):
        updated = self.sim.apply(self.state, action)
        self.repository.save(self.game_id, updated, self.state["revision"])
        self.state = updated
        return updated

    def advance(self):
        return self.step({"type": "advance"})

    def unit(self, uid):
        return next(u for u in self.state["units"] if u["id"] == uid)

    def gate(self):
        farm = next(f for f in self.state["map_features"] if f["id"] == "hougoumont")
        return farm["openings"][0]


def arranged(**placement):
    """A Hougoumont start with units placed (and otherwise changed) by id."""
    s = build_state(ENTRY)
    for u in s["units"]:
        u.update(placement.get(u["id"], {}))
    return s


class GateDefenderPolicyTests(unittest.TestCase):
    def test_gate_defender_keeps_the_gate_party_and_orders_close_on_breach(self):
        from battle.command_policy import gate_defender_actions

        view = engine.view(build_state(ENTRY), "allied")
        standing, orders = gate_defender_actions(view)
        self.assertEqual(standing, [{"unit_id": "A1", "profile_id": "close_on_breach"}])
        # The gate party already holds the gateway; nobody is sent onto it.
        self.assertNotIn("A1", [o["unit_id"] for o in orders])
        self.assertNotIn([11, 9], [o["destination"] for o in orders])
        view["contacts"] = [{"id": "F1", "pos": [11, 9], "side": "french"}]
        view["standing_orders"] = [{"unit_id": "A1", "profile_id": "close_on_breach"}]
        standing, orders = gate_defender_actions(view)
        self.assertEqual(standing, [])
        self.assertEqual(orders[0], {"unit_id": "A1", "stance": "close_gate", "destination": None})
        # Little Round Top has no gate: the policy is the fallback ring.
        from battle.command_policy import fallback_orders
        lrt = engine.view(build_state(LITTLE_ROUND_TOP), "union")
        self.assertEqual(gate_defender_actions(lrt), ([], fallback_orders(lrt, "defender")))

    def test_hougoumont_gate_defender_run_records_policy_and_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "hougoumont.sqlite"
            result = build_headless(db, scenario_id=ENTRY.id, scenarios=catalog()).run()
            self.assertEqual(result["replay"]["status"], "identical")
            self.assertEqual(result["run"]["player_policy"], "scripted-gate-defender-v1")
            self.assertEqual(result["run"]["opponent"], "scripted-gate-attacker-v1")
            final = build_replay(db).repository.load(result["game_id"])
            self.assertEqual(final["run"], result["run"])
            # The French gate attacker issues its own standing orders; A1 is the first gate party.
            allied = [(o["unit_id"], o["profile_id"], o["status"]) for o in final["standing_orders"]
                      if o["unit_id"].startswith("A")]
            self.assertEqual(allied[0], ("A1", "close_on_breach", "delivered"))
            self.assertNotIn("A1", [o["unit_id"] for o in final["orders"] if o["side"] == "allied"])
            with self.assertRaisesRegex(ValueError, "defending side of a gated scenario"):
                build_headless(Path(tmp) / "lrt.sqlite", player_policy="scripted-gate-defender-v1")

    def test_model_french_run_gives_the_computer_allies_the_gate_defender(self):
        from battle.command_policy import fallback_orders
        from test_headless_player import FakeProvider

        provider = FakeProvider(lambda p: fallback_orders(p["observation"], "attacker"))
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "french.sqlite"
            runner = build_headless(db, scenario_id=ENTRY.id, scenarios=catalog(),
                                    player_side="french", player_provider="openrouter",
                                    provider=provider)
            result = runner.run()
            self.assertTrue(provider.calls)
            self.assertEqual(result["run"]["opponent"], "scripted-gate-defender-v1")
            final = build_replay(db).repository.load(result["game_id"])
            allied = [d for d in final["decisions"] if d["side"] == "allied"]
            self.assertTrue(allied)
            self.assertEqual({(d["source"], d["policy"]) for d in allied},
                             {("scripted", "scripted-gate-defender-v1")})
            self.assertEqual((allied[0]["turn"], allied[0]["standing"]),
                             (0, [{"unit_id": "A1", "profile_id": "close_on_breach"}]))
            # Issued once, through courier or voice delivery like a player's.
            self.assertEqual([(o["unit_id"], o["profile_id"], o["sent_turn"], o["status"])
                              for o in final["standing_orders"]],
                             [("A1", "close_on_breach", 0, "delivered")])
            self.assertEqual(result["replay"]["status"], "identical")
            # A fresh replay service has no provider and re-runs no policy.
            self.assertEqual(build_replay(db).verify(result["game_id"])["status"], "identical")

    def test_computer_gate_defender_orders_close_gate_on_a_delivered_breach(self):
        run = EngineRun(arranged(F1={"pos": [10, 10]}))  # Inside the compound.
        run.advance()
        self.assertIn([10, 10], [c["pos"] for c in engine.view(run.state, "allied")["contacts"]])
        commander = CommanderService(run.sim, DisabledProvider(), scenarios=catalog())
        decision = commander.decide(run.state, "allied", mode="scripted",
                                    policy="scripted-gate-defender-v1")
        self.assertEqual(decision["orders"][0],
                         {"unit_id": "A1", "stance": "close_gate", "destination": None})
        run.step({"type": "advance", "decision": decision})
        recorded = run.state["decisions"][-1]
        self.assertEqual((recorded["policy"], recorded["standing"]),
                         ("scripted-gate-defender-v1",
                          [{"unit_id": "A1", "profile_id": "close_on_breach"}]))
        self.assertIn(("A1", "close_gate", "delivered"),
                      [(o["unit_id"], o["stance"], o["status"]) for o in run.state["orders"]
                       if o["side"] == "allied"])
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")


ATTACKER = "scripted-gate-attacker-v1"
OUTSIDE, GATEWAY = [11, 8], [11, 9]


def attack(run, commander, turns):
    """Advance ``run`` ``turns`` intervals with the French computer side
    deciding under the gate attacker every third turn, as the runner does."""
    for _ in range(turns):
        decision = None
        if run.state["turn"] % 3 == 0:
            decision = commander.decide(run.state, "french", mode="scripted", policy=ATTACKER)
        run.step({"type": "advance", "decision": decision})


class GateAttackerPolicyTests(unittest.TestCase):
    def test_gate_attacker_reaches_the_outside_hex_and_pushes_through_delivery(self):
        # No garrison in sight: F1, ordered into the farm, marches through the outside hex.
        far = {"A1": {"pos": [20, 18]}, "A2": {"pos": [21, 18]}, "A3": {"pos": [22, 18]}}
        run = EngineRun(arranged(F1={"pos": [11, 5]}, **far))
        commander = CommanderService(run.sim, DisabledProvider(), scenarios=catalog())
        attack(run, commander, 1)
        self.assertEqual(run.state["decisions"][0]["orders"][0],
                         {"unit_id": "F1", "stance": "move", "destination": GATEWAY})
        while run.unit("F1")["pos"] != OUTSIDE and run.state["turn"] < 12:
            attack(run, commander, 1)
        self.assertEqual(run.unit("F1")["pos"], OUTSIDE)
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")
        # A1 holds the gateway. F1, already on the outside hex, pushes only once the
        # policy's order to enter has been delivered by normal transport.
        run = EngineRun(arranged(A1={"ammo": 0, "strength": 80, "initial": 80}, A2={"ammo": 0}, A3={"pos": [20, 2]},
                                 F1={"pos": OUTSIDE, "strength": 60, "initial": 60}))
        commander = CommanderService(run.sim, DisabledProvider(), scenarios=catalog())
        while run.state["turn"] < 15 and not any(e["kind"] == "gateway_carried" for e in run.state["events"]):
            attack(run, commander, 1)
        delivered = next(e["turn"] for e in run.state["events"]
                         if e["kind"] == "order_delivered" and e.get("unit_id") == "F1")
        pushes = [e for e in run.state["events"] if e["kind"] == "gateway_push"]
        self.assertTrue(pushes)
        self.assertEqual({tuple(e["pushers"]) for e in pushes}, {("F1",)})
        self.assertGreater(delivered, 0)
        self.assertGreaterEqual(min(e["turn"] for e in pushes), delivered)
        carried = next(e for e in run.state["events"] if e["kind"] == "gateway_carried")
        self.assertEqual((carried["unit_id"], carried["holder_id"]), ("F1", "A1"))
        self.assertIn(list(run.unit("F1")["pos"]), COMPOUND)
        self.assertEqual({d["policy"] for d in run.state["decisions"]}, {ATTACKER})
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")

    def test_gate_attacker_reads_only_the_hq_view(self):
        from battle.command_policy import gate_attacker_actions

        s = build_state(ENTRY)
        view = engine.view(s, "french")
        standing, orders = gate_attacker_actions(view)
        self.assertEqual(standing, [{"unit_id": "F1", "profile_id": "firm"},
                                    {"unit_id": "F3", "profile_id": "firm"}])
        # F1 makes for the gateway; F3 waits by the walls; F2 takes a fire position.
        self.assertEqual(orders, [{"unit_id": "F1", "stance": "move", "destination": GATEWAY},
                                  {"unit_id": "F3", "stance": "move", "destination": [10, 12]},
                                  {"unit_id": "F2", "stance": "move", "destination": [9, 10]}])
        # A1 truly leaves the gateway for F2's fire position; nobody has reported it.
        engine.find_unit(s, "A1")["pos"] = [9, 10]
        self.assertEqual(gate_attacker_actions(engine.view(s, "french")), (standing, orders))
        # A delivered contact on that hex does move F2 to another free hex by the walls.
        view["contacts"] = [{"id": "A1", "pos": [9, 10], "side": "allied"}]
        self.assertNotIn([9, 10], [o["destination"] for o in gate_attacker_actions(view)[1]])
        # Once inside the walls the assault holds.
        view["contacts"] = []
        view["units"][0].update(pos=[11, 10], stance="move")
        self.assertIn({"unit_id": "F1", "stance": "hold", "destination": None}, gate_attacker_actions(view)[1])

    def test_gate_attacker_selection_and_refusal(self):
        import subprocess
        import sys
        from battle.command_policy import scripted_policy

        self.assertEqual((scripted_policy(ENTRY, "french"), scripted_policy(ENTRY, "allied")),
                         (ATTACKER, "scripted-gate-defender-v1"))
        self.assertEqual({scripted_policy(LITTLE_ROUND_TOP, side) for side in LITTLE_ROUND_TOP.sides},
                         {"scripted-fallback-v1"})
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "h.sqlite"
            computer = build_headless(db, scenario_id=ENTRY.id, scenarios=catalog())
            self.assertEqual(computer.metadata(build_state(ENTRY))["opponent"], ATTACKER)
            player = build_headless(db, scenario_id=ENTRY.id, scenarios=catalog(), player_side="french")
            meta = player.metadata(build_state(ENTRY))
            self.assertEqual((meta["player_policy"], meta["opponent"]), (ATTACKER, "scripted-gate-defender-v1"))
            refused = (
                dict(player_policy=ATTACKER),  # Little Round Top has no gate.
                dict(opponent=ATTACKER),
                dict(scenario_id=ENTRY.id, scenarios=catalog(), player_policy=ATTACKER),  # Allied player.
                dict(scenario_id=ENTRY.id, scenarios=catalog(), player_side="french", opponent=ATTACKER),
            )
            for kwargs in refused:
                with self.subTest(**{k: v for k, v in kwargs.items() if k != "scenarios"}):
                    with self.assertRaisesRegex(ValueError, "attacking side of a gated scenario"):
                        build_headless(db, **kwargs)
            cli = subprocess.run(
                [sys.executable, "-m", "battle", "--headless", "--db", str(db),
                 "--player-policy", ATTACKER], capture_output=True, text=True,
                cwd=Path(__file__).resolve().parent.parent)
        self.assertEqual(cli.returncode, 2)
        self.assertIn(f"{ATTACKER} needs the attacking side of a gated scenario", cli.stderr)
        # Only the gate controls add fields: a fallback decision keeps its shape.
        run = EngineRun(build_state(ENTRY))
        commander = CommanderService(run.sim, DisabledProvider(), scenarios=catalog())
        plain = commander.decide(run.state, "french", mode="scripted")
        gated = commander.decide(run.state, "french", mode="scripted", policy=ATTACKER)
        self.assertEqual(set(gated) - set(plain), {"policy", "standing"})
        self.assertNotIn("policy", plain)


class HoldCompoundEngineTests(unittest.TestCase):
    def test_gate_closes_with_french_inside_and_cuts_them_off(self):
        # The garrison inside has no cartridges, so the French get in; the
        # gate party works the gate under its delivered standing order.
        run = EngineRun(arranged(
            A1={"pos": [12, 10], "strength": 60, "initial": 60, "ammo": 0},
            A2={"ammo": 0}, A3={"pos": [11, 3]},
            F1={"pos": [11, 8], "stance": "move", "target": [11, 10]},
            F2={"pos": [11, 7], "stance": "move", "target": [10, 10]},
        ))
        run.step({"type": "standing", "instruction": {"unit_id": "A1", "profile_id": "close_on_breach"}})
        entered = None
        while run.gate()["state"] not in ("closed", "barred") and run.state["turn"] < 12:
            run.advance()
            if entered is None and list(run.unit("F1")["pos"]) in COMPOUND:
                entered = run.state["turn"]
        self.assertIsNotNone(entered)
        self.assertEqual(run.gate()["state"], "closed")
        kinds = [e["kind"] for e in run.state["events"]]
        self.assertIn("standing_gate_close", kinds)
        self.assertIn("gate_blocked", kinds)  # F1 stood in the gateway first.
        cut = next(e for e in run.state["events"] if e["kind"] == "units_cut_off")
        self.assertEqual(cut["unit_ids"], ["F1"])
        self.assertEqual(run.unit("F1")["cut_off"]["turn"], run.state["turn"])
        self.assertIn(list(run.unit("F1")["pos"]), COMPOUND)
        # The gate party is still effective inside: possession is contested.
        self.assertEqual(run.unit("A1")["status"], "ready")
        self.assertEqual(run.state["capture"], 0)
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")

    def test_capture_counter_resets_after_a_partial_hold(self):
        run = EngineRun(arranged(A1={"pos": [12, 5]}, A2={"pos": [11, 6]}, A3={"pos": [12, 6]},
                                 F1={"pos": [11, 10], "ammo": 0}))
        counts = [run.advance()["capture"] for _ in range(2)]
        # A2 commands; its own order goes by voice and it marches back in.
        run.step({"type": "orders", "orders": [{"unit_id": "A2", "stance": "move", "destination": [10, 9]}]})
        while run.state["capture"] and run.state["status"] == "active":
            counts.append(run.advance()["capture"])
        self.assertEqual(run.state["status"], "active")
        self.assertEqual(counts, [1, 2, 3, 4, 5, 0])
        self.assertIn(list(run.unit("A2")["pos"]), COMPOUND)
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")

    def test_mutual_loss_is_a_draw(self):
        broken = {"status": "lost", "strength": 0}
        run = EngineRun(arranged(**{uid: broken for uid in ("A1", "A2", "A3", "F1", "F2", "F3")}))
        run.advance()
        self.assertEqual((run.state["status"], run.state["winner"], run.state["reason"]),
                         ("complete", "draw", "Both commands lost combat effectiveness."))
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")

    def test_defender_without_an_effective_formation_loses(self):
        run = EngineRun(arranged(A1={"status": "lost", "strength": 0}, A2={"status": "routed"},
                                 A3={"status": "merged"}))
        run.advance()
        self.assertEqual((run.state["status"], run.state["winner"], run.state["reason"]),
                         ("complete", "french", "Allied formations can no longer hold the farm."))
        self.assertEqual(run.replay.verify(run.game_id)["status"], "identical")


if __name__ == "__main__":
    unittest.main()
