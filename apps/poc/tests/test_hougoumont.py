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
        self.assertEqual((s["rules"], s["scenario"]), ("poc-10", "hougoumont-north-gate-v1"))
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
            self.assertEqual((final["rules"], final["status"]), ("poc-10", "complete"))
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


if __name__ == "__main__":
    unittest.main()
