"""poc-13 part B: succession, spoken-order reach, smoothbore fire and the
1775 voice, plus the carried review items. Design: docs/research/47.

Fixtures are small synthetic entries on flat ground; none is a scenario.
"""

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from battle import command_policy, engine, grid, runtime, scenario
from battle.engine_v2 import InvalidOrder
from battle.presentation import COLONIAL_VOICE_PROFILE, present_view
from battle.scenario_command import (
    COLONIAL_COMMUNICATIONS,
    SMOOTHBORE_1775,
    WEAPONS_1775,
    CommandEntry,
    WeaponEntry,
)
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from battle.storage import Store
from scenario_fixtures import DUEL, GATE_OUTSIDE, GATEWAY, flat_terrain, gate_entry
from test_gateway_push import events, unit

COMMAND = CommandEntry(succession={"union": ("B2", "B3"), "confederate": ()})


def advance(s, n=1):
    for _ in range(n):
        if s["status"] != "active":break
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def era_entry(units=None, command=COMMAND, weapons=None, communications=COLONIAL_COMMUNICATIONS,
              voice=COLONIAL_VOICE_PROFILE):
    """B1 commands Blue at 5,12; B2 is two hexes north of it, B3 eight hexes
    south; G1 (no cartridges) stands far to the north-east."""
    units = units or (UnitEntry("B1", "union", "Blue command", (5, 12)),
                      UnitEntry("B2", "union", "Blue front company", (5, 10)),
                      UnitEntry("B3", "union", "Blue column", (5, 20)),
                      UnitEntry("G1", "confederate", "Grey guard", (20, 2), {"ammo": 0}))
    return dataclasses.replace(
        DUEL, id="test-1775", labels={"poc-12": "test-1775-v0", "poc-13": "test-1775-v1"},
        prompt_version="test-1775-v1", prompt_setting="Test Bridge, 1775",
        units=units, command=command, weapons=weapons,
        communications=communications, voice_profile=voice,
        victory=VictoryEntry(kind="hold-objective", objective=(1, 1), deadline_turns=60, objective_name="far corner"))


def era(**kw):
    return build_state(dry_run(validate(era_entry(**kw))))


def order(s, uid, stance="move", destination=None):
    return engine.issue(s, "union", {"unit_id": uid, "stance": stance, "destination": destination})


def last(s, kind, **match):
    found = [e for e in events(s, kind) if all(e.get(k) == v for k, v in match.items())]
    return found[-1] if found else None


