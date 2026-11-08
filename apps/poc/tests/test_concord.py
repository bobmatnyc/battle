"""Concord North Bridge, 19 April 1775: the catalog entry, its variants, the
scripted historical-order policies and the headless run. Design:
docs/research/43-concord-scenario-spec.md; comparison: docs/research/48.

No test asserts a winner: the policies issue the recorded orders and the
engine decides the outcome.
"""

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from battle import engine, grid, runtime
from battle.bootstrap import PLAYER_SCENARIOS, build_headless, build_headless_scenarios, build_replay
from battle.command_policy import SCRIPTED_POLICIES, scripted_policy
from battle.concord_policy import (
    MILITIA_ORDERS, MILITIA_POLICY, REGULARS_ORDERS, REGULARS_POLICY,
    militia_actions, regulars_actions,
)
from battle.scenario_command import COLONIAL_COMMUNICATIONS, WEAPONS_1775
from battle.scenario_concord import (
    APPROACH, BRIDGE, CONCORD_NORTH_BRIDGE as ENTRY, EAST_END, TOWN, VARIANTS, WEST_END, before,
)
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate
from battle.presentation import COLONIAL_VOICE_PROFILE


def advance(s, n=1):
    for _ in range(n):
        if s["status"] != "active":break
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def unit(s, uid):
    return next(u for u in s["units"] if u["id"] == uid)


def digest(state):
    import hashlib
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


class ConcordEntryTests(unittest.TestCase):
    def test_entry_registers_in_the_headless_catalog_after_a_dry_run(self):
        self.assertEqual(build_headless_scenarios().resolve("concord-north-bridge"), ENTRY)
        # docs/research/74: both desks draw water, the bridge and roads, so Concord is a
        # player scenario, after Little Round Top (the default) and Hougoumont.
        self.assertEqual([e.id for e in PLAYER_SCENARIOS][:3],
                         ["little-round-top", "hougoumont-north-gate", "concord-north-bridge"])
        ids = build_headless_scenarios().ids()
        self.assertEqual(len(ids), len(set(ids)), "no entry is listed twice in the headless catalog")
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        # docs/research/50: v2 has the command fire release; v1 stays buildable as ``before``.
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "concord-north-bridge-v2"))
        self.assertEqual(build_state(before(ENTRY))["scenario"], "concord-north-bridge-v1")
        self.assertEqual(s["sides"], [{"id": "provincial", "name": "Provincials", "role": "attacker"},
                                      {"id": "british", "name": "British", "role": "defender"}])
        self.assertEqual((ENTRY.date, ENTRY.start_time), ("1775-04-19", "09:25:00"))

    def test_entry_declares_command_rules_the_1775_weapons_and_voice(self):
        s = build_state(ENTRY)
        self.assertIsNotNone(ENTRY.command)
        self.assertIn("command_rules", s)
        self.assertIs(ENTRY.weapons, WEAPONS_1775)
        self.assertEqual(s["weapon_rules"], {"smoothbore muskets": dataclasses.asdict(WEAPONS_1775["smoothbore muskets"])})
        self.assertEqual({u["weapon_class"] for u in s["units"]}, {"smoothbore muskets"})
        self.assertEqual((ENTRY.communications, ENTRY.voice_profile), (COLONIAL_COMMUNICATIONS, COLONIAL_VOICE_PROFILE))

    def test_musket_range_guard_one_weapon_range_only(self):
        # The own-range threat check (tactics_v10.threat_range) does not handle
        # mixed ranges; Concord and every variant must use one range.
        for entry in [ENTRY] + [v.entry for v in VARIANTS.values()]:
            with self.subTest(entry.id):
                self.assertIs(entry.weapons, WEAPONS_1775)
                self.assertEqual(len({w.range_hexes for w in entry.weapons.values()}), 1)
                classes = {u.overrides.get("weapon_class", "rifled muskets") for u in entry.units}
                self.assertEqual(classes, set(entry.weapons))

    def test_river_is_impassable_except_at_the_bridge(self):
        s = build_state(ENTRY)
        water = [c for c in s["cells"].values() if c.get("water")]
        self.assertEqual({c["pos"][0] for c in water}, {BRIDGE[0]})
        self.assertEqual(len(water), grid.ROWS)
        self.assertEqual([c["pos"] for c in water if c.get("crossing")], [list(BRIDGE)])
        self.assertEqual(s["cells"][grid.key(list(BRIDGE))]["crossing"], "bridge")
        route = grid.path(s["cells"], [7, 4], [16, 4])
        self.assertIn(list(BRIDGE), route)

    def test_open_questions_are_labelled_and_each_alternative_is_a_variant(self):
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        for field in ("map.banks", "map.bridge", "units.british"):
            self.assertTrue(ENTRY.provenance[field].startswith("reconstruction:"), field)
        self.assertEqual(set(VARIANTS), {"british-west-bank", "planks-lifted", "two-companies"})
        for name, variant in VARIANTS.items():
            with self.subTest(name):
                self.assertEqual(variant.entry.variant, name)
                self.assertRegex(variant.source, r"S4[7-9]")
                self.assertRegex(variant.question, r"43 §6 question [123]")
                dry_run(validate(variant.entry))
                self.assertNotEqual(variant.entry.labels, ENTRY.labels)

    def test_variants_differ_from_the_entry_in_their_own_question_only(self):
        main = build_state(ENTRY)
        west = build_state(VARIANTS["british-west-bank"].entry)
        self.assertTrue(all(u["pos"][0] <= BRIDGE[0] for u in west["units"]))
        planks = build_state(VARIANTS["planks-lifted"].entry)
        key = grid.key(list(BRIDGE))
        self.assertGreater(planks["cells"][key]["move_cost"], main["cells"][key]["move_cost"])
        two = VARIANTS["two-companies"].entry
        british = [u for u in two.units if u.side == "british"]
        self.assertEqual((len(british), sum(u.overrides["initial"] for u in british)), (2, 90))
        three = [u for u in ENTRY.units if u.side == "british"]
        self.assertEqual((len(three), sum(u.overrides["initial"] for u in three)), (3, 96))

    def test_fire_postures_follow_the_recorded_orders(self):
        s = build_state(ENTRY)
        self.assertEqual({u["fire_posture"] for u in s["units"] if u["side"] == "provincial"}, {"hold_fire"})
        self.assertEqual({u["fire_posture"] for u in s["units"] if u["side"] == "british"}, {"open_fire"})


