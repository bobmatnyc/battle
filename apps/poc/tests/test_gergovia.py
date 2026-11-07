"""Gergovia, 52 BCE: the catalog entry, its variants, the scripted policies
and the headless run. Plan: docs/research/57; runs: docs/research/62.

No test asserts a winner: the policies act as Caesar describes, and the
engine decides the outcome.
"""

import tempfile
import unittest

from battle import engine, victory
from battle.bootstrap import PLAYER_SCENARIOS, build_headless_scenarios
from battle.broadcast import hears
from battle.command_policy import SCRIPTED_POLICIES, scripted_policy
from battle.gergovia_policy import (
    GALLIC_ORDERS, POLICIES, ROMAN_ORDERS, gallic_actions, roman_actions, roman_no_cover_actions, roman_runner_actions,
)
from battle.presentation import ROMAN_VOICE_PROFILE
from battle.scenario_command import ROMAN_COMMUNICATIONS, TACTICS_V11
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate
from battle.scenario_gergovia import (
    AS_DEFAULT, BELOW_GATE, DC0, DEADLINE, FORWARD, GALLIC_DELAYS, GALLIC_POLICY, GERGOVIA_RECALL as ENTRY,
    PURSUIT, PUSH_TO, RALLY, RECALL_REACH, RECALL_TURN, RETURN_TURN, ROMAN_NO_COVER_POLICY, ROMAN_POLICY, ROMAN_RUNNER_POLICY,
    SEXTIUS_POST, SEXTIUS_TURN, TENTH, UNDER_WALL, VALLEY, VARIANTS, gallic_delay_policy,
)
from test_hill_223 import digest, run, unit
from test_pegasus_engine import advance


def differences(entry):
    """The snapshot paths in which ``entry`` differs from the default, apart
    from its labels: ``units.<id>.<field>`` per unit, else the top-level key
    (as ``test_hill_223.differences``)."""
    a, b = build_state(entry), build_state(ENTRY)
    out = set()
    for k in set(a) | set(b):
        if k == "scenario" or a.get(k) == b.get(k):
            continue
        if k != "units":
            out.add(k)
            continue
        for x, y in zip(a["units"], b["units"]):
            out |= {f"units.{x['id']}.{f}" for f in set(x) | set(y) if x.get(f) != y.get(f)}
    return out


def receipts(s):
    return s["broadcasts"][0]["receipts"]


EAST_OF_VALLEY = (20, 17)  # In reach of the Tenth and not behind the valley (authored test hex).


