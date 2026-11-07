"""Surrender and captives (docs/research/59 §1).

Fixtures are the small synthetic 1944 entries of ``test_pegasus_engine`` on
flat ground; none is a historical scenario. D1, a 75-man group at (12, 4),
may declare a surrender rule. B2, a 17-man party holding fire, stands next
to it; B1 (union headquarters) is across the canal and G1 (confederate
headquarters) far to the west. A line unit's estimate of 17 men at this
range is 1 to 60, and the rule reads the high end.
"""

import dataclasses
import json
import unittest

from battle import captives, engine, formations, recon
from battle.scenario_entry import UnitEntry, build_state, validate
from scenario_fixtures import DUEL
from test_formations import SPLIT, fixture as formation_fixture
from test_gateway_push import events, unit
from test_pegasus_engine import advance, night, night_entry

YIELDS = {"reach": 2, "odds_pct": 70, "support_reach": 3, "rear_only": False}
HOLD = {"fire_posture": "hold_fire"}
GROUP = (12, 4)


def roster(rule=YIELDS, b2=(12, 3), extra=(), group=None):
    """B1, G1 far off; B2 (17 men) at ``b2``; D1 (75 men) at GROUP with ``rule``."""
    d1 = {"strength": 75, "initial": 75, **HOLD, **(group or {})}
    if rule is not None:
        d1["surrender"] = dict(rule) if isinstance(rule, dict) else rule
    return (UnitEntry("B1", "union", "Company post", (12, 16), HOLD),
            UnitEntry("B2", "union", "Patrol", b2, {"strength": 17, "initial": 17, **HOLD}),
            UnitEntry("G1", "confederate", "Battalion post", (20, 2), HOLD),
            UnitEntry("D1", "confederate", "Command group", GROUP, d1),
            *extra)


def state(rule=YIELDS, sight=None, **kw):
    return night(units=roster(rule, **kw), **({} if sight is None else {"observation_range": sight}))


def surrendered(s):
    return [(e["unit_id"], e["holder_id"], e["count"]) for e in events(s, "unit_surrendered")]


class SurrenderRuleTests(unittest.TestCase):
    """When a declaring unit yields, read from what it observes."""

    def test_an_undeclared_unit_never_surrenders(self):
        s = advance(state(rule=None), 2)
        self.assertEqual(surrendered(s), [])
        self.assertNotIn("captives", s)
        self.assertEqual(unit(s, "D1")["strength"], 75)

    def test_a_declaring_unit_yields_to_a_seen_party_that_it_believes_strong_enough(self):
        s = advance(state(), 1)
        self.assertEqual(surrendered(s), [("D1", "B2", 75)])
        d1 = unit(s, "D1")
        self.assertEqual((d1["strength"], d1["status"], d1["surrendered"]), (0, "lost", True))
        self.assertEqual(s["captives"], [{"id": "K1", "count": 75, "from_unit": "D1", "from_side": "confederate",
                                          "holder_id": "B2", "holder_side": "union", "turn": 1,
                                          "status": "held"}])
        self.assertEqual(unit(s, "B2")["captives"], 75)

    def test_odds_below_the_declared_ratio_do_not_yield(self):
        s = advance(state(rule={**YIELDS, "odds_pct": 100}), 2)
        self.assertEqual(surrendered(s), [])

    def test_an_enemy_beyond_reach_does_not_count(self):
        s = advance(state(b2=(12, 1)), 1)  # 3 hexes off; reach 2.
        self.assertEqual(surrendered(s), [])

    def test_a_seen_friend_within_support_reach_prevents_the_surrender(self):
        friend = UnitEntry("D2", "confederate", "Rifle group", (12, 7), HOLD)  # 3 hexes south.
        self.assertEqual(surrendered(advance(state(extra=(friend,), sight=3), 1)), [])

    def test_a_friend_the_unit_cannot_see_gives_no_support(self):
        friend = UnitEntry("D2", "confederate", "Rifle group", (12, 7), HOLD)
        self.assertEqual(surrendered(advance(state(extra=(friend,), sight=2), 1)), [("D1", "B2", 75)])

    def test_an_enemy_the_unit_cannot_observe_does_not_change_the_decision(self):
        # At odds 100 the seen party alone is not enough. B3, 80 men 2 hexes
        # off and within reach, is beyond a 1-hex sight in both of the first
        # two states, so the decision is the same; seen, it tips the balance.
        rule = {**YIELDS, "odds_pct": 100}
        hidden = UnitEntry("B3", "union", "Column", (12, 2), {"strength": 80, "initial": 80, **HOLD})
        alone = advance(state(rule=rule, sight=1), 1)
        with_hidden = advance(state(rule=rule, sight=1, extra=(hidden,)), 1)
        self.assertEqual(surrendered(alone), surrendered(with_hidden))
        self.assertEqual(surrendered(alone), [])
        self.assertEqual(surrendered(advance(state(rule=rule, sight=2, extra=(hidden,)), 1)), [("D1", "B2", 75)])

    def test_rear_only_counts_only_enemies_outside_the_units_arc(self):
        rule = {**YIELDS, "rear_only": True}
        facing_south = {"facing": 180, "arc": 90, "reorient_turns": 0}
        rear = advance(state(rule=rule, group=facing_south), 1)  # B2 north: the rear.
        front = advance(state(rule=rule, group=facing_south, b2=(12, 5)), 1)  # B2 south: the front.
        self.assertEqual(surrendered(rear), [("D1", "B2", 75)])
        self.assertEqual(surrendered(front), [])

    def test_the_nearest_seen_enemy_holds_the_captives(self):
        near = UnitEntry("B3", "union", "Second party", (12, 5), {"strength": 17, "initial": 17, **HOLD})
        s = advance(state(b2=(12, 2), extra=(near,)), 1)
        self.assertEqual(surrendered(s), [("D1", "B3", 75)])

    def test_decisions_in_one_interval_are_taken_together(self):
        # D1 (odds 50) yields even with D2's support; D2 (odds 70) does not
        # with D1's. Taken one after the other, D2 would have lost D1's
        # support and yielded too; taken together it stands until it sees
        # D1 gone, in a later interval.
        d2 = UnitEntry("D2", "confederate", "Rifle group", (11, 4),
                       {"strength": 20, "initial": 20, "surrender": dict(YIELDS), **HOLD})
        s = advance(state(rule={**YIELDS, "odds_pct": 50}, extra=(d2,)), 1)
        self.assertEqual(surrendered(s), [("D1", "B2", 75)])
        self.assertEqual(surrendered(advance(s, 1)), [("D1", "B2", 75), ("D2", "B2", 20)])


