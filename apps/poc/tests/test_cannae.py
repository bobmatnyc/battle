"""Cannae, 216 BCE: the catalog entry, its defaults (D86 ruling, Bob 2026-11-07
13:10Z: doc 63 option A, the designed yield, scripted orders, sources in
parallel), its variants, the scripted controls and a short headless run with
its replay check. Plan: docs/research/63; entry and deviations: docs/research/68.

No test asserts a winner: the controls act as Polybius and Livy describe, and
the engine decides the outcome.
"""

import importlib.util
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from battle import grid
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import PLAYER_SCENARIOS, build_headless, build_headless_scenarios, build_replay
from battle.cannae_policy import (
    BACK_ROW, CARTHAGINIAN_ORDERS, POLICIES, ROMAN_ORDERS, carthaginian_actions, deserters_actions, roman_actions,
    roman_reserve_actions,
)
from battle.command_policy import SCRIPTED_POLICIES, scripted_policy
from battle.presentation import ROMAN_VOICE_PROFILE
from battle.recon import CONTACT_MAX_AGE
from battle.scenario_army import ARMY_SCALES
from battle.scenario_cannae import (
    ADVANCE_WAIT, AFRICANS, ALAE, CANNAE_ENVELOPMENT as ENTRY, CARTHAGINIAN_POLICY, CAVALRY_DELAYS, CENTRE, CRESCENT,
    D86, DEADLINE, DESERTER_TURN, EXITS, HASDRUBAL, HEAVY, LANE_COLS, LEGIONS, LIGHT_TURN, PRESS_ROW, RESERVE, RIDE,
    RIVER_COL, ROMAN_POLICY, SIGNAL_REACH, VARIANTS, VELITES, cavalry_delay_policy,
)
from battle.scenario_command import ROMAN_216_COMMUNICATIONS, TACTICS_V11
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate

POC = Path(__file__).resolve().parents[1]
FALLS = [{"unit_id": u, "stance": "retreat", "destination": [0, 3], "sent_turn": 10} for u in ("LT1", "LT2", "LT3")]


def unit(s, uid):
    return next(u for u in s["units"] if u["id"] == uid)


def differences(entry):
    """Snapshot paths in which ``entry`` differs from the default, apart from its labels."""
    a, b = build_state(entry), build_state(ENTRY)
    out = set()
    for k in set(a) | set(b):
        if k in ("scenario", "friendly_reports") or a.get(k) == b.get(k):  # Reports mirror the units.
            continue
        if k != "units":
            out.add(k)
            continue
        ua, ub = {u["id"]: u for u in a["units"]}, {u["id"]: u for u in b["units"]}
        for uid in set(ua) | set(ub):
            if uid not in ua or uid not in ub:
                out.add(f"units.{uid}")
                continue
            out |= {f"units.{uid}.{f}" for f in set(ua[uid]) | set(ub[uid]) if ua[uid].get(f) != ub[uid].get(f)}
    return out


def observation(turn, units=(), contacts=(), orders=(), operational=True):
    """A minimal commander view for the scripted controls."""
    return {"turn": turn, "command": {"operational": operational},
            "units": [dict({"status": "ready", "accepts_orders": True}, **u) for u in units],
            "contacts": [dict({"age": 0}, **c) for c in contacts], "orders": list(orders)}


def sent(uid, stance, destination, turn):
    return {"unit_id": uid, "stance": stance, "destination": destination, "sent_turn": turn}


