"""docs/research/75: Pegasus Bridge and Hill 223 on the command desk.

Each computer side plays its entry's own scripted control (default ruling
bt-D08, as for Concord in docs/research/74): the German garrison at Pegasus,
the German battalion at Hill 223. Each player gets a brief whose lines carry a
provenance label. No model or provider is called. The slice also carries the
fixes from the slice 1 review (docs/research/75 §5).
"""
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from battle.adapters.http_api import HttpApi
from battle.adapters.openrouter import DisabledProvider
from battle.adapters.rules import LittleRoundTopCatalog, RulesSimulation
from battle.bootstrap import HEADLESS_SCENARIOS, PLAYER_SCENARIOS, build_application, build_scenarios
from battle.command_policy import scripted_policy
from battle.concord_sensitivity import RELEASE_SENSITIVITY, SENSITIVITY
from battle.config import Settings
from battle.contracts import UnknownScenario
from battle.presentation import scenario_brief
from battle.scenario import LITTLE_ROUND_TOP
from battle.scenario_concord import CONCORD_NORTH_BRIDGE
from battle.scenario_concord import VARIANTS as CONCORD_VARIANTS
from battle.scenario_entry import PROVENANCE, validate
from battle.scenario_hill223 import HILL_223_PATROL, GERMAN_POLICY as HILL_GERMAN
from battle.scenario_hill223 import VARIANTS as HILL_VARIANTS
from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE
from battle.scenario_pegasus import CANAL, CROSSED_SENSITIVITY, GUARD_POLICY, PEGASUS_BRIDGE, RANGE_SENSITIVITY
from battle.scenario_pegasus import VARIANTS as PEGASUS_VARIANTS
from battle.services.commander import CommanderService
from scenario_fixtures import DUEL
from test_playable_concord import RefusingProvider, first_decision, opened
from test_scenario_catalog import battle_service
from test_services import MemoryRepository
from battle.adapters.rules import ScenarioRegistry

PEGASUS, HILL = "pegasus-bridge", "hill-223-patrol"
# The entries made player-facing by docs/research/74 and 75, and only they, opt in (bt-D08).
DESK_SCRIPTED = ("concord-north-bridge", PEGASUS, HILL)
BRIEF_KEYS = ("desk.campaign", "desk.place", "desk.conditions", "brief.{side}.headings", "brief.{side}.subhead",
              "brief.{side}.mission_text", "brief.{side}.win", "brief.{side}.loss")


def every_known_entry():
    """Every entry a catalog, variant table or sensitivity table builds."""
    tables = (CONCORD_VARIANTS, SENSITIVITY, RELEASE_SENSITIVITY, PEGASUS_VARIANTS, RANGE_SENSITIVITY,
              CROSSED_SENSITIVITY, HILL_VARIANTS)
    return list(HEADLESS_SCENARIOS) + [v.entry for table in tables for v in table.values()]


def play_to_result(app, orders=()):
    """Send ``orders`` from the desk, then clock intervals until the battle ends."""
    state = app.repository.load(app.game_id)
    if orders:
        app.execute("orders", {"orders": list(orders)}, game_id=app.game_id, revision=state["revision"])
    while True:
        state = app.repository.load(app.game_id)
        if state["status"] != "active":
            return state
        app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])


class CatalogTests(unittest.TestCase):
    def test_pegasus_and_hill_223_follow_the_three_and_the_default_stays(self):
        self.assertEqual([e.id for e in PLAYER_SCENARIOS],
                         ["little-round-top", "hougoumont-north-gate", "concord-north-bridge", PEGASUS, HILL])
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, None)
            listing = HttpApi(app).read("/api/scenarios", {})
            self.assertEqual(listing["default"], "little-round-top")
            self.assertEqual(listing["scenarios"][3:], [
                {"id": PEGASUS, "title": "Pegasus Bridge", "location": "Caen Canal bridge · Bénouville, Normandy",
                 "date": "1944-06-06"},
                {"id": HILL, "title": "Hill 223", "location": "Hill southwest of Hill 223 · Châtel-Chéhéry, Argonne",
                 "date": "1918-10-08"}])
            app.close()

    def test_the_headless_catalog_keeps_its_order_and_lists_no_entry_twice(self):
        self.assertEqual([e.id for e in HEADLESS_SCENARIOS],
                         ["little-round-top", "hougoumont-north-gate", "concord-north-bridge",
                          "concord-north-bridge-v1", PEGASUS, HILL, "gergovia-recall", "cannae-envelopment"])
        self.assertLessEqual({e.id for e in PLAYER_SCENARIOS}, {e.id for e in HEADLESS_SCENARIOS})

    def test_only_the_intended_entries_carry_the_desk_opponent_flag(self):
        # Slice 1 review: derived entries (Concord v1, its sensitivities, Pegasus's relabelled runs)
        # must not inherit the flag from the entry they copy.
        flagged = sorted({e.id for e in every_known_entry() if e.desk_scripted_opponent})
        self.assertEqual(flagged, sorted(DESK_SCRIPTED))


