"""Concord North Bridge geometry sensitivity variants (docs/research/49).

Why: doc 48 gap 11 found that the authored layout gives the bridge's radius-1
ring three west-bank hexes and one east-bank hex, so the provincials can fill
it while one British company stands in it. The owner's sequence asks for
sensitivity checks before any fire-release change; these variants move or
reshape the bridge and keep every sourced fact.
What: ``Geometry`` holds the authored hexes a Concord layout fixes (bridge,
river column per row, approach, start hexes, headquarters, town).
``geometry_entry`` builds a ``ScenarioEntry`` from the baseline
``concord_entry`` with that geometry and labels it ``sensitivity``.
``SENSITIVITY`` holds each variant as a ``scenario_concord.Variant``.
``POLICIES`` holds the two scripted Concord policies rebound to each
variant's hexes: the same code objects as ``concord_policy``, with only the
four geometry constants replaced (``rebind``). Nothing here changes the
baseline entry, its policies or any rule.
Test: `test_baseline_geometry_rebuilds_the_baseline_entry`,
`test_ring_geometry_of_each_variant`, `test_rebound_policies_run_the_baseline_code`.
"""

import types
from dataclasses import dataclass, replace

from . import concord_policy, grid
from .scenario_concord import (
    APPROACH, BRIDGE, BRIDGE_MOVE_COST, BRITISH_THREE, PROVINCIALS, RIVER_COL, TOWN, Variant,
    _open_fire, concord_entry,
)
from .scenario_entry import UnitEntry


@dataclass(frozen=True)
class Geometry:
    """The authored hexes of one Concord layout. ``river`` is the river's
    column on each row; the bridge is the one crossing, on its own row.
    ``names`` renames a British company whose post moves (unit id -> name)."""

    bridge: tuple
    river: tuple
    approach: dict
    provincials: dict
    british: dict
    headquarters: dict
    town: tuple
    names: dict = None

    @property
    def west_end(self):
        return (self.bridge[0] - 1, self.bridge[1])

    @property
    def east_end(self):
        return (self.bridge[0] + 1, self.bridge[1])


BASELINE_GEOMETRY = Geometry(
    bridge=BRIDGE, river=(RIVER_COL,) * grid.ROWS, approach=APPROACH,
    provincials={u.id: u.pos for u in PROVINCIALS}, british={u.id: u.pos for u in BRITISH_THREE},
    headquarters={"provincial": (3, 10), "british": (21, 10)}, town=TOWN)


def ring_banks(g):
    """Counts of the bridge's radius-1 neighbours by bank: ``west``, ``east``, ``water``."""
    counts = {"west": 0, "east": 0, "water": 0}
    for c, r in grid.neighbors(list(g.bridge)):
        counts["water" if c == g.river[r] else "west" if c < g.river[r] else "east"] += 1
    return counts


def _terrain(g, bridge_cost=BRIDGE_MOVE_COST):
    """``scenario_concord._terrain`` with the river column taken per row."""
    def terrain():
        cells = {}
        for r in range(grid.ROWS):
            river = g.river[r]
            for c in range(grid.COLS):
                elevation = 36 + 2 * max(0, river - 1 - c) if c < river else 36
                cell = {"pos": [c, r], "elevation": elevation, "terrain": "open",
                        "move_cost": 100, "cover": 10,
                        "area": "provincial-ridge" if c < river else "town-bank"}
                if c == river:
                    cell.update(elevation=34, terrain="water", water=True, cover=0, area="concord-river")
                    if (c, r) == g.bridge:
                        cell.update(crossing="bridge", move_cost=bridge_cost, area="north-bridge")
                cells[grid.key([c, r])] = cell
        return cells
    return terrain


def _features(g):
    """``scenario_concord.FEATURES`` with the roads on the bridge's row."""
    row = g.bridge[1]
    return {
        "roads": (
            {"id": "muster-road", "kind": "road", "name": "Road from the muster field to the North Bridge",
             "points": [[2, row], list(g.west_end)]},
            {"id": "town-road", "kind": "road", "name": "Road from the North Bridge to the town",
             "points": [list(g.east_end), [23, row]]},
        ),
        "buildings": (),
        "works": (),
    }


