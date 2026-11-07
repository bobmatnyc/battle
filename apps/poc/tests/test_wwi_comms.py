"""The 1918 voice-and-runner profile and the American 1918 voice (docs/research/59 §4).

Fixtures are the small synthetic entries of ``test_pegasus_engine`` on flat
ground; none is a historical scenario. B1 is union headquarters at (12, 16);
B2 stands 1 hex off, B3 2 hexes off and B4 far away.
"""

import dataclasses
import unittest

from battle import command_policy, comms, engine
from battle.presentation import VOICE_PROFILES, WWI_VOICE_PROFILE, present_view, scripted_text
from battle.scenario_command import WWI_COMMUNICATIONS
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_gateway_push import events
from test_pegasus_engine import advance, night, night_entry, order

UNITS = (UnitEntry("B1", "union", "Company post", (12, 16)),
         UnitEntry("B2", "union", "Party in earshot", (12, 15)),
         UnitEntry("B3", "union", "Party two hexes off", (12, 14)),
         UnitEntry("B4", "union", "Party far off", (0, 0)),
         UnitEntry("G1", "confederate", "Guard", (23, 20), {"ammo": 0}))


def wwi_entry(reach=1, **kw):
    return night_entry(units=UNITS, communications=WWI_COMMUNICATIONS, voice=WWI_VOICE_PROFILE,
                       voice_reach=reach, **kw)


def wwi(reach=1):
    return build_state(validate(wwi_entry(reach)))


class VoiceReachTests(unittest.TestCase):
    """Voice reach is the entry's; beyond it the word goes by runner."""

    def test_the_profile_has_voice_and_runner_and_no_radio(self):
        profile = comms.PROFILES[WWI_COMMUNICATIONS]
        self.assertEqual(profile["methods"], ["voice", "courier"])
        self.assertNotIn("radio_range", profile)
        self.assertNotIn("voice_reach", profile)

    def test_orders_within_the_entrys_reach_are_spoken_and_beyond_go_by_runner(self):
        s = wwi(reach=1)
        self.assertEqual(order(s, "B2", "hold")["transport"]["method"], "voice")
        self.assertEqual(order(s, "B3", "hold")["transport"]["method"], "courier")
        self.assertEqual(order(s, "B4", "hold")["transport"]["method"], "courier")

    def test_a_longer_declared_reach_speaks_farther(self):
        s = wwi(reach=2)
        self.assertEqual(order(s, "B3", "hold")["transport"]["method"], "voice")
        self.assertEqual(s["commanders"]["union"]["voice_reach"], 2)
        self.assertEqual(engine.view(s, "union")["command"]["voice_reach"], 2)

    def test_reach_zero_speaks_only_to_the_command_detachment(self):
        s = wwi(reach=0)
        self.assertEqual(order(s, "B1", "hold")["transport"]["method"], "voice")
        self.assertEqual(order(s, "B2", "hold")["transport"]["method"], "courier")

    def test_a_spoken_order_arrives_next_interval(self):
        s = wwi(reach=1)
        sent = order(s, "B2", "hold")
        s = advance(s)
        self.assertEqual(next(e for e in events(s, "order_delivered") if e["order_id"] == sent["id"])["turn"], 1)

    def test_reports_never_go_by_radio(self):
        s = advance(wwi(reach=1))
        methods = {e["transport"]["method"] for e in events(s, "report_sent")}
        self.assertNotIn("radio", methods)

    def test_other_profiles_write_no_reach(self):
        s = night(units=UNITS)
        self.assertNotIn("voice_reach", s["commanders"]["union"])


class VoiceReachValidationTests(unittest.TestCase):
    """The profile needs a reach from the entry; no other profile takes one."""

    def test_the_profile_refuses_a_missing_or_bad_reach(self):
        for bad in (None, -1, 1.5, True, "1"):
            with self.subTest(reach=bad):
                with self.assertRaisesRegex(ValueError, "voice_reach"):
                    validate(wwi_entry(bad))

    def test_other_profiles_refuse_a_reach(self):
        for profile in ("civil-war-courier-v1", "colonial-1775-voice-v1", "wwii-1944-radio-v1"):
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(ValueError, "voice_reach"):
                    validate(night_entry(units=UNITS, communications=profile, voice_reach=1))

    def test_an_edition_before_poc_13_refuses_the_profile(self):
        entry = dataclasses.replace(DUEL, communications=WWI_COMMUNICATIONS, voice_reach=1)
        with self.assertRaisesRegex(ValueError, "voice reach"):
            build_state(entry, rules="poc-12")


class AmericanVoiceTests(unittest.TestCase):
    """The 1918 American voice: authored wording, display only."""

    def test_prompt_states_the_period_voice_and_the_declared_reach(self):
        prompt = command_policy.system_prompt("union", wwi_entry(reach=1))
        self.assertIn("American Expeditionary Forces in France in 1918", prompt)
        self.assertIn("Address the player as Sir", prompt)
        self.assertNotIn("Address the player as General", prompt)
        self.assertIn("within 1 hexes of your command detachment by voice", prompt)
        self.assertIn("radio", VOICE_PROFILES[WWI_VOICE_PROFILE])  # It names radio only to rule it out.

    def test_order_staff_and_prisoner_text_in_the_1918_voice(self):
        entry = wwi_entry(reach=1)
        s = build_state(entry)
        order(s, "B2", "hold")
        order(s, "B4", "move", [1, 1])
        engine.message(s, "union", "General, the men are in position.")
        engine.message(s, "union", "B2: 75 prisoners taken from D1.", kind="captives")
        shown = present_view(engine.view(s, "union"), entry)["dispatches"]
        self.assertEqual([d.get("message_key") for d in shown],
                         ["order.spoken", "order.carried", None, "captives.taken"])
        self.assertIn("by word of mouth", shown[0]["display_text"])
        self.assertIn("Sent by runner", shown[1]["display_text"])
        self.assertTrue(shown[2]["display_text"].startswith("Sir, "))
        self.assertEqual(shown[3]["display_text"], "B2 to headquarters: We have taken 75 prisoners from D1.")
        self.assertFalse(any("General" in d["display_text"] for d in shown))
        self.assertEqual([d["text"] for d in shown][3], "B2: 75 prisoners taken from D1.")  # Stored text unchanged.

    def test_scripted_text_in_the_1918_voice(self):
        self.assertTrue(scripted_text(WWI_VOICE_PROFILE).startswith("Sir, "))


if __name__ == "__main__":
    unittest.main()