class GergoviaEntryTests(unittest.TestCase):
    def test_entry_registers_in_the_headless_catalog_after_a_dry_run(self):
        self.assertEqual(build_headless_scenarios().resolve("gergovia-recall"), ENTRY)
        self.assertNotIn(ENTRY, PLAYER_SCENARIOS)  # Doc 57 §9 q7: headless only.
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "gergovia-recall-v1"))
        self.assertEqual(s["sides"], [{"id": "roman", "name": "Roman", "role": "attacker"},
                                      {"id": "gallic", "name": "Gallic", "role": "defender"}])
        self.assertEqual((ENTRY.start_time, ENTRY.player), ("12:00:00", "roman"))

    def test_entry_takes_the_doc_57_defaults(self):
        s = build_state(ENTRY)
        self.assertEqual((s["max_turns"], DEADLINE * 30), (240, 120 * 60))  # 120 minutes.
        signal = s["broadcasts"][0]
        self.assertEqual((signal["turn"], signal["reach"], signal["stance"], signal["destination"]),
                         (1, 8, "retreat", list(RALLY)))  # D85 (Bob 2026-11-07 13:10Z): earlier recall.
        self.assertEqual(signal["block_hexes"], [list(p) for p in VALLEY])
        self.assertEqual((ENTRY.communications, ENTRY.voice_profile, ENTRY.tactics),
                         (ROMAN_COMMUNICATIONS, ROMAN_VOICE_PROFILE, TACTICS_V11))
        self.assertEqual(set(ENTRY.weapons), {u["weapon_class"] for u in s["units"]})
        # S1: every forward group pursues to the gate until it hears the recall; the default 2 officers.
        for uid in FORWARD:
            u = unit(s, uid)
            self.assertEqual((u["exploit"], u["officers"]), (PURSUIT, 2), uid)
        self.assertEqual((unit(s, "R8f")["initial"], unit(s, "R8f")["rout_strength"]), (4, 0))
        self.assertEqual([unit(s, u)["initial"] for u in FORWARD[:4]], [60] * 4)
        self.assertNotIn("AE", {u["id"] for u in s["units"]})  # Doc 57 §9 q6: no Aedui by default.
        self.assertEqual((s["victory"]["force"], s["victory"]["recover_needed"]), (244, 122))
        self.assertEqual(ENTRY.scripted, {"roman": ROMAN_POLICY, "gallic": GALLIC_POLICY})

    def test_every_basis_carries_a_kind_and_each_open_question_cites_the_ruling(self):
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        cited = " ".join(v for v in ENTRY.provenance.values() if DC0 in v)
        for q in range(1, 9):
            self.assertIn(f"doc 57 §9 q{q}", cited)
        self.assertRegex(ENTRY.provenance["signal"], r"S60 VII\.47")
        for name, variant in VARIANTS.items():
            self.assertRegex(variant.source, r"S6[0-4]|^authored|^sourced|^inferred", name)

    def test_each_named_variant_differs_only_in_its_own_question(self):
        forward = lambda *fields: {f"units.{u}.{f}" for u in FORWARD for f in fields}  # noqa: E731
        centuries = lambda *fields: {f"units.{u}.{f}" for u in FORWARD[:4] for f in fields}  # noqa: E731
        expected = {
            "recall-audible": {"broadcasts"},
            "recall-by-runner": set(), "no-cover": set(),
            "ardour": forward("exploit") | {"friendly_reports"},
            "leaders-fall": forward("officers", "officer_step") | {"friendly_reports"},
            "aedui-misread": {"units", "contacts", "friendly_reports", "feature_reports", "commanders"},
            **{f"gallic-delay-{d}": set() for d in GALLIC_DELAYS},
            **{f"strength-{n}": centuries("initial", "strength", "ammo", "officer_step")
               | {"friendly_reports", "victory"} for n in (40, 80)},
            **{name: set() for name in AS_DEFAULT},
        }
        self.assertEqual(set(VARIANTS), set(expected))
        for name, variant in VARIANTS.items():
            with self.subTest(name):
                self.assertEqual(variant.entry.variant, name)
                self.assertRegex(variant.question, r"doc 57 §8")
                dry_run(validate(variant.entry))
                self.assertNotEqual(variant.entry.labels, ENTRY.labels)
                self.assertNotIn(variant.entry.id, build_headless_scenarios().ids())
                if name == "aedui-misread":  # One added unit; every default unit is unchanged.
                    added = build_state(variant.entry)["units"]
                    self.assertEqual(added[:-1], build_state(ENTRY)["units"])
                    self.assertEqual((added[-1]["id"], added[-1]["side"], added[-1]["fire_posture"]),
                                     ("AE", "gallic", "hold_fire"))
                    continue
                self.assertEqual(differences(variant.entry), expected[name])
        scripted = {n: VARIANTS[n].entry.scripted for n in ("recall-by-runner", "no-cover")}
        self.assertEqual(scripted, {"recall-by-runner": {"roman": ROMAN_RUNNER_POLICY, "gallic": GALLIC_POLICY},
                                    "no-cover": {"roman": ROMAN_NO_COVER_POLICY, "gallic": GALLIC_POLICY}})
        for d in GALLIC_DELAYS:
            self.assertEqual(VARIANTS[f"gallic-delay-{d}"].entry.scripted["gallic"], gallic_delay_policy(d))


