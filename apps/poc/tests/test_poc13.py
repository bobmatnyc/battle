"""poc-13 part A: an impassable river with crossings, fire discipline, and
contacts that age out of the assault check. Design: docs/research/46.

Fixtures are small synthetic duels on flat ground; none is a scenario.
"""

import dataclasses
import json
import unittest

from battle import engine, grid, runtime
from battle.engine_v2 import InvalidOrder
from battle.scenario_entry import FireEntry, UnitEntry, VictoryEntry, build_state, dry_run, validate
from scenario_fixtures import DUEL, flat_terrain
from test_gateway_push import FARM, events, held_gateway, unit

RIVER_ROW = 10
BRIDGE = [12, 10]


def advance(s, n=1):
    for _ in range(n):
        if s["status"] != "active":break
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def river_terrain(crossing=None):
    """Flat ground with impassable water along row 10; ``crossing`` (bridge or
    ford) makes the water hex at BRIDGE passable."""
    def build():
        cells = flat_terrain()
        for c in range(grid.COLS):
            cells[grid.key([c, RIVER_ROW])].update(terrain="water", water=True, cover=0)
        if crossing:cells[grid.key(BRIDGE)]["crossing"] = crossing
        return cells
    return build


def river_entry(crossing=None, units=None, fire=None):
    """B1 (Blue command) south of the river, G1 far to the north-east."""
    units = units or (UnitEntry("B1", "union", "Blue detachment", (5, 12)),
                      UnitEntry("G1", "confederate", "Grey detachment", (20, 2), {"ammo": 0}))
    return dataclasses.replace(
        DUEL, id="test-river", labels={"poc-13": "test-river-v1"},
        units=units, fire=fire,
        victory=VictoryEntry(kind="hold-objective", objective=(1, 1), deadline_turns=60, objective_name="far corner"),
        map=dataclasses.replace(DUEL.map, terrain=river_terrain(crossing)))


def river(crossing=None, **kw):
    return build_state(dry_run(validate(river_entry(crossing, **kw))))


def moved_through(s, uid):
    return [e["destination"] for e in events(s, "unit_moved") if e["unit_id"] == uid]


class RiverTests(unittest.TestCase):
    """Water blocks troops and couriers, never sight; a bridge or ford crosses it."""

    def test_unit_cannot_cross_without_a_bridge(self):
        s = river()
        unit(s, "B1").update(stance="move", target=[5, 7])
        s = advance(s, 20)
        self.assertTrue(all(p[1] > RIVER_ROW for p in moved_through(s, "B1") + [unit(s, "B1")["pos"]]))
        self.assertEqual(grid.path(s["cells"], [5, 11], [5, 9]), [])

    def test_courier_estimate_across_water_without_a_bridge_is_unknown(self):
        s = river(units=(UnitEntry("B1", "union", "Blue detachment", (5, 12)),
                         UnitEntry("B2", "union", "Blue outpost", (5, 7)),
                         UnitEntry("G1", "confederate", "Grey detachment", (20, 2), {"ammo": 0})))
        order = engine.issue(s, "union", {"unit_id": "B2", "stance": "hold", "destination": None})
        self.assertIsNone(order["arrival_turn"])

    def test_unit_crosses_at_the_bridge(self):
        for crossing in ("bridge", "ford"):
            with self.subTest(crossing):
                s = river(crossing)
                unit(s, "B1").update(stance="move", target=[5, 7])
                s = advance(s, 40)
                water = [p for p in moved_through(s, "B1") if p[1] == RIVER_ROW]
                self.assertEqual(water, [BRIDGE])
                self.assertEqual(unit(s, "B1")["pos"], [5, 7])

    def test_sight_and_fire_cross_water_that_troops_cannot(self):
        s = river(units=(UnitEntry("B1", "union", "Blue detachment", (5, 12)),
                         UnitEntry("G1", "confederate", "Grey detachment", (5, 8), {"ammo": 0})))
        self.assertEqual(grid.path(s["cells"], [5, 11], [5, 9]), [])
        self.assertTrue(grid.visible(s["cells"], [5, 12], [5, 8]))
        s = advance(s)
        self.assertTrue([e for e in events(s, "volley") if e["unit_id"] == "B1" and e["target_id"] == "G1"])

    def test_registration_refuses_bad_water_data(self):
        bad_crossing = dataclasses.replace(river_entry(), map=dataclasses.replace(
            river_entry().map, terrain=lambda: {**river_terrain()(), grid.key([3, 3]): {
                **flat_terrain()[grid.key([3, 3])], "crossing": "bridge"}}))
        with self.assertRaisesRegex(ValueError, "crossing"):
            dry_run(validate(bad_crossing))
        drowned = river_entry(units=(UnitEntry("B1", "union", "Blue detachment", (5, 10)),
                                     UnitEntry("G1", "confederate", "Grey detachment", (20, 2))))
        with self.assertRaisesRegex(ValueError, "impassable water"):
            dry_run(validate(drowned))
        with self.assertRaisesRegex(ValueError, "poc-13"):
            build_state(dataclasses.replace(river_entry(), labels={"poc-12": "x", "poc-13": "y"}), "poc-12")

    def test_move_order_into_water_is_refused(self):
        s = river()
        with self.assertRaisesRegex(InvalidOrder, "water"):
            engine.issue(s, "union", {"unit_id": "B1", "stance": "move", "destination": [5, 10]})


