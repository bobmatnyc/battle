"""Service tests use constructor injection; no HTTP, credential file or model calls."""

import ast
import copy
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from battle import analysis, scenario
from battle.adapters.openrouter import OpenRouterProvider, ProviderUnavailable
from battle.adapters.rules import RulesSimulation, LittleRoundTopCatalog
from battle.config import Settings
from battle.contracts import AuditUnavailable, Conflict
from battle.presentation import present_view
from battle.services.battle import BattleService
from battle.services.commander import CommanderService
from battle.services.queries import BattleQueries
from battle.services.replay import ReplayService
from battle.services.headless import HeadlessRunner
from battle.storage import Store


class MemoryRepository:
    """Small port double with copy isolation and atomic revision semantics."""

    def __init__(self):
        self.games = {}
        self.snapshots = {}
        self.audit = []
        self.fail_save = False

    def latest(self):
        return next(reversed(self.games), None)

    def create(self, state):
        gid = f"game-{len(self.games) + 1}"
        self.games[gid] = copy.deepcopy(state)
        self.snapshots[gid] = {0: copy.deepcopy(state)}
        return gid

    def load(self, gid, revision=None):
        return copy.deepcopy(
            self.games[gid] if revision is None else self.snapshots[gid][revision]
        )

    def save(self, gid, state, expected):
        if state["revision"] != expected + 1:
            raise ValueError("Revision must advance exactly once.")
        if self.games[gid]["revision"] != expected:
            raise Conflict("Stale revision")
        if self.fail_save:
            raise OSError("Injected storage failure")
        self.games[gid] = copy.deepcopy(state)
        self.snapshots[gid][state["revision"]] = copy.deepcopy(state)

    def messages(self, gid):
        return []

    def history(self, gid):
        return [
            {"revision": r, "turn": s["turn"]} for r, s in self.snapshots[gid].items()
        ]

    def clock_event(self, gid, command, speed=None):
        self.audit.append((gid, command, speed))


class ManualClock:
    def __init__(self, step, *, audit):
        self.step, self.audit = step, audit
        self.running = self.inflight = False
        self.speed = 10
        self.started = self.closed = False

    def status(self):
        return {"running": self.running, "inflight": self.inflight, "speed": self.speed}

    def control(self, command, speed=None):
        self.audit(command, speed)
        if command == "start":
            self.running = True
        elif command in ("pause", "reset"):
            self.running = False
        elif command == "speed":
            self.speed = speed
        return self.status()

    def pump(self):
        if self.running:
            self.inflight = True
            try:
                return self.step()
            finally:
                self.inflight = False

    def start_worker(self):
        self.started = True

    def close(self):
        self.closed = True


class FakeProvider:
    available = True
    model = "test-model"

    def __init__(self, result=None, error=None):
        self.result = result or {"text": "General, hold the line.", "orders": []}
        self.error = error
        self.calls = []

    def request(self, instruction, payload):
        self.calls.append(copy.deepcopy(payload))
        if self.error:
            raise self.error
        return copy.deepcopy(self.result), {"model": self.model}


def compose(repository=None, provider=None, clock=ManualClock):
    repository = repository if repository is not None else MemoryRepository()
    provider = provider if provider is not None else FakeProvider()
    simulation = RulesSimulation()
    commander = CommanderService(simulation, provider)
    replay = ReplayService(repository, simulation)
    queries = BattleQueries(
        repository, simulation, replay, assess=analysis.assess, present=present_view
    )
    return BattleService(
        repository,
        simulation,
        commander,
        LittleRoundTopCatalog(),
        queries,
        clock,
        mode="openrouter",
    )


def execute(app, command, **payload):
    return app.execute(
        command,
        payload,
        game_id=app.game_id,
        revision=app.repository.load(app.game_id)["revision"],
    )


