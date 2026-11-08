"""Spend accounting for paid model runs (docs/research/69 §9).

Why: a cap checked between games lets one long game overrun it by the whole
game (up to $30 for an Astra Hill 223 game, doc 69 §4). Reserving one
worst-case call before every call bounds the overrun by one call.
What: ``decision_cost`` reads a decision's recorded ``usage.cost`` and fails
closed; ``worst_case_call`` prices the largest bill one request can produce;
``SpendGuard`` refuses a call unless the cap still covers the batch's spend
plus that reserve. Nothing here reads a credential or calls a provider.
Test: `test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap`,
`test_reserve_covers_the_full_request_body_the_adapter_sends`,
`test_missing_cost_fails_closed_and_stops_the_batch`.
"""

import math
from dataclasses import dataclass
from decimal import Decimal

# USD per million tokens, (input, output), doc 69 §3. Sonnet and Opus are the
# Anthropic list prices that OpenRouter carries at no markup; Astra's are
# derived from stored costs (its cache writes bill at the input rate).
PRICES = {
    "anthropic/claude-sonnet-5.5": (2.0, 10.0),
    "anthropic/claude-opus-5.5": (4.0, 20.0),
    "openai/gpt-6-astra": (12.5, 50.0),
}
# Authored, not measured: tokens a provider adds that are not in the request
# body, such as the chat template and the response_format schema restated as
# instructions. The body itself (including the 532-byte schema) is counted.
PROVIDER_OVERHEAD_TOKENS = 1024
RESERVE_BASIS = (
    "input tokens <= the UTF-8 bytes of the full serialized request body the adapter sends (model, both "
    "messages, temperature, max_tokens, the response_format JSON schema, reasoning; a token covers at least one "
    f"byte) plus {PROVIDER_OVERHEAD_TOKENS} provider-overhead tokens (authored), at the input price; output "
    "tokens = the request's max_tokens from the same Settings (reasoning counts inside it), at the output price; "
    "no cache discount"
)


class BudgetExhausted(RuntimeError):
    """The cap cannot cover one more worst-case call; raised before the call."""


class CostUnreadable(RuntimeError):
    """A paid decision has no readable ``usage.cost``; never counted as $0."""


def decision_cost(decision):
    """Why: the cap is only real if every paid call is counted.
    What: the decision's ``usage.cost`` in USD. A missing, non-numeric,
    negative or non-finite cost raises ``CostUnreadable``.
    Test: `test_missing_cost_fails_closed_and_stops_the_batch`.
    """
    usage = decision.get("usage") if isinstance(decision, dict) else None
    cost = usage.get("cost") if isinstance(usage, dict) else None
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        turn = decision.get("turn") if isinstance(decision, dict) else None
        raise CostUnreadable(f"cost unreadable for the player decision at turn {turn}")
    return float(cost)


@dataclass(frozen=True)
class Price:
    """USD per million input and output tokens, and the request's output limit."""

    input_per_mtok: float
    output_per_mtok: float
    max_output_tokens: int

    def __post_init__(self):
        rates = (self.input_per_mtok, self.output_per_mtok)
        # D37: a rate of 0 would make the reserve, and so the cap, ignore that side of the bill.
        if any(not math.isfinite(r) or r <= 0 for r in rates) or self.max_output_tokens < 1:
            raise ValueError("prices must be finite and above 0, and max_output_tokens 1 or more")


def _usd(amount):
    """``amount`` as an exact Decimal of its shortest float repr (13.99 is
    13.99, not 13.9900000000000002131628...)."""
    return Decimal(repr(float(amount)))


def _reserve(price, body_bytes):
    tokens_in = Decimal(body_bytes + PROVIDER_OVERHEAD_TOKENS)
    return (tokens_in * _usd(price.input_per_mtok)
            + Decimal(price.max_output_tokens) * _usd(price.output_per_mtok)) / Decimal(1_000_000)


def worst_case_call(price, body_bytes):
    """The most one request whose serialized body is ``body_bytes`` long can
    cost, per ``RESERVE_BASIS``."""
    return float(_reserve(price, body_bytes))


class SpendGuard:
    """Why: every provider call of a batch must fit under the batch's cap.
    What: ``check`` (before a call) raises ``BudgetExhausted`` when
    ``spent + worst_case_call > cap``; a call landing exactly on the cap is
    allowed. ``charge`` (after it) adds the call's recorded cost. The sums are
    exact decimals of each amount's float repr, so 14 - 13.99 - 0.01 is 0, not
    -2e-16. ``body_size(instruction, payload)`` is the byte length of the
    request body the provider will send; the composition edge supplies it from
    the adapter. One guard spans a whole batch.
    Test: `test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap`,
    `test_reserve_covers_the_full_request_body_the_adapter_sends`,
    `test_a_call_landing_exactly_on_the_cap_is_allowed_and_one_cent_over_is_refused`,
    `test_the_exact_cap_call_is_sent_and_the_cent_over_call_is_never_sent`.
    """

    def __init__(self, cap_usd, price, body_size, spent_usd=0.0):
        if not (math.isfinite(cap_usd) and cap_usd > 0):
            raise ValueError("the cap must be a positive amount")
        self.cap_usd, self.price, self.body_size = cap_usd, price, body_size
        # D37: exact decimal sums; float drift refused a call landing exactly on the cap.
        self._cap, self._spent = _usd(cap_usd), _usd(spent_usd)

    @property
    def spent_usd(self):
        return float(self._spent)

    def check(self, instruction, payload):
        reserve = _reserve(self.price, self.body_size(instruction, payload))
        if self._spent + reserve > self._cap:
            raise BudgetExhausted(
                f"cap ${self.cap_usd:.4f} - spent ${self.spent_usd:.4f} < reserve ${float(reserve):.4f} for the next call")

    def charge(self, cost):
        self._spent += _usd(cost)

    def at_cap(self):
        """True once the spend has reached the cap; no game starts then."""
        return self._spent >= self._cap
