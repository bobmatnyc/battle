"""D37 guards on the paid model batch (docs/research/78): the exact cap, the
key-limit check, the key from the environment only, the pinned model and the
provider-limit stop. Fake openers and fake providers only: no network, no
credential, no spend."""

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest import mock

from battle.adapters.openrouter import KEY_INFO_URL, KeyInfoError, OpenRouterProvider, fetch_key_info, request_body
from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import build_replay
from battle.command_policy import scripted_actions, scripted_policy
from battle.config import Settings
from battle.paid_batch import (
    BT_T28_LRT_V4, D37_OPTION_A, PAID_PLANS, check_key, fake_key_opener, key_limit_check, plan_settings,
)
from battle.scenario import LITTLE_ROUND_TOP
from battle.spend import BudgetExhausted, Price, SpendGuard

POC = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("model_runs", POC / "scripts" / "model_runs.py")
model_runs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model_runs)

SOURCE = {"commit": "0" * 40, "clean": True}
DUMMY_KEY = "dummy-not-a-key"  # A placeholder; no opener here reaches a network.
SONNET = "anthropic/claude-sonnet-5.5"
# Reserves of exactly $0.01 and $0.02 with a zero-byte body: 1,024 overhead tokens at
# $0.0009765625 per million ($0.000001) plus 9,999 or 19,999 output tokens at $1 per million.
CENT, TWO_CENTS = (0.0009765625, 1.0, 9999), (0.0009765625, 1.0, 19999)


class Reply:
    """A urllib response stand-in."""

    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, limit=-1):
        return self.body


def http_error(code, body=None):
    raw = json.dumps(body).encode() if body is not None else b"not json"
    return urllib.error.HTTPError("https://openrouter.ai/x", code, "refused", {}, io.BytesIO(raw))


class ChatOpener:
    """Answers chat-completions requests with the entry's scripted orders and
    a cost, until call ``refuse_at``, which gets ``refusal`` (an exception to
    raise or a body to return). Every request body is kept."""

    def __init__(self, entry, refuse_at=None, refusal=None, cost=0.01):
        self.entry, self.refuse_at, self.refusal, self.cost = entry, refuse_at, refusal, cost
        self.bodies = []

    def __call__(self, request, timeout):
        body = json.loads(request.data)
        self.bodies.append(body)
        if len(self.bodies) == self.refuse_at:
            if isinstance(self.refusal, BaseException):
                raise self.refusal
            return Reply(self.refusal)
        observation = json.loads(body["messages"][1]["content"])["observation"]
        side = observation["side"]
        _, orders = scripted_actions(scripted_policy(self.entry, side), observation, self.entry.sides[side].role)
        return Reply({"id": f"gen-{len(self.bodies)}", "model": body["model"],
                      "choices": [{"finish_reason": "stop",
                                   "message": {"content": json.dumps({"text": "Orders.", "orders": orders})}}],
                      "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": self.cost}})


class CostFake:
    """A provider fake whose n-th call costs ``costs[n-1]``."""

    available, model, effort = True, "fake/d37", "high"

    def __init__(self, entry, costs):
        self.entry, self.costs, self.calls = entry, costs, 0

    def request(self, instruction, payload):
        self.calls += 1
        side = payload["observation"]["side"]
        _, orders = scripted_actions(scripted_policy(self.entry, side), payload["observation"],
                                     self.entry.sides[side].role)
        return {"text": "Orders.", "orders": orders}, {"model": self.model, "response_id": f"gen-{self.calls}",
                                                       "usage": {"cost": self.costs[self.calls - 1]}}


def git_repo(path):
    for args in (("init", "-q"), ("commit", "-q", "--allow-empty", "-m", "base")):
        subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                       check=True, capture_output=True)


def never(*args, **kwargs):
    raise AssertionError("this opener or provider must not be called")


def key_reply(**data):
    base = {"limit": 14.0, "limit_remaining": 14.0, "limit_reset": None, "is_free_tier": False, "usage": 0,
            "label": "masked-key-label-placeholder"}  # OpenRouter's label can show part of the key.
    return lambda request, timeout: Reply({"data": {**base, **data}})


def batch_files(directory):
    return "".join(p.read_text() for p in Path(directory).iterdir() if p.suffix in (".json", ".jsonl"))


