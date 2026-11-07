"""Broadcast signals with audibility (docs/research/60 §1).

Fixtures are the small synthetic entries of ``test_pegasus_engine`` on flat
ground (a canal on row 10); none is a historical scenario and every value is
authored for the test. B1 is union headquarters at (12, 16) and sounds the
signal; B2 stands 3 hexes off, B3 5 hexes off and B4 far away. G1 is far
off across the canal with no ammunition, so no contact or fire decides.
"""

import dataclasses
import json
import unittest

from battle import engine, grid, runtime
from battle.engine_v2 import InvalidOrder
from battle.presentation import ROMAN_VOICE_PROFILE
from battle.scenario_broadcast import BroadcastEntry
from battle.scenario_command import ROMAN_COMMUNICATIONS
from battle.scenario_entry import UnitEntry, build_state, dry_run, validate
from scenario_fixtures import DUEL
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night_entry

RALLY = (12, 19)
UNITS = (UnitEntry("B1", "union", "Command group", (12, 16)),
         UnitEntry("B2", "union", "Group in earshot", (12, 13)),
         UnitEntry("B3", "union", "Group beyond earshot", (12, 11)),
         UnitEntry("B4", "union", "Group far off", (0, 20)),
         UnitEntry("G1", "confederate", "Guard", (20, 2), {"ammo": 0}))
RECALL = BroadcastEntry(id="recall", side="union", kind="recall", reach=4, stance="retreat",
                        destination=RALLY, turn=2, meaning="Recall: fall back to the reserve line.")


def signal_entry(*signals, units=UNITS, communications=ROMAN_COMMUNICATIONS, **kw):
    return night_entry(units=units, communications=communications, voice=ROMAN_VOICE_PROFILE,
                       voice_reach=1, broadcasts=signals or (RECALL,), **kw)


def signal_state(*signals, **kw):
    return build_state(dry_run(validate(signal_entry(*signals, **kw))))


def without_signal():
    return build_state(validate(dataclasses.replace(signal_entry(), broadcasts=None)))


def receipts(s):
    return s["broadcasts"][0]["receipts"]


def between(a, b):
    """A hex strictly between ``a`` and ``b`` on the grid line."""
    return tuple(grid.line(list(a), list(b))[1])


class AudibilityTests(unittest.TestCase):
    """A sounded signal reaches every unit of its side in reach and not blocked."""

    def test_units_in_reach_hear_and_units_beyond_do_not(self):
        s = advance(signal_state(), 2)
        self.assertEqual(s["broadcasts"][0]["sounded_turn"], 2)
        self.assertEqual(s["broadcasts"][0]["sounder_id"], "B1")
        got = {uid: (r["heard"], r["turn"]) for uid, r in receipts(s).items()}
        self.assertEqual(got, {"B2": (True, 2), "B3": (False, 2), "B4": (False, 2)})
        self.assertEqual(receipts(s)["B3"]["reason"], "out_of_reach")
        self.assertEqual([e["unit_id"] for e in events(s, "signal_heard")], ["B2"])
        self.assertEqual([e["unit_id"] for e in events(s, "signal_not_heard")], ["B3", "B4"])
        self.assertEqual([e["turn"] for e in events(s, "signal_sounded")], [2])

    def test_nothing_is_sounded_before_the_declared_turn(self):
        s = advance(signal_state(), 1)
        self.assertIsNone(s["broadcasts"][0]["sounded_turn"])
        self.assertEqual(receipts(s), {})

    def test_a_declared_block_on_the_line_stops_the_sound(self):
        block = between((12, 16), (12, 13))
        s = advance(signal_state(dataclasses.replace(RECALL, block_hexes=(block,))), 2)
        self.assertEqual((receipts(s)["B2"]["heard"], receipts(s)["B2"]["reason"]), (False, "blocked"))

    def test_a_block_off_the_line_does_not(self):
        s = advance(signal_state(dataclasses.replace(RECALL, block_hexes=((3, 18),))), 2)
        self.assertTrue(receipts(s)["B2"]["heard"])

    def test_a_unit_that_hears_takes_up_the_signal_and_one_that_does_not_keeps_its_mission(self):
        s = advance(signal_state(), 2)
        self.assertEqual((unit(s, "B2")["stance"], unit(s, "B2")["target"]), ("retreat", list(RALLY)))
        self.assertEqual(unit(s, "B2")["heard_signals"], ["recall"])
        self.assertEqual(unit(s, "B2")["mission_result"]["template"], "retreat")
        self.assertEqual((unit(s, "B3")["stance"], unit(s, "B3")["target"]), ("hold", None))
        self.assertNotIn("heard_signals", unit(s, "B3"))

    def test_an_unheard_signal_does_not_change_the_units_decision(self):
        """Two states differ only in a signal B3 cannot hear; B3 decides alike in both."""
        with_signal, plain = signal_state(), without_signal()
        for s in (with_signal, plain):
            engine.find_unit(s, "B3").update(target=[5, 12], stance="move")
        with_signal, plain = advance(with_signal, 4), advance(plain, 4)
        self.assertFalse(receipts(with_signal)["B3"]["heard"])
        own = lambda s: {k: v for k, v in unit(s, "B3").items() if k != "local_decision_seq"}  # An event index.
        self.assertEqual(own(with_signal), own(plain))
        heard = [e for e in events(with_signal, "local_decision") if e["unit_id"] == "B3"]
        plain_decisions = [e for e in events(plain, "local_decision") if e["unit_id"] == "B3"]
        strip = lambda es: [{k: v for k, v in e.items() if k != "seq"} for e in es]
        self.assertEqual(strip(heard), strip(plain_decisions))

    def test_the_same_unit_in_reach_does_change_its_decision(self):
        s = signal_state()
        engine.find_unit(s, "B3").update(pos=[12, 14], target=[5, 12], stance="move")
        s = advance(s, 2)
        self.assertEqual(unit(s, "B3")["stance"], "retreat")

    def test_a_routed_unit_hears_but_does_not_obey(self):
        s = advance(signal_state(), 1)
        unit(s, "B2")["status"] = "routed"
        s = advance(s, 1)
        self.assertEqual((receipts(s)["B2"]["heard"], receipts(s)["B2"]["obeyed"]), (True, False))
        self.assertNotEqual(unit(s, "B2")["stance"], "retreat")

    def test_the_signal_is_not_an_addressed_packet(self):
        s = advance(signal_state(), 2)
        self.assertEqual(s["orders"], [])
        self.assertEqual([e for e in events(s, "order_sent")], [])
        self.assertFalse(any((r.get("data") or {}).get("signal_id") for r in s["reports"]))

    def test_a_disrupted_command_does_not_sound_the_signal(self):
        s = advance(signal_state(), 1)
        unit(s, "B1")["status"] = "routed"
        s = advance(s, 1)
        self.assertIsNone(s["broadcasts"][0]["sounded_turn"])
        self.assertEqual(receipts(s), {})

    def test_runs_are_deterministic(self):
        self.assertEqual(advance(signal_state(), 4), advance(signal_state(), 4))


