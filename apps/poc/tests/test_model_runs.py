"""The model-run batch driver (scripts/model_runs.py, doc 69 §9) and the
runner's abort on fallback, with fake providers only: no network, no spend."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import build_headless
from battle.command_policy import scripted_actions, scripted_policy
from battle.contracts import ProviderFailure
from battle.scenario_concord import CONCORD_NORTH_BRIDGE
from battle.scenario_pegasus import PEGASUS_BRIDGE
from battle.services.headless import ModelFallback

POC = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("model_runs", POC / "scripts" / "model_runs.py")
model_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model_runs)


class ScriptedFake:
    """Answers with the entry's own scripted orders and reports ``cost`` per
    call (None: no cost key). ``fail`` maps a call number to an exception to
    raise or a non-dict reply to return."""

    available = True
    model = "fake/model-runs"
    effort = "high"

    def __init__(self, entry, cost=0.01, fail=None):
        self.entry, self.cost, self.fail = entry, cost, fail or {}
        self.calls = 0

    def request(self, instruction, payload):
        self.calls += 1
        fault = self.fail.get(self.calls)
        if isinstance(fault, Exception):
            raise fault
        usage = {"prompt_tokens": 100, "completion_tokens": 20}
        if self.cost is not None:
            usage["cost"] = self.cost
        metadata = {"model": self.model, "usage": usage, "response_id": f"gen-{self.calls}"}
        if fault is not None:
            return fault, metadata
        observation = payload["observation"]
        side = observation["side"]
        _, orders = scripted_actions(scripted_policy(self.entry, side), observation,
                                     self.entry.sides[side].role)
        return {"text": "Orders follow.", "orders": orders}, metadata


def batch(tmp, plan, games, cap, **fake):
    """Runs the driver quietly; returns (exit code, summary, per-game lines, fakes)."""
    fakes = []

    def provider_for(entry):
        fakes.append(ScriptedFake(entry, **fake))
        return fakes[-1]

    out = io.StringIO()
    with redirect_stdout(out):
        code, summary = model_runs.run_batch(plan, games, cap, Path(tmp) / "b", provider_for=provider_for)
    lines = [json.loads(line) for line in out.getvalue().splitlines()]
    return code, summary, [r for r in lines if "summary" not in r], fakes


class ModelRunsTest(unittest.TestCase):
    def test_model_runs_on_four_entries_replay_with_no_fallbacks(self):
        plan = ["concord-north-bridge", "pegasus-bridge", "hill-223-patrol", "gergovia-recall",
                "concord-north-bridge/two-companies"]
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, fakes = batch(tmp, plan, 1, 100.0, cost=0.01)
        self.assertEqual((code, summary["status"], summary["model_games"]), (0, "complete", 5), summary)
        for game, fake in zip(games, fakes):
            self.assertEqual(game["status"], "model_game", game)
            self.assertEqual(game["replay"], "identical", game)
            counts = game["player_decisions"]
            self.assertEqual(counts["fallback"], 0, game)
            self.assertEqual(counts["model"], counts["total"], game)
            self.assertEqual(counts["total"], fake.calls, game)
            self.assertAlmostEqual(game["cost_usd"], 0.01 * fake.calls)
        self.assertEqual([g["variant"] for g in games], [None] * 4 + ["two-companies"])
        self.assertEqual(games[4]["entry"], "concord-north-bridge-two-companies")

    def test_batch_stops_at_the_cost_cap(self):
        # Pegasus default: 2 model calls per game, so $0.06 a game; the cap is hit after game 2.
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, _ = batch(tmp, ["pegasus-bridge"], 5, 0.10, cost=0.03)
        self.assertEqual(code, model_runs.EXIT_CAP)
        self.assertEqual((summary["status"], summary["played"], summary["not_started"]),
                         ("cap_reached", 2, 3), summary)
        self.assertAlmostEqual(summary["spent_usd"], 0.12)
        self.assertEqual(len(games), 2)

    def test_cli_exits_non_zero_at_the_cap(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            code = model_runs.main(
                ["--plan", "pegasus-bridge", "--model", "fake/model-runs", "--games", "3",
                 "--cap-usd", "0.05", "--dir", str(Path(tmp) / "b")],
                provider_for=lambda entry: ScriptedFake(entry, cost=0.03))
        self.assertEqual(code, model_runs.EXIT_CAP)

    def test_missing_cost_fails_closed_and_stops_the_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, _ = batch(tmp, ["pegasus-bridge"], 3, 100.0, cost=None)
            failed_db = Path(games[0]["db"])
            self.assertTrue(failed_db.name.endswith(".failed.sqlite"), failed_db)
            self.assertTrue(failed_db.exists())
        self.assertEqual(code, model_runs.EXIT_FAILED)
        self.assertEqual((summary["played"], summary["model_games"], summary["spend_complete"]),
                         (1, 0, False), summary)
        self.assertIsNone(games[0]["cost_usd"])
        self.assertIn("cost unreadable", games[0]["reason"])
        for bad in ({}, {"cost": None}, {"cost": "0.01"}, {"cost": True}, {"cost": -1.0},
                    {"cost": float("nan")}):
            with self.assertRaises(model_runs.GameFailed, msg=bad):
                model_runs.decision_cost({"usage": bad})

    def test_provider_error_or_junk_reply_fails_the_game_and_stops_the_batch(self):
        cases = {
            "provider_error HTTP 429": ProviderFailure("HTTP 429", {"usage": {"cost": 0.02}}),
            "invalid_response TypeError": "not an order object",
            "provider_error TimeoutError": TimeoutError(),
        }
        for reason, fault in cases.items():
            with self.subTest(reason), tempfile.TemporaryDirectory() as tmp:
                code, summary, games, fakes = batch(tmp, ["pegasus-bridge"], 3, 100.0, cost=0.01,
                                                    fail={2: fault})
                self.assertEqual(code, model_runs.EXIT_FAILED)
                self.assertEqual((summary["played"], summary["model_games"]), (1, 0), summary)
                self.assertEqual(games[0]["status"], "failed")
                self.assertEqual(games[0]["reason"], f"fallback: {reason}")
                self.assertEqual(fakes[0].calls, 2)  # Aborted at the fallback; no later call.
                self.assertTrue(games[0]["db"].endswith(".failed.sqlite"))
        # A paid failure is counted; an unpaid one with no cost leaves spend incomplete.
        self.assertAlmostEqual(self._spent(ProviderFailure("HTTP 429", {"usage": {"cost": 0.02}})), 0.03)

    def _spent(self, fault):
        with tempfile.TemporaryDirectory() as tmp:
            _, summary, _, _ = batch(tmp, ["pegasus-bridge"], 1, 100.0, cost=0.01, fail={2: fault})
        return summary["spent_usd"]

    def test_finished_game_with_a_fallback_is_not_a_model_game(self):
        good = {"replay": {"status": "identical"}, "player_decisions": {"total": 3, "model": 3, "fallback": 0}}
        self.assertIsNone(model_runs.model_game_failure(good))
        for counts, reason in (({"total": 3, "model": 2, "fallback": 1}, "1 fallback decision(s)"),
                               ({"total": 3, "model": 2, "fallback": 0}, "1 non-model decision(s)")):
            self.assertEqual(model_runs.model_game_failure({**good, "player_decisions": counts}), reason)
        self.assertEqual(model_runs.model_game_failure({**good, "replay": {"status": "diverged"}}),
                         "replay diverged")

    def test_abort_on_fallback_raises_before_the_fallback_is_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = build_headless(
                Path(tmp) / "g.sqlite", player_provider="openrouter",
                provider=ScriptedFake(PEGASUS_BRIDGE, fail={2: "junk"}),
                scenario_id=PEGASUS_BRIDGE.id, scenarios=ScenarioRegistry([PEGASUS_BRIDGE]),
                abort_on_fallback=True)
            with self.assertRaises(ModelFallback) as caught:
                runner.run()
            state = runner.repository.load(runner.repository.latest())
            with self.assertRaises(ValueError):  # Scripted runs keep their path; the option needs a model.
                build_headless(Path(tmp) / "s.sqlite", scenario_id=CONCORD_NORTH_BRIDGE.id,
                               abort_on_fallback=True)
        self.assertEqual(caught.exception.decision["fallback_stage"], "invalid_response")
        self.assertEqual(state["status"], "active")
        mine = [d for d in state["decisions"] if d.get("side") == "british"]
        self.assertEqual([d["fallback"] for d in mine], [False])

    def test_unknown_plan_names_are_refused_before_any_game(self):
        for item in ("cannae-envelopment", "pegasus-bridge/no-such-variant", "little-round-top/x"):
            with self.subTest(item), tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                model_runs.run_batch([item], 1, 1.0, Path(tmp) / "b", provider_for=lambda e: None)


if __name__ == "__main__":
    unittest.main()