def sounded_early(entry, turn=2, **positions):
    """``entry``'s state with the recall moved to ``turn`` and units placed at
    ``positions``, advanced to it: reach, block and binding on the starting
    geometry, apart from the default's own interval."""
    s = build_state(entry)
    for uid, pos in positions.items():
        unit(s, uid)["pos"] = list(pos)
    s["broadcasts"][0]["turn"] = turn
    return advance(s, turn)


class GergoviaSignalTests(unittest.TestCase):
    """The recall, its reach and the valley block, through the engine."""

    def test_the_valley_blocks_the_recall_and_reach_bounds_it(self):
        s = sounded_early(ENTRY)
        self.assertEqual((s["broadcasts"][0]["sounded_turn"], s["broadcasts"][0]["sounder_id"]), (2, "RX"))
        got = {uid: (r["heard"], r["reason"]) for uid, r in receipts(s).items() if uid in FORWARD}
        self.assertEqual(got, {"R8a": (False, "blocked"), **{u: (False, "out_of_reach") for u in FORWARD[1:]}})
        # S1: an unheard group keeps its mission and its pursuit.
        self.assertEqual({(unit(s, u)["stance"], unit(s, u)["exploit_state"]) for u in FORWARD}, {("hold", "pressing")})
        signal = s["broadcasts"][0]
        self.assertEqual(hears(signal, list(TENTH), [14, 17]), (False, "blocked"))
        self.assertEqual(hears(dict(signal, block_hexes=[]), list(TENTH), [14, 17]), (True, "heard"))
        self.assertEqual((ENTRY.broadcasts[0].turn, RECALL_REACH), (RECALL_TURN, 8))

    def test_the_default_recall_sounds_before_the_forward_force_breaks(self):
        # D85 (Bob 2026-11-07 13:10Z): earlier recall. At interval 40 the default
        # battle ended at 36, before the recall (doc 62 §5); now it sounds first.
        s = build_state(ENTRY)
        while s["status"] == "active" and s["broadcasts"][0]["sounded_turn"] is None and s["turn"] < DEADLINE:
            s = advance(s)
        signal = s["broadcasts"][0]
        self.assertEqual((s["status"], signal["sounded_turn"], signal["sounder_id"]), ("active", RECALL_TURN, "RX"))
        self.assertLess(RECALL_TURN, 19)  # VII.47: the recall precedes the pursuit's arrival at the gate (19).
        got = {uid: (r["heard"], r["reason"]) for uid, r in receipts(s).items() if uid in FORWARD}
        self.assertEqual(got, {"R8a": (False, "blocked"), **{u: (False, "out_of_reach") for u in FORWARD[1:]}})
        audible = advance(build_state(VARIANTS["recall-audible"].entry), RECALL_TURN)
        self.assertEqual((audible["status"], {receipts(audible)[u]["obeyed"] for u in FORWARD}), ("active", {True}))

    def test_a_group_in_reach_on_the_tenths_side_hears_and_obeys(self):
        s = sounded_early(ENTRY, R8a=EAST_OF_VALLEY)
        self.assertEqual((receipts(s)["R8a"]["heard"], receipts(s)["R8a"]["obeyed"]), (True, True))
        self.assertEqual((unit(s, "R8a")["stance"], unit(s, "R8a")["target"]), ("retreat", list(RALLY)))

    def test_recall_audible_reaches_every_forward_group(self):
        s = sounded_early(VARIANTS["recall-audible"].entry)
        self.assertTrue(all(receipts(s)[u]["heard"] and receipts(s)[u]["obeyed"] for u in FORWARD))
        self.assertEqual({unit(s, u)["stance"] for u in FORWARD}, {"retreat"})
        self.assertEqual({unit(s, u)["exploit_state"] for u in FORWARD}, {"stopped"})


