"""poc-9: scenario-defined sides and victory kinds; poc-8 frozen for replay.

The poc-8 digest below is the final state of the scripted Little Round Top
run at commit ed33325 (before poc-9), without the headless ``run`` metadata.
"""

import dataclasses
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from battle import engine, scenario, victory
from battle.adapters.openrouter import DisabledProvider
from battle.adapters.rules import RulesSimulation, ScenarioRegistry
from battle.bootstrap import build_headless, build_replay
from battle.command_policy import fallback_orders
from battle.scenario import LITTLE_ROUND_TOP
from battle.services.commander import CommanderService
from scenario_fixtures import BLUE_GREY_DUEL, DUEL

POC8_LRT_RUN_SHA256 = "1a5977b73636a83efcf22cd57aeca9215f803a6ccc267f3d523ad26a89134c4f"
POC9_LRT_STATE_SHA256 = "26cf11e317b914fd0efd7cef65162a1df6e9ac439512814057b82c0377db06a1"
POC9_KEYS = ("sides", "player_side", "victory")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def play(state):
    """The scripted headless loop: the player side issues direct orders, the
    other side records scripted decisions every third interval."""
    sim = RulesSimulation()
    commander = CommanderService(sim, DisabledProvider())
    player = sim.player_side(state)
    opponent = next(side for side in engine.sides(state) if side != player)
    while state["status"] == "active":
        decision = None
        if state["turn"] % 3 == 0:
            orders = fallback_orders(sim.view(state, player), sim.role(state, player))
            if orders:
                state = sim.apply(state, {"type": "orders", "orders": orders})
            decision = commander.decide(state, side=opponent, mode="scripted")
        state = sim.apply(state, {"type": "advance", "decision": decision})
    return state


def as_poc8(state):
    """A poc-9 Little Round Top snapshot written in poc-8 terms."""
    state = {k: v for k, v in state.items() if k not in POC9_KEYS}
    text = json.dumps(state, sort_keys=True)
    return json.loads(text.replace('"poc-9"', '"poc-8"').replace("little-round-top-v9", "little-round-top-v8"))


def registry():
    return ScenarioRegistry([LITTLE_ROUND_TOP, DUEL, BLUE_GREY_DUEL])


class RulesEditionTests(unittest.TestCase):
    def test_poc8_little_round_top_replays_through_frozen_engine(self):
        final = play(scenario.create("poc-8"))
        self.assertEqual((final["rules"], final["turn"], final["winner"]), ("poc-8", 60, "union"))
        self.assertEqual(digest(final), POC8_LRT_RUN_SHA256)

    def test_little_round_top_poc9_plays_identically_to_poc8(self):
        start = scenario.create("poc-9")
        self.assertEqual(start["rules"], "poc-9")
        self.assertEqual(start["scenario"], "little-round-top-v9")
        self.assertEqual(
            {k: start[k] for k in POC9_KEYS},
            {
                "sides": [
                    {"id": "union", "name": "Union", "role": "defender"},
                    {"id": "confederate", "name": "Confederate", "role": "attacker"},
                ],
                "player_side": "union",
                "victory": {"kind": "hold-objective", "radius": 1, "hold_turns": 3,
                            "objective_name": "summit"},
            },
        )
        self.assertEqual(as_poc8(start), scenario.create("poc-8"))
        final = play(start)
        self.assertEqual(digest(as_poc8(final)), POC8_LRT_RUN_SHA256)

    def test_little_round_top_poc9_snapshot_is_pinned(self):
        self.assertEqual(digest(scenario.create("poc-9")), POC9_LRT_STATE_SHA256)


