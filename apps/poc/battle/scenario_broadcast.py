"""Broadcast signal data for scenario entries (docs/research/60 §1).

Why: at Gergovia a trumpet recall reached the legion near Caesar and not the
legions across the valley (docs/research/57, VII.47). Orders are addressed
packets, so a signal that every unit in earshot hears needs its own record.
Each signal is entry data the rules read only when a snapshot carries it, so
earlier battles play as before. Kept apart from ``scenario_entry`` for size.
What: the ``BroadcastEntry`` record, its registration checks, ``declares``
(``build_state`` refuses signals before ``poc-13``) and the snapshot setup.
"""

from dataclasses import dataclass

from . import grid

BROADCAST_KINDS = ("recall",)
# Stances a recall may carry: withdraw to a hex, or hold where the unit stands.
BROADCAST_STANCES = ("retreat", "hold")


@dataclass(frozen=True)
class BroadcastEntry:
    """A signal sounded from a side's command detachment, stored in ``broadcasts``.

    It is sounded at the start of interval ``turn``, or, with ``turn`` None,
    at the start of the interval after the commander orders it (a ``signal``
    action). Every live unit of ``side`` other than the command detachment
    within ``reach`` hexes hears it, unless a hex of ``block_hexes`` lies
    strictly between the two on the grid line (a valley or other declared
    obstacle to sound). A unit that hears it takes up ``stance`` (and
    ``destination`` for ``retreat``) as its mission; a unit that does not
    hear it keeps its mission. ``kind`` ``recall`` also halts a declared
    exploit whose ``recall_binding`` is true (``standing.exploit``).
    ``meaning`` is the plain text; ``basis`` labels the values.
    """

    id: str
    side: str
    kind: str
    reach: int
    stance: str
    destination: tuple[int, int] | None
    meaning: str
    turn: int | None = None
    block_hexes: tuple[tuple[int, int], ...] = ()
    basis: str = "authored: signal reach, block and timing are POC choices"


def _hexes(value):
    try:
        return all(grid.valid(list(p)) for p in value)
    except TypeError:
        return False


def _signal_problems(entry, b):
    problems = []
    if not (isinstance(b.id, str) and b.id) or b.side not in entry.sides or b.kind not in BROADCAST_KINDS:
        problems.append(f"broadcast {b.id!r} needs an id, a scenario side and a kind of {BROADCAST_KINDS}")
    if not (type(b.reach) is int and 1 <= b.reach <= grid.COLS + grid.ROWS):
        problems.append(f"broadcast {b.id!r} reach must be a positive integer of hexes")
    if b.stance not in BROADCAST_STANCES:
        problems.append(f"broadcast {b.id!r} stance must be one of {BROADCAST_STANCES}")
    elif (b.stance == "retreat") != (b.destination is not None) or (
            b.destination is not None and not _hexes([b.destination])):
        problems.append(f"broadcast {b.id!r} retreat needs a destination hex on the grid; hold takes none")
    if b.turn is not None and not (type(b.turn) is int and 1 <= b.turn <= entry.victory.deadline_turns):
        problems.append(f"broadcast {b.id!r} turn must be None (by order) or an integer from 1 to the deadline")
    if not _hexes(b.block_hexes):
        problems.append(f"broadcast {b.id!r} block_hexes must be hexes on the grid")
    if not b.meaning or not b.basis:
        problems.append(f"broadcast {b.id!r} needs a meaning and a basis")
    return problems


def problems(entry):
    """Why: a signal the rules cannot sound must fail at registration.
    What: signals need a profile that declares ``broadcast`` (the Roman
    profile); ids are unique; each signal is checked by ``_signal_problems``.
    Test: `test_registration_refuses_bad_signals`, `test_signal_ids_are_unique`,
    `test_a_profile_without_signals_refuses_them`."""
    from . import comms

    signals = tuple(entry.broadcasts or ())
    if not signals:
        return []
    found = []
    if not comms.PROFILES.get(entry.communications, {}).get("broadcast"):
        found.append(f"broadcast signals need a profile that sounds them, not {entry.communications}")
    ids = [b.id for b in signals]
    if len(set(ids)) != len(ids):
        found.append("broadcast ids must be unique")
    for b in signals:
        found.extend(_signal_problems(entry, b))
    return found


def declares(entry):
    """True when ``entry`` declares a broadcast signal; ``build_state`` then
    refuses an edition before ``poc-13``.
    Test: `test_an_edition_before_poc_13_refuses_signals`."""
    return bool(entry.broadcasts)


def setup(s, entry):
    """Store the entry's signals in ``s['broadcasts']``, unsounded; nothing for an entry without them."""
    if not entry.broadcasts:
        return
    s["broadcasts"] = [{"id": b.id, "side": b.side, "kind": b.kind, "reach": b.reach, "stance": b.stance,
                        "destination": None if b.destination is None else list(b.destination),
                        "meaning": b.meaning, "turn": b.turn,
                        "block_hexes": [list(p) for p in b.block_hexes],
                        "ordered_turn": None, "sounded_turn": None, "sounder_id": None, "receipts": {}}
                       for b in entry.broadcasts]