class GergoviaArdourTests(unittest.TestCase):
    """Ardour (Caesar's VII.52 reading) against signal failure (VII.47)."""

    def test_both_readings_pursue_to_the_gate_from_the_start(self):
        for entry in (ENTRY, VARIANTS["ardour"].entry):
            s = advance(build_state(entry), 1)
            started = [e for e in s["events"] if e["kind"] == "exploit_started"]
            self.assertEqual(sorted(e["unit_id"] for e in started), sorted(FORWARD), entry.id)
            self.assertTrue(all(e["press_to"] == list(BELOW_GATE) for e in started))
        self.assertEqual({unit(build_state(ENTRY), u)["exploit"]["recall_binding"] for u in FORWARD}, {True})
        self.assertEqual({unit(build_state(VARIANTS["ardour"].entry), u)["exploit"]["recall_binding"]
                          for u in FORWARD}, {False})

    def test_a_heard_recall_stops_the_pursuit_under_signal_failure_but_not_under_ardour(self):
        result = {}
        for name, entry in (("signal-failure", ENTRY), ("ardour", VARIANTS["ardour"].entry)):
            s = sounded_early(entry, R8a=EAST_OF_VALLEY)
            u = unit(s, "R8a")
            result[name] = (receipts(s)["R8a"]["heard"], u["stance"], u.get("exploit_state"))
        # Both hear and take up the recall as the mission; only ardour keeps pressing.
        self.assertEqual(result, {"signal-failure": (True, "retreat", "stopped"),
                                  "ardour": (True, "retreat", "pressing")})

    def test_an_unheard_group_presses_on_under_both_readings(self):
        for entry in (ENTRY, VARIANTS["ardour"].entry):
            s = sounded_early(entry, turn=20)
            self.assertFalse(receipts(s)["R8c"]["heard"], entry.id)
            self.assertLess(unit(s, "R8c")["pos"][1], 17)
            self.assertEqual(unit(s, "R8c")["exploit_state"], "pressing")


class GergoviaVictoryTests(unittest.TestCase):
    def test_recover_force_scores_the_forward_force_at_the_tenths_line(self):
        kind = victory.KINDS["recover-force"]
        for placed, strength, won in ((("R8a", "R8b"), 60, False), (("R8a", "R8b", "R8c"), 60, True),
                                      (("R8a", "R8b", "R8c"), 40, False), (("RX", "R13"), 80, False)):
            with self.subTest(placed=placed, strength=strength):
                s = build_state(ENTRY)
                self.assertEqual(kind.score(s), (None, None))
                for uid in placed:
                    unit(s, uid).update(pos=list(RALLY), strength=strength)
                self.assertEqual(kind.score(s)[0] == "roman", won)
        s = build_state(ENTRY)
        for uid in FORWARD:
            unit(s, uid)["strength"] = 24
        self.assertEqual(kind.score(s)[0], "gallic")  # 5 * 24 = 120 < 122: the force can no longer recover.
        s = build_state(ENTRY)
        s["turn"] = DEADLINE
        self.assertEqual(kind.score(s), ("gallic", "The forward force was not brought back to the rally point "
                                                   "by the deadline."))


