"""Composition root: concrete dependencies are constructed only at process edges."""

from dataclasses import replace

from . import analysis
from .adapters.openrouter import OpenRouterProvider
from .adapters.rules import RulesSimulation, ScenarioRegistry
from .clock import SimulationClock
from .config import Settings
from .presentation import present_view
from .scenario import LITTLE_ROUND_TOP
from .scenario_hougoumont import HOUGOUMONT_NORTH_GATE
from .services.battle import BattleService
from .services.commander import CommanderService
from .services.queries import BattleQueries
from .services.replay import ReplayService
from .storage import Store

# Player-facing scenarios; the first is the default. Test fixtures stay out.
PLAYER_SCENARIOS = (LITTLE_ROUND_TOP, HOUGOUMONT_NORTH_GATE)


def build_scenarios():
    """The player-facing scenario catalog, validated against the current rules."""
    return ScenarioRegistry(PLAYER_SCENARIOS)


def build_application(db, *, offline=False, settings=None, scenario_id=None):
    """Why: the interactive server composes every concrete dependency here.
    What: new games use ``scenario_id`` (None: the catalog default); an unknown
    id raises ``UnknownScenario`` before any database is opened.
    Test: `test_new_game_creation_selects_and_refuses_scenarios`.
    """
    scenarios = build_scenarios()
    scenarios.resolve(scenario_id)
    settings = settings if settings is not None else Settings.load()
    repository = Store(db)
    simulation = RulesSimulation()
    commander = CommanderService(
        simulation, OpenRouterProvider(settings), scenarios=scenarios
    )
    replay = ReplayService(repository, simulation)
    queries = BattleQueries(
        repository, simulation, replay, assess=analysis.assess, present=present_view
    )
    return BattleService(
        repository,
        simulation,
        commander,
        scenarios,
        queries,
        SimulationClock,
        mode="scripted" if offline or not commander.available else "openrouter",
        scenario_id=scenario_id,
    )


def build_replay(db):
    # Replaying requires neither provider configuration nor clock construction.
    return ReplayService(Store(db), RulesSimulation())


def build_headless(
    db,
    *,
    player_side=None,
    player_provider="scripted",
    opponent=None,
    settings=None,
    provider=None,
    model=None,
    effort=None,
    max_tokens=None,
    timeout=None,
    scenario_id=None,
    scenarios=None,
    player_policy=None,
):
    """Why: the headless run composes its player provider here, never in services.
    What: ``scripted`` uses ``DisabledProvider``; ``openrouter`` builds the
    OpenRouter adapter from ``Settings`` with CLI overrides applied, unless a
    ``provider`` is injected (tests use a fake). Overrides left as None keep the
    ``Settings`` value. The defaults reproduce the scripted baseline run.
    ``scenario_id`` picks the scenario from ``scenarios`` (default: the
    player-facing catalog); an unknown id raises ``UnknownScenario`` before
    any credential is read or database opened. ``player_side`` None is the
    scenario's player side; a side the scenario lacks raises ValueError.
    Test: `test_build_headless_composes_openrouter_overrides`,
    `test_build_headless_refuses_openrouter_without_credential`,
    `test_build_headless_refuses_unknown_scenario`.
    """
    from .adapters.openrouter import DisabledProvider
    from .command_policy import OPPONENT_POLICY
    from .services.headless import HeadlessRunner

    scenarios = scenarios if scenarios is not None else build_scenarios()
    entry = scenarios.resolve(scenario_id)
    if player_side is not None and player_side not in entry.sides:
        # Checked before any credential is read or database opened.
        raise ValueError(
            f"Unknown player side {player_side!r}; {entry.id} has {', '.join(entry.sides)}."
        )
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
    commander = CommanderService(simulation, provider, scenarios=scenarios)
    return HeadlessRunner(
        repository,
        simulation,
        commander,
        scenarios,
        ReplayService(repository, simulation),
        player_side=player_side,
        player_mode=player_provider,
        opponent=opponent or OPPONENT_POLICY,
        scenario_id=scenario_id,
        player_policy=player_policy,
    )
