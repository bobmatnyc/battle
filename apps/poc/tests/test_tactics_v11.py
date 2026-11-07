"""tactics_v11: the local threat check reads the range of the enemy a unit
observes, not only its own (docs/research/55).

Fixtures are the small synthetic 1944 entries of ``test_pegasus_engine`` on
flat ground; none is a historical scenario. B1 stands 3 hexes south of G1,
which holds its fire, so neither side is under fire and only the threat
check decides.
"""

import dataclasses
import unittest
from copy import deepcopy

from battle import recon, tactics_v10, tactics_v11
from battle.scenario_command import TACTICS_V11, WeaponEntry
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night, night_entry

SHORT = WeaponEntry(1, 100, "assumption: test value")
MEDIUM = WeaponEntry(2, 100, "assumption: test value")
LONG = WeaponEntry(3, 100, "assumption: test value")
MIXED = {"short rifles": SHORT, "carbines": MEDIUM, "machine guns": LONG}
REACTIONS = ("defend", "take_cover", "withdraw")


def duel(b1="short rifles", g1="machine guns", extra=(), tactics=TACTICS_V11, weapons=MIXED):
    """B1 (``b1``) at 3 hexes from G1 (``g1``, holding fire); ``extra`` adds units."""
    units = (UnitEntry("B1", "union", "Blue", (5, 5), {"weapon_class": b1}),
             UnitEntry("G1", "confederate", "Grey", (5, 2), {"fire_posture": "hold_fire", "weapon_class": g1}),
             *extra)
    return night(units=units, weapons=weapons, tactics=tactics)


def sightings(s, identify=None):
    """B1's contacts this interval; ``identify`` names the class B1 has made
    out for G1, as ``recon.estimate`` does at high quality within 2 hexes."""
    contacts = deepcopy(recon.scan(s)["B1"])
    for c in contacts:
        if identify and c["id"] == "G1":
            c["composition"]["weapons"] = identify
    return contacts


class ThreatRangeTests(unittest.TestCase):
    """The distance at which an observed contact makes a unit halt and react."""

    def test_a_short_range_unit_uses_an_identified_enemys_longer_range(self):
        s = duel()
        contacts = sightings(s, identify="machine guns")
        self.assertEqual(tactics_v11.threat_range(s, unit(s, "B1"), contacts), 3)
        self.assertEqual(tactics_v10.threat_range(s, unit(s, "B1")), 1)

    def test_a_short_range_unit_halts_for_a_longer_range_enemy_it_sees(self):
        s = duel()
        contacts = sightings(s, identify="machine guns")
        self.assertIn(tactics_v11.decide(s, unit(s, "B1"), contacts)["action"], REACTIONS)
        self.assertEqual(tactics_v10.decide(s, unit(s, "B1"), contacts)["action"], "observe")

    def test_an_unidentified_contact_counts_at_the_longest_range_in_the_table(self):
        s = duel(g1="short rifles")
        [contact] = sightings(s)
        self.assertEqual(contact["composition"]["weapons"], "not established")
        self.assertEqual(tactics_v11.threat_range(s, unit(s, "B1"), [contact]), 3)

    def test_the_units_own_longer_range_is_kept(self):
        s = duel(b1="machine guns", g1="short rifles")
        contacts = sightings(s, identify="short rifles")
        self.assertEqual(tactics_v11.threat_range(s, unit(s, "B1"), contacts), 3)

    def test_without_weapon_rules_the_threat_range_stays_five(self):
        s = duel(weapons=None)
        contacts = sightings(s, identify="machine guns")
        for seen in ([], contacts):
            with self.subTest(contacts=len(seen)):
                self.assertEqual(tactics_v11.threat_range(s, unit(s, "B1"), seen), 5)

    def test_a_hidden_longer_range_enemy_does_not_change_the_decision(self):
        # G2 carries the longest range and stands 9 hexes off, beyond B1's sight (7).
        hidden = UnitEntry("G2", "confederate", "Hidden guns", (5, 14),
                           {"fire_posture": "hold_fire", "weapon_class": "machine guns"})
        alone, with_hidden = duel(g1="short rifles"), duel(g1="short rifles", extra=(hidden,))
        seen_alone = sightings(alone, identify="short rifles")
        seen_with = sightings(with_hidden, identify="short rifles")
        self.assertNotIn("G2", [c["id"] for c in seen_with])
        first = tactics_v11.decide(alone, unit(alone, "B1"), seen_alone)
        second = tactics_v11.decide(with_hidden, unit(with_hidden, "B1"), seen_with)
        self.assertEqual(first, second)
        self.assertEqual(first["action"], "observe")
        self.assertEqual(tactics_v11.threat_range(with_hidden, unit(with_hidden, "B1"), seen_with), 1)