class GergoviaPolicyTests(unittest.TestCase):
    def test_policies_are_registered_and_chosen_for_their_sides(self):
        for policy in (ROMAN_POLICY, ROMAN_NO_COVER_POLICY, ROMAN_RUNNER_POLICY, GALLIC_POLICY,
                       *map(gallic_delay_policy, GALLIC_DELAYS)):
            self.assertIn(policy, SCRIPTED_POLICIES)
        self.assertEqual((scripted_policy(ENTRY, "roman"), scripted_policy(ENTRY, "gallic")),
                         (ROMAN_POLICY, GALLIC_POLICY))

    def test_every_order_carries_a_source_locator_or_a_label(self):
        for order in ROMAN_ORDERS + GALLIC_ORDERS:
            with self.subTest(order["id"]):
                self.assertRegex(order["source"], r"S60 VII\.\d+")
                self.assertTrue(order["provenance"].startswith(PROVENANCE))

    def test_roman_policies_send_sextius_and_the_runner_recall_once(self):
        view = engine.view(build_state(ENTRY), "roman")
        sextius = {"unit_id": "R13", "stance": "move", "destination": list(SEXTIUS_POST)}
        view["turn"] = SEXTIUS_TURN - 1
        self.assertEqual(roman_actions(view), ([], []))
        view["turn"] = SEXTIUS_TURN
        self.assertEqual(roman_actions(view), ([], [sextius]))
        self.assertEqual(roman_no_cover_actions(view), ([], []))
        view["orders"] = [dict(sextius, id="o1")]
        self.assertEqual(roman_actions(view), ([], []))
        view.update(turn=RECALL_TURN, orders=[])
        sent = roman_runner_actions(view)[1]
        self.assertEqual(sent, [{"unit_id": u, "stance": "retreat", "destination": list(RALLY)} for u in FORWARD[:3]])
        view["orders"] = [dict(o, id=f"o{i}") for i, o in enumerate(sent)]
        self.assertEqual([o["unit_id"] for o in roman_runner_actions(view)[1]], ["R8d", "R8f"])
        view["command"]["operational"] = False
        self.assertEqual(roman_runner_actions(view), ([], []))

    def test_the_gallic_masses_return_at_their_turn_then_push_only_once_romans_reach_the_wall(self):
        view = engine.view(build_state(ENTRY), "gallic")
        view["turn"] = RETURN_TURN - 1
        self.assertEqual(gallic_actions(view), ([], []))
        view["turn"] = RETURN_TURN
        back = [{"unit_id": u, "stance": "move", "destination": list(h)} for u, h in UNDER_WALL.items()]
        self.assertEqual(gallic_actions(view), ([], back))
        view["orders"] = [dict(o, id=f"o{i}") for i, o in enumerate(back)]
        view["contacts"] = [{"id": "c1", "pos": [10, 17], "age": 0}]
        self.assertEqual(gallic_actions(view), ([], []))  # Romans in the camps, not at the wall.
        view["contacts"] = [{"id": "c1", "pos": [11, 3], "age": 0}]
        push = [{"unit_id": u, "stance": "move", "destination": list(PUSH_TO)} for u in UNDER_WALL]
        self.assertEqual(gallic_actions(view), ([], push))
        view["contacts"] = [{"id": "c1", "pos": [11, 3], "age": 5}]
        self.assertEqual(gallic_actions(view), ([], []))  # A stale contact does not count.
        view["contacts"] = [{"id": "c1", "pos": [11, 3]}]
        self.assertEqual(gallic_actions(view), ([], []))  # A contact with no age is stale, not fresh.
        delayed = POLICIES[gallic_delay_policy(GALLIC_DELAYS[0])]
        view.update(turn=RETURN_TURN, orders=[], contacts=[])
        self.assertEqual(delayed(view), ([], []))
        view["turn"] = RETURN_TURN + GALLIC_DELAYS[0]
        self.assertEqual(delayed(view), ([], back))


class GergoviaRunTests(unittest.TestCase):
    def test_two_headless_runs_give_the_same_battle_and_replay_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = run(ENTRY, tmp, "one.sqlite")
            two = run(ENTRY, tmp, "two.sqlite")
        for result, final in (one, two):
            self.assertEqual(result["replay"]["status"], "identical")
            self.assertEqual((result["run"]["player_policy"], result["run"]["opponent"]),
                             (ROMAN_POLICY, GALLIC_POLICY))
            self.assertEqual(final["scenario"], "gergovia-recall-v1")
        self.assertEqual(digest(*one), digest(*two))


if __name__ == "__main__":
    unittest.main()
