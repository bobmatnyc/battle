"""Victory kind ``raid-and-return`` (docs/research/59 §3).

Fixtures are the small synthetic 1944 entries of ``test_pegasus_engine`` on
flat ground; none is a historical scenario. Grey (the attacker) sends G2, a
20-man party, from (5, 2) to the objective at (5, 8) and back. The tests
place G2 by hand between intervals, so only the scoring decides. Everyone
holds fire and no one is in sight of anyone else.
"""

import dataclasses
import json
import unittest

from battle import engine, victory
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from scenario_fixtures import DUEL
from test_gateway_push import unit
from test_pegasus_engine import advance, night_entry

HOLD = {"fire_posture": "hold_fire"}
HOME = (5, 2)
OBJECTIVE = (5, 8)
RAID = VictoryEntry(kind="raid-and-return", objective=OBJECTIVE, deadline_turns=12, radius=1, hold_turns=1,
                    objective_name="gun position", raiders=("G2",), return_hex=HOME, return_radius=1,
                    return_pct=50)
UNITS = (UnitEntry("B1", "union", "Company post", (12, 16), HOLD),
         UnitEntry("G1", "confederate", "Battalion post", (20, 2), HOLD),
         # rout_strength 0: a party cut down by hand must not rout before scoring.
         UnitEntry("G2", "confederate", "Raiding party", HOME,
                   {"strength": 20, "initial": 20, "rout_strength": 0, **HOLD}))


def with_victory(victory):
    return dataclasses.replace(night_entry(units=UNITS), victory=victory)


def raid(**fields):
    return with_victory(dataclasses.replace(RAID, **fields))


def raid_state(**fields):
    return build_state(dry_run(validate(raid(**fields))))


def step(s, pos=None, **changes):
    """Place G2 at ``pos`` (and apply ``changes``), then advance one interval."""
    if pos is not None:
        unit(s, "G2")["pos"] = list(pos)
    unit(s, "G2").update(changes)
    return advance(s, 1)


def there_and_back(s):
    s = step(s, OBJECTIVE)
    return step(s, HOME)


class RaidScoringTests(unittest.TestCase):
    """The attacker wins by raiding the objective and bringing the force back."""

    def test_raid_then_return_wins_for_the_attacker(self):
        s = there_and_back(raid_state())
        self.assertEqual((s["status"], s["winner"], s["turn"]), ("complete", "confederate", 2))
        self.assertEqual(s["reason"], "The raiders reached the gun position and 20 of them came back by the deadline.")
        self.assertEqual(s["victory"]["raided_turn"], 1)

    def test_standing_at_home_without_the_raid_wins_nothing(self):
        s = raid_state()
        for _ in range(12):
            s = step(s)
        self.assertEqual((s["winner"], s["turn"]), ("union", 12))
        self.assertIsNone(s["victory"]["raided_turn"])

    def test_the_raid_lasts_hold_turns_intervals(self):
        s = step(raid_state(hold_turns=2), OBJECTIVE)
        self.assertIsNone(s["victory"]["raided_turn"])
        s = step(s, HOME)
        self.assertEqual(s["status"], "active")
        s = step(step(s, OBJECTIVE), OBJECTIVE)
        self.assertEqual(s["victory"]["raided_turn"], 4)

    def test_too_few_returning_men_do_not_win(self):
        for fields, strength, won in (({"return_pct": 50}, 9, False), ({"return_pct": 50}, 10, True),
                                      ({"return_pct": None, "return_strength": 15}, 14, False),
                                      ({"return_pct": None, "return_strength": 15}, 15, True)):
            with self.subTest(fields=fields, strength=strength):
                s = step(step(raid_state(**fields), OBJECTIVE), HOME, strength=strength)
                self.assertEqual(s["winner"] == "confederate", won)

    def test_min_captives_counts_captives_held_by_the_returning_raiders(self):
        for held, won in ((None, False), ("G1", False), ("G2", True)):
            with self.subTest(holder=held):
                s = step(raid_state(min_captives=5), OBJECTIVE)
                if held:
                    s["captives"] = [{"id": "K1", "count": 5, "from_unit": "B9", "from_side": "union",
                                      "holder_id": held, "holder_side": "confederate", "turn": 1, "status": "held"}]
                s = step(s, HOME)
                self.assertEqual(s["winner"] == "confederate", won)

    def test_escaped_captives_do_not_count(self):
        s = step(raid_state(min_captives=5), OBJECTIVE)
        s["captives"] = [{"id": "K1", "count": 5, "from_unit": "B9", "from_side": "union", "holder_id": "G2",
                          "holder_side": "confederate", "turn": 1, "status": "escaped"}]
        self.assertEqual(step(s, HOME)["status"], "active")

    def test_the_defender_wins_when_no_raider_is_effective(self):
        s = step(raid_state(), OBJECTIVE, status="routed")
        self.assertEqual((s["winner"], s["reason"]), ("union", "The raiding force is no longer effective."))

    def test_nothing_of_the_raid_state_reaches_either_view(self):
        s = step(raid_state(), OBJECTIVE)
        for side in ("union", "confederate"):
            text = json.dumps(engine.view(s, side))
            self.assertNotIn("raided", text)
            self.assertNotIn("return_hex", text)


