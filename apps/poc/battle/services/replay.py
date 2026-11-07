"""Replay consumes recorded inputs. It has no commander/provider dependency."""

from ..contracts import BattleRepository, Simulation
from ..replay import verify, verify_recorded


class ReplayService:
    def __init__(self, repository: BattleRepository, simulation: Simulation):
        self.repository = repository
        self.simulation = simulation

    def verify(self, game_id):
        # A batch-recorded game (``BatchStore.inputs``) re-runs its inputs;
        # every other game compares each stored snapshot as before.
        inputs = getattr(self.repository, "inputs", None)
        recorded = inputs(game_id) if inputs is not None else None
        if recorded:
            return verify_recorded(self.repository, game_id, self.simulation.apply, recorded)
        return verify(self.repository, game_id, self.simulation.apply)