def duel(b1="open_fire", g1="open_fire", g1_strength=40, warning_shots_release=False, b2=None):
    """B1 and G1 three hexes apart on open ground; B2 (if a posture) far behind B1."""
    def side(uid, side, name, pos, posture, extra=None):
        return UnitEntry(uid, side, name, pos, {"fire_posture": posture, **(extra or {})})
    units = [side("B1", "union", "Blue detachment", (5, 8), b1),
             side("G1", "confederate", "Grey detachment", (5, 5), g1,
                  {"strength": g1_strength, "initial": g1_strength})]
    if b2:units.append(side("B2", "union", "Blue reserve", (5, 16), b2))
    entry = dataclasses.replace(
        DUEL, id="test-fire", labels={"poc-13": "test-fire-v1"}, units=tuple(units),
        fire=FireEntry(warning_shots_release=warning_shots_release),
        victory=VictoryEntry(kind="hold-objective", objective=(20, 20), deadline_turns=60, objective_name="far hex"))
    return build_state(dry_run(validate(entry)))


def volleys(s, uid):
    return [e for e in events(s, "volley") if e["unit_id"] == uid]


class FireDisciplineTests(unittest.TestCase):
    """hold_fire units never fire first, return fire, and take delivered orders."""

    def test_hold_fire_units_do_not_fire_first(self):
        s = advance(duel("hold_fire", "hold_fire"), 3)
        self.assertEqual(events(s, "volley"), [])
        self.assertEqual(unit(s, "B1")["fire_posture"], "hold_fire")

    def test_hold_fire_unit_returns_fire_when_fired_upon(self):
        s = advance(duel("hold_fire", "open_fire"))
        self.assertTrue(volleys(s, "G1"))
        returned = volleys(s, "B1")
        self.assertTrue(returned)
        self.assertTrue(returned[0]["returning_fire"])
        self.assertGreaterEqual(returned[0]["turn"], volleys(s, "G1")[0]["turn"])

    def test_warning_shots_release_only_when_authored(self):
        # Two Grey men cause no casualties in the first intervals: a warning shot.
        for flag, expected in ((False, False), (True, True)):
            with self.subTest(warning_shots_release=flag):
                s = advance(duel("hold_fire", "open_fire", g1_strength=2, warning_shots_release=flag), 2)
                self.assertTrue(volleys(s, "G1"))
                self.assertEqual([e for e in events(s, "casualties") if e["unit_id"] == "B1"], [])
                self.assertEqual(bool(volleys(s, "B1")), expected)

    def test_open_fire_order_delivered_later_changes_the_posture(self):
        s = duel("hold_fire", "hold_fire")
        s = advance(s, 2)
        engine.issue(s, "union", {"unit_id": "B1", "stance": "open_fire", "destination": None})
        self.assertEqual(events(s, "volley"), [])
        s = advance(s, 3)
        self.assertEqual(unit(s, "B1")["fire_posture"], "open_fire")
        first = volleys(s, "B1")[0]
        self.assertFalse(first.get("returning_fire", False))
        self.assertEqual(volleys(s, "G1")[0]["turn"], first["turn"])  # G1 returns fire at once.
        self.assertEqual(next(u for u in engine.view(s, "union")["units"] if u["id"] == "B1")["fire_posture"], "open_fire")

    def test_hq_view_shows_the_posture_only_as_reported(self):
        s = duel("hold_fire", "hold_fire", b2="hold_fire")
        order = engine.issue(s, "union", {"unit_id": "B2", "stance": "open_fire", "destination": None})
        posture = lambda s: next(u for u in engine.view(s, "union")["units"] if u["id"] == "B2")["fire_posture"]
        while unit(s, "B2")["fire_posture"] != "open_fire":
            s = advance(s)
            self.assertLessEqual(s["turn"], 10)
        delivered = [e for e in events(s, "order_delivered") if e["order_id"] == order["id"]]
        self.assertEqual(delivered[0]["turn"], s["turn"])
        self.assertEqual(posture(s), "hold_fire")  # The report is still on its way.
        s = advance(s, 6)
        self.assertEqual(posture(s), "open_fire")

    def test_registration_refuses_unknown_postures(self):
        for fire, override in ((FireEntry(default_posture="fire_at_will"), {}),
                               (FireEntry(warning_shots_release="no"), {}),
                               (None, {"fire_posture": "volley"})):
            with self.subTest(fire=fire, override=override):
                entry = dataclasses.replace(DUEL, fire=fire, units=(
                    UnitEntry("B1", "union", "Blue detachment", (5, 4), override), DUEL.units[1]))
                with self.assertRaisesRegex(ValueError, "fire"):
                    validate(entry)

    def test_posture_order_keeps_the_mission(self):
        s = duel("hold_fire", "hold_fire")
        unit(s, "B1").update(stance="move", target=[5, 14], order_version=1)
        engine.issue(s, "union", {"unit_id": "B1", "stance": "open_fire", "destination": None})
        s = advance(s, 2)
        b1 = unit(s, "B1")
        self.assertEqual((b1["fire_posture"], b1["stance"], b1["order_version"]), ("open_fire", "move", 1))


