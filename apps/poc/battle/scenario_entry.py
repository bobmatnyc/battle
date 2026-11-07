"""Scenario entries: one data record per scenario, built into an initial battle.

Why: later battles must be added as data, not as forks of the Little Round Top
builder. What: ``ScenarioEntry`` holds sides and per-side missions, units and
command attachment, map reference, setting, victory, rules edition, prompt
version, order catalog and variant label. ``build_state`` turns an entry into the
initial snapshot for a rules edition; ``validate`` refuses an entry the current
rules cannot run. Format: ``docs/research/38-scenario-catalog.md``.
"""

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from . import grid, scenario_checks, scenario_command, scenario_units, scenario_wwii
from .scenario_command import CommandEntry, WeaponEntry
from .scenario_wwii import BridgeEntry, SignalEntry

# Sides and roles of every edition before poc-9, which fixed them in the rules.
SIDES = ("union", "confederate")
LEGACY_ROLES = {"union": "defender", "confederate": "attacker"}
RULES_VERSION = "poc-13"
EDITIONS = ("poc-1", "poc-2", "poc-3", "poc-4", "poc-5", "poc-6", "poc-7", "poc-8", "poc-9", "poc-10", "poc-11", "poc-12", "poc-13")
# poc-9 takes side ids, names, roles, the player side and the victory kind from
# the entry (stored in the snapshot); these remain fixed by the rules.
ROLES = ("defender", "attacker")
SIDE_ID = re.compile(r"[a-z][a-z0-9_]{0,31}")
SECONDS_PER_TURN = 30  # engine.issue states delays as turns * 30 seconds.
ORDER_CATALOG = ("hold", "move", "rest", "retreat", "resupply", "recon", "dig_in")
# poc-10: an entry whose map declares a gate offers Close the gate as well.
GATE_ORDER_CATALOG = ORDER_CATALOG + ("close_gate",)
# docs/research/52 labels; "inferred:" is a reading from sourced facts (54).
PROVENANCE = ("sourced:", "reconstruction:", "authored:", "inferred:")
# comms.PROFILES ids; the Napoleonic profile shares the 1863 transport rates.
# poc-13B: the 1775 profile adds a voice reach (scenario_command).
COMMUNICATIONS = ("civil-war-courier-v1", "napoleonic-courier-v1", scenario_command.COLONIAL_COMMUNICATIONS,
                  scenario_wwii.RADIO_COMMUNICATIONS)


