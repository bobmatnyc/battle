"""Army-scale rules (docs/research/63 §10, 68): declared scale, per-unit speed,
army-scale fire and morale, flank and rear, the yield and wheel doctrines, the
two 216 BCE profiles and the ``encircle`` victory kind. Every rule is off unless
an entry declares it; the last test pins every saved poc-13 entry's play.
"""

import hashlib
import json
import unittest
from dataclasses import replace

from battle import army, engine, grid, recon, victory
from battle.bootstrap import HEADLESS_SCENARIOS
from battle.comms import PROFILES
from battle.scenario_army import ArmyEntry
from battle.scenario_cannae import ARMY, CANNAE_ENVELOPMENT as ENTRY, HEAVY_INFANTRY, LIGHT_INFANTRY
from battle.scenario_command import CARTHAGE_216_COMMUNICATIONS, ROMAN_216_COMMUNICATIONS, WWI_COMMUNICATIONS
from battle.scenario_entry import MapEntry, UnitEntry, build_state, validate
from battle.victory_encircle import enclosure
from test_pegasus_engine import advance

# Every poc-13 headless entry after 40 engine-only intervals, recorded at 5704c40
# (before the army-scale rules): the rules are opt-in, so these must not move.
RECORDED = {
    "little-round-top": "2de7dd04565fdb202749d0fcc8272cfc9630878f2735802c1b5f79d6b5dbe305",
    "hougoumont-north-gate": "c419bdb263f092a6bf8cc14460bc174a044fcfa64c1163e225739a2d0f6375ad",
    "concord-north-bridge": "7b1513109b32eee6893bda64980f3139e11ac0c8b3fd40a532d6a9558b67bfe9",
    "concord-north-bridge-v1": "b1e3a7dc4a570618b15ae5c33c9056bbe3cb608366e0f5a4993ef5f61e31de9e",
    "pegasus-bridge": "793f482a9b2767fd62757764789cbdb0e5930bc9d57bf825468e37ad0b5ced95",
    "hill-223-patrol": "6974db68984ac4a637279ff2c9c66aac779c4c21efe7aeee50d11f38493d4432",
    "gergovia-recall": "2229a151d8ecad5467d85f503197c810f61c7e6ead554e27446ed397449aee3b",
}
KEEP = ("SC1", "C4")  # The two command detachments; reports need a recipient.


def unit(s, uid):
    return next(u for u in s["units"] if u["id"] == uid)


def field(*placed):
    """A Cannae snapshot holding only the command detachments, far off, and
    ``placed`` ((id, hex), ...), scored by a hold-objective that never ends."""
    s = build_state(ENTRY)
    wanted = dict(placed)
    s["units"] = [u for u in s["units"] if u["id"] in wanted or u["id"] in KEEP]
    for u in s["units"]:
        u["pos"] = list(wanted.get(u["id"], (0, 20) if u["side"] == "roman" else (0, 0)))
        u.update(target=None, stance="hold", mission_result=None)
        u.pop("exploit", None)
    for side in s["friendly_reports"]:
        s["friendly_reports"][side] = {u["id"]: dict(u, observed_turn=0, received_turn=0)
                                       for u in s["units"] if u["side"] == side}
    s["victory"] = {"kind": "hold-objective", "radius": 0, "hold_turns": 999, "objective_name": "x"}
    s["max_turns"] = 999
    return s


def volleys(s, uid):
    return [e for e in s["events"] if e["kind"] == "volley" and e["unit_id"] == uid]