def stale_assault(age):
    """G1 four hexes from the held gateway, ordered into the farm. The objective
    is moved off the compound, so only Grey headquarters' contact of B3 in the
    farm makes the move an assault. The contact is ``age`` intervals old when
    G1 decides."""
    s = held_gateway(rules="poc-13")
    s["objective"] = [1, 1]
    unit(s, "G1").update(pos=[15, 10], stance="move", target=list(FARM))
    s["turn"] = 10
    b3 = unit(s, "B3")
    s["contacts"]["grey"] = {"B3": {"id": "B3", "pos": list(b3["pos"]), "observed_turn": s["turn"] + 1 - age,
                                    "received_turn": s["turn"], "strength_range": [30, 50], "quality": 50}}
    return s


class StaleContactTests(unittest.TestCase):
    """The assault check reads only contacts the commander view still shows."""

    def test_fresh_contact_still_makes_an_assault(self):
        s = advance(stale_assault(6))
        self.assertEqual([e for e in events(s, "local_decision") if e["unit_id"] == "G1"][-1]["action"], "continue")

    def test_seven_turn_old_contact_no_longer_triggers_the_assault_exemption(self):
        s = advance(stale_assault(7))
        self.assertNotEqual([e for e in events(s, "local_decision") if e["unit_id"] == "G1"][-1]["action"], "continue")

    def test_poc12_keeps_reading_contacts_of_any_age(self):
        s = stale_assault(7)
        s = json.loads(json.dumps(s).replace('"poc-13"', '"poc-12"'))
        s = advance(s)
        self.assertEqual([e for e in events(s, "local_decision") if e["unit_id"] == "G1"][-1]["action"], "continue")