def unit(uid, side, name, pos):
    """Default aggregate detachment; entries override fields per unit."""
    return {'id':uid,'side':side,'name':name,'pos':pos,'initial':40,'strength':40,
            'ammo':1600,'morale':85,'suppression':0,'fatigue':0,'status':'ready',
            'target':None,'stance':'hold','move_credit':0,'loss_credit':0,
            'order_version':0,'skill':70,'unit_type':'infantry','weapon_class':scenario_command.DEFAULT_WEAPON_CLASS,
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
class SideBrief:
    """Command-desk text for the player who commands one side (display only).

    Never stored in a snapshot and never put in a prompt. ``mission_text``
    marks emphasis as ``**bold**``; ``win`` and ``loss`` are the outcome
    headlines for this side's player.
    """

    kicker: str
    tagline: str
    subhead: str
    mission_title: str
    mission_text: str
    win: str
    loss: str


@dataclass(frozen=True)
class DeskBrief:
    """Scenario-wide command-desk text (display only, like ``SideBrief``).

    ``place`` and ``objective_label`` caption the objective on the map,
    ``objective_key`` is its map-key entry, ``conditions`` the weather line and
    ``draw`` the outcome headline for a draw.
    """

    campaign: str
    place: str
    objective_label: str
    objective_key: str
    conditions: str
    draw: str


@dataclass(frozen=True)
class SideEntry:
    """One side: its mission is the only objective text its own prompt shows.

    ``name`` labels the side in outcome reports and staff prose; ``role`` is
    ``defender`` or ``attacker`` for the victory kind (poc-9 stores both).
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
    brief: SideBrief | None = None


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
    """Victory: ``kind`` names an entry of ``victory.KINDS``, which checks the
    remaining fields. Sides take part through their ``role``. ``radius``,
    ``hold_turns`` and ``objective_name`` parameterise ``hold-objective``.
    ``seize-and-hold`` (docs/research/54) also reads ``more_objectives``
    (further hexes to seize) and ``relief_turn`` (None: no relief); the
    other kinds refuse both."""

    kind: str
    objective: tuple[int, int]
    deadline_turns: int
    radius: int = 1
    hold_turns: int = 3
    objective_name: str = "objective"
    more_objectives: tuple[tuple[int, int], ...] = ()
    relief_turn: int | None = None


@dataclass(frozen=True)
class GateEntry:
    """Authored gate labour (poc-10), stored in the snapshot as ``gate_rules``.

    Labour units, as Dig in counts them: a party adds ``min(strength,
    work_cap)`` per interval. Closing needs ``close_labour``, barring a closed
    gate a further ``bar_labour``; attackers force a closed (not barred) gate
    with ``force_labour``. No source gives these numbers: they are POC
    sensitivity parameters, labelled by ``basis``.
    """

    close_labour: int
    bar_labour: int
    force_labour: int
    work_cap: int
    basis: str = "authored POC sensitivity parameter; not a historical estimate"


@dataclass(frozen=True)
class GatewayPushEntry:
    """Authored push through a held gateway (poc-11), stored as ``push_rules``.

    Attackers on a gate's outside hex add ``min(strength, push_cap)`` per
    interval against an enemy in the gateway; at ``push_labour`` the holder
    gives way (docs/research/44). Sensitivity parameters, labelled by ``basis``.
    """

    push_labour: int
    push_cap: int
    basis: str = "authored sensitivity parameter; not a historical estimate"


# FireEntry defaults left out of a snapshot (docs/research/50).
OMITTED = (('release_by', 'unit'), ('release_scope', 'hit'))


@dataclass(frozen=True)
class FireEntry:
    """Fire discipline (poc-13), stored in the snapshot as ``fire_rules``.

    ``default_posture`` (``hold_fire`` or ``open_fire``) is every unit's
    posture unless a unit override names ``fire_posture``. A ``hold_fire``
    unit fires only when fired upon (docs/research/46). Whether a warning
    shot (enemy fire that causes the unit no casualties in that interval)
    counts as being fired upon is ``warning_shots_release``; no source
    settles it, so it is an authored sensitivity flag, off by default.
    ``release_by`` (unit|command), ``release_scope`` (hit|earshot): docs/research/50.
    """

    default_posture: str = "open_fire"
    warning_shots_release: bool = False
    release_by: str = "unit"
    release_scope: str = "hit"
    basis: str = "authored sensitivity parameter; not a historical estimate"


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
    ``player_side`` is the side the interactive player commands (None: the
    first side).
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
    player_side: str | None = None
    gates: GateEntry | None = None
    gateway_push: GatewayPushEntry | None = None
    fire: FireEntry | None = None  # poc-13; None means FireEntry().
    command: CommandEntry | None = None  # poc-13B succession; None: none.
    weapons: Mapping[str, WeaponEntry] | None = None  # poc-13B; None: rifle baseline.
    tactics: str | None = None  # docs/research/55: "tactics_v11"; None: tactics_v10.
    # docs/research/53 (1944): bridge state, codeword signals, night observation.
    bridges: tuple[BridgeEntry, ...] | None = None
    signals: tuple[SignalEntry, ...] | None = None
    observation_range: int | None = None  # None: each unit's own (7 hexes).
    # Side id -> scripted control id (command_policy.SCRIPTED_POLICIES) for an
    # entry with its own controls (Concord); None: the gate or fallback rule.
    scripted: Mapping[str, str] | None = None
    desk: DeskBrief | None = None
    # Field name -> "sourced: ...", "reconstruction: ..." or "authored: ...".
    # Documentation only: never stored in a snapshot or shown in a prompt.
    provenance: Mapping[str, str] = field(default_factory=dict)

    @property
    def player(self):
        return self.player_side or next(iter(self.sides))

    @property
    def start_local(self):
        return f"{self.date}T{self.start_time}"

    def owns(self, state):
        """True when ``state`` is a snapshot of this scenario in any edition."""
        return state.get("scenario") in self.labels.values()


def validate(entry):
    """Why: a scenario must fail at registration, not mid-battle, when it asks
    for something the current rules cannot do.
    What: raises ValueError listing every mismatch with the current engine:
    side ids, names and roles, the player side, the victory kind and its own
    checks (``victory.KINDS``), grid geometry, turn length, order catalog,
    communications, voice, unit roster and command attachment, headquarters
    and supply hexes on the grid, unit overrides that would replace a
    unit's id, side or hex, and provenance notes without a kind label.
    Test: `test_catalog_refuses_entry_the_rules_cannot_run`,
    `test_registry_refuses_off_grid_headquarters_and_supply`,
    `test_registry_refuses_overrides_of_unit_identity`.
    """
    from .presentation import VOICE_PROFILES

    problems = []
    if entry.rules != RULES_VERSION:
        problems.append(f"rules {entry.rules!r} is not the current edition {RULES_VERSION!r}")
    if entry.rules not in entry.labels:
        problems.append(f"no snapshot label for {entry.rules!r}")
    problems.extend(_side_problems(entry))
    victory = entry.victory
    if not grid.valid(list(victory.objective)) or victory.deadline_turns <= 0:
        problems.append("victory objective or deadline is invalid")
    shape = (entry.map.cols, entry.map.rows, entry.map.metres_per_hex)
    if shape != (grid.COLS, grid.ROWS, grid.METRES_PER_HEX):
        problems.append(f"map must be {grid.COLS}x{grid.ROWS} hexes of {grid.METRES_PER_HEX} m")
    if entry.seconds_per_turn != SECONDS_PER_TURN:
        problems.append(f"turns must be {SECONDS_PER_TURN} seconds")
    catalog = GATE_ORDER_CATALOG if _has_gates(entry) else ORDER_CATALOG
    if tuple(entry.order_catalog) != catalog:
        problems.append(f"order catalog must be {catalog}")
    if _has_gates(entry) != (entry.gates is not None):
        problems.append("authored gate labour is required exactly when a building declares openings")
    elif entry.gates and not all(
        type(v) is int and v > 0
        for v in (entry.gates.close_labour, entry.gates.bar_labour, entry.gates.force_labour, entry.gates.work_cap)
    ):
        problems.append("gate labour values must be positive integers")
    push = entry.gateway_push
    if _has_gates(entry) != (push is not None):
        problems.append("authored gateway push is required exactly when a building declares openings")
    elif push and not all(type(v) is int and v > 0 for v in (push.push_labour, push.push_cap)):
        problems.append("gateway push values must be positive integers")
    problems.extend(scenario_checks.fire_problems(entry, entry.fire or FireEntry()))
    problems.extend(scenario_command.command_problems(entry))  # poc-13B
    problems.extend(scenario_command.weapon_problems(entry))
    problems.extend(scenario_wwii.problems(entry))  # docs/research/53
    problems.extend(scenario_units.problems(entry))  # docs/research/58
    problems.extend(_scripted_problems(entry))
    if entry.communications not in COMMUNICATIONS:
        problems.append(f"communications must be one of {COMMUNICATIONS}")
    if entry.voice_profile not in VOICE_PROFILES:
        problems.append(f"voice profile must be one of {tuple(VOICE_PROFILES)}")
    if not entry.prompt_version or not all(s.mission for s in entry.sides.values()):
        problems.append("prompt version and every side's mission are required")
    problems.extend(_roster_problems(entry))
    unlabelled = [k for k, v in entry.provenance.items() if not str(v).startswith(PROVENANCE)]
    if unlabelled:
        problems.append(f"provenance of {', '.join(unlabelled)} must start with one of {PROVENANCE}")
    if problems:
        raise ValueError(f"Scenario {entry.id!r} cannot run: " + "; ".join(problems))
    return entry


def _scripted_problems(entry):
    """An entry's own scripted controls name its sides and known controls."""
    from .command_policy import SCRIPTED_POLICIES

    return [f"scripted control for {side!r} must be a scenario side and one of {SCRIPTED_POLICIES}"
            for side, policy in (entry.scripted or {}).items()
            if side not in entry.sides or policy not in SCRIPTED_POLICIES]


def _side_problems(entry):
    from . import victory

    problems = []
    if len(entry.sides) < 2:
        problems.append("a scenario needs at least two sides")
    for side, spec in entry.sides.items():
        if not isinstance(side, str) or not SIDE_ID.fullmatch(side):
            problems.append(f"side id {side!r} must be lower-case letters, digits or _")
        if not spec.name:
            problems.append(f"side {side!r} needs a display name")
        if spec.role not in ROLES:
            problems.append(f"side {side!r} role must be one of {ROLES}")
    if entry.player not in entry.sides:
        problems.append(f"player side {entry.player!r} is not a scenario side")
    kind = victory.KINDS.get(entry.victory.kind)
    if kind is None:
        problems.append(f"victory kind {entry.victory.kind!r} is not one of {tuple(victory.KINDS)}")
    else:
        problems.extend(kind.problems(entry))
    return problems


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
    problems = scenario_checks.feature_problems(entry.map.features)
    if not problems:
        try:
            state = build_state(entry)
        except Exception as exc:
            problems.append(f"build_state failed: {type(exc).__name__}: {exc}")
        else:
            problems.extend(_terrain_problems(state["cells"]))
            problems.extend(scenario_checks.water_problems(entry, state["cells"]))
            problems.extend(scenario_wwii.bridge_cell_problems(entry, state["cells"]))
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


def _has_gates(entry):
    return any(b.get("openings") for b in entry.map.features.get("buildings", ()))


def _at_least(rules, edition):
    return EDITIONS.index(rules) >= EDITIONS.index(edition)


def build_state(entry, rules=None):
    """Why: one builder serves every scenario, so an entry needs no code.
    What: returns the initial snapshot of ``entry`` in ``rules`` (default the
    entry's edition), layering each edition's additions in the order the
    Little Round Top builder always used, so its snapshots stay byte-identical.
    From poc-9 the snapshot also stores ``sides`` (a list of id, name and
    role in entry order; a list because storage sorts object keys and side
    order fixes event order), ``player_side`` and ``victory`` (the kind's
    parameters), so the engine and replay never need the catalog.
    Raises ValueError for an edition the entry has no label for, or for an
    edition before poc-9 when the sides are not Union/Confederate.
    Test: `test_little_round_top_entry_rebuilds_every_edition_byte_identically`,
    `test_duel_fixture_runs_headless_and_replays`.
    """
    rules = rules or entry.rules
    if rules not in entry.labels or rules not in EDITIONS:
        raise ValueError(f"Scenario {entry.id!r} has no {rules!r} edition.")
    sides = tuple(entry.sides)
    if not _at_least(rules, 'poc-9') and sides != SIDES:
        raise ValueError(f"{rules} supports only the sides {SIDES}.")
    if not _at_least(rules, 'poc-10') and _has_gates(entry):
        raise ValueError(f"{rules} has no gates; building openings need poc-10.")
    if not _at_least(rules, 'poc-13') and scenario_checks.has_water(entry):
        raise ValueError(f"{rules} has no impassable water; a river needs poc-13.")
    if not _at_least(rules, 'poc-13') and scenario_command.declares(entry):
        raise ValueError(f"{rules} has no succession, voice reach, weapon table or tactics_v11; they need poc-13.")
    if not _at_least(rules, 'poc-13') and scenario_wwii.declares(entry):
        raise ValueError(f"{rules} has no bridge state, radio, signals or night range; they need poc-13.")
    if not _at_least(rules, 'poc-13') and scenario_units.declares(entry):
        raise ValueError(f"{rules} has no declared rout_strength, press_assault, gun facing or surrender; they need poc-13.")
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
         'contacts': {x: {} for x in sides},
         'friendly_reports': {side: {u['id']: dict(u, observed_turn=0, received_turn=0)
                                     for u in units if u['side'] == side} for side in sides},
         'dispatches': {x: [] for x in sides}, 'events': [], 'decisions': [],
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
        s['acknowledgements'] = {side: {} for side in sides}
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
    if _at_least(rules, 'poc-8'):
        s.update(recommendations=[], standing_orders=[])
        for u in units:
            u.update(standing_profile='balanced', standing_version=0)
            s['friendly_reports'][u['side']][u['id']].update(
                standing_profile='balanced', standing_version=0)
    if _at_least(rules, 'poc-9'):
        from . import victory
        s['sides'] = [{'id': side, 'name': spec.name, 'role': spec.role}
                      for side, spec in entry.sides.items()]
        s['player_side'] = entry.player
        s['victory'] = victory.KINDS[entry.victory.kind].setup(entry)
    if _at_least(rules, 'poc-10') and entry.gates:
        from dataclasses import asdict
        s['gate_rules'] = asdict(entry.gates)
    if _at_least(rules, 'poc-11') and entry.gateway_push:
        from dataclasses import asdict
        s['push_rules'] = asdict(entry.gateway_push)
        s['push_effort'] = {}
    if _at_least(rules, 'poc-13'):
        from dataclasses import asdict
        # docs/research/50: only a non-default release is written, so every
        # earlier poc-13 snapshot and digest stays as it was.
        s['fire_rules'] = {k: v for k, v in asdict(entry.fire or FireEntry()).items() if (k, v) not in OMITTED}
        for u in units:
            u.setdefault('fire_posture', s['fire_rules']['default_posture'])
            s['friendly_reports'][u['side']][u['id']]['fire_posture'] = u['fire_posture']
        scenario_command.setup(s, entry, units)  # poc-13B: writes nothing without the data.
        scenario_wwii.setup(s, entry, units)  # docs/research/53: nor does the 1944 data.
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
