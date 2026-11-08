"""The model-run batch driver (scripts/model_runs.py, doc 69 §9-§10), the
runner's abort on fallback and its spend guard, with fake providers only:
no network, no credential, no spend."""

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import build_headless
from battle.command_policy import scripted_actions, scripted_policy
from battle.adapters.openrouter import RESPONSE_FORMAT, OpenRouterProvider
from battle.command_policy import system_prompt
from battle.config import Settings
from battle.contracts import ProviderFailure
from battle.paid_batch import fake_key_opener
from battle.scenario_concord import CONCORD_NORTH_BRIDGE
from battle.scenario_hougoumont import HOUGOUMONT_NORTH_GATE
from battle.scenario_pegasus import PEGASUS_BRIDGE
from battle.services.headless import ModelFallback
from battle.spend import PROVIDER_OVERHEAD_TOKENS, CostUnreadable, Price, decision_cost, worst_case_call

POC = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("model_runs", POC / "scripts" / "model_runs.py")
model_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model_runs)

# A near-zero reserve (D37: a rate must be above 0): only the spend made counts against the cap.
FREE = Price(1e-9, 1e-9, 1)
SOURCE = {"commit": "0" * 40, "clean": True}
# D37: main() needs a key in its environment; this placeholder is never sent anywhere real.
DUMMY_KEY = "dummy-not-a-key"


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
        if isinstance(fault, BaseException):
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


def batch(tmp, plan, games, cap, price=FREE, **fake):
    """Runs the driver quietly; returns (exit code, summary, per-game lines, fakes)."""
    fakes = []

    def provider_for(entry):
        fakes.append(ScriptedFake(entry, **fake))
        return fakes[-1]

    out = io.StringIO()
    with redirect_stdout(out):
        code, summary = model_runs.run_batch(plan, games, cap, Path(tmp) / "b", price=price, source=SOURCE,
                                             provider_for=provider_for)
    lines = [json.loads(line) for line in out.getvalue().splitlines()]
    return code, summary, [r for r in lines if "summary" not in r], fakes


