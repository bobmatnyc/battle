"""Milestone 2: a model plays one side headless; proven with fake providers only."""

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from battle import command_policy, engine, runtime, scenario
from battle.adapters.openrouter import OpenRouterProvider
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import build_headless, build_replay
from battle.command_policy import (
    MISSIONS,
    OPPONENT_POLICY,
    PROMPT_VERSION,
    fallback_orders,
)
from battle.config import Settings
from battle.services.commander import CommanderService

TELEMETRY_KEYS = {
    "requested_model",
    "model",
    "effort",
    "latency_ms",
    "usage",
    "response_id",
    "proposed_orders",
    "validation",
    "rejected_proposal",
    "fallback",
    "fallback_reason",
    "prompt_version",
    "side",
}


class FakeProvider:
    """Answers from the authorized observation it receives; records every call."""

    available = True
    model = "fake/player-model"
    effort = "high"

    def __init__(self, propose=None, error=None):
        self.propose = propose or (lambda payload: fallback_orders(payload["observation"]))
        self.error = error
        self.calls = []

    def request(self, instruction, payload):
        self.calls.append((instruction, copy.deepcopy(payload)))
        if self.error:
            raise self.error
        orders = self.propose(payload)
        return {"text": "General, orders follow.", "orders": orders}, {
            "model": "fake/player-model-2026",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            "response_id": f"gen-{len(self.calls)}",
        }


def run_headless(tmp, provider, side="union"):
    runner = build_headless(
        Path(tmp) / "battle.sqlite",
        player_side=side,
        player_provider="openrouter",
        provider=provider,
    )
    return runner, runner.run()


def player_decisions(runner, result, side="union"):
    state = runner.repository.load(result["game_id"])
    return state, [d for d in state["decisions"] if d.get("side") == side]


def advanced_state(turns=24):
    """Scripted battle state with contacts, built only through recorded actions."""
    simulation = RulesSimulation()
    commander = CommanderService(simulation, FakeProvider())
    state = scenario.create()
    while state["turn"] < turns:
        decision = None
        if state["turn"] % 3 == 0:
            decision = commander.decide(state, side="confederate", mode="scripted")
        state = simulation.apply(state, {"type": "advance", "decision": decision})
    return state


