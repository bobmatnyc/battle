"""Full local simulation use case, sharing the same ports as interactive play."""

from ..command_policy import OPPONENT_POLICY, PROMPT_VERSION, fallback_orders
from ..contracts import BattleRepository, Commander, ScenarioCatalog, Simulation
from ..scenario import SIDES
from .replay import ReplayService

PLAYER_MODES = ("scripted", "openrouter")


class HeadlessRunner:
    """Why: a model must be able to play one side end to end, with a scripted
    control on the other side, and the run must replay without a provider.
    What: ``player_side`` is driven by ``commander`` in ``player_mode``; the
    other side is the explicit scripted ``opponent``. The scripted Union
    default keeps today's direct-orders path, so its run is unchanged.
    Test: `test_model_player_run_records_side_decisions_and_replays`,
    `test_default_headless_run_keeps_baseline_path`.
    """

    def __init__(
        self,
        repository: BattleRepository,
        simulation: Simulation,
        commander: Commander,
        scenarios: ScenarioCatalog,
        replay: ReplayService,
        *,
        player_side="union",
        player_mode="scripted",
        opponent=OPPONENT_POLICY,
    ):
        if player_side not in SIDES:
            raise ValueError(f"Unknown player side {player_side!r}")
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
        self.opponent_side = next(s for s in SIDES if s != player_side)
        self.player_mode = player_mode
        self.opponent = opponent

    @property
    def baseline(self):
        # Today's scripted-vs-scripted run: Union orders bypass decision records.
        return self.player_mode == "scripted" and self.player_side == "union"

    def metadata(self, state):
        model_run = self.player_mode == "openrouter"
        return {
            "rules": state.get("rules"),
            "scenario": state.get("scenario"),
            "prompt_version": PROMPT_VERSION,
            "player_side": self.player_side,
            "player_provider": self.player_mode,
            "model": self.commander.model if model_run else None,
            "effort": self.commander.effort if model_run else None,
            "opponent_side": self.opponent_side,
            "opponent": self.opponent,
        }

    def run(self):
        state = self.scenarios.create()
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
                action = self._player_action(state)
                if action:
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
        if not self.baseline:
            summary["run"] = state["run"]
            summary["player_decisions"] = self._decision_counts(state)
        return summary

    def _player_action(self, state):
        if self.baseline:
            orders = fallback_orders(self.simulation.view(state, "union"))
            return {"type": "orders", "orders": orders} if orders else None
        decision = self.commander.decide(
            state, side=self.player_side, mode=self.player_mode
        )
        return {"type": "decision", "decision": decision}

    def _decision_counts(self, state):
        mine = [d for d in state["decisions"] if d.get("side") == self.player_side]
        return {
            "total": len(mine),
            "model": sum(1 for d in mine if d["source"] == "openrouter"),
            "fallback": sum(1 for d in mine if d.get("fallback")),
        }
