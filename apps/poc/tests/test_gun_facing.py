"""Gun facing and a reorientation delay (docs/research/59 §2).

Fixtures are the small synthetic 1944 entries of ``test_pegasus_engine`` on
flat ground north of its canal; none is a historical scenario. G1, a gun
group at (12, 4), may face south (180 degrees) with a 90-degree arc; B1
stands 4 hexes due north of it, in its rear, or 4 hexes due south, in front.
B1 holds its fire and has no ammunition, so only G1's fire decides.
"""

import dataclasses
import unittest

from battle import engine, facing, formations
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_formations import SPLIT, fixture as formation_fixture
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night, night_entry

GUN = (12, 4)
NORTH = (12, 0)  # Bearing 0 from GUN: the rear of a south-facing gun.
SOUTH = (12, 8)  # Bearing 180 from GUN: its front.
SOUTHWARD = {"facing": 180, "arc": 90, "reorient_turns": 2}
QUIET = {"fire_posture": "hold_fire", "ammo": 0}


def gun_units(b1=NORTH, **gun):
    return (UnitEntry("B1", "union", "Patrol", b1, QUIET),
            UnitEntry("G1", "confederate", "Gun group", GUN, gun))


def gun_state(b1=NORTH, **gun):
    return night(units=gun_units(b1, **gun))


def volley_turns(s):
    return [e["turn"] for e in events(s, "volley") if e["unit_id"] == "G1"]


class BearingTests(unittest.TestCase):
    """Bearings are whole degrees clockwise from map north (up the map)."""

    def test_bearings_and_arcs(self):
        self.assertEqual(facing.bearing(GUN, NORTH), 0)
        self.assertEqual(facing.bearing(GUN, SOUTH), 180)
        self.assertEqual(facing.bearing(GUN, (16, 4)), 90)
        self.assertEqual(facing.bearing(GUN, (8, 4)), 270)
        gun = {"pos": list(GUN), **SOUTHWARD}
        self.assertTrue(facing.within(gun, SOUTH))
        self.assertFalse(facing.within(gun, NORTH))
        self.assertFalse(facing.within(gun, (16, 4)))  # 90 degrees off a 90-degree arc's centre.


class FacingFireTests(unittest.TestCase):
    """``engine.volley`` with and without a declared facing."""

    def test_an_undeclared_gun_fires_at_an_enemy_on_any_side(self):
        s = advance(gun_state(), 1)
        self.assertNotIn("facing", unit(s, "G1"))
        self.assertEqual(volley_turns(s), [1])
        self.assertEqual(events(s, "gun_reorienting"), [])

    def test_a_declared_gun_fires_inside_its_arc_at_once(self):
        s = advance(gun_state(b1=SOUTH, **SOUTHWARD), 1)
        self.assertEqual(volley_turns(s), [1])
        self.assertEqual(unit(s, "G1")["facing"], 180)

    def test_a_gun_turns_for_its_delay_before_firing_into_its_rear(self):
        s = advance(gun_state(**SOUTHWARD), 3)
        turning = events(s, "gun_reorienting")
        self.assertEqual([(e["turn"], e["from_facing"], e["bearing"], e["ready_turn"]) for e in turning],
                         [(1, 180, 0, 3)])
        self.assertEqual([(e["turn"], e["facing"]) for e in events(s, "gun_reoriented")], [(3, 0)])
        self.assertEqual(volley_turns(s), [3])
        self.assertEqual(unit(s, "G1")["facing"], 0)
        self.assertNotIn("reorienting", unit(s, "G1"))

    def test_a_zero_delay_turns_and_fires_in_the_same_interval(self):
        s = advance(gun_state(**{**SOUTHWARD, "reorient_turns": 0}), 1)
        self.assertEqual(volley_turns(s), [1])
        self.assertEqual(unit(s, "G1")["facing"], 0)

    def test_a_turned_gun_no_longer_covers_its_old_front(self):
        s = gun_state(b1=SOUTH, **{**SOUTHWARD, "facing": 0})
        self.assertFalse(facing.within(unit(s, "G1"), SOUTH))
        self.assertEqual(volley_turns(advance(s, 1)), [])

    def test_an_enemy_the_gun_cannot_see_does_not_start_a_turn(self):
        # Sight 3: B1, 4 hexes off in the rear, is not seen, so the gun stays put.
        s = advance(night(units=gun_units(**SOUTHWARD), observation_range=3), 2)
        self.assertEqual(events(s, "gun_reorienting"), [])
        self.assertEqual(unit(s, "G1")["facing"], 180)