class SelectionTests(unittest.TestCase):
    """Only an entry that names tactics_v11 gets it; every other snapshot is unchanged."""

    def test_the_snapshot_names_tactics_v11_only_when_the_entry_selects_it(self):
        self.assertEqual(duel()["tactics"], TACTICS_V11)
        self.assertNotIn("tactics", duel(tactics=None, weapons={"machine guns": LONG}, g1="machine guns",
                                         b1="machine guns"))
        self.assertNotIn("tactics", build_state(DUEL))

    def test_the_engine_reacts_by_tactics_v11_only_on_an_entry_that_selects_it(self):
        v11 = advance(duel(g1="carbines", weapons={"short rifles": SHORT, "carbines": MEDIUM, "machine guns": LONG}))
        [decision] = [e for e in events(v11, "local_decision") if e["unit_id"] == "B1"]
        self.assertIn(decision["action"], REACTIONS)  # Unidentified at 3 hexes: the table's 3.
        single = {"short rifles": SHORT}
        v10 = advance(duel(g1="short rifles", tactics=None, weapons=single))
        [decision] = [e for e in events(v10, "local_decision") if e["unit_id"] == "B1"]
        self.assertEqual(decision["action"], "observe")

    def test_an_edition_before_poc_13_refuses_tactics_v11(self):
        with self.assertRaisesRegex(ValueError, "tactics_v11"):
            build_state(dataclasses.replace(DUEL, tactics=TACTICS_V11), rules="poc-12")

    def test_a_snapshot_with_an_unknown_tactics_edition_is_refused_at_execution(self):
        s = duel()
        s["tactics"] = "tactics_v9"
        with self.assertRaisesRegex(ValueError, "Unsupported tactics edition 'tactics_v9'"):
            advance(s)

    def test_an_unknown_tactics_edition_is_refused(self):
        with self.assertRaisesRegex(ValueError, "tactics"):
            validate(night_entry(tactics="tactics_v9"))


class MixedRangeGuardTests(unittest.TestCase):
    """weapon_problems refuses mixed ranges on tactics_v10 and accepts them on tactics_v11."""

    UNITS = (UnitEntry("B1", "union", "Blue", (5, 4), {"weapon_class": "short rifles"}),
             UnitEntry("G1", "confederate", "Grey", (5, 2), {"weapon_class": "machine guns"}))

    def test_mixed_ranges_are_refused_on_tactics_v10(self):
        with self.assertRaisesRegex(ValueError, r"single weapon range.*\[1, 2, 3\]"):
            validate(night_entry(units=self.UNITS, weapons=MIXED))

    def test_mixed_ranges_are_accepted_on_tactics_v11(self):
        entry = validate(night_entry(units=self.UNITS, weapons=MIXED, tactics=TACTICS_V11))
        self.assertEqual(sorted(w["range_hexes"] for w in build_state(entry)["weapon_rules"].values()), [1, 2, 3])

    def test_an_observer_weapon_label_is_refused_as_a_class_name(self):
        for label in ("long arms", "not established"):
            units = (self.UNITS[0], UnitEntry("G1", "confederate", "Grey", (5, 2), {"weapon_class": label}))
            weapons = {"short rifles": SHORT, label: LONG}
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "observer's label"):
                validate(night_entry(units=units, weapons=weapons, tactics=TACTICS_V11))

    def test_tactics_v11_still_refuses_a_unit_outside_the_table(self):
        units = self.UNITS[:1] + (UnitEntry("G1", "confederate", "Grey", (5, 2)),)
        with self.assertRaisesRegex(ValueError, "G1"):
            validate(night_entry(units=units, weapons=MIXED, tactics=TACTICS_V11))

if __name__ == "__main__":
    unittest.main()
