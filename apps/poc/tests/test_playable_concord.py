"""docs/research/74: Concord North Bridge on the command desk.

The desk's computer side plays the entry's own scripted control when the entry
says so (default ruling bt-D08: newly player-facing entries only); Little Round
Top and Hougoumont keep the plain fallback control. The provincial player gets
an authored brief with provenance labels. No model or provider is called.
"""
import tempfile
import unittest
from pathlib import Path

from battle import engine
from battle.adapters.http_api import HttpApi
from battle.adapters.openrouter import DisabledProvider
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import PLAYER_SCENARIOS, build_application, build_scenarios
from battle.command_policy import fallback_orders, scripted_policy
from battle.concord_policy import REGULARS_POLICY
from battle.config import Settings
from battle.presentation import scenario_brief
from battle.scenario_concord import CONCORD_NORTH_BRIDGE as ENTRY
from battle.services.commander import CommanderService

CONCORD = "concord-north-bridge"


class RefusingProvider:
    """A provider that fails the test if the desk asks it for an opponent decision."""

    available = True
    model = "refusing-test-provider"

    def request(self, *_args, **_kwargs):
        raise AssertionError("the desk asked a provider for a scripted opponent's decision")


def opened(tmp, scenario_id):
    return build_application(Path(tmp) / "battle.sqlite", offline=True, settings=Settings(),
                             scenario_id=scenario_id)


def first_decision(app):
    """Advance the opening interval (a decision interval) and return the stored opponent decision."""
    state = app.repository.load(app.game_id)
    app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
    after = app.repository.load(app.game_id)
    return state, [d for d in after["decisions"] if d.get("role") != "staff"][-1]


class DeskOpponentTests(unittest.TestCase):
    def test_concord_desk_opponent_plays_the_regulars_policy_as_headless_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, CONCORD)
            before, decision = first_decision(app)
            self.assertEqual(decision["side"], "british")
            self.assertEqual(decision["policy"], REGULARS_POLICY)
            # The same record the headless runner's opponent call makes from that state.
            headless = CommanderService(RulesSimulation(), DisabledProvider(), scenarios=build_scenarios()).decide(
                before, side="british", mode="scripted", policy=scripted_policy(ENTRY, "british"))
            self.assertEqual(decision, headless)
            self.assertTrue(decision["orders"], "the regulars' guard orders go out at the start")
            app.close()

    def test_concord_desk_opponent_stays_scripted_in_openrouter_mode_without_a_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, CONCORD)
            app.commander.provider = RefusingProvider()
            state = app.repository.load(app.game_id)
            app.execute("mode", {"mode": "openrouter"}, game_id=app.game_id, revision=state["revision"])
            _, decision = first_decision(app)
            self.assertEqual((decision["source"], decision["policy"], decision["fallback"]),
                             ("scripted", REGULARS_POLICY, False))
            app.close()

    def test_little_round_top_and_hougoumont_keep_the_plain_desk_opponent(self):
        # bt-D08 default: only newly player-facing entries opt in, so Hougoumont's French
        # still play the fallback control on the desk, not the headless gate attacker.
        for scenario_id in ("little-round-top", "hougoumont-north-gate"):
            with self.subTest(scenario_id), tempfile.TemporaryDirectory() as tmp:
                app = opened(tmp, scenario_id)
                entry = build_scenarios().resolve(scenario_id)
                self.assertFalse(entry.desk_scripted_opponent)
                before, decision = first_decision(app)
                side = engine.computer_side(before)
                self.assertNotIn("policy", decision)
                observation = RulesSimulation().observation(before, side)
                self.assertEqual(decision["orders"], fallback_orders(observation, engine.role(before, side)))
                app.close()

    def test_only_concord_opts_in(self):
        self.assertEqual([e.id for e in PLAYER_SCENARIOS if e.desk_scripted_opponent], [CONCORD])


class ConcordDeskTests(unittest.TestCase):
    def test_scenario_list_adds_concord_after_the_two_and_keeps_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, None)
            listing = HttpApi(app).read("/api/scenarios", {})
            self.assertEqual(listing["default"], "little-round-top")
            self.assertEqual(listing["scenarios"][2], {"id": CONCORD, "title": "Concord North Bridge",
                                                        "location": "North Bridge · Concord, Massachusetts",
                                                        "date": "1775-04-19"})
            app.close()

    def test_provincial_brief_is_authored_with_provenance(self):
        brief = scenario_brief(ENTRY, "provincial")
        self.assertEqual(brief["campaign"], "CONCORD · 19 APRIL 1775")
        self.assertEqual(brief["mission"]["title"], "Clear the bridge")
        self.assertIn("do not fire unless first fired upon", brief["mission"]["text"])
        self.assertIn("**09:35**", brief["mission"]["text"])
        self.assertEqual(brief["objective"], {"place": "North Bridge", "label": "BRIDGE OBJECTIVE",
                                              "key": "BRIDGE", "ring": True})
        self.assertEqual(brief["outcomes"], {"win": "The bridge is carried.", "loss": "The regulars hold the bridge.",
                                             "draw": "The battle ends in a draw."})
        self.assertNotIn(ENTRY.sides["british"].mission, str(brief))
        for key in ("desk.campaign", "desk.place", "desk.conditions", "brief.provincial.subhead",
                    "brief.provincial.mission_text", "brief.provincial.win", "brief.provincial.loss",
                    "brief.provincial.headings"):
            self.assertIn(key, ENTRY.provenance)

    def test_1775_staff_answer_addresses_the_colonel(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, CONCORD)
            state = app.repository.load(app.game_id)
            app.execute("chat", {"text": "Report."}, game_id=app.game_id, revision=state["revision"])
            answer = app.state()["messages"][-1]["content"]
            self.assertTrue(answer.startswith("Colonel, "), answer)
            app.close()

    def test_a_desk_battle_at_concord_plays_offline_to_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, CONCORD)
            state = app.repository.load(app.game_id)
            # The Acton company's move toward the bridge approach, as a player would send it.
            app.execute("orders", {"orders": [{"unit_id": "P1", "stance": "move", "destination": [11, 10]}]},
                        game_id=app.game_id, revision=state["revision"])
            while state["status"] == "active":
                state = app.repository.load(app.game_id)
                if state["status"] != "active":
                    break
                app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
            self.assertLessEqual(state["turn"], ENTRY.victory.deadline_turns)
            self.assertIn(state["winner"], ("provincial", "british"))
            self.assertEqual(app.state()["last_commander_source"], "scripted")
            app.close()


if __name__ == "__main__":
    unittest.main()
