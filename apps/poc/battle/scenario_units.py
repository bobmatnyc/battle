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
# ``press_assault`` tactics_v11 presses only into a gated compound; without
# ``facing``, ``arc`` and ``reorient_turns`` a unit fires on every side
# (docs/research/59 §2); without ``surrender`` a unit never yields (§1).
FACING_KEYS = ("facing", "arc", "reorient_turns")
KEYS = ("rout_strength", "press_assault", "surrender") + FACING_KEYS
SURRENDER_FIELDS = ("odds_pct", "reach", "rear_only", "support_reach")


def _surrender_problems(u):
    """docs/research/59: a rule with exactly ``SURRENDER_FIELDS``: ``reach`` 1
    to 7 hexes (the sight cap), ``odds_pct`` 1 to 1000, ``support_reach`` 0 to
    7 and a boolean ``rear_only``, which needs a declared facing."""
    if "surrender" not in u.overrides:
        return []
    r = u.overrides["surrender"]
    if not (isinstance(r, dict) and tuple(sorted(r)) == SURRENDER_FIELDS and _int(r["reach"])
            and 1 <= r["reach"] <= 7 and _int(r["odds_pct"]) and 1 <= r["odds_pct"] <= 1000
            and _int(r["support_reach"]) and 0 <= r["support_reach"] <= 7 and type(r["rear_only"]) is bool):
        return [f"unit {u.id!r} surrender must have exactly {SURRENDER_FIELDS}: reach 1-7, odds_pct 1-1000, "
                "support_reach 0-7 and rear_only true or false"]
    if r["rear_only"] and "facing" not in u.overrides:
        return [f"unit {u.id!r} surrender rear_only needs a declared facing"]
    return []


def _facing_problems(u):
    """docs/research/59: all three facing keys or none; a bearing of 0 to 359,
    an arc of 1 to 359 degrees and a non-negative whole number of intervals."""
    declared = [k for k in FACING_KEYS if k in u.overrides]
    if not declared:
        return []
    if len(declared) != len(FACING_KEYS):
        return [f"unit {u.id!r} must declare facing, arc and reorient_turns together"]
    o = u.overrides
    if not (_int(o["facing"]) and 0 <= o["facing"] <= 359 and _int(o["arc"]) and 1 <= o["arc"] <= 359
            and _int(o["reorient_turns"]) and o["reorient_turns"] >= 0):
        return [f"unit {u.id!r} facing must be an integer bearing of 0 to 359, arc an integer of 1 to 359 "
                "degrees and reorient_turns an integer of 0 or more"]
    return []


def _int(value):
    return type(value) is int


def _starting_strength(u):
    from .scenario_entry import unit

    return u.overrides.get("strength", unit(u.id, u.side, u.name, list(u.pos))["strength"])


def problems(entry):
    """Why: a key the rules cannot use must fail at registration.
    What: each declared ``rout_strength`` is an integer (not a boolean) of 0
    or more and below the unit's starting strength, so the unit does not
    rout before it has lost a man; each declared ``press_assault`` is a
    boolean on an entry that selects tactics_v11, the only tactics edition
    that reads it; a facing is declared whole (``_facing_problems``); a
    surrender rule has every field in range (``_surrender_problems``).
    Test: `test_registration_refuses_a_bad_rout_strength`, `test_registration_refuses_a_bad_rule`,
    `test_the_threshold_is_compared_with_the_default_strength_when_none_is_set`,
    `test_refused_on_a_tactics_v10_entry`, `test_refused_unless_a_boolean`,
    `test_registration_refuses_bad_facing_values`, `test_the_three_keys_are_declared_together`."""
    found = []
    for u in entry.units:
        found.extend(_facing_problems(u))
        found.extend(_surrender_problems(u))
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
