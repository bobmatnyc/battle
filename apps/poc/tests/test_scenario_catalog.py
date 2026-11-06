"""Scenario catalog: entries as data, Little Round Top unchanged, a second scenario.

Digests below were taken from commit 503d541, before scenarios became entries.
"""

import copy
import dataclasses
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from battle import analysis, command_policy, scenario
from battle.adapters.rules import LittleRoundTopCatalog, RulesSimulation, ScenarioRegistry
from battle.bootstrap import build_application, build_headless, build_replay
from battle.config import Settings
from battle.contracts import UnknownScenario
from battle.presentation import present_view
from battle.scenario import LITTLE_ROUND_TOP
from battle.scenario_entry import build_state
from battle.services.battle import BattleService
from battle.services.commander import CommanderService
from battle.services.queries import BattleQueries
from battle.services.replay import ReplayService
from scenario_fixtures import DUEL
from test_services import ManualClock, MemoryRepository

POC = Path(__file__).resolve().parent.parent

LRT_STATE_SHA256 = {
    "poc-1": "ed33cbb8dceaf4fcd413c0568939a5e0bd21f23671af29ed1cb11bc391459163",
    "poc-2": "835b935dcbdf54e4d2fc37e4ad4b4dd0ada80aeb863375b5ce05a130161badbc",
    "poc-3": "05493fe56f56eeada9c603913cc00c4fdeb526600551f3cb8aef222e6982568b",
    "poc-4": "51996e8236107a7eb955afead33215bb7f84d748fe8cabcfa8949205fdeb25ac",
    "poc-5": "aa9077098582ab34787a0bb7be74f4580e024e158e8525512c199cfd1c40d83d",
    "poc-6": "a79dba3003982db67822615c1415da719dcde8c1a0753ce7cab76e5c22439e6c",
    "poc-7": "36baf293938e4f4306a7b0555297aabff7959c82e1a4109fe49cb6a39aa9d962",
    "poc-8": "351ddb3394dda90498066d4e6efa5f120be5774b9afe6480dc98e209e1f90311",
}
LRT_PROMPT_SHA256 = {
    "union": "5610516d16b9d275756c57c0bd0f9b1b52ca8e4dffa11bb480b76d770dd0c123",
    "confederate": "6e359c8a3508fe20d19d4baeceb9293b3362c1c578d3f597086c017fccc5d0b9",
}
LRT_MAP_SHA256 = "bd39cef2937dd5e6a0d478306dd99aaecf470bb54e46b750cec5006b7dcf32fa"


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def registry():
    return ScenarioRegistry([LITTLE_ROUND_TOP, DUEL])


class RecordingProvider:
    available = True
    model = "fake/catalog"

    def __init__(self):
        self.calls = []

    def request(self, instruction, payload):
        self.calls.append(instruction)
        return {"text": "Orders.", "orders": []}, {"model": self.model}


class LittleRoundTopEntryTests(unittest.TestCase):
    def test_little_round_top_entry_rebuilds_every_edition_byte_identically(self):
        for edition, digest in LRT_STATE_SHA256.items():
            with self.subTest(edition=edition):
                self.assertEqual(sha256(json.dumps(scenario.create(edition))), digest)
        catalog = LittleRoundTopCatalog()
        self.assertEqual(json.dumps(catalog.create()), json.dumps(scenario.create()))
        self.assertEqual(sha256(json.dumps(catalog.map())), LRT_MAP_SHA256)

    def test_little_round_top_prompt_is_byte_identical_to_lrt_side_v2(self):
        self.assertEqual(LITTLE_ROUND_TOP.prompt_version, "lrt-side-v2")
        for side, digest in LRT_PROMPT_SHA256.items():
            with self.subTest(side=side):
                self.assertEqual(sha256(command_policy.system_prompt(side)), digest)
                self.assertEqual(
                    command_policy.system_prompt(side, LITTLE_ROUND_TOP),
                    command_policy.system_prompt(side),
                )


class CatalogTests(unittest.TestCase):
    def test_catalog_resolves_ids_and_refuses_unknown_scenarios(self):
        catalog = registry()
        self.assertEqual(catalog.ids(), ("little-round-top", "test-duel"))
        self.assertIs(catalog.resolve(), LITTLE_ROUND_TOP)
        self.assertIs(catalog.resolve("test-duel"), DUEL)
        self.assertEqual(catalog.create("test-duel")["scenario"], "test-duel-v1")
        for bad in ("hougoumont", "", 7):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(UnknownScenario, "Known scenarios: little-round-top, test-duel"):
                    catalog.resolve(bad)
        with self.assertRaises(ValueError):
            ScenarioRegistry([LITTLE_ROUND_TOP, LITTLE_ROUND_TOP])
        with self.assertRaises(ValueError):
            build_state(DUEL, "poc-7")

    def test_catalog_resolves_saved_games_by_label(self):
        catalog = registry()
        for edition in LRT_STATE_SHA256:
            self.assertIs(catalog.for_state(scenario.create(edition)), LITTLE_ROUND_TOP)
        self.assertIs(catalog.for_state(catalog.create("test-duel")), DUEL)
        with self.assertRaises(UnknownScenario):
            LittleRoundTopCatalog().for_state(catalog.create("test-duel"))

    def test_catalog_refuses_entry_the_rules_cannot_run(self):
        victory = dataclasses.replace(DUEL.victory, hold_turns=5)
        geometry = dataclasses.replace(DUEL.map, cols=12)
        swapped = {
            "union": dataclasses.replace(DUEL.sides["union"], role="attacker"),
            "confederate": DUEL.sides["confederate"],
        }
        command = {
            "union": dataclasses.replace(DUEL.sides["union"], command_unit="G1"),
            "confederate": DUEL.sides["confederate"],
        }
        cases = {
            "rules": dict(rules="poc-9"),
            "victory": dict(victory=victory),
            "map must be": dict(map=geometry),
            "seconds": dict(seconds_per_turn=60),
            "order catalog": dict(order_catalog=("hold", "move")),
            "must be the defender": dict(sides=swapped),
            "command unit": dict(sides=command),
            "unique": dict(units=DUEL.units + (DUEL.units[0],)),
            "voice": dict(voice_profile="napoleonic-en-v1"),
        }
        for problem, change in cases.items():
            with self.subTest(problem=problem):
                with self.assertRaisesRegex(ValueError, problem):
                    ScenarioRegistry([dataclasses.replace(DUEL, **change)])