class SideTests(unittest.TestCase):
    def test_renamed_side_duel_runs_headless_and_replays(self):
        catalog = registry()
        with tempfile.TemporaryDirectory() as tmp:
            for player in (None, "grey"):
                with self.subTest(player=player):
                    db = Path(tmp) / f"{player}.sqlite"
                    runner = build_headless(
                        db, player_side=player, scenario_id="test-duel-blue-grey", scenarios=catalog
                    )
                    result = runner.run()
                    state = runner.repository.load(result["game_id"])
                    self.assertEqual(engine.sides(state), ("blue", "grey"))
                    self.assertEqual(state["player_side"], "blue")
                    self.assertEqual({u["side"] for u in state["units"]}, {"blue", "grey"})
                    self.assertEqual(set(state["dispatches"]), {"blue", "grey"})
                    self.assertNotIn("union", json.dumps(state))
                    self.assertNotIn("confederate", json.dumps(state))
                    self.assertEqual(result["replay"]["status"], "identical")
                    # Replay from storage alone, with no catalog or provider.
                    self.assertEqual(build_replay(db).verify(result["game_id"]), result["replay"])
                    if player == "grey":
                        sides = {d["side"] for d in state["decisions"]}
                        self.assertEqual(sides, {"grey", "blue"})

    def test_renamed_sides_play_the_same_battle_as_union_confederate(self):
        # Side ids are labels: the same duel under other ids ends the same way.
        # Contact reports are sorted by side id (recon.reports), so events
        # within an interval may come in another order; compare outcomes.
        renamed = play(registry().create("test-duel-blue-grey"))
        original = play(registry().create("test-duel"))
        names = {"blue": "union", "grey": "confederate"}
        text = json.dumps(renamed["units"])
        for new, old in names.items():
            text = text.replace(f'"{new}"', f'"{old}"')
        self.assertEqual(json.loads(text), original["units"])
        self.assertEqual(names[renamed["winner"]], original["winner"])
        self.assertEqual((renamed["reason"], renamed["turn"]), (original["reason"], original["turn"]))
        kinds = lambda s: sorted(e["kind"] for e in s["events"])
        self.assertEqual(kinds(renamed), kinds(original))

    def test_player_actions_and_views_use_the_player_side(self):
        sim = RulesSimulation()
        state = registry().create("test-duel-blue-grey")
        self.assertEqual(sim.view(state)["side"], "blue")
        self.assertEqual(sim.role(state, "grey"), "attacker")
        state = sim.apply(state, {"type": "orders", "orders": [
            {"unit_id": "B1", "stance": "move", "destination": [5, 5]}]})
        self.assertEqual(state["orders"][-1]["side"], "blue")
        with self.assertRaisesRegex(ValueError, "outside your command"):
            sim.apply(state, {"type": "orders", "orders": [
                {"unit_id": "G1", "stance": "move", "destination": [2, 6]}]})
        with self.assertRaisesRegex(ValueError, "Unknown decision side"):
            sim.apply(state, {"type": "decision", "decision": {
                "side": "confederate", "source": "scripted", "orders": []}})
        god = sim.god_view(state)
        self.assertEqual(set(god["commands"]), {"blue", "grey"})
        commander = CommanderService(sim, DisabledProvider(), scenarios=registry())
        reply = commander.chat(state, "Status?", mode="scripted")
        self.assertIn("keep the knoll", reply["text"])


