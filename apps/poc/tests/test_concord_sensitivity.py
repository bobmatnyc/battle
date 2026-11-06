"""Concord North Bridge geometry sensitivity (docs/research/49).

Why: doc 48 gap 11 found that the authored radius-1 ring around the bridge
favours the provincials. These tests pin the baseline run so the variants
cannot move it, and check that every sensitivity variant builds, runs and
replays. No test asserts a winner.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from battle import command_policy, concord_policy, engine, grid
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import PLAYER_SCENARIOS, build_headless, build_headless_scenarios, build_replay
from battle.concord_sensitivity import (
    BASELINE_GEOMETRY, POLICIES, SENSITIVITY, SENSITIVITY_GEOMETRY, geometry_entry, rebind, ring_banks,
)
from battle.scenario_command import WEAPONS_1775
from battle.scenario_concord import CONCORD_NORTH_BRIDGE as ENTRY, FEATURES, VARIANTS
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate

POC = Path(__file__).resolve().parent.parent
# Before docs/research/50 (the v1 entry, each company releasing itself),
# taken at d6f1748, before any sensitivity variant existed: sha256 of the
# sort-keyed JSON of the headless run summary without ``game_id`` and the
# saved final state of the baseline ``concord-north-bridge`` run.
BEFORE_RUN_SHA256 = "8755f91fab16f90beae38aa4e77aa4bba07b4ffdcc779f09aa693822bd148b79"
# The same commit: sha256 of ``scripts/concord_timeline.py`` stdout (now
# ``--before``) with the ``game_id`` value replaced by an ellipsis.
BEFORE_TIMELINE_SHA256 = "b4c03cfb5a9c4ebd9d4be9d0578d226b0d40d36361eaa23c89725044e3d3bda1"
# After docs/research/50 (the v2 entry: command fire release, hit scope), the
# same two digests of the baseline run.
AFTER_RUN_SHA256 = "8672d94d86a04fc375a56567aa029d4d59049b243523951bdaaa8a4fee2a05dd"
AFTER_TIMELINE_SHA256 = "340c2cbe33b6d94be051fab15a9385053b1d429d52ebed73ea0dc98c86f27067"
# The ``sensitivity-earshot-release`` variant: the same two digests. Taken
# after the HQ-knowledge refusals of docs/research/50; the a377ff8 values
# (b03a3d1b..., 5a8c36dc...) no longer hold, because headquarters' report
# still places P3 out of earshot when P1 is hit.
EARSHOT_RUN_SHA256 = "7d5c8fb20c64dd57cdd8f06006b35fa425981c332a8500d806b16e77329eb73d"
EARSHOT_TIMELINE_SHA256 = "1063d9afc57eea5c8856cd38d1cae4ab68c619d6b83af87e85987b70d86bb181"
GAME_ID = re.compile(r"'game_id': '[0-9a-f]+'")


def run(entry, tmp, name):
    """Run ``entry`` headless in its own database; the summary and saved state."""
    db = Path(tmp) / name
    scenarios = None if entry is ENTRY else ScenarioRegistry([entry])
    result = build_headless(db, scenario_id=entry.id, scenarios=scenarios).run()
    return result, build_replay(db).repository.load(result["game_id"]), db


def masked_timeline(seed, *args):
    """``concord_timeline.py`` stdout under ``PYTHONHASHSEED=seed``, game_id masked."""
    env = {**os.environ, "PYTHONHASHSEED": str(seed)}
    out = subprocess.run([sys.executable, str(POC / "scripts" / "concord_timeline.py"), *args], cwd=POC, env=env,
                         check=True, capture_output=True, text=True).stdout
    return GAME_ID.sub("'game_id': '…'", out)


def run_digest(entry):
    with tempfile.TemporaryDirectory() as tmp:
        result, final, _ = run(entry, tmp, "baseline.sqlite")
    summary = {k: v for k, v in result.items() if k != "game_id"}
    return hashlib.sha256(json.dumps({"result": summary, "final": final}, sort_keys=True).encode()).hexdigest()


class BaselinePinTests(unittest.TestCase):
    def test_before_entry_keeps_its_pinned_digest(self):
        from battle.scenario_concord import CONCORD_NORTH_BRIDGE_BEFORE as BEFORE
        self.assertEqual(build_state(BEFORE)["scenario"], "concord-north-bridge-v1")
        self.assertNotIn("release_by", build_state(BEFORE)["fire_rules"])
        self.assertEqual(run_digest(BEFORE), BEFORE_RUN_SHA256)

    def test_baseline_run_keeps_its_pinned_digest(self):
        self.assertEqual(run_digest(ENTRY), AFTER_RUN_SHA256)

    def test_earshot_variant_keeps_its_pinned_digest(self):
        from battle.concord_sensitivity import RELEASE_SENSITIVITY
        self.assertEqual(run_digest(RELEASE_SENSITIVITY["sensitivity-earshot-release"].entry), EARSHOT_RUN_SHA256)

    def test_baseline_timeline_is_the_same_under_two_hash_seeds(self):
        # One process has one hash seed, so a replay inside it cannot show
        # an order that depends on set or dict hashing; two processes can.
        for args, pin in (((), AFTER_TIMELINE_SHA256), (("--before",), BEFORE_TIMELINE_SHA256),
                          (("--variant", "sensitivity-earshot-release"), EARSHOT_TIMELINE_SHA256)):
            with self.subTest(args=args):
                first, second = masked_timeline(1, *args), masked_timeline(2, *args)
                self.assertEqual(first, second)
                self.assertEqual(hashlib.sha256(first.encode()).hexdigest(), pin)


class SensitivityEntryTests(unittest.TestCase):
    def test_baseline_geometry_rebuilds_the_baseline_entry(self):
        # The geometry builder is the baseline's own layout when given its
        # constants, so a variant differs only where its geometry differs.
        rebuilt = geometry_entry("baseline-check", BASELINE_GEOMETRY)
        self.assertEqual(rebuilt.map.terrain(), ENTRY.map.terrain())
        self.assertEqual(rebuilt.map.features, FEATURES)
        self.assertEqual(rebuilt.units, ENTRY.units)
        self.assertEqual(rebuilt.victory, ENTRY.victory)
        self.assertEqual(rebuilt.sides, ENTRY.sides)
        self.assertEqual(ring_banks(BASELINE_GEOMETRY), {"west": 3, "east": 1, "water": 2})

    def test_variants_are_labelled_sensitivity_and_state_what_they_keep_and_change(self):
        self.assertEqual(set(SENSITIVITY), {"sensitivity-odd-row-bridge", "sensitivity-balanced-ring",
                                            "sensitivity-balanced-ring-full"})
        self.assertFalse(set(SENSITIVITY) & set(VARIANTS))
        for name, variant in SENSITIVITY.items():
            with self.subTest(name):
                self.assertEqual(variant.entry.variant, name)
                self.assertTrue(variant.question.startswith("sensitivity:"))
                self.assertTrue(variant.reading.startswith("sensitivity:"))
                self.assertIn("keeps", variant.source)
                self.assertIn("changes", variant.reading)
                note = variant.entry.provenance["sensitivity"]
                self.assertTrue(note.startswith("authored: sensitivity:"))
                self.assertNotIn("reconstruction:", note)
                self.assertTrue(all(str(v).startswith(PROVENANCE) for v in variant.entry.provenance.values()))
                self.assertNotEqual(variant.entry.labels, ENTRY.labels)

    def test_each_variant_validates_dry_runs_and_keeps_one_musket_range(self):
        for name, variant in SENSITIVITY.items():
            with self.subTest(name):
                entry = variant.entry
                dry_run(validate(entry))
                self.assertIs(entry.weapons, WEAPONS_1775)
                self.assertEqual(len({w.range_hexes for w in entry.weapons.values()}), 1)
                self.assertEqual({u.overrides["weapon_class"] for u in entry.units}, set(entry.weapons))
                # Same forces, strengths and sides as the baseline.
                self.assertEqual([(u.id, u.overrides) for u in entry.units],
                                 [(u.id, u.overrides) for u in ENTRY.units])

    def test_variants_are_headless_only(self):
        headless = build_headless_scenarios()
        for name, variant in SENSITIVITY.items():
            with self.subTest(name):
                self.assertNotIn(variant.entry, PLAYER_SCENARIOS)
                with self.assertRaises(Exception):
                    headless.resolve(variant.entry.id)

    def test_ring_geometry_of_each_variant(self):
        expected = {"sensitivity-odd-row-bridge": {"west": 1, "east": 3, "water": 2},
                    "sensitivity-balanced-ring": {"west": 2, "east": 2, "water": 2},
                    "sensitivity-balanced-ring-full": {"west": 2, "east": 2, "water": 2}}
        for name, variant in SENSITIVITY.items():
            with self.subTest(name):
                g = SENSITIVITY_GEOMETRY[name]
                self.assertEqual(ring_banks(g), expected[name])
                s = build_state(variant.entry)
                self.assertEqual(s["objective"], list(g.bridge))
                bridge = s["cells"][grid.key(list(g.bridge))]
                self.assertEqual(bridge["crossing"], "bridge")
                # The river cuts the map: with the bridge impassable no route crosses.
                cells = {**s["cells"], grid.key(list(g.bridge)): {**bridge, "crossing": None}}
                self.assertEqual(grid.path(cells, list(g.west_end), list(g.east_end)), [])
                self.assertIn(list(g.bridge), grid.path(s["cells"], [7, 4], [16, 4]))
                # Every approach hex and start hex lies on its own bank.
                for uid, pos in g.approach.items():
                    self.assertLess(pos[0], g.river[pos[1]], uid)
                for uid, pos in g.british.items():
                    self.assertGreater(pos[0], g.river[pos[1]], uid)


class SensitivityPolicyTests(unittest.TestCase):
    def test_rebound_policies_run_the_baseline_code(self):
        for policy, fn in POLICIES.items():
            with self.subTest(policy):
                base = (concord_policy.militia_actions if policy.startswith(concord_policy.MILITIA_POLICY)
                        else concord_policy.regulars_actions)
                self.assertIs(fn.__code__, base.__code__)
                self.assertIn(policy, command_policy.SCRIPTED_POLICIES)
                self.assertIn(policy, command_policy.NAMED_POLICIES)
        # Bound to the baseline constants, the copy gives the baseline's orders.
        militia = rebind(concord_policy.militia_actions, BASELINE_GEOMETRY)
        regulars = rebind(concord_policy.regulars_actions, BASELINE_GEOMETRY)
        s = build_state(ENTRY)
        for side, fn, base in (("provincial", militia, concord_policy.militia_actions),
                               ("british", regulars, concord_policy.regulars_actions)):
            view = engine.view(s, side)
            self.assertEqual(fn(view), base(view))

    def test_each_variant_names_its_rebound_policies(self):
        for name, variant in SENSITIVITY.items():
            with self.subTest(name):
                entry = variant.entry
                self.assertEqual(command_policy.scripted_policy(entry, "provincial"),
                                 f"{concord_policy.MILITIA_POLICY}@{name}")
                self.assertEqual(command_policy.scripted_policy(entry, "british"),
                                 f"{concord_policy.REGULARS_POLICY}@{name}")
                view = engine.view(build_state(entry), "provincial")
                orders = command_policy.scripted_actions(entry.scripted["provincial"], view, "attacker")[1]
                self.assertEqual([o["destination"] for o in orders],
                                 [list(SENSITIVITY_GEOMETRY[name].approach[u]) for u in ("P1", "P2", "P3")])
                # Every geometry constant the copies read is this variant's.
                g = SENSITIVITY_GEOMETRY[name]
                for side in ("provincial", "british"):
                    bound = POLICIES[entry.scripted[side]].__globals__
                    self.assertEqual((bound["APPROACH"], bound["BRIDGE"], bound["EAST_END"], bound["TOWN"]),
                                     (g.approach, g.bridge, g.east_end, g.town))
        self.assertEqual(POLICIES[f"{concord_policy.REGULARS_POLICY}@sensitivity-odd-row-bridge"]
                         .__globals__["TOWN"], (22, 11))

    def test_rebind_refuses_a_constant_it_does_not_replace(self):
        # A later concord_policy constant (say WEST_END) would otherwise run on
        # the baseline hexes in every variant without a word.
        scope = {**vars(concord_policy), "WEST_END": (11, 10)}
        for source in ("def probe(o):\n    return WEST_END\n",
                       "def probe(o):\n    return [p for p in o if p == WEST_END]\n",
                       "def probe(o):\n    return any(p == WEST_END for p in o)\n"):
            with self.subTest(source):
                exec(source, scope)
                with self.assertRaisesRegex(ValueError, "WEST_END"):
                    rebind(scope["probe"], BASELINE_GEOMETRY)
        # A helper called by name runs on its own module's globals, so a
        # constant it reads cannot be rebound either.
        for constant in ("WEST_END", "APPROACH"):
            with self.subTest(helper_reads=constant):
                exec(f"def _helper(o):\n    return {constant}\n\ndef probe(o):\n    return _helper(o)\n", scope)
                with self.assertRaisesRegex(ValueError, constant):
                    rebind(scope["probe"], BASELINE_GEOMETRY)
        # The real policies bind: every constant they read is a hex or NON_GEOMETRY.
        self.assertEqual(len(POLICIES), 2 * len(SENSITIVITY))


class SensitivityRunTests(unittest.TestCase):
    def assert_runs_and_replays(self, name):
        entry = SENSITIVITY[name].entry
        with tempfile.TemporaryDirectory() as tmp:
            first, final, db = run(entry, tmp, "a.sqlite")
            second, again, _ = run(entry, tmp, "b.sqlite")
            self.assertEqual(first["replay"]["status"], "identical")
            self.assertEqual(build_replay(db).verify(first["game_id"])["status"], "identical")
        self.assertEqual(final["status"], "complete")
        self.assertEqual(first["run"]["scenario_id"], entry.id)
        self.assertEqual((first["run"]["player_policy"], first["run"]["opponent"]),
                         (entry.scripted["provincial"], entry.scripted["british"]))
        strip = lambda r: {k: v for k, v in r.items() if k != "game_id"}
        self.assertEqual(strip(first), strip(second))
        self.assertEqual(json.dumps(final["events"], sort_keys=True), json.dumps(again["events"], sort_keys=True))

    def test_odd_row_bridge_runs_and_replays_identically(self):
        self.assert_runs_and_replays("sensitivity-odd-row-bridge")

    def test_balanced_ring_runs_and_replays_identically(self):
        self.assert_runs_and_replays("sensitivity-balanced-ring")

    def test_balanced_ring_full_runs_and_replays_identically(self):
        self.assert_runs_and_replays("sensitivity-balanced-ring-full")


if __name__ == "__main__":
    unittest.main()
