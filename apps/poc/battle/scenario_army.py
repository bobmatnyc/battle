"""Army-scale entry data (docs/research/63 §2.2 and §10, 68).

Why: Cannae (doc 63) needs a declared scale, per-unit speed, army-scale
losses and morale, a flank and rear effect and two local doctrines. Each is
entry data that the rules read only when a snapshot carries it
(``army_rules``), so every earlier battle and every saved poc-13 game plays
as before. Kept apart from ``scenario_entry`` for size.
What: the ``ArmyEntry`` record, the declared scale it allows, the unit keys
``move_rate``, ``yield`` and ``wheel``, their registration checks and the
snapshot setup ``build_state`` calls.
"""

from dataclasses import dataclass
from typing import Mapping

# Doc 63 §2.2 option A: 200 m hexes and 180 s intervals on the unchanged grid.
# Any other declared scale is refused until an entry needs it (option B is a variant).
ARMY_SCALES = ((200, 180),)
UNIT_KEYS = ("move_rate", "yield", "wheel")
YIELD_FIELDS = ("limit", "rear_step")
WHEEL_FIELDS = ("front_row", "reach", "rear_step")
MAX_MOVE_RATE = 3  # Doc 63 §6: cavalry 3 hexes an interval, the fastest declared.


@dataclass(frozen=True)
class ArmyEntry:
    """Army-scale fire and morale (doc 63 gap 3 and 4), stored as ``army_rules``.

    A volley fires ``engaged_pct`` per cent of the unit's strength; a class in
    ``shock_classes`` spends no ammunition. Morale falls ``morale_per_pct``
    points per per cent of the unit's starting strength lost. A blow from a
    flank multiplies the loss by ``flank_pct`` per cent, from the rear by
    ``rear_pct``, and the extra share again counts toward morale. Each unit
    starts facing its side's ``fronts`` bearing (degrees clockwise from map
    north). Sensitivity parameters, labelled by ``basis``.
    """

    engaged_pct: int
    morale_per_pct: int
    flank_pct: int
    rear_pct: int
    shock_classes: tuple[str, ...]
    fronts: Mapping[str, int]
    basis: str = "authored sensitivity parameter; not a historical estimate"


def _int(value, low, high):
    return type(value) is int and low <= value <= high


def _rule_problems(u, name, fields, check):
    if name not in u.overrides:
        return []
    r = u.overrides[name]
    if not (isinstance(r, dict) and tuple(sorted(r)) == fields and check(r)):
        return [f"unit {u.id!r} {name} must have exactly {fields} in range"]
    return []


def problems(entry):
    """Why: army-scale data the rules cannot use must fail at registration.
    What: a scale other than 50 m and 30 s must be one of ``ARMY_SCALES`` and
    needs ``army``; ``army`` needs a weapon table naming every shock class,
    integer coefficients (``engaged_pct`` 1-100, ``morale_per_pct`` 0-100,
    ``flank_pct`` and ``rear_pct`` 100-1000) and a front of 0-359 for every
    side; the unit keys need ``army``: ``move_rate`` 1 to ``MAX_MOVE_RATE``,
    ``yield`` with a ``limit`` of 1-7 and a ``rear_step`` of -1 or 1,
    ``wheel`` with a ``reach`` of 1-7, a ``front_row`` on the grid and a
    ``rear_step`` of -1 or 1.
    Test: `test_registration_refuses_an_undeclared_scale`,
    `test_registration_refuses_bad_army_data`,
    `test_the_unit_keys_need_army_rules`."""
    from . import grid
    from .scenario_entry import SECONDS_PER_TURN

    found = []
    army = entry.army
    scale = (entry.map.metres_per_hex, entry.seconds_per_turn)
    if scale != (grid.METRES_PER_HEX, SECONDS_PER_TURN) and (army is None or scale not in ARMY_SCALES):
        found.append(f"a scale other than {grid.METRES_PER_HEX} m and {SECONDS_PER_TURN} s must be one of "
                     f"{ARMY_SCALES} (metres, seconds) and needs army rules, not {scale}")
    declared = [u.id for u in entry.units if any(k in u.overrides for k in UNIT_KEYS)]
    if army is None:
        if declared:
            found.append(f"units {declared} declare {UNIT_KEYS}, which need army rules")
        return found
    if not entry.weapons or not set(army.shock_classes) <= set(entry.weapons):
        found.append("army shock_classes must name classes of the entry's weapon table")
    if not (_int(army.engaged_pct, 1, 100) and _int(army.morale_per_pct, 0, 100)
            and _int(army.flank_pct, 100, 1000) and _int(army.rear_pct, 100, 1000)):
        found.append("army engaged_pct 1-100, morale_per_pct 0-100, flank_pct and rear_pct 100-1000")
    if set(army.fronts) != set(entry.sides) or not all(_int(v, 0, 359) for v in army.fronts.values()):
        found.append("army fronts must give every side a bearing of 0 to 359")
    step = lambda v: v in (-1, 1) and type(v) is int
    for u in entry.units:
        if "move_rate" in u.overrides and not _int(u.overrides["move_rate"], 1, MAX_MOVE_RATE):
            found.append(f"unit {u.id!r} move_rate must be an integer of 1 to {MAX_MOVE_RATE}")
        found.extend(_rule_problems(u, "yield", YIELD_FIELDS,
                                    lambda r: _int(r["limit"], 1, 7) and step(r["rear_step"])))
        found.extend(_rule_problems(u, "wheel", WHEEL_FIELDS,
                                    lambda r: _int(r["reach"], 1, 7) and _int(r["front_row"], 0, grid.ROWS - 1)
                                    and step(r["rear_step"])))
    return found


def declares(entry):
    """True when ``entry`` declares army rules; ``build_state`` then refuses an
    edition before ``poc-13``."""
    return entry.army is not None


def setup(s, entry, units):
    """Store ``army_rules`` and each unit's starting ``front``; nothing for an
    entry without army rules, so earlier battles keep their snapshots."""
    army = entry.army
    if army is None:
        return
    s["army_rules"] = {"engaged_pct": army.engaged_pct, "morale_per_pct": army.morale_per_pct,
                       "flank_pct": army.flank_pct, "rear_pct": army.rear_pct,
                       "shock_classes": list(army.shock_classes)}
    s["metres_per_hex"] = entry.map.metres_per_hex
    for u in units:
        u["front"] = army.fronts[u["side"]]