class ExactCapTest(unittest.TestCase):
    """Item 1: spend so far + the call's reserve may equal the cap, never pass it."""

    def test_a_call_landing_exactly_on_the_cap_is_allowed_and_one_cent_over_is_refused(self):
        size = lambda instruction, payload: 0  # noqa: E731 - only the 1,024 overhead tokens are input.
        cent = Price(*CENT)  # (1,024 x 0.0009765625 + 9,999 x 1) per million: $0.01.
        exact = SpendGuard(14.0, cent, size)
        exact.charge(13.99)
        exact.check("i", {})  # 13.99 + 0.01 == 14.00: allowed.
        over = SpendGuard(14.0, Price(*TWO_CENTS), size)
        over.charge(13.99)
        with self.assertRaises(BudgetExhausted):
            over.check("i", {})  # 13.99 + 0.02 == 14.01: refused.
        full = SpendGuard(14.0, cent, size, spent_usd=14.0)
        with self.assertRaises(BudgetExhausted):
            full.check("i", {})
        self.assertTrue(full.at_cap())

    def test_the_exact_cap_call_is_sent_and_the_cent_over_call_is_never_sent(self):
        # Pegasus default makes 2 player calls: the first costs $13.99, the second's reserve is
        # $0.01 (exactly the cap) or $0.02 (a cent over).
        for rates, calls, status in ((CENT, 2, "model_game"), (TWO_CENTS, 1, "stopped")):
            fakes = []
            with self.subTest(rates=rates), tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()), \
                    mock.patch.object(model_runs, "request_size", lambda settings: lambda i, p: 0):
                code, summary = model_runs.run_batch(
                    ["pegasus-bridge"], 1, 14.0, Path(tmp) / "b", price=Price(*rates), source=SOURCE,
                    provider_for=lambda e: fakes.append(CostFake(e, [13.99, 0.01])) or fakes[-1])
                self.assertEqual(fakes[0].calls, calls)
                self.assertEqual(code, model_runs.EXIT_CAP)
                self.assertEqual(summary["model_games"] + len(summary["stopped_or_failed"]), 1)
                if status == "stopped":
                    self.assertEqual(summary["stopped_or_failed"][0]["status"], "stopped")
                self.assertLessEqual(summary["spent_usd"], 14.0)


