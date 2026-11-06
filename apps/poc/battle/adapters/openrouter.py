"""OpenRouter HTTP adapter. Credentials and urllib never enter application services."""

import json
import urllib.error
import urllib.request
from ..command_policy import ORDER_RESPONSE_SCHEMA
from ..config import Settings
from ..contracts import ProviderFailure


class ProviderUnavailable(ProviderFailure):
    """Sanitized provider failure; response content and credentials are discarded.
    Metadata from a decoded body is kept on ``metadata`` (see ProviderFailure)."""


class AmbiguousJSON(ValueError):
    """The reply held more than one JSON object; none is chosen."""


class NoContent(ValueError):
    """The reply held neither message content nor tool-call arguments."""


# OpenRouter structured outputs: strict JSON Schema for the order reply.
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "commander_orders",
        "strict": True,
        "schema": ORDER_RESPONSE_SCHEMA,
    },
}


def response_metadata(body):
    """Why: telemetry must survive a response whose content fails to parse.
    What: extracts model, usage, response_id and finish_reason from a decoded
    body; never message content. Malformed fields become None or {}.
    Test: `test_truncated_reasoning_response_keeps_paid_telemetry`.
    """
    if not isinstance(body, dict):
        return {}
    choices = body.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else None
    usage = body.get("usage")
    return {
        # Returned model only; None when the provider omits it.
        "model": body.get("model"),
        "usage": usage if isinstance(usage, dict) else {},
        "response_id": body.get("id"),
        "finish_reason": first.get("finish_reason") if isinstance(first, dict) else None,
    }


def reasoning_field(effort):
    """Why: the effort request shape is provider-specific; keep it in one place.
    What: returns the request-body fragment for ``effort``; empty for no effort.
    The shape is OpenRouter's unified ``reasoning`` parameter
    (``{"reasoning": {"effort": "high"}}``). Confirmed live on 2026-11-06:
    openai/gpt-6-astra reported 3,211 reasoning tokens and an
    anthropic/claude-sonnet-5.5 probe reported 47 with this field set.
    Test: `test_openrouter_request_carries_configured_effort_and_limits`.
    """
    return {"reasoning": {"effort": effort}} if effort else {}


def single_json_object(text):
    """Why: some models ignore the requested response format and wrap the order
    JSON in prose or a Markdown fence; the orders are still usable.
    What: returns the one JSON object in ``text``: the whole text, or the only
    top-level object found by scanning (this covers fenced and embedded forms).
    Nothing is repaired. Raises JSONDecodeError when no object decodes,
    AmbiguousJSON for two or more, and ValueError when the whole text is valid
    JSON but not an object. Engine validation still runs on the result.
    Test: `test_order_json_after_prose_parses_to_model_decision`,
    `test_fenced_order_json_parses_to_model_decision`,
    `test_two_json_objects_are_ambiguous_and_fall_back`.
    """
    try:
        whole = json.loads(text)
    except json.JSONDecodeError as error:
        found = embedded_objects(text)
        if not found:
            raise error from None
        if len(found) > 1:
            raise AmbiguousJSON("More than one JSON object") from None
        return found[0]
    if not isinstance(whole, dict):
        raise ValueError("Model response is not an object")
    return whole


def embedded_objects(text):
    """Returns every top-level JSON object in ``text``; nested ones are skipped."""
    decoder = json.JSONDecoder()
    found = []
    index = text.find("{")
    while index != -1:
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            index = text.find("{", index + 1)
            continue
        if isinstance(value, dict):
            found.append(value)
        index = text.find("{", end)
    return found


def reply_text(body):
    """Why: a reply may arrive as message content or as tool-call arguments.
    What: returns the content string, else the arguments of the single tool call.
    Raises NoContent when neither is present, AmbiguousJSON for several calls.
    Test: `test_tool_call_arguments_parse_to_model_decision`.
    """
    message = body["choices"][0]["message"]
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    calls = message.get("tool_calls") or []
    if len(calls) > 1:
        raise AmbiguousJSON("More than one tool call")
    arguments = calls[0].get("function", {}).get("arguments") if calls else None
    if isinstance(arguments, str):
        return arguments
    raise NoContent("Reply has no content")


def failure_reason(exc):
    """Safe reason for a failed request: ``HTTP <code>`` or the exception type.
    A connect timeout arrives as URLError wrapping TimeoutError; report the timeout."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, TimeoutError):
        return "TimeoutError"
    return type(exc).__name__


class OpenRouterProvider:
    def __init__(self, settings: Settings, *, opener=urllib.request.urlopen):
        self._settings = settings
        self._open = opener

    @property
    def available(self):
        return bool(self._settings.api_key)

    @property
    def model(self):
        return self._settings.model

    @property
    def effort(self):
        return self._settings.effort or None

    def request(self, instruction, payload):
        if not self.available:
            raise ProviderUnavailable("No provider credential configured")
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": json.dumps(payload)},
                    ],
                    "temperature": 0.3,
                    "max_tokens": self._settings.request_max_tokens,
                    "response_format": RESPONSE_FORMAT,
                    **reasoning_field(self._settings.effort),
                }
            ).encode(),
            headers={
                "Authorization": "Bearer " + self._settings.api_key,
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Battle local POC",
            },
        )
        metadata = {}
        try:
            with self._open(request, timeout=self._settings.request_timeout) as response:
                body = json.loads(response.read(1000000))
            # Captured before parsing content: a truncated or null reply was paid for.
            metadata = response_metadata(body)
            return single_json_object(reply_text(body)), metadata
        except Exception as exc:
            raise ProviderUnavailable(failure_reason(exc), metadata) from None


class DisabledProvider:
    """Explicit no-network dependency for headless runs."""

    available = False
    model = ""
    effort = None

    def request(self, instruction, payload):
        raise ProviderUnavailable("Provider disabled")
