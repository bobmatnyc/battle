"""Bounded commander/staff decisions. Provider outputs are validated by rules."""

import re
import time
from copy import deepcopy
from ..contracts import DecisionProvider, ProviderFailure, ScenarioCatalog, Simulation
from ..command_policy import (
    DEFAULT_SCENARIO, GATE_POLICIES, scripted_actions, system_prompt,
)

# Reasons a ProviderFailure may carry into telemetry: an HTTP status, or one of
# the exception names the provider adapter reports. Anything else is replaced
# by the exception type, so free text from a provider never reaches a record.
HTTP_REASON = re.compile(r"HTTP \d{3}")
KNOWN_REASONS = frozenset(
    {
        # Transport.
        "TimeoutError",
        "URLError",
        "OSError",
        "ConnectionError",
        "ConnectionResetError",
        "ConnectionRefusedError",
        "RemoteDisconnected",
        "IncompleteRead",
        "SSLError",
        # Body and reply decoding.
        "JSONDecodeError",
        "UnicodeDecodeError",
        "AmbiguousJSON",
        "NoContent",
        "ReplyTooLarge",
        "ReplyTruncated",
        "ProviderError",
        "KeyError",
        "IndexError",
        "TypeError",
        "ValueError",
        "AttributeError",
    }
)


def failure_kind(exc):
    """Why: a fallback must say why the provider failed (HTTP 429, TimeoutError,
    JSONDecodeError) without leaking response content or credentials.
    What: a ProviderFailure's own reason when it is ``HTTP <3 digits>`` or a
    name in KNOWN_REASONS; otherwise, and for every other exception, the
    exception type name only.
    Test: `test_unsafe_provider_failure_text_keeps_type_only`,
    `test_unknown_reason_name_is_not_recorded`,
    `test_http_429_records_http_code_without_body`.
    """
    if isinstance(exc, ProviderFailure):
        reason = str(exc)
        if HTTP_REASON.fullmatch(reason) or reason in KNOWN_REASONS:
            return reason
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
        # json, extracted or tool_call; null when a provider does not report it.
        reply_format=metadata.get("reply_format"),
    )
    # Only an in-body provider error adds this key, so other records keep their shape.
    if "error_code" in metadata:
        telemetry["provider_error_code"] = metadata["error_code"]


