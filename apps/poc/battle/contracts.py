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


class UnknownScenario(ValueError):
    """The requested scenario id, or a saved game's label, is not in the catalog."""


class ProviderFailure(RuntimeError):
    """Why: a decoded but unusable response was still paid for; its telemetry
    must reach the decision record.
    What: ``str()`` is a safe reason (HTTP code or type name). ``metadata`` holds
    only response metadata (model, usage, response_id, finish_reason, and an
    in-body provider error's numeric error_code), never
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
    # side None: the snapshot's player side (Union before poc-9).
    def view(self, state: Document, side: str | None = None) -> Document: ...
    def god_view(self, state: Document) -> Document: ...
    def observation(self, state: Document, side: str) -> Document: ...
    def validate_orders(
        self, state: Document, side: str, orders: list[Document]
    ) -> list[Document]: ...
    # The side the interactive player commands in this snapshot.
    def player_side(self, state: Document) -> str: ...
    # The one side the computer commands: every side except the player's.
    def computer_side(self, state: Document) -> str: ...
    # "defender" or "attacker" for ``side`` in this snapshot.
    def role(self, state: Document, side: str) -> str: ...


class ScenarioCatalog(Protocol):
    """Scenario entries by id; ``None`` selects the catalog's default scenario.

    ``resolve`` and ``for_state`` return the entry (``scenario_entry.ScenarioEntry``)
    for an id or a saved snapshot; both raise ``UnknownScenario`` when absent.
    """

    default_id: str
    def ids(self) -> tuple[str, ...]: ...
    def resolve(self, scenario_id: str | None = None) -> Any: ...
    def for_state(self, state: Document) -> Any: ...
    def create(self, scenario_id: str | None = None) -> Document: ...
    def map(self, scenario_id: str | None = None) -> Document: ...


class DecisionProvider(Protocol):
    """Receives authorized observations only; never receives the world snapshot."""

    @property
    def available(self) -> bool: ...
    @property
    def model(self) -> str: ...
    # Optional: requested reasoning effort, or None. Test doubles may omit it.
    @property
    def effort(self) -> str | None: ...
    # Optional: id of the requested reply contract, or None. Test doubles may omit it.
    @property
    def response_format(self) -> str | None: ...
    # Metadata may carry reply_format: "json", "extracted" or "tool_call".
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
    @property
    def response_format(self) -> str | None: ...
    def decide(
        self, state: Document, side: str, mode: str = "openrouter",
        policy: str | None = None,
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
