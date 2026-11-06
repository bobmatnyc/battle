"""poc-12 contact rules: a push that never deletes a holder for want of room,
a fair tie-break for contested hexes, and assaults that press on under fire.
Design: docs/research/45.

The gate fixture (see test_gateway_push) is a row of three compound hexes:
back room 9,10, farm 10,10 and the gateway 11,10, whose gate opens onto
12,10. Only the farm lies beside the gateway.
"""

import dataclasses
import unittest

from battle import engine, gates, grid, runtime
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from scenario_fixtures import DUEL, GATE_OUTSIDE, GATEWAY
from test_gateway_push import BACK_ROOM, FARM, KEY, OUTSIDE_WALLS, events, held_gateway, push_in, unit


def advance(s, n=1):
    for _ in range(n):
        s = runtime.apply(s, {"type": "advance", "decision": None})
    return s


def total(s):
    return sum(u["strength"] for u in s["units"])


def at_threshold(b1=BACK_ROOM, farm=True, holder=40, pusher=40, rules="poc-12"):
    """B2 holds the gateway, G1 on the outside hex is ordered into the farm,
    and one more interval of G1's labour carries the push to ``push_labour``."""
    s = held_gateway(b1=b1, farm=farm, rules=rules)
    unit(s, "B2").update(strength=holder, initial=holder)
    unit(s, "G1").update(strength=pusher, initial=pusher, stance="move", target=list(FARM))
    s["push_effort"][KEY] = s["push_rules"]["push_labour"] - min(pusher, s["push_rules"]["push_cap"])
    s["turn"] = 1
    return s


SIZES = {"larger holder": (100, 10), "smaller holder": (10, 100), "equal": (40, 40)}


class PushRuleTests(unittest.TestCase):
    """(a) The push never removes a holder because the compound is full."""

    def test_crowded_courtyard_stalls_the_push_and_conserves_strength(self):
        for name, (holder, pusher) in SIZES.items():
            with self.subTest(name):
                s = at_threshold(holder=holder, pusher=pusher)
                before = total(s)
                gates.push(s)
                self.assertEqual(total(s), before)
                self.assertEqual((unit(s, "B2")["strength"], unit(s, "B2")["status"]), (holder, "ready"))
                self.assertEqual((unit(s, "B2")["pos"], unit(s, "G1")["pos"]), (GATEWAY, GATE_OUTSIDE))
                self.assertEqual(events(s, "gateway_carried"), [])
                stalled = events(s, "gateway_push_stalled")
                self.assertEqual([(e["holder_id"], e["reason"]) for e in stalled], [("B2", "no_free_hex_beside_gateway")])
                self.assertEqual(s["push_effort"][KEY], s["push_rules"]["push_labour"])

    def test_one_free_hex_beside_the_gateway_takes_the_holder(self):
        for name, (holder, pusher) in SIZES.items():
            with self.subTest(name):
                s = at_threshold(farm=False, holder=holder, pusher=pusher)
                before = total(s)
                gates.push(s)
                carried = events(s, "gateway_carried")
                self.assertEqual([(e["outcome"], e["holder_pos"], e["losses"]) for e in carried],
                                 [("displaced", FARM, 0)])
                self.assertEqual((unit(s, "B2")["pos"], unit(s, "G1")["pos"]), (FARM, GATEWAY))
                self.assertEqual((total(s), unit(s, "B2")["strength"]), (before, holder))
                self.assertEqual(s["push_effort"][KEY], 0)

    def test_displacement_is_one_step_to_the_nearest_legal_hex(self):
        # Farm and back room free: the holder steps back one hex, into the farm.
        s = at_threshold(b1=OUTSIDE_WALLS, farm=False)
        gates.push(s)
        self.assertEqual(unit(s, "B2")["pos"], FARM)
        self.assertEqual(grid.distance(GATEWAY, unit(s, "B2")["pos"]), 1)
        # Only the back room free, behind an occupied farm: no hex beside the
        # gateway is free, so the push stalls; the holder never jumps two hexes.
        s = at_threshold(b1=OUTSIDE_WALLS)
        gates.push(s)
        self.assertEqual(unit(s, "B2")["pos"], GATEWAY)
        self.assertEqual(events(s, "gateway_push_stalled")[0]["reason"], "no_free_hex_beside_gateway")

    def test_stalled_push_carries_once_a_hex_beside_the_gateway_frees(self):
        s = at_threshold()
        gates.push(s)
        unit(s, "B3")["pos"] = [10, 12]  # The farm's garrison leaves the walls.
        s["turn"] = 2
        gates.push(s)
        self.assertEqual([e["holder_pos"] for e in events(s, "gateway_carried")], [FARM])
        self.assertEqual(unit(s, "G1")["pos"], GATEWAY)

    def test_crowded_courtyard_never_destroys_the_holder_in_play(self):
        s = advance(push_in(held_gateway(b1=BACK_ROOM, rules="poc-12")), 3)
        self.assertEqual([e for e in events(s, "gateway_carried") if e["outcome"] == "overrun"], [])
        self.assertGreater(unit(s, "B2")["strength"], 0)
        self.assertTrue(events(s, "gateway_push_stalled"))

    def test_poc11_keeps_the_overrun(self):
        s = at_threshold(rules="poc-11")
        gates.push(s)
        self.assertEqual([e["outcome"] for e in events(s, "gateway_carried")], ["overrun"])


