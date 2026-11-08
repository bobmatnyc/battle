"""The paid model batch: its fixed plan, its key and the key's limit (D37, docs/research/78).

Why: the spend cap in ``battle.spend`` is the batch's own bound. D37 adds a
second, separate bound (the OpenRouter key's credit limit, equal to the cap),
takes the key only from the environment the batch was started with, and fixes
the model, plan and cap the owner approved, so none of them comes from a file
or a flag by accident.
What: ``PAID_PLANS`` (``d37-option-a``), ``plan_settings`` and
``environment_settings`` (the key from the given environment only, never
``.env.local``), ``key_limit_check`` (a pure check of the key-info ``data``
against the cap) and ``check_key`` (fetch through an injectable opener, then
check; every failure raises ``PaidRunRefused``). Nothing here prints or
records a key.
Test: `tests/test_d37_guards.py`.
"""

import math
import json
from dataclasses import dataclass, replace
from decimal import Decimal

from .adapters.openrouter import KEY_INFO_URL, KeyInfoError, fetch_key_info
from .config import Settings

KEY_ENV = "OPENROUTER_API_KEY"
# A stand-in the dry run hands its fake opener; it is not a credential.
DRY_RUN_KEY = "dry-run-no-key"


class PaidRunRefused(ValueError):
    """The paid batch may not start; the message never holds a key."""


@dataclass(frozen=True)
class PaidPlan:
    """A paid batch fixed by an owner ruling: model, request limits, cap and
    ``items`` (plan item, games) in play order."""

    name: str
    ruling: str
    model: str
    effort: str
    max_tokens: int
    timeout: float
    cap_usd: float
    items: tuple

    @property
    def games(self):
        return sum(n for _, n in self.items)

    def plan(self):
        """The plan as ``run_batch`` items, ``ENTRY[/VARIANT]:N``."""
        return [f"{item}:{n}" for item, n in self.items]


# D37 (Bob): option A of doc 69 section 5, cheap entries first (doc 69 section 5,
# "Controls that keep the cap real"); effort high, 4,000 output tokens and 90 s
# are the doc 69 section 2 request limits the $10.65 planning figure used.
D37_OPTION_A = PaidPlan(
    name="d37-option-a",
    ruling="D37 option A: Sonnet 5.5, 12 games, $14 cap, on an OpenRouter key limited to $14",
    model="anthropic/claude-sonnet-5.5", effort="high", max_tokens=4000, timeout=90.0, cap_usd=14.0,
    items=(("little-round-top", 1), ("hougoumont-north-gate", 1), ("concord-north-bridge", 3),
           ("pegasus-bridge", 3), ("gergovia-recall", 2), ("hill-223-patrol", 2)),
)
PAID_PLANS = {D37_OPTION_A.name: D37_OPTION_A}


def environment_key(environ):
    """The key in ``environ[KEY_ENV]``, stripped; missing or empty refuses.
    Test: `test_missing_empty_or_rejected_key_refuses_to_start`."""
    key = (environ.get(KEY_ENV) or "").strip()
    if not key:
        raise PaidRunRefused(f"{KEY_ENV} is missing or empty in the batch environment; "
                             "a paid batch never reads .env.local")
    return key


def plan_settings(plan, environ=None):
    """The one ``Settings`` of ``plan``: its model and limits, and the key from
    ``environ`` (None: no key, for the dry run). No other variable is read."""
    key = "" if environ is None else environment_key(environ)
    return Settings(api_key=key, model=plan.model, effort=plan.effort, max_tokens=plan.max_tokens,
                    timeout=plan.timeout)


def environment_settings(environ, **overrides):
    """``Settings.load`` from ``environ`` alone (no dotenv file) with the
    non-None ``overrides`` applied once; a missing or empty key refuses.
    Test: `test_a_key_only_in_env_local_is_refused`,
    `test_reserve_and_pins_use_the_environment_settings`."""
    loaded = Settings.load(None, environ)
    loaded = replace(loaded, api_key=environment_key(environ))
    return replace(loaded, **{k: v for k, v in overrides.items() if v is not None})


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def _usd(value):
    return Decimal(repr(float(value)))


