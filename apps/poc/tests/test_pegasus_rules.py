"""Pegasus Bridge scenario rules (docs/research/54): a demolition triggered by
the battle, the sappers' clearing of the charges, and the seize-and-hold
victory kind. Both are read only from keys a new entry declares.

Fixtures are the small synthetic canal entries of ``test_pegasus_engine``
(canal along row 10, bridge at (12, 10)); none is the Pegasus scenario. The
Grey side (``confederate``) guards the bridge in the demolition tests and
attacks it in the victory tests, as the fixture's roles require.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from battle import engine, formations, grid, runtime, victory
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from battle.scenario_wwii import DemolitionEntry
from battle.storage import Store
from test_formations import SPLIT, fixture as formation_fixture
from test_gateway_push import events, unit
from test_pegasus_engine import BRIDGE, CANAL_BRIDGE, HAM, advance, night, night_entry

# The guard stands north of the bridge, adjacent to it; B2 two hexes south of
# it is in sight at a night range of 2. Both hold their fire, so neither fires.
GUARD = (12, 9)
QUIET = {"fire_posture": "hold_fire"}
UNITS = (
    UnitEntry("B1", "union", "Company headquarters", (12, 16), QUIET),
    UnitEntry("B2", "union", "Leading platoon, with sappers", (12, 11), {**QUIET, "clears_charges": True}),
    UnitEntry("G1", "confederate", "Bridge guard", GUARD, QUIET),
)
NO_SAPPERS = (UNITS[0], UnitEntry("B2", "union", "Leading platoon", (12, 11), QUIET), UNITS[2])
ON_CONTACT = DemolitionEntry(side="confederate", trigger="contact", delay=2, removal_turns=2)


def wired(demolition=ON_CONTACT, units=UNITS, **kw):
    bridge = dataclasses.replace(CANAL_BRIDGE, state="charges", demolition=demolition)
    return night(bridges=(bridge,), units=units, observation_range=2, **kw)


def changes(s):
    return [(e["turn"], e["from_state"], e["to_state"], e["cause"]) for e in events(s, "bridge_state_changed")]


class DemolitionTests(unittest.TestCase):
    """The guard fires the charges after contact or a crossing; sappers on the bridge clear them."""

    def test_contact_arms_the_charges_and_the_guard_fires_them_after_the_delay(self):
        s = advance(wired(), 3)
        armed = events(s, "demolition_armed")
        self.assertEqual([(e["turn"], e["bridge_id"], e["trigger"], e["due_turn"]) for e in armed],
                         [(1, "canal-bridge", "contact", 3)])
        self.assertEqual(changes(s), [(3, "charges", "destroyed", "demolished")])
        self.assertEqual(s["cells"][grid.key(list(BRIDGE))]["bridge_state"], "destroyed")

    def test_no_firing_party_within_reach_means_no_firing(self):
        s = advance(wired())
        unit(s, "G1")["pos"] = [12, 4]  # The guard leaves the bridge before the charges are due.
        s = advance(s, 4)
        self.assertEqual(changes(s), [])
        unit(s, "G1")["pos"] = list(GUARD)  # Back within reach: the armed charges fire.
        s = advance(s)
        self.assertEqual(changes(s), [(6, "charges", "destroyed", "demolished")])

    def test_enemy_on_the_bridge_clears_the_charges_before_they_are_due(self):
        s = wired(dataclasses.replace(ON_CONTACT, delay=4))
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s, 6)
        self.assertEqual(changes(s), [(2, "charges", "intact", "charges_removed")])
        self.assertEqual(s["cells"][grid.key(list(BRIDGE))]["bridge_state"], "intact")

    def test_a_unit_without_sappers_never_clears_the_charges(self):
        s = wired(dataclasses.replace(ON_CONTACT, delay=40), units=NO_SAPPERS)
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s, 8)
        self.assertEqual(changes(s), [])
        self.assertEqual(s["bridge_demolition"][0]["removal"], 0)

    def test_registration_refuses_a_non_boolean_sapper_key(self):
        units = (UNITS[0], UnitEntry("B2", "union", "Leading platoon", (12, 11), {"clears_charges": "yes"}), UNITS[2])
        with self.assertRaisesRegex(ValueError, "clears_charges"):
            validate(night_entry(bridges=(CANAL_BRIDGE,), units=units))

    def test_charges_due_in_the_interval_the_clearing_ends_are_fired_first(self):
        s = wired(dataclasses.replace(ON_CONTACT, delay=1))
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s, 3)
        self.assertEqual(changes(s), [(2, "charges", "destroyed", "demolished")])

    def test_crossing_trigger_waits_for_an_enemy_on_the_bridge(self):
        s = advance(wired(dataclasses.replace(ON_CONTACT, trigger="crossing", removal_turns=9)), 3)
        self.assertEqual(events(s, "demolition_armed"), [])  # In sight, but not crossing.
        unit(s, "B2")["pos"] = list(BRIDGE)
        s = advance(s, 3)
        self.assertEqual([e["turn"] for e in events(s, "demolition_armed")], [4])
        self.assertEqual(changes(s), [(6, "charges", "destroyed", "demolished")])

    def test_only_a_declared_demolition_writes_state(self):
        self.assertIn("bridge_demolition", wired())
        plain = night(bridges=(dataclasses.replace(CANAL_BRIDGE, state="charges"),), units=UNITS)
        self.assertNotIn("bridge_demolition", plain)
        self.assertEqual(changes(advance(plain, 4)), [])

    def test_registration_refuses_bad_demolition_data(self):
        cases = {
            "unknown side": (dataclasses.replace(ON_CONTACT, side="french"), "charges"),
            "unknown trigger": (dataclasses.replace(ON_CONTACT, trigger="dawn"), "charges"),
            "negative delay": (dataclasses.replace(ON_CONTACT, delay=-1), "charges"),
            "negative reach": (dataclasses.replace(ON_CONTACT, reach=-1), "charges"),
            "no clearing time": (dataclasses.replace(ON_CONTACT, removal_turns=0), "charges"),
            "not wired": (ON_CONTACT, "intact"),
        }
        for name, (bad, state) in cases.items():
            with self.subTest(name):
                bridge = dataclasses.replace(CANAL_BRIDGE, state=state, demolition=bad)
                with self.assertRaisesRegex(ValueError, "demolition"):
                    validate(night_entry(bridges=(bridge,), units=UNITS))

    def test_triggered_demolition_replays_identically(self):
        s = wired()
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "demolition.sqlite")
            gid = store.create(s)
            for _ in range(5):
                n = runtime.apply(s, {"type": "advance", "decision": None})
                store.save(gid, n, s["revision"])
                s = n
            self.assertEqual(changes(s), [(3, "charges", "destroyed", "demolished")])
            self.assertEqual(runtime.verify_replay(store, gid)["status"], "identical")


# Two hexes north of the bridge: within a 2-hex firing reach, outside a 1-hex sight.
FAR_GUARD = (12, 8)


def crossing_state(guard=GUARD, guard_sight=None, enemy_on_bridge=True, reach=1):
    """A crossing-trigger bridge with the guard at ``guard`` and B2 on the
    bridge (or far off). ``guard_sight`` overrides the guard's night range."""
    sight = {} if guard_sight is None else {"observation_range": guard_sight}
    units = UNITS[:2] + (UnitEntry("G1", "confederate", "Bridge guard", guard, {**QUIET, **sight}),)
    s = wired(dataclasses.replace(ON_CONTACT, trigger="crossing", reach=reach, removal_turns=9), units=units)
    unit(s, "B2")["pos"] = list(BRIDGE) if enemy_on_bridge else [2, 18]
    return s


