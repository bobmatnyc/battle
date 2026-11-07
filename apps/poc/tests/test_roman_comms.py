"""The Roman signal profile and the Roman voice (docs/research/60 §4).

Fixtures are the small synthetic entries of ``test_pegasus_engine`` on flat
ground; none is a historical scenario. B1 is union headquarters at (12, 16);
B2 stands 1 hex off and B3 far away.
"""

import dataclasses
import unittest

from battle import command_policy, comms, engine
from battle.presentation import ROMAN_VOICE_PROFILE, VOICE_PROFILES, present_view, scripted_text
from battle.scenario_command import ROMAN_COMMUNICATIONS
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_pegasus_engine import night_entry, order

UNITS = (UnitEntry("B1", "union", "Command group", (12, 16)),
         UnitEntry("B2", "union", "Group in earshot", (12, 15)),
         UnitEntry("B3", "union", "Group far off", (0, 0)),
         UnitEntry("G1", "confederate", "Guard", (23, 20), {"ammo": 0}))


def roman_entry(reach=1, **kw):
    return night_entry(units=UNITS, communications=ROMAN_COMMUNICATIONS, voice=ROMAN_VOICE_PROFILE,
                       voice_reach=reach, **kw)


class RomanProfileTests(unittest.TestCase):
    """Signal, voice and runner; the voice reach is the entry's."""

    def test_the_profile_has_signal_voice_and_runner_and_no_radio(self):
        profile = comms.PROFILES[ROMAN_COMMUNICATIONS]
        self.assertEqual(profile["methods"], ["signal", "voice", "courier"])
        self.assertNotIn("radio_range", profile)
        self.assertNotIn("voice_reach", profile)

    def test_orders_within_the_entrys_reach_are_spoken_and_beyond_go_by_runner(self):
        s = build_state(validate(roman_entry(reach=1)))
        self.assertEqual(s["commanders"]["union"]["voice_reach"], 1)
        self.assertEqual(order(s, "B2", "hold")["transport"]["method"], "voice")
        self.assertEqual(order(s, "B3", "hold")["transport"]["method"], "courier")

    def test_the_profile_refuses_a_missing_reach(self):
        with self.assertRaisesRegex(ValueError, "voice_reach"):
            validate(roman_entry(reach=None))

    def test_an_edition_before_poc_13_refuses_the_profile(self):
        entry = dataclasses.replace(DUEL, communications=ROMAN_COMMUNICATIONS, voice_reach=1)
        with self.assertRaisesRegex(ValueError, "voice reach"):
            build_state(entry, rules="poc-12")


class RomanVoiceTests(unittest.TestCase):
    """The Roman voice: authored wording, display only."""

    def test_prompt_states_the_period_voice_the_reach_and_the_signals(self):
        prompt = command_policy.system_prompt("union", roman_entry(reach=1))
        self.assertIn("Roman army of the late Republic", prompt)
        self.assertIn("Address the player as Imperator", prompt)
        self.assertNotIn("Address the player as General", prompt)
        self.assertIn("within 1 hexes of your command detachment by voice", prompt)
        self.assertIn("A trumpet signal", prompt)
        self.assertIn("radio", VOICE_PROFILES[ROMAN_VOICE_PROFILE])  # Named only to rule it out.

    def test_order_and_staff_text_in_the_roman_voice(self):
        entry = roman_entry(reach=1)
        s = build_state(entry)
        order(s, "B2", "hold")
        order(s, "B3", "move", [1, 1])
        engine.message(s, "union", "General, the cohorts are in position.")
        engine.message(s, "union", "B1: signal recall sounded. Recall.", kind="broadcast")
        shown = present_view(engine.view(s, "union"), entry)["dispatches"]
        self.assertEqual([d.get("message_key") for d in shown],
                         ["order.spoken", "order.carried", None, "signal.sounded"])
        self.assertIn("by word of mouth", shown[0]["display_text"])
        self.assertIn("A runner carries the word", shown[1]["display_text"])
        self.assertTrue(shown[2]["display_text"].startswith("Imperator, "))
        self.assertEqual(shown[3]["display_text"], "The trumpets sound from B1: Recall.")
        self.assertFalse(any("General" in d["display_text"] for d in shown))
        self.assertEqual(shown[3]["text"], "B1: signal recall sounded. Recall.")  # Stored text unchanged.

    def test_scripted_text_in_the_roman_voice(self):
        self.assertTrue(scripted_text(ROMAN_VOICE_PROFILE).startswith("Imperator, "))


if __name__ == "__main__":
    unittest.main()
