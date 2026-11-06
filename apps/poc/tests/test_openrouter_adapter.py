"""OpenRouter adapter response handling, driven through the real provider.

Every test injects an opener stub; no test makes a network call.
"""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from battle.adapters.openrouter import OpenRouterProvider, ProviderUnavailable
from battle.adapters.rules import LittleRoundTopCatalog, RulesSimulation
from battle.bootstrap import build_headless
from battle.command_policy import fallback_orders
from battle.config import Settings
from battle.contracts import ProviderFailure
from battle.services.commander import CommanderService, failure_kind

SECRET = "synthetic-credential-value"
USAGE = {
    "prompt_tokens": 900,
    "completion_tokens": 300,
    "completion_tokens_details": {"reasoning_tokens": 47},
}


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return self.body


def body_with(message, finish_reason="stop"):
    return {
        "id": "gen-live-shape",
        "model": "anthropic/claude-sonnet-5.5",
        "usage": USAGE,
        "choices": [{"finish_reason": finish_reason, "message": message}],
    }


def orders_from(request):
    payload = json.loads(json.loads(request.data)["messages"][1]["content"])
    return fallback_orders(payload["observation"])


def answer(message_for):
    """Opener stub whose reply message is built from the request's own observation."""
    requests = []

    def opener(request, timeout):
        requests.append((json.loads(request.data), timeout))
        return Response(json.dumps(body_with(message_for(orders_from(request)))).encode())

    opener.requests = requests
    return opener


def raising(exc):
    def opener(request, timeout):
        raise exc

    return opener


def commander(opener, **settings):
    provider = OpenRouterProvider(
        Settings(api_key=SECRET, model="anthropic/claude-sonnet-5.5", **settings),
        opener=opener,
    )
    return CommanderService(RulesSimulation(), provider)


def decide(opener):
    return commander(opener, effort="high").decide(
        LittleRoundTopCatalog().create(), side="union"
    )


def dispatch(orders):
    return json.dumps({"text": "General, orders follow.", "orders": orders})


class StructuredResponseParsingTests(unittest.TestCase):
    def assert_model_decision(self, decision):
        self.assertEqual(decision["source"], "openrouter")
        self.assertFalse(decision["fallback"])
        self.assertEqual(decision["validation"], {"valid": True, "error": None})
        self.assertTrue(decision["orders"])
        self.assertEqual(decision["orders"], decision["proposed_orders"])
        self.assertEqual(decision["usage"], USAGE)

    def test_order_json_after_prose_parses_to_model_decision(self):
        def message(orders):
            return {
                "content": "General, no enemy contact has been reported. "
                "The orders are as follows.\n" + dispatch(orders)
            }

        self.assert_model_decision(decide(answer(message)))

    def test_fenced_order_json_parses_to_model_decision(self):
        def message(orders):
            return {"content": "Orders:\n```json\n" + dispatch(orders) + "\n```\n"}

        self.assert_model_decision(decide(answer(message)))

    def test_tool_call_arguments_parse_to_model_decision(self):
        def message(orders):
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "issue_orders", "arguments": dispatch(orders)},
                    }
                ],
            }

        self.assert_model_decision(decide(answer(message)))

    def test_prose_only_content_falls_back_with_decode_reason_and_usage(self):
        prose = "General, the orders are as follows. - U1 to [11,13]."
        decision = decide(answer(lambda orders: {"content": prose}))
        self.assertTrue(decision["fallback"])
        self.assertEqual(decision["source"], "scripted")
        self.assertEqual(decision["fallback_stage"], "provider_error")
        self.assertEqual(decision["fallback_reason"], "JSONDecodeError")
        self.assertEqual(decision["usage"], USAGE)
        self.assertEqual(decision["response_id"], "gen-live-shape")
        self.assertNotIn(prose, json.dumps(decision))

    def test_two_json_objects_are_ambiguous_and_fall_back(self):
        def message(orders):
            return {"content": dispatch(orders) + "\nor\n" + dispatch([])}

        decision = decide(answer(message))
        self.assertTrue(decision["fallback"])
        self.assertEqual(decision["fallback_reason"], "AmbiguousJSON")
        self.assertIsNone(decision["proposed_orders"])

    def test_request_body_carries_order_json_schema(self):
        opener = answer(lambda orders: {"content": dispatch(orders)})
        decide(opener)
        body, _ = opener.requests[0]
        response_format = body["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        spec = response_format["json_schema"]
        self.assertTrue(spec["strict"])
        schema = spec["schema"]
        self.assertEqual(set(schema["required"]), {"text", "orders"})
        order = schema["properties"]["orders"]["items"]
        self.assertEqual(set(order["required"]), {"unit_id", "stance", "destination"})
        self.assertFalse(order["additionalProperties"])


class ProviderFailureReasonTests(unittest.TestCase):
    def test_timeout_records_timeout_error(self):
        decision = decide(raising(TimeoutError("read timed out after 18 s")))
        self.assertTrue(decision["fallback"])
        self.assertEqual(decision["fallback_reason"], "TimeoutError")

    def test_connect_timeout_wrapped_in_url_error_records_timeout_error(self):
        decision = decide(raising(urllib.error.URLError(TimeoutError("timed out"))))
        self.assertEqual(decision["fallback_reason"], "TimeoutError")

    def test_http_429_records_http_code_without_body(self):
        error = urllib.error.HTTPError(
            "https://openrouter.ai", 429, "Too Many Requests", {}, io.BytesIO(b"body " + SECRET.encode())
        )
        decision = decide(raising(error))
        self.assertEqual(decision["fallback_reason"], "HTTP 429")
        self.assertNotIn(SECRET, json.dumps(decision))

    def test_unsafe_provider_failure_text_keeps_type_only(self):
        self.assertEqual(failure_kind(ProviderUnavailable("HTTP 503")), "HTTP 503")
        self.assertEqual(
            failure_kind(ProviderFailure("Bearer " + SECRET)), "ProviderFailure"
        )
        self.assertEqual(failure_kind(ValueError("HTTP 500")), "ValueError")


class EffortDefaultTests(unittest.TestCase):
    def test_effort_raises_default_limits_unless_explicit(self):
        plain = Settings(api_key="k")
        high = Settings(api_key="k", effort="high")
        explicit = Settings(api_key="k", effort="high", max_tokens=900, timeout=40.0)
        self.assertEqual((plain.request_max_tokens, plain.request_timeout), (650, 18.0))
        self.assertEqual((high.request_max_tokens, high.request_timeout), (4000, 90.0))
        self.assertEqual((explicit.request_max_tokens, explicit.request_timeout), (900, 40.0))

    def test_cli_effort_without_limits_uses_effort_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = build_headless(
                Path(tmp) / "battle.sqlite",
                player_provider="openrouter",
                settings=Settings(api_key="k", model="m"),
                effort="high",
            )
        settings = runner.commander.provider._settings
        self.assertEqual((settings.request_max_tokens, settings.request_timeout), (4000, 90.0))

    def test_environment_limits_count_as_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings.load(
                path=Path(tmp) / "absent.env",
                environ={"OPENROUTER_EFFORT": "high", "OPENROUTER_MAX_TOKENS": "1200"},
            )
        self.assertEqual((settings.request_max_tokens, settings.request_timeout), (1200, 90.0))

if __name__ == "__main__":
    unittest.main()