class DeskOpponentTests(unittest.TestCase):
    def test_each_desk_opponent_plays_its_entrys_policy_as_headless_does(self):
        for scenario_id, entry, side, policy in ((PEGASUS, PEGASUS_BRIDGE, "german", GUARD_POLICY),
                                                 (HILL, HILL_223_PATROL, "german", HILL_GERMAN)):
            with self.subTest(scenario_id), tempfile.TemporaryDirectory() as tmp:
                app = opened(tmp, scenario_id)
                before, decision = first_decision(app)
                self.assertEqual((decision["side"], decision["policy"]), (side, policy))
                headless = CommanderService(RulesSimulation(), DisabledProvider(), scenarios=build_scenarios()).decide(
                    before, side=side, mode="scripted", policy=scripted_policy(entry, side))
                self.assertEqual(decision, headless)
                app.close()

    def test_each_desk_opponent_stays_scripted_in_openrouter_mode_without_a_provider_call(self):
        for scenario_id, policy in ((PEGASUS, GUARD_POLICY), (HILL, HILL_GERMAN)):
            with self.subTest(scenario_id), tempfile.TemporaryDirectory() as tmp:
                app = opened(tmp, scenario_id)
                app.commander.provider = RefusingProvider()
                state = app.repository.load(app.game_id)
                app.execute("mode", {"mode": "openrouter"}, game_id=app.game_id, revision=state["revision"])
                _, decision = first_decision(app)
                self.assertEqual((decision["source"], decision["policy"], decision["fallback"]),
                                 ("scripted", policy, False))
                app.close()

    def test_a_label_the_desk_catalog_does_not_know_keeps_the_call_made_before_the_opt_in(self):
        # Slice 1 review: ``_opponent_control``'s ``except UnknownScenario`` branch. A duel save opened
        # by a catalog that lacks the duel entry: scripted mode records no policy, as before 74.
        repository = MemoryRepository()
        repository.create(ScenarioRegistry([LITTLE_ROUND_TOP, DUEL]).create("test-duel"))
        app = battle_service(LittleRoundTopCatalog(), repository)
        state = repository.load(app.game_id)
        self.assertEqual(app._opponent_control(state, "union"), ("scripted", None))
        app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
        decision = [d for d in repository.load(app.game_id)["decisions"] if d.get("role") != "staff"][-1]
        self.assertEqual(decision["source"], "scripted")
        self.assertNotIn("policy", decision)
        # In openrouter mode the advance still refuses the unmapped label, as at 0fadd68, and asks
        # no provider.
        app.mode = "openrouter"
        state = repository.load(app.game_id)
        while state["turn"] % 3:  # Intervals with no decision; the next one decides.
            app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
            state = repository.load(app.game_id)
        with self.assertRaises(UnknownScenario):
            app.execute("advance", {}, game_id=app.game_id, revision=state["revision"])
        self.assertEqual(app.commander.provider.calls, [])
        self.assertEqual(repository.load(app.game_id)["revision"], state["revision"], "nothing was committed")


class ValidateTests(unittest.TestCase):
    def test_the_desk_opponent_flag_needs_a_scripted_control_for_every_side(self):
        # Slice 1 review: the flag is refused unless the entry's scripted map, or its gates, cover every side.
        for entry in (replace(LITTLE_ROUND_TOP, desk_scripted_opponent=True),
                      replace(PEGASUS_BRIDGE, scripted={"british": PEGASUS_BRIDGE.scripted["british"]})):
            with self.subTest(entry.id), self.assertRaisesRegex(ValueError, "desk_scripted_opponent"):
                validate(entry)
        validate(replace(HOUGOUMONT_NORTH_GATE, desk_scripted_opponent=True))  # Gates: a control per role.
        for entry in PLAYER_SCENARIOS:
            validate(entry)


