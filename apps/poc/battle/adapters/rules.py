"""Versioned Python rules exposed through the application simulation port."""

from .. import command_policy, engine, runtime, scenario, grid


class RulesSimulation:
    apply = staticmethod(runtime.apply)
    view = staticmethod(engine.view)
    god_view = staticmethod(engine.god_view)
    observation = staticmethod(command_policy.observation_for)
    validate_orders = staticmethod(command_policy.validated)


class LittleRoundTopCatalog:
    create = staticmethod(scenario.create)

    def map(self):
        return {
            "setting": {
                "location": "Little Round Top · Gettysburg, Pennsylvania",
                "start_local": "1863-07-02T16:30:00",
                "time_basis": "Scenario local time; authored start time",
            },
            "cells": list(scenario.terrain().values()),
            "cols": grid.COLS,
            "rows": grid.ROWS,
            "radius": grid.RADIUS,
            "metres_per_hex": grid.METRES_PER_HEX,
            "width": 1080,
            "height": 840,
            "source": "Library of Congress, Gettysburg topographic map (1876). Authored POC terrain; approximate registration.",
            "source_url": "https://www.loc.gov/item/99447491/",
        }