class SuccessionTests(unittest.TestCase):
    """An officer's fall passes command on; with none left a fallback applies."""

    def test_next_officer_takes_command_and_the_unit_keeps_its_order(self):
        s = era(units=(UnitEntry("B1", "union", "Blue command", (5, 12)),
                       UnitEntry("B2", "union", "Blue front company", (5, 10), {"morale": 100}),
                       UnitEntry("B3", "union", "Blue column", (5, 20)),
                       UnitEntry("G1", "confederate", "Grey guard", (20, 2), {"ammo": 0})))
        self.assertEqual((unit(s, "B2")["officers"], unit(s, "B2")["officer_step"]), (2, 13))
        unit(s, "B2").update(stance="move", target=[5, 6], order_version=1, loss_credit=1400)
        s = advance(s)
        b2 = unit(s, "B2")
        self.assertEqual(last(s, "officer_down", unit_id="B2")["officers_left"], 1)
        self.assertEqual((b2["officers"], b2.get("leaderless", False)), (1, False))
        self.assertEqual((b2["stance"], b2["target"]), ("move", [5, 6]))
        sent = order(s, "B2", "hold")  # B2 has marched out of earshot: a runner relays it.
        s = advance(s, 6)
        self.assertTrue(last(s, "order_delivered", order_id=sent["id"]))
        self.assertEqual(unit(s, "B2")["stance"], "hold")

    def test_unit_with_no_officer_left_keeps_its_last_order_and_refuses_new_ones(self):
        s = era(units=(UnitEntry("B1", "union", "Blue command", (5, 12)),
                       UnitEntry("B2", "union", "Blue front company", (5, 10),
                                 {"initial": 26, "strength": 26, "morale": 100, "officers": 1}),
                       UnitEntry("B3", "union", "Blue column", (5, 20)),
                       UnitEntry("G1", "confederate", "Grey guard", (20, 2), {"ammo": 0})))
        unit(s, "B2").update(stance="hold", order_version=1, loss_credit=1300)
        s = advance(s)
        b2 = unit(s, "B2")
        self.assertTrue(b2["leaderless"])
        self.assertTrue(last(s, "unit_leaderless", unit_id="B2"))
        self.assertEqual(b2["morale"], 90 - 13 * 4 - 10)  # Holding caps morale at 90 first.
        self.assertNotEqual(b2["status"], "routed")
        self.assertTrue(engine.comms.operational(s, "union"))  # Only B2 lost its officers.
        sent = order(s, "B2", "move", [5, 6])
        s = advance(s, 3)
        self.assertEqual(last(s, "order_refused", order_id=sent["id"])["unit_id"], "B2")
        self.assertEqual((unit(s, "B2")["stance"], unit(s, "B2")["pos"]), ("hold", [5, 10]))

    def test_side_command_passes_to_the_named_successor_after_the_delay(self):
        s = era()
        unit(s, "B1")["morale"] = 0
        s = advance(s)
        self.assertEqual(unit(s, "B1")["status"], "routed")
        self.assertEqual(last(s, "command_vacant", side="union")["unit_id"], "B1")
        with self.assertRaisesRegex(InvalidOrder, "disrupted"):
            order(s, "B3", "hold")
        s = advance(s)
        self.assertEqual(last(s, "command_succeeded", side="union")["to_unit"], "B2")
        self.assertEqual(s["commanders"]["union"]["unit_id"], "B2")
        self.assertEqual(engine.view(s, "union")["hq"], unit(s, "B2")["pos"])
        self.assertEqual(order(s, "B3", "hold")["transport"]["method"], "courier")

    def test_side_with_no_successor_falls_back_to_standing_orders(self):
        s = era(command=CommandEntry(succession={"union": (), "confederate": ()}))
        unit(s, "B3").update(stance="move", target=[5, 16], order_version=1)
        unit(s, "B1")["morale"] = 0
        s = advance(s, 6)
        self.assertEqual(last(s, "command_lost", side="union")["unit_id"], "B1")
        self.assertEqual(s["commanders"]["union"]["unit_id"], "B1")
        self.assertEqual(unit(s, "B3")["pos"][1] < 20, True)  # The column marches on.
        with self.assertRaisesRegex(InvalidOrder, "disrupted"):
            order(s, "B3", "hold")

    def test_split_apportions_officers_and_combine_adds_them(self):
        from battle import command

        a = {"initial": 40, "strength": 40, "officers": 1, "officer_step": 20, "officer_losses": 5}
        child = dict(a, initial=10, strength=10)
        command.split_officers(a, child, 10)
        self.assertEqual((a["officers"], child["officers"], child["leaderless"], "leaderless" in a), (1, 0, True, False))
        command.combine_officers(a, child)
        self.assertEqual((a["officers"], a["officer_losses"]), (1, 0))
        plain = {"initial": 40, "strength": 40}
        command.split_officers(plain, dict(plain), 10)
        self.assertNotIn("officers", plain)  # Earlier battles carry no officers.

    def test_registration_refuses_bad_command_data(self):
        cases = {
            "unknown unit": CommandEntry(succession={"union": ("B9",), "confederate": ()}),
            "other side": CommandEntry(succession={"union": ("G1",), "confederate": ()}),
            "the command unit": CommandEntry(succession={"union": ("B1",), "confederate": ()}),
            "unknown side": CommandEntry(succession={"red": (), "union": (), "confederate": ()}),
            "negative delay": dataclasses.replace(COMMAND, succession_delay=-1),
            "officers": dataclasses.replace(COMMAND, officers="two"),
        }
        for name, command in cases.items():
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, "command|succession|officers"):
                    validate(era_entry(command=command))
        with self.assertRaisesRegex(ValueError, "officers"):
            validate(era_entry(units=(UnitEntry("B1", "union", "Blue command", (5, 12), {"officers": -1}),
                                      UnitEntry("G1", "confederate", "Grey guard", (20, 2)))))
        with self.assertRaisesRegex(ValueError, "poc-13"):
            build_state(era_entry(), "poc-12")