class ScaleAndProfileTests(unittest.TestCase):
    def test_registration_refuses_an_undeclared_scale(self):
        validate(ENTRY)  # 200 m and 180 s with army rules (doc 63 option A).
        with self.assertRaisesRegex(ValueError, "needs army rules"):
            validate(replace(ENTRY, army=None, units=tuple(
                replace(u, overrides={k: v for k, v in u.overrides.items() if k not in ("move_rate", "yield", "wheel")})
                for u in ENTRY.units)))
        with self.assertRaisesRegex(ValueError, "must be one of"):
            validate(replace(ENTRY, seconds_per_turn=120))
        with self.assertRaisesRegex(ValueError, "must be one of"):
            validate(replace(ENTRY, map=replace(ENTRY.map, metres_per_hex=150)))

    def test_registration_refuses_bad_army_data(self):
        for bad, text in ((dict(engaged_pct=0), "engaged_pct"), (dict(rear_pct=99), "rear_pct"),
                          (dict(fronts={"roman": 0}), "fronts"), (dict(shock_classes=("pikes",)), "shock_classes")):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, text):
                validate(replace(ENTRY, army=replace(ARMY, **bad)))

    def test_the_unit_keys_need_army_rules(self):
        from battle.scenario_gergovia import GERGOVIA_RECALL as G

        first = replace(G.units[0], overrides={**G.units[0].overrides, "move_rate": 2})
        with self.assertRaisesRegex(ValueError, "need army rules"):
            validate(replace(G, units=(first,) + G.units[1:]))
        for key, value in (("move_rate", 4), ("yield", {"limit": 0, "rear_step": -1}),
                           ("wheel", {"reach": 2, "front_row": 6, "rear_step": 2})):
            u = ENTRY.units[0]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                validate(replace(ENTRY, units=(replace(u, overrides={**u.overrides, key: value}),) + ENTRY.units[1:]))

    def test_side_profiles_are_checked_at_registration(self):
        s = build_state(ENTRY)
        self.assertEqual({k: c["communications"] for k, c in s["commanders"].items()},
                         {"roman": ROMAN_216_COMMUNICATIONS, "carthaginian": CARTHAGE_216_COMMUNICATIONS})
        self.assertTrue(PROFILES[ROMAN_216_COMMUNICATIONS]["broadcast"])
        self.assertNotIn("broadcast", PROFILES[CARTHAGE_216_COMMUNICATIONS])
        self.assertEqual({c["voice_reach"] for c in s["commanders"].values()}, {1})
        sides = dict(ENTRY.sides)
        sides["carthaginian"] = replace(sides["carthaginian"], communications="no-such-profile")
        with self.assertRaisesRegex(ValueError, "carthaginian communications must be one of"):
            validate(replace(ENTRY, sides=sides))
        sides["carthaginian"] = replace(sides["carthaginian"], communications="civil-war-courier-v1")
        with self.assertRaisesRegex(ValueError, "must both take"):
            validate(replace(ENTRY, sides=sides))
        self.assertNotEqual(WWI_COMMUNICATIONS, CARTHAGE_216_COMMUNICATIONS)

    def test_the_delivery_estimate_uses_the_declared_interval(self):
        s = build_state(ENTRY)
        self.assertEqual(engine.estimate(s, s["turn"] + 2), "Expected delivery in 360 seconds.")
        self.assertEqual((s["seconds_per_turn"], s["metres_per_hex"]), (180, 200))


