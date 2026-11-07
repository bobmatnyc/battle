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

from battle import grid, runtime, victory
from battle.scenario_entry import UnitEntry, VictoryEntry, build_state, dry_run, validate
from battle.scenario_wwii import DemolitionEntry
from battle.storage import Store
from test_gateway_push import events, unit
from test_pegasus_engine import BRIDGE, CANAL_BRIDGE, advance, night, night_entry

# The guard stands north of the bridge, adjacent to it; B2 two hexes south of
# it is in sight at a night range of 2. Both hold their fire, so neither fires.
GUARD = (12, 9)
QUIET = {"fire_posture": "hold_fire"}
UNITS = (
    UnitEntry("B1", "union", "Company headquarters", (12, 16), QUIET),
    UnitEntry("B2", "union", "Leading platoon", (12, 11), QUIET),
    UnitEntry("G1", "confederate", "Bridge guard", GUARD, QUIET),
)
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
