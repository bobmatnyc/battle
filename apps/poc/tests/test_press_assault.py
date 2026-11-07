"""A declared assault in open ground under tactics_v11 (docs/research/58 §2).

Fixtures are the mixed-range duel of ``test_tactics_v11`` on flat ground:
B1 (1-hex short rifles) stands 3 hexes south of G1 (3-hex machine guns,
holding fire). G1's weapon is not established, so it counts at the table's
longest range (3) and B1 halts for it unless it presses the assault.
None is a historical scenario.
"""

import dataclasses
import unittest

from battle import engine, grid, tactics_v11
from battle.scenario_command import TACTICS_V11
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night_entry, order
from test_tactics_v11 import LONG, MIXED, REACTIONS, duel, sightings

PRESS = {"press_assault": True}
TOWARD_G1 = [5, 3]  # The hex next to G1 on B1's side.


def pressing_duel(declared=True, extra=(), **kw):
    """The duel with B1 on a move order toward G1; ``declared`` gives B1 the key."""
    b1 = UnitEntry("B1", "union", "Blue", (5, 5), {"weapon_class": "short rifles", **(PRESS if declared else {})})
    g1 = UnitEntry("G1", "confederate", "Grey", (5, 2), {"fire_posture": "hold_fire", "weapon_class": "machine guns"})
    s = build_state(validate(night_entry(units=(b1, g1, *extra), weapons=MIXED, tactics=TACTICS_V11, **kw)))
    unit(s, "B1").update(stance="move", target=list(TOWARD_G1))
    return s


class PressDecisionTests(unittest.TestCase):
    """The local decision of a unit on a move order that sees an unidentified contact."""

    def test_without_the_key_the_unit_halts_as_today(self):
        s = pressing_duel(declared=False)
        self.assertNotIn("press_assault", unit(s, "B1"))
        self.assertIn(tactics_v11.decide(s, unit(s, "B1"), sightings(s))["action"], REACTIONS)

    def test_with_the_key_the_unit_presses_toward_its_objective(self):
        s = pressing_duel()
        decision = tactics_v11.decide(s, unit(s, "B1"), sightings(s))
        self.assertEqual(decision["action"], "continue")
        self.assertIn("pressing the assault", decision["reason"])

    def test_the_key_needs_a_move_order(self):
        s = pressing_duel()
        unit(s, "B1").update(stance="hold", target=None)
        self.assertIn(tactics_v11.decide(s, unit(s, "B1"), sightings(s))["action"], REACTIONS)

    def test_a_pressing_unit_still_withdraws_on_failing_morale(self):
        s = pressing_duel()
        unit(s, "B1")["morale"] = 10
        decision = tactics_v11.decide(s, unit(s, "B1"), sightings(s))
        self.assertEqual(decision["action"], "withdraw")
        self.assertIn("morale is failing", decision["reason"])

    def test_a_routed_pressing_unit_falls_back(self):
        s = pressing_duel()
        unit(s, "B1")["status"] = "routed"
        self.assertEqual(tactics_v11.decide(s, unit(s, "B1"), sightings(s))["action"], "route")

    def test_a_hidden_enemy_does_not_change_the_decision(self):
        # G2, a much stronger force, stands 9 hexes off, beyond B1's sight (7).
        hidden = UnitEntry("G2", "confederate", "Hidden column", (5, 14),
                           {"strength": 80, "initial": 80, "fire_posture": "hold_fire",
                            "weapon_class": "machine guns"})
        alone, with_hidden = pressing_duel(), pressing_duel(extra=(hidden,))
        seen_alone, seen_with = sightings(alone), sightings(with_hidden)
        self.assertNotIn("G2", [c["id"] for c in seen_with])
        first = tactics_v11.decide(alone, unit(alone, "B1"), seen_alone)
        second = tactics_v11.decide(with_hidden, unit(with_hidden, "B1"), seen_with)
        self.assertEqual(first, second)
        self.assertEqual(first["action"], "continue")


class PressEngineTests(unittest.TestCase):
    """Through the engine, from a delivered move order."""

    def run_toward_g1(self, declared):
        s = pressing_duel(declared=declared)
        unit(s, "B1").update(stance="hold", target=None)
        order(s, "B1", destination=list(TOWARD_G1))
        return advance(s, 3)  # Long enough to close; losses later make both withdraw.

    def test_with_the_key_the_unit_closes_to_contact_and_engages(self):
        s = self.run_toward_g1(declared=True)
        self.assertEqual(grid.distance(unit(s, "B1")["pos"], unit(s, "G1")["pos"]), 1)
        self.assertTrue([e for e in events(s, "volley") if e["unit_id"] == "B1"])

    def test_without_the_key_the_unit_halts_at_the_first_unidentified_contact(self):
        s = self.run_toward_g1(declared=False)
        self.assertGreater(grid.distance(unit(s, "B1")["pos"], unit(s, "G1")["pos"]), 1)
        self.assertFalse([e for e in events(s, "volley") if e["unit_id"] == "B1"])


class PressValidationTests(unittest.TestCase):
    """Only a tactics_v11 entry may declare the key, and only as a boolean."""

    UNITS = (UnitEntry("B1", "union", "Blue", (5, 5), {"weapon_class": "machine guns", **PRESS}),
             UnitEntry("G1", "confederate", "Grey", (5, 2), {"weapon_class": "machine guns"}))

    def test_refused_on_a_tactics_v10_entry(self):
        with self.assertRaisesRegex(ValueError, "press_assault"):
            validate(night_entry(units=self.UNITS, weapons={"machine guns": LONG}))

    def test_refused_unless_a_boolean(self):
        units = (dataclasses.replace(self.UNITS[0], overrides={"weapon_class": "machine guns", "press_assault": "yes"}),) + self.UNITS[1:]
        with self.assertRaisesRegex(ValueError, "press_assault"):
            validate(night_entry(units=units, weapons=MIXED, tactics=TACTICS_V11))

    def test_an_edition_before_poc_13_refuses_the_key(self):
        units = (dataclasses.replace(DUEL.units[0], overrides=PRESS),) + DUEL.units[1:]
        with self.assertRaisesRegex(ValueError, "press_assault"):
            build_state(dataclasses.replace(DUEL, units=units), rules="poc-12")

    def test_an_undeclared_tactics_v11_snapshot_carries_no_key(self):
        self.assertFalse(any("press_assault" in u for u in duel()["units"]))


if __name__ == "__main__":
    unittest.main()
