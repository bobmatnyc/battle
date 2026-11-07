"""1944 scenario data: bridge state, codeword signals and night observation.

Why: the Pegasus Bridge scenario (docs/research/52, gaps 1, 4 and 5) needs a
bridge that can be wired and blown, success codewords that travel as
reports, and a night observation range. Each is entry data the rules read
only when a snapshot carries it, so earlier battles play as before
(docs/research/53). Kept apart from ``scenario_entry`` for size.
What: the ``BridgeEntry`` and ``SignalEntry`` records, their registration
checks and the snapshot setup ``build_state`` calls.
"""

from dataclasses import dataclass

from . import grid

# docs/research/53: company radio in 1944, with voice and runner still used.
RADIO_COMMUNICATIONS = "wwii-1944-radio-v1"
BRIDGE_STATES = ("intact", "charges", "destroyed")
SIGNAL_CONDITIONS = ("taken",)
MAX_OBSERVATION_RANGE = 7  # grid.visible never sees beyond 7 hexes.


DEMOLITION_TRIGGERS = ("contact", "crossing")


@dataclass(frozen=True)
class DemolitionEntry:
    """A guard that fires a wired bridge, and an enemy that can clear the charges
    (docs/research/54), stored in the snapshot as ``bridge_demolition``.

    The charges are armed at the first interval start when ``trigger`` holds:
    ``contact``, a live, unrouted unit of ``side`` within ``reach`` hexes of the
    bridge sees an enemy unit (``recon.sees``); ``crossing``, an enemy unit
    stands on the bridge hex. ``delay`` intervals after arming, at the first
    interval start when a live, unrouted unit of ``side`` is still within
    ``reach`` (the firing party), the bridge is destroyed. Enemy units on the
    bridge hex clear the charges after ``removal_turns`` intervals there in
    all (the sappers' work); a cleared bridge is ``intact`` and cannot be
    fired. Authored sensitivity values, labelled by ``basis``.
    """

    side: str
    trigger: str
    delay: int
    reach: int = 1
    removal_turns: int = 2
    basis: str = "authored: demolition trigger and timings are POC choices"


@dataclass(frozen=True)
class BridgeEntry:
    """A bridge hex with a state (docs/research/53), stored in ``map_features``.

    ``pos`` is a water hex whose ``crossing`` is ``bridge``. ``state`` is
    ``intact``, ``charges`` (wired for demolition, still passable) or
    ``destroyed`` (impassable). ``schedule`` lists authored ``(turn, state)``
    changes, applied at the start of that interval: the scripted stand-in
    for a demolition or a removal of charges. ``demolition`` (None: none)
    triggers the firing from the battle instead (docs/research/54). ``basis``
    labels the values.
    """

    id: str
    name: str
    pos: tuple[int, int]
    state: str = "intact"
    schedule: tuple[tuple[int, str], ...] = ()
    basis: str = "authored: bridge state and schedule are POC choices"
    demolition: DemolitionEntry | None = None


@dataclass(frozen=True)
class SignalEntry:
    """A success codeword sent as a report (docs/research/53), stored in ``signals``.

    When a unit of ``side`` stands on bridge ``bridge`` while it is not
    destroyed, with no enemy unit within ``radius`` hexes (condition
    ``taken``), that unit sends ``codeword`` once to its command detachment
    by the ordinary report transport. ``meaning`` is the report's plain text.
    """

    codeword: str
    meaning: str
    side: str
    bridge: str
    condition: str = "taken"
    radius: int = 1
    basis: str = "authored: the trigger condition is a POC choice"


def _schedule_problems(b):
    turns = [t for t, _ in b.schedule]
    if not all(type(t) is int and t > 0 for t in turns) or turns != sorted(set(turns)):
        return [f"bridge {b.id!r} schedule turns must be positive integers in increasing order"]
    states = [b.state, *(state for _, state in b.schedule)]
    if any(state not in BRIDGE_STATES for state in states):
        return [f"bridge {b.id!r} states must be one of {BRIDGE_STATES}"]
    if "destroyed" in states[:-1]:
        return [f"bridge {b.id!r} schedule may not change a destroyed bridge"]
    return []


