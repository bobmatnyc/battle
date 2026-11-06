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


class ReplyTooLarge(ValueError):
    """The reply text exceeds MAX_REPLY_CHARS; it is not scanned."""


class ReplyTruncated(ValueError):
    """The provider stopped at its token limit (``finish_reason`` ``length``)."""


# OpenRouter structured outputs: strict JSON Schema for the order reply.
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "commander_orders",
        "strict": True,
        "schema": ORDER_RESPONSE_SCHEMA,
    },
}

# Recorded in run metadata so runs with different reply contracts stay distinct.
RESPONSE_FORMAT_ID = "json_schema:commander_orders"


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


# Longest reply text the extractor will scan. A full order reply is a few KB;
# the cap bounds the work a hostile or runaway reply can cause.
MAX_REPLY_CHARS = 64 * 1024

# Reply formats recorded in decision telemetry as ``reply_format``.
REPLY_JSON = "json"
REPLY_EXTRACTED = "extracted"
REPLY_TOOL_CALL = "tool_call"


def parse_reply(text):
    """Why: some models ignore the requested response format and wrap the order
    JSON in prose or a Markdown fence; the orders are still usable, and
    telemetry must say which form arrived.
    What: returns ``(object, format)``. ``format`` is ``json`` when the whole
    text is one JSON object, else ``extracted`` for the single top-level object
    ``top_level_object`` finds. Nothing is repaired; engine validation still
    runs. Raises ReplyTooLarge above MAX_REPLY_CHARS, ValueError when the whole
    text is valid JSON but not an object, else what ``top_level_object`` raises.
    Test: `test_order_json_after_prose_parses_to_model_decision`,
    `test_megabyte_degenerate_reply_fails_fast`,
    `test_reply_format_records_json_extracted_and_tool_call`.
    """
    if len(text) > MAX_REPLY_CHARS:
        raise ReplyTooLarge("Reply exceeds the extraction limit")
    try:
        whole = json.loads(text)
    except json.JSONDecodeError:
        return top_level_object(text), REPLY_EXTRACTED
    if not isinstance(whole, dict):
        raise ValueError("Model response is not an object")
    return whole, REPLY_JSON


def single_json_object(text):
    """Returns the one JSON object in ``text``; see ``parse_reply``."""
    return parse_reply(text)[0]


def top_level_object(text):
    """Why: an object nested in an array, or in an outer structure that never
    closes or fails to decode, is a fragment of something else. Taking it would
    accept orders from a truncated or rejected wrapper.
    What: one linear pass. Outside any structure, text is prose and its quotes
    are ignored. A ``{`` or ``[`` opens a top-level region; brackets are then
    counted, skipping JSON strings, until the region closes. A closed ``{``
    region is decoded once. Returns the single decoded object. Raises
    JSONDecodeError when there is none, and AmbiguousJSON when the text holds
    any other candidate beside it: a second object, a ``{`` region that fails
    to decode or never closes, or an array that contains a ``{``. A region with
    no ``{`` (a footnote such as ``[1]``) is prose. Regions are disjoint, so
    the cost is linear in ``len(text)``.
    Test: `test_object_inside_truncated_wrapper_falls_back`,
    `test_orders_array_in_prose_falls_back`,
    `test_failed_region_before_object_is_ambiguous`.
    """
    found = []
    failed = 0
    depth = 0
    start = 0
    holds_object = False
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif depth == 0:
            if char in "{[":
                depth, start, holds_object = 1, index, char == "{"
        elif char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
            holds_object = holds_object or char == "{"
        elif char in "}]":
            depth -= 1
            if depth == 0:
                failed += close_region(text, start, index, holds_object, found)
    if depth > 0 and holds_object:
        failed += 1  # An outer structure opened and never closed: truncated.
    if not found:
        raise json.JSONDecodeError("No top-level JSON object", text, 0)
    if len(found) + failed > 1:
        raise AmbiguousJSON("More than one JSON candidate")
    return found[0]


def close_region(text, start, end, holds_object, found):
    """Decodes one closed top-level region into ``found``.
    Returns 1 when the region is a rival candidate that did not decode to an
    object, else 0. An array is never the reply; one holding a ``{`` is a rival."""
    if text[start] == "[":
        return 1 if holds_object else 0
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return 1
    if not isinstance(value, dict):
        return 1
    found.append(value)
    return 0


def reply_text(body):
    """Why: a reply may arrive as message content or as tool-call arguments.
    What: returns ``(text, from_tool_call)``: the content string, else the
    arguments of the single tool call. Raises NoContent when neither is
    present, AmbiguousJSON for several calls.
    Test: `test_tool_call_arguments_parse_to_model_decision`.
    """
    message = body["choices"][0]["message"]
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content, False
    calls = message.get("tool_calls") or []
    if len(calls) > 1:
        raise AmbiguousJSON("More than one tool call")
    arguments = calls[0].get("function", {}).get("arguments") if calls else None
    if isinstance(arguments, str):
        return arguments, True
    raise NoContent("Reply has no content")


def decoded_reply(body, metadata):
    """Why: a reply cut off at the token limit may still hold a complete-looking
    object, and telemetry must record how the order object was found.
    What: returns ``(object, reply_format)`` from a decoded body; the format is
    ``tool_call`` for tool-call arguments, else ``parse_reply``'s format.
    Raises ReplyTruncated when ``finish_reason`` is ``length``, after the
    content parsed; a reply that also fails to parse keeps the parse reason.
    Test: `test_length_finish_with_complete_object_falls_back`.
    """
    text, from_tool_call = reply_text(body)
    result, reply_format = parse_reply(text)
    if metadata.get("finish_reason") == "length":
        raise ReplyTruncated("Reply stopped at the token limit")
    return result, REPLY_TOOL_CALL if from_tool_call else reply_format


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

    @property
    def response_format(self):
        return RESPONSE_FORMAT_ID

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
            result, reply_format = decoded_reply(body, metadata)
            return result, {**metadata, "reply_format": reply_format}
        except Exception as exc:
            raise ProviderUnavailable(failure_reason(exc), metadata) from None


class DisabledProvider:
    """Explicit no-network dependency for headless runs."""

    available = False
    model = ""
    effort = None
    response_format = None

    def request(self, instruction, payload):
        raise ProviderUnavailable("Provider disabled")
