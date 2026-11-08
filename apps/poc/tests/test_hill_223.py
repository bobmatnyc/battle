"""Hill 223, 8 October 1918: the catalog entry, its variants, the scripted
policies and the headless run. Plan: docs/research/56; runs: docs/research/61.

The policies act as the sources describe or doc 56 infers, and the engine
decides the outcome. One test pins the scripted default's result (bt-T17), so
a rules change that flips it fails by name.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from battle import engine, grid, victory
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import PLAYER_SCENARIOS, build_headless, build_headless_scenarios, build_replay
from battle.command_policy import SCRIPTED_POLICIES, scripted_policy
from battle.hill223_policy import (
    AMERICAN_ORDERS, GERMAN_ORDERS, company_g_actions, company_reinforces_actions, german_actions,
)
from battle.presentation import WWI_VOICE_PROFILE
from battle.scenario_command import TACTICS_V11, WWI_COMMUNICATIONS
from battle.scenario_entry import PROVENANCE, build_state, dry_run, validate
from battle.scenario_hill223 import (
    AMERICAN_POLICY, AS_DEFAULT, DC0, DEADLINE, GERMAN_POLICY, HILL_223_PATROL as ENTRY, PATROL_START,
    PATROL_TARGET, REINFORCE_POLICY, REINFORCE_TURN, SHACK, SURRENDER_G1, SURRENDER_G2, VARIANTS, hill_223_col,
    post,
)
from test_pegasus_engine import advance


def unit(s, uid):
    return next(u for u in s["units"] if u["id"] == uid)


def differences(entry):
    """The snapshot paths in which ``entry`` differs from the default, apart
    from its labels: ``units.<id>.<field>`` per unit, else the top-level key."""
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


def first(s, kind, limit, **match):
    """Advance ``s`` until an event of ``kind`` matching ``match`` appears."""
    for _ in range(limit):
        found = [e for e in s["events"] if e["kind"] == kind and all(e.get(k) == v for k, v in match.items())]
        if found or s["status"] != "active":
            return s, found
        s = advance(s, 1)
    return s, []


def run(entry, tmp, name="hill223.sqlite"):
    db = Path(tmp) / name
    scenarios = None if entry is ENTRY else ScenarioRegistry([entry])
    # Batch store (docs/research/54 precedent): the replay re-runs the recorded inputs.
    result = build_headless(db, scenario_id=entry.id, scenarios=scenarios, keyframe_every=0).run()
    return result, build_replay(db).repository.load(result["game_id"])


def digest(result, final):
    summary = {k: v for k, v in result.items() if k != "game_id"}
    return hashlib.sha256(json.dumps({"result": summary, "final": final}, sort_keys=True).encode()).hexdigest()


class Hill223EntryTests(unittest.TestCase):
    def test_entry_registers_in_the_headless_catalog_after_a_dry_run(self):
        self.assertEqual(build_headless_scenarios().resolve("hill-223-patrol"), ENTRY)
        # docs/research/75: doc 56 §9 q6 kept it headless at first; it is now a player scenario,
        # after Pegasus, and its German side plays its scripted control on the desk.
        self.assertIn(ENTRY, PLAYER_SCENARIOS)
        self.assertTrue(ENTRY.desk_scripted_opponent)
        dry_run(validate(ENTRY))
        s = build_state(ENTRY)
        self.assertEqual((s["rules"], s["scenario"]), ("poc-13", "hill-223-patrol-v1"))
        self.assertEqual(s["sides"], [{"id": "american", "name": "American", "role": "attacker"},
                                      {"id": "german", "name": "German", "role": "defender"}])
        self.assertEqual((ENTRY.date, ENTRY.start_time, ENTRY.player), ("1918-10-08", "06:45:00", "american"))

    def test_entry_takes_the_doc_56_defaults(self):
        s = build_state(ENTRY)
        self.assertEqual(DEADLINE * 30, (10 * 60 + 30 - (6 * 60 + 45)) * 60)  # 06:45 to 10:30.
        self.assertEqual((s["max_turns"], s["victory"]["kind"]), (DEADLINE, "raid-and-return"))
        self.assertEqual({u["observation_range"] for u in s["units"]}, {3})
        self.assertEqual(hill_223_col() - 5, 10)  # Valley 500 yd = 10 hexes (S57).
        self.assertEqual(unit(s, "D1")["surrender"], SURRENDER_G1)
        self.assertEqual([u["id"] for u in s["units"] if "surrender" in u], ["D1"])
        self.assertEqual((ENTRY.communications, ENTRY.voice_profile, ENTRY.voice_reach, ENTRY.tactics),
                         (WWI_COMMUNICATIONS, WWI_VOICE_PROFILE, 1, TACTICS_V11))
        a1 = unit(s, "A1")
        self.assertEqual((a1["initial"], a1["officers"], a1["officer_step"], a1["rout_strength"]), (17, 4, 3, 4))
        self.assertEqual((a1["fire_posture"], a1["press_assault"], a1["exploit"]["press_to"]),
                         ("hold_fire", True, list(post())))
        self.assertEqual(sum(u["initial"] for u in s["units"] if u["side"] == "german"), 205)
        self.assertEqual({u["id"] for u in s["units"] if "facing" in u}, {"D1", "D2", "D3", "D4"})
        self.assertEqual(s["victory"]["return_needed"], 5)  # A quarter of 17, rounded up.

    def test_the_return_resumes_after_a_local_withdrawal_per_the_d7b_ruling(self):
        # D7b ruling 2026-11-07: "Return resumes after a local withdrawal clears."
        for entry in [ENTRY] + [v.entry for v in VARIANTS.values()]:
            with self.subTest(entry.id):
                self.assertIs(unit(build_state(entry), "A1")["exploit"]["resume_after_withdrawal"], True)
        self.assertIn("per D7b ruling 2026-11-07", ENTRY.provenance["return"])
        self.assertIn("per D7b ruling 2026-11-07", next(o for o in AMERICAN_ORDERS if o["id"] == "return")["provenance"])

    def test_every_basis_carries_a_kind_and_each_open_question_cites_the_ruling(self):
        self.assertTrue(all(v.startswith(PROVENANCE) for v in ENTRY.provenance.values()))
        cited = " ".join(v for v in ENTRY.provenance.values() if DC0 in v)
        for q in range(1, 8):
            self.assertIn(f"doc 56 §9 q{q}", cited)
        for field in ("surrender", "german.command_unit"):
            self.assertTrue(ENTRY.provenance[field].startswith("inferred:"), field)
        self.assertTrue(ENTRY.provenance["units.patrol"].startswith("sourced:"))

    def test_each_named_variant_differs_only_in_its_own_question(self):
        valley = {"cells", "briefing_cells", "hq", "rally_points", "victory", "friendly_reports",
                  "units.AHQ.pos", "units.A2.pos", "units.A3.pos", "units.A1.exploit"}
        expected = {
            "valley-narrow": valley, "valley-wide": valley,
            "surrender-on-threat": {"units.D1.surrender", "friendly_reports"},
            "gun-turn-delay-2": {f"units.{g}.reorient_turns" for g in ("D2", "D3", "D4")} | {"friendly_reports"},
            "gun-turn-delay-4": {f"units.{g}.reorient_turns" for g in ("D2", "D3", "D4")} | {"friendly_reports"},
            "observation-2": {f"units.{u.id}.observation_range" for u in ENTRY.units},
            "observation-4": {f"units.{u.id}.observation_range" for u in ENTRY.units},
            "company-reinforces": set(), **{name: set() for name in AS_DEFAULT},
        }
        self.assertEqual(set(VARIANTS), set(expected))
        for name, variant in VARIANTS.items():
            with self.subTest(name):
                self.assertEqual(variant.entry.variant, name)
                self.assertRegex(variant.question, r"doc 56 §8")
                dry_run(validate(variant.entry))
                self.assertNotEqual(variant.entry.labels, ENTRY.labels)
                self.assertNotIn(variant.entry.id, build_headless_scenarios().ids())
                self.assertEqual(differences(variant.entry), expected[name])
        self.assertEqual(VARIANTS["company-reinforces"].entry.scripted["american"], REINFORCE_POLICY)
        self.assertEqual(build_state(VARIANTS["surrender-on-threat"].entry)["units"][4]["surrender"], SURRENDER_G2)
        self.assertEqual(hill_223_col(5) - hill_223_col(18), -13)

    def test_a_sides_report_does_not_share_nested_unit_data(self):
        # The departure order is a nested override; completing it in the truth
        # must not change the American report, which only delivery may change.
        s = build_state(ENTRY)
        unit(s, "A1")["mission_result"]["status"] = "completed"
        self.assertEqual(s["friendly_reports"]["american"]["A1"]["mission_result"]["status"], "active")


class Hill223PolicyTests(unittest.TestCase):
    def test_policies_are_registered_and_chosen_for_their_sides(self):
        for policy in (AMERICAN_POLICY, GERMAN_POLICY, REINFORCE_POLICY):
            self.assertIn(policy, SCRIPTED_POLICIES)
        self.assertEqual((scripted_policy(ENTRY, "american"), scripted_policy(ENTRY, "german")),
                         (AMERICAN_POLICY, GERMAN_POLICY))

    def test_every_order_carries_a_source_locator_or_a_label(self):
        for order in AMERICAN_ORDERS + GERMAN_ORDERS:
            with self.subTest(order["id"]):
                self.assertRegex(order["source"], r"S(40|57|58)|^authored:")
                self.assertTrue(order["provenance"].startswith(PROVENANCE))

    def test_only_the_reinforcement_variant_sends_an_order_and_only_once(self):
        view = engine.view(build_state(VARIANTS["company-reinforces"].entry), "american")
        for turn in (0, REINFORCE_TURN - 1, REINFORCE_TURN, 300):
            view["turn"] = turn
            self.assertEqual(company_g_actions(view), ([], []))
            self.assertEqual(german_actions(engine.view(build_state(ENTRY), "german")), ([], []))
        view["turn"] = REINFORCE_TURN - 1
        self.assertEqual(company_reinforces_actions(view), ([], []))
        view["turn"] = REINFORCE_TURN
        sent = [{"unit_id": "A3", "stance": "move", "destination": list(PATROL_START)}]
        self.assertEqual(company_reinforces_actions(view), ([], sent))
        view["orders"] = [dict(sent[0], id="o1")]
        self.assertEqual(company_reinforces_actions(view), ([], []))
        view["orders"] = []
        view["command"]["operational"] = False
        self.assertEqual(company_reinforces_actions(view), ([], []))


class Hill223RulesTests(unittest.TestCase):
    """The doc 56 mechanisms on the entry itself, through the engine."""

    def test_the_patrol_holds_fire_until_struck_then_returns_fire(self):
        s, volleys = first(build_state(ENTRY), "volley", 80, unit_id="A1")
        self.assertTrue(volleys, "the patrol never fired")
        self.assertTrue(volleys[0]["returning_fire"])
        struck = [e["turn"] for e in s["events"] if e["kind"] == "unit_under_fire" and e["unit_id"] == "A1"]
        self.assertTrue(struck and min(struck) <= volleys[0]["turn"])
        self.assertTrue(all(e["kind"] != "volley" or e["unit_id"] != "A1" or e["turn"] >= min(struck)
                            for e in s["events"]))

    def test_the_command_group_yields_to_the_patrol_and_the_captives_are_conserved(self):
        s, yielded = first(build_state(ENTRY), "unit_surrendered", 80, unit_id="D1")
        self.assertEqual([(e["holder_id"], e["count"]) for e in yielded], [("A1", 75)])
        d1 = unit(s, "D1")
        self.assertEqual((d1["status"], d1["strength"], d1["surrendered"]), ("lost", 0, True))
        record = s["captives"][0]
        self.assertEqual((record["from_unit"], record["holder_id"], record["count"], record["status"]),
                         ("D1", "A1", 75, "held"))
        self.assertEqual(unit(s, "A1")["captives"], 75)

    def test_raid_and_return_scores_the_entrys_raid(self):
        kind = victory.KINDS["raid-and-return"]
        for strength, captives, won in ((17, 0, False), (17, 1, True), (4, 1, False), (5, 1, True)):
            with self.subTest(strength=strength, captives=captives):
                s = build_state(ENTRY)
                unit(s, "A1")["pos"] = list(PATROL_TARGET)
                self.assertEqual(kind.score(s), (None, None))
                self.assertEqual(s["victory"]["raided_turn"], 0)
                s["turn"] = 1
                unit(s, "A1").update(pos=list(post()), strength=strength)
                if captives:
                    s["captives"] = [{"id": "K1", "count": captives, "from_unit": "D1", "from_side": "german",
                                      "holder_id": "A1", "holder_side": "american", "turn": 1, "status": "held"}]
                self.assertEqual(kind.score(s)[0] == "american", won)
        self.assertEqual(grid.distance(PATROL_TARGET, SHACK), 1)

    def test_the_deadline_reason_names_the_unmet_condition_on_the_entry(self):
        # The surrender-on-threat run at 679b637: the patrol home with 12 men and no captives at the deadline.
        kind = victory.KINDS["raid-and-return"]
        for pos, reason in ((post(), "The raiders reached the German command post and 12 of them came back by the "
                                     "deadline, but they brought back 0 captives against the 1 required."),
                            (PATROL_TARGET, "The German kept the raiders from returning by the deadline.")):
            with self.subTest(pos=pos):
                s = build_state(ENTRY)
                unit(s, "A1")["pos"] = list(PATROL_TARGET)
                kind.score(s)
                s["turn"] = s["max_turns"]
                unit(s, "A1").update(pos=list(pos), strength=12)
                self.assertEqual(kind.score(s), ("german", reason))


class Hill223RunTests(unittest.TestCase):
    def test_two_headless_runs_give_the_same_battle_and_replay_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = run(ENTRY, tmp, "one.sqlite")
            two = run(ENTRY, tmp, "two.sqlite")
        for result, final in (one, two):
            self.assertEqual(result["replay"]["status"], "identical")
            self.assertEqual((result["run"]["player_policy"], result["run"]["opponent"]),
                             (AMERICAN_POLICY, GERMAN_POLICY))
            self.assertEqual(final["scenario"], "hill-223-patrol-v1")
        self.assertEqual(digest(*one), digest(*two))

    def test_the_scripted_default_ends_in_an_american_win_at_turn_27(self):
        # bt-T17: the outcome observed at a01a58b.
        with tempfile.TemporaryDirectory() as tmp:
            result, final = run(ENTRY, tmp)
        self.assertEqual((final["status"], final["winner"], final["turn"]), ("complete", "american", 27))
        self.assertEqual(result["winner"], "american")


if __name__ == "__main__":
    unittest.main()