class KeyLimitTest(unittest.TestCase):
    """Item 2: the key's own limit, checked before any spend, fail closed."""

    def test_key_limit_check_accepts_an_unlimited_key_or_one_with_the_cap_remaining(self):
        good = {"limit": 14.0, "limit_remaining": 14.0, "limit_reset": None, "is_free_tier": False, "usage": 0}
        record = key_limit_check(good, 14.0)
        self.assertTrue(record["ok"], record)
        self.assertFalse(record["unlimited"])
        self.assertNotIn("label", record)
        # B62: the limit itself may be above the cap; only the remaining credit must cover it.
        for name, change in {"limit below remaining": {"limit": 10, "limit_remaining": 14},
                             "limit above the cap": {"limit": 14.01}, "limit $20": {"limit": 20.0},
                             "remaining above the cap": {"limit": 500.0, "limit_remaining": 312.5}}.items():
            with self.subTest(name):
                passed = key_limit_check({**good, **change}, 14.0)
                self.assertTrue(passed["ok"], passed)
                self.assertFalse(passed["unlimited"])
        # B62: both null is an unlimited key; it passes and says so.
        unlimited = key_limit_check({**good, "limit": None, "limit_remaining": None, "usage": 3.5}, 14.0)
        self.assertEqual((unlimited["ok"], unlimited["unlimited"], unlimited["reasons"]), (True, True, []))
        self.assertEqual((unlimited["limit"], unlimited["limit_remaining"]), (None, None))
        # bt-T24 (Bob, option B): a resetting limit passes when the cap remains; the record keeps the reset.
        for name, change in {"limited, resets monthly": {"limit_reset": "monthly"},
                             "limited, resets daily": {"limit_reset": "daily"},
                             "limited, resets weekly, $20 limit": {"limit": 20.0, "limit_reset": "weekly"},
                             "limited, other reset string": {"limit_reset": "hourly"},
                             "unlimited, resets monthly": {"limit": None, "limit_remaining": None,
                                                           "limit_reset": "monthly"}}.items():
            with self.subTest(name):
                passed = key_limit_check({**good, **change}, 14.0)
                self.assertEqual((passed["ok"], passed["reasons"]), (True, []))
                self.assertEqual(passed["limit_reset"], change["limit_reset"])
                self.assertEqual(passed["unlimited"], name.startswith("unlimited"))
        absent ={k: v for k, v in good.items() if k not in ("limit", "limit_remaining")}
        bad = {
            "limit null, remaining set": {"limit": None},
            "remaining null, limit set": {"limit_remaining": None},
            "remaining below the cap": {"limit_remaining": 13.99},
            "unlimited but free tier": {"limit": None, "limit_remaining": None, "is_free_tier": True},
            "unlimited but the reset is empty": {"limit": None, "limit_remaining": None, "limit_reset": ""},
            "unlimited but the reset is a number": {"limit": None, "limit_remaining": None, "limit_reset": 30},
            "remaining not a number": {"limit_remaining": "14"},
            "remaining a boolean": {"limit_remaining": True},
            "free tier": {"is_free_tier": True},
            "free tier not a boolean": {"is_free_tier": "no"},
            "limit not a number": {"limit": "14"},
            "limit a boolean": {"limit": True},
            "remaining missing": {"limit_remaining": float("nan")},
            # bt-T24: a resetting key still needs the cap remaining, and the reset must be a non-empty string.
            "resets monthly, remaining below the cap": {"limit_reset": "monthly", "limit_remaining": 13.99},
            "resets monthly, free tier": {"limit_reset": "monthly", "is_free_tier": True},
            "resets monthly, only limit null": {"limit_reset": "monthly", "limit": None},
            "resets monthly, remaining not a number": {"limit_reset": "monthly", "limit_remaining": "14"},
            "limit_reset empty string": {"limit_reset": ""},
            "limit_reset only whitespace": {"limit_reset": "  "},
            "limit_reset a number": {"limit_reset": 30},
            "limit_reset zero": {"limit_reset": 0},
            "limit_reset true": {"limit_reset": True},
            "limit_reset false": {"limit_reset": False},
            "limit_reset a list": {"limit_reset": ["monthly"]},
            "limit_reset an object": {"limit_reset": {"every": "month"}},
        }
        for name, change in bad.items():
            with self.subTest(name):
                refused = key_limit_check({**good, **change}, 14.0)
                self.assertFalse(refused["ok"])
                self.assertEqual(refused["unlimited"], name.startswith("unlimited"))  # As read, not the verdict.
        # A missing field is not a null one: absent limit fields, or no data, fail closed.
        # bt-T21 review: a reply missing is_free_tier or limit_reset is refused, unlimited or not.
        both_null = {**good, "limit": None, "limit_remaining": None}
        without = lambda info, *names: {k: v for k, v in info.items() if k not in names}  # noqa: E731
        shapes = (without(both_null, "limit_reset", "is_free_tier", "usage"),
                  without(both_null, "is_free_tier"), without(both_null, "limit_reset"),
                  without(good, "is_free_tier"), without(good, "limit_reset"),
                  without(good, "limit_reset", "is_free_tier", "usage"))
        for info in (absent, {**absent, "limit": None}, {}, "junk", *shapes):
            with self.subTest(info=info):
                self.assertFalse(key_limit_check(info, 14.0)["ok"])

    def test_key_info_call_is_a_get_with_the_key_and_fails_closed(self):
        seen = []

        def opener(request, timeout):
            seen.append((request.full_url, request.get_method(), request.get_header("Authorization")))
            return Reply({"data": {"limit": 14.0}})

        self.assertEqual(fetch_key_info(DUMMY_KEY, opener=opener), {"limit": 14.0})
        self.assertEqual(seen, [(KEY_INFO_URL, "GET", "Bearer " + DUMMY_KEY)])
        self.assertEqual(KEY_INFO_URL, "https://openrouter.ai/api/v1/key")
        failures = {
            "HTTP 500": (http_error(500), False), "HTTP 401": (http_error(401), True),
            "HTTP 403": (http_error(403), True), "URLError": (urllib.error.URLError("down"), False),
            "TimeoutError": (TimeoutError(), False),
        }
        for reason, (exc, rejected) in failures.items():
            def raising(request, timeout, exc=exc):
                raise exc
            with self.subTest(reason), self.assertRaises(KeyInfoError) as caught:
                fetch_key_info(DUMMY_KEY, opener=raising)
            self.assertEqual((str(caught.exception), caught.exception.rejected), (reason, rejected))
        for junk in (b"not json", b"[]", b'{"data": null}', b'{"error": {"code": 401}}'):
            reply = Reply(None)
            reply.body = junk
            with self.subTest(junk), self.assertRaises(KeyInfoError):
                fetch_key_info(DUMMY_KEY, opener=lambda request, timeout, r=reply: r)

    def test_main_refuses_to_start_when_the_key_check_fails_and_records_a_passing_check_without_the_key(self):
        argv = ["--plan", "pegasus-bridge", "--model", SONNET, "--games", "1", "--cap-usd", "14"]
        env = {"OPENROUTER_API_KEY": DUMMY_KEY}
        for opener in (key_reply(limit=None), key_reply(limit_remaining=None), key_reply(limit_remaining=1.0),
                       key_reply(is_free_tier=True), key_reply(limit_reset="monthly", limit_remaining=13.99),
                       key_reply(limit_reset=""), key_reply(limit_reset=30),
                       lambda request, timeout: (_ for _ in ()).throw(OSError())):
            with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as err, \
                    self.assertRaises(SystemExit) as refused:
                git_repo(tmp)
                model_runs.main([*argv, "--dir", str(Path(tmp) / "b")], provider_for=never, repo=tmp,
                                environ=env, key_opener=opener)
            self.assertEqual(refused.exception.code, 2)
            self.assertNotIn(DUMMY_KEY, err.getvalue())
            self.assertFalse((Path(tmp) / "b").exists())
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            git_repo(tmp)
            model_runs.main([*argv, "--dir", str(Path(tmp) / "b")], repo=tmp, environ=env,
                            key_opener=key_reply(), provider_for=lambda e: CostFake(e, [0.01] * 10))
            manifest = json.loads((Path(tmp) / "b" / "manifest.json").read_text())
            written = batch_files(Path(tmp) / "b")
        check = manifest["key_check"]
        self.assertEqual((check["ok"], check["limit"], check["limit_remaining"], check["is_free_tier"]),
                         (True, 14.0, 14.0, False))
        self.assertEqual(check["endpoint"], KEY_INFO_URL)
        self.assertNotIn(DUMMY_KEY, written)
        self.assertNotIn("masked-key-label", written)  # The key's label is not recorded.


