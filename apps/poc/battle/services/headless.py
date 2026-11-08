"""Full local simulation use case, sharing the same ports as interactive play."""

from ..command_policy import (
    NAMED_POLICIES, OPPONENT_POLICY, SCRIPTED_POLICIES, gate_policy_refusal,
    scripted_actions, scripted_policy,
)
from ..spend import decision_cost
from ..contracts import BattleRepository, Commander, ScenarioCatalog, Simulation
from .replay import ReplayService

PLAYER_MODES = ("scripted", "openrouter")


class ModelFallback(RuntimeError):
    """Why: a model game in which any player decision fell back to the
    scripted control is not a model result (doc 69 §8 gap 4), and a batch
    must not keep paying for it.
    What: raised by ``HeadlessRunner.run`` under ``abort_on_fallback`` before
    the fallback decision is committed. ``decision`` is that record, kept so
    the caller can read its stage, reason and any paid ``usage``.
    Test: `test_abort_on_fallback_raises_before_the_fallback_is_committed`.
    """

    def __init__(self, decision):
        super().__init__(
            f"player decision at turn {decision.get('turn')} fell back: "
            f"{decision.get('fallback_stage')} {decision.get('fallback_reason')}"
        )
        self.decision = decision


class HeadlessRunner:
    """Why: a model must be able to play one side end to end, with a scripted
    control on the other side, and the run must replay without a provider.
    What: ``player_side`` is driven by ``commander`` in ``player_mode``; the
    other side is the explicit scripted ``opponent``. Sides come from the
    scenario entry; ``player_side`` None is the entry's player side. A
    scripted run of that side keeps the direct-orders path, so Little Round
    Top's default run is unchanged.
    ``player_policy`` picks the scripted control of a scripted player side,
    on that direct-orders path or through decision records for another side
    (None: the entry's choice, ``scripted-gate-defender-v1`` for the defender
    and ``scripted-gate-attacker-v1`` for the attacker of a gated entry, else
    ``scripted-fallback-v1``); a gate control is refused for a side of another
    role or scenario. A run under a gate policy records it as
    ``player_policy`` in run metadata and its summary; other runs keep their
    metadata and output unchanged.
    ``opponent`` picks the computer side's control by the same rule (None:
    the entry's choice); its decisions carry a gate control's standing
    instructions, and run metadata records it as ``opponent``.
    ``scenario_id`` selects the catalog entry (None: the catalog default);
    an unknown id raises ``UnknownScenario`` before anything is stored.
    ``abort_on_fallback`` (default False, for model runs) raises
    ``ModelFallback`` at the first player decision that is not the model's
    own; the run stops there and that decision is not committed. It needs
    ``player_mode`` ``openrouter``. Off, every run plays and records as before.
    ``spend_guard`` (default None, model runs only) is charged each player
    decision's recorded cost (``CostUnreadable`` when it has none); its
    ``check`` runs before each call through the commander (``build_headless``).
    Test: `test_abort_on_fallback_raises_before_the_fallback_is_committed`,
    `test_model_player_run_records_side_decisions_and_replays`,
    `test_default_headless_run_keeps_baseline_path`,
    `test_duel_fixture_runs_headless_and_replays`,
    `test_gate_attacker_selection_and_refusal`.
    """

    def __init__(
        self,
        repository: BattleRepository,
        simulation: Simulation,
        commander: Commander,
        scenarios: ScenarioCatalog,
        replay: ReplayService,
        *,
        player_side=None,
        player_mode="scripted",
        opponent=None,
        scenario_id=None,
        player_policy=None,
        abort_on_fallback=False,
        spend_guard=None,
    ):
        self.scenario = scenarios.resolve(scenario_id)
        sides = tuple(self.scenario.sides)
        player_side = self.scenario.player if player_side is None else player_side
        if player_side not in sides:
            raise ValueError(
                f"Unknown player side {player_side!r}; {self.scenario.id} has {', '.join(sides)}"
            )
        if player_mode not in PLAYER_MODES:
            raise ValueError(f"Unknown player provider {player_mode!r}")
        self.repository = repository
        self.simulation = simulation
        self.commander = commander
        self.scenarios = scenarios
        self.replay = replay
        self.player_side = player_side
        # Two-sided scenarios only: the victory kind refuses any other count.
        self.opponent_side = next(s for s in sides if s != player_side)
        self.player_mode = player_mode
        self.opponent = self._opponent(opponent)
        self.player_policy = self._policy(player_policy)
        if abort_on_fallback and player_mode != "openrouter":
            raise ValueError("abort_on_fallback needs a model player side")
        self.abort_on_fallback = abort_on_fallback
        if spend_guard is not None and player_mode != "openrouter":
            raise ValueError("spend_guard needs a model player side")
        self.spend_guard = spend_guard

    @property
    def baseline(self):
        # Scripted-vs-scripted run: the interactive player's side issues direct
        # orders without decision records, as the Union always did.
        return self.player_mode == "scripted" and self.player_side == self.scenario.player

    def _opponent(self, requested):
        # The computer side's control, by the same rule as the player's.
        default = scripted_policy(self.scenario, self.opponent_side)
        if requested is None:
            return default
        if requested not in SCRIPTED_POLICIES:
            raise ValueError(f"Unknown opponent control {requested!r}")
        refusal = gate_policy_refusal(requested, default)
        if refusal:
            raise ValueError(refusal)
        return requested

    def _policy(self, requested):
        if self.player_mode != "scripted":
            if requested not in (None, OPPONENT_POLICY):
                raise ValueError(
                    f"Player policy {requested!r} needs a scripted player side"
                )
            return None
        default = scripted_policy(self.scenario, self.player_side)
        if requested is None:
            return default
        if requested not in SCRIPTED_POLICIES:
            raise ValueError(f"Unknown player policy {requested!r}")
        refusal = gate_policy_refusal(requested, default)
        if refusal:
            raise ValueError(refusal)
        return requested

    @property
    def gate_policy(self):
        # A named control (gate or Concord) is recorded in run metadata.
        return self.player_policy in NAMED_POLICIES

    def metadata(self, state):
        model_run = self.player_mode == "openrouter"
        extra = {"player_policy": self.player_policy} if self.gate_policy else {}
        return {
            "rules": state.get("rules"),
            "scenario": state.get("scenario"),
            "scenario_id": self.scenario.id,
            "variant": self.scenario.variant,
            "prompt_version": self.scenario.prompt_version,
            "player_side": self.player_side,
            "player_provider": self.player_mode,
            "model": self.commander.model if model_run else None,
            "effort": self.commander.effort if model_run else None,
            "response_format": self.commander.response_format if model_run else None,
            "opponent_side": self.opponent_side,
            "opponent": self.opponent,
            **extra,
        }

    def run(self):
        state = self.scenarios.create(self.scenario.id)
        state["run"] = self.metadata(state)
        game_id = self.repository.create(state)

        def commit(action):
            nonlocal state
            updated = self.simulation.apply(state, action)
            self.repository.save(game_id, updated, state["revision"])
            state = updated

        while state["status"] == "active":
            opponent_decision = None
            if state["turn"] % 3 == 0:
                for action in self._player_actions(state):
                    commit(action)
                opponent_decision = self.commander.decide(
                    state, side=self.opponent_side, mode="scripted", policy=self.opponent
                )
            commit({"type": "advance", "decision": opponent_decision})
        summary = {
            "game_id": game_id,
            "winner": state["winner"],
            "turns": state["turn"],
            "events": len(state["events"]),
            "strength": {u["id"]: u["strength"] for u in state["units"]},
            "replay": self.replay.verify(game_id),
        }
        if self.gate_policy or not self.baseline:
            summary["run"] = state["run"]
        if not self.baseline:
            summary["player_decisions"] = self._decision_counts(state)
        return summary

    def _player_actions(self, state):
        if not self.baseline:
            decision = self.commander.decide(
                state, side=self.player_side, mode=self.player_mode, policy=self.player_policy
            )
            # Doc 69 §8 gap 4: a fallback is never a model decision; stop before it is stored.
            model_made = decision.get("source") == "openrouter" and not decision.get("fallback")
            if self.abort_on_fallback and not model_made:
                raise ModelFallback(decision)
            if self.spend_guard is not None:
                self.spend_guard.charge(decision_cost(decision))
            return [{"type": "decision", "decision": decision}]
        view = self.simulation.view(state, self.player_side)
        standing, orders = scripted_actions(
            self.player_policy, view, self.scenario.sides[self.player_side].role
        )
        actions = [{"type": "standing", "instruction": i} for i in standing]
        return actions + ([{"type": "orders", "orders": orders}] if orders else [])

    def _decision_counts(self, state):
        mine = [d for d in state["decisions"] if d.get("side") == self.player_side]
        return {
            "total": len(mine),
            "model": sum(1 for d in mine if d["source"] == "openrouter"),
            "fallback": sum(1 for d in mine if d.get("fallback")),
        }