class SuccessionReviewTests(unittest.TestCase):
    """Fixes from the part B review (code-critic)."""

    def test_both_commands_falling_in_one_interval_replay_identically(self):
        s = era()
        unit(s, "B1")["morale"] = 0
        unit(s, "G1")["morale"] = 0
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "succession.sqlite")
            gid = store.create(s)
            for _ in range(3):  # In memory, as the headless runner keeps it.
                if s["status"] != "active":break
                n = runtime.apply(s, {"type": "advance", "decision": None})
                store.save(gid, n, s["revision"])
                s = n
            self.assertEqual([e["side"] for e in events(s, "command_vacant")], ["union", "confederate"])
            self.assertEqual(runtime.verify_replay(store, gid)["status"], "identical")

    def test_standing_instruction_to_a_leaderless_unit_is_refused(self):
        from battle import standing

        s = era()
        sent = standing.issue(s, "union", {"unit_id": "B2", "profile_id": "cautious"})
        unit(s, "B2")["leaderless"] = True
        s = advance(s, 3)
        self.assertEqual(next(o for o in s["standing_orders"] if o["id"] == sent["id"])["status"], "refused")
        self.assertEqual(unit(s, "B2")["standing_profile"], "balanced")

    def test_registration_refuses_units_without_an_officer(self):
        with self.assertRaisesRegex(ValueError, "officers must be a positive integer"):
            validate(era_entry(command=dataclasses.replace(COMMAND, officers=0)))
        with self.assertRaisesRegex(ValueError, "officers must be a positive integer"):
            validate(era_entry(units=(UnitEntry("B1", "union", "Blue command", (5, 12), {"officers": 0}),
                                      UnitEntry("G1", "confederate", "Grey guard", (20, 2)))))

    def test_reports_on_their_way_to_the_fallen_command_go_to_the_successor(self):
        s = era()
        unit(s, "B1")["morale"] = 0
        s = advance(s)  # B1 routs: the vacancy opens.
        pending = next(r for r in s["reports"] if r["data"] and r["data"].get("id") == "B3")
        rid, before = pending["transport"]["id"], pending["transport"]["forwardings"]
        self.assertEqual(pending["transport"]["recipient_id"], "B1")
        s = advance(s)  # B2 takes command.
        moved = next(r for r in s["reports"] if r["transport"]["id"] == rid)["transport"]
        self.assertEqual((moved["recipient_id"], moved["forwardings"], moved["address"]),
                         ("B2", before + 1, unit(s, "B2")["pos"]))
        for _ in range(12):
            if any(e["report_id"] == rid for e in events(s, "report_received")):break
            s = advance(s)
        self.assertTrue(any(e["report_id"] == rid for e in events(s, "report_received")))

    def test_1775_standing_and_recommendation_text_does_not_say_general(self):
        from battle import analysis, standing

        s = era()
        standing.issue(s, "union", {"unit_id": "B3", "profile_id": "cautious"})
        view = engine.view(s, "union")
        view["recommendations"] = [{"id": "A1", "text": "General, the men are fatigued."}]
        shown = present_view(view, era_entry())
        self.assertTrue(shown["dispatches"][-1]["display_text"].startswith("Colonel, preserve"))
        self.assertEqual(shown["recommendations"][0]["display_text"], "Colonel, the men are fatigued.")
        rows = present_view(dict(view, analysis=analysis.assess(view)), era_entry())["analysis"]["units"]
        self.assertTrue(all(r["recommendation"]["display_reason"].startswith("Colonel,") for r in rows))
        # Other voices are untouched: no display text is added or changed.
        plain = present_view(dict(view, analysis=analysis.assess(view)))
        self.assertEqual(plain["dispatches"][-1]["display_text"], plain["dispatches"][-1]["text"])
        self.assertNotIn("display_text", plain["recommendations"][0])
        self.assertNotIn("display_reason", plain["analysis"]["units"][0]["recommendation"])


