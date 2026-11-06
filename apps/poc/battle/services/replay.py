"""Replay consumes recorded inputs. It has no commander/provider dependency."""

from ..contracts import BattleRepository, Simulation
from ..replay import verify


class ReplayService:
    def __init__(self, repository: BattleRepository, simulation: Simulation):
        self.repository = repository
        self.simulation = simulation

    def verify(self, game_id):
        return verify(self.repository, game_id, self.simulation.apply)