# A walled pen on open ground: feeders 15,10, 16,11 and 15,11 all touch
# JUNCTION 16,10, whose two northern edges (to 16,9 and 15,9) are the only
# way out. Walls on the cells keep every route through the junction, which is
# the one hex each unit needs; beyond it the units part for separate hexes.
JUNCTION = [16, 10]
FEEDERS = {"C1": [15, 10], "C2": [16, 11], "C3": [15, 11]}
DESTINATIONS = {"C1": [16, 5], "C2": [13, 6], "C3": [19, 6]}
PEN = [JUNCTION, *FEEDERS.values()]
EXITS = ([16, 9], [15, 9])


def corridor(movers, rules="poc-12"):
    """The duel with C1-C3 in the feeders; ``movers`` are ordered out of the pen."""
    entry = dataclasses.replace(
        DUEL, id="test-corridor", labels={"poc-11": "test-corridor-v1", "poc-12": "test-corridor-v2"},
        units=DUEL.units + tuple(UnitEntry(uid, "union", f"Column {uid}", tuple(pos)) for uid, pos in FEEDERS.items()),
        victory=VictoryEntry(kind="hold-objective", objective=(4, 5), deadline_turns=60, objective_name="knoll"))
    s = build_state(dry_run(validate(entry)), rules)
    inside = {grid.key(p) for p in PEN}
    for p in PEN:
        for n in grid.neighbors(p):
            if grid.key(n) in inside or (p == JUNCTION and n in EXITS):continue
            s["cells"][grid.key(p)].setdefault("walls", []).append(n)
            s["cells"][grid.key(n)].setdefault("walls", []).append(list(p))
    for uid in movers:
        unit(s, uid).update(stance="move", target=list(DESTINATIONS[uid]))
    return s


def junction_turns(s):
    """Per unit, the turns it entered the junction and the turns it was refused it."""
    moved = {e["unit_id"]: e["turn"] for e in events(s, "unit_moved") if e["destination"] == JUNCTION}
    refused = {}
    for e in events(s, "movement_blocked"):
        if e["destination"] == JUNCTION:refused.setdefault(e["unit_id"], []).append(e["turn"])
    return moved, refused


class ContestedHexTests(unittest.TestCase):
    """(b) Units wanting one hex take turns; none waits for ever."""

    def test_two_units_contending_for_one_hex_both_move(self):
        s = advance(corridor(("C1", "C2")), 16)
        moved, _ = junction_turns(s)
        self.assertEqual(sorted(moved), ["C1", "C2"])
        self.assertEqual([unit(s, u)["pos"] for u in ("C1", "C2")], [DESTINATIONS["C1"], DESTINATIONS["C2"]])

    def test_three_way_contention_lets_every_unit_through(self):
        s = advance(corridor(("C1", "C2", "C3")), 24)
        moved, refused = junction_turns(s)
        self.assertEqual(sorted(moved), ["C1", "C2", "C3"])
        # Each interval in which the junction was contested, one contender entered it.
        for turn in {t for turns in refused.values() for t in turns}:
            contested = [e for e in events(s, "movement_blocked")
                         if e["turn"] == turn and e["destination"] == JUNCTION and e.get("reason") == "contested"]
            if contested:self.assertIn(turn, moved.values())
        self.assertEqual([unit(s, u)["pos"] for u in ("C1", "C2", "C3")], [DESTINATIONS[u] for u in ("C1", "C2", "C3")])

    def test_priority_rotates_and_never_starves_a_unit(self):
        # Isolated: the same contenders, never moved, propose one hex each round.
        s = corridor(())
        for case, uids, expected in (("two", ("C1", "C2"), ["C1", "C2", "C1", "C2"]),
                                     ("three", ("C1", "C2", "C3"), ["C1", "C2", "C3", "C1", "C2", "C3"])):
            with self.subTest(case):
                for uid in uids:unit(s, uid).pop("contest_wait", None)
                winners = []
                for _ in expected:
                    moves = [(unit(s, uid), JUNCTION, 100) for uid in uids]
                    winners += [u["id"] for u, _, _ in engine.contest(s, moves, {})]
                    for u, _, _ in moves:
                        if u["id"] == winners[-1]:u.pop("contest_wait", None)
                self.assertEqual(winners, expected)

    def test_poc11_contenders_still_wait(self):
        s = advance(corridor(("C1", "C2"), rules="poc-11"), 6)
        self.assertEqual(junction_turns(s)[0], {})


