"""poc-13 registration checks for scenario entries (docs/research/46).

Why: a river and fire discipline are scenario data, so an entry that the
rules cannot run must be refused at registration, as ``scenario_entry``
refuses other faults. Kept apart from ``scenario_entry`` for size only.
"""

from . import grid

# A water cell (``water: true``) is impassable unless it is a crossing.
CROSSINGS = ("bridge", "ford")
FIRE_POSTURES = ("hold_fire", "open_fire")


def fire_problems(entry, fire):
    """poc-13 fire discipline: known postures and a boolean warning-shot flag."""
    problems = []
    if fire.default_posture not in FIRE_POSTURES or type(fire.warning_shots_release) is not bool:
        problems.append(f"fire default posture must be one of {FIRE_POSTURES} and warning_shots_release a boolean")
    for u in entry.units:
        if "fire_posture" in u.overrides and u.overrides["fire_posture"] not in FIRE_POSTURES:
            problems.append(f"unit {u.id!r} fire posture must be one of {FIRE_POSTURES}")
    return problems


def water_problems(entry, cells):
    """Why: a river must be data the rules can run, refused at registration.
    What: problems with poc-13 water: ``water`` must be true where present, a
    ``crossing`` (one of CROSSINGS) only on a water cell, no unit,
    headquarters, supply point or objective on impassable water, and no
    water, crossing or not, on a building's compound or gateway hexes.
    Test: `test_registration_refuses_bad_water_data`,
    `test_registration_refuses_water_in_a_compound_or_gateway`."""
    problems = []
    for k in sorted(cells):
        c = cells[k]
        if "water" in c and c["water"] is not True:
            problems.append(f"terrain cell {k} water must be true when present")
        if "crossing" in c and (not c.get("water") or c["crossing"] not in CROSSINGS):
            problems.append(f"terrain cell {k} crossing must be one of {CROSSINGS} on a water cell")
    if problems or not any(c.get("water") for c in cells.values()):
        return problems
    # poc-13B (review LOW): gate passage and walls are not defined over water.
    for b in entry.map.features.get("buildings", ()):
        hexes = [b["pos"], *b.get("compound", ())]
        hexes += [p for o in b.get("openings", ()) for p in (o["inside"], o["outside"])]
        if any(cells[grid.key(list(p))].get("water") for p in hexes):
            problems.append(f"building {b['id']!r} has water in a compound or gateway hex")
    places = [(f"unit {u.id!r}", u.pos) for u in entry.units]
    places += [(f"{side} headquarters", s.headquarters) for side, s in entry.sides.items()]
    places += [(f"{side} supply", s.supply.pos) for side, s in entry.sides.items() if s.supply]
    places.append(("victory objective", entry.victory.objective))
    for name, pos in places:
        if not grid.passable(cells[grid.key(list(pos))]):
            problems.append(f"{name} stands on impassable water")
    return problems


def has_water(entry):
    return any(c.get("water") for c in entry.map.terrain().values())