def _policy_ids(name):
    return {"provincial": f"{concord_policy.MILITIA_POLICY}@{name}",
            "british": f"{concord_policy.REGULARS_POLICY}@{name}"}


def geometry_entry(name, g, note=None):
    """Why: a sensitivity variant must differ from the baseline in its
    authored geometry only.
    What: ``concord_entry(name)`` with the units, headquarters, objective,
    terrain and roads of ``g``, the policies rebound to ``g``
    (``_policy_ids``) and a ``sensitivity`` provenance note. Forces,
    strengths, missions, fire postures, weapons and victory rules are the
    baseline's.
    Test: `test_baseline_geometry_rebuilds_the_baseline_entry`.
    """
    names = g.names or {}
    british = tuple(UnitEntry(u.id, u.side, names.get(u.id, u.name), g.british[u.id], u.overrides)
                    for u in BRITISH_THREE)
    base = concord_entry(name, british=_open_fire(british))
    provincials = tuple(UnitEntry(u.id, u.side, u.name, g.provincials[u.id], u.overrides) for u in PROVINCIALS)
    provenance = dict(base.provenance)
    if note:
        provenance["sensitivity"] = f"authored: sensitivity: {note}"
        provenance["scripted"] = ("reconstruction: the scripted historical-order policies of "
                                  "battle/concord_policy.py, rebound to this variant's hexes")
    return replace(
        base,
        units=provincials + base.units[len(PROVINCIALS):],
        sides={side: replace(spec, headquarters=g.headquarters[side]) for side, spec in base.sides.items()},
        victory=replace(base.victory, objective=g.bridge),
        map=replace(base.map, terrain=_terrain(g), features=_features(g)),
        scripted=_policy_ids(name) if note else base.scripted,
        provenance=provenance,
    )


# concord_policy constants that are not hexes and stay as the baseline has them.
NON_GEOMETRY = ("FRESH", "CLEAR_RADIUS")


def _names(code):
    """Global names ``code`` and its nested code objects (comprehensions,
    generator expressions, lambdas) read."""
    names = set(code.co_names)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            names |= _names(const)
    return names


def _unbound(fn, hexes):
    """Upper-case constants ``fn`` reads that ``rebind`` would leave on the
    baseline: any outside ``hexes`` and ``NON_GEOMETRY``, and any but
    ``NON_GEOMETRY`` in a module function it calls by name, since such a
    helper keeps its own module's globals."""
    scope, own = fn.__globals__, _names(fn.__code__)
    found = {n for n in own if n.isupper()} - set(hexes) - set(NON_GEOMETRY)
    seen, todo = {fn.__code__}, [scope[n] for n in own if isinstance(scope.get(n), types.FunctionType)]
    while todo:
        helper = todo.pop()
        if helper.__code__ in seen:
            continue
        seen.add(helper.__code__)
        names = _names(helper.__code__)
        found |= {n for n in names if n.isupper()} - set(NON_GEOMETRY)
        todo.extend(scope[n] for n in names if isinstance(scope.get(n), types.FunctionType))
    return sorted(found)


def rebind(fn, g):
    """Why: a variant's policies must run on its own hexes, never silently on
    the baseline's.
    What: ``fn`` (a ``concord_policy`` function) with its module's geometry
    constants replaced by ``g``'s. The code object is shared, so the order
    logic cannot drift from the baseline policy. Raises ValueError when an
    upper-case constant ``fn`` reads would stay on the baseline (``_unbound``).
    Test: `test_rebound_policies_run_the_baseline_code`,
    `test_rebind_refuses_a_constant_it_does_not_replace`.
    """
    hexes = {"APPROACH": g.approach, "BRIDGE": g.bridge, "EAST_END": g.east_end, "TOWN": g.town}
    unbound = _unbound(fn, hexes)
    if unbound:
        raise ValueError(f"{fn.__name__} reads {', '.join(unbound)}, which rebind does not replace; "
                         "add it to the geometry or to NON_GEOMETRY")
    return types.FunctionType(fn.__code__, {**fn.__globals__, **hexes}, fn.__name__,
                              fn.__defaults__, fn.__closure__)