class OrderedSignalTests(unittest.TestCase):
    """A signal declared without a turn is sounded by the commander's order."""

    ORDERED = dataclasses.replace(RECALL, turn=None)

    def test_ordered_signal_sounds_at_the_next_interval(self):
        s = advance(signal_state(self.ORDERED), 1)
        s = runtime.apply(s, {"type": "signal", "signal_id": "recall"})
        self.assertEqual(s["broadcasts"][0]["ordered_turn"], 1)
        self.assertIsNone(s["broadcasts"][0]["sounded_turn"])
        s = advance(s, 1)
        self.assertEqual(s["broadcasts"][0]["sounded_turn"], 2)
        self.assertTrue(receipts(s)["B2"]["heard"])

    def test_an_unordered_signal_is_never_sounded(self):
        s = advance(signal_state(self.ORDERED), 5)
        self.assertIsNone(s["broadcasts"][0]["sounded_turn"])

    def test_orders_the_rules_cannot_follow_are_refused(self):
        s = signal_state(self.ORDERED, dataclasses.replace(RECALL, id="timed"))
        for signal_id in ("unknown", "timed"):
            with self.subTest(signal_id=signal_id):
                with self.assertRaises(InvalidOrder):
                    runtime.apply(s, {"type": "signal", "signal_id": signal_id})
        s = runtime.apply(s, {"type": "signal", "signal_id": "recall"})
        with self.assertRaises(InvalidOrder):
            runtime.apply(s, {"type": "signal", "signal_id": "recall"})


class SignalViewTests(unittest.TestCase):
    """Headquarters knows what it sounded, never who heard it."""

    def test_the_view_shows_the_sounding_but_no_receipt(self):
        s = advance(signal_state(), 2)
        shown = engine.view(s, "union")["broadcasts"]
        self.assertEqual([(b["id"], b["sounded_turn"]) for b in shown], [("recall", 2)])
        self.assertNotIn("receipts", json.dumps(engine.view(s, "union")))
        self.assertEqual(engine.view(s, "confederate")["broadcasts"], [])
        self.assertIn("receipts", json.dumps(engine.god_view(s)["broadcasts"]))

    def test_a_battle_without_signals_writes_nothing(self):
        s = advance(build_state(validate(night_entry(units=UNITS))), 2)
        self.assertNotIn("broadcasts", s)
        self.assertNotIn("broadcasts", engine.view(s, "union"))


class SignalValidationTests(unittest.TestCase):
    """Registration refuses a signal the rules cannot sound."""

    def test_registration_refuses_bad_signals(self):
        for fields in ({"id": ""}, {"side": "nobody"}, {"kind": "advance"}, {"reach": 0}, {"reach": 1.5},
                       {"reach": True}, {"stance": "move"}, {"destination": None}, {"destination": (99, 1)},
                       {"stance": "hold"}, {"turn": 0}, {"turn": 61}, {"block_hexes": ((99, 1),)},
                       {"meaning": ""}, {"basis": ""}):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, "broadcast"):
                    validate(signal_entry(dataclasses.replace(RECALL, **fields)))

    def test_a_hold_signal_needs_no_destination(self):
        validate(signal_entry(dataclasses.replace(RECALL, stance="hold", destination=None)))

    def test_signal_ids_are_unique(self):
        with self.assertRaisesRegex(ValueError, "broadcast"):
            validate(signal_entry(RECALL, RECALL))

    def test_a_profile_without_signals_refuses_them(self):
        with self.assertRaisesRegex(ValueError, "broadcast"):
            validate(dataclasses.replace(signal_entry(), communications="civil-war-courier-v1", voice_reach=None))

    def test_an_edition_before_poc_13_refuses_signals(self):
        entry = dataclasses.replace(DUEL, broadcasts=(RECALL,))
        with self.assertRaisesRegex(ValueError, "poc-12 has no .*broadcast"):
            build_state(entry, rules="poc-12")


if __name__ == "__main__":
    unittest.main()