class VoiceReachTests(unittest.TestCase):
    """A spoken order reaches only units within earshot; others get a runner."""

    def test_order_within_voice_reach_is_spoken_and_delivered_next_interval(self):
        s = era()
        self.assertEqual(grid.distance(unit(s, "B1")["pos"], unit(s, "B2")["pos"]), 2)
        sent = order(s, "B2", "move", [5, 8])
        self.assertEqual((sent["transport"]["method"], sent["arrival_turn"]), ("voice", 1))
        s = advance(s)
        self.assertEqual(last(s, "order_delivered", order_id=sent["id"])["turn"], 1)

    def test_order_beyond_voice_reach_goes_by_runner_and_the_unit_keeps_its_last_order(self):
        s = era()
        unit(s, "B3").update(stance="move", target=[5, 16], order_version=1)
        sent = order(s, "B3", "hold")
        self.assertEqual(sent["transport"]["method"], "courier")
        self.assertGreater(sent["arrival_turn"], 1)
        s = advance(s)
        self.assertIsNone(last(s, "order_delivered", order_id=sent["id"]))
        self.assertEqual(unit(s, "B3")["stance"], "move")
        s = advance(s, sent["arrival_turn"] + 4)
        self.assertTrue(last(s, "order_delivered", order_id=sent["id"]))

    def test_unit_out_of_earshot_at_delivery_gets_the_word_by_runner(self):
        s = era()
        # Headquarters still places B2 at 5,10, in earshot; it has moved on.
        unit(s, "B2").update(pos=[5, 4], stance="move", target=[5, 2], order_version=1)
        sent = order(s, "B2", "hold")
        self.assertEqual(sent["transport"]["method"], "voice")
        s = advance(s)
        self.assertEqual(last(s, "voice_out_of_reach")["packet"]["recipient_id"], "B2")
        self.assertIsNone(last(s, "order_delivered", order_id=sent["id"]))
        self.assertEqual(unit(s, "B2")["stance"], "move")
        s = advance(s, 12)
        self.assertGreater(last(s, "order_delivered", order_id=sent["id"])["turn"], 1)

    def test_courier_profiles_keep_voice_for_the_command_detachment_only(self):
        s = era(command=None, communications="civil-war-courier-v1", voice="civil-war-en-v1")
        self.assertEqual(order(s, "B2", "hold")["transport"]["method"], "courier")
        self.assertEqual(order(s, "B1", "hold")["transport"]["method"], "voice")


def firing(distance, weapons=WEAPONS_1775):
    """B1 (smoothbore) ``distance`` hexes south of G1, which holds its fire."""
    units = (UnitEntry("B1", "union", "Blue command", (5, 5 + distance), {"weapon_class": "smoothbore muskets"}),
             UnitEntry("G1", "confederate", "Grey guard", (5, 5),
                       {"fire_posture": "hold_fire", "weapon_class": "smoothbore muskets"}))
    return advance(era(units=units, command=None, weapons=weapons))


def volleys(s):
    return [e for e in events(s, "volley") if e["unit_id"] == "B1"]


