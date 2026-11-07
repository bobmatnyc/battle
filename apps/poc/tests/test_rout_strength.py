"""A declared rout threshold for small units (docs/research/58 §1).

Fixtures are the small synthetic 1944 entries of ``test_pegasus_engine`` on
flat ground, far apart so that no contact or fire decides; none is a
historical scenario. The engine's rout check runs every interval, so a unit
built below the threshold shows the rule without combat.
"""

import dataclasses
import unittest

from battle import engine, formations
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_formations import SPLIT, fixture as formation_fixture
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night, night_entry


def party(**overrides):
    """B1, a small union party far from G1; ``overrides`` replace its fields."""
    return (UnitEntry("B1", "union", "Patrol", (12, 16), {"strength": 8, "initial": 17, **overrides}),
            UnitEntry("G1", "confederate", "Guard", (20, 2), {"ammo": 0}))


class RoutThresholdTests(unittest.TestCase):
    """The engine routs a unit below its declared ``rout_strength``, else below 12."""

    def test_a_declared_unit_with_8_men_does_not_rout_at_threshold_4(self):
        s = advance(night(units=party(rout_strength=4)), 2)
        self.assertEqual(unit(s, "B1")["rout_strength"], 4)
        self.assertNotEqual(unit(s, "B1")["status"], "routed")
        self.assertEqual([e for e in events(s, "unit_routed") if e["unit_id"] == "B1"], [])

    def test_an_undeclared_unit_still_routs_under_12(self):
        s = night(units=party())
        self.assertNotIn("rout_strength", unit(s, "B1"))
        s = advance(s)
        self.assertEqual(unit(s, "B1")["status"], "routed")
        self.assertEqual([e["unit_id"] for e in events(s, "unit_routed")], ["B1"])

    def test_an_undeclared_unit_of_12_does_not_rout(self):
        s = advance(night(units=party(strength=12)))
        self.assertNotEqual(unit(s, "B1")["status"], "routed")

    def test_a_declared_unit_routs_below_its_own_threshold(self):
        s = night(units=party(rout_strength=4))
        for strength, routed in ((4, False), (3, True)):
            with self.subTest(strength=strength):
                unit(s, "B1")["strength"] = strength
                s = advance(s)
                self.assertEqual(unit(s, "B1")["status"] == "routed", routed)


class RoutValidationTests(unittest.TestCase):
    """Registration refuses a threshold the rules cannot use."""

    def test_registration_refuses_a_bad_rout_strength(self):
        for bad in (-1, 8, 9, "4", 4.0, True, None):
            with self.subTest(rout_strength=bad):
                with self.assertRaisesRegex(ValueError, "rout_strength"):
                    validate(night_entry(units=party(rout_strength=bad)))

    def test_the_threshold_is_compared_with_the_default_strength_when_none_is_set(self):
        units = (UnitEntry("B1", "union", "Patrol", (12, 16), {"rout_strength": 39}),
                 UnitEntry("G1", "confederate", "Guard", (20, 2), {"rout_strength": 40}))
        with self.assertRaisesRegex(ValueError, r"'G1' rout_strength") as caught:
            validate(night_entry(units=units))
        self.assertNotIn("'B1'", str(caught.exception))

    def test_zero_is_accepted(self):
        self.assertEqual(night(units=party(rout_strength=0))["units"][0]["rout_strength"], 0)

    def test_an_edition_before_poc_13_refuses_rout_strength(self):
        units = (dataclasses.replace(DUEL.units[0], overrides={"rout_strength": 4}),) + DUEL.units[1:]
        with self.assertRaisesRegex(ValueError, "rout_strength"):
            build_state(dataclasses.replace(DUEL, units=units), rules="poc-12")


def declare(s, uid, threshold=4):
    """Give ``uid`` a rout threshold in truth and in headquarters' report."""
    engine.find_unit(s, uid)["rout_strength"] = threshold
    s["friendly_reports"]["union"][uid]["rout_strength"] = threshold


class RoutFormationTests(unittest.TestCase):
    """A split would copy one absolute threshold to two smaller halves and a
    combine would keep only one, so neither applies to a declaring unit.
    Fixture: ``test_formations.fixture``; U1 and U2 adjacent, U2 the command unit."""

    def test_split_of_a_declaring_unit_is_refused_at_request(self):
        s = formation_fixture()
        declare(s, "U1")
        with self.assertRaisesRegex(ValueError, "rout_strength"):
            formations.request(s, "union", SPLIT)
        self.assertEqual(s["formation_ops"], [])

    def test_combine_is_refused_whichever_unit_declares(self):
        for carrier in ("U1", "U2"):
            with self.subTest(carrier=carrier):
                s = formation_fixture()
                declare(s, carrier)
                with self.assertRaisesRegex(ValueError, "rout_strength"):
                    formations.request(s, "union", {"kind": "combine", "unit_id": "U2", "partner_id": "U1"})

    def test_split_applied_after_the_unit_declared_is_refused_at_execution(self):
        s = formation_fixture()
        formations.request(s, "union", SPLIT)
        engine.find_unit(s, "U1")["rout_strength"] = 4
        for _ in range(3):
            engine.advance(s)
        op = s["formation_ops"][0]
        self.assertEqual(op["status"], "refused")
        self.assertIn("rout_strength", op["reason"])

    def test_split_or_combine_queued_before_any_fixed_key_is_refused_at_execution(self):
        # bt-T02: each key formations.declares_rout reads, given after the request was accepted.
        keys = {
            "rout_strength": {"rout_strength": 4},
            "facing": {"facing": 0, "arc": 180, "reorient_turns": 0},
            "surrender": {"surrender": {"odds_pct": 100, "reach": 1, "rear_only": False, "support_reach": 0}},
            "captives": {"captives": 5},
            "exploit": {"exploit": {"trigger": "arrival", "press_to": [2, 8], "recall_binding": True,
                                    "max_loss_pct": 50}},
        }
        requests = {"split": SPLIT, "combine": {"kind": "combine", "unit_id": "U2", "partner_id": "U1"}}
        for key, fields in keys.items():
            for kind, request in requests.items():
                with self.subTest(key=key, kind=kind):
                    s = formation_fixture()
                    formations.request(s, "union", request)  # Valid when queued: U1 declares nothing yet.
                    engine.find_unit(s, "U1").update(fields)
                    for _ in range(3):
                        engine.advance(s)
                    op = s["formation_ops"][0]
                    self.assertEqual((op["status"], op["reason"]), ("refused", formations.ROUT_REFUSAL))
                    self.assertFalse(events(s, "unit_split") or events(s, "units_combined"))
                    self.assertNotEqual(engine.find_unit(s, "U1")["status"], "merged")


if __name__ == "__main__":
    unittest.main()