class CommanderService:
    def __init__(
        self,
        simulation: Simulation,
        provider: DecisionProvider,
        *,
        scenarios: ScenarioCatalog | None = None,
        timer=time.perf_counter,
    ):
        self.simulation = simulation
        self.provider = provider
        # Source of each battle's missions and prompt version; bootstrap injects it.
        self.scenarios = scenarios
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

    @property
    def response_format(self):
        # Optional on providers; test doubles may omit it.
        return getattr(self.provider, "response_format", None)

    def scenario(self, state):
        """Why: prompts must use the battle's own scenario missions.
        What: the injected catalog's entry for ``state``. Without a catalog,
        Little Round Top serves only its own snapshots; any other scenario
        raises ValueError rather than receiving another battle's mission.
        Only the provider path calls this.
        Test: `test_commander_without_catalog_refuses_other_scenarios`.
        """
        if self.scenarios is not None:
            return self.scenarios.for_state(state)
        if not DEFAULT_SCENARIO.owns(state):
            raise ValueError(
                f"No scenario catalog injected for {state.get('scenario')!r}."
            )
        return DEFAULT_SCENARIO

    def display_scenario(self, state):
        """Why: scripted text reaches no model and changes no state, so an
        unmapped snapshot label must not break it, as it never did before
        scenarios became entries.
        What: ``scenario(state)`` when the label is known, else the catalog
        default (Little Round Top without a catalog).
        Test: `test_scripted_paths_and_map_survive_an_unmapped_label`.
        """
        try:
            return self.scenario(state)
        except ValueError:  # UnknownScenario is a ValueError.
            if self.scenarios is not None:
                return self.scenarios.resolve()
            return DEFAULT_SCENARIO

    def decide(self, state, side, mode="openrouter", policy=None):
        """Why: a model may command one side; every outcome must be auditable.
        What: returns a decision record for ``side``. In ``openrouter`` mode it
        asks the provider with that side's prompt and authorized observation,
        validates the proposal, and on any failure falls back to scripted orders
        with ``fallback`` set, the reason, and the rejected proposal kept.
        Response metadata (model, usage, response_id, finish_reason) is kept
        whenever the provider decoded a body, including on fallback;
        ``reply_format`` is the provider's (json, extracted, tool_call), or
        ``none`` when the provider failed. In any other mode the scripted
        control ``policy`` decides (None: ``scripted-fallback-v1``); a
        ``scripted-gate-defender-v1`` or ``scripted-gate-attacker-v1`` decision
        also carries the ``standing``
        instructions it issues and its ``policy``. A model's fallback stays
        the plain fallback control.
        Test: `test_model_french_run_gives_the_computer_allies_the_gate_defender`,
        `test_computer_gate_defender_orders_close_gate_on_a_delivered_breach`, `test_invalid_proposal_falls_back_flagged_with_rejected_orders`,
        `test_provider_timeout_falls_back_without_partial_state`,
        `test_truncated_reasoning_response_keeps_paid_telemetry`,
        `test_reply_format_records_json_extracted_and_tool_call`.
        """
        observation = self.simulation.observation(state, side)
        observation.pop("dispatches", None)
        if mode != "openrouter":
            return self._scripted(state, side, observation, policy)
        scenario = self.scenario(state)
        telemetry = {
            "requested_model": self.provider.model,
            "effort": self.effort,
            "prompt_version": scenario.prompt_version,
        }
        started = self.timer()
        try:
            result, metadata = self.provider.request(
                system_prompt(side, scenario),
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
            telemetry["reply_format"] = "none"  # No order object was parsed.
            return self._fallback(
                state, side, observation, telemetry, "provider_error", failure_kind(exc)
            )
        telemetry["latency_ms"] = self._elapsed(started)
        record_response(telemetry, metadata)
        if not isinstance(result, dict):
            telemetry["reply_format"] = "none"
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
            "voice_profile": self.display_scenario(state).voice_profile,
            "validation": {"valid": True, "error": None},
            "rejected_proposal": None,
            "fallback": False,
            "fallback_reason": None,
        }

    def _elapsed(self, started):
        return round((self.timer() - started) * 1000, 1)

    def _scripted(self, state, side, observation, policy=None):
        # The scripted control, chosen explicitly; not a fallback.
        standing, orders = scripted_actions(
            policy, observation, self.simulation.role(state, side)
        )
        record = {
            "source": "scripted",
            "side": side,
            "orders": self.simulation.validate_orders(state, side, orders),
            "text": "General, we shall proceed according to our standing orders.",
            "observation": observation,
            "turn": state["turn"],
            "fallback": False,
            "fallback_reason": None,
            "model": None,
            "voice_profile": self.display_scenario(state).voice_profile,
        }
        if policy in GATE_POLICIES.values():
            # Only the gate controls add fields, so other records keep their shape;
            # replay issues the stored instructions without re-running the policy.
            record.update(policy=policy, standing=standing)
        return record

    def _fallback(self, state, side, observation, telemetry, stage, reason):
        record = {
            "model": None,
            "usage": {},
            "response_id": None,
            "finish_reason": None,
            "reply_format": "none",
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
        """Why: the player's staff adviser answers from authorized reports.
        What: in ``openrouter`` mode asks the provider with the battle's own
        scenario prompt (an unmapped label raises, as in ``decide``); a
        provider failure, or scripted mode, gives the scripted summary, whose
        charge comes from ``display_scenario`` and so never fails on the label.
        Test: `test_scripted_paths_and_map_survive_an_unmapped_label`.
        """
        side = self.simulation.player_side(state)
        observation = self.simulation.observation(state, side)
        error = None
        if mode == "openrouter":
            scenario = self.scenario(state)
            try:
                result, metadata = self.provider.request(
                    system_prompt(side, scenario)
                    + f" You are the {scenario.sides[side].name} player's staff adviser. Answer their question. Propose orders only when requested. Orders require player approval.",
                    {"request": text, "observation": deepcopy(observation)},
                )
                return {
                    **metadata,
                    "text": str(result.get("text", "No dispatch."))[:3000],
                    "orders": self.simulation.validate_orders(
                        state, side, result.get("orders", [])
                    ),
                    "source": "openrouter",
                    "voice_profile": self.display_scenario(state).voice_profile,
                }
            except Exception as exc:
                error = failure_kind(exc)
        spec = self.display_scenario(state).sides.get(side)
        charge = f"Our charge is to {spec.charge}. " if spec else ""
        answer = (
            f"General, our command comprises {len(observation['units'])} detachments, "
            f"with {len(observation['contacts'])} enemy sightings reported to headquarters. "
            f"{charge}Send your instructions by runner; "
            "the latest reports may already be out of date."
        )
        return {
            "text": answer,
            "orders": [],
            "source": "scripted",
            "fallback_reason": error,
            "voice_profile": self.display_scenario(state).voice_profile,
        }