class SmoothboreTests(unittest.TestCase):
    """Smoothbore muskets reach less far and hit less often than the rifle baseline."""

    def test_smoothbore_does_not_fire_beyond_its_range(self):
        self.assertEqual(volleys(firing(3)), [])
        self.assertTrue(volleys(firing(2)))
        self.assertTrue(volleys(firing(3, weapons=None)))  # The rifle baseline reaches 3.

    def test_smoothbore_volley_is_weaker_than_the_rifle_baseline(self):
        smooth = volleys(firing(2))[0]["exposure"]
        rifle = volleys(firing(2, weapons=None))[0]["exposure"]
        self.assertEqual((smooth, rifle), (72, 240))

    def test_values_are_labelled_assumptions_and_bad_values_are_refused(self):
        self.assertTrue(SMOOTHBORE_1775.basis.startswith("assumption:"))
        for bad in (WeaponEntry(0, 60, "x"), WeaponEntry(2, 150, "x"), WeaponEntry(6, 60, "x")):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "weapon"):
                    validate(era_entry(weapons={"smoothbore muskets": bad}))


class VoiceTests(unittest.TestCase):
    """The 1775 entry speaks in a period voice in prompts and order text."""

    def test_1775_prompt_uses_the_period_voice_and_states_the_voice_reach(self):
        prompt = command_policy.system_prompt("union", era_entry())
        self.assertIn("American Revolution in 1775", prompt)
        self.assertIn("within 2 hexes of your command detachment by voice", prompt)
        self.assertNotIn("Address the player as General", prompt)
        self.assertIn("Orders travel by runner.", command_policy.system_prompt("union"))

    def test_1775_order_text_is_in_the_period_voice(self):
        s = era()
        order(s, "B2", "hold")
        order(s, "B3", "move", [5, 18])
        shown = present_view(engine.view(s, "union"), era_entry())["dispatches"]
        self.assertEqual([d["message_key"] for d in shown], ["order.spoken", "order.carried"])
        self.assertTrue(shown[0]["display_text"].startswith("To B2: Stand fast"))
        self.assertIn("by word of mouth", shown[0]["display_text"])
        plain = present_view(engine.view(s, "union"))["dispatches"]
        self.assertEqual(plain[0]["display_text"], plain[0]["text"])

    def test_scripted_order_text_uses_the_entry_voice(self):
        from battle.adapters.openrouter import DisabledProvider
        from battle.adapters.rules import RulesSimulation
        from battle.adapters.rules import ScenarioRegistry
        from battle.services.commander import CommanderService

        catalog = ScenarioRegistry([scenario.LITTLE_ROUND_TOP, era_entry()])
        commander = CommanderService(RulesSimulation(), DisabledProvider(), scenarios=catalog)
        self.assertTrue(commander.decide(era(), "union", mode="scripted")["text"].startswith("Colonel"))
        self.assertTrue(commander.decide(scenario.create(), "union", mode="scripted")["text"].startswith("General"))