def _down(pos):
    return (pos[0], pos[1] + 1)


# Everything one row south: the bridge sits on an odd row, where the ring has
# one west-bank hex and three east-bank hexes (B1 and B3 stand in it).
ODD_ROW = Geometry(
    bridge=_down(BRIDGE), river=BASELINE_GEOMETRY.river,
    approach={uid: _down(p) for uid, p in APPROACH.items()},
    provincials={uid: _down(p) for uid, p in BASELINE_GEOMETRY.provincials.items()},
    british={uid: _down(p) for uid, p in BASELINE_GEOMETRY.british.items()},
    headquarters={side: _down(p) for side, p in BASELINE_GEOMETRY.headquarters.items()},
    town=_down(TOWN))
# The bridge stays; the river steps one column west below it, so the ring has
# two hexes on each bank. P3's baseline hex (11, 11) is river: it goes to (10, 11).
_BENT_RIVER = tuple(RIVER_COL if r <= BRIDGE[1] else RIVER_COL - 1 for r in range(grid.ROWS))
BALANCED = replace(BASELINE_GEOMETRY, river=_BENT_RIVER, approach={**APPROACH, "P3": (10, 11)})
# The same ring with B3 on its second east-bank hex: two companies a side inside it.
BALANCED_FULL = replace(BALANCED, british={**BALANCED.british, "B3": (12, 11)},
                        names={"B3": "Light company · south of the road"})

_KEEPS = ("keeps the sourced date, place, forces (Acton 40, about 400 provincials; three British "
          "companies, about 96), missions, Barrett's hold-fire order and the British open fire (S47, S48), "
          "and the baseline weapons, communications, command and victory rules")

SENSITIVITY = {
    name: Variant(question=f"sensitivity: doc 48 gap 11 ({question})", reading=f"sensitivity: {reading}",
                  source=f"authored geometry, no source; {_KEEPS}",
                  entry=geometry_entry(name, g, f"{reading}; {_KEEPS}"))
    for name, g, question, reading in (
        ("sensitivity-odd-row-bridge", ODD_ROW,
         "does the even-row ring decide the hold",
         "changes the authored layout by moving every hex one row south: bridge (12, 11) on an odd row, "
         "ring 1 west-bank hex and 3 east-bank hexes, B1 and B3 inside it"),
        ("sensitivity-balanced-ring", BALANCED,
         "does a balanced ring change the hold",
         "changes the river to column 11 below the bridge (bridge (12, 10) kept): ring 2 west-bank "
         "and 2 east-bank hexes; P3's approach moves from (11, 11), now river, to (10, 11)"),
        ("sensitivity-balanced-ring-full", BALANCED_FULL,
         "does a balanced ring with two British companies in it change the hold",
         "changes the river as sensitivity-balanced-ring and moves B3 from (13, 9) to (12, 11), "
         "the ring's second east-bank hex"),
    )
}
SENSITIVITY_GEOMETRY = {"sensitivity-odd-row-bridge": ODD_ROW, "sensitivity-balanced-ring": BALANCED,
                        "sensitivity-balanced-ring-full": BALANCED_FULL}

POLICIES = {}
for _name, _g in SENSITIVITY_GEOMETRY.items():
    _ids = _policy_ids(_name)
    POLICIES[_ids["provincial"]] = rebind(concord_policy.militia_actions, _g)
    POLICIES[_ids["british"]] = rebind(concord_policy.regulars_actions, _g)
# Policy id -> the side and variant it fits (command_policy.NAMED_POLICIES).
NEEDS = {policy: f"the {side} side of the Concord {name} variant"
         for name in SENSITIVITY_GEOMETRY for side, policy in _policy_ids(name).items()}
