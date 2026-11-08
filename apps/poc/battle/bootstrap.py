"""Composition root: concrete dependencies are constructed only at process edges."""

from dataclasses import replace

from . import analysis
from .batch_store import BatchStore, recorded_in
from .adapters.openrouter import OpenRouterProvider
from .adapters.rules import RulesSimulation, ScenarioRegistry
from .clock import SimulationClock
from .config import Settings
from .presentation import present_view
from .scenario import LITTLE_ROUND_TOP
from .scenario_concord import CONCORD_NORTH_BRIDGE, CONCORD_NORTH_BRIDGE_V1
from .scenario_cannae import CANNAE_ENVELOPMENT
from .scenario_gergovia import GERGOVIA_RECALL
from .scenario_hill223 import HILL_223_PATROL
from .scenario_hougoumont import HOUGOUMONT_NORTH_GATE
from .scenario_pegasus import PEGASUS_BRIDGE
from .services.battle import BattleService
from .services.commander import CommanderService
from .services.queries import BattleQueries
from .services.replay import ReplayService
from .storage import Store

# Player-facing scenarios; the first is the default. Test fixtures stay out.
# docs/research/74: Concord joins after the two; both desks draw its river, bridge and roads.
# docs/research/75: Pegasus Bridge and Hill 223 follow; both desks draw the canal, the
# bridges and their charges, and Hill 223's ravine, woods and trench.
PLAYER_SCENARIOS = (LITTLE_ROUND_TOP, HOUGOUMONT_NORTH_GATE, CONCORD_NORTH_BRIDGE, PEGASUS_BRIDGE, HILL_223_PATROL)
# Headless runs also offer Concord's v1 entry, so saved v1 games still open
# (docs/research/50), Gergovia (docs/research/57 §9 q7, 62) and Cannae
# (docs/research/63 §9 q12, 68), which wait on the BCE date ruling bt-D07.
# The catalog order is unchanged by the moves to the desk.
HEADLESS_SCENARIOS = (LITTLE_ROUND_TOP, HOUGOUMONT_NORTH_GATE, CONCORD_NORTH_BRIDGE, CONCORD_NORTH_BRIDGE_V1,
                      PEGASUS_BRIDGE, HILL_223_PATROL, GERGOVIA_RECALL, CANNAE_ENVELOPMENT)


def build_scenarios():
    """The player-facing scenario catalog, validated against the current rules."""
    return ScenarioRegistry(PLAYER_SCENARIOS)


def build_headless_scenarios():
    """The headless catalog: the player scenarios plus the headless-only entries, validated."""
    return ScenarioRegistry(HEADLESS_SCENARIOS)


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
        repository, simulation, replay, assess=analysis.assess, present=present_view,
        scenarios=scenarios,
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
    # A database written by a batch run (``BatchStore``) re-runs its recorded inputs.
    store = BatchStore(db) if recorded_in(db) else Store(db)
    return ReplayService(store, RulesSimulation())


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
    keyframe_every=None,
    abort_on_fallback=False,
    spend_guard=None,
):
    """Why: the headless run composes its player provider here, never in services.
    What: ``scripted`` uses ``DisabledProvider``; ``openrouter`` builds the
    OpenRouter adapter from ``Settings`` with CLI overrides applied, unless a
    ``provider`` is injected (tests use a fake). Overrides left as None keep the
    ``Settings`` value. The defaults reproduce the scripted baseline run.
    ``scenario_id`` picks the scenario from ``scenarios`` (default: the
    headless catalog, the player scenarios plus the headless-only entries); an unknown id raises ``UnknownScenario`` before
    any credential is read or database opened. ``player_side`` None is the
    scenario's player side; a side the scenario lacks raises ValueError.
    ``keyframe_every`` None stores every revision's snapshot (``Store``); a
    whole number opts a batch run into ``BatchStore``: inputs and digests per
    revision, full snapshots at revision 0, the end and every K-th revision.
    ``abort_on_fallback`` passes to ``HeadlessRunner`` (doc 69 §9), as does
    ``spend_guard``, whose ``check`` the commander runs before each request.
    Test: `test_build_headless_composes_openrouter_overrides`,
    `test_build_headless_refuses_openrouter_without_credential`,
    `test_build_headless_refuses_unknown_scenario`,
    `test_batch_run_keeps_the_pinned_digest_and_only_the_end_snapshots`.
    """
    from .adapters.openrouter import DisabledProvider
    from .services.headless import HeadlessRunner

    scenarios = scenarios if scenarios is not None else build_headless_scenarios()
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
    repository = Store(db) if keyframe_every is None else BatchStore(db, keyframe_every)
    simulation = RulesSimulation()
    commander = CommanderService(simulation, provider, scenarios=scenarios,
                                 before_request=spend_guard.check if spend_guard else None)
    return HeadlessRunner(
        repository,
        simulation,
        commander,
        scenarios,
        ReplayService(repository, simulation),
        player_side=player_side,
        player_mode=player_provider,
        opponent=opponent,
        scenario_id=scenario_id,
        player_policy=player_policy,
        abort_on_fallback=abort_on_fallback,
        spend_guard=spend_guard,
    )
