"""Application-owned ports. Adapters depend on these contracts, not vice versa.

Battle snapshots/actions remain versioned JSON documents for exact old-save replay.
Repository save is a single atomic compare-and-swap of state and all audit records.
"""

from typing import Any, Callable, Protocol

Document = dict[str, Any]


class Conflict(ValueError):
    """The caller's battle identity or revision is no longer current."""


class AuditUnavailable(ValueError):
    """Full ground-truth audit is not yet available to the caller."""


class ProviderFailure(RuntimeError):
    """Why: a decoded but unusable response was still paid for; its telemetry
    must reach the decision record.
    What: ``str()`` is a safe reason (HTTP code or type name). ``metadata`` holds
    only response metadata (model, usage, response_id, finish_reason), never
    message content, prompt text or credentials; empty when nothing was decoded.
    Test: `test_truncated_reasoning_response_keeps_paid_telemetry`.
    """

    def __init__(self, reason: str, metadata: Document | None = None):
        super().__init__(reason)
        self.metadata: Document = dict(metadata or {})


class BattleRepository(Protocol):
    def latest(self) -> str | None: ...
    def create(self, state: Document) -> str: ...
    def load(self, game_id: str, revision: int | None = None) -> Document: ...
    def save(self, game_id: str, state: Document, expected: int) -> None: ...
    def history(self, game_id: str) -> list[Document]: ...
    def messages(self, game_id: str) -> list[Document]: ...
    def clock_event(
        self, game_id: str, command: str, speed: float | None = None
    ) -> None: ...


class Simulation(Protocol):
    """Pure, version-aware transitions and permission-limited projections."""

    def apply(self, state: Document, action: Document) -> Document: ...
    def view(self, state: Document, side: str = "union") -> Document: ...
    def god_view(self, state: Document) -> Document: ...
    def observation(self, state: Document, side: str) -> Document: ...
    def validate_orders(
        self, state: Document, side: str, orders: list[Document]
    ) -> list[Document]: ...


class ScenarioCatalog(Protocol):
    def create(self) -> Document: ...
    def map(self) -> Document: ...


class DecisionProvider(Protocol):
    """Receives authorized observations only; never receives the world snapshot."""

    @property
    def available(self) -> bool: ...
    @property
    def model(self) -> str: ...
    # Optional: requested reasoning effort, or None. Test doubles may omit it.
    @property
    def effort(self) -> str | None: ...
    def request(
        self, instruction: str, payload: Document
    ) -> tuple[Document, Document]: ...


class Commander(Protocol):
    @property
    def available(self) -> bool: ...
    @property
    def model(self) -> str: ...
    @property
    def effort(self) -> str | None: ...
    def decide(
        self, state: Document, side: str = "confederate", mode: str = "openrouter"
    ) -> Document: ...
    def chat(
        self, state: Document, text: str, mode: str = "openrouter"
    ) -> Document: ...


class Clock(Protocol):
    def status(self) -> Document: ...
    def control(self, command: str, speed: float | None = None) -> Document: ...
    def start_worker(self) -> None: ...
    def close(self) -> None: ...


class ClockFactory(Protocol):
    def __call__(
        self, step: Callable[[], bool], *, audit: Callable[[str, float | None], None]
    ) -> Clock: ...