class BriefTests(unittest.TestCase):
    def test_pegasus_brief_is_labelled_and_states_the_seize_and_hold(self):
        brief = scenario_brief(PEGASUS_BRIDGE, "british")
        self.assertEqual(brief["campaign"], "NORMANDY · 6 JUNE 1944")
        self.assertEqual(brief["mission"]["title"], "Seize the canal bridge")
        text = brief["mission"]["text"]
        for phrase in ("intact", "24 Platoon", "Neilson", "charges", "Ham", "**03:25**", "one minute"):
            self.assertIn(phrase, text)
        self.assertEqual(brief["objective"]["place"], "Caen Canal bridge")
        self.assertEqual(brief["outcomes"], {"win": "The bridge is held until relief.", "loss": "The bridge is lost.",
                                             "draw": "The battle ends in a draw."})
        self.assertNotIn(PEGASUS_BRIDGE.sides["german"].mission, str(brief))
        self.assert_labelled(PEGASUS_BRIDGE, "british")

    def test_hill_223_brief_is_labelled_and_states_the_raid_and_return(self):
        brief = scenario_brief(HILL_223_PATROL, "american")
        self.assertEqual(brief["campaign"], "ARGONNE · 8 OCTOBER 1918")
        self.assertEqual(brief["mission"]["title"], "Bring the patrol back")
        text = brief["mission"]["text"]
        for phrase in ("Acting Sergeant Early", "17", "runner", "5 men", "one prisoner", "**10:30**"):
            self.assertIn(phrase, text)
        self.assertIn("Company G", brief["subhead"])
        self.assertEqual(brief["outcomes"]["win"], "The patrol is back with prisoners.")
        self.assertNotIn(HILL_223_PATROL.sides["german"].mission, str(brief))
        self.assert_labelled(HILL_223_PATROL, "american")
        # Doc 56 §9 q1 / doc 61 §3: the player is the Company G commander.
        self.assertIn("Company G commander", HILL_223_PATROL.provenance["player_side"])

    def assert_labelled(self, entry, side):
        for key in BRIEF_KEYS:
            key = key.format(side=side)
            with self.subTest(key):
                self.assertTrue(entry.provenance[key].startswith(PROVENANCE), key)
        cited = " ".join(entry.provenance[k.format(side=side)] for k in BRIEF_KEYS)
        self.assertRegex(cited, r"S5\d|S40")  # The doc's own source register.

    def test_concord_subhead_cites_s49_for_the_guard_and_labels_light(self):
        # Slice 1 review: S49 says the companies guarded the bridge; "light" is not in S47 to S49.
        note = CONCORD_NORTH_BRIDGE.provenance["brief.provincial.subhead"]
        self.assertIn("guarding the bridge (S49", note)
        self.assertIn("authored: 'light'", note)


class StaffAnswerTests(unittest.TestCase):
    def answer(self, scenario_id):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, scenario_id)
            state = app.repository.load(app.game_id)
            app.execute("chat", {"text": "Report."}, game_id=app.game_id, revision=state["revision"])
            text = app.state()["messages"][-1]["content"]
            app.close()
            return text

    def test_the_closing_follows_each_voice_and_its_transport(self):
        # Slice 1 review: no "by runner" alone where orders are spoken; 1863 and 1815 unchanged.
        for scenario_id, start, closing in (
                ("little-round-top", "General, ", "Send your instructions by runner; "),
                ("hougoumont-north-gate", "General, ", "Send your instructions by runner; "),
                ("concord-north-bridge", "Colonel, ",
                 "Give your orders by word of mouth to the companies within earshot, or send them by runner; "),
                (PEGASUS, "Major, ", "Send your orders by wireless, by word of mouth close by, or by runner; "),
                (HILL, "Sir, ", "Pass your orders by word of mouth close by, or send them by runner; ")):
            with self.subTest(scenario_id):
                text = self.answer(scenario_id)
                self.assertTrue(text.startswith(start), text)
                self.assertIn(closing + "the latest reports may already be out of date.", text)


class PlayTests(unittest.TestCase):
    def test_a_desk_battle_at_pegasus_plays_offline_to_a_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, PEGASUS)
            # 24 Platoon, with the sappers, onto the bridge, as a player would send it.
            state = play_to_result(app, [{"unit_id": "D24", "stance": "move", "destination": list(CANAL)}])
            self.assertIn(state["winner"], ("british", "german"))
            self.assertLessEqual(state["turn"], PEGASUS_BRIDGE.victory.deadline_turns)
            self.assertTrue(state["reason"])
            german = [d for d in state["decisions"] if d.get("side") == "german" and d.get("role") != "staff"]
            self.assertTrue(german and all(d["policy"] == GUARD_POLICY for d in german))
            self.assertEqual(app.state()["last_commander_source"], "scripted")
            app.close()

    def test_a_desk_battle_at_hill_223_plays_offline_to_a_readable_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = opened(tmp, HILL)
            state = play_to_result(app)
            self.assertIn(state["winner"], ("american", "german"))
            self.assertLessEqual(state["turn"], HILL_223_PATROL.victory.deadline_turns)
            # The raid-and-return reasons of 08e7ef2/ec1be7b name the raid, the men home and the captives.
            self.assertRegex(state["reason"], r"raiders|raiding force")
            german = [d for d in state["decisions"] if d.get("side") == "german" and d.get("role") != "staff"]
            self.assertTrue(german and all(d["policy"] == HILL_GERMAN for d in german))
            app.close()


if __name__ == "__main__":
    unittest.main()
