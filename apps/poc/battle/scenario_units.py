"""Unit keys an entry may declare for small or assaulting units (docs/research/58).

Why: Hill 223 and Gergovia (docs/research/56 and 57, §10) field parties of 4
to 17 men, which the fixed 12-man rout check breaks at once. Each key is a
unit override written to the snapshot only by an entry that declares it, so
earlier battles and their digests are unchanged. Kept apart from
``scenario_entry`` for size.
What: the registration checks for the keys and ``declares``, which
``build_state`` uses to refuse them in an edition before ``poc-13``.
"""

# engine.advance: a unit without ``rout_strength`` routs below 12 men.
DEFAULT_ROUT_STRENGTH = 12


def _starting_strength(u):
    from .scenario_entry import unit

    return u.overrides.get("strength", unit(u.id, u.side, u.name, list(u.pos))["strength"])


def problems(entry):
    """Why: a threshold the rules cannot use must fail at registration.
    What: each declared ``rout_strength`` is an integer (not a boolean) of 0
    or more and below the unit's starting strength, so the unit does not
    rout before it has lost a man.
    Test: `test_registration_refuses_a_bad_rout_strength`,
    `test_the_threshold_is_compared_with_the_default_strength_when_none_is_set`."""
    found = []
    for u in entry.units:
        if "rout_strength" not in u.overrides:
            continue
        r = u.overrides["rout_strength"]
        start = _starting_strength(u)
        if not (type(r) is int and 0 <= r < start):
            found.append(f"unit {u.id!r} rout_strength must be an integer of 0 or more below its "
                         f"starting strength ({start}), not {r!r}")
    return found


def declares(entry):
    """True when any unit of ``entry`` declares ``rout_strength``."""
    return any("rout_strength" in u.overrides for u in entry.units)