class ConcordPolicyTests(unittest.TestCase):
    def test_policies_are_registered_and_chosen_for_their_sides(self):
        self.assertIn(MILITIA_POLICY, SCRIPTED_POLICIES)
        self.assertIn(REGULARS_POLICY, SCRIPTED_POLICIES)
        self.assertEqual((scripted_policy(ENTRY, "provincial"), scripted_policy(ENTRY, "british")),
                         ("scripted-concord-militia-v1", "scripted-concord-regulars-v1"))

    def test_every_order_carries_a_source_locator(self):
        for order in MILITIA_ORDERS + REGULARS_ORDERS:
            with self.subTest(order["id"]):
                self.assertRegex(order["source"], r"S4[7-9]|doc 43")
                self.assertTrue(order["provenance"].startswith(PROVENANCE))

    def test_militia_advance_with_the_acton_company_leading(self):
        view = engine.view(build_state(ENTRY), "provincial")
        standing, orders = militia_actions(view)
        self.assertEqual(standing, [])
        self.assertEqual(orders, [{"unit_id": uid, "stance": "move", "destination": list(APPROACH[uid])}
                                  for uid in ("P1", "P2", "P3")])
        self.assertEqual(APPROACH["P1"], WEST_END)

    def test_militia_give_buttricks_fire_order_once_fired_upon(self):
        s = build_state(ENTRY)
        view = engine.view(s, "provincial")
        quiet = militia_actions(view)[1]
        self.assertNotIn("open_fire", [o["stance"] for o in quiet])
        hit = dict(next(u for u in view["units"] if u["id"] == "P1"), strength=38)
        view["units"] = [hit if u["id"] == "P1" else u for u in view["units"]]
        view["orders"] = [{"unit_id": uid, "stance": "move", "destination": list(APPROACH[uid]),
                           "status": "delivered"} for uid in APPROACH]
        orders = militia_actions(view)[1]
        self.assertEqual([(o["unit_id"], o["stance"]) for o in orders],
                         [("P1", "open_fire"), ("P2", "open_fire"), ("P3", "open_fire")])

    def test_militia_cross_once_no_fresh_british_contact_holds_the_far_end(self):
        view = engine.view(build_state(ENTRY), "provincial")
        view["orders"] = [{"unit_id": uid, "stance": s, "destination": None, "status": "delivered"}
                          for uid in APPROACH for s in ("move", "open_fire")]
        for u in view["units"]:
            u["fire_posture"] = "open_fire"
        view["units"][0]["strength"] = 30
        view["contacts"] = [{"id": "B1", "pos": [20, 10], "age": 0}]
        orders = militia_actions(view)[1]
        self.assertEqual(orders[:2], [{"unit_id": "P1", "stance": "move", "destination": list(EAST_END)},
                                      {"unit_id": "P2", "stance": "move", "destination": list(BRIDGE)}])
        view["contacts"] = [{"id": "B1", "pos": list(EAST_END), "age": 0}]
        self.assertEqual(militia_actions(view)[1], [])

    def test_regulars_guard_the_crossing_then_fall_back_to_the_town(self):
        s = build_state(ENTRY)
        view = engine.view(s, "british")
        standing, orders = regulars_actions(view)
        self.assertEqual(standing, [])
        self.assertEqual(orders, [{"unit_id": u, "stance": "hold", "destination": None} for u in ("B1", "B2", "B3")])
        view["orders"] = [{"unit_id": u, "stance": "hold", "destination": None, "status": "delivered"}
                          for u in ("B1", "B2", "B3")]
        self.assertEqual(regulars_actions(view)[1], [])
        for u in view["units"]:
            if u["id"] in ("B1", "B3"):
                u["status"] = "routed"
        orders = regulars_actions(view)[1]
        self.assertEqual(orders, [{"unit_id": "B2", "stance": "retreat", "destination": list(TOWN)}])

    def test_policies_issue_nothing_while_command_is_disrupted(self):
        view = engine.view(build_state(ENTRY), "provincial")
        view["command"]["operational"] = False
        self.assertEqual(militia_actions(view), ([], []))
        self.assertEqual(regulars_actions(view), ([], []))