class RaidValidationTests(unittest.TestCase):
    """Registration refuses a raid the rules cannot score."""

    def test_registration_refuses_bad_raid_fields(self):
        for fields in ({"raiders": ()}, {"raiders": ("B1",)}, {"raiders": ("G2", "G2")}, {"raiders": ("X9",)},
                       {"return_hex": None}, {"return_hex": (99, 2)}, {"return_radius": -1},
                       {"return_pct": None}, {"return_strength": 5}, {"return_pct": 0}, {"return_pct": 101},
                       {"return_pct": None, "return_strength": 21}, {"min_captives": 0},
                       {"relief_turn": 3}, {"more_objectives": ((6, 6),)}):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, "raid-and-return|seize-and-hold"):
                    validate(raid(**fields))

    def test_other_kinds_refuse_the_raid_fields(self):
        for kind in ("hold-objective", "seize-and-hold"):
            for fields in ({"raiders": ("G2",)}, {"return_hex": HOME}, {"return_pct": 50}, {"return_strength": 5},
                           {"min_captives": 1}, {"return_radius": 2}):
                with self.subTest(kind=kind, fields=fields):
                    entry = with_victory(VictoryEntry(
                        kind=kind, objective=OBJECTIVE, deadline_turns=12, objective_name="gun position", **fields))
                    with self.assertRaisesRegex(ValueError, "raid-and-return"):
                        validate(entry)

    def test_an_edition_before_poc_13_refuses_the_poc_13_victory_kinds(self):
        seize = VictoryEntry(kind="seize-and-hold", objective=OBJECTIVE, deadline_turns=12,
                             objective_name="gun position")
        # No unit declares a scenario_units key, so only the victory kind can trigger the refusal.
        units = UNITS[:2] + (UnitEntry("G2", "confederate", "Raiding party", HOME, {"strength": 20, "initial": 20}),)
        for victory_entry in (RAID, seize):
            with self.subTest(kind=victory_entry.kind):
                entry = dataclasses.replace(DUEL, victory=victory_entry, units=units,
                                            labels={"poc-12": "test-duel-v5", "poc-13": "test-duel-v6"})
                validate(entry)
                with self.assertRaisesRegex(ValueError, f"poc-12 has no .*{victory_entry.kind}"):
                    build_state(entry, rules="poc-12")
                self.assertEqual(build_state(entry, rules="poc-13")["victory"]["kind"], victory_entry.kind)

    def test_a_valid_raid_builds_its_parameters_into_the_snapshot(self):
        v = raid_state(min_captives=3)["victory"]
        self.assertEqual(v, {"kind": "raid-and-return", "objective": list(OBJECTIVE), "radius": 1, "hold_turns": 1,
                             "objective_name": "gun position", "raiders": ["G2"], "force": 20,
                             "return_hex": list(HOME), "return_radius": 1, "return_needed": 10,
                             "min_captives": 3, "captures": 0, "raided_turn": None})
        self.assertIn("raid-and-return", victory.KINDS)


if __name__ == "__main__":
    unittest.main()