class KeyFromEnvironmentTest(unittest.TestCase):
    """Item 3: the paid path takes the key from the injected environment only."""

    def test_a_key_only_in_env_local_is_refused(self):
        argv = ["--plan", "pegasus-bridge", "--model", SONNET, "--games", "1", "--cap-usd", "14"]
        with tempfile.TemporaryDirectory() as root:
            dotenv = Path(root) / ".env.local"  # Outside the repo, so the tree stays clean.
            dotenv.write_text(f"OPENROUTER_API_KEY={DUMMY_KEY}\n")
            tmp = Path(root) / "repo"
            tmp.mkdir()
            git_repo(tmp)
            defaults = (dotenv, None)  # Settings.load() would read this file by default.
            with mock.patch.object(Settings.load.__func__, "__defaults__", defaults), \
                    mock.patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True):
                self.assertEqual(Settings.load().api_key, DUMMY_KEY)  # The trap is armed.
                for args in (argv, ["--paid-plan", D37_OPTION_A.name]):
                    with self.subTest(args[0]), redirect_stderr(io.StringIO()) as err, \
                            redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
                        model_runs.main([*args, "--dir", str(Path(tmp) / "b")], repo=tmp,
                                        provider_for=lambda e: CostFake(e, [0.0] * 10))
                    self.assertEqual(refused.exception.code, 2)
                    self.assertIn("OPENROUTER_API_KEY is missing", err.getvalue())
                    self.assertFalse((Path(tmp) / "b").exists())

    def test_missing_empty_or_rejected_key_refuses_to_start(self):
        cases = {"missing": ({}, never), "empty": ({"OPENROUTER_API_KEY": "  "}, never),
                 "rejected 401": ({"OPENROUTER_API_KEY": DUMMY_KEY},
                                  lambda request, timeout: (_ for _ in ()).throw(http_error(401))),
                 "rejected 403": ({"OPENROUTER_API_KEY": DUMMY_KEY},
                                  lambda request, timeout: (_ for _ in ()).throw(http_error(403)))}
        for name, (env, opener) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp, \
                    redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as refused:
                git_repo(tmp)
                model_runs.main(["--paid-plan", D37_OPTION_A.name, "--dir", str(Path(tmp) / "b")], repo=tmp,
                                environ=env, key_opener=opener, chat_opener=never)
            self.assertEqual(refused.exception.code, 2)
            self.assertIn("rejected" if name.startswith("rejected") else "missing or empty", err.getvalue())
            self.assertFalse((Path(tmp) / "b").exists())
        with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY"):
            model_runs.run_batch(["pegasus-bridge"], 1, 14.0, "unused", price=Price(2.0, 10.0, 4000), source=SOURCE,
                                 settings=Settings(model=SONNET, effort="high", max_tokens=4000),
                                 key_check={"ok": True}, opener=never)
        with self.assertRaisesRegex(ValueError, "key-limit check"):
            model_runs.run_batch(["pegasus-bridge"], 1, 14.0, "unused", price=Price(2.0, 10.0, 4000), source=SOURCE,
                                 settings=Settings(api_key=DUMMY_KEY, model=SONNET, effort="high", max_tokens=4000),
                                 key_check=None, opener=never)


def paid_run(tmp, chat, plan=D37_OPTION_A, key_opener=None):
    """Runs ``--paid-plan <plan>`` (default d37-option-a) with fake key and chat openers."""
    git_repo(tmp)
    with redirect_stdout(io.StringIO()):
        code = model_runs.main(["--paid-plan", plan.name, "--dir", str(Path(tmp) / "b")], repo=tmp,
                               environ={"OPENROUTER_API_KEY": DUMMY_KEY},
                               key_opener=key_opener or fake_key_opener(14.0), chat_opener=chat)
    out = Path(tmp) / "b"
    return (code, json.loads((out / "manifest.json").read_text()),
            [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines()],
            json.loads((out / "batch-summary.json").read_text()), out)


