"""Victory kind ``recover-force`` (docs/research/60 §3).

Fixtures are the small synthetic entries of ``test_pegasus_engine`` on flat
ground; none is a historical scenario and every value is authored for the
test. Grey (the attacker) must bring G2, a 20-man forward party at (5, 8),
back to the rally hex (5, 2). The tests place G2 by hand between intervals,
so only the scoring decides. Everyone holds fire and no one is in sight of
anyone else.
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
RALLY = (5, 2)
FORWARD = (5, 8)
RECOVER = VictoryEntry(kind="recover-force", objective=FORWARD, deadline_turns=12, objective_name="taken camps",
                       recover_units=("G2",), rally_hex=RALLY, rally_radius=1, recover_pct=50)
UNITS = (UnitEntry("B1", "union", "Company post", (12, 16), HOLD),
         UnitEntry("G1", "confederate", "Command group", (20, 2), HOLD),
         # rout_strength 0: a party cut down by hand must not rout before scoring.
         UnitEntry("G2", "confederate", "Forward party", FORWARD,
                   {"strength": 20, "initial": 20, "rout_strength": 0, **HOLD}))


def with_victory(victory_entry, units=UNITS):
    return dataclasses.replace(night_entry(units=units), victory=victory_entry)


def recover(**fields):
    return with_victory(dataclasses.replace(RECOVER, **fields))


def recover_state(**fields):
    return build_state(dry_run(validate(recover(**fields))))


def step(s, pos=None, **changes):
    """Place G2 at ``pos`` (and apply ``changes``), then advance one interval."""
    if pos is not None:
        unit(s, "G2")["pos"] = list(pos)
    unit(s, "G2").update(changes)
    return advance(s, 1)


class RecoverScoringTests(unittest.TestCase):
    """The attacker wins by bringing the declared share of the force back to the rally hex."""

    def test_bringing_the_force_back_wins_for_the_attacker(self):
        s = step(step(recover_state()), RALLY)
        self.assertEqual((s["status"], s["winner"], s["turn"]), ("complete", "confederate", 2))
        self.assertEqual(s["reason"], "The commander brought 20 of the forward force back to the rally point "
                                      "by the deadline.")
        self.assertEqual(s["victory"]["recovered_turn"], 2)

    def test_a_force_left_forward_loses_at_the_deadline(self):
        s = recover_state()
        for _ in range(12):
            s = step(s)
        self.assertEqual((s["winner"], s["turn"]), ("union", 12))
        self.assertEqual(s["reason"], "The forward force was not brought back to the rally point by the deadline.")

    def test_too_few_returning_men_do_not_win(self):
        for fields, strength, won in (({"recover_pct": 50}, 9, False), ({"recover_pct": 50}, 10, True),
                                      ({"recover_pct": None, "recover_strength": 15}, 14, False),
                                      ({"recover_pct": None, "recover_strength": 15}, 15, True)):
            with self.subTest(fields=fields, strength=strength):
                s = step(recover_state(**fields), RALLY, strength=strength)
                self.assertEqual(s["winner"] == "confederate", won)

    def test_men_outside_the_rally_radius_do_not_count(self):
        s = step(recover_state(), (5, 5))
        self.assertEqual(s["status"], "active")

    def test_a_routed_party_does_not_count(self):
        s = step(recover_state(), RALLY, status="routed")
        self.assertNotEqual(s["winner"], "confederate")

    def test_the_defender_wins_when_the_force_can_no_longer_bring_back_enough(self):
        s = step(recover_state(), strength=9)
        self.assertEqual((s["winner"], s["reason"]),
                         ("union", "The forward force can no longer bring back the men required."))

    def test_nothing_of_the_recovery_state_reaches_either_view(self):
        s = step(recover_state())
        for side in ("union", "confederate"):
            text = json.dumps(engine.view(s, side))
            for marker in ("recover_units", "recovered_turn", "recover_needed", "rally_hex"):
                self.assertNotIn(marker, text)


class RecoverValidationTests(unittest.TestCase):
    """Registration refuses a recovery the rules cannot score."""

    def test_registration_refuses_bad_recover_fields(self):
        for fields in ({"recover_units": ()}, {"recover_units": ("B1",)}, {"recover_units": ("G2", "G2")},
                       {"recover_units": ("X9",)}, {"rally_hex": None}, {"rally_hex": (99, 2)},
                       {"rally_radius": -1}, {"rally_radius": True}, {"recover_pct": None},
                       {"recover_strength": 5}, {"recover_pct": 0}, {"recover_pct": 101},
                       {"recover_pct": None, "recover_strength": 21},
                       {"relief_turn": 3}, {"more_objectives": ((6, 6),)}, {"raiders": ("G2",)},
                       {"return_hex": RALLY}):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, "recover-force|seize-and-hold|raid-and-return"):
                    validate(recover(**fields))

    def test_a_force_that_starts_recovered_is_refused(self):
        with self.assertRaisesRegex(ValueError, "recover-force .*already"):
            validate(recover(rally_hex=FORWARD))

    def test_other_kinds_refuse_the_recover_fields(self):
        raid = {"raiders": ("G2",), "return_hex": RALLY, "return_pct": 50}
        for kind, base in (("hold-objective", {}), ("seize-and-hold", {}), ("raid-and-return", raid)):
            for fields in ({"recover_units": ("G2",)}, {"rally_hex": RALLY}, {"rally_radius": 2},
                           {"recover_pct": 50}, {"recover_strength": 5}):
                with self.subTest(kind=kind, fields=fields):
                    entry = with_victory(VictoryEntry(kind=kind, objective=FORWARD, deadline_turns=12,
                                                      objective_name="taken camps", **base, **fields))
                    with self.assertRaisesRegex(ValueError, "recover-force"):
                        validate(entry)

    def test_an_edition_before_poc_13_refuses_the_kind(self):
        # No unit declares a scenario_units key, so only the victory kind can trigger the refusal.
        units = UNITS[:2] + (UnitEntry("G2", "confederate", "Forward party", FORWARD, {"strength": 20, "initial": 20}),)
        entry = dataclasses.replace(DUEL, victory=RECOVER, units=units,
                                    labels={"poc-12": "test-duel-v5", "poc-13": "test-duel-v6"})
        validate(entry)
        with self.assertRaisesRegex(ValueError, "poc-12 has no .*recover-force"):
            build_state(entry, rules="poc-12")
        self.assertEqual(build_state(entry, rules="poc-13")["victory"]["kind"], "recover-force")

    def test_a_valid_recovery_builds_its_parameters_into_the_snapshot(self):
        v = recover_state()["victory"]
        self.assertEqual(v, {"kind": "recover-force", "objective_name": "taken camps", "recover_units": ["G2"],
                             "force": 20, "rally_hex": list(RALLY), "rally_radius": 1, "recover_needed": 10,
                             "recovered_turn": None})
        self.assertIn("recover-force", victory.KINDS)


if __name__ == "__main__":
    unittest.main()