class HeadlessPlayerTests(unittest.TestCase):
    def test_model_player_run_records_side_decisions_and_replays(self):
        provider = FakeProvider()
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = run_headless(tmp, provider)
            state, mine = player_decisions(runner, result)
            self.assertEqual(state["status"], "complete")
            self.assertEqual(result["turns"], state["turn"])
            self.assertEqual(len(mine), len(provider.calls))
            self.assertEqual(len(mine), 20)
            model_made = [d for d in mine if d["source"] == "openrouter"]
            self.assertTrue(model_made)
            for decision in mine:
                self.assertTrue(TELEMETRY_KEYS <= set(decision), decision.keys())
                self.assertEqual(decision["fallback"], decision["source"] != "openrouter")
            first = model_made[0]
            self.assertEqual(first["requested_model"], "fake/player-model")
            self.assertEqual(first["model"], "fake/player-model-2026")
            self.assertEqual(first["effort"], "high")
            self.assertEqual(first["response_id"], "gen-1")
            self.assertEqual(first["usage"]["completion_tokens"], 20)
            self.assertEqual(first["validation"], {"valid": True, "error": None})
            self.assertGreaterEqual(first["latency_ms"], 0)
            union_orders = [o for o in state["orders"] if o["source"] == "openrouter"]
            self.assertTrue(union_orders)
            self.assertTrue(all(o["side"] == "union" for o in union_orders))
            opponent = [d for d in state["decisions"] if d.get("side") == "confederate"]
            self.assertTrue(opponent)
            self.assertTrue(all(d["source"] == "scripted" for d in opponent))
            self.assertEqual(
                state["run"],
                {
                    "rules": "poc-13",
                    "scenario": "little-round-top-v13",
                    "scenario_id": "little-round-top",
                    "variant": None,
                    "prompt_version": PROMPT_VERSION,
                    "player_side": "union",
                    "player_provider": "openrouter",
                    "model": "fake/player-model",
                    "effort": "high",
                    # FakeProvider reports no reply contract.
                    "response_format": None,
                    "opponent_side": "confederate",
                    "opponent": OPPONENT_POLICY,
                },
            )
            self.assertEqual(result["replay"]["status"], "identical")
            # Replay from storage alone, with the provider now refusing calls.
            calls = len(provider.calls)
            provider.error = AssertionError("replay must not call the provider")
            replay = build_replay(Path(tmp) / "battle.sqlite").verify(result["game_id"])
            self.assertEqual(replay["status"], "identical")
            self.assertEqual(len(provider.calls), calls)

    def test_confederate_player_run_issues_confederate_model_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = run_headless(tmp, FakeProvider(), side="confederate")
            state, mine = player_decisions(runner, result, "confederate")
            self.assertTrue(any(d["source"] == "openrouter" for d in mine))
            model_orders = [o for o in state["orders"] if o["source"] == "openrouter"]
            self.assertTrue(all(o["side"] == "confederate" for o in model_orders))
            union = [d for d in state["decisions"] if d.get("side") == "union"]
            self.assertTrue(union and all(d["source"] == "scripted" for d in union))
            self.assertEqual(result["replay"]["status"], "identical")

    def test_player_prompt_excludes_opponent_mission_and_truth(self):
        state = advanced_state()
        for side, other in (("union", "confederate"), ("confederate", "union")):
            provider = FakeProvider()
            CommanderService(RulesSimulation(), provider).decide(state, side=side)
            instruction, payload = provider.calls[0]
            self.assertIn(MISSIONS[side], instruction)
            self.assertNotIn(MISSIONS[other], instruction)
            if side == "union":
                self.assertNotIn("3 consecutive turns", instruction)
            observation = payload["observation"]
            self.assertEqual(observation["side"], side)
            self.assertEqual({u["side"] for u in observation["units"]}, {side})
            self.assertTrue(all(o["side"] == side for o in observation["orders"]))
            for key in ("events", "decisions", "reports", "cells", "friendly_reports", "run"):
                self.assertNotIn(key, observation)
            self.assertTrue(all(s["side"] == side for s in observation["supply_sites"]))
            # Enemy knowledge arrives only as observed estimates, never exact state.
            self.assertTrue(observation["contacts"])
            for contact in observation["contacts"]:
                self.assertEqual(contact["side"], other)
                self.assertIn("strength_range", contact)
                for hidden in ("strength", "ammo", "morale", "fatigue", "target"):
                    self.assertNotIn(hidden, contact)

    def test_invalid_proposal_falls_back_flagged_with_rejected_orders(self):
        # Ordering an enemy unit is never legal for the Union player.
        bad = [{"unit_id": "C1", "stance": "hold", "destination": None}]
        provider = FakeProvider(propose=lambda payload: copy.deepcopy(bad))
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = run_headless(tmp, provider)
            state, mine = player_decisions(runner, result)
            self.assertEqual(result["player_decisions"]["model"], 0)
            self.assertEqual(result["player_decisions"]["fallback"], len(mine))
            decision = mine[0]
            self.assertEqual(decision["source"], "scripted")
            self.assertTrue(decision["fallback"])
            self.assertEqual(decision["fallback_stage"], "validation_failed")
            self.assertEqual(decision["fallback_reason"], "InvalidOrder")
            self.assertEqual(decision["rejected_proposal"], bad)
            self.assertEqual(decision["proposed_orders"], bad)
            self.assertFalse(decision["validation"]["valid"])
            self.assertIn("outside your command", decision["validation"]["error"])
            self.assertEqual(decision["requested_model"], "fake/player-model")
            self.assertFalse(any(o["source"] == "openrouter" for o in state["orders"]))
            self.assertTrue(all(o["unit_id"].startswith("U") for o in decision["orders"]))
            self.assertEqual(result["replay"]["status"], "identical")

    def test_provider_timeout_falls_back_without_partial_state(self):
        state = advanced_state(turns=12)
        before = copy.deepcopy(state)
        simulation = RulesSimulation()
        failing = CommanderService(
            simulation, FakeProvider(error=TimeoutError("private-provider-detail"))
        )
        failed = failing.decide(state, side="union")
        self.assertEqual(state, before)
        self.assertEqual(failed["source"], "scripted")
        self.assertTrue(failed["fallback"])
        self.assertEqual(failed["fallback_stage"], "provider_error")
        self.assertEqual(failed["fallback_reason"], "TimeoutError")
        self.assertIsNone(failed["validation"])
        self.assertIsNone(failed["proposed_orders"])
        self.assertIsNone(failed["response_id"])
        self.assertNotIn("private-provider-detail", json.dumps(failed))
        scripted = failing.decide(state, side="union", mode="scripted")
        self.assertEqual(failed["orders"], scripted["orders"])
        after_failed = simulation.apply(state, {"type": "decision", "decision": failed})
        after_scripted = simulation.apply(state, {"type": "decision", "decision": scripted})
        for key in ("orders", "events", "units", "dispatches", "revision"):
            self.assertEqual(after_failed[key], after_scripted[key], key)
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(error=TimeoutError("private-provider-detail"))
            runner, result = run_headless(tmp, provider)
            self.assertEqual(result["player_decisions"]["fallback"], len(provider.calls))
            self.assertEqual(result["replay"]["status"], "identical")

    def test_telemetry_is_stored_with_decisions_without_credentials(self):
        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                return self.body

        def opener(request, timeout):
            payload = json.loads(json.loads(request.data)["messages"][1]["content"])
            content = {"text": "General.", "orders": fallback_orders(payload["observation"])}
            return Response(
                json.dumps(
                    {
                        "id": "gen-http",
                        "model": "fake/returned",
                        "usage": {"total_tokens": 7},
                        "choices": [{"message": {"content": json.dumps(content)}}],
                    }
                ).encode()
            )

        secret = "synthetic-credential-value"
        provider = OpenRouterProvider(
            Settings(api_key=secret, model="fake/requested", effort="high"),
            opener=opener,
        )
        with tempfile.TemporaryDirectory() as tmp:
            runner, result = run_headless(tmp, provider)
            db = sqlite3.connect(Path(tmp) / "battle.sqlite")
            rows = [json.loads(r[0]) for r in db.execute("SELECT payload FROM decisions")]
            dump = "\n".join(line for line in db.iterdump())
            db.close()
            mine = [d for d in rows if d.get("side") == "union"]
            self.assertTrue(mine)
            self.assertEqual(mine[0]["response_id"], "gen-http")
            self.assertEqual(mine[0]["model"], "fake/returned")
            self.assertEqual(mine[0]["requested_model"], "fake/requested")
            self.assertEqual(mine[0]["effort"], "high")
            self.assertNotIn(secret, dump)
            self.assertNotIn("You are a commander", dump)


