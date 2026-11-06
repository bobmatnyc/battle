"""Scenario entries: one data record per scenario, built into an initial battle.

Why: later battles must be added as data, not as forks of the Little Round Top
builder. What: ``ScenarioEntry`` holds sides and per-side missions, units and
command attachment, map reference, setting, victory, rules edition, prompt
version, order catalog and variant label. ``build_state`` turns an entry into the
initial snapshot for a rules edition; ``validate`` refuses an entry the current
rules cannot run. Format: ``docs/research/38-scenario-catalog.md``.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from . import grid

SIDES = ("union", "confederate")
RULES_VERSION = "poc-8"
EDITIONS = ("poc-1", "poc-2", "poc-3", "poc-4", "poc-5", "poc-6", "poc-7", "poc-8")
# The poc-8 engine scores one victory model with fixed side roles and constants
# (engine.advance). An entry asking for anything else needs a new rules edition.
POC8_VICTORY = {"kind": "hold-objective", "radius": 1, "hold_turns": 3}
POC8_ROLES = {"union": "defender", "confederate": "attacker"}
POC8_SECONDS_PER_TURN = 30  # engine.issue states delays as turns * 30 seconds.
POC8_ORDER_CATALOG = ("hold", "move", "rest", "retreat", "resupply", "recon", "dig_in")
POC8_COMMUNICATIONS = "civil-war-courier-v1"  # comms.PROFILE, the only profile.


def unit(uid, side, name, pos):
    """Default aggregate detachment; entries override fields per unit."""
    return {'id':uid,'side':side,'name':name,'pos':pos,'initial':40,'strength':40,
            'ammo':1600,'morale':85,'suppression':0,'fatigue':0,'status':'ready',
            'target':None,'stance':'hold','move_credit':0,'loss_credit':0,
            'order_version':0,'skill':70,'unit_type':'infantry','weapon_class':'rifled muskets',
            'recon_role':'line','recon_skill':35,'local_action':'hold','local_reason':'Awaiting contact; hold position.',
            'tactical_target':None,'last_attacked_turn':-99,'withdraw_until':0}


@dataclass(frozen=True)
class SupplyEntry:
    """A finite ammunition point (poc-5 and later)."""

    name: str
    pos: tuple[int, int]
    ammo: int
    weapon_class: str


@dataclass(frozen=True)
class SideEntry:
    """One side: its mission is the only objective text its own prompt shows.

    ``headquarters`` is the rally point (and the poc-1/poc-2 headquarters);
    ``command_unit`` is the detachment the side's controller is attached to.
    ``charge`` completes the staff adviser's scripted summary.
    """

    name: str
    role: str
    mission: str
    charge: str
    command_unit: str
    headquarters: tuple[int, int]
    supply: SupplyEntry | None = None


@dataclass(frozen=True)
class UnitEntry:
    """A starting detachment; ``overrides`` replace fields of ``unit()``."""

    id: str
    side: str
    name: str
    pos: tuple[int, int]
    overrides: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VictoryEntry:
    """Victory model. ``deadline_turns`` and ``objective`` are free; the rest is
    fixed by the rules edition (see ``POC8_VICTORY``)."""

    kind: str
    objective: tuple[int, int]
    defender: str
    attacker: str
    deadline_turns: int
    radius: int = 1
    hold_turns: int = 3


@dataclass(frozen=True)
class MapEntry:
    """Terrain reference: a cell builder, authored features and display data."""

    terrain: Callable[[], dict]
    features: Mapping[str, Any]
    cols: int
    rows: int
    metres_per_hex: int
    width: int
    height: int
    source: str
    source_url: str | None


@dataclass(frozen=True)
class ScenarioEntry:
    """Everything that distinguishes one scenario from another.

    ``labels`` maps each supported rules edition to the snapshot's
    ``scenario`` label; a catalog resolves saved games by that label.
    """

    id: str
    title: str
    variant: str | None
    rules: str
    prompt_version: str
    prompt_setting: str
    labels: Mapping[str, str]
    location: str
    date: str
    start_time: str
    time_basis: str
    seconds_per_turn: int
    weather: Mapping[str, str]
    sides: Mapping[str, SideEntry]
    units: tuple[UnitEntry, ...]
    victory: VictoryEntry
    map: MapEntry
    order_catalog: tuple[str, ...]
    communications: str
    voice_profile: str
    tools_per_unit: int = 20

    @property
    def start_local(self):
        return f"{self.date}T{self.start_time}"

    def owns(self, state):
        """True when ``state`` is a snapshot of this scenario in any edition."""
        return state.get("scenario") in self.labels.values()


def validate(entry):
    """Why: a scenario must fail at registration, not mid-battle, when it asks
    for something the current rules cannot do.
    What: raises ValueError listing every mismatch with the poc-8 engine: side
    ids and roles, victory model, grid geometry, turn length, order catalog,
    communications, voice, unit roster and command attachment, headquarters
    and supply hexes on the grid, and unit overrides that would replace a
    unit's id, side or hex.
    Test: `test_catalog_refuses_entry_the_rules_cannot_run`,
    `test_registry_refuses_off_grid_headquarters_and_supply`,
    `test_registry_refuses_overrides_of_unit_identity`.
    """
    from .presentation import VOICE_PROFILE

    problems = []
    if entry.rules != RULES_VERSION:
        problems.append(f"rules {entry.rules!r} is not the current edition {RULES_VERSION!r}")
    if entry.rules not in entry.labels:
        problems.append(f"no snapshot label for {entry.rules!r}")
    if tuple(entry.sides) != SIDES:
        problems.append(f"sides must be {SIDES} in {RULES_VERSION}")
    for side, role in POC8_ROLES.items():
        if side in entry.sides and entry.sides[side].role != role:
            problems.append(f"{side} must be the {role} in {RULES_VERSION}")
    victory = entry.victory
    for name, required in POC8_VICTORY.items():
        if getattr(victory, name) != required:
            problems.append(f"victory {name} must be {required!r} in {RULES_VERSION}")
    if (victory.defender, victory.attacker) != ("union", "confederate"):
        problems.append("victory defender/attacker must be union/confederate")
    if not grid.valid(list(victory.objective)) or victory.deadline_turns <= 0:
        problems.append("victory objective or deadline is invalid")
    shape = (entry.map.cols, entry.map.rows, entry.map.metres_per_hex)
    if shape != (grid.COLS, grid.ROWS, grid.METRES_PER_HEX):
        problems.append(f"map must be {grid.COLS}x{grid.ROWS} hexes of {grid.METRES_PER_HEX} m")
    if entry.seconds_per_turn != POC8_SECONDS_PER_TURN:
        problems.append(f"turns must be {POC8_SECONDS_PER_TURN} seconds")
    if tuple(entry.order_catalog) != POC8_ORDER_CATALOG:
        problems.append(f"order catalog must be {POC8_ORDER_CATALOG}")
    if entry.communications != POC8_COMMUNICATIONS:
        problems.append(f"communications must be {POC8_COMMUNICATIONS!r}")
    if entry.voice_profile != VOICE_PROFILE:
        problems.append(f"voice profile must be {VOICE_PROFILE!r}")
    if not entry.prompt_version or not all(s.mission for s in entry.sides.values()):
        problems.append("prompt version and every side's mission are required")
    problems.extend(_roster_problems(entry))
    if problems:
        raise ValueError(f"Scenario {entry.id!r} cannot run: " + "; ".join(problems))
    return entry


# Fields a unit override may not replace: the roster and command attachment
# are checked against them, so an override would bypass those checks.
FIXED_UNIT_FIELDS = ("id", "side", "pos")


def _roster_problems(entry):
    ids = [u.id for u in entry.units]
    positions = [tuple(u.pos) for u in entry.units]
    problems = []
    if len(set(ids)) != len(ids) or len(set(positions)) != len(positions):
        problems.append("unit ids and starting hexes must be unique")
    for u in entry.units:
        if u.side not in entry.sides or not grid.valid(list(u.pos)):
            problems.append(f"unit {u.id} has an unknown side or invalid hex")
        fixed = [name for name in FIXED_UNIT_FIELDS if name in u.overrides]
        if fixed:
            problems.append(f"unit {u.id} overrides may not set {', '.join(fixed)}")
    for side, spec in entry.sides.items():
        if not grid.valid(list(spec.headquarters)):
            problems.append(f"{side} headquarters {spec.headquarters} is off the grid")
        if spec.supply and not grid.valid(list(spec.supply.pos)):
            problems.append(f"{side} supply point {spec.supply.pos} is off the grid")
    by_id = {u.id: u for u in entry.units}
    for side, spec in entry.sides.items():
        attached = by_id.get(spec.command_unit)
        if attached is None or attached.side != side:
            problems.append(f"{side} command unit {spec.command_unit!r} is not a {side} unit")
    return problems


def dry_run(entry):
    """Why: some faults only show once an entry is built (a terrain builder that
    misses hexes, a feature off the map), and must not surface mid-battle.
    What: builds ``entry`` once in its own edition and raises ValueError unless
    the build succeeds, the terrain has exactly one cell per grid hex with the
    fields movement and fire read, and every feature position, road point and
    road hex lies on the grid. Returns ``entry``.
    Test: `test_registry_dry_run_refuses_terrain_gaps_and_off_grid_features`.
    """
    problems = _feature_problems(entry.map.features)
    if not problems:
        try:
            state = build_state(entry)
        except Exception as exc:
            problems.append(f"build_state failed: {type(exc).__name__}: {exc}")
        else:
            problems.extend(_terrain_problems(state["cells"]))
            for f in state.get("map_features", []):
                hexes = ([f["pos"]] if "pos" in f else []) + list(f.get("hexes", []))
                if not all(grid.valid(list(p)) for p in hexes):
                    problems.append(f"built feature {f.get('id')!r} leaves the grid")
    if problems:
        raise ValueError(f"Scenario {entry.id!r} cannot run: " + "; ".join(problems))
    return entry


CELL_FIELDS = ("pos", "elevation", "terrain", "move_cost", "cover")


def _terrain_problems(cells):
    expected = {grid.key([c, r]) for r in range(grid.ROWS) for c in range(grid.COLS)}
    problems = []
    missing, extra = expected - set(cells), set(cells) - expected
    if missing:
        problems.append(f"terrain misses {len(missing)} grid hexes, e.g. {sorted(missing)[0]}")
    if extra:
        problems.append(f"terrain has {len(extra)} cells off the grid, e.g. {sorted(extra)[0]}")
    for k in sorted(expected & set(cells)):
        cell = cells[k]
        if any(name not in cell for name in CELL_FIELDS) or grid.key(cell["pos"]) != k:
            problems.append(f"terrain cell {k} lacks {', '.join(CELL_FIELDS)} or names another hex")
            break
    return problems


def _feature_problems(features):
    problems = []
    for road in features.get("roads", ()):
        if not all(grid.valid(list(p)) for p in road["points"]):
            problems.append(f"road {road['id']!r} has points off the grid")
    for kind in ("buildings", "works"):
        for f in features.get(kind, ()):
            if not grid.valid(list(f["pos"])):
                problems.append(f"{kind[:-1]} {f['id']!r} at {f['pos']} is off the grid")
    return problems


def _at_least(rules, edition):
    return EDITIONS.index(rules) >= EDITIONS.index(edition)


def build_state(entry, rules=None):
    """Why: one builder serves every scenario, so an entry needs no code.
    What: returns the initial snapshot of ``entry`` in ``rules`` (default the
    entry's edition), layering each edition's additions in the order the
    Little Round Top builder always used, so its snapshots stay byte-identical.
    Raises ValueError for an edition the entry has no label for.
    Test: `test_little_round_top_entry_rebuilds_every_edition_byte_identically`,
    `test_duel_fixture_runs_headless_and_replays`.
    """
    rules = rules or entry.rules
    if rules not in entry.labels or rules not in EDITIONS:
        raise ValueError(f"Scenario {entry.id!r} has no {rules!r} edition.")
    units = [unit(u.id, u.side, u.name, list(u.pos)) for u in entry.units]
    for built, spec in zip(units, entry.units):
        built.update(deepcopy(dict(spec.overrides)))
    s = {'rules': rules, 'scenario': entry.labels[rules], 'turn': 0, 'revision': 0,
         'status': 'active', 'winner': None, 'reason': None,
         'objective': list(entry.victory.objective),
         'recon_memory': {}, 'intel_assets': [], 'capture': 0,
         'max_turns': entry.victory.deadline_turns,
         'seconds_per_turn': entry.seconds_per_turn, 'units': units,
         'cells': entry.map.terrain(), 'orders': [], 'reports': [],
         'contacts': {x: {} for x in SIDES},
         'friendly_reports': {side: {u['id']: dict(u, observed_turn=0, received_turn=0)
                                     for u in units if u['side'] == side} for side in SIDES},
         'dispatches': {x: [] for x in SIDES}, 'events': [], 'decisions': [],
         'weather': dict(entry.weather),
         'hq': {side: list(spec.headquarters) for side, spec in entry.sides.items()}}
    if _at_least(rules, 'poc-3'):
        s['rally_points'] = {side: list(pos) for side, pos in s['hq'].items()}
        # Staff are attached to existing aggregate detachments, not extra soldiers.
        s['commanders'] = {side: {'controller_id': side + '-commander',
                                  'unit_id': spec.command_unit,
                                  'communications': entry.communications}
                           for side, spec in entry.sides.items()}
        s['hq'] = {side: next(list(u['pos']) for u in units if u['id'] == c['unit_id'])
                   for side, c in s['commanders'].items()}
        s['acknowledgements'] = {side: {} for side in SIDES}
    if _at_least(rules, 'poc-4'):
        s.update(formation_ops=[], formation_notices={}, retired_units=[])
    if _at_least(rules, 'poc-5'):
        s['supply_sites'] = [{'id': side + '-ammunition', 'side': side,
                              'name': spec.supply.name, 'pos': list(spec.supply.pos),
                              'ammo': spec.supply.ammo, 'weapon_class': spec.supply.weapon_class}
                             for side, spec in entry.sides.items() if spec.supply]
    if _at_least(rules, 'poc-6'):
        from . import features
        for u in units:
            u['tools'] = entry.tools_per_unit
        features.setup(s, entry.map.features)
        for u in units:
            s['friendly_reports'][u['side']][u['id']]['tools'] = u['tools']
    if rules == 'poc-7':
        s['recommendations'] = []
    if rules == 'poc-8':
        s.update(recommendations=[], standing_orders=[])
        for u in units:
            u.update(standing_profile='balanced', standing_version=0)
            s['friendly_reports'][u['side']][u['id']].update(
                standing_profile='balanced', standing_version=0)
    return s


def map_document(entry):
    """The command-desk map and setting for ``entry`` (briefing terrain only)."""
    return {
        "setting": {
            "location": entry.location,
            "start_local": entry.start_local,
            "time_basis": entry.time_basis,
        },
        "cells": list(entry.map.terrain().values()),
        "cols": entry.map.cols,
        "rows": entry.map.rows,
        "radius": grid.RADIUS,
        "metres_per_hex": entry.map.metres_per_hex,
        "width": entry.map.width,
        "height": entry.map.height,
        "source": entry.map.source,
        "source_url": entry.map.source_url,
    }