class PinnedModelTest(unittest.TestCase):
    """Item 4: the paid plan fixes Sonnet 5.5 in the body, the price and the manifest."""

    def test_paid_plan_pins_sonnet_in_body_price_and_manifest_and_refuses_overrides(self):
        for extra in (["--model", "openai/gpt-4.1-mini"], ["--model", SONNET], ["--cap-usd", "20"],
                      ["--games", "2"], ["--plan", "pegasus-bridge"], ["--effort", "low"],
                      ["--input-price", "0", "--output-price", "0"]):
            with self.subTest(extra), tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as err, \
                    redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
                git_repo(tmp)
                model_runs.main(["--paid-plan", D37_OPTION_A.name, *extra, "--dir", str(Path(tmp) / "b")], repo=tmp,
                                environ={"OPENROUTER_API_KEY": DUMMY_KEY}, key_opener=fake_key_opener(14.0),
                                chat_opener=never)
            self.assertEqual(refused.exception.code, 2)
            self.assertIn("--paid-plan d37-option-a fixes", err.getvalue())
            self.assertFalse((Path(tmp) / "b").exists())
        # Little Round Top is first; three calls are answered, the fourth is refused for credit.
        chat = ChatOpener(LITTLE_ROUND_TOP, refuse_at=4, refusal=http_error(402, {"error": {"code": 402}}))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OPENROUTER_MODEL": "x/y"}):
            code, manifest, games, summary, _ = paid_run(tmp, chat)
        self.assertEqual({b["model"] for b in chat.bodies}, {SONNET})
        self.assertEqual({(b["max_tokens"], b["reasoning"]["effort"]) for b in chat.bodies}, {(4000, "high")})
        self.assertEqual((manifest["model"], manifest["cap_usd"], manifest["paid_plan"]),
                         (SONNET, 14.0, "d37-option-a"))
        self.assertEqual((manifest["prices"]["input_per_mtok"], manifest["prices"]["output_per_mtok"]), (2.0, 10.0))
        self.assertEqual(manifest["games_per_item"], dict(D37_OPTION_A.items))
        self.assertEqual(sum(manifest["games_per_item"].values()), 12)
        self.assertEqual(games[0]["pins"]["model"], SONNET)
        self.assertEqual((code, summary["planned"]), (model_runs.EXIT_PROVIDER_LIMIT, 12))

    def test_dry_run_prints_the_plan_and_a_fake_key_check_with_no_key_or_network(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as out:
            git_repo(tmp)
            code = model_runs.main(["--paid-plan", D37_OPTION_A.name, "--dry-run"], repo=tmp, environ={},
                                   key_opener=never, chat_opener=never)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [".git"])
        shown = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((shown["model"], shown["cap_usd"], shown["games"]), (SONNET, 14.0, 12))
        self.assertEqual(shown["plan"], dict(D37_OPTION_A.items))
        self.assertEqual(shown["play_order"], [f"{item} x{n}" for item, n in D37_OPTION_A.items])
        self.assertTrue(shown["key_check"]["ok"])
        self.assertIn("fake", shown["key_check"]["opener"])