class CarriedReviewTests(unittest.TestCase):
    def test_prompt_lists_fire_orders_with_a_null_destination_under_new_versions(self):
        from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE

        for entry in (scenario.LITTLE_ROUND_TOP, HOUGOUMONT_NORTH_GATE):
            with self.subTest(entry.id):
                self.assertIn("hold/rest/resupply/dig_in/hold_fire/open_fire use null",
                              command_policy.system_prompt(next(iter(entry.sides)), entry))
        self.assertEqual((scenario.LITTLE_ROUND_TOP.prompt_version, HOUGOUMONT_NORTH_GATE.prompt_version),
                         ("lrt-side-v3", "hougoumont-side-v2"))

    def test_model_telemetry_records_the_rules_edition_and_order_catalog(self):
        from battle.adapters.rules import RulesSimulation
        from battle.services.commander import CommanderService
        from test_scenario_catalog import RecordingProvider

        decision = CommanderService(RulesSimulation(), RecordingProvider()).decide(scenario.create(), "union")
        self.assertEqual((decision["rules"], decision["order_catalog"]), ("poc-13", "common-orders-v5"))

    def test_posture_orders_replay_identically(self):
        from test_poc13 import duel

        s = duel("hold_fire", "hold_fire")
        actions = ([{"type": "orders", "orders": [{"unit_id": "B1", "stance": "hold_fire", "destination": None}]}]
                   + [{"type": "advance", "decision": None}] * 2
                   + [{"type": "orders", "orders": [{"unit_id": "B1", "stance": "open_fire", "destination": None}]}]
                   + [{"type": "advance", "decision": None}] * 4)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "posture.sqlite")
            gid = store.create(s)
            for action in actions:
                n = runtime.apply(s, action)
                store.save(gid, n, s["revision"])
                s = n
            self.assertEqual([e["fire_posture"] for e in events(s, "fire_posture_set")], ["hold_fire", "open_fire"])
            self.assertTrue(events(s, "volley"))
            self.assertEqual(runtime.verify_replay(store, gid)["status"], "identical")

    def test_registration_refuses_water_in_a_compound_or_gateway(self):
        for name, pos, crossing in (("gateway", GATEWAY, None), ("outside", GATE_OUTSIDE, "bridge"),
                                    ("compound", [9, 10], "ford")):
            with self.subTest(name):
                def terrain(pos=pos, crossing=crossing):
                    cells = flat_terrain()
                    cells[grid.key(pos)].update(water=True, **({"crossing": crossing} if crossing else {}))
                    return cells
                entry = gate_entry()
                entry = dataclasses.replace(entry, map=dataclasses.replace(entry.map, terrain=terrain))
                with self.assertRaisesRegex(ValueError, "water in a compound or gateway"):
                    dry_run(validate(entry))


def smoothbore_approach(distance, grey_stance="move"):
    """Two smoothbore command detachments ``distance`` hexes apart in one
    column, under weapon and command rules. Blue orders itself north past
    Grey's hex; Grey orders itself south past Blue's, or to hold."""
    units = (UnitEntry("B1", "union", "Blue company", (5, 5 + distance), {"weapon_class": "smoothbore muskets"}),
             UnitEntry("G1", "confederate", "Grey company", (5, 5), {"weapon_class": "smoothbore muskets"}))
    command = CommandEntry(succession={"union": (), "confederate": ()})
    s = era(units=units, command=command, weapons=WEAPONS_1775)
    engine.issue(s, "union", {"unit_id": "B1", "stance": "move", "destination": [5, 1]})
    grey = [5, 18] if grey_stance == "move" else None
    engine.issue(s, "confederate", {"unit_id": "G1", "stance": grey_stance, "destination": grey})
    return s


class SmoothboreApproachMechanicsCheck(unittest.TestCase):
    """Mechanics check, NOT historical calibration: two smoothbore formations
    ordered to close must not halt for good on fire that cannot reach them.
    No winner is asserted; the values are assumptions (docs/research/47)."""

    LIMIT = 12  # intervals

    def run_until_in_range(self, s):
        gaps = []
        for _ in range(self.LIMIT):
            if s["status"] != "active":break
            s = advance(s)
            gaps.append(grid.distance(unit(s, "B1")["pos"], unit(s, "G1")["pos"]))
            if gaps[-1] <= SMOOTHBORE_1775.range_hexes:break
        return s, gaps

    def test_formations_ordered_to_close_reach_smoothbore_range(self):
        for distance in (3, 4, 5):
            with self.subTest(distance=distance):
                s, gaps = self.run_until_in_range(smoothbore_approach(distance))
                self.assertLessEqual(min(gaps), SMOOTHBORE_1775.range_hexes, gaps)
                for uid in ("B1", "G1"):
                    halted = [e for e in events(s, "local_decision") if e["unit_id"] == uid]
                    self.assertFalse(all(e["action"] == "defend" for e in halted), (uid, gaps))

    def test_a_holding_formation_still_holds_while_the_other_closes(self):
        for distance in (3, 4, 5):
            with self.subTest(distance=distance):
                s, gaps = self.run_until_in_range(smoothbore_approach(distance, grey_stance="hold"))
                self.assertLessEqual(min(gaps), SMOOTHBORE_1775.range_hexes, gaps)
                self.assertEqual([e for e in events(s, "unit_moved") if e["unit_id"] == "G1"], [])
                self.assertEqual(unit(s, "G1")["stance"], "hold")


