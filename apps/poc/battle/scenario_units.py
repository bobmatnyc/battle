"""Unit keys an entry may declare for small or assaulting units (docs/research/58).

Why: Hill 223 and Gergovia (docs/research/56 and 57, §10) field parties of 4
to 17 men, which the fixed 12-man rout check breaks at once, and assault in
open ground, where tactics_v11 halts a moving unit at its first unidentified
contact. Each key is a unit override written to the snapshot only by an
entry that declares it, so earlier battles and their digests are unchanged.
Kept apart from ``scenario_entry`` for size.
What: the registration checks for the keys and ``declares``, which
``build_state`` uses to refuse them in an edition before ``poc-13``.
"""

from .scenario_command import TACTICS_V11

# Without ``rout_strength`` a unit routs below 12 men (engine.advance); without
# ``press_assault`` tactics_v11 presses only into a gated compound.
KEYS = ("rout_strength", "press_assault")


def _starting_strength(u):
    from .scenario_entry import unit

    return u.overrides.get("strength", unit(u.id, u.side, u.name, list(u.pos))["strength"])


def problems(entry):
    """Why: a key the rules cannot use must fail at registration.
    What: each declared ``rout_strength`` is an integer (not a boolean) of 0
    or more and below the unit's starting strength, so the unit does not
    rout before it has lost a man; each declared ``press_assault`` is a
    boolean on an entry that selects tactics_v11, the only tactics edition
    that reads it.
    Test: `test_registration_refuses_a_bad_rout_strength`,
    `test_the_threshold_is_compared_with_the_default_strength_when_none_is_set`,
    `test_refused_on_a_tactics_v10_entry`, `test_refused_unless_a_boolean`."""
    found = []
    for u in entry.units:
        if "press_assault" in u.overrides and (type(u.overrides["press_assault"]) is not bool
                                               or entry.tactics != TACTICS_V11):
            found.append(f"unit {u.id!r} press_assault must be true or false, on an entry that selects "
                         f"{TACTICS_V11}")
        if "rout_strength" not in u.overrides:
            continue
        r = u.overrides["rout_strength"]
        start = _starting_strength(u)
        if not (type(r) is int and 0 <= r < start):
            found.append(f"unit {u.id!r} rout_strength must be an integer of 0 or more below its "
                         f"starting strength ({start}), not {r!r}")
    return found


def declares(entry):
    """True when any unit of ``entry`` declares one of ``KEYS``."""
    return any(key in u.overrides for u in entry.units for key in KEYS)
