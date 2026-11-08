"""Spend accounting for paid model runs (docs/research/69 §9).

Why: a cap checked between games lets one long game overrun it by the whole
game (up to $30 for an Astra Hill 223 game, doc 69 §4). Reserving one
worst-case call before every call bounds the overrun by one call.
What: ``decision_cost`` reads a decision's recorded ``usage.cost`` and fails
closed; ``worst_case_call`` prices the largest bill one request can produce;
``SpendGuard`` refuses a call unless the cap still covers the batch's spend
plus that reserve. Nothing here reads a credential or calls a provider.
Test: `test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap`,
`test_worst_case_reserve_grows_with_the_request`,
`test_missing_cost_fails_closed_and_stops_the_batch`.
"""

import json
import math
from dataclasses import dataclass

# USD per million tokens, (input, output), doc 69 §3. Sonnet and Opus are the
# Anthropic list prices that OpenRouter carries at no markup; Astra's are
# derived from stored costs (its cache writes bill at the input rate).
PRICES = {
    "anthropic/claude-sonnet-5.5": (2.0, 10.0),
    "anthropic/claude-opus-5.5": (4.0, 20.0),
    "openai/gpt-6-astra": (12.5, 50.0),
}
# Tokens for message framing around the two messages; measured requests
# carry far fewer, so this only adds margin.
FRAMING_TOKENS = 64
RESERVE_BASIS = (
    "input tokens <= UTF-8 bytes of the system prompt plus the JSON user message (a token covers at least one "
    f"byte) plus {FRAMING_TOKENS} framing tokens, at the input price; output tokens = the request's max_tokens "
    "(reasoning counts inside it), at the output price; no cache discount"
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
        if any(not math.isfinite(r) or r < 0 for r in rates) or self.max_output_tokens < 1:
            raise ValueError("prices must be finite and 0 or more, and max_output_tokens 1 or more")


def worst_case_call(price, instruction, payload):
    """The most one request of ``instruction`` and ``payload`` can cost, per ``RESERVE_BASIS``."""
    size = len(instruction.encode()) + len(json.dumps(payload).encode())
    return ((size + FRAMING_TOKENS) * price.input_per_mtok
            + price.max_output_tokens * price.output_per_mtok) / 1_000_000


class SpendGuard:
    """Why: every provider call of a batch must fit under the batch's cap.
    What: ``check`` (before a call) raises ``BudgetExhausted`` when
    ``cap - spent - worst_case_call < 0``; ``charge`` (after it) adds the
    call's recorded cost. One guard spans a whole batch.
    Test: `test_budget_stops_mid_game_before_the_call_that_would_cross_the_cap`.
    """

    def __init__(self, cap_usd, price, spent_usd=0.0):
        if not (math.isfinite(cap_usd) and cap_usd > 0):
            raise ValueError("the cap must be a positive amount")
        self.cap_usd, self.price, self.spent_usd = cap_usd, price, spent_usd

    def check(self, instruction, payload):
        reserve = worst_case_call(self.price, instruction, payload)
        if self.cap_usd - self.spent_usd - reserve < 0:
            raise BudgetExhausted(
                f"cap ${self.cap_usd:.4f} - spent ${self.spent_usd:.4f} < reserve ${reserve:.4f} for the next call")

    def charge(self, cost):
        self.spent_usd += cost