class ConcordRunTests(unittest.TestCase):
    def run_once(self, tmp, name):
        db = Path(tmp) / name
        result = build_headless(db, scenario_id=ENTRY.id).run()
        final = build_replay(db).repository.load(result["game_id"])
        return result, final

    def test_headless_run_records_the_policies_and_replays_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, final = self.run_once(tmp, "concord-a.sqlite")
            second, again = self.run_once(tmp, "concord-b.sqlite")
            self.assertEqual(first["replay"]["status"], "identical")
            self.assertEqual(build_replay(Path(tmp) / "concord-a.sqlite").verify(first["game_id"])["status"],
                             "identical")
            self.assertEqual(first["run"]["player_policy"], MILITIA_POLICY)
            self.assertEqual(first["run"]["opponent"], REGULARS_POLICY)
            self.assertEqual({d.get("policy") for d in final["decisions"]}, {REGULARS_POLICY})
            # The engine draws no random number: the same inputs give the same battle.
            strip = lambda r: {k: v for k, v in r.items() if k != "game_id"}
            self.assertEqual(strip(first), strip(second))
            self.assertEqual(digest(final["events"]), digest(again["events"]))
            self.assertEqual(final["status"], "complete")
            # The recorded orders were issued and went through delivery.
            stances = {(o["side"], o["stance"]) for o in final["orders"]}
            self.assertTrue({("provincial", "move"), ("british", "hold")} <= stances)


if __name__ == "__main__":
    unittest.main()