class DecisionSideTests(unittest.TestCase):
    def test_decision_orders_are_issued_for_their_side(self):
        state = scenario.create()
        decision = {
            "source": "openrouter",
            "side": "union",
            "orders": [{"unit_id": "U1", "stance": "hold", "destination": None}],
        }
        updated = runtime.apply(state, {"type": "decision", "decision": decision})
        self.assertEqual(updated["orders"][0]["side"], "union")
        self.assertEqual(updated["turn"], state["turn"])
        self.assertEqual(updated["decisions"][-1]["side"], "union")
        with self.assertRaises(ValueError):
            runtime.apply(
                state, {"type": "decision", "decision": dict(decision, side="neutral")}
            )

    def test_decision_without_side_replays_as_confederate(self):
        # Shape of every decision recorded before decisions named their side.
        state = scenario.create("poc-8")  # Side-less decisions exist only before poc-9.
        legacy = {
            "source": "scripted",
            "orders": [{"unit_id": "C1", "stance": "move", "destination": [6, 19]}],
        }
        updated = runtime.apply(state, {"type": "advance", "decision": legacy})
        self.assertEqual(updated["orders"][0]["side"], "confederate")
        self.assertNotIn("side", updated["decisions"][0])


class CompositionTests(unittest.TestCase):
    def test_default_headless_run_keeps_baseline_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = build_headless(Path(tmp) / "battle.sqlite")
            result = runner.run()
            self.assertEqual(
                set(result), {"game_id", "winner", "turns", "events", "strength", "replay"}
            )
            state = runner.repository.load(result["game_id"])
            history = runner.repository.history(result["game_id"])
            types = {
                runner.repository.load(result["game_id"], h["revision"])["last_action"]["type"]
                for h in history[1:]
            }
            self.assertEqual(types, {"orders", "advance"})
            self.assertTrue(all(d["side"] == "confederate" for d in state["decisions"]))
            self.assertEqual(state["run"]["player_provider"], "scripted")
            self.assertEqual(state["run"]["opponent"], OPPONENT_POLICY)
            self.assertIsNone(state["run"]["model"])

    def test_build_headless_composes_openrouter_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = build_headless(
                Path(tmp) / "battle.sqlite",
                player_provider="openrouter",
                settings=Settings(api_key="synthetic", model="base/model"),
                model="cli/model",
                effort="high",
                max_tokens=900,
                timeout=40.0,
            )
            settings = runner.commander.provider._settings
            self.assertEqual(
                (settings.model, settings.effort, settings.max_tokens, settings.timeout),
                ("cli/model", "high", 900, 40.0),
            )
            self.assertEqual(runner.metadata(scenario.create())["effort"], "high")

    def test_build_headless_refuses_openrouter_without_credential(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build_headless(
                    Path(tmp) / "battle.sqlite",
                    player_provider="openrouter",
                    settings=Settings(api_key=""),
                )
            with self.assertRaises(ValueError):
                build_headless(Path(tmp) / "battle.sqlite", player_side="neutral")

    def test_openrouter_request_carries_configured_effort_and_limits(self):
        calls = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                return json.dumps(
                    {"choices": [{"message": {"content": '{"orders":[]}'}}]}
                ).encode()

        def opener(request, timeout):
            calls.append((json.loads(request.data), timeout))
            return Response()

        tuned = Settings(api_key="k", model="m", effort="high", max_tokens=900, timeout=40.0)
        _, metadata = OpenRouterProvider(tuned, opener=opener).request("i", {})
        OpenRouterProvider(Settings(api_key="k", model="m"), opener=opener).request("i", {})
        (body, timeout), (plain, plain_timeout) = calls
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual((body["max_tokens"], timeout), (900, 40.0))
        self.assertNotIn("reasoning", plain)
        self.assertEqual((plain["max_tokens"], plain_timeout), (650, 18.0))
        self.assertIsNone(metadata["model"])
        with self.assertRaises(ValueError):
            Settings(effort="extreme")

    def test_run_metadata_records_prompt_version_and_response_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = build_headless(
                Path(tmp) / "battle.sqlite",
                player_provider="openrouter",
                settings=Settings(api_key="synthetic", model="m"),
            )
            scripted = build_headless(Path(tmp) / "scripted.sqlite")
        metadata = runner.metadata(scenario.create())
        self.assertEqual(metadata["prompt_version"], "lrt-side-v2")
        self.assertEqual(metadata["response_format"], "json_schema:commander_orders")
        self.assertIsNone(scripted.metadata(scenario.create())["response_format"])


def probe_refused(state, side, unit_id):
    """True when the engine refuses a plain hold order to ``unit_id``."""
    try:
        engine.validate_order(
            state, side, {"unit_id": unit_id, "stance": "hold", "destination": None}
        )
    except engine.InvalidOrder:
        return True
    return False


class OrderAcceptanceObservationTests(unittest.TestCase):
    def observe(self, state, side="union"):
        provider = FakeProvider()
        CommanderService(RulesSimulation(), provider).decide(state, side=side)
        instruction, payload = provider.calls[0]
        return instruction, payload["observation"]

    def test_observation_marks_reported_routed_unit_unable_to_accept_orders(self):
        state = scenario.create()
        # HQ has received a routed report for U1; ground truth is unchanged.
        state["friendly_reports"]["union"]["U1"]["status"] = "routed"
        # U3 broke in ground truth, but HQ has not been told: still orderable.
        engine.find_unit(state, "U3")["status"] = "routed"
        instruction, observation = self.observe(state)
        units = {u["id"]: u for u in observation["units"]}
        self.assertEqual(
            (units["U1"]["accepts_orders"], units["U1"]["order_refusal"]),
            (False, "reported_routed"),
        )
        self.assertEqual(
            (units["U3"]["accepts_orders"], units["U3"]["order_refusal"]), (True, None)
        )
        self.assertEqual(observation["order_contract"]["orderable_units"], ["U2", "U3"])
        for unit_id, unit in units.items():
            self.assertEqual(unit["accepts_orders"], not probe_refused(state, "union", unit_id))
        self.assertIn("orderable_units", instruction)
        # Earlier editions keep their observation unchanged.
        legacy = command_policy.observation_for(scenario.create(rules="poc-7"), "union")
        self.assertNotIn("orderable_units", legacy["order_contract"])
        self.assertNotIn("accepts_orders", legacy["units"][0])

    def test_observation_marks_every_unit_refused_when_command_disrupted(self):
        state = scenario.create()
        engine.find_unit(state, "U2")["status"] = "routed"  # HQ's own detachment.
        _, observation = self.observe(state)
        self.assertFalse(observation["command"]["operational"])
        self.assertEqual(observation["order_contract"]["orderable_units"], [])
        for unit in observation["units"]:
            self.assertEqual(
                (unit["accepts_orders"], unit["order_refusal"]), (False, "command_disrupted")
            )
            self.assertTrue(probe_refused(state, "union", unit["id"]))


if __name__ == "__main__":
    unittest.main()
