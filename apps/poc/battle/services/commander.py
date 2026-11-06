"""Bounded commander/staff decisions. Provider outputs are validated by rules."""

import re
import time
from copy import deepcopy
from ..contracts import DecisionProvider, ProviderFailure, Simulation
from ..command_policy import PROMPT_VERSION, fallback_orders, system_prompt
from ..presentation import VOICE_PROFILE

# Shapes a ProviderFailure reason may take: "HTTP 429" or an exception type name.
SAFE_REASON = re.compile(r"HTTP \d{3}|[A-Za-z_][A-Za-z0-9_]{0,63}")


def failure_kind(exc):
    """Why: a fallback must say why the provider failed (HTTP 429, TimeoutError,
    JSONDecodeError) without leaking response content or credentials.
    What: a ProviderFailure's own reason when it is an HTTP code or a type name;
    otherwise, and for every other exception, the exception type name only.
    Test: `test_unsafe_provider_failure_text_keeps_type_only`,
    `test_http_429_records_http_code_without_body`.
    """
    if isinstance(exc, ProviderFailure) and SAFE_REASON.fullmatch(str(exc)):
        return str(exc)
    return type(exc).__name__


def validation_error(exc):
    # Rule/validation messages are game text built from the proposal, never from
    # provider configuration, so a bounded message is safe to keep.
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def record_response(telemetry, metadata):
    """Copies provider response metadata into ``telemetry``; never content."""
    metadata = metadata if isinstance(metadata, dict) else {}
    telemetry.update(
        model=metadata.get("model"),
        usage=metadata.get("usage") or {},
        response_id=metadata.get("response_id"),
        finish_reason=metadata.get("finish_reason"),
    )


class CommanderService:
    def __init__(
        self,
        simulation: Simulation,
        provider: DecisionProvider,
        *,
        timer=time.perf_counter,
    ):
        self.simulation = simulation
        self.provider = provider
        # Latency is measured here, at the service edge; replay never calls it.
        self.timer = timer

    @property
    def available(self):
        return self.provider.available

    @property
    def model(self):
        return self.provider.model

    @property
    def effort(self):
        return getattr(self.provider, "effort", None)

    def decide(self, state, side="confederate", mode="openrouter"):
        """Why: a model may command one side; every outcome must be auditable.
        What: returns a decision record for ``side``. In ``openrouter`` mode it
        asks the provider with that side's prompt and authorized observation,
        validates the proposal, and on any failure falls back to scripted orders
        with ``fallback`` set, the reason, and the rejected proposal kept.
        Response metadata (model, usage, response_id, finish_reason) is kept
        whenever the provider decoded a body, including on fallback.
        Test: `test_invalid_proposal_falls_back_flagged_with_rejected_orders`,
        `test_provider_timeout_falls_back_without_partial_state`,
        `test_truncated_reasoning_response_keeps_paid_telemetry`.
        """
        observation = self.simulation.observation(state, side)
        observation.pop("dispatches", None)
        if mode != "openrouter":
            return self._scripted(state, side, observation)
        telemetry = {
            "requested_model": self.provider.model,
            "effort": self.effort,
            "prompt_version": PROMPT_VERSION,
        }
        started = self.timer()
        try:
            result, metadata = self.provider.request(
                system_prompt(side),
                {
                    "task": "Choose your next tactical orders.",
                    "observation": deepcopy(observation),
                },
            )
        except Exception as exc:
            telemetry["latency_ms"] = self._elapsed(started)
            # A decoded response that failed to parse was still paid for.
            if isinstance(exc, ProviderFailure):
                record_response(telemetry, exc.metadata)
            return self._fallback(
                state, side, observation, telemetry, "provider_error", failure_kind(exc)
            )
        telemetry["latency_ms"] = self._elapsed(started)
        record_response(telemetry, metadata)
        if not isinstance(result, dict):
            return self._fallback(
                state, side, observation, telemetry, "invalid_response", "TypeError"
            )
        proposed = deepcopy(result.get("orders"))
        telemetry["proposed_orders"] = deepcopy(proposed)
        try:
            orders = self.simulation.validate_orders(state, side, deepcopy(proposed))
        except Exception as exc:
            telemetry["validation"] = {"valid": False, "error": validation_error(exc)}
            telemetry["rejected_proposal"] = deepcopy(proposed)
            return self._fallback(
                state, side, observation, telemetry, "validation_failed", failure_kind(exc)
            )
        return {
            **telemetry,
            "source": "openrouter",
            "side": side,
            "orders": orders,
            "text": str(result.get("text", "Orders prepared."))[:1500],
            "observation": observation,
            "turn": state["turn"],
            "voice_profile": VOICE_PROFILE,
            "validation": {"valid": True, "error": None},
            "rejected_proposal": None,
            "fallback": False,
            "fallback_reason": None,
        }

    def _elapsed(self, started):
        return round((self.timer() - started) * 1000, 1)

    def _scripted(self, state, side, observation):
        # The scripted control, chosen explicitly; not a fallback.
        return {
            "source": "scripted",
            "side": side,
            "orders": self.simulation.validate_orders(
                state, side, fallback_orders(observation)
            ),
            "text": "General, we shall proceed according to our standing orders.",
            "observation": observation,
            "turn": state["turn"],
            "fallback": False,
            "fallback_reason": None,
            "model": None,
            "voice_profile": VOICE_PROFILE,
        }

    def _fallback(self, state, side, observation, telemetry, stage, reason):
        record = {
            "model": None,
            "usage": {},
            "response_id": None,
            "finish_reason": None,
            "proposed_orders": None,
            "validation": None,  # None: the provider produced nothing to validate.
            "rejected_proposal": None,
            **telemetry,
        }
        returned_model = record["model"]
        # Scripted labels overwrite telemetry: a fallback is never a model decision.
        record.update(self._scripted(state, side, observation))
        record.update(
            model=returned_model,
            fallback=True,
            fallback_stage=stage,
            fallback_reason=reason,
        )
        return record

    def chat(self, state, text, mode="openrouter"):
        observation = self.simulation.observation(state, "union")
        error = None
        if mode == "openrouter":
            try:
                result, metadata = self.provider.request(
                    system_prompt("union")
                    + " You are the Union player's staff adviser. Answer their question. Propose orders only when requested. Orders require player approval.",
                    {"request": text, "observation": deepcopy(observation)},
                )
                return {
                    **metadata,
                    "text": str(result.get("text", "No dispatch."))[:3000],
                    "orders": self.simulation.validate_orders(
                        state, "union", result.get("orders", [])
                    ),
                    "source": "openrouter",
                    "voice_profile": VOICE_PROFILE,
                }
            except Exception as exc:
                error = failure_kind(exc)
        answer = (
            f"General, our command comprises {len(observation['units'])} detachments, "
            f"with {len(observation['contacts'])} enemy sightings reported to headquarters. "
            "Our charge is to hold the marked summit until five o'clock. Send your instructions by runner; "
            "the latest reports may already be out of date."
        )
        return {
            "text": answer,
            "orders": [],
            "source": "scripted",
            "fallback_reason": error,
            "voice_profile": VOICE_PROFILE,
        }