class HeldGunTests(unittest.TestCase):
    """A gun holding its fire still turns toward a rear party it sees; turning
    never fires and never releases it. B1 fires on G1 only when ``b1_fires``."""

    def held(self, b1_fires=False):
        b1 = {"fire_posture": "hold_fire", "ammo": 0} if not b1_fires else {}
        units = (UnitEntry("B1", "union", "Patrol", NORTH, b1),
                 UnitEntry("G1", "confederate", "Gun group", GUN, {**SOUTHWARD, "fire_posture": "hold_fire"}))
        return night(units=units)

    def test_a_held_gun_turns_while_holding_its_fire(self):
        s = advance(self.held(), 3)
        self.assertEqual([(e["turn"], e["ready_turn"]) for e in events(s, "gun_reorienting")], [(1, 3)])
        self.assertEqual([e["turn"] for e in events(s, "gun_reoriented")], [3])
        self.assertEqual(unit(s, "G1")["facing"], 0)
        self.assertEqual(unit(s, "G1")["fire_posture"], "hold_fire")
        self.assertEqual(volley_turns(s), [])

    def test_a_held_gun_released_after_the_delay_fires_at_once(self):
        s = advance(self.held(), 3)  # Turned at turn 3, still holding.
        engine.find_unit(s, "B1").update(fire_posture="open_fire", ammo=1600)
        s = advance(s, 2)  # B1 fires at turn 4; G1 returns fire that interval.
        first = min(e["turn"] for e in events(s, "volley") if e["unit_id"] == "B1")
        self.assertEqual(first, 4)
        self.assertIn(first, volley_turns(s))
        self.assertEqual([e["turn"] for e in events(s, "gun_reorienting")], [1])

    def test_a_held_gun_does_not_fire_before_release(self):
        s = advance(self.held(), 6)
        self.assertEqual(volley_turns(s), [])


class FacingValidationTests(unittest.TestCase):
    """Registration refuses a facing the rules cannot use."""

    def test_registration_refuses_bad_facing_values(self):
        for bad in ({"facing": 360}, {"facing": -1}, {"arc": 0}, {"arc": 360}, {"reorient_turns": -1},
                    {"facing": 1.5}, {"arc": True}, {"reorient_turns": "2"}):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "facing"):
                    validate(night_entry(units=gun_units(**{**SOUTHWARD, **bad})))

    def test_the_three_keys_are_declared_together(self):
        for missing in SOUTHWARD:
            with self.subTest(missing=missing):
                partial = {k: v for k, v in SOUTHWARD.items() if k != missing}
                with self.assertRaisesRegex(ValueError, "facing, arc and reorient_turns"):
                    validate(night_entry(units=gun_units(**partial)))

    def test_an_edition_before_poc_13_refuses_a_facing(self):
        units = (dataclasses.replace(DUEL.units[0], overrides=dict(SOUTHWARD)),) + DUEL.units[1:]
        with self.assertRaisesRegex(ValueError, "facing"):
            build_state(dataclasses.replace(DUEL, units=units), rules="poc-12")

    def test_a_facing_unit_neither_splits_nor_combines(self):
        s = formation_fixture()
        engine.find_unit(s, "U1").update(SOUTHWARD)
        with self.assertRaisesRegex(ValueError, "facing"):
            formations.request(s, "union", SPLIT)


if __name__ == "__main__":
    unittest.main()