def _demolition_problems(entry, b):
    """docs/research/54: a demolition names a side, a known trigger, non-negative
    integer delay and reach, a positive clearing time, and a wired bridge."""
    d = b.demolition
    if d is None:
        return []
    counts = ((d.delay, 0), (d.reach, 0), (d.removal_turns, 1))
    if (d.side not in entry.sides or d.trigger not in DEMOLITION_TRIGGERS
            or not all(type(n) is int and n >= low for n, low in counts) or b.state != "charges"):
        return [f"bridge {b.id!r} demolition needs a scenario side, a trigger in {DEMOLITION_TRIGGERS}, "
                "non-negative integer delay and reach, removal_turns of 1 or more and a bridge wired with charges"]
    return []


def problems(entry):
    """Why: 1944 data the rules cannot run must fail at registration.
    What: problems with ``entry``'s bridges (unique ids, known states, a
    schedule in increasing turns that never revives a destroyed bridge, a
    demolition the rules can run: docs/research/54),
    signals (a scenario side, a declared bridge, a known condition, a
    non-negative integer radius, a codeword) and ``observation_range`` (an
    integer of 1 to 7). Terrain checks are in ``bridge_cell_problems``.
    Test: `test_registration_refuses_bad_bridge_data`,
    `test_registration_refuses_bad_demolition_data`,
    `test_registration_refuses_a_signal_for_an_unknown_bridge_or_side`,
    `test_registration_refuses_a_bad_observation_range`."""
    found = []
    bridges = entry.bridges or ()
    ids = [b.id for b in bridges]
    if len(set(ids)) != len(ids):
        found.append("bridge ids must be unique")
    for b in bridges:
        found.extend(_schedule_problems(b))
        found.extend(_demolition_problems(entry, b))
    for x in entry.signals or ():
        if (x.side not in entry.sides or x.bridge not in ids or x.condition not in SIGNAL_CONDITIONS
                or type(x.radius) is not int or x.radius < 0 or not x.codeword):
            found.append(f"signal {x.codeword!r} needs a scenario side, a declared bridge, a condition in "
                         f"{SIGNAL_CONDITIONS}, a non-negative integer radius and a codeword")
    r = entry.observation_range
    if r is not None and not (type(r) is int and 1 <= r <= MAX_OBSERVATION_RANGE):
        found.append(f"observation_range must be an integer of 1 to {MAX_OBSERVATION_RANGE} hexes")
    return found


def bridge_cell_problems(entry, cells):
    """Each declared bridge stands on a water hex whose crossing is a bridge."""
    return [f"bridge {b.id!r} at {b.pos} must be a water hex with a bridge crossing"
            for b in entry.bridges or ()
            if not grid.valid(list(b.pos)) or cells[grid.key(list(b.pos))].get("crossing") != "bridge"
            or not cells[grid.key(list(b.pos))].get("water")]


def declares(entry):
    """True when ``entry`` uses any 1944 rule data (docs/research/53)."""
    from . import comms

    radio = comms.PROFILES.get(entry.communications, {}).get("radio_range")
    return bool(entry.bridges or entry.signals or entry.observation_range is not None or radio)


def setup(s, entry, units):
    """Store ``entry``'s 1944 data in snapshot ``s``: each unit's night
    ``observation_range`` (a unit override wins), the bridges and the
    signals. Nothing is written for an entry without them."""
    from . import bridges, signals

    if entry.observation_range is not None:
        for u in units:
            u.setdefault("observation_range", entry.observation_range)
    if entry.bridges:
        bridges.setup(s, entry.bridges)
    if entry.signals:
        signals.setup(s, entry.signals)
