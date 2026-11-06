"""OpenRouter adapter response handling, driven through the real provider.

Every test injects an opener stub; no test makes a network call.
"""

import io
import json
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path

from battle.adapters.openrouter import (
    OpenRouterProvider,
    ProviderUnavailable,
    single_json_object,
)
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


def answer(message_for, finish_reason="stop"):
    """Opener stub whose reply message is built from the request's own observation."""
    requests = []

    def opener(request, timeout):
        requests.append((json.loads(request.data), timeout))
        message = message_for(orders_from(request))
        return Response(json.dumps(body_with(message, finish_reason)).encode())

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


class ExtractionBoundaryTests(unittest.TestCase):
    """Replies whose order object is a fragment, truncated or oversized fall back."""

    def assert_provider_fallback(self, decision, reason):
        self.assertTrue(decision["fallback"])
        self.assertEqual(decision["source"], "scripted")
        self.assertEqual(decision["fallback_stage"], "provider_error")
        self.assertEqual(decision["fallback_reason"], reason)
        self.assertIsNone(decision["proposed_orders"])
        self.assertEqual(decision["reply_format"], "none")
        self.assertEqual(decision["usage"], USAGE)

    def test_object_inside_truncated_wrapper_falls_back(self):
        # The outer object never closes; the inner order object is a fragment.
        def message(orders):
            return {"content": 'ok {"reply": ' + dispatch(orders)}

        self.assert_provider_fallback(decide(answer(message)), "JSONDecodeError")

    def test_orders_array_in_prose_falls_back(self):
        def message(orders):
            return {"content": "Orders: [" + dispatch(orders) + "]"}

        self.assert_provider_fallback(decide(answer(message)), "JSONDecodeError")

    def test_failed_region_before_object_is_ambiguous(self):
        # A draft that fails to decode is a rival candidate; neither is chosen.
        def message(orders):
            return {"content": 'Draft {"text": "x", "orders": [,]} Final ' + dispatch(orders)}

        self.assert_provider_fallback(decide(answer(message)), "AmbiguousJSON")

    def test_footnote_bracket_in_prose_does_not_block_extraction(self):
        def message(orders):
            return {"content": "Per the report [1], orders follow. " + dispatch(orders)}

        decision = decide(answer(message))
        self.assertFalse(decision["fallback"])
        self.assertEqual(decision["reply_format"], "extracted")

    def test_length_finish_with_complete_object_falls_back(self):
        opener = answer(lambda orders: {"content": dispatch(orders)}, finish_reason="length")
        decision = decide(opener)
        self.assert_provider_fallback(decision, "ReplyTruncated")
        self.assertEqual(decision["finish_reason"], "length")

    def test_megabyte_degenerate_reply_fails_fast(self):
        content = "x{" * (512 * 1024)  # 1 MiB of unclosed openers.
        provider = OpenRouterProvider(
            Settings(api_key=SECRET, model="m"),
            opener=lambda request, timeout: Response(
                json.dumps(body_with({"content": content})).encode()
            ),
        )
        started = time.perf_counter()
        with self.assertRaises(ProviderUnavailable) as caught:
            provider.request("i", {})
        self.assertLess(time.perf_counter() - started, 1.0)
        self.assertEqual(str(caught.exception), "ReplyTooLarge")
        self.assertEqual(caught.exception.metadata["usage"], USAGE)

    def test_degenerate_reply_under_cap_stays_fast(self):
        for content in ("x{" * 32700, '{"a":[' * 10900, "{]" * 32700):
            started = time.perf_counter()
            with self.assertRaises(ValueError):
                single_json_object(content)
            self.assertLess(time.perf_counter() - started, 0.25, content[:8])

    def test_reply_format_records_json_extracted_and_tool_call(self):
        def tool_call(orders):
            return {
                "content": None,
                "tool_calls": [{"function": {"name": "f", "arguments": dispatch(orders)}}],
            }

        cases = {
            "json": lambda orders: {"content": dispatch(orders)},
            "extracted": lambda orders: {"content": "Orders: " + dispatch(orders)},
            "tool_call": tool_call,
            "none": lambda orders: {"content": "No orders, General."},
        }
        for expected, message in cases.items():
            self.assertEqual(decide(answer(message))["reply_format"], expected)


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

    def test_unknown_reason_name_is_not_recorded(self):
        # An identifier-shaped reason outside the adapter's names may be content.
        self.assertEqual(failure_kind(ProviderFailure("sk_live_abc123")), "ProviderFailure")
        self.assertEqual(failure_kind(ProviderUnavailable("HTTP 5034")), "ProviderUnavailable")
        for reason in ("ReplyTooLarge", "ReplyTruncated", "AmbiguousJSON", "TimeoutError"):
            self.assertEqual(failure_kind(ProviderUnavailable(reason)), reason)


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