class CrossingSightTests(unittest.TestCase):
    """The crossing trigger arms only when a guard within reach sees the enemy on the bridge."""

    def test_crossing_with_no_guard_within_reach_arms_nothing(self):
        s = advance(crossing_state(guard=(12, 4)), 3)
        self.assertEqual(events(s, "demolition_armed"), [])

    def test_crossing_the_guard_cannot_see_arms_nothing(self):
        s = advance(crossing_state(guard=FAR_GUARD, guard_sight=1, reach=2), 3)
        self.assertEqual(events(s, "demolition_armed"), [])
        seen = advance(crossing_state(guard=FAR_GUARD, guard_sight=2, reach=2))  # Control: in sight, it arms.
        self.assertEqual([e["turn"] for e in events(seen, "demolition_armed")], [1])

    def test_an_enemy_the_guard_cannot_observe_does_not_change_the_arming_decision(self):
        decisions = []
        for on_bridge in (True, False):
            s = advance(crossing_state(guard=FAR_GUARD, guard_sight=1, reach=2, enemy_on_bridge=on_bridge), 3)
            decisions.append(([e["turn"] for e in events(s, "demolition_armed")], s["bridge_demolition"][0]["armed_turn"]))
        self.assertEqual(decisions[0], decisions[1])


def ham_state(enemy_near, sight):
    """B2 holds the bridge; G1, holding fire, stands 2 hexes north (within the
    signal's 2-hex radius) or far off. Every unit sees ``sight`` hexes."""
    units = (UnitEntry("B1", "union", "Company headquarters", (12, 16), QUIET),
             UnitEntry("B2", "union", "Leading platoon", BRIDGE, QUIET),
             UnitEntry("G1", "confederate", "Guard", FAR_GUARD if enemy_near else (20, 2), QUIET))
    return night(bridges=(CANAL_BRIDGE,), signals=(dataclasses.replace(HAM, radius=2),), units=units,
                 observation_range=sight)


