"""1944 engine and data for the Pegasus Bridge scenario: bridge state, company
radio and the 1944 voice, codeword signals, night observation in fire and a
single authored weapon range. Design: docs/research/53.

Fixtures are small synthetic entries on flat ground with a canal along row
10; none is the Pegasus scenario (that entry is a separate task).
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from battle import command_policy, engine, grid, runtime, tactics_v10
from battle.presentation import WWII_VOICE_PROFILE, present_view
from battle.scenario_command import WeaponEntry
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from battle.scenario_wwii import RADIO_COMMUNICATIONS, BridgeEntry, SignalEntry
from battle.storage import Store
from scenario_fixtures import DUEL, flat_terrain
from test_gateway_push import events, unit

CANAL_ROW = 10
BRIDGE = (12, 10)
CANAL_BRIDGE = BridgeEntry("canal-bridge", "Canal bridge", BRIDGE)
HAM = SignalEntry("Ham", "Canal bridge taken intact.", "union", "canal-bridge")
RIFLE_1944 = WeaponEntry(1, 100, "assumption: test value")


def canal_terrain():
    cells = flat_terrain()
    for c in range(grid.COLS):
        cells[grid.key([c, CANAL_ROW])].update(terrain="water", water=True, cover=0)
    cells[grid.key(list(BRIDGE))]["crossing"] = "bridge"
    return cells


DEFAULT_UNITS = (
    UnitEntry("B1", "union", "Company headquarters", (12, 16)),
    UnitEntry("B2", "union", "Leading platoon", (12, 11)),
    UnitEntry("G1", "confederate", "Guard", (20, 2), {"ammo": 0}),
)


def night_entry(units=DEFAULT_UNITS, communications="civil-war-courier-v1", voice="civil-war-en-v1", **kw):
    return dataclasses.replace(
        DUEL, id="test-1944", labels={"poc-13": "test-1944-v1"},
        prompt_version="test-1944-v1", prompt_setting="Test Canal, 1944",
        units=units, communications=communications, voice_profile=voice,
        victory=VictoryEntry(kind="hold-objective", objective=(1, 1), deadline_turns=60, objective_name="far corner"),
        map=dataclasses.replace(DUEL.map, terrain=canal_terrain), **kw)


def night(**kw):
    return build_state(dry_run(validate(night_entry(**kw))))


def advance(s, n=1):
    for _ in range(n):
        if s["status"] != "active":break
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def order(s, uid, stance="move", destination=None, side="union"):
    return engine.issue(s, side, {"unit_id": uid, "stance": stance, "destination": destination})


def bridge_feature(features):
    return next(f for f in features if f["id"] == "canal-bridge")


class BridgeStateTests(unittest.TestCase):
    """A bridge hex is intact, wired with charges, or destroyed; destroyed blocks crossing."""

    def test_destroyed_bridge_cannot_be_crossed_and_a_wired_one_can(self):
        for state, crosses in (("destroyed", False), ("charges", True), ("intact", True)):
            with self.subTest(state):
                s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, state=state),))
                self.assertEqual(s["cells"][grid.key(list(BRIDGE))]["bridge_state"], state)
                self.assertEqual(bool(grid.path(s["cells"], [12, 11], [12, 8])), crosses)
                unit(s, "B2").update(stance="move", target=[12, 8], order_version=1)
                s = advance(s, 12)
                self.assertEqual(unit(s, "B2")["pos"][1] < CANAL_ROW, crosses)

    def test_order_to_a_destroyed_bridge_is_refused_as_water(self):
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, state="destroyed"),))
        with self.assertRaisesRegex(engine.InvalidOrder, "impassable water"):
            order(s, "B2", "move", list(BRIDGE))

    def test_move_to_a_bridge_blown_unreported_is_accepted_and_fails_to_path(self):
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, schedule=((1, "destroyed"),)),))
        s = advance(s)
        self.assertEqual(bridge_feature(engine.view(s, "union")["map_features"])["state"], "intact")
        sent = order(s, "B2", "move", list(BRIDGE))  # Accepted: headquarters believes the bridge stands.
        s = advance(s, 8)
        self.assertTrue([e for e in events(s, "order_delivered") if e["order_id"] == sent["id"]])
        self.assertFalse([e for e in events(s, "unit_moved") if e["unit_id"] == "B2"])
        self.assertEqual(grid.path(s["cells"], unit(s, "B2")["pos"], list(BRIDGE)), [])
        # Once B2's report arrives headquarters knows, and the same order is refused.
        self.assertEqual(bridge_feature(engine.view(s, "union")["map_features"])["state"], "destroyed")
        with self.assertRaisesRegex(engine.InvalidOrder, "impassable water"):
            order(s, "B2", "move", list(BRIDGE))

    def test_scheduled_demolition_is_an_event_and_replays_identically(self):
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, schedule=((2, "charges"), (4, "destroyed"))),))
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "bridge.sqlite")
            gid = store.create(s)
            for _ in range(6):
                n = runtime.apply(s, {"type": "advance", "decision": None})
                store.save(gid, n, s["revision"])
                s = n
            changes = [(e["turn"], e["bridge_id"], e["from_state"], e["to_state"]) for e in events(s, "bridge_state_changed")]
            self.assertEqual(changes, [(2, "canal-bridge", "intact", "charges"), (4, "canal-bridge", "charges", "destroyed")])
            self.assertEqual(s["cells"][grid.key(list(BRIDGE))]["bridge_state"], "destroyed")
            self.assertEqual(runtime.verify_replay(store, gid)["status"], "identical")

    def test_headquarters_learns_the_state_by_report_while_god_view_shows_it(self):
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, schedule=((1, "destroyed"),)),))
        self.assertEqual(bridge_feature(engine.view(s, "union")["map_features"])["state"], "intact")
        s = advance(s)
        self.assertEqual(bridge_feature(engine.god_view(s)["map_features"])["state"], "destroyed")
        self.assertEqual(bridge_feature(engine.view(s, "union")["map_features"])["state"], "intact")
        s = advance(s, 4)  # B2, beside the bridge, saw it go; its runner reaches B1.
        known = bridge_feature(engine.view(s, "union")["map_features"])
        self.assertEqual((known["state"], known["observed_turn"]), ("destroyed", 1))
        self.assertEqual(bridge_feature(engine.view(s, "confederate")["map_features"])["state"], "intact")

    def test_delivery_estimate_uses_the_bridge_state_headquarters_knows(self):
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, schedule=((1, "destroyed"),)),),
                  units=(UnitEntry("B1", "union", "Company headquarters", (12, 16)),
                         UnitEntry("B2", "union", "Platoon across the canal", (12, 6)),
                         UnitEntry("G1", "confederate", "Guard", (20, 2), {"ammo": 0})))
        s = advance(s)
        # The true route is gone, but headquarters still believes the bridge stands.
        self.assertIsNotNone(order(s, "B2", "hold")["arrival_turn"])

    def test_registration_refuses_bad_bridge_data(self):
        cases = {
            "not on a bridge crossing": dataclasses.replace(CANAL_BRIDGE, pos=(3, 3)),
            "unknown state": dataclasses.replace(CANAL_BRIDGE, state="blown"),
            "schedule": dataclasses.replace(CANAL_BRIDGE, schedule=((3, "destroyed"), (2, "intact"))),
            "after destroyed": dataclasses.replace(CANAL_BRIDGE, schedule=((2, "destroyed"), (3, "intact"))),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, "bridge"):
                    dry_run(validate(night_entry(bridges=(bad,))))
        with self.assertRaisesRegex(ValueError, "bridge ids"):
            validate(night_entry(bridges=(CANAL_BRIDGE, CANAL_BRIDGE)))


class RadioAndVoiceTests(unittest.TestCase):
    """1944 company radio beside voice and runner, and the British 1944 voice."""

    UNITS = (UnitEntry("B1", "union", "Company headquarters", (12, 16)),
             UnitEntry("B2", "union", "Platoon in earshot", (12, 14)),
             UnitEntry("B3", "union", "Platoon across the canal", (12, 8)),
             UnitEntry("B4", "union", "Platoon far off", (0, 0)),
             UnitEntry("G1", "confederate", "Guard", (23, 20), {"ammo": 0}))

    def radio(self):
        return night(units=self.UNITS, communications=RADIO_COMMUNICATIONS, voice=WWII_VOICE_PROFILE)

    def test_order_within_radio_range_goes_by_radio_and_arrives_next_interval(self):
        s = self.radio()
        sent = order(s, "B3", "hold")
        self.assertEqual((sent["transport"]["method"], sent["arrival_turn"]), ("radio", 1))
        s = advance(s)
        self.assertEqual(next(e for e in events(s, "order_delivered") if e["order_id"] == sent["id"])["turn"], 1)

    def test_voice_and_runner_paths_remain(self):
        s = self.radio()
        self.assertEqual(order(s, "B2", "hold")["transport"]["method"], "voice")
        self.assertEqual(order(s, "B4", "hold")["transport"]["method"], "courier")
        self.assertEqual(order(s, "B1", "hold")["transport"]["method"], "voice")

    def test_unit_out_of_radio_range_at_delivery_gets_the_word_by_runner(self):
        s = self.radio()
        unit(s, "B3")["pos"] = [0, 2]  # Headquarters still places B3 within range.
        sent = order(s, "B3", "hold")
        self.assertEqual(sent["transport"]["method"], "radio")
        s = advance(s)
        self.assertEqual(events(s, "radio_out_of_range")[-1]["packet"]["recipient_id"], "B3")
        self.assertFalse([e for e in events(s, "order_delivered") if e["order_id"] == sent["id"]])

    def test_reports_from_units_within_radio_range_travel_by_radio(self):
        s = advance(self.radio())
        by_sender = {tuple(e["transport"]["origin"]): e["transport"]["method"]
                     for e in events(s, "report_sent") if e["report_kind"] == "friendly"}
        self.assertEqual(by_sender[(12, 8)], "radio")
        self.assertEqual(by_sender[(0, 0)], "courier")
        self.assertEqual(by_sender[(12, 16)], "voice")

    def test_1944_prompt_uses_the_british_voice_and_states_the_radio(self):
        prompt = command_policy.system_prompt("union", night_entry(communications=RADIO_COMMUNICATIONS, voice=WWII_VOICE_PROFILE))
        self.assertIn("June 1944", prompt)
        self.assertIn("Address the player as Major", prompt)
        self.assertNotIn("Address the player as General", prompt)
        self.assertIn("within 10 hexes of your command detachment by radio", prompt)

    def test_1944_order_and_staff_text_address_the_major(self):
        entry = night_entry(units=self.UNITS, communications=RADIO_COMMUNICATIONS, voice=WWII_VOICE_PROFILE)
        s = build_state(entry)
        order(s, "B3", "hold")
        order(s, "B4", "move", [1, 1])
        engine.message(s, "union", "General, the men are in position.")
        shown = present_view(engine.view(s, "union"), entry)["dispatches"]
        self.assertEqual([d.get("message_key") for d in shown[:2]], ["order.radioed", "order.carried"])
        self.assertIn("by wireless", shown[0]["display_text"])
        self.assertTrue(shown[2]["display_text"].startswith("Major, "))
        self.assertFalse(any("General" in d["display_text"] for d in shown))

    def test_scripted_order_text_addresses_the_major(self):
        from battle.adapters.openrouter import DisabledProvider
        from battle.adapters.rules import RulesSimulation, ScenarioRegistry
        from battle import scenario
        from battle.services.commander import CommanderService

        entry = night_entry(communications=RADIO_COMMUNICATIONS, voice=WWII_VOICE_PROFILE)
        commander = CommanderService(RulesSimulation(), DisabledProvider(),
                                     scenarios=ScenarioRegistry([scenario.LITTLE_ROUND_TOP, entry]))
        self.assertTrue(commander.decide(build_state(entry), "union", mode="scripted")["text"].startswith("Major"))


class SignalTests(unittest.TestCase):
    """A success codeword is a report with a sender, receiver and two turns."""

    def test_codeword_arrives_as_a_delivered_report_not_a_flag(self):
        s = night(bridges=(CANAL_BRIDGE,), signals=(HAM,))
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s)
        sent = events(s, "signal_sent")
        self.assertEqual([(e["codeword"], e["sender_id"], e["receiver_id"], e["sent_turn"]) for e in sent],
                         [("Ham", "B2", "B1", 1)])
        self.assertEqual(engine.view(s, "union")["signals"], [])  # Headquarters has not heard yet.
        s = advance(s, 6)
        [heard] = engine.view(s, "union")["signals"]
        self.assertEqual({k: heard[k] for k in ("codeword", "meaning", "sender_id", "receiver_id", "sent_turn")},
                         {"codeword": "Ham", "meaning": HAM.meaning, "sender_id": "B2", "receiver_id": "B1", "sent_turn": 1})
        self.assertGreater(heard["delivered_turn"], heard["sent_turn"])
        self.assertEqual(len(events(s, "signal_sent")), 1)  # Sent once.
        self.assertEqual(engine.view(s, "confederate")["signals"], [])

    def test_codeword_is_not_sent_while_an_enemy_is_near_or_the_bridge_is_down(self):
        s = night(bridges=(CANAL_BRIDGE,), signals=(HAM,),
                  units=DEFAULT_UNITS[:2] + (UnitEntry("G1", "confederate", "Guard", (12, 9), {"fire_posture": "hold_fire"}),))
        unit(s, "B2")["pos"] = list(BRIDGE)
        self.assertFalse(events(advance(s), "signal_sent"))
        s = night(bridges=(dataclasses.replace(CANAL_BRIDGE, state="destroyed"),), signals=(HAM,))
        unit(s, "B2")["pos"] = list(BRIDGE)
        self.assertFalse(events(advance(s), "signal_sent"))

    def test_codeword_dropped_by_a_disrupted_command_is_resent_and_arrives(self):
        s = night(bridges=(CANAL_BRIDGE,), signals=(HAM,))
        unit(s, "B2")["pos"] = list(BRIDGE)
        unit(s, "B1")["leaderless"] = True  # Command disrupted: no report can be received.
        s = advance(s, 6)
        lost = events(s, "signal_lost")
        self.assertEqual((lost[0]["codeword"], lost[0]["reason"], lost[0]["sent_turn"]), ("Ham", "command_disrupted", 1))
        self.assertGreater(len(events(s, "signal_sent")), 1)  # Re-sent while the bridge is still held.
        self.assertEqual(engine.view(s, "union")["signals"], [])
        unit(s, "B1").pop("leaderless")
        s = advance(s, 8)
        [heard] = engine.view(s, "union")["signals"]
        self.assertEqual((heard["codeword"], heard["sender_id"]), ("Ham", "B2"))
        self.assertGreater(heard["sent_turn"], 1)

    def test_codeword_whose_courier_expires_is_resent_and_arrives(self):
        s = night(bridges=(CANAL_BRIDGE,), signals=(HAM,))
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s)
        report = next(r for r in s["reports"] if r["kind"] == "signal")
        report["transport"]["expires_turn"] = s["turn"] + 1  # Fault injection: the runner is lost.
        s = advance(s)
        lost = events(s, "signal_lost")
        self.assertEqual((lost[0]["reason"], lost[0]["sent_turn"]), ("expired", 1))
        self.assertEqual([e["sent_turn"] for e in events(s, "signal_sent")], [1, 2])
        s = advance(s, 6)
        [heard] = engine.view(s, "union")["signals"]
        self.assertEqual((heard["codeword"], heard["sent_turn"]), ("Ham", 2))

    def test_registration_refuses_a_signal_for_an_unknown_bridge_or_side(self):
        for bad in (dataclasses.replace(HAM, bridge="orne-bridge"), dataclasses.replace(HAM, side="french"),
                    dataclasses.replace(HAM, condition="destroyed"), dataclasses.replace(HAM, radius=-1)):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "signal"):
                    validate(night_entry(bridges=(CANAL_BRIDGE,), signals=(bad,)))


def exchange(distance, observation_range=None, weapons=None, weapon_class="rifled muskets"):
    """B1 (open fire) ``distance`` hexes south of G1, which holds its fire and its ground."""
    units = (UnitEntry("B1", "union", "Blue", (5, 2 + distance), {"weapon_class": weapon_class}),
             UnitEntry("G1", "confederate", "Grey", (5, 2), {"fire_posture": "hold_fire", "weapon_class": weapon_class}))
    return advance(night(units=units, observation_range=observation_range, weapons=weapons))


def volleys(s):
    return [e for e in events(s, "volley") if e["unit_id"] == "B1"]


class DarknessTests(unittest.TestCase):
    """A night observation range limits fire and targeting, not only spotting."""

    def test_target_beyond_the_night_observation_range_is_not_fired_on(self):
        self.assertTrue(volleys(exchange(3)))  # Daylight: the rifle baseline reaches 3 hexes.
        night_run = exchange(3, observation_range=2)
        self.assertEqual(volleys(night_run), [])
        decision = [e for e in events(night_run, "local_decision") if e["unit_id"] == "B1"][-1]
        self.assertEqual(decision["contacts"], [])  # Targeting sees nothing either.

    def test_target_within_the_night_observation_range_is_fired_on(self):
        self.assertTrue(volleys(exchange(2, observation_range=2)))

    def test_observation_range_is_written_only_when_declared(self):
        s = night(observation_range=2, units=DEFAULT_UNITS[:2] + (
            UnitEntry("G1", "confederate", "Guard", (20, 2), {"ammo": 0, "observation_range": 3}),))
        self.assertEqual([u["observation_range"] for u in s["units"]], [2, 2, 3])
        self.assertFalse(any("observation_range" in u for u in night()["units"]))

    def test_registration_refuses_a_bad_observation_range(self):
        for bad in (0, 8, "2"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "observation_range"):
                    validate(night_entry(observation_range=bad))


class SingleRangeTests(unittest.TestCase):
    """One authored weapon range for every unit; a second range is refused."""

    def test_single_range_of_one_hex_fires_only_at_one_hex(self):
        table = {"rifles 1944": RIFLE_1944}
        self.assertEqual(volleys(exchange(2, weapons=table, weapon_class="rifles 1944")), [])
        self.assertTrue(volleys(exchange(1, weapons=table, weapon_class="rifles 1944")))

    def test_a_second_different_range_is_refused_at_validation(self):
        table = {"rifles 1944": RIFLE_1944, "machine guns 1944": WeaponEntry(2, 100, "assumption: test")}
        units = (UnitEntry("B1", "union", "Blue", (5, 4), {"weapon_class": "rifles 1944"}),
                 UnitEntry("G1", "confederate", "Grey", (5, 2), {"weapon_class": "machine guns 1944"}))
        with self.assertRaisesRegex(ValueError, r"single weapon range.*\[1, 2\]"):
            validate(night_entry(units=units, weapons=table))

    def test_a_unit_outside_the_table_is_a_second_range_and_is_refused(self):
        units = (UnitEntry("B1", "union", "Blue", (5, 4), {"weapon_class": "rifles 1944"}),
                 UnitEntry("G1", "confederate", "Grey", (5, 2)))
        with self.assertRaisesRegex(ValueError, "single weapon range.*G1"):
            validate(night_entry(units=units, weapons={"rifles 1944": RIFLE_1944}))

    def test_threat_range_still_uses_the_units_own_range(self):
        s = exchange(1, weapons={"rifles 1944": RIFLE_1944}, weapon_class="rifles 1944")
        self.assertEqual(tactics_v10.threat_range(s, unit(s, "B1")), 1)


class GatingTests(unittest.TestCase):
    """Nothing new is written for an entry that declares none of the keys."""

    def test_entry_without_the_1944_keys_writes_none_of_their_state(self):
        s = build_state(DUEL)
        self.assertNotIn("signals", s)
        self.assertNotIn("bridge_schedule", s)
        self.assertFalse(any("bridge_state" in c for c in s["cells"].values()))
        self.assertFalse(any(f.get("kind") == "bridge" for f in s["map_features"]))
        self.assertFalse(any("observation_range" in u for u in s["units"]))
        self.assertNotIn("signals", engine.view(s, "union"))


if __name__ == "__main__":
    unittest.main()