def key_limit_check(info, cap_usd):
    """Why: the key's own credit limit is a backstop separate from the cap
    (D37); a key without one, or with more than the cap, is no backstop.
    What: the check record of the key-info ``data`` object ``info``: ``ok``,
    the reasons it fails, and ``limit``, ``limit_remaining``, ``limit_reset``,
    ``is_free_tier`` and ``usage`` as read (never ``label``, which can show
    part of the key). ``ok`` needs ``limit`` set and <= ``cap_usd``,
    ``limit_remaining`` >= ``cap_usd``, ``limit_reset`` None (a limit that
    resets is refused), and ``is_free_tier`` not true; a
    missing or non-numeric amount fails. Amounts compare as exact decimals.
    Test: `test_key_limit_check_accepts_only_a_key_limited_to_the_cap`.
    """
    info = info if isinstance(info, dict) else {}
    limit, remaining = _amount(info.get("limit")), _amount(info.get("limit_remaining"))
    free = info.get("is_free_tier")
    reset = info.get("limit_reset")
    reasons = []
    if limit is None:
        reasons.append("the key has no credit limit (limit is null or not a number)")
    elif _usd(limit) > _usd(cap_usd):
        reasons.append(f"the key's limit ${limit} is above the ${cap_usd} cap")
    if remaining is None:
        reasons.append("limit_remaining is null or not a number")
    elif _usd(remaining) < _usd(cap_usd):
        reasons.append(f"the key's limit_remaining ${remaining} is below the ${cap_usd} cap")
    if reset is not None:  # D37 review C: a limit that resets re-arms the key mid-batch.
        reasons.append(f"the key's limit resets ({reset if reset in ('daily', 'weekly', 'monthly') else 'unrecognised'}); "
                       "use a key whose limit never resets")
    if free is True:
        reasons.append("the key is on the free tier")
    elif "is_free_tier" in info and not isinstance(free, bool):
        reasons.append("is_free_tier is not a boolean")
    return {
        "ok": not reasons, "reasons": reasons, "cap_usd": cap_usd, "limit": limit, "limit_remaining": remaining,
        "limit_reset": reset if reset in (None, "daily", "weekly", "monthly") else "unrecognised",
        "is_free_tier": free if isinstance(free, bool) else None, "usage": _amount(info.get("usage")),
    }


def check_key(api_key, cap_usd, *, opener, source="openrouter"):
    """Why: the batch must not start on a key that is rejected or unlimited.
    What: ``fetch_key_info`` through ``opener`` then ``key_limit_check``;
    returns the record (with ``endpoint`` and ``opener`` = ``source``) when
    it passes. A failed call (network, HTTP, decode; 401 or 403 is a rejected
    key) or a failed check raises ``PaidRunRefused``.
    Test: `test_main_refuses_to_start_when_the_key_check_fails_and_records_a_passing_check_without_the_key`.
    """
    try:
        info = fetch_key_info(api_key, opener=opener)
    except KeyInfoError as exc:
        why = "the key was rejected" if exc.rejected else "the key-info call failed"
        raise PaidRunRefused(f"{why} ({exc}) at {KEY_INFO_URL}; nothing was spent") from None
    record = {**key_limit_check(info, cap_usd), "endpoint": KEY_INFO_URL, "opener": source}
    if not record["ok"]:
        raise PaidRunRefused("key-limit check failed: " + "; ".join(record["reasons"]))
    return record


class _FakeResponse:
    def __init__(self, body):
        self._body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, limit=-1):
        return self._body


def fake_key_opener(cap_usd):
    """An opener that answers the key-info call as a fresh key limited to
    ``cap_usd`` would, with no network; the dry run uses it."""
    def opener(request, timeout):
        return _FakeResponse({"data": {"limit": cap_usd, "limit_remaining": cap_usd, "limit_reset": None,
                                       "is_free_tier": False, "usage": 0}})
    return opener
