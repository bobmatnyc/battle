"""Registration checks for an entry's sides, roster and built terrain.

Why: ``scenario_entry.validate`` and ``dry_run`` refuse an entry the rules
cannot run; these checks were moved here from ``scenario_entry`` for size only
(no behaviour change). What: side ids, names, roles and the victory kind's own
checks; scripted controls; unit ids, hexes and command attachment; and the
built terrain's cell coverage.
Test: `test_catalog_refuses_entry_the_rules_cannot_run`,
`test_registry_refuses_off_grid_headquarters_and_supply`,
`test_registry_refuses_overrides_of_unit_identity`,
`test_registry_dry_run_refuses_terrain_gaps_and_off_grid_features`.
"""

import re

from . import grid

# poc-9 takes side ids, names, roles, the player side and the victory kind from
# the entry (stored in the snapshot); these remain fixed by the rules.
ROLES = ("defender", "attacker")
SIDE_ID = re.compile(r"[a-z][a-z0-9_]{0,31}")
# Fields a unit override may not replace: the roster and command attachment
# are checked against them, so an override would bypass those checks.
FIXED_UNIT_FIELDS = ("id", "side", "pos")
CELL_FIELDS = ("pos", "elevation", "terrain", "move_cost", "cover")


def scripted_problems(entry):
    """An entry's own scripted controls name its sides and known controls."""
    from .command_policy import SCRIPTED_POLICIES

    return [f"scripted control for {side!r} must be a scenario side and one of {SCRIPTED_POLICIES}"
            for side, policy in (entry.scripted or {}).items()
            if side not in entry.sides or policy not in SCRIPTED_POLICIES]


def side_problems(entry):
    """Side ids, names and roles, the player side and the victory kind's checks."""
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


def roster_problems(entry):
    """Unique unit ids and hexes, known sides, fixed fields, HQ/supply hexes."""
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


def terrain_problems(cells):
    """One cell per grid hex, each carrying the fields movement and fire read."""
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