def assault_set_up(target=FARM, **g1):
    """G1 four hexes from the held gateway, under B2's fire."""
    s = held_gateway(rules="poc-12")
    unit(s, "G1").update(pos=[15, 10], stance="move", target=list(target), **g1)
    return s


def decision(s, uid):
    return [e for e in events(s, "local_decision") if e["unit_id"] == uid][-1]


class AssaultHaltTests(unittest.TestCase):
    """(c) Assault missions press on within five hexes of the enemy."""

    def test_assault_into_the_compound_continues_within_five_hexes(self):
        s = advance(assault_set_up())
        self.assertEqual(decision(s, "G1")["action"], "continue")
        self.assertEqual(unit(s, "G1")["pos"], [14, 10])

    def test_assault_under_fire_reaches_the_gate(self):
        s = advance(assault_set_up(), 4)
        self.assertEqual(unit(s, "G1")["pos"], GATE_OUTSIDE)

    def test_ordinary_move_still_halts(self):
        s = advance(assault_set_up(target=[15, 6]))
        self.assertIn(decision(s, "G1")["action"], ("defend", "take_cover"))
        self.assertEqual(unit(s, "G1")["pos"], [15, 10])

    def test_assault_below_its_withdrawal_threshold_still_withdraws(self):
        s = advance(assault_set_up(ammo=1))
        self.assertEqual(decision(s, "G1")["action"], "withdraw")
        self.assertIn("ammunition is below the standing reserve", decision(s, "G1")["reason"])

    def test_poc11_assault_still_halts(self):
        s = held_gateway(rules="poc-11")
        unit(s, "G1").update(pos=[15, 10], stance="move", target=list(FARM))
        s = advance(s)
        self.assertNotEqual(decision(s, "G1")["action"], "continue")


# Taken at fdd63c2, before poc-12, as sha256 of the sort-keyed JSON state: the
# scripted poc-11 Little Round Top run (test_scenario_sides.play); poc-11 saves
# advanced through BattleService (Little Round Top 10 then 30 intervals,
# Hougoumont 40); the poc-11 north-gate arrangement advanced 15 intervals; and
# the poc-11 crowded-courtyard push advanced 4 intervals.
POC11_LRT_RUN_SHA256 = "94227b61f3fc91e1ae98ddfaba2952110f53e2aa449f440ea491e366fdc40e40"
POC11_LRT_SAVE_ADVANCED_SHA256 = "2276728f980a735d64aba87cee7fe9a09a953aa07623198c00d34af7469e5b2c"
POC11_HOUGOUMONT_SAVE_ADVANCED_SHA256 = "99db0dfb92c28112b8236da9b78f35a77f4509b8709af0d70dfc4a2889e7ee2b"
POC11_AT_THE_NORTH_GATE_SHA256 = "c30e732b1505a6eb1a20b1c6be6b4bdeb2d8ba811891f5670bb92e97b19117b1"
POC11_OVERRUN_SHA256 = "acb24a0c3d8a7aab4a059b5bf36206fb4a8b1c5fe16271f69ed1ad46511e9755"


class Poc12EditionTests(unittest.TestCase):
    def test_new_games_use_poc12(self):
        from battle import scenario
        self.assertEqual((scenario.create()["rules"], scenario.create()["scenario"]), ("poc-12", "little-round-top-v12"))

    def test_poc11_runs_and_saves_keep_their_digests(self):
        import json
        from unittest import mock
        from battle import engine_v11, scenario
        from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE as HOUGOUMONT
        from test_gates import advance_through_service
        from test_gateway_push import at_the_north_gate
        from test_scenario_sides import digest, play

        self.assertEqual(digest(play(scenario.create("poc-11"))), POC11_LRT_RUN_SHA256)
        with mock.patch.object(engine_v11, "advance", wraps=engine_v11.advance) as frozen:
            save = advance_through_service(scenario.create("poc-11"), 10)
            final = advance_through_service(json.loads(json.dumps(save, sort_keys=True)), 30)
            hougoumont = advance_through_service(build_state(HOUGOUMONT, "poc-11"), 40,
                                                 (scenario.LITTLE_ROUND_TOP, HOUGOUMONT))
        self.assertEqual(frozen.call_count, 40 + hougoumont["turn"])
        self.assertEqual((final["rules"], final["turn"]), ("poc-11", 40))
        self.assertEqual(digest(final), POC11_LRT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(hougoumont), POC11_HOUGOUMONT_SAVE_ADVANCED_SHA256)
        self.assertEqual(digest(advance(at_the_north_gate("poc-11"), 15)), POC11_AT_THE_NORTH_GATE_SHA256)
        overrun = advance(push_in(held_gateway(b1=[9, 10])), 4)
        self.assertEqual(overrun["rules"], "poc-11")
        self.assertEqual(digest(overrun), POC11_OVERRUN_SHA256)


if __name__ == "__main__":
    unittest.main()