class SecondScenarioTests(unittest.TestCase):
    def test_duel_fixture_runs_headless_and_replays(self):
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("first", "second"):
                db = Path(tmp) / f"{name}.sqlite"
                runner = build_headless(
                    db, player_side="confederate", scenario_id="test-duel", scenarios=registry()
                )
                result = runner.run()
                state = runner.repository.load(result["game_id"])
                self.assertEqual(state["scenario"], "test-duel-v1")
                self.assertEqual({u["id"] for u in state["units"]}, {"B1", "G1"})
                self.assertEqual(state["run"]["scenario_id"], "test-duel")
                self.assertEqual(state["run"]["variant"], "flat")
                self.assertEqual(state["run"]["prompt_version"], "test-duel-v1")
                self.assertEqual(result["replay"]["status"], "identical")
                # Replay from storage alone, with no catalog or provider.
                self.assertEqual(build_replay(db).verify(result["game_id"]), result["replay"])
                results.append({k: v for k, v in result.items() if k != "game_id"})
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["turns"], 12)

    def test_duel_prompt_shows_only_its_own_side_mission(self):
        catalog = registry()
        state = catalog.create("test-duel")
        missions = {side: spec.mission for side, spec in DUEL.sides.items()}
        for side, other in (("union", "confederate"), ("confederate", "union")):
            with self.subTest(side=side):
                provider = RecordingProvider()
                commander = CommanderService(RulesSimulation(), provider, scenarios=catalog)
                decision = commander.decide(state, side=side)
                instruction = provider.calls[0]
                self.assertIn(missions[side], instruction)
                self.assertNotIn(missions[other], instruction)
                self.assertIn("Test Duel, 1863", instruction)
                for lrt_mission in command_policy.MISSIONS.values():
                    self.assertNotIn(lrt_mission, instruction)
                self.assertEqual(decision["prompt_version"], "test-duel-v1")

    def test_commander_without_catalog_refuses_other_scenarios(self):
        state = registry().create("test-duel")
        commander = CommanderService(RulesSimulation(), RecordingProvider())
        with self.assertRaisesRegex(ValueError, "test-duel-v1"):
            commander.decide(state, side="union")
        # Little Round Top still needs no catalog, as before.
        decision = commander.decide(scenario.create(), side="union")
        self.assertEqual(decision["prompt_version"], "lrt-side-v2")


class SelectionTests(unittest.TestCase):
    def test_new_game_creation_selects_and_refuses_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(UnknownScenario):
                build_application(Path(tmp) / "x.sqlite", offline=True, settings=Settings(), scenario_id="nope")
            self.assertFalse((Path(tmp) / "x.sqlite").exists())
        repository = MemoryRepository()
        simulation = RulesSimulation()
        catalog = registry()
        app = BattleService(
            repository,
            simulation,
            CommanderService(simulation, RecordingProvider(), scenarios=catalog),
            catalog,
            BattleQueries(
                repository,
                simulation,
                ReplayService(repository, simulation),
                assess=analysis.assess,
                present=present_view,
            ),
            ManualClock,
            scenario_id="test-duel",
        )
        self.assertEqual(repository.load(app.game_id)["scenario"], "test-duel-v1")
        self.assertEqual(app.map()["setting"]["location"], "Synthetic test ground")
        before = app.game_id
        revision = repository.load(before)["revision"]
        with self.assertRaises(UnknownScenario):
            app.execute("new", {"scenario": "nope"}, game_id=before, revision=revision)
        self.assertEqual(app.game_id, before)
        app.execute("new", {"scenario": "little-round-top"}, game_id=before, revision=revision)
        self.assertEqual(repository.load(app.game_id)["scenario"], "little-round-top-v8")
        self.assertEqual(app.map()["setting"]["start_local"], "1863-07-02T16:30:00")
        app.close()

    def test_build_headless_refuses_unknown_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "battle.sqlite"
            with self.assertRaisesRegex(UnknownScenario, "'test-duel'"):
                build_headless(db, scenario_id="test-duel")
            self.assertFalse(db.exists())
            cli = subprocess.run(
                [sys.executable, "-m", "battle", "--headless", "--db", str(db), "--scenario", "nope"],
                cwd=POC,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(cli.returncode, 2)
            self.assertIn("Unknown scenario 'nope'. Known scenarios: little-round-top.", cli.stderr)
            self.assertFalse(db.exists())

    def test_entry_build_does_not_mutate_entry_data(self):
        before = copy.deepcopy(LITTLE_ROUND_TOP.map.features)
        build_state(LITTLE_ROUND_TOP)
        self.assertEqual(LITTLE_ROUND_TOP.map.features, before)


if __name__ == "__main__":
    unittest.main()
