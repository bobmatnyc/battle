"""Versioned Python rules and scenario entries exposed through application ports."""

from .. import command_policy, engine, runtime
from ..contracts import UnknownScenario
from ..scenario import LITTLE_ROUND_TOP
from ..scenario_entry import build_state, dry_run, map_document, validate


class RulesSimulation:
    apply = staticmethod(runtime.apply)
    view = staticmethod(engine.view)
    god_view = staticmethod(engine.god_view)
    observation = staticmethod(command_policy.observation_for)
    validate_orders = staticmethod(command_policy.validated)
    player_side = staticmethod(engine.player_side)
    role = staticmethod(engine.role)


class ScenarioRegistry:
    """Why: several scenarios must share one catalog, chosen by id for new
    games and by snapshot label for saved ones.
    What: validates every entry against the current rules and dry-runs its
    build once on construction, refuses duplicate ids or labels, and resolves ``scenario_id`` (None means
    ``default``) or a state's ``scenario`` label to its entry. Unknown ids
    raise ``UnknownScenario`` naming the known ids.
    Test: `test_catalog_resolves_ids_and_refuses_unknown_scenarios`,
    `test_catalog_resolves_saved_games_by_label`,
    `test_registry_dry_run_refuses_terrain_gaps_and_off_grid_features`.
    """

    def __init__(self, entries, default=None):
        entries = tuple(dry_run(validate(entry)) for entry in entries)
        if not entries:
            raise ValueError("A scenario catalog needs at least one entry.")
        self._entries = {}
        self._labels = {}
        for entry in entries:
            if entry.id in self._entries:
                raise ValueError(f"Duplicate scenario id {entry.id!r}.")
            self._entries[entry.id] = entry
            for label in entry.labels.values():
                if self._labels.setdefault(label, entry.id) != entry.id:
                    raise ValueError(f"Scenario label {label!r} belongs to two entries.")
        self.default_id = default or entries[0].id
        self.resolve(self.default_id)

    def ids(self):
        return tuple(self._entries)

    def resolve(self, scenario_id=None):
        scenario_id = self.default_id if scenario_id is None else scenario_id
        entry = self._entries.get(scenario_id) if isinstance(scenario_id, str) else None
        if entry is None:
            raise UnknownScenario(
                f"Unknown scenario {scenario_id!r}. Known scenarios: {', '.join(self._entries)}."
            )
        return entry

    def for_state(self, state):
        scenario_id = self._labels.get(state.get("scenario"))
        if scenario_id is None:
            raise UnknownScenario(
                f"Saved scenario {state.get('scenario')!r} is not in this catalog."
            )
        return self._entries[scenario_id]

    def create(self, scenario_id=None):
        return build_state(self.resolve(scenario_id))

    def map(self, scenario_id=None):
        return map_document(self.resolve(scenario_id))


class LittleRoundTopCatalog(ScenarioRegistry):
    """Compatibility catalog holding Little Round Top only."""

    def __init__(self):
        super().__init__([LITTLE_ROUND_TOP])