class LiveServiceSideTests(unittest.TestCase):
    """The clock-driven service commands every side except the player's."""

    def step_once(self, entry):
        from battle import analysis
        from battle.presentation import present_view
        from battle.services.battle import BattleService
        from battle.services.queries import BattleQueries
        from battle.services.replay import ReplayService
        from test_services import ManualClock, MemoryRepository

        catalog = ScenarioRegistry([LITTLE_ROUND_TOP, entry])
        repository = MemoryRepository()
        sim = RulesSimulation()
        app = BattleService(
            repository, sim, CommanderService(sim, DisabledProvider(), scenarios=catalog), catalog,
            BattleQueries(repository, sim, ReplayService(repository, sim),
                          assess=analysis.assess, present=present_view),
            ManualClock, scenario_id=entry.id,
        )
        try:
            self.assertTrue(app.clock_step())
            state = repository.load(app.game_id)
            self.assertEqual(app.queries.replay_service.verify(app.game_id)["status"], "identical")
            return state
        finally:
            app.close()

    def assertComputerCommands(self, state, computer, player):
        self.assertEqual({d["side"] for d in state["decisions"]}, {computer})
        sides = {o["side"] for o in state["orders"]}
        self.assertIn(computer, sides)
        self.assertNotIn(player, sides)

    def test_clock_step_gives_renamed_opponent_the_computer_orders(self):
        state = self.step_once(BLUE_GREY_DUEL)
        self.assertComputerCommands(state, computer="grey", player="blue")

    def test_clock_step_commands_union_when_the_player_is_confederate(self):
        entry = dataclasses.replace(
            DUEL, id="test-duel-confederate-player",
            labels={"poc-11": "test-duel-confederate-player-v1"}, player_side="confederate",
        )
        state = self.step_once(entry)
        self.assertEqual(state["player_side"], "confederate")
        self.assertComputerCommands(state, computer="union", player="confederate")

    def test_poc8_game_still_commands_the_confederates(self):
        sim = RulesSimulation()
        self.assertEqual(sim.computer_side(scenario.create("poc-8")), "confederate")
        self.assertEqual(sim.computer_side(scenario.create()), "confederate")

    def test_poc9_decision_without_side_is_refused(self):
        sim = RulesSimulation()
        decision = {"source": "scripted", "orders": []}
        with self.assertRaisesRegex(ValueError, "must name its side"):
            sim.apply(scenario.create(), {"type": "decision", "decision": decision})
        legacy = sim.apply(scenario.create("poc-8"), {"type": "decision", "decision": decision})
        self.assertEqual(legacy["decisions"][-1], decision)


class VictoryKindTests(unittest.TestCase):
    def test_victory_kinds_refuse_unknown_kinds_and_bad_roles(self):
        first, second = DUEL.sides
        cases = {
            "victory kind 'courtyard-possession' is not one of": dict(
                victory=dataclasses.replace(DUEL.victory, kind="courtyard-possession")),
            "radius must be an integer": dict(victory=dataclasses.replace(DUEL.victory, radius=-1)),
            "hold_turns must be a positive integer": dict(
                victory=dataclasses.replace(DUEL.victory, hold_turns=0)),
            "role must be one of": dict(sides={
                first: dataclasses.replace(DUEL.sides[first], role="garrison"),
                second: DUEL.sides[second]}),
            "side id 'Union!'": dict(
                sides={"Union!": DUEL.sides[first], second: DUEL.sides[second]},
                units=(dataclasses.replace(DUEL.units[0], side="Union!"), DUEL.units[1])),
            "player side 'french' is not a scenario side": dict(player_side="french"),
            "at least two sides": dict(sides={first: DUEL.sides[first]}, units=DUEL.units[:1]),
        }
        for problem, change in cases.items():
            with self.subTest(problem=problem):
                with self.assertRaisesRegex(ValueError, problem):
                    ScenarioRegistry([dataclasses.replace(DUEL, **change)])
        self.assertEqual(tuple(victory.KINDS), ("hold-objective", "hold-compound"))

    def test_hold_objective_parameters_come_from_the_entry(self):
        entry = dataclasses.replace(
            BLUE_GREY_DUEL,
            victory=dataclasses.replace(BLUE_GREY_DUEL.victory, radius=0, hold_turns=1),
        )
        state = ScenarioRegistry([entry]).create()
        self.assertEqual(state["victory"]["radius"], 0)
        # The attacker alone on the objective wins after one interval.
        attacker = next(u for u in state["units"] if u["side"] == "grey")
        attacker["pos"] = list(state["objective"])
        state["turn"] = 1
        self.assertEqual(
            victory.score(state),
            ("grey", "The attackers held the knoll uncontested for 30 seconds."),
        )
        for u in state["units"]:
            if u["side"] == "blue":
                u["status"] = "routed"
        self.assertEqual(
            victory.score(state), ("grey", "Blue formations can no longer hold the position.")
        )


if __name__ == "__main__":
    unittest.main()