@contextmanager
def dummy_env(**variables):
    """A dummy environment with no credential, and no .env.local file read."""
    environ = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), **variables}
    load = Settings.load.__func__
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, environ, clear=True), \
            mock.patch.object(Settings, "load", classmethod(
                lambda cls, path=None, environ=None: load(cls, Path(tmp) / "absent.env", os.environ))):
        yield


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


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

    def test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap(self):
        # Hill 223 default makes 9 calls. The reserve is 4,000 output tokens at
        # $7.50 per million = $0.03, each call costs $0.03 and the cap is $0.10:
        # calls 1-3 fit; before call 4, 0.10 - 0.09 - 0.03 < 0, so it is never made.
        price = Price(1e-6, 7.5, 4000)  # Input priced at almost nothing.
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, fakes = batch(tmp, ["hill-223-patrol"], 2, 0.10, price=price, cost=0.03)
            stopped = games[0]
            self.assertTrue(Path(stopped["db"]).exists())
        self.assertEqual(code, model_runs.EXIT_CAP)
        self.assertEqual(fakes[0].calls, 3)
        self.assertEqual((stopped["status"], stopped["decision_index"], stopped["turn"]), ("stopped", 3, 9))
        self.assertTrue(stopped["db"].endswith(".stopped.sqlite"))
        self.assertIn("budget:", stopped["reason"])
        self.assertAlmostEqual(summary["spent_usd"], 0.09)
        self.assertLessEqual(summary["spent_usd"], 0.10)
        self.assertEqual((summary["played"], summary["not_started"]), (1, 1))

    def test_reserve_covers_the_full_request_body_the_adapter_sends(self):
        # Capture the exact bytes the adapter would POST; the opener never touches the network.
        settings = Settings(api_key="dummy-not-a-key", model="anthropic/claude-sonnet-5.5", effort="high",
                            max_tokens=16000)
        sent = []

        def opener(request, timeout):
            sent.append(request.data)
            raise OSError("no network in tests")

        instruction = system_prompt("british", PEGASUS_BRIDGE)
        payload = {"task": "Choose your next tactical orders.", "observation": {"units": ["x" * 5000]}}
        with self.assertRaises(ProviderFailure):
            OpenRouterProvider(settings, opener=opener).request(instruction, payload)
        body = sent[0]
        self.assertIn(b'"response_format"', body)
        size = model_runs.request_size(settings)(instruction, payload)
        self.assertEqual(size, len(body))
        self.assertGreater(size, len(instruction.encode()) + len(json.dumps(payload).encode())
                           + len(json.dumps(RESPONSE_FORMAT)))
        per_token = Price(1_000_000.0, 1e-9, 16000)  # $1 a token: the reserve in dollars is the token bound.
        self.assertAlmostEqual(worst_case_call(per_token, size), len(body) + PROVIDER_OVERHEAD_TOKENS, places=6)

    def test_reserve_and_pins_use_the_environment_settings(self):
        # Sonnet at 16,000 output tokens reserves over $0.16 for the first call, so a $0.15
        # cap refuses it; at 650 tokens (Settings without the environment) it would play.
        with dummy_env(OPENROUTER_EFFORT="high", OPENROUTER_MAX_TOKENS="16000", OPENROUTER_API_KEY=DUMMY_KEY), \
                tempfile.TemporaryDirectory() as tmp:
            git(tmp, "init", "-q")
            git(tmp, "commit", "-q", "--allow-empty", "-m", "base")
            fakes = []
            with redirect_stdout(io.StringIO()):
                code = model_runs.main(
                    ["--plan", "pegasus-bridge", "--model", "anthropic/claude-sonnet-5.5", "--games", "1",
                     "--cap-usd", "0.15", "--dir", str(Path(tmp) / "b")],
                    provider_for=lambda entry: fakes.append(ScriptedFake(entry)) or fakes[-1], repo=tmp,
                    key_opener=fake_key_opener(0.15))
            manifest = json.loads((Path(tmp) / "b" / "manifest.json").read_text())
            game = json.loads((Path(tmp) / "b" / "runs.jsonl").read_text().splitlines()[0])
        self.assertEqual(manifest["prices"]["max_output_tokens"], 16000)
        self.assertEqual((manifest["effort"], manifest["request_max_tokens"], manifest["request_timeout"]),
                         ("high", 16000, 90.0))
        self.assertEqual((game["pins"]["effort"], game["pins"]["request_max_tokens"]), ("high", 16000))
        self.assertEqual((code, fakes[0].calls, game["status"]), (model_runs.EXIT_CAP, 0, "stopped"))

    def test_interrupt_mid_game_records_the_game_and_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "b"
            with redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                model_runs.run_batch(["pegasus-bridge"], 2, 100.0, out, price=FREE, source=SOURCE,
                                     provider_for=lambda e: ScriptedFake(e, fail={2: KeyboardInterrupt()}))
            names = sorted(p.name for p in out.iterdir())
            record = json.loads((out / "runs.jsonl").read_text().splitlines()[0])
            self.assertEqual(record["db_sha256"], hashlib.sha256(Path(record["db"]).read_bytes()).hexdigest())
            summary = json.loads((out / "batch-summary.json").read_text())
        self.assertNotIn("pegasus-bridge-1.sqlite", names)
        self.assertIn("pegasus-bridge-1.failed.sqlite", names)
        self.assertEqual((record["status"], record["reason"], record["decision_index"]),
                         ("failed", "interrupted: KeyboardInterrupt", 1))
        self.assertEqual((summary["status"], summary["played"]), ("interrupted", 1))
        self.assertIs(record["cost_complete"], False)
        self.assertIs(summary["spend_complete"], False)

    def test_cli_exits_non_zero_at_the_cap(self):
        with dummy_env(OPENROUTER_API_KEY=DUMMY_KEY), tempfile.TemporaryDirectory() as tmp:
            git(tmp, "init", "-q")
            git(tmp, "commit", "-q", "--allow-empty", "-m", "base")
            with redirect_stdout(io.StringIO()):
                code = model_runs.main(
                    ["--plan", "pegasus-bridge", "--model", "fake/model-runs", "--games", "3",
                     "--cap-usd", "0.05", "--input-price", "0.000001", "--output-price", "0.000001",
                     "--dir", str(Path(tmp) / "b")],
                    provider_for=lambda entry: ScriptedFake(entry, cost=0.03), repo=tmp,
                    key_opener=fake_key_opener(0.05))
        self.assertEqual(code, model_runs.EXIT_CAP)

    def test_dirty_tree_is_refused_and_pins_appear(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            git(repo, "init", "-q")
            (repo / "a.txt").write_text("a\n")
            git(repo, "add", "a.txt")
            git(repo, "commit", "-q", "-m", "base")
            pin = model_runs.source_pin(repo)
            self.assertEqual(pin["clean"], True)
            self.assertEqual(len(pin["commit"]), 40)
            (repo / "a.txt").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "dirty"):
                model_runs.source_pin(repo)
            with dummy_env(), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as refused:
                model_runs.main(["--plan", "pegasus-bridge", "--model", "anthropic/claude-sonnet-5.5",
                                 "--games", "1", "--cap-usd", "1", "--dir", str(Path(tmp) / "b")],
                                provider_for=lambda entry: ScriptedFake(entry), repo=repo)
            self.assertEqual(refused.exception.code, 2)
            self.assertFalse((Path(tmp) / "b").exists())  # Refused before anything is written.

            out = Path(tmp) / "c"
            with redirect_stdout(io.StringIO()):
                model_runs.run_batch(["pegasus-bridge"], 1, 1.0, out, price=Price(2.0, 10.0, 4000), source=pin,
                                     settings=Settings(model="anthropic/claude-sonnet-5.5", effort="high",
                                                       max_tokens=4000), provider_for=ScriptedFake)
            manifest = json.loads((out / "manifest.json").read_text())
            game = json.loads((out / "runs.jsonl").read_text().splitlines()[0])
        self.assertEqual(manifest["source"], pin)
        self.assertEqual((manifest["model"], manifest["cap_usd"], manifest["plan"]),
                         ("anthropic/claude-sonnet-5.5", 1.0, ["pegasus-bridge"]))
        self.assertEqual(manifest["prices"]["input_per_mtok"], 2.0)
        self.assertIn("reserve_basis", manifest["prices"])
        pins = manifest["entries"]["pegasus-bridge"]
        self.assertEqual((pins["rules"], pins["player_side"]), ("poc-13", "british"))
        british = pins["sides"]["british"]
        self.assertEqual((british["control"], british["control_version"]), ("scripted-pegasus-coup-de-main-v1", "v1"))
        self.assertEqual(british["prompt_version"], PEGASUS_BRIDGE.prompt_version)
        self.assertEqual(british["prompt_sha256"],
                         hashlib.sha256(system_prompt("british", PEGASUS_BRIDGE).encode()).hexdigest())
        self.assertEqual(set(pins["sides"]), {"british", "german"})
        self.assertEqual((manifest["effort"], manifest["request_max_tokens"]), ("high", 4000))
        keys = ("source", "model", "effort", "request_max_tokens", "request_timeout", "cap_usd", "prices")
        self.assertEqual(game["pins"], {**{k: manifest[k] for k in keys}, **pins})

    def test_hougoumont_is_labelled_asymmetric_and_pegasus_symmetric(self):
        self.assertEqual(model_runs.action_set(HOUGOUMONT_NORTH_GATE, HOUGOUMONT_NORTH_GATE.player),
                         {"control": "scripted-gate-defender-v1", "symmetric": False,
                          "control_only": ["standing instruction close_on_breach"]})
        self.assertEqual(model_runs.action_set(HOUGOUMONT_NORTH_GATE, "french")["control_only"],
                         ["standing instruction firm"])
        for item in ("little-round-top", "concord-north-bridge", "pegasus-bridge", "hill-223-patrol",
                     "gergovia-recall"):
            entry = model_runs.resolve(item)
            self.assertTrue(model_runs.action_set(entry, entry.player)["symmetric"], item)

    def test_missing_cost_fails_closed_and_stops_the_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, fakes = batch(tmp, ["pegasus-bridge"], 3, 100.0, cost=None)
            failed_db = Path(games[0]["db"])
            self.assertTrue(failed_db.name.endswith(".failed.sqlite"), failed_db)
            self.assertTrue(failed_db.exists())
        self.assertEqual(code, model_runs.EXIT_FAILED)
        self.assertEqual((summary["played"], summary["model_games"], summary["spend_complete"]),
                         (1, 0, False), summary)
        self.assertEqual(fakes[0].calls, 1)  # Stopped at the first call with no cost.
        self.assertFalse(games[0]["cost_complete"])
        self.assertIn("cost unreadable", games[0]["reason"])
        for bad in ({}, {"cost": None}, {"cost": "0.01"}, {"cost": True}, {"cost": -1.0},
                    {"cost": float("nan")}):
            with self.assertRaises(CostUnreadable, msg=bad):
                decision_cost({"usage": bad})

    def test_provider_error_or_junk_reply_fails_the_game_and_stops_the_batch(self):
        cases = {
            "provider_error HTTP 429": (ProviderFailure("HTTP 429", {"usage": {"cost": 0.02}}), 0.03, True),
            "invalid_response TypeError": ("not an order object", 0.02, True),
            "provider_error TimeoutError": (TimeoutError(), 0.01, False),
        }
        for reason, (fault, spent, complete) in cases.items():
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
                self.assertAlmostEqual(summary["spent_usd"], spent)
                self.assertEqual(summary["spend_complete"], complete)

    def test_fallback_keeps_the_partial_run_and_its_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary, games, _ = batch(tmp, ["pegasus-bridge"], 2, 100.0, cost=0.01, fail={2: "junk"})
            record = json.loads((Path(tmp) / "b" / "runs.jsonl").read_text().splitlines()[0])
            db = Path(record["db"])
            self.assertTrue(db.exists())
            self.assertEqual(record["db_sha256"], hashlib.sha256(db.read_bytes()).hexdigest())
            listed = json.loads((Path(tmp) / "b" / "batch-summary.json").read_text())["stopped_or_failed"]
        self.assertEqual(code, model_runs.EXIT_FAILED)
        self.assertEqual(
            {k: record[k] for k in ("entry", "variant", "model", "turn", "decision_index", "reason", "cost_usd")},
            {"entry": "pegasus-bridge", "variant": None, "model": "fake/model-runs", "turn": 3,
             "decision_index": 1, "reason": "fallback: invalid_response TypeError", "cost_usd": 0.02})
        self.assertEqual(listed, [{k: v for k, v in record.items() if k != "pins"}])
        self.assertEqual(summary["stopped_or_failed"], listed)

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

    def test_unknown_plan_names_and_used_directories_are_refused(self):
        for item in ("cannae-envelopment", "pegasus-bridge/no-such-variant", "little-round-top/x"):
            with self.subTest(item), tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                model_runs.run_batch([item], 1, 1.0, Path(tmp) / "b", price=FREE, source=SOURCE,
                                     provider_for=lambda e: None)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "runs.jsonl").write_text("earlier\n")
            with self.assertRaisesRegex(ValueError, "already holds a batch"):
                model_runs.run_batch(["pegasus-bridge"], 1, 1.0, tmp, price=FREE, source=SOURCE,
                                     provider_for=ScriptedFake)
            self.assertEqual((Path(tmp) / "runs.jsonl").read_text(), "earlier\n")
        with self.assertRaisesRegex(ValueError, "No price"):
            model_runs.price_for(Settings(model="fake/unpriced"))


if __name__ == "__main__":
    unittest.main()