class CaptiveAccountTests(unittest.TestCase):
    """Captives are conserved, held by a unit and reported by the report path."""

    def test_personnel_are_conserved(self):
        s = advance(state(), 3)
        held = sum(k["count"] for k in s["captives"])
        self.assertEqual(unit(s, "D1")["strength"] + held, 75)
        self.assertEqual(unit(s, "B2")["captives"], held)

    def test_captives_escape_when_their_holder_routs(self):
        s = advance(state(), 1)
        unit(s, "B2")["morale"] = 10
        s = advance(s, 1)
        self.assertEqual(unit(s, "B2")["status"], "routed")
        self.assertEqual(s["captives"][0]["status"], "escaped")
        self.assertEqual(s["captives"][0]["escaped_turn"], 2)
        self.assertEqual(unit(s, "B2")["captives"], 0)
        self.assertEqual([(e["captive_id"], e["count"]) for e in events(s, "captives_escaped")], [("K1", 75)])

    def test_headquarters_learns_of_the_captives_only_by_delivered_report(self):
        s = advance(state(), 1)
        union = engine.view(s, "union")
        self.assertNotIn("captives", union["units"][[u["id"] for u in union["units"]].index("B2")])
        self.assertFalse(any("prisoners" in d["text"] for d in union["dispatches"]))
        for _ in range(20):
            s = advance(s, 1)
            union = engine.view(s, "union")
            if any("prisoners" in d["text"] for d in union["dispatches"]):
                break
        self.assertIn("B2: 75 prisoners taken from D1.", [d["text"] for d in union["dispatches"]])
        reported = next(u for u in union["units"] if u["id"] == "B2")
        self.assertEqual(reported["captives"], 75)

    def test_the_yielding_side_is_not_told(self):
        s = advance(state(), 6)
        text = json.dumps(engine.view(s, "confederate"))
        self.assertNotIn("prisoners", text)
        self.assertNotIn("captives", text)


class SurrenderValidationTests(unittest.TestCase):
    """Registration refuses a rule the engine cannot run."""

    def test_registration_refuses_a_bad_rule(self):
        for bad in ({**YIELDS, "reach": 0}, {**YIELDS, "reach": 8}, {**YIELDS, "odds_pct": 0},
                    {**YIELDS, "odds_pct": 1001}, {**YIELDS, "support_reach": -1}, {**YIELDS, "rear_only": 1},
                    {k: v for k, v in YIELDS.items() if k != "reach"}, {**YIELDS, "extra": 1}, "yes", True):
            with self.subTest(rule=bad):
                with self.assertRaisesRegex(ValueError, "surrender"):
                    validate(night_entry(units=roster(rule=bad)))

    def test_rear_only_needs_a_declared_facing(self):
        with self.assertRaisesRegex(ValueError, "rear_only needs a declared facing"):
            validate(night_entry(units=roster(rule={**YIELDS, "rear_only": True})))

    def test_an_edition_before_poc_13_refuses_a_surrender_rule(self):
        units = (dataclasses.replace(DUEL.units[0], overrides={"surrender": dict(YIELDS)}),) + DUEL.units[1:]
        with self.assertRaisesRegex(ValueError, "surrender"):
            build_state(dataclasses.replace(DUEL, units=units), rules="poc-12")

    def test_a_unit_holding_captives_neither_splits_nor_combines(self):
        s = formation_fixture()
        engine.find_unit(s, "U1")["captives"] = 5
        with self.assertRaisesRegex(ValueError, "captives"):
            formations.request(s, "union", SPLIT)


if __name__ == "__main__":
    unittest.main()
