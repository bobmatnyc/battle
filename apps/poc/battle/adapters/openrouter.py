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


class ProviderError(ValueError):
    """The response body, or its first choice, carried an ``error`` object
    instead of a reply. OpenRouter can send this with HTTP 200."""


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


def first_choice(body):
    """The first choice of a decoded body when it is an object, else None."""
    choices = body.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else None
    return first if isinstance(first, dict) else None


def body_error(body):
    """The ``error`` object of the body or its first choice, else None."""
    for holder in (body, first_choice(body) or {}):
        error = holder.get("error")
        if error is not None:
            return error if isinstance(error, dict) else {}
    return None


def error_code(error):
    """An HTTP-shaped integer code from a provider error object, else None.
    The message and any string code are dropped: they may carry content."""
    code = error.get("code")
    if isinstance(code, int) and not isinstance(code, bool) and 100 <= code <= 599:
        return code
    return None


def response_metadata(body):
    """Why: telemetry must survive a response whose content fails to parse.
    What: extracts model, usage, response_id and finish_reason from a decoded
    body; never message content. Malformed fields become None or {}. A body
    carrying an ``error`` object adds ``error_code`` (see ``error_code``);
    other bodies have no such key.
    Test: `test_truncated_reasoning_response_keeps_paid_telemetry`,
    `test_in_body_provider_error_falls_back_as_provider_error`.
    """
    if not isinstance(body, dict):
        return {}
    first = first_choice(body)
    usage = body.get("usage")
    metadata = {
        # Returned model only; None when the provider omits it.
        "model": body.get("model"),
        "usage": usage if isinstance(usage, dict) else {},
        "response_id": body.get("id"),
        "finish_reason": first.get("finish_reason") if first else None,
    }
    error = body_error(body)
    if error is not None:
        metadata["error_code"] = error_code(error)
        limit = limit_refusal(metadata["error_code"], body)
        if limit is not None:  # D37: an in-body 402 stops a paid batch too.
            metadata["provider_limit"] = limit
    return metadata


# D37: the ``error.metadata.limit_source`` values OpenRouter's limits doc
# (openrouter.ai/docs/api/reference/limits, read 2026-11-08) names for credit
# and budget refusals. Any other value is recorded as None, never as text.
LIMIT_SOURCES = frozenset({
    "openrouter_key_limit", "openrouter_credits", "openrouter_in_flight_budget",
    "openrouter_guardrail_budget", "openrouter_workspace_budget",
})


def limit_refusal(status, body):
    """Why: a paid batch must stop, not fall back, when OpenRouter refuses for
    credit or a spend limit (D37, docs/research/78).
    What: ``{"status", "limit_source"}`` when ``status`` is 402 (insufficient
    credits or the key's limit), or 403 or 429 whose body names a credit or
    budget ``limit_source``; else None. ``limit_source`` is one of
    ``LIMIT_SOURCES`` or None; no message text is kept.
    Test: `test_a_provider_credit_refusal_stops_the_batch_and_keeps_the_partial_game`.
    """
    error = body_error(body) if isinstance(body, dict) else None
    details = error.get("metadata") if isinstance(error, dict) else None
    source = details.get("limit_source") if isinstance(details, dict) else None
    source = source if source in LIMIT_SOURCES else None
    if status == 402 or (status in (403, 429) and source is not None):
        return {"status": status, "limit_source": source}
    return None


def http_error_metadata(exc):
    """Metadata for an HTTP error response: ``provider_limit`` when its body
    is a credit or budget refusal (``limit_refusal``), else nothing. The body
    is read up to 64 KiB and never kept."""
    try:
        body = json.loads(exc.read(64 * 1024))
    except Exception:  # noqa: BLE001 - an unreadable body still has its status.
        body = None
    finally:
        exc.close()
    limit = limit_refusal(exc.code, body)
    return {"provider_limit": limit} if limit is not None else {}


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
    Raises ProviderError when the body or its first choice holds an ``error``
    object, before any content is read. Raises ReplyTruncated when
    ``finish_reason`` is ``length``, after the content parsed; a reply that
    also fails to parse keeps the parse reason.
    Test: `test_length_finish_with_complete_object_falls_back`,
    `test_in_body_provider_error_falls_back_as_provider_error`.
    """
    # A 200 body {"id", "error"} once hit body["choices"] and fell back as KeyError.
    if body_error(body) is not None:
        raise ProviderError("Response body carries a provider error")
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


def request_body(settings, instruction, payload):
    """Why: a spend reserve must size the exact request that is sent (doc 69 §9).
    What: the serialized chat-completions body ``OpenRouterProvider.request``
    sends for ``settings``; it carries no credential.
    Test: `test_reserve_covers_the_full_request_body_the_adapter_sends`.
    """
    return json.dumps(
        {
            "model": settings.model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(payload)},
            ],
            "temperature": 0.3,
            "max_tokens": settings.request_max_tokens,
            "response_format": RESPONSE_FORMAT,
            **reasoning_field(settings.effort),
        }
    ).encode()


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
            data=request_body(self._settings, instruction, payload),
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
            if isinstance(exc, urllib.error.HTTPError):  # D37: keep a credit refusal's status and source.
                metadata = {**metadata, **http_error_metadata(exc)}
            raise ProviderUnavailable(failure_reason(exc), metadata) from None


# D37: OpenRouter's key-info endpoint (limits doc, "Checking your limits").
KEY_INFO_URL = "https://openrouter.ai/api/v1/key"


class KeyInfoError(ValueError):
    """The key-info call failed; ``rejected`` is True for HTTP 401 or 403.
    The message is ``HTTP <code>`` or an exception name, never content."""

    def __init__(self, reason, rejected=False):
        super().__init__(reason)
        self.rejected = rejected


def fetch_key_info(api_key, *, opener=urllib.request.urlopen, timeout=15.0):
    """Why: a paid batch checks the key's own credit limit before any spend
    (D37 backstop, docs/research/78).
    What: GET ``KEY_INFO_URL`` with the key as a bearer token through
    ``opener`` and returns the response's ``data`` object. Any network, HTTP,
    decode or shape error raises ``KeyInfoError`` (fail closed); 401 and 403
    are ``rejected``. The key goes only in the request header.
    Test: `test_key_info_call_is_a_get_with_the_key_and_fails_closed`.
    """
    if not api_key:
        raise KeyInfoError("no key", rejected=True)
    request = urllib.request.Request(KEY_INFO_URL, headers={"Authorization": "Bearer " + api_key}, method="GET")
    try:
        with opener(request, timeout=timeout) as response:
            body = json.loads(response.read(1000000))
    except urllib.error.HTTPError as exc:
        exc.close()  # The body is not read: only the status is kept.
        raise KeyInfoError(f"HTTP {exc.code}", rejected=exc.code in (401, 403)) from None
    except Exception as exc:  # noqa: BLE001 - every failure refuses the batch.
        raise KeyInfoError(failure_reason(exc)) from None
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        raise KeyInfoError("no data object")
    return data


class DisabledProvider:
    """Explicit no-network dependency for headless runs."""

    available = False
    model = ""
    effort = None
    response_format = None

    def request(self, instruction, payload):
        raise ProviderUnavailable("Provider disabled")
