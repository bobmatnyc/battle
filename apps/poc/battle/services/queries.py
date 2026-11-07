"""Read models for current state, history and audit, independent of HTTP."""

from collections.abc import Callable
from ..contracts import AuditUnavailable, BattleRepository, Document, Simulation, UnknownScenario
from ..presentation import present_analysis, scenario_brief
from .replay import ReplayService


class BattleQueries:
    def __init__(
        self,
        repository: BattleRepository,
        simulation: Simulation,
        replay: ReplayService,
        *,
        assess: Callable[[Document], Document],
        present: Callable[..., Document],
        scenarios=None,
    ):
        self.repository = repository
        self.simulation = simulation
        self.replay_service = replay
        self.assess = assess
        self.present = present
        self.scenarios = scenarios

    def _entry(self, state):
        """The catalog entry owning ``state``'s label; None for no catalog or a
        label from another catalog (display then keeps the original voice)."""
        if self.scenarios is None:
            return None
        try:
            return self.scenarios.for_state(state)
        except UnknownScenario:
            return None

    def project(self, state, *, god=False, side=None):
        """Why: the desk and replay show one side's commander view or God's.
        What: the presented view of ``state``: God's when ``god``, else the
        commander view of ``side`` (None: the snapshot's player side), with
        that side's brief and assessment. A side the snapshot lacks, or a side
        named together with ``god``, raises ValueError. Never mutates ``state``.
        Test: `test_each_side_replay_equals_its_live_view_at_every_revision`,
        `test_replay_refuses_an_unknown_side_and_side_with_god`."""
        if side is not None and (god or side not in state.get("friendly_reports", {})):
            # docs/research/65: one view per request; a side must be the battle's own.
            raise ValueError("Unknown side for this battle, or a side with the God view.")
        commander_view = self.simulation.view(state, side)
        # Early report summaries omitted immutable, pre-briefed own-unit traits.
        # These editions have no training/remixing; restore only those traits,
        # never live strength, condition, position or enemy information.
        if state.get("rules", "poc-1") in {"poc-1", "poc-2", "poc-3"}:
            own = {unit["id"]: unit for unit in state["units"]
                   if unit["side"] == commander_view["side"]}
            for report in commander_view["units"]:
                source = own.get(report["id"], {})
                for key in ("unit_type", "skill", "weapon_class", "recon_role", "recon_skill"):
                    if key not in report and key in source:
                        report[key] = source[key]
        entry = self._entry(state)
        result = self.present(
            self.simulation.god_view(state) if god else commander_view, entry
        )
        if entry is not None:
            result["scenario_brief"] = scenario_brief(entry, commander_view["side"])
        result["analysis"] = present_analysis(self.assess(commander_view), entry)  # poc-13B review: 1775 address
        return result

    def replay(self, game_id, revision, *, god=False, side=None):
        """Read-only: the stored snapshot at ``revision`` through ``project``."""
        return self.project(self.repository.load(game_id, revision), god=god, side=side)

    def history(self, game_id):
        return self.repository.history(game_id)

    def export(self, game_id):
        state = self.repository.load(game_id)
        if state["status"] != "complete":
            raise AuditUnavailable("Full audit unlocks after battle completion.")
        return {
            "game_id": game_id,
            "state": state,
            "replay": self.replay_service.verify(game_id),
        }