def ham_sent(s):
    return [(e["sender_id"], e["sent_turn"]) for e in events(advance(s), "signal_sent")]


class HamSightTests(unittest.TestCase):
    """The holder's codeword decision counts only the enemies it sees."""

    def test_an_enemy_the_holder_cannot_observe_does_not_change_the_ham_decision(self):
        self.assertEqual(ham_sent(ham_state(enemy_near=True, sight=1)), ham_sent(ham_state(enemy_near=False, sight=1)))
        self.assertEqual(ham_sent(ham_state(enemy_near=True, sight=1)), [("B2", 1)])

    def test_an_enemy_the_holder_sees_within_the_radius_still_stops_ham(self):
        self.assertEqual(ham_sent(ham_state(enemy_near=True, sight=2)), [])


def sapper(s, uid):
    """Give ``uid`` the sapper key in truth and in headquarters' report."""
    engine.find_unit(s, uid)["clears_charges"] = True
    s["friendly_reports"]["union"][uid]["clears_charges"] = True


class SapperFormationTests(unittest.TestCase):
    """D2: a unit carrying sappers neither splits nor combines (docs/research/54).
    Fixture: Little Round Top on open ground (``test_formations.fixture``);
    U1 and U2 are adjacent, U2 is the command unit."""

    def test_split_of_a_sapper_unit_is_refused_at_request(self):
        s = formation_fixture()
        sapper(s, "U1")
        with self.assertRaisesRegex(ValueError, "sappers"):
            formations.request(s, "union", SPLIT)
        self.assertEqual(s["formation_ops"], [])

    def test_combine_is_refused_at_request_whichever_unit_carries_sappers(self):
        for carrier in ("U1", "U2"):  # U2 absorbing a sapper unit; a sapper unit absorbing U1.
            with self.subTest(carrier=carrier):
                s = formation_fixture()
                sapper(s, carrier)
                with self.assertRaisesRegex(ValueError, "sappers"):
                    formations.request(s, "union", {"kind": "combine", "unit_id": "U2", "partner_id": "U1"})
                self.assertEqual(s["formation_ops"], [])

    def test_split_applied_after_the_unit_gained_sappers_is_refused_at_execution(self):
        s = formation_fixture()
        formations.request(s, "union", SPLIT)  # Valid when queued: U1 has no sappers yet.
        engine.find_unit(s, "U1")["clears_charges"] = True  # A path that skips request validation.
        for _ in range(3):
            engine.advance(s)
        op = s["formation_ops"][0]
        self.assertFalse([e for e in s["events"] if e["kind"] == "unit_split"])
        self.assertIsNone(next((u for u in s["units"] if u["id"] == "UD1"), None))
        self.assertEqual(op["status"], "refused")
        self.assertIn("sappers", op["reason"])

    def test_units_without_sappers_still_split(self):
        s = formation_fixture()
        formations.request(s, "union", SPLIT)
        for _ in range(3):
            engine.advance(s)
        self.assertEqual(s["formation_ops"][0]["status"], "completed")


SEIZE = VictoryEntry(kind="seize-and-hold", objective=BRIDGE, deadline_turns=20, radius=1, hold_turns=2,
                     objective_name="canal bridge", relief_turn=10)
