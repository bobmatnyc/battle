"""poc-13 part B scenario data: succession, voice reach and weapon tables.

Why: the Concord era needs command succession, a spoken-order reach and
smoothbore fire (docs/research/47). Each is entry data that the rules read
only when a snapshot carries it, so battles without it play as before. Kept
apart from ``scenario_entry`` for size.
What: the ``CommandEntry`` and ``WeaponEntry`` records, the 1775 constants,
their registration checks and the snapshot setup ``build_state`` calls.
"""

from dataclasses import asdict, dataclass
from typing import Mapping

# poc-13B: the 1775 profile adds a voice reach to the courier transport
# (comms.PROFILES); a voice packet beyond it is relayed by runner.
COLONIAL_COMMUNICATIONS = "colonial-1775-voice-v1"
MAX_FIRE_RANGE = 5  # engine.volley never fires beyond 5 hexes.


@dataclass(frozen=True)
class CommandEntry:
    """Officers and succession (poc-13B), stored in the snapshot as ``command_rules``.

    Each unit starts with ``officers`` (a unit override ``officers`` replaces
    it). Each time a unit's losses since its last officer fell reach
    ``initial // (officers + 1)``, one officer falls and the next takes
    command. A unit with no officer left is leaderless: it keeps its last
    order and its standing orders, refuses new orders and loses
    ``leaderless_morale`` morale once. When a side's command detachment is
    lost, routed or leaderless, command is vacant for ``succession_delay``
    intervals and then passes to the first operational unit in that side's
    ``succession`` list; with none, the side keeps no command and its units
    continue under standing orders. Sensitivity parameters, labelled by ``basis``.
    """

    succession: Mapping[str, tuple[str, ...]]
    officers: int = 2
    succession_delay: int = 1
    leaderless_morale: int = 10
    basis: str = "authored sensitivity parameter; not a historical estimate"


@dataclass(frozen=True)
class WeaponEntry:
    """One weapon class's fire values (poc-13B), stored as ``weapon_rules``.

    ``range_hexes`` (1 to 5) is the farthest hex the class fires at. The
    exposure falls from the rifle baseline's 7 at 1 hex to 0 beyond
    ``range_hexes`` and is scaled by ``effect_pct`` (1 to 100), the share of
    the baseline's effect. ``basis`` cites the source or labels an assumption.
    """

    range_hexes: int
    effect_pct: int
    basis: str


# poc-13B: smoothbore muskets for 1775. No source in docs/research gives a
# smoothbore range or hit rate (docs/research/43, R5), so both values are
# assumptions and are labelled as such.
SMOOTHBORE_1775 = WeaponEntry(
    range_hexes=2,
    effect_pct=60,
    basis="assumption: 100 m (2 hexes) and 60% of the rifled-musket effect; "
          "no source read gives smoothbore range or accuracy (docs/research/47)",
)
WEAPONS_1775 = {"smoothbore muskets": SMOOTHBORE_1775}


def _count(value, low=0):
    return type(value) is int and value >= low


def command_problems(entry):
    """Why: a succession list the rules cannot follow must fail at registration.
    What: problems with ``entry.command``: every side of the list is a
    scenario side, every successor a unit of that side other than its
    command unit and listed once; ``officers`` (the default and every unit
    override) is a positive integer, the other counts non-negative integers.
    Test: `test_registration_refuses_bad_command_data`,
    `test_registration_refuses_units_without_an_officer`."""
    command, problems = entry.command, []
    # poc-13B review: a unit starts with at least one officer; only losses or
    # a split make it leaderless, so no unit starts orderable without one.
    for u in entry.units:
        if "officers" in u.overrides and not _count(u.overrides["officers"], 1):
            problems.append(f"unit {u.id!r} officers must be a positive integer")
    if command is None:
        return problems
    if not _count(command.officers, 1):
        problems.append("command officers must be a positive integer")
    if not all(_count(v) for v in (command.succession_delay, command.leaderless_morale)):
        problems.append("command succession_delay and leaderless_morale must be non-negative integers")
    sides = {u.id: u.side for u in entry.units}
    for side, successors in command.succession.items():
        if side not in entry.sides:
            problems.append(f"succession names unknown side {side!r}")
            continue
        successors = tuple(successors)
        if len(set(successors)) != len(successors) or entry.sides[side].command_unit in successors:
            problems.append(f"{side} succession must list each unit once and not its command unit")
        for uid in successors:
            if sides.get(uid) != side:
                problems.append(f"{side} succession names {uid!r}, which is not a {side} unit")
    return problems


def weapon_problems(entry):
    """``entry.weapons``: each class has an integer range of 1 to 5 hexes,
    an integer effect of 1 to 100 per cent and a basis."""
    problems = []
    for name, w in (entry.weapons or {}).items():
        if not (type(w.range_hexes) is int and 1 <= w.range_hexes <= MAX_FIRE_RANGE
                and type(w.effect_pct) is int and 1 <= w.effect_pct <= 100 and w.basis):
            problems.append(f"weapon {name!r} needs range_hexes 1-{MAX_FIRE_RANGE}, effect_pct 1-100 and a basis")
    return problems


def declares(entry):
    """True when ``entry`` uses any poc-13B rule data."""
    from . import comms

    reach = comms.PROFILES.get(entry.communications, {}).get("voice_reach")
    return bool(entry.command or entry.weapons or reach)


def setup(s, entry, units):
    """Store the entry's poc-13B rules in snapshot ``s``: ``command_rules``
    with each unit's ``officers`` and ``officer_step``, and ``weapon_rules``.
    Nothing is written for an entry without them, so earlier battles keep
    their snapshots."""
    if entry.command:
        rules = asdict(entry.command)
        rules["succession"] = {side: list(ids) for side, ids in entry.command.succession.items()}
        s["command_rules"] = rules
        s["command_vacancy"] = {}
        for u in units:
            u.setdefault("officers", entry.command.officers)
            u.update(officer_step=max(1, u["initial"] // (u["officers"] + 1)), officer_losses=0)
            s["friendly_reports"][u["side"]][u["id"]].update(officers=u["officers"])
    if entry.weapons:
        s["weapon_rules"] = {name: asdict(w) for name, w in entry.weapons.items()}
