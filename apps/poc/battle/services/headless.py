"""Full local simulation use case, sharing the same ports as interactive play."""

from ..command_policy import (
    GATE_DEFENDER_POLICY, OPPONENT_POLICY, SCRIPTED_POLICIES, fallback_orders,
    gate_defender_actions, scripted_policy,
)
from ..contracts import BattleRepository, Commander, ScenarioCatalog, Simulation
from .replay import ReplayService

PLAYER_MODES = ("scripted", "openrouter")


class HeadlessRunner:
    """Why: a model must be able to play one side end to end, with a scripted
    control on the other side, and the run must replay without a provider.
    What: ``player_side`` is driven by ``commander`` in ``player_mode``; the
    other side is the explicit scripted ``opponent``. Sides come from the
    scenario entry; ``player_side`` None is the entry's player side. A
    scripted run of that side keeps the direct-orders path, so Little Round
    Top's default run is unchanged.
    ``player_policy`` picks the scripted control of that direct-orders path
    (None: the entry's choice, ``scripted-gate-defender-v1`` for the defender
    of a gated entry, else ``scripted-fallback-v1``). A run under the gate
    policy records it as ``player_policy`` in run metadata and its summary;
    other runs keep their metadata and output unchanged.
    ``scenario_id`` selects the catalog entry (None: the catalog default);
    an unknown id raises ``UnknownScenario`` before anything is stored.
    Test: `test_model_player_run_records_side_decisions_and_replays`,
    `test_default_headless_run_keeps_baseline_path`,
    `test_duel_fixture_runs_headless_and_replays`.
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
        opponent=OPPONENT_POLICY,
        scenario_id=None,
        player_policy=None,
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
        if opponent != OPPONENT_POLICY:
            raise ValueError(f"Unknown opponent control {opponent!r}")
        self.repository = repository
        self.simulation = simulation
        self.commander = commander
        self.scenarios = scenarios
        self.replay = replay
        self.player_side = player_side
        # Two-sided scenarios only: the victory kind refuses any other count.
        self.opponent_side = next(s for s in sides if s != player_side)
        self.player_mode = player_mode
        self.opponent = opponent
        self.player_policy = self._policy(player_policy)

    @property
    def baseline(self):
        # Scripted-vs-scripted run: the interactive player's side issues direct
        # orders without decision records, as the Union always did.
        return self.player_mode == "scripted" and self.player_side == self.scenario.player

    def _policy(self, requested):
        if not self.baseline:
            if requested not in (None, OPPONENT_POLICY):
                raise ValueError(
                    f"Player policy {requested!r} needs a scripted run of the scenario's player side"
                )
            return None
        default = scripted_policy(self.scenario, self.player_side)
        if requested is None:
            return default
        if requested not in SCRIPTED_POLICIES:
            raise ValueError(f"Unknown player policy {requested!r}")
        if requested == GATE_DEFENDER_POLICY and default != GATE_DEFENDER_POLICY:
            raise ValueError(f"{GATE_DEFENDER_POLICY} needs the defending side of a gated scenario")
        return requested

    @property
    def gate_policy(self):
        return self.player_policy == GATE_DEFENDER_POLICY

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
                    state, side=self.opponent_side, mode="scripted"
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
                state, side=self.player_side, mode=self.player_mode
            )
            return [{"type": "decision", "decision": decision}]
        view = self.simulation.view(state, self.player_side)
        standing = []
        if self.gate_policy:
            standing, orders = gate_defender_actions(view)
        else:
            orders = fallback_orders(view, self.scenario.sides[self.player_side].role)
        actions = [{"type": "standing", "instruction": i} for i in standing]
        return actions + ([{"type": "orders", "orders": orders}] if orders else [])

    def _decision_counts(self, state):
        mine = [d for d in state["decisions"] if d.get("side") == self.player_side]
        return {
            "total": len(mine),
            "model": sum(1 for d in mine if d["source"] == "openrouter"),
            "fallback": sum(1 for d in mine if d.get("fallback")),
        }