FAR = {"B1": [0, 20], "B2": [2, 20]}


def seize_entry(v=SEIZE, **kw):
    return dataclasses.replace(night_entry(**kw), victory=v)


def seize_state(v=SEIZE, **kw):
    s = build_state(dry_run(validate(seize_entry(v, **kw))))
    for uid, pos in FAR.items():
        unit(s, uid)["pos"] = pos
    unit(s, "G1")["pos"] = list(BRIDGE)  # Grey attacks: it stands on the bridge alone.
    return s


def score_until(s, turn):
    """Score each interval up to ``turn``; the first result and its turn, else (None, None, turn)."""
    while s["turn"] < turn:
        s["turn"] += 1
        winner, reason = victory.score(s)
        if winner:
            return winner, reason, s["turn"]
    return None, None, s["turn"]


class SeizeAndHoldTests(unittest.TestCase):
    """The attacker seizes the objective, then must keep it until relief or the deadline."""

    def test_seized_objective_held_until_relief_wins_at_the_relief_turn(self):
        s = seize_state()
        winner, reason, turn = score_until(s, 20)
        self.assertEqual((winner, turn), ("confederate", 10))
        self.assertIn("canal bridge", reason)
        self.assertIn("relie", reason)
        self.assertEqual(s["victory"]["history"], [{"objective": 0, "event": "seized", "turn": 2}])

    def test_seizure_lapses_when_no_attacker_remains_and_the_defender_wins_at_the_deadline(self):
        s = seize_state()
        self.assertEqual(score_until(s, 4)[0], None)
        unit(s, "G1")["pos"] = [12, 4]  # The attacker leaves the bridge and its ring.
        winner, reason, turn = score_until(s, 20)
        self.assertEqual((winner, turn), ("union", 20))
        self.assertEqual([h["event"] for h in s["victory"]["history"]], ["seized", "lapsed"])

    def test_seizure_after_the_relief_turn_wins_once_it_is_made(self):
        s = seize_state()
        unit(s, "G1")["pos"] = [12, 4]
        self.assertEqual(score_until(s, 12)[0], None)
        unit(s, "G1")["pos"] = list(BRIDGE)
        self.assertEqual(score_until(s, 20)[::2], ("confederate", 14))

    def test_without_relief_the_seizure_must_last_to_the_deadline(self):
        s = seize_state(dataclasses.replace(SEIZE, relief_turn=None))
        winner, reason, turn = score_until(s, 20)
        self.assertEqual((winner, turn), ("confederate", 20))
        self.assertIn("deadline", reason)

    def test_destroyed_objective_bridge_is_a_defender_win(self):
        s = seize_state(bridges=(CANAL_BRIDGE,))
        s["cells"][grid.key(list(BRIDGE))]["bridge_state"] = "destroyed"
        next(f for f in s["map_features"] if f["id"] == "canal-bridge")["state"] = "destroyed"
        winner, reason, turn = score_until(s, 20)
        self.assertEqual((winner, turn), ("union", 1))
        self.assertIn("destroyed", reason)

    def test_every_objective_must_be_seized(self):
        s = seize_state(dataclasses.replace(SEIZE, more_objectives=((20, 4),)))
        self.assertEqual(score_until(s, 19)[0], None)  # Only the first is held.
        winner, _, turn = score_until(s, 20)
        self.assertEqual((winner, turn), ("union", 20))

    def test_registration_refuses_bad_seize_and_hold_parameters(self):
        cases = {
            "relief_turn": dataclasses.replace(SEIZE, relief_turn=0),
            "relief_turn ": dataclasses.replace(SEIZE, relief_turn=21),
            "more_objectives": dataclasses.replace(SEIZE, more_objectives=((40, 4),)),
            "more_objectives ": dataclasses.replace(SEIZE, more_objectives=(BRIDGE,)),
        }
        for name, bad in cases.items():
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, name.strip()):
                    validate(seize_entry(bad))
        for kind in ("hold-objective",):
            with self.subTest(kind):
                with self.assertRaisesRegex(ValueError, "relief_turn and more_objectives"):
                    validate(seize_entry(dataclasses.replace(SEIZE, kind=kind)))


if __name__ == "__main__":
    unittest.main()