class Poc13EditionTests(unittest.TestCase):
    def test_new_games_use_poc13(self):
        from battle import scenario
        s = scenario.create()
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "little-round-top-v13"))
        self.assertEqual({u["fire_posture"] for u in s["units"]}, {"open_fire"})
        self.assertEqual(s["fire_rules"]["warning_shots_release"], False)

    def test_poc12_runs_and_saves_keep_their_digests(self):
        from unittest import mock
        from battle import engine_v12, scenario
        from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE as HOUGOUMONT
        from test_contact import at_threshold, corridor
        from test_gates import advance_through_service
        from test_gateway_push import at_the_north_gate
        from test_scenario_sides import digest, play

        self.assertEqual(digest(play(scenario.create("poc-12"))), POC12_LRT_RUN_SHA256)
        with mock.patch.object(engine_v12, "advance", wraps=engine_v12.advance) as frozen:
            save = advance_through_service(scenario.create("poc-12"), 10)
            final = advance_through_service(json.loads(json.dumps(save, sort_keys=True)), 30)
            hougoumont = advance_through_service(build_state(HOUGOUMONT, "poc-12"), 40,
                                                 (scenario.LITTLE_ROUND_TOP, HOUGOUMONT))
        self.assertEqual(frozen.call_count, final["turn"] + hougoumont["turn"])
        self.assertEqual((final["rules"], hougoumont["rules"]), ("poc-12", "poc-12"))
        self.assertEqual(digest(final), POC12_LRT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(hougoumont), POC12_HOUGOUMONT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(advance(at_the_north_gate("poc-12"), 15)), POC12_AT_THE_NORTH_GATE_SHA256)
        self.assertEqual(digest(advance(at_threshold(), 4)), POC12_STALL_SHA256)
        self.assertEqual(digest(advance(corridor(("C1", "C2", "C3")), 24)), POC12_CORRIDOR_SHA256)


# Taken at b2d93bd, before poc-13, as sha256 of the sort-keyed JSON state: the
# scripted poc-12 Little Round Top run (test_scenario_sides.play); poc-12 saves
# advanced through BattleService (Little Round Top 10 then 30 intervals, which
# ends at turn 28; Hougoumont 40, which ends at turn 29); the poc-12 north-gate
# arrangement (ends at turn 12); the crowded-courtyard stall advanced 4
# intervals; and the three-way corridor contest advanced 24 intervals.
POC12_LRT_RUN_SHA256 = "94d7f6d98da35e4dd2061a81a5600170c6b7b9b7d8eff5a96c8b66e539942ee0"
POC12_LRT_SAVE_ADVANCED_SHA256 = "d68ee8eeddb733dc35087bfdbf4bb602fdccef914062cdf2c9b3e3b967620951"
POC12_HOUGOUMONT_SAVE_ADVANCED_SHA256 = "a6ca85312b026243314c2b29b2c55bc6998c49f7ee91e886231379c60ee04ded"
POC12_AT_THE_NORTH_GATE_SHA256 = "c8276c4f9bda8ad56c9b932cee3db0eaaf4bdc032d0b580ca73a392cae5631b5"
POC12_STALL_SHA256 = "ecaa23ad5198369edbec3e08f711b7d30b4740acbc471fa9b535a7ac6bd1c396"
POC12_CORRIDOR_SHA256 = "0c8bb38f433d0914bfdd4bf8a10f85acf68d11514d2c27afbfd70cc97228de60"


if __name__ == "__main__":
    unittest.main()