class SingleGamePlanTest(unittest.TestCase):
    """bt-T28: ``bt-t28-lrt-v4`` is one Little Round Top game at the D37 settings, under the same guards."""

    def test_bt_t28_plan_is_one_little_round_top_game_at_the_d37_settings(self):
        self.assertIs(PAID_PLANS["bt-t28-lrt-v4"], BT_T28_LRT_V4)
        self.assertEqual((BT_T28_LRT_V4.items, BT_T28_LRT_V4.games, BT_T28_LRT_V4.plan()),
                         ((("little-round-top", 1),), 1, ["little-round-top:1"]))
        fields = ("model", "effort", "max_tokens", "timeout", "cap_usd")
        self.assertEqual([getattr(BT_T28_LRT_V4, f) for f in fields], [SONNET, "high", 4000, 90.0, 14.0])
        self.assertEqual([getattr(BT_T28_LRT_V4, f) for f in fields], [getattr(D37_OPTION_A, f) for f in fields])
        self.assertEqual(plan_settings(BT_T28_LRT_V4), plan_settings(D37_OPTION_A))
        self.assertIn("12:51Z", BT_T28_LRT_V4.ruling)
        self.assertIn("bt-T28", BT_T28_LRT_V4.ruling)
        self.assertEqual(D37_OPTION_A.games, 12)  # The D37 plan is unchanged.

    def test_bt_t28_dry_run_reads_no_key_calls_nothing_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as out:
            git_repo(tmp)
            code = model_runs.main(["--paid-plan", BT_T28_LRT_V4.name, "--dir", str(Path(tmp) / "b"), "--dry-run"],
                                   repo=tmp, environ={}, key_opener=never, chat_opener=never)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [".git"])
        shown = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((shown["paid_plan"], shown["model"], shown["cap_usd"], shown["games"], shown["plan"]),
                         ("bt-t28-lrt-v4", SONNET, 14.0, 1, {"little-round-top": 1}))
        self.assertEqual(shown["key"], "not read in a dry run")

    def test_bt_t28_plan_keeps_the_override_refusal_reservation_and_provider_limit_stop(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as err, \
                redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            git_repo(tmp)
            model_runs.main(["--paid-plan", BT_T28_LRT_V4.name, "--games", "2", "--dir", str(Path(tmp) / "b")],
                            repo=tmp, environ={"OPENROUTER_API_KEY": DUMMY_KEY},
                            key_opener=fake_key_opener(14.0), chat_opener=never)
        self.assertIn("--paid-plan bt-t28-lrt-v4 fixes", err.getvalue())
        # The D37 key's shape: a $50 limit that resets monthly, with the cap remaining (bt-T24).
        resetting = key_reply(limit=50.0, limit_remaining=36.0, limit_reset="monthly", usage=14.0)
        refusal = http_error(402, {"error": {"code": 402, "metadata": {"limit_source": "openrouter_credits"}}})
        chat = ChatOpener(LITTLE_ROUND_TOP, refuse_at=3, refusal=refusal)
        with tempfile.TemporaryDirectory() as tmp:
            code, manifest, games, summary, _ = paid_run(tmp, chat, BT_T28_LRT_V4, resetting)
        self.assertEqual((code, len(chat.bodies), summary["planned"]), (model_runs.EXIT_PROVIDER_LIMIT, 3, 1))
        self.assertEqual({(b["model"], b["max_tokens"], b["reasoning"]["effort"]) for b in chat.bodies},
                         {(SONNET, 4000, "high")})
        self.assertEqual((manifest["paid_plan"], manifest["key_check"]["limit_reset"]), ("bt-t28-lrt-v4", "monthly"))
        self.assertEqual(games[0]["pins"]["sides"]["union"]["prompt_version"], "lrt-side-v4")
        self.assertEqual((manifest["closed"]["played"], manifest["closed"]["not_started"]), (1, 0))
        # The reservation: after a $13.99 call the next call's reserve would pass $14, so it is never sent.
        chat = ChatOpener(LITTLE_ROUND_TOP, cost=13.99)
        with tempfile.TemporaryDirectory() as tmp:
            code, manifest, games, summary, _ = paid_run(tmp, chat, BT_T28_LRT_V4)
        self.assertEqual((code, len(chat.bodies)), (model_runs.EXIT_CAP, 1))
        self.assertLessEqual(manifest["closed"]["spent_usd"], 14.0)


class ProviderLimitTest(unittest.TestCase):
    """Item 5: a credit or budget refusal stops the batch and keeps the partial game."""

    def run_refused(self, refusal, refuse_at=3):
        chat = ChatOpener(LITTLE_ROUND_TOP, refuse_at=refuse_at, refusal=refusal)
        settings = Settings(api_key=DUMMY_KEY, model=SONNET, effort="high", max_tokens=4000, timeout=90.0)
        check = check_key(DUMMY_KEY, 14.0, opener=fake_key_opener(14.0))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "b"
        with redirect_stdout(io.StringIO()):
            code, summary = model_runs.run_batch(["little-round-top"], 2, 14.0, out, price=Price(2.0, 10.0, 4000),
                                                 source=SOURCE, settings=settings, key_check=check, opener=chat,
                                                 paid_plan=D37_OPTION_A.name)
        games = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines()]
        manifest = json.loads((out / "manifest.json").read_text())
        return code, summary, games, manifest, chat, out

    def test_a_provider_credit_refusal_stops_the_batch_and_keeps_the_partial_game(self):
        refusals = {
            "HTTP 402 openrouter_key_limit": http_error(402, {"error": {"code": 402, "message": "m", "metadata": {
                "limit_source": "openrouter_key_limit"}}}),
            "HTTP 402 unnamed": http_error(402),
            "HTTP 403 openrouter_guardrail_budget": http_error(403, {"error": {"code": 403, "metadata": {
                "limit_source": "openrouter_guardrail_budget"}}}),
            "HTTP 402 openrouter_credits": {"id": "gen-x", "error": {"code": 402, "metadata": {
                "limit_source": "openrouter_credits"}}},  # An in-body refusal with HTTP 200.
        }
        for reason, refusal in refusals.items():
            with self.subTest(reason):
                code, summary, games, manifest, chat, out = self.run_refused(refusal)
                self.assertEqual(code, model_runs.EXIT_PROVIDER_LIMIT)
                self.assertEqual(len(chat.bodies), 3)  # Nothing is sent after the refusal.
                stopped = games[0]
                self.assertEqual((stopped["status"], stopped["reason"]), ("stopped", f"provider_limit: {reason}"))
                self.assertTrue(stopped["db"].endswith(".stopped.sqlite"))
                self.assertTrue(Path(stopped["db"]).exists())
                self.assertAlmostEqual(stopped["cost_usd"], 0.02)
                self.assertEqual((summary["status"], summary["reason"], summary["not_started"]),
                                 ("provider_limit", stopped["reason"], 1))
                self.assertAlmostEqual(summary["spent_usd"], 0.02)
                self.assertEqual((manifest["closed"]["status"], manifest["closed"]["reason"]),
                                 ("provider_limit", stopped["reason"]))
                self.assertAlmostEqual(manifest["closed"]["spent_usd"], 0.02)
                replay = build_replay(Path(stopped["db"]))
                state = replay.repository.load(replay.repository.latest())
                mine = [d for d in state["decisions"] if d.get("side") == LITTLE_ROUND_TOP.player]
                self.assertEqual([d["fallback"] for d in mine], [False, False])  # No scripted fallback kept.
                self.assertEqual(sorted(p.name for p in out.iterdir() if p.suffix == ".sqlite"),
                                 ["little-round-top-1.stopped.sqlite"])

    def test_other_refusals_fail_the_game_as_before(self):
        for refusal in (http_error(403, {"error": {"code": 403, "message": "flagged"}}),
                        http_error(429, {"error": {"code": 429, "metadata": {"error_type": "rate_limit_exceeded"}}})):
            with self.subTest(refusal.code):
                code, summary, games, _, chat, _ = self.run_refused(refusal)
                self.assertEqual((code, summary["status"]), (model_runs.EXIT_FAILED, "failed"))
                self.assertEqual(games[0]["reason"], f"fallback: provider_error HTTP {refusal.code}")
                self.assertNotIn("provider_limit", games[0])
                self.assertEqual(len(chat.bodies), 3)


class SizedCostFake(CostFake):
    """A ``CostFake`` that also keeps the byte length of the body the adapter
    would send for each call under ``settings``."""

    def __init__(self, entry, costs, settings):
        super().__init__(entry, costs)
        self.settings, self.sizes = settings, []

    def request(self, instruction, payload):
        self.sizes.append(len(request_body(self.settings, instruction, payload)))
        return super().request(instruction, payload)


