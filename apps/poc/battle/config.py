"""Process configuration, read once at the composition root. Never sent to clients."""

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping
import os

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "openai/gpt-4.1-mini"
DEFAULT_MAX_TOKENS = 650
DEFAULT_TIMEOUT = 18.0
# Limits used when a reasoning effort is set and no limit was given explicitly.
# Live runs on 2026-11-06: openai/gpt-6-astra spent 3,211 reasoning tokens on one
# decision at high effort, and its slowest call took 19.2 s, past the 18 s
# default. 4000 tokens leaves room for reasoning plus a 3-order reply; 90 s is
# about 4.7 times the slowest observed call.
EFFORT_MAX_TOKENS = 4000
EFFORT_TIMEOUT = 90.0
# Reasoning effort levels accepted by the CLI; "" sends no reasoning field.
EFFORTS = ("", "low", "medium", "high")


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = DEFAULT_MODEL
    effort: str = ""
    # None means "not given"; request_max_tokens/request_timeout pick the default.
    max_tokens: int | None = None
    timeout: float | None = None

    def __post_init__(self):
        if self.effort not in EFFORTS:
            raise ValueError(f"Unsupported effort {self.effort!r}; use one of {EFFORTS[1:]}")
        if any(v is not None and v <= 0 for v in (self.max_tokens, self.timeout)):
            raise ValueError("max_tokens and timeout must be positive")

    @property
    def request_max_tokens(self) -> int:
        """Why: a reasoning model spends tokens before it answers, so 650 truncates.
        What: the explicit limit if given, else EFFORT_MAX_TOKENS when an effort is
        set, else DEFAULT_MAX_TOKENS.
        Test: `test_effort_raises_default_limits_unless_explicit`.
        """
        if self.max_tokens is not None:
            return self.max_tokens
        return EFFORT_MAX_TOKENS if self.effort else DEFAULT_MAX_TOKENS

    @property
    def request_timeout(self) -> float:
        """The explicit timeout, else EFFORT_TIMEOUT with an effort, else DEFAULT_TIMEOUT."""
        if self.timeout is not None:
            return self.timeout
        return EFFORT_TIMEOUT if self.effort else DEFAULT_TIMEOUT

    @classmethod
    def load(
        cls, path: Path | None = ROOT / ".env.local", environ: Mapping[str, str] | None = None
    ):
        """Settings from ``environ`` (default ``os.environ``), then the dotenv
        file at ``path``. ``path`` None reads no file: the paid batch takes its
        key from the injected environment only (D37, docs/research/78).
        Test: `test_a_key_only_in_env_local_is_refused`."""
        environment = os.environ if environ is None else environ
        values = {}
        if path is not None and path.exists():  # D37: None reads no .env.local.
            for line in path.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")

        def read(name):
            return environment.get(name, values.get(name, ""))

        def limit(name, kind):
            # Unset stays None so an effort can choose its own default.
            value = read(name)
            return kind(value) if value else None

        return cls(
            api_key=read("OPENROUTER_API_KEY"),
            model=read("OPENROUTER_MODEL") or DEFAULT_MODEL,
            effort=read("OPENROUTER_EFFORT"),
            max_tokens=limit("OPENROUTER_MAX_TOKENS", int),
            timeout=limit("OPENROUTER_TIMEOUT", float),
        )
