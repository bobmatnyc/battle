"""Command fire release (``fire_rules.release_by``), docs/research/50.

Why: doc 48 §7 item 1 found that a hold-fire company at Concord released
itself; in the record Buttrick's order released the fire (S47). These tests
pin the gated engine mechanic and the old path it leaves unchanged. Fixtures
are small synthetic entries, plus the Concord baseline run. No test asserts
a winner.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from battle import engine, grid
from battle.bootstrap import build_headless, build_replay
from battle.concord_sensitivity import SENSITIVITY
from battle.scenario_concord import CONCORD_NORTH_BRIDGE as ENTRY, RELEASE_PROVENANCE, VARIANTS, before
from battle.scenario_entry import FireEntry, UnitEntry, build_state, dry_run, validate
from test_poc13b import advance, era_entry, events, unit


def fire_era(g1, release_by=None):
    """Blue holds fire: B1 commands at 5,12, B2 is 2 hexes north (in the
    1775 voice reach), B3 8 hexes south. G1 opens fire from ``g1``."""
    fire = FireEntry(default_posture="hold_fire") if release_by is None else \
        FireEntry(default_posture="hold_fire", release_by=release_by)
    units = (UnitEntry("B1", "union", "Blue command", (5, 12)),
             UnitEntry("B2", "union", "Blue front company", (5, 10)),
             UnitEntry("B3", "union", "Blue column", (5, 20)),
             UnitEntry("G1", "confederate", "Grey guard", g1, {"fire_posture": "open_fire"}))
    return build_state(dry_run(validate(dataclasses.replace(era_entry(units=units), fire=fire))))


def first(s, kind, **match):
    return next((e for e in events(s, kind) if all(e.get(k) == v for k, v in match.items())), None)


class CommandReleaseTests(unittest.TestCase):
    def test_command_releases_the_unit_and_every_hold_fire_unit_in_voice_reach(self):
        s = advance(fire_era((5, 7), "command"))
        hit = first(s, "casualties", unit_id="B2")
        self.assertEqual(hit["turn"], 1)
        orders = {o["unit_id"]: o for o in s["orders"] if o["side"] == "union"}
        self.assertEqual(sorted(orders), ["B1", "B2"])  # B3 is out of earshot.
        for o in orders.values():
            self.assertEqual((o["stance"], o["status"], o["sent_turn"], o["arrival_turn"]),
                             ("open_fire", "delivered", 1, 1))
            self.assertEqual(o["transport"]["method"], "voice")
        posture = first(s, "fire_posture_set", unit_id="B2")
        volley = first(s, "volley", unit_id="B2")
        self.assertLess(posture["seq"], volley["seq"])
        self.assertNotIn("returning_fire", volley)
        self.assertEqual((unit(s, "B2")["fire_posture"], unit(s, "B3")["fire_posture"]),
                         ("open_fire", "hold_fire"))

    def test_command_releases_a_unit_fired_upon_in_the_previous_interval(self):
        s = fire_era((5, 7), "command")
        unit(s, "G1")["ammo"] = 0  # Only last interval's losses can release B2.
        engine.emit(s, "casualties", unit_id="B2", count=1, remaining=99)
        s = advance(s)
        orders = {o["unit_id"]: o for o in s["orders"] if o["side"] == "union"}
        self.assertEqual(sorted(orders), ["B1", "B2"])
        self.assertEqual({o["sent_turn"] for o in orders.values()}, {1})
        self.assertNotIn("returning_fire", first(s, "volley", unit_id="B2"))

    def test_unit_out_of_voice_reach_keeps_its_own_release(self):
        s = advance(fire_era((5, 17), "command"))
        self.assertGreater(grid.distance(unit(s, "B1")["pos"], unit(s, "B3")["pos"]), 2)
        self.assertTrue(first(s, "volley", unit_id="B3")["returning_fire"])
        self.assertEqual([o for o in s["orders"] if o["side"] == "union"], [])
        self.assertEqual(unit(s, "B1")["fire_posture"], "hold_fire")

    def test_release_by_unit_is_the_old_path_and_stays_out_of_the_snapshot(self):
        explicit, default = fire_era((5, 7), "unit"), fire_era((5, 7))
        self.assertNotIn("release_by", explicit["fire_rules"])
        explicit, default = advance(explicit, 4), advance(default, 4)
        self.assertEqual(explicit, default)
        self.assertTrue(first(explicit, "volley", unit_id="B2")["returning_fire"])
        self.assertEqual([o for o in explicit["orders"] if o["side"] == "union"], [])

    def test_registration_refuses_an_unknown_release_by(self):
        entry = dataclasses.replace(era_entry(), fire=FireEntry(release_by="captain"))
        with self.assertRaisesRegex(ValueError, "release_by"):
            validate(entry)


class ConcordReleaseTests(unittest.TestCase):
    def test_first_provincial_release_is_a_delivered_open_fire_order_from_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "concord.sqlite"
            result = build_headless(db, scenario_id=ENTRY.id).run()
            final = build_replay(db).repository.load(result["game_id"])
        provincial = {u["id"] for u in final["units"] if u["side"] == "provincial"}
        volley = next(e for e in final["events"] if e["kind"] == "volley" and e["unit_id"] in provincial)
        self.assertNotIn("returning_fire", volley)
        posture = next(e for e in final["events"] if e["kind"] == "fire_posture_set"
                       and e["unit_id"] == volley["unit_id"])
        self.assertLess(posture["seq"], volley["seq"])
        order = next(o for o in final["orders"] if o["id"] == posture["order_id"])
        self.assertEqual((order["side"], order["stance"], order["status"]), ("provincial", "open_fire", "delivered"))
        self.assertEqual((order["sent_turn"], order["arrival_turn"]), (volley["turn"], volley["turn"]))
        self.assertEqual((order["source"], order["transport"]["method"]), ("command_release", "voice"))
        self.assertEqual(final["fire_rules"]["release_by"], "command")

    def test_every_concord_variant_inherits_the_command_release_and_keeps_a_before_form(self):
        entries = [ENTRY, *(v.entry for v in VARIANTS.values()), *(v.entry for v in SENSITIVITY.values())]
        for entry in entries:
            with self.subTest(entry=entry.id):
                self.assertEqual(entry.fire.release_by, "command")
                self.assertTrue(entry.labels["poc-13"].endswith("-v2"))
                self.assertLessEqual(set(RELEASE_PROVENANCE), set(entry.provenance))
                old = before(entry)
                dry_run(validate(old))
                self.assertEqual(old.labels["poc-13"], entry.labels["poc-13"][:-1] + "1")
                self.assertNotIn("release_by", build_state(old)["fire_rules"])
                self.assertFalse(set(RELEASE_PROVENANCE) & set(old.provenance))


if __name__ == "__main__":
    unittest.main()