class Poc13EditionTests(unittest.TestCase):
    def test_poc13_runs_and_saves_keep_their_part_a_digests(self):
        from unittest import mock
        from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE as HOUGOUMONT
        from test_contact import at_threshold, corridor
        from test_gates import advance_through_service
        from test_gateway_push import at_the_north_gate
        from test_poc13 import duel
        from test_scenario_sides import digest, play

        self.assertEqual(digest(play(scenario.create("poc-13"))), POC13_LRT_RUN_SHA256)
        with mock.patch.object(engine, "advance", wraps=engine.advance) as live:
            save = advance_through_service(scenario.create("poc-13"), 10)
            final = advance_through_service(json.loads(json.dumps(save, sort_keys=True)), 30)
            hougoumont = advance_through_service(build_state(HOUGOUMONT, "poc-13"), 40,
                                                 (scenario.LITTLE_ROUND_TOP, HOUGOUMONT))
        self.assertGreaterEqual(live.call_count, final["turn"] + hougoumont["turn"])
        self.assertEqual((final["rules"], hougoumont["rules"]), ("poc-13", "poc-13"))
        self.assertEqual(digest(final), POC13_LRT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(hougoumont), POC13_HOUGOUMONT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(advance(at_the_north_gate("poc-13"), 15)), POC13_AT_THE_NORTH_GATE_SHA256)
        self.assertEqual(digest(advance(at_threshold(rules="poc-13"), 4)), POC13_STALL_SHA256)
        self.assertEqual(digest(advance(corridor(("C1", "C2", "C3"), rules="poc-13"), 24)), POC13_CORRIDOR_SHA256)
        self.assertEqual(digest(advance(duel("hold_fire", "open_fire"), 12)), POC13_FIRE_DUEL_SHA256)


# Taken at e165371 (poc-13 part A, before part B) as sha256 of the sort-keyed
# JSON state: the scripted poc-13 Little Round Top run (Union, turn 60); saves
# advanced through BattleService (Little Round Top 10 then 30 intervals, ends
# at turn 28; Hougoumont 40, ends at turn 29); the north-gate arrangement
# (turn 12); the courtyard stall (4 intervals); the corridor contest (24); and
# the part A hold-fire duel (12 intervals).
POC13_LRT_RUN_SHA256 = "925e9261fabb679cb177f603c795b3f358a94de242e8f82443faa6f91190e16d"
POC13_LRT_SAVE_ADVANCED_SHA256 = "961ae3827da2bb6a6cf29d9caa186c3aeabe9d7cbbef79cf90c6166f0d6b0e2f"
POC13_HOUGOUMONT_SAVE_ADVANCED_SHA256 = "a02f11b5e29c88ed35b14af98d7d1611895ebb6ac518acebdffd301d503a5d86"
POC13_AT_THE_NORTH_GATE_SHA256 = "5929ec8c2033521ee7fa947b1352ca532acec9752fb24cd54c99c4c74f3aeb23"
POC13_STALL_SHA256 = "258c943805930637c2c72752ab972e53026973d36735f6cbb0b2445864537f8f"
POC13_CORRIDOR_SHA256 = "2e27fa2fd63eac4f1514dbe32eb6aadc9dbfa2b7c8a9f51aec69d6956c0c2017"
POC13_FIRE_DUEL_SHA256 = "10a85a6241579a9ab0d4c88d5df5941643114fcd8c89a321969d3403afbc684b"


if __name__ == "__main__":
    unittest.main()