class FireMoraleAndFrontTests(unittest.TestCase):
    def test_aspect_reads_the_bearing_against_the_front(self):
        target = {"pos": [10, 10], "front": 0}
        north_west, west, south_west = (9, 9), (9, 10), (9, 11)
        self.assertEqual([army.aspect(target, p) for p in (north_west, west, south_west)], ["front", "flank", "rear"])

    def test_a_shock_volley_fires_the_engaged_share_and_spends_nothing(self):
        s = advance(field(("L1", (10, 10)), ("C1", (10, 9))))
        shot = volleys(s, "L1")[0]
        self.assertEqual(shot["rounds"], 3550 * 13 // 100)
        self.assertEqual(unit(s, "L1")["ammo"], 3550 * 2)  # Heavy infantry spends no ammunition.
        self.assertGreater(unit(s, "C1")["strength"], 2750 - 100)  # About 1 per cent, not the whole unit.
        s = advance(field(("V1", (10, 10)), ("C1", (10, 9))))
        self.assertEqual(unit(s, "V1")["ammo"], 3500 * 3 - 3500 * 13 // 100)  # Light troops spend theirs.

    def test_a_rear_blow_costs_more_men_and_morale_than_a_frontal_one(self):
        front = advance(field(("L1", (10, 10)), ("C1", (10, 9))))  # C1 faces 180 (down): the legion is in front.
        rear = advance(field(("L1", (10, 10)), ("C1", (10, 11))))  # The legion is behind C1.
        self.assertEqual(volleys(front, "L1")[0]["aspect"], "front")
        self.assertEqual(volleys(rear, "L1")[0]["aspect"], "rear")
        hit = lambda s: 2750 - unit(s, "C1")["strength"]
        self.assertGreater(hit(rear), hit(front))
        self.assertLess(unit(rear, "C1")["morale"], unit(front, "C1")["morale"])

    def test_morale_falls_by_share_of_strength_not_by_man(self):
        u = {"initial": 3550}
        self.assertEqual(army.morale_loss({"army_rules": {"morale_per_pct": 2}}, u, 3550 * 100, 0), 200)
        self.assertEqual(army.morale_loss({"army_rules": {"morale_per_pct": 2}}, u, 3600, 3600), 4)
        s = advance(field(("L1", (10, 10)), ("C1", (10, 11))))
        self.assertGreater(unit(s, "C1")["morale"], 28)  # 4 a man would have routed it at once.

    def test_the_front_follows_movement_but_not_a_step_back(self):
        events = []
        emit = lambda s, kind, **d: events.append((kind, d))
        u = {"id": "L1", "front": 0, "local_action": "continue"}
        army.moved({}, u, [10, 10], [10, 11], emit)
        self.assertEqual(u["front"], 150)
        u.update({"local_action": "yield", "yield": {"limit": 3, "rear_step": -1}})
        army.moved({}, u, [10, 11], [10, 10], emit)
        self.assertEqual((u["front"], u["yielded"], events[-1][0]), (150, 1, "unit_yielded"))
        u["local_action"] = "withdraw"
        army.moved({}, u, [10, 10], [11, 10], emit)
        self.assertEqual(u["front"], 150)

    def test_a_cavalry_unit_moves_three_hexes_an_interval(self):
        s = field(("EQ", (5, 15)), ("C1", (20, 0)))
        unit(s, "EQ").update(target=[5, 9], stance="move")
        s = advance(s)
        moves = [e for e in s["events"] if e["kind"] == "unit_moved" and e["unit_id"] == "EQ"]
        self.assertEqual((len(moves), unit(s, "EQ")["pos"][1]), (3, 12))
        s = field(("L1", (5, 15)), ("C1", (20, 0)))
        unit(s, "L1").update(target=[5, 9], stance="move")
        self.assertEqual(unit(advance(s), "L1")["pos"][1], 14)  # Infantry: one hex.

    def test_a_routed_enemy_is_reported_as_routed_only_at_army_scale(self):
        s = field(("L1", (10, 10)), ("C1", (10, 7)))
        unit(s, "C1")["status"] = "routed"
        self.assertTrue(recon.scan(s)["L1"][0]["routed"])
        del s["army_rules"]
        self.assertNotIn("routed", recon.scan(s)["L1"][0])


class DoctrineTests(unittest.TestCase):
    def test_a_pressed_centre_unit_yields_up_to_its_limit_without_routing(self):
        s = field(("L1", (16, 12)), ("C5", (16, 11)))
        rows = []
        for _ in range(16):  # The legion follows the yielding unit, as the press keeps contact.
            unit(s, "L1").update(target=list(unit(s, "C5")["pos"]), stance="move", press_assault=True)
            s = advance(s)
            rows.append(unit(s, "C5")["pos"][1])
        c5 = unit(s, "C5")
        self.assertEqual((c5["yielded"], c5["status"]), (3, "ready"))
        self.assertEqual(min(rows), 8)  # Three rows back from row 11, then it stands.
        self.assertEqual(c5["front"], 180)  # A yield keeps the front.
        self.assertEqual(sum(e["kind"] == "unit_yielded" for e in s["events"]), 3)

    def test_an_unpressed_unit_does_not_yield(self):
        s = advance(field(("L1", (16, 15)), ("C5", (16, 11))), 4)  # In sight, never adjacent.
        self.assertEqual((unit(s, "C5")["pos"], unit(s, "C5").get("yielded")), ([16, 11], None))
        s = field(("L1", (16, 12)), ("C5", (16, 11)))
        unit(s, "C5").pop("yield")  # C2 (no-design): no doctrine, no yield.
        self.assertEqual(unit(advance(s, 4), "C5")["pos"], [16, 11])

    def test_an_african_wheels_on_an_enemy_past_its_front_row(self):
        s = advance(field(("AF2", (13, 6)), ("L1", (14, 5))))  # Row 5 is past row 6, 2 hexes off.
        af = unit(s, "AF2")
        wheeled = [e for e in s["events"] if e["kind"] == "unit_wheeled"]
        self.assertEqual((wheeled[0]["unit_id"], wheeled[0]["toward_id"], af["local_action"]), ("AF2", "L1", "wheel"))
        self.assertLessEqual(grid.distance(af["pos"], [14, 5]), 1)
        self.assertNotEqual(af["front"], 180)  # It faces inward.

    def test_an_enemy_level_with_the_front_row_does_not_trigger_the_wheel(self):
        s = advance(field(("AF2", (13, 6)), ("L1", (15, 6))))
        self.assertFalse([e for e in s["events"] if e["kind"] == "unit_wheeled"])
        s = advance(field(("AF2", (13, 6)), ("L1", (17, 5))))  # Past the row but beyond the 2-hex reach.
        self.assertFalse([e for e in s["events"] if e["kind"] == "unit_wheeled"])


def _cells():
    return {grid.key([c, r]): {"pos": [c, r], "elevation": 0, "terrain": "open", "move_cost": 100, "cover": 0}
            for c in range(grid.COLS) for r in range(grid.ROWS)}


class EncircleTests(unittest.TestCase):
    def test_a_ring_of_enemies_encloses_and_a_gap_does_not(self):
        ring = grid.neighbors([10, 10])
        self.assertEqual(enclosure(_cells(), {"L1": [10, 10]}, ring, [[10, 20]], 0), (["L1"], 0, 0))
        self.assertEqual(enclosure(_cells(), {"L1": [10, 10]}, ring[:-1], [[10, 20]], 0), ([], 1, 1))
        wall = [[c, 15] for c in range(grid.COLS) if c != 7]
        self.assertEqual(enclosure(_cells(), {"L1": [10, 10]}, wall, [[10, 20], [3, 20]], 0), ([], 2, 1))

    def test_zoc_0_lets_a_unit_pass_between_two_enemies(self):
        gate = [[c, 15] for c in range(grid.COLS) if c not in (7, 8)]  # A two-hex gap.
        self.assertEqual(enclosure(_cells(), {"L1": [10, 10]}, gate, [[10, 20]], 0)[0], [])
        self.assertEqual(enclosure(_cells(), {"L1": [10, 10]}, gate, [[10, 20]], 1)[0], ["L1"])

    def _scored(self, **placed):
        s = build_state(ENTRY)
        for uid, pos in placed.items():
            unit(s, uid)["pos"] = list(pos)
        return s

    def test_the_centre_breaking_wins_for_the_attacker_at_once(self):
        s = build_state(ENTRY)
        for uid in ("C1", "C2", "C3", "C4"):
            unit(s, uid)["status"] = "routed"
        self.assertEqual(victory.score(s), (None, None))
        unit(s, "C5").update(status="lost", strength=0)
        winner, reason = victory.score(s)
        self.assertEqual((winner, reason), ("roman", "The Carthaginian centre broke: 5 of its 8 centre units routed or lost."))

    def test_an_enclosed_pocket_wins_for_the_defender_at_the_deadline(self):
        s = build_state(ENTRY)
        for u in s["units"]:  # Every Roman heavy unit inside a ring of Carthaginians at the top of the map.
            if u["side"] == "carthaginian":
                u["pos"] = [0, 0]
        units = [u for u in s["units"] if u["side"] == "carthaginian"]
        unit(s, "L1")["pos"] = [5, 5]
        for u, p in zip(units, grid.neighbors([5, 5])):
            u["pos"] = p
        for u in (x for x in s["units"] if x["id"] in ENTRY.victory.pocket_units[1:]):
            u.update(status="lost", strength=0)
        s["turn"] = s["max_turns"]
        winner, reason = victory.score(s)
        self.assertEqual(winner, "carthaginian")
        self.assertIn("was enclosed by the deadline: 3550 men enclosed", reason)
        self.assertEqual((s["victory"]["closed_turn"], s["victory"]["record"][-1][:3]), (160, [160, 1, 3550]))

    def test_an_open_army_wins_for_the_attacker_at_the_deadline(self):
        s = build_state(ENTRY)
        s["turn"] = s["max_turns"]
        winner, reason = victory.score(s)
        self.assertEqual((winner, s["victory"]["record"][-1][1]), ("roman", 0))
        self.assertEqual(reason, "The Roman army was not enclosed by the deadline: 0 men enclosed and 0 lost, "
                                 "short of the 28400 required.")
        self.assertNotIn("victory", engine.view(s, "roman"))
        self.assertNotIn("victory", engine.view(s, "carthaginian"))

    def test_headquarters_learn_of_the_pocket_from_reports_only(self):
        s = build_state(ENTRY)
        units = [u for u in s["units"] if u["side"] == "carthaginian"]
        unit(s, "L1")["pos"] = [5, 5]
        for u, p in zip(units, grid.neighbors([5, 5])):
            u["pos"] = p
        victory.score(s)
        self.assertEqual(s["victory"]["closed_turn"], 0)  # On the ground ...
        self.assertEqual(s["victory"]["known_closed_turn"], {"roman": None, "carthaginian": None})  # ... not yet known.

    def test_other_kinds_refuse_the_encircle_fields(self):
        from battle.scenario_gergovia import GERGOVIA_RECALL as G

        with self.assertRaisesRegex(ValueError, "use encircle"):
            validate(replace(G, victory=replace(G.victory, zoc=1)))


class OptInTests(unittest.TestCase):
    def test_every_saved_poc13_entry_plays_as_recorded(self):
        played = {}
        for entry in HEADLESS_SCENARIOS:
            if entry.id in RECORDED:
                s = advance(build_state(entry), 40)
                played[entry.id] = hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()
                self.assertNotIn("army_rules", s)
        self.assertEqual(played, RECORDED)

    def test_army_rules_change_nothing_unless_declared(self):
        self.assertFalse(army.on(build_state(HEADLESS_SCENARIOS[0])))
        self.assertEqual(army.max_rate(build_state(HEADLESS_SCENARIOS[0])), 1)
        self.assertEqual(army.max_rate(build_state(ENTRY)), 3)
        self.assertIsInstance(ARMY, ArmyEntry)
        self.assertTrue(isinstance(ENTRY.map, MapEntry) and isinstance(ENTRY.units[0], UnitEntry))
        self.assertEqual({HEAVY_INFANTRY, LIGHT_INFANTRY} - set(ENTRY.weapons), set())


if __name__ == "__main__":
    unittest.main()