class ServiceTests(unittest.TestCase):
    def test_legacy_traits_do_not_refresh_remote_condition_or_reveal_enemy(self):
        app = compose()
        state = scenario.create("poc-3")
        report = state["friendly_reports"]["union"]["U1"]
        report.pop("unit_type")
        report.pop("skill")
        state["units"][0].update(fatigue=80, morale=20, strength=15)
        before = copy.deepcopy(state)
        view = app.queries.project(state)
        observed = next(unit for unit in view["units"] if unit["id"] == "U1")
        self.assertEqual((observed["unit_type"], observed["skill"]), ("infantry", 70))
        self.assertEqual((observed["fatigue"], observed["morale"], observed["strength"]), (0, 85, 40))
        self.assertEqual(view["contacts"], [])
        self.assertTrue(all(unit["side"] == "union" for unit in view["units"]))
        self.assertEqual(state, before)

    def test_can_run_commands_clock_and_replay_with_injected_dependencies(self):
        app = compose()
        execute(app, "standing", instruction={"unit_id": "U2", "profile_id": "firm"})
        app.clock_control(app.game_id, "start")
        app.clock.pump()
        app.clock_control(app.game_id, "pause")
        self.assertEqual(app.state()["turn"], 1)
        self.assertEqual(
            next(u for u in app.state()["units"] if u["id"] == "U2")[
                "standing_profile"
            ],
            "firm",
        )
        self.assertEqual(
            app.queries.replay_service.verify(app.game_id)["status"], "identical"
        )
        self.assertEqual(len(app.commander.provider.calls), 1)
        app.start()
        app.close()
        self.assertTrue(app.clock.started and app.clock.closed)

    def test_provider_receives_only_authorized_projection(self):
        app = compose()
        execute(app, "advance")
        observation = app.commander.provider.calls[0]["observation"]
        self.assertEqual({u["side"] for u in observation["units"]}, {"confederate"})
        for key in ("events", "decisions", "reports", "cells", "api_key"):
            self.assertNotIn(key, observation)
        self.assertEqual(observation["contacts"], [])

    def test_illegal_model_orders_fall_back_without_hidden_effects(self):
        provider = FakeProvider(
            {"orders": [{"unit_id": "U1", "stance": "hold", "destination": None}]}
        )
        app = compose(provider=provider)
        execute(app, "advance")
        decision = app.repository.load(app.game_id)["decisions"][0]
        self.assertEqual(decision["source"], "scripted")
        self.assertTrue(all(o["unit_id"].startswith("C") for o in decision["orders"]))

    def test_provider_failure_records_type_without_exception_secrets(self):
        app = compose(
            provider=FakeProvider(error=TimeoutError("private-provider-detail"))
        )
        execute(app, "advance")
        state = app.repository.load(app.game_id)
        self.assertEqual(state["decisions"][0]["fallback_reason"], "TimeoutError")
        self.assertNotIn("private-provider-detail", json.dumps(state))

    def test_invalid_revision_is_rejected_before_inference(self):
        app = compose()
        with self.assertRaises(Conflict):
            app.execute("advance", {}, game_id=app.game_id, revision=99)
        self.assertEqual(app.commander.provider.calls, [])
        self.assertEqual(app.state()["revision"], 0)

    def test_failed_commit_keeps_state_and_audit_unchanged(self):
        app = compose()
        before = app.repository.load(app.game_id)
        app.repository.fail_save = True
        with self.assertRaises(OSError):
            execute(app, "advance")
        self.assertEqual(app.repository.load(app.game_id), before)
        self.assertEqual(len(app.repository.history(app.game_id)), 1)

    def test_sqlite_failure_rolls_back_service_command_and_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Store(Path(tmp) / "battle.sqlite")
            app = compose(repository=repo)
            before = repo.load(app.game_id)
            with repo.connect() as db:
                db.execute(
                    "CREATE TRIGGER fail_save BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'injected'); END"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                execute(app, "advance")
            self.assertEqual(repo.load(app.game_id), before)
            self.assertEqual(len(repo.history(app.game_id)), 1)

    def test_queries_and_replay_do_not_consult_provider(self):
        app = compose()
        execute(app, "advance")
        before = len(app.commander.provider.calls)
        app.commander.provider.error = AssertionError("Provider must not be called")
        app.state()
        app.state(god=True)
        app.queries.replay(app.game_id, 0)
        app.queries.replay_service.verify(app.game_id)
        self.assertEqual(len(app.commander.provider.calls), before)
        self.assertEqual(app.state()["analysis"], app.state(god=True)["analysis"])
        with self.assertRaises(AuditUnavailable):
            app.queries.export(app.game_id)

    def test_pause_does_not_wait_for_blocked_provider(self):
        entered, release = threading.Event(), threading.Event()

        class BlockingProvider(FakeProvider):
            def request(self, instruction, payload):
                entered.set()
                if not release.wait(3):
                    raise TimeoutError()
                return super().request(instruction, payload)

        app = compose(provider=BlockingProvider())
        app.clock_control(app.game_id, "start")
        worker = threading.Thread(target=app.clock.pump)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            paused = app.clock_control(app.game_id, "pause")
            self.assertFalse(paused["clock"]["running"])
            self.assertTrue(paused["clock"]["inflight"])
            with self.assertRaises(Conflict):
                execute(
                    app, "standing", instruction={"unit_id": "U2", "profile_id": "firm"}
                )
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(app.state()["turn"], 1)
        self.assertFalse(app.clock.running)

    def test_reset_preserves_history_and_invalidates_old_identity(self):
        app = compose()
        old = app.game_id
        execute(app, "advance")
        execute(app, "new")
        self.assertNotEqual(app.game_id, old)
        self.assertEqual(app.repository.load(old)["turn"], 1)
        self.assertEqual(app.state()["turn"], 0)
        with self.assertRaises(Conflict):
            app.execute("orders", {}, game_id=old, revision=1)

    def test_staff_proposals_are_recorded_without_execution(self):
        proposal = {"unit_id": "U1", "stance": "hold", "destination": None}
        app = compose(
            provider=FakeProvider({"text": "General, hold.", "orders": [proposal]})
        )
        execute(app, "chat", text="Propose an order")
        state = app.repository.load(app.game_id)
        self.assertEqual(state["orders"], [])
        self.assertEqual(state["decisions"][0]["orders"], [proposal])
        self.assertEqual(state["last_action"]["type"], "chat")


class RepositoryContract:
    def test_copy_isolation_and_immutable_history(self):
        state = scenario.create()
        gid = self.repo.create(state)
        loaded = self.repo.load(gid)
        loaded["turn"] = 999
        self.assertEqual(self.repo.load(gid)["turn"], 0)
        simulation = RulesSimulation()
        updated = simulation.apply(state, {"type": "advance", "decision": None})
        self.repo.save(gid, updated, 0)
        self.assertEqual(self.repo.load(gid, 0), state)
        self.assertEqual(self.repo.load(gid), updated)

    def test_compare_and_swap_conflict_is_atomic(self):
        state = scenario.create()
        gid = self.repo.create(state)
        updated = RulesSimulation().apply(state, {"type": "advance", "decision": None})
        self.repo.save(gid, updated, 0)
        with self.assertRaises(Conflict):
            self.repo.save(gid, updated, 0)
        self.assertEqual(self.repo.load(gid), updated)
        self.assertEqual(len(self.repo.history(gid)), 2)


class MemoryRepositoryTests(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()


class SQLiteRepositoryTests(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Store(Path(self.tmp.name) / "contract.sqlite")


class AdapterTests(unittest.TestCase):
    def test_configuration_precedence_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.local"
            path.write_text(
                "OPENROUTER_API_KEY=file-test-secret\nOPENROUTER_MODEL=file-model\n"
            )
            settings = Settings.load(path, {"OPENROUTER_MODEL": "env-model"})
            self.assertEqual(settings.model, "env-model")
            self.assertEqual(settings.api_key, "file-test-secret")
            self.assertNotIn("file-test-secret", repr(settings))

    def test_openrouter_adapter_can_use_injected_transport(self):
        calls = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                return json.dumps(
                    {
                        "choices": [{"message": {"content": '{"orders":[]}'}}],
                        "model": "test-model",
                    }
                ).encode()

        def opener(request, timeout):
            calls.append((request, timeout))
            return Response()

        provider = OpenRouterProvider(
            Settings(api_key="synthetic-test-key", model="test-model"), opener=opener
        )
        result, metadata = provider.request(
            "test instruction", {"observation": {"units": []}}
        )
        self.assertEqual(result, {"orders": []})
        self.assertEqual(metadata["model"], "test-model")
        self.assertEqual(calls[0][1], 18)
        self.assertEqual(json.loads(calls[0][0].data)["model"], "test-model")

    def test_network_adapter_discards_exception_body(self):
        def fail(*args, **kwargs):
            raise OSError("do-not-leak-this")

        provider = OpenRouterProvider(Settings(api_key="test"), opener=fail)
        with self.assertRaises(ProviderUnavailable) as caught:
            provider.request("test", {})
        self.assertEqual(str(caught.exception), "OSError")

    def test_truncated_reasoning_response_keeps_paid_telemetry(self):
        usage = {
            "prompt_tokens": 1200,
            "completion_tokens": 650,
            "total_tokens": 1850,
            "completion_tokens_details": {"reasoning_tokens": 650},
        }

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                return json.dumps(
                    {
                        "id": "gen-truncated-1",
                        "model": "returned-model",
                        "usage": usage,
                        "choices": [
                            {
                                "finish_reason": "length",
                                "message": {"content": None},
                            }
                        ],
                    }
                ).encode()

        provider = OpenRouterProvider(
            Settings(
                api_key="synthetic-test-key",
                model="requested-model",
                effort="high",
                max_tokens=650,
            ),
            opener=lambda request, timeout: Response(),
        )
        commander = CommanderService(RulesSimulation(), provider)
        decision = commander.decide(LittleRoundTopCatalog().create(), "confederate")
        self.assertTrue(decision["fallback"])
        self.assertEqual(decision["source"], "scripted")
        # The adapter's safe reason: a null content reply cut off at max_tokens.
        self.assertEqual(decision["fallback_reason"], "NoContent")
        self.assertEqual(decision["usage"], usage)
        self.assertEqual(
            decision["usage"]["completion_tokens_details"]["reasoning_tokens"], 650
        )
        self.assertEqual(decision["model"], "returned-model")
        self.assertEqual(decision["response_id"], "gen-truncated-1")
        self.assertEqual(decision["finish_reason"], "length")
        self.assertNotIn("synthetic-test-key", json.dumps(decision))


class ArchitectureTests(unittest.TestCase):
    def test_application_services_do_not_import_concrete_io_adapters(self):
        root = Path(__file__).resolve().parents[1] / "battle"
        for path in (root / "services").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                modules = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                for module in modules:
                    self.assertFalse(
                        any(
                            part in module.split(".")
                            for part in (
                                "storage",
                                "sqlite3",
                                "urllib",
                                "server",
                                "adapters",
                                "config",
                                "bootstrap",
                                "inference",
                            )
                        ),
                        (path.name, module),
                    )

    def test_http_handler_does_not_reach_into_rules_or_storage(self):
        root = Path(__file__).resolve().parents[1] / "battle"
        tree = ast.parse((root / "server.py").read_text())
        handler = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "make_handler"
        )
        names = {n.id for n in ast.walk(handler) if isinstance(n, ast.Name)}
        self.assertFalse(
            names
            & {"engine", "runtime", "Store", "scenario", "inference", "SimulationClock"}
        )


if __name__ == "__main__":
    unittest.main()
