"""Composition root: concrete dependencies are constructed only at process edges."""

from dataclasses import replace

from . import analysis
from .adapters.openrouter import OpenRouterProvider
from .adapters.rules import LittleRoundTopCatalog, RulesSimulation
from .clock import SimulationClock
from .config import Settings
from .presentation import present_view
from .services.battle import BattleService
from .services.commander import CommanderService
from .services.queries import BattleQueries
from .services.replay import ReplayService
from .storage import Store


def build_application(db, *, offline=False, settings=None):
    settings = settings if settings is not None else Settings.load()
    repository = Store(db)
    simulation = RulesSimulation()
    commander = CommanderService(simulation, OpenRouterProvider(settings))
    replay = ReplayService(repository, simulation)
    queries = BattleQueries(
        repository, simulation, replay, assess=analysis.assess, present=present_view
    )
    return BattleService(
        repository,
        simulation,
        commander,
        LittleRoundTopCatalog(),
        queries,
        SimulationClock,
        mode="scripted" if offline or not commander.available else "openrouter",
    )


def build_replay(db):
    # Replaying requires neither provider configuration nor clock construction.
    return ReplayService(Store(db), RulesSimulation())


def build_headless(
    db,
    *,
    player_side="union",
    player_provider="scripted",
    opponent=None,
    settings=None,
    provider=None,
    model=None,
    effort=None,
    max_tokens=None,
    timeout=None,
):
    """Why: the headless run composes its player provider here, never in services.
    What: ``scripted`` uses ``DisabledProvider``; ``openrouter`` builds the
    OpenRouter adapter from ``Settings`` with CLI overrides applied, unless a
    ``provider`` is injected (tests use a fake). Overrides left as None keep the
    ``Settings`` value. The defaults reproduce the scripted baseline run.
    Test: `test_build_headless_composes_openrouter_overrides`,
    `test_build_headless_refuses_openrouter_without_credential`.
    """
    from .adapters.openrouter import DisabledProvider
    from .command_policy import OPPONENT_POLICY
    from .services.headless import HeadlessRunner

    if player_provider == "openrouter" and provider is None:
        settings = settings if settings is not None else Settings.load()
        overrides = {
            "model": model,
            "effort": effort,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        settings = replace(
            settings, **{k: v for k, v in overrides.items() if v is not None}
        )
        provider = OpenRouterProvider(settings)
        if not provider.available:
            raise ValueError(
                "OpenRouter player run needs OPENROUTER_API_KEY in the environment or .env.local."
            )
    elif provider is None:
        provider = DisabledProvider()
    repository = Store(db)
    simulation = RulesSimulation()
    commander = CommanderService(simulation, provider)
    return HeadlessRunner(
        repository,
        simulation,
        commander,
        LittleRoundTopCatalog(),
        ReplayService(repository, simulation),
        player_side=player_side,
        player_mode=player_provider,
        opponent=opponent or OPPONENT_POLICY,
    )
