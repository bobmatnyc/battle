"""Pegasus Bridge, 6 June 1944: the catalog entry, its variants, the scripted
policies and the headless run. Plan: docs/research/52; runs: docs/research/54.

No test asserts a winner: the policies issue the orders the sources describe
or doc 52 infers, and the engine decides the outcome.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from battle import engine, grid
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import PLAYER_SCENARIOS, build_headless, build_headless_scenarios, build_replay
from battle.command_policy import SCRIPTED_POLICIES, scripted_policy
from battle.pegasus_policy import (
    ALARM_TURNS, BRITISH_ORDERS, GERMAN_ORDERS, coup_de_main_actions, early_alarm_actions, guard_actions,
)
from battle.presentation import WWII_VOICE_PROFILE
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate
from battle.scenario_pegasus import (
    BRITISH_POLICY, CANAL, CANAL_WEST, CANAL_WEST_N, CROSSED_SENSITIVITY, EARLY_ALARM_POLICY, GUARD_POLICY,
    ON_CONTACT, ORNE, PEGASUS_BRIDGE as ENTRY, RANGE_SENSITIVITY, RELIEF_TURN, VARIANTS,
)
from battle.scenario_wwii import RADIO_COMMUNICATIONS

# sha256 of the sort-keyed JSON of the baseline headless run summary without
# ``game_id`` and its saved final state, taken on EVO at the commit that adds
# the entry (docs/research/54). Re-pinned in the D2 fix round: 24 Platoon's
# unit record gained ``clears_charges``; the ee9dd07 value was 57669556....
BASELINE_RUN_SHA256 = "3f3d755155902086f5f0ed76cfb1591b0e601721c305fa9e2c5a9ff2ca47f367"


def run(entry, tmp, name="pegasus.sqlite"):
    db = Path(tmp) / name
    scenarios = None if entry is ENTRY else ScenarioRegistry([entry])
    result = build_headless(db, scenario_id=entry.id, scenarios=scenarios).run()
    return result, build_replay(db).repository.load(result["game_id"])


def run_digest(entry):
    with tempfile.TemporaryDirectory() as tmp:
        result, final = run(entry, tmp)
    summary = {k: v for k, v in result.items() if k != "game_id"}
    return hashlib.sha256(json.dumps({"result": summary, "final": final}, sort_keys=True).encode()).hexdigest()


class PegasusEntryTests(unittest.TestCase):
    def test_entry_registers_in_the_headless_catalog_after_a_dry_run(self):
        self.assertEqual(build_headless_scenarios().resolve("pegasus-bridge"), ENTRY)
        # docs/research/75: both desks draw the canal, the bridges and the charges, so Pegasus is
        # a player scenario, after Concord, and its German side plays its scripted control there.
        self.assertIn(ENTRY, PLAYER_SCENARIOS)
        self.assertTrue(ENTRY.desk_scripted_opponent)
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "pegasus-bridge-v1"))
        self.assertEqual(s["sides"], [{"id": "british", "name": "British", "role": "attacker"},
                                      {"id": "german", "name": "German", "role": "defender"}])
        self.assertEqual((ENTRY.date, ENTRY.start_time), ("1944-06-06", "00:25:00"))

    def test_entry_declares_the_1944_rules_on_the_canal_bridge_only(self):
        s = build_state(ENTRY)
        self.assertEqual([(b.id, b.pos, b.state, b.demolition) for b in ENTRY.bridges],
                         [("canal-bridge", CANAL, "charges", ON_CONTACT)])
        self.assertEqual(ON_CONTACT.trigger, "contact")
        self.assertEqual([x.codeword for x in ENTRY.signals], ["Ham"])
        self.assertEqual({u["observation_range"] for u in s["units"]}, {2})
        self.assertEqual({u["weapon_class"] for u in s["units"]}, set(ENTRY.weapons))
        self.assertEqual({w.range_hexes for w in ENTRY.weapons.values()}, {2})
        self.assertEqual((ENTRY.communications, ENTRY.voice_profile), (RADIO_COMMUNICATIONS, WWII_VOICE_PROFILE))
        self.assertEqual((s["victory"]["kind"], s["victory"]["relief_turn"], s["max_turns"]),
                         ("seize-and-hold", RELIEF_TURN, RELIEF_TURN))
        self.assertEqual(RELIEF_TURN * 30, 3 * 3600)  # S51: about 3 hours after landing.
        self.assertEqual(s["bridge_demolition"][0]["bridge_id"], "canal-bridge")
        # Only 24 Platoon carries sappers (S52 sheet 2); every other unit lacks the key.
        self.assertEqual([u["id"] for u in s["units"] if u.get("clears_charges")], ["D24"])
        self.assertTrue(ENTRY.provenance["units.sappers"].startswith("sourced:"))

    def test_waterways_are_impassable_except_at_the_bridges_and_each_ring_is_balanced(self):
        s = build_state(ENTRY)
        crossings = sorted(c["pos"] for c in s["cells"].values() if c.get("water") and c.get("crossing"))
        self.assertEqual(crossings, [list(CANAL), list(ORNE)])
        self.assertEqual(grid.distance(CANAL, ORNE), 10)
        for bridge in (CANAL, ORNE):
            ring = [s["cells"][grid.key(p)] for p in grid.neighbors(list(bridge))]
            west = [c for c in ring if not c.get("water") and c["pos"][0] < bridge[0]]
            east = [c for c in ring if not c.get("water") and c["pos"][0] >= bridge[0]]
            self.assertEqual((len(west), len(east)), (2, 2), bridge)
        self.assertIn(list(CANAL), grid.path(s["cells"], [12, 12], [4, 10]))

    def test_inferred_items_are_labelled_and_every_basis_carries_a_kind(self):
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        for field in ("german.mission", "bridge", "demolition", "alarm"):
            self.assertTrue(ENTRY.provenance[field].startswith("inferred:"), field)
        self.assertTrue(ENTRY.provenance["relief"].startswith("sourced:"))
        self.assertIn("that the holder sees", ENTRY.provenance["signals"])
        self.assertTrue(ON_CONTACT.basis.startswith("inferred:"))

    def test_each_named_variant_differs_in_its_own_question(self):
        self.assertEqual(set(VARIANTS), {"both-bridges", "orne-platoons", "guard-only", "demolish-on-crossing",
                                         "relief-1h", "no-relief", "early-alarm"})
        for name, variant in VARIANTS.items():
            with self.subTest(name):
                self.assertEqual(variant.entry.variant, name)
                self.assertRegex(variant.question, r"doc 52 §(9|10)")
                dry_run(validate(variant.entry))
                self.assertNotEqual(variant.entry.labels, ENTRY.labels)
        both = build_state(VARIANTS["both-bridges"].entry)
        self.assertEqual(both["victory"]["objectives"], [list(CANAL), list(ORNE)])
        self.assertEqual([x.codeword for x in VARIANTS["both-bridges"].entry.signals], ["Ham", "Jam"])
        orne = VARIANTS["orne-platoons"].entry
        self.assertEqual(orne.victory.objective, ORNE)
        self.assertEqual(sum(u.overrides["initial"] for u in orne.units if u.id.startswith("G") and u.id != "GHQ"), 12)
        self.assertIsNone(VARIANTS["guard-only"].entry.bridges[0].demolition)
        self.assertEqual(VARIANTS["demolish-on-crossing"].entry.bridges[0].demolition.trigger, "crossing")
        self.assertEqual(VARIANTS["relief-1h"].entry.victory.relief_turn, 120)
        no_relief = VARIANTS["no-relief"].entry.victory
        self.assertEqual((no_relief.relief_turn, no_relief.deadline_turns), (None, 480))
        self.assertEqual(VARIANTS["early-alarm"].entry.scripted["german"], EARLY_ALARM_POLICY)
        guard = sum(u.overrides["initial"] for u in VARIANTS["both-bridges"].entry.units if u.id.startswith("G")
                    and u.id != "GHQ")
        self.assertEqual(guard, 50)  # S51 p. 1 para 2, S54.

    def test_sensitivity_entries_keep_one_weapon_range_and_are_in_no_catalog(self):
        for hexes in (1, 3):
            entry = RANGE_SENSITIVITY[f"range-{hexes}"].entry
            self.assertEqual({w.range_hexes for w in entry.weapons.values()}, {hexes})
        catalog = set(build_headless_scenarios().ids())
        self.assertIn(ENTRY.id, catalog)
        for name, variant in {**RANGE_SENSITIVITY, **CROSSED_SENSITIVITY}.items():
            with self.subTest(name):
                dry_run(validate(variant.entry))
                self.assertTrue(variant.entry.provenance["sensitivity"].startswith("authored: sensitivity:"))
                self.assertNotIn(variant.entry.id, catalog)
                self.assertNotIn(variant.entry, PLAYER_SCENARIOS)


class PegasusPolicyTests(unittest.TestCase):
    def test_policies_are_registered_and_chosen_for_their_sides(self):
        for policy in (BRITISH_POLICY, GUARD_POLICY, EARLY_ALARM_POLICY):
            self.assertIn(policy, SCRIPTED_POLICIES)
        self.assertEqual((scripted_policy(ENTRY, "british"), scripted_policy(ENTRY, "german")),
                         (BRITISH_POLICY, GUARD_POLICY))

    def test_every_order_carries_a_source_locator_or_an_inferred_label(self):
        for order in BRITISH_ORDERS + GERMAN_ORDERS:
            with self.subTest(order["id"]):
                self.assertRegex(order["source"], r"S5[0-6]|^inferred:")
                self.assertTrue(order["provenance"].startswith(PROVENANCE))

    def test_british_platoons_get_their_tasks_then_dig_in_once_ham_arrives(self):
        view = engine.view(build_state(ENTRY), "british")
        standing, orders = coup_de_main_actions(view)
        self.assertEqual(standing, [])
        self.assertEqual(orders, [{"unit_id": "D25", "stance": "move", "destination": list(CANAL_WEST)},
                                  {"unit_id": "D24", "stance": "move", "destination": list(CANAL)},
                                  {"unit_id": "B14", "stance": "move", "destination": list(CANAL_WEST_N)}])
        view["orders"] = [dict(o, id=f"o{i}") for i, o in enumerate(orders)]
        for u in view["units"]:
            u["pos"] = {"D25": list(CANAL_WEST), "B14": list(CANAL_WEST_N)}.get(u["id"], u["pos"])
        self.assertEqual(coup_de_main_actions(view)[1], [])  # No codeword yet: no digging.
        view["signals"] = [{"codeword": "Ham", "bridge": "canal-bridge", "sent_turn": 11, "delivered_turn": 12}]
        self.assertEqual(coup_de_main_actions(view)[1], [{"unit_id": "D25", "stance": "dig_in", "destination": None},
                                                         {"unit_id": "B14", "stance": "dig_in", "destination": None}])

    def test_reserve_moves_at_the_alarm_turn_and_early_in_the_variant(self):
        view = engine.view(build_state(ENTRY), "german")
        view["turn"] = ALARM_TURNS["R1"] - 1
        self.assertEqual(guard_actions(view), ([], []))
        view["turn"] = ALARM_TURNS["R1"] + 1
        self.assertEqual(guard_actions(view)[1], [{"unit_id": "R1", "stance": "move", "destination": list(CANAL_WEST)}])
        view["turn"] = 3
        self.assertEqual([o["unit_id"] for o in early_alarm_actions(view)[1]], ["R1", "R2"])
        self.assertEqual(early_alarm_actions(view)[1][1]["destination"], list(CANAL_WEST_N))

    def test_policies_issue_nothing_while_command_is_disrupted(self):
        for side, policy in (("british", coup_de_main_actions), ("german", early_alarm_actions)):
            view = engine.view(build_state(ENTRY), side)
            view["turn"] = 300
            view["command"]["operational"] = False
            self.assertEqual(policy(view), ([], []), side)


class PegasusRunTests(unittest.TestCase):
    def test_headless_run_records_the_policies_and_replays_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, final = run(ENTRY, tmp)
        self.assertEqual(result["replay"]["status"], "identical")
        self.assertEqual((result["run"]["player_policy"], result["run"]["opponent"]), (BRITISH_POLICY, GUARD_POLICY))
        self.assertEqual(final["scenario"], "pegasus-bridge-v1")

    def test_baseline_run_keeps_its_pinned_digest(self):
        self.assertEqual(run_digest(ENTRY), BASELINE_RUN_SHA256)

    def test_a_held_bridge_run_sends_ham_by_report_and_replays_identically(self):
        # The guard-only bridge with relief at one hour: a short run in which
        # the codeword path, the reserve alarm and the relief clause all run.
        entry = CROSSED_SENSITIVITY["guard-only+relief-1h"].entry
        with tempfile.TemporaryDirectory() as tmp:
            result, final = run(entry, tmp)
        self.assertEqual(result["replay"]["status"], "identical")
        sent = [e for e in final["events"] if e["kind"] == "signal_sent"]
        for heard in final["signals_received"]["british"]:
            self.assertGreater(heard["delivered_turn"], heard["sent_turn"])
            self.assertIn((heard["codeword"], heard["sent_turn"]), {(e["codeword"], e["turn"]) for e in sent})
        self.assertEqual(final["signals_received"]["german"], [])


if __name__ == "__main__":
    unittest.main()