class CannaeEntryTests(unittest.TestCase):
    def test_entry_registers_in_the_headless_catalog_after_a_dry_run(self):
        self.assertEqual(build_headless_scenarios().resolve("cannae-envelopment"), ENTRY)
        self.assertNotIn(ENTRY, PLAYER_SCENARIOS)  # Doc 63 §9 q12: headless only.
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "cannae-envelopment-v2"))  # docs/research/82: cannae-d38.
        self.assertEqual(s["sides"], [{"id": "roman", "name": "Roman", "role": "attacker"},
                                      {"id": "carthaginian", "name": "Carthaginian", "role": "defender"}])
        self.assertEqual((ENTRY.start_time, ENTRY.player, s["commanders"]["roman"]["unit_id"]),
                         ("08:00:00", "roman", "SC1"))

    def test_entry_takes_every_doc_63_default(self):
        s = build_state(ENTRY)
        # Doc 63 §8 rows 1-5: option A, the unchanged grid, 08:00 to 16:00.
        self.assertEqual((ENTRY.map.metres_per_hex, ENTRY.seconds_per_turn, ENTRY.map.cols, ENTRY.map.rows),
                         (200, 180, 24, 21))
        self.assertIn((200, 180), ARMY_SCALES)
        self.assertEqual((s["max_turns"], DEADLINE * 180), (160, 8 * 3600))
        # Rows 6-7: 23 Roman and 18 Carthaginian units with doc 63's strengths.
        strengths = {u["id"]: u["initial"] for u in s["units"]}
        self.assertEqual(len(s["units"]), 41)
        self.assertEqual([strengths[u] for u in HEAVY], [3550] * 16)
        self.assertEqual([strengths[u] for u in VELITES], [3500] * 4)
        self.assertEqual([strengths[u] for u in ("EQ", "SC1", "SC2")], [1600, 2400, 2400])
        self.assertEqual([strengths[u] for u in AFRICANS + CENTRE], [5000] * 2 + [2750] * 8)
        self.assertEqual([strengths[u] for u in ("LT1", "LT2", "LT3")], [2670] * 3)
        self.assertEqual([strengths[u] for u in HASDRUBAL + ("NU1", "NU2")], [2170] * 3 + [1750] * 2)
        self.assertEqual(sum(strengths[u] for u in AFRICANS + CENTRE + ("LT1", "LT2", "LT3")), 40010)
        # Row 8: the block 8 wide, 2 deep, legions in front.
        rows = {u["id"]: u["pos"] for u in s["units"]}
        self.assertEqual({rows[u][1] for u in LEGIONS}, {11})
        self.assertEqual({rows[u][1] for u in ALAE}, {12})
        self.assertEqual(sorted(rows[u][0] for u in LEGIONS), list(range(13, 21)))
        # Rows 9-10: the crescent one hex ahead; 3 hexes from the Roman front to the crescent.
        self.assertEqual({rows[u][1] for u in CRESCENT}, {8})
        self.assertEqual({rows[u][1] for u in CENTRE if u not in CRESCENT}, {7})
        self.assertEqual(11 - 8, 3)
        for af, end in (("AF1", "C1"), ("AF2", "C8")):  # The Africans one hex behind each end of the centre.
            self.assertEqual((grid.distance(rows[af], rows[end]), rows[af][1]), (1, rows[end][1] - 1))
        # Row 11: the river lane, 2 hexes, and the impassable river.
        self.assertEqual((LANE_COLS, RIVER_COL), ((21, 22), 23))
        self.assertTrue(all(s["cells"][grid.key([RIVER_COL, r])]["water"] for r in range(21)))
        self.assertEqual(rows["EQ"][0], 21)
        # Rows 12-14, 16: weapons, cavalry speed 3, sight 7, voice 1, messenger at the engine rates.
        self.assertEqual({k: (w.range_hexes, w.effect_pct) for k, w in ENTRY.weapons.items()},
                         {"heavy infantry": (1, 100), "light infantry": (1, 40), "heavy cavalry": (1, 100),
                          "light cavalry": (1, 40)})
        self.assertEqual({unit(s, u).get("move_rate", 1) for u in ("EQ", "SC1", "SC2") + HASDRUBAL + ("NU1", "NU2")},
                         {3})
        self.assertEqual({unit(s, u).get("move_rate", 1) for u in HEAVY + VELITES + CENTRE}, {1})
        self.assertTrue(all("observation_range" not in u for u in s["units"]))  # The 7-hex cap.
        self.assertEqual((ENTRY.voice_reach, SIGNAL_REACH, ENTRY.tactics), (1, 6, TACTICS_V11))
        self.assertEqual((ENTRY.communications, ENTRY.voice_profile), (ROMAN_216_COMMUNICATIONS, ROMAN_VOICE_PROFILE))
        # Rows 18-21: the doctrines.
        for uid in CENTRE:
            self.assertEqual(unit(s, uid)["yield"], {"limit": 3, "rear_step": -1}, uid)
        for uid in AFRICANS:
            self.assertEqual(unit(s, uid)["wheel"], {"reach": 2, "front_row": 6, "rear_step": -1}, uid)
        for uid in HEAVY:
            u = unit(s, uid)
            self.assertEqual(u["exploit"], {"trigger": "arrival", "press_to": [u["pos"][0], PRESS_ROW],
                                            "recall_binding": False, "max_loss_pct": 50}, uid)
        # Rows 22-25: the victory.
        v = s["victory"]
        self.assertEqual((v["kind"], v["zoc"], v["centre_break"], v["enclosed_needed"]),
                         ("encircle", 1, 5, 16 * 3550 // 2))
        self.assertEqual(v["exits"], [list(p) for p in EXITS.values()])
        self.assertTrue(all(p[1] == 20 for p in EXITS.values()))  # On the Roman edge.
        self.assertEqual((v["pocket_units"], v["centre_units"]), (list(HEAVY), list(CENTRE)))

    def test_every_open_value_is_labelled_with_the_d86_provenance(self):
        self.assertEqual(D86, "D86 (Bob 2026-11-07 13:10Z): doc 63 defaults")
        for key in ("start_time", "deadline", "scale", "player_side", "scope", "sources_pass", "hierarchy", "army",
                    "signal"):
            self.assertIn(D86, ENTRY.provenance[key], key)
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        source = (POC / "battle" / "scenario_cannae.py").read_text()
        self.assertIn("# D86 (Bob 2026-11-07 13:10Z): doc 63 defaults", source)

    def test_the_designed_yield_is_c1_and_no_design_drops_it(self):
        self.assertEqual(differences(VARIANTS["no-design"].entry), {f"units.{u}.yield" for u in CENTRE})

    def test_each_named_variant_differs_only_in_its_own_question(self):
        expect = {
            "no-design": {f"units.{u}.yield" for u in CENTRE},
            "one-wing-fixed-af1": {"units.AF1.wheel"},
            "one-wing-fixed-af2": {"units.AF2.wheel"},
            "roman-reserve": {"units.A7.pos", "units.A8.pos", "units.A7.exploit", "units.A8.exploit", "units.A7.name",
                              "units.A8.name"},
            "aemilius-commands": {"commanders", "hq"},
            "roman-horse-holds": {f"units.{u}.{f}" for u in ("EQ", "SC1", "SC2")
                                  for f in ("initial", "strength", "ammo")},
            "dust": {f"units.{u}.observation_range" for u in HEAVY + VELITES + ("EQ", "SC1", "SC2")},
            "deserters": {"units.ND"},
            "zoc-0": {"victory"},
        }
        for name, paths in expect.items():
            with self.subTest(name):
                self.assertEqual(differences(VARIANTS[name].entry), paths)
        for d in CAVALRY_DELAYS:
            entry = VARIANTS[f"cavalry-delayed-{d}"].entry
            self.assertEqual((differences(entry), entry.scripted["carthaginian"]), (set(), cavalry_delay_policy(d, 2)))
        self.assertIn("units.L2.pos", differences(VARIANTS["wide-front"].entry))
        for name, v in VARIANTS.items():
            dry_run(validate(v.entry))
            self.assertEqual(v.entry.id, f"cannae-envelopment-{name}")

    def test_policies_are_registered_and_chosen_for_their_sides(self):
        for policy in POLICIES:
            self.assertIn(policy, SCRIPTED_POLICIES)
        self.assertEqual((scripted_policy(ENTRY, "roman"), scripted_policy(ENTRY, "carthaginian")),
                         (ROMAN_POLICY, CARTHAGINIAN_POLICY))


class CannaePolicyTests(unittest.TestCase):
    def test_every_order_carries_a_source_locator_or_a_label(self):
        for order in ROMAN_ORDERS + CARTHAGINIAN_ORDERS:
            self.assertTrue(order["source"].startswith(("S65", "S66", "S67", "authored:")), order["id"])
            self.assertTrue(order["provenance"].startswith(PROVENANCE), order["id"])

    def test_the_light_troops_fall_back_then_the_heavy_infantry_advances_once(self):
        s = build_state(ENTRY)
        units = [dict(u) for u in s["units"] if u["side"] == "roman"]
        self.assertEqual(roman_actions(observation(LIGHT_TURN - 1, units)), ([], []))
        _, first = roman_actions(observation(LIGHT_TURN, units))
        self.assertEqual(first, [{"unit_id": v, "stance": "retreat", "destination": [unit(s, v)["pos"][0], BACK_ROW["roman"]]}
                                 for v in VELITES[:3]])
        retreats = [sent(v, "retreat", [0, 15], LIGHT_TURN) for v in VELITES]
        self.assertEqual(roman_actions(observation(LIGHT_TURN + 1, units, orders=retreats)), ([], []))  # Not cleared.
        cleared = [dict(u, pos=[u["pos"][0], 15]) if u["id"] in VELITES else u for u in units]
        _, advance = roman_actions(observation(LIGHT_TURN + 1, cleared, orders=retreats))
        self.assertEqual([o["unit_id"] for o in advance], list(LEGIONS[:3]))
        self.assertEqual(advance[0], {"unit_id": "L1", "stance": "move", "destination": [13, 10]})
        _, late = roman_actions(observation(LIGHT_TURN + ADVANCE_WAIT, units, orders=retreats))
        self.assertEqual([o["unit_id"] for o in late], list(LEGIONS[:3]))  # The wait ends it.
        everyone = retreats + [sent(u, "move", [0, 0], LIGHT_TURN + 1) for u in HEAVY]
        self.assertEqual(roman_actions(observation(LIGHT_TURN + 20, cleared, orders=everyone)), ([], []))
        reserve = [sent(u, "move", [0, 0], LIGHT_TURN + 1) for u in HEAVY if u not in RESERVE]
        self.assertEqual(roman_reserve_actions(observation(LIGHT_TURN + 20, cleared, orders=retreats + reserve)),
                         ([], []))
        self.assertEqual(roman_actions(observation(LIGHT_TURN, units, operational=False)), ([], []))

    def _carthaginians(self):
        s = build_state(ENTRY)
        return [dict(u) for u in s["units"] if u["side"] == "carthaginian"]

    def test_hasdrubal_rides_only_after_the_roman_right_cavalry_leaves_the_view(self):
        units, eq = self._carthaginians(), {"id": "EQ", "pos": [21, 11]}
        falls = [sent(u, "retreat", [0, 3], LIGHT_TURN) for u in ("LT1", "LT2", "LT3")]
        rides = lambda orders: [o for o in orders if o["unit_id"] in HASDRUBAL]
        no_ride = lambda orders: [o for o in rides(orders) if o["destination"] == list(RIDE[o["unit_id"]])]
        self.assertEqual(no_ride(carthaginian_actions(observation(30, units, [eq], falls))[1]), [])  # D34: it pursues.
        self.assertEqual(rides(carthaginian_actions(observation(CONTACT_MAX_AGE + 1, units, [], falls))[1]), [])
        gone = carthaginian_actions(observation(CONTACT_MAX_AGE + 2, units, [], falls))[1]
        routed = carthaginian_actions(observation(3, units, [dict(eq, routed=True)], falls))[1]
        want = [{"unit_id": u, "stance": "move", "destination": list(RIDE[u])} for u in HASDRUBAL]
        self.assertEqual((rides(gone), rides(routed)), (want, want))
        ridden = falls + [sent(u, "move", list(RIDE[u]), 20) for u in HASDRUBAL]
        self.assertEqual(rides(carthaginian_actions(observation(21, units, [], ridden))[1]), [])

    def test_the_horse_pursues_the_roman_right_cavalry_while_it_is_in_view_and_unrouted(self):
        # D34 (Bob 2026-11-08 14:22Z): Cannae ride fix option (i), policy only; the Dd8 q5 view rule is unchanged.
        units, eq = self._carthaginians(), {"id": "EQ", "pos": [21, 11]}
        horse = lambda orders: [o for o in orders if o["unit_id"] in HASDRUBAL]
        pursue = lambda pos: [{"unit_id": u, "stance": "move", "destination": pos} for u in HASDRUBAL]
        ride = [{"unit_id": u, "stance": "move", "destination": list(RIDE[u])} for u in HASDRUBAL]
        # In view and unrouted: each horse unit is sent to EQ's reported hex, once per reported hex.
        self.assertEqual(horse(carthaginian_actions(observation(3, units, [eq]))[1]), pursue([21, 11]))
        chased = [sent(u, "move", [21, 11], 3) for u in HASDRUBAL]
        self.assertEqual(horse(carthaginian_actions(observation(4, units, [eq], chased))[1]), [])
        moved = dict(eq, pos=[21, 13], age=2)
        self.assertEqual(horse(carthaginian_actions(observation(6, units, [moved], chased))[1]), pursue([21, 13]))
        # Out of view: no pursuit; before interval 8 nothing, after it the ride, even after a pursuit.
        self.assertEqual(horse(carthaginian_actions(observation(3, units))[1]), [])
        self.assertEqual(horse(carthaginian_actions(observation(CONTACT_MAX_AGE + 2, units, [], FALLS + chased))[1]),
                         ride)
        # Routed: no pursuit; the ride, even after a pursuit.
        self.assertEqual(horse(carthaginian_actions(observation(9, units, [dict(eq, routed=True)], FALLS + chased))[1]),
                         ride)
        # After a pursuit and the ride, the charge still follows the arrival.
        ridden = FALLS + chased + [sent(u, "move", list(RIDE[u]), 20) for u in HASDRUBAL]
        there = [dict(u, pos=list(RIDE["HC1"])) if u["id"] == "HC1" else u for u in units]
        rear = [{"id": "A3", "pos": [15, 12]}]
        self.assertEqual(carthaginian_actions(observation(25, there, rear, ridden))[1],
                         [{"unit_id": "HC1", "stance": "move", "destination": [15, 12]}])
        # The ride is not interrupted by EQ coming back into view.
        self.assertEqual(horse(carthaginian_actions(observation(21, units, [eq], ridden))[1]), [])

    def test_the_charge_follows_a_reported_arrival_and_targets_the_roman_rear(self):
        units = self._carthaginians()
        ridden = FALLS + [sent(u, "move", list(RIDE[u]), 20) for u in HASDRUBAL]
        rear = [{"id": "A3", "pos": [15, 12]}, {"id": "A5", "pos": [17, 12]}, {"id": "L4", "pos": [16, 9]},
                {"id": "A1", "pos": [13, 11]}, {"id": "V1", "pos": [13, 15]}]
        self.assertEqual(carthaginian_actions(observation(25, units, rear, ridden))[1][:1], [])  # Not yet there.
        there = [dict(u, pos=list(RIDE["HC1"])) if u["id"] == "HC1" else u for u in units]
        _, charge = carthaginian_actions(observation(25, there, rear, ridden))
        self.assertEqual(charge, [{"unit_id": "HC1", "stance": "move", "destination": [15, 12]},
                                  {"unit_id": "HC2", "stance": "move", "destination": [17, 12]},
                                  {"unit_id": "HC3", "stance": "move", "destination": [13, 11]}])
        charged = ridden + [sent(o["unit_id"], "move", o["destination"], 25) for o in charge]
        self.assertFalse([o for o in carthaginian_actions(observation(26, there, rear, charged))[1]
                          if o["unit_id"] in HASDRUBAL])

    def test_a_cavalry_delay_holds_the_ride_for_its_intervals(self):
        units, delayed = self._carthaginians(), POLICIES[cavalry_delay_policy(10)]  # v1: HC1 only.
        rides = lambda orders: [o for o in orders if o["unit_id"] in HASDRUBAL]
        self.assertEqual(rides(delayed(observation(20, units, orders=FALLS))[1]),
                         [{"unit_id": "HC1", "stance": "hold", "destination": None}])
        held = FALLS + [sent("HC1", "hold", None, 20)]
        self.assertEqual(rides(delayed(observation(29, units, orders=held))[1]), [])
        self.assertEqual([o["destination"] for o in rides(delayed(observation(30, units, orders=held))[1])],
                         [list(RIDE[u]) for u in HASDRUBAL])

    def test_the_deserters_open_fire_then_attack_the_roman_rear(self):
        units = [dict(u) for u in build_state(VARIANTS["deserters"].entry)["units"] if u["side"] == "carthaginian"]
        self.assertFalse([o for o in deserters_actions(observation(DESERTER_TURN - 1, units))[1] if o["unit_id"] == "ND"])
        first = deserters_actions(observation(DESERTER_TURN, units))[1]
        self.assertEqual(first[0], {"unit_id": "ND", "stance": "open_fire", "destination": None})
        then = deserters_actions(observation(DESERTER_TURN + 1, units, [{"id": "A2", "pos": [14, 12]}],
                                             [sent("ND", "open_fire", None, DESERTER_TURN)]))[1]
        self.assertEqual(then[0], {"unit_id": "ND", "stance": "move", "destination": [14, 12]})


class CannaeRunTests(unittest.TestCase):
    def test_a_short_headless_run_replays_identically_and_summarises(self):
        """Twelve intervals of the default (the deadline moved, nothing else), through
        the runs script's own path: BatchStore, the closing replay check, the summary."""
        spec = importlib.util.spec_from_file_location("cannae_runs", POC / "scripts" / "cannae_runs.py")
        runs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runs)
        short = replace(ENTRY, victory=replace(ENTRY.victory, deadline_turns=12))
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cannae.sqlite"
            result = build_headless(db, scenario_id=short.id, scenarios=ScenarioRegistry([short]), keyframe_every=0).run()
            final = build_replay(db).repository.load(result["game_id"])
        row = runs.summarise("short", short, result, final, 0.0)
        self.assertEqual((row["replay"], row["turn"], row["time"]), ("identical", 12, "08:36:00"))
        self.assertEqual(len(final["victory"]["record"]), 12)
        self.assertIn(row["winner"], ("roman", "carthaginian"))
        self.assertEqual((row["edition"], row["broke_through"]), ("cannae-d38", {}))  # docs/research/82 Q3.
        self.assertEqual(sorted(runs.ENTRIES), sorted(["default", *VARIANTS]))


if __name__ == "__main__":
    unittest.main()