def sonnet_reserve(body_bytes):
    """The worst-case call at the D37 rates, worked by hand from RESERVE_BASIS (not
    through battle.spend): (body + 1,024) input tokens at $2 and 4,000 output tokens at
    $10 per million."""
    return (Decimal(body_bytes + 1024) * 2 + Decimal(4000) * 10) / Decimal(1_000_000)


GENERIC = ["--plan", "pegasus-bridge", "--model", SONNET, "--games", "1", "--cap-usd", "14"]


class UnlimitedKeyTest(unittest.TestCase):
    """B62: the current key has no credit limit; the $14 cap rests on the reservation,
    cost reconciliation and the provider-limit stop."""

    def test_the_call_whose_real_sonnet_reserve_would_pass_the_cap_is_never_sent(self):
        settings = plan_settings(D37_OPTION_A)  # Sonnet 5.5, effort high, 4,000 tokens; no key.
        price = model_runs.price_for(settings)
        self.assertEqual((price.input_per_mtok, price.output_per_mtok, price.max_output_tokens), (2.0, 10.0, 4000))

        def run(costs):
            fakes = []
            with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
                code, summary = model_runs.run_batch(
                    ["pegasus-bridge"], 1, 14.0, Path(tmp) / "b", price=price, source=SOURCE, settings=settings,
                    provider_for=lambda e: fakes.append(SizedCostFake(e, costs, settings)) or fakes[-1])
            return code, summary, fakes[0]

        _, _, probe = run([0.01, 0.01])  # Pegasus default: two player calls; their real body sizes.
        self.assertEqual(probe.calls, 2)
        self.assertGreater(probe.sizes[1], 1000)  # The real body, not a zero-byte stand-in.
        second = sonnet_reserve(probe.sizes[1])
        self.assertGreater(second, Decimal("0.04"))  # 4,000 output tokens at $10 alone are $0.04.
        # Landing exactly on the cap: the second call is sent.
        code, summary, fake = run([float(Decimal(14) - second), float(second)])
        self.assertEqual((fake.calls, fake.sizes), (2, probe.sizes))
        self.assertEqual((code, summary["spent_usd"]), (model_runs.EXIT_CAP, 14.0))
        # One millionth of a dollar more spent first: the second call's reserve would pass $14.
        code, summary, fake = run([float(Decimal(14) - second + Decimal("0.000001")), 0.01])
        self.assertEqual(fake.calls, 1)  # The second call is never sent.
        self.assertEqual(code, model_runs.EXIT_CAP)
        stopped = summary["stopped_or_failed"][0]
        self.assertEqual(stopped["status"], "stopped")
        self.assertTrue(stopped["reason"].startswith("budget: "), stopped["reason"])
        self.assertLessEqual(summary["spent_usd"], 14.0)

    def test_a_402_through_main_stops_the_paid_batch_with_exit_5_and_closes_the_manifest(self):
        refusal = http_error(402, {"error": {"code": 402, "metadata": {"limit_source": "openrouter_credits"}}})
        chat = ChatOpener(LITTLE_ROUND_TOP, refuse_at=3, refusal=refusal)
        with tempfile.TemporaryDirectory() as tmp:
            code, manifest, games, summary, out = paid_run(tmp, chat)
            databases = sorted(p.name for p in out.iterdir() if p.suffix == ".sqlite")
            kept = Path(games[0]["db"]).exists()
        self.assertEqual(code, model_runs.EXIT_PROVIDER_LIMIT)
        self.assertEqual(len(chat.bodies), 3)  # Nothing is sent after the refusal.
        self.assertEqual(databases, ["little-round-top-1.stopped.sqlite"])
        self.assertTrue(kept)
        reason = "provider_limit: HTTP 402 openrouter_credits"
        self.assertEqual((games[0]["status"], games[0]["reason"]), ("stopped", reason))
        closed = manifest["closed"]
        self.assertEqual((closed["status"], closed["exit"], closed["reason"], closed["played"], closed["not_started"]),
                         ("provider_limit", 5, reason, 1, 11))
        self.assertAlmostEqual(closed["spent_usd"], 0.02)
        self.assertEqual((summary["status"], summary["exit"]), ("provider_limit", 5))

    def test_a_key_with_no_limit_passes_through_main_and_the_manifest_says_unlimited(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            git_repo(tmp)
            code = model_runs.main([*GENERIC, "--dir", str(Path(tmp) / "b")], repo=tmp,
                                   environ={"OPENROUTER_API_KEY": DUMMY_KEY},
                                   key_opener=key_reply(limit=None, limit_remaining=None, usage=3.5),
                                   provider_for=lambda e: CostFake(e, [0.01] * 10))
            manifest = json.loads((Path(tmp) / "b" / "manifest.json").read_text())
            written = batch_files(Path(tmp) / "b")
        self.assertEqual(code, model_runs.EXIT_DONE)
        check = manifest["key_check"]
        self.assertEqual((check["ok"], check["unlimited"], check["limit"], check["limit_remaining"], check["usage"]),
                         (True, True, None, None, 3.5))
        self.assertEqual(check["endpoint"], KEY_INFO_URL)
        self.assertNotIn(DUMMY_KEY, written)
        self.assertNotIn("masked-key-label", written)

    def test_a_monthly_reset_key_with_the_cap_remaining_passes_through_main_and_the_manifest_records_the_reset(self):
        # bt-T24 (Bob, option B): the battle key's limit resets monthly; with $14 remaining it may run.
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            git_repo(tmp)
            code = model_runs.main([*GENERIC, "--dir", str(Path(tmp) / "b")], repo=tmp,
                                   environ={"OPENROUTER_API_KEY": DUMMY_KEY},
                                   key_opener=key_reply(limit=20.0, limit_remaining=14.0, limit_reset="monthly",
                                                        usage=6.0),
                                   provider_for=lambda e: CostFake(e, [0.01] * 10))
            manifest = json.loads((Path(tmp) / "b" / "manifest.json").read_text())
            written = batch_files(Path(tmp) / "b")
            every_byte = b"".join(p.read_bytes() for p in (Path(tmp) / "b").rglob("*") if p.is_file())
        self.assertNotIn(DUMMY_KEY.encode(), every_byte)  # Every file, the game databases included.
        self.assertNotIn(b"masked-key-label", every_byte)
        self.assertEqual(code, model_runs.EXIT_DONE)
        check = manifest["key_check"]
        self.assertEqual((check["ok"], check["unlimited"], check["limit_reset"], check["limit"],
                          check["limit_remaining"], check["usage"]), (True, False, "monthly", 20.0, 14.0, 6.0))
        self.assertEqual(check["endpoint"], KEY_INFO_URL)
        self.assertNotIn("label", check)
        self.assertNotIn(DUMMY_KEY, written)
        self.assertNotIn("masked-key-label", written)


class ReviewFixesTest(unittest.TestCase):
    """Code-critic on 998063c, items A (price overrides), B (named plan) and D (redirects).
    Item C is a case in `test_key_limit_check_accepts_an_unlimited_key_or_one_with_the_cap_remaining`."""

    def refused(self, argv, **kwargs):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as err, \
                redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            git_repo(tmp)
            model_runs.main([*argv, "--dir", str(Path(tmp) / "b")], repo=tmp,
                            environ={"OPENROUTER_API_KEY": DUMMY_KEY}, **kwargs)
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse((Path(tmp) / "b").exists())
        return err.getvalue()

    def test_price_overrides_cannot_lower_a_listed_price_and_no_rate_is_zero(self):
        for rates in (["0", "0"], ["0.001", "0.001"], ["2", "10"]):
            with self.subTest(rates):
                err = self.refused([*GENERIC, "--input-price", rates[0], "--output-price", rates[1]],
                                   provider_for=never, key_opener=fake_key_opener(14.0), chat_opener=never)
                self.assertIn("listed price", err)
        for rates in ((0.0, 10.0, 1), (2.0, 0.0, 1), (-1.0, 10.0, 1), (2.0, -0.5, 1)):
            with self.subTest(rates), self.assertRaises(ValueError):
                Price(*rates)

    def test_a_real_run_needs_a_named_plan(self):
        err = self.refused(GENERIC, key_opener=never, chat_opener=never)
        self.assertIn("named plan", err)
        settings = Settings(api_key=DUMMY_KEY, model=SONNET, effort="high", max_tokens=4000, timeout=90.0)
        for plan, cap, model in ((None, 14.0, SONNET), ("no-such-plan", 14.0, SONNET),
                                 (D37_OPTION_A.name, 20.0, SONNET),
                                 (D37_OPTION_A.name, 14.0, "anthropic/claude-opus-5.5")):
            with self.subTest(plan=plan, cap=cap, model=model), tempfile.TemporaryDirectory() as tmp, \
                    self.assertRaisesRegex(ValueError, "named plan"):
                model_runs.run_batch(["pegasus-bridge"], 1, cap, Path(tmp) / "b", price=Price(2.0, 10.0, 4000),
                                     source=SOURCE, settings=replace(settings, model=model),
                                     key_check={"ok": True}, opener=never, paid_plan=plan)
            self.assertFalse((Path(tmp) / "b").exists())
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            git_repo(tmp)  # A dry run of the generic path is still allowed: it spends nothing.
            self.assertEqual(model_runs.main([*GENERIC, "--dry-run"], repo=tmp, environ={}, key_opener=never,
                                             chat_opener=never), 0)

    def test_the_key_header_is_not_copied_on_redirect(self):
        sent = []

        def opener(request, timeout):
            sent.append(request)
            raise OSError("no network in tests")

        with self.assertRaises(KeyInfoError):
            fetch_key_info(DUMMY_KEY, opener=opener)
        settings = Settings(api_key=DUMMY_KEY, model=SONNET, effort="high", max_tokens=4000)
        with self.assertRaises(Exception):
            OpenRouterProvider(settings, opener=opener).request("i", {"observation": {}})
        self.assertEqual(len(sent), 2)
        for request in sent:
            with self.subTest(request.full_url):
                self.assertEqual(request.unredirected_hdrs.get("Authorization"), "Bearer " + DUMMY_KEY)
                self.assertNotIn("Authorization", request.headers)  # urllib copies these on a redirect.


if __name__ == "__main__":
    unittest.main()
