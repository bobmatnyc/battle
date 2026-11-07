"""The ``encircle`` victory kind and its enclosure measure (doc 63 §5, gap 7; docs/research/68).

Why: doc 36 asks whether local decisions produce an encirclement, and allows
a failed pincer; no other kind scores an enclosure. Kept apart from
``victory`` for size; registered in ``victory.KINDS``.
What: ``enclosure`` reads route geometry as ``experiments/cannae/
test_escape_routes.py`` does, on the live state: a unit is enclosed when no
path leads from its hex to an exit with enemy-held hexes, and hexes within
``zoc`` of an enemy, treated as blocked. ``Encircle`` scores it and records,
every interval, what doc 63 §5 asks to be recorded but not scored. Only an
entry that names the kind writes its fields, so every other battle scores as
before.
"""

from . import grid, recon
from .victory import INEFFECTIVE, HoldObjective, _seize_only_problems, _side_with_role, _starting_strength

KIND = "encircle"
FIELDS = (("exits", ()), ("pocket_units", ()), ("centre_units", ()), ("zoc", None), ("min_enclosed_pct", None),
          ("centre_break", None))
FLOW_CAP = 24  # Passage width counted up to the grid's width; wider is "open".
# Dd8 (Bob 2026-11-07): Q2 literal reading. Doc 63 §5's centre break wins "before that":
# only while enclosed and lost men are below min_enclosed_pct (doc 68 §8 q2). False: at any interval.
BREAK_ONLY_BELOW_SHARE = True


def encircle_only_problems(entry):
    """docs/research/68: the encircle fields belong to ``encircle``."""
    v = entry.victory
    if v.kind != KIND and any(getattr(v, name) != empty for name, empty in FIELDS):
        return [f"{v.kind} does not read {', '.join(name for name, _ in FIELDS)}; use {KIND}"]
    return []


def _blocked(cells, enemies, zoc):
    blocked = {grid.key(p) for p in enemies}
    ring = [list(p) for p in enemies]
    for _ in range(zoc):
        ring = [n for p in ring for n in grid.neighbors(p) if grid.key(n) not in blocked]
        blocked |= {grid.key(n) for n in ring}
    return blocked


def _open(cells, blocked, p):
    k = grid.key(p)
    return k not in blocked and grid.passable(cells[k])


def _flow(reach, sources, exits):
    """The number of hex-disjoint paths from ``sources`` to ``exits`` within
    ``reach`` (the open hexes connected to an exit), up to ``FLOW_CAP``: by
    Menger's theorem, the narrowest hex count across the passage. Unit-capacity
    maximum flow on split hexes (Edmonds-Karp)."""
    cap, out = {}, {}

    def edge(a, b):
        if (a, b) not in cap:
            out.setdefault(a, []).append(b)
            out.setdefault(b, []).append(a)
            cap.setdefault((b, a), 0)
        cap[(a, b)] = cap.get((a, b), 0) + 1

    for k in sorted(reach):
        edge((k, 0), (k, 1))
        for n in grid.neighbors([int(v) for v in k.split(",")]):
            if grid.key(n) in reach:
                edge((k, 1), (grid.key(n), 0))
    for k in sorted({grid.key(p) for p in sources} & set(reach)):
        edge("S", (k, 0))
    for k in sorted({grid.key(p) for p in exits} & set(reach)):
        edge((k, 1), "T")
    total = 0
    while total < FLOW_CAP:
        parent, frontier = {"S": None}, ["S"]
        while frontier and "T" not in parent:
            nxt = []
            for a in frontier:
                for b in out.get(a, ()):
                    if b not in parent and cap[(a, b)] > 0:
                        parent[b] = a
                        nxt.append(b)
            frontier = nxt
        if "T" not in parent:
            return total
        b = "T"
        while parent[b] is not None:
            a = parent[b]
            cap[(a, b)] -= 1
            cap[(b, a)] += 1
            b = a
        total += 1
    return total


def enclosure(cells, pocket, enemies, exits, zoc, flow=True):
    """Why: the pocket must be read from the ground, not from losses.
    What: for ``pocket`` (unit id -> hex), ``enemies`` (hexes) and ``exits``
    (hexes), returns ``(enclosed, open_exits, narrowest)``: the ids with no
    path to an exit over hexes neither held by an enemy nor within ``zoc``
    of one (the unit's own hex is exempt; standing on an open exit is out),
    the number of exits such a path reaches from at least one unit, and the
    narrowest hex count across those paths (``_flow``; 0 when none, None
    when ``flow`` is false).
    Test: `test_a_ring_of_enemies_encloses_and_a_gap_does_not`,
    `test_zoc_0_lets_a_unit_pass_between_two_enemies`."""
    blocked = _blocked(cells, enemies, zoc)
    reach, members = {}, {}  # Open hex -> its component's first exit; that exit -> the open exits in it.
    for e in exits:
        if not _open(cells, blocked, e):
            continue
        if grid.key(e) in reach:
            members[reach[grid.key(e)]] += 1
            continue
        label, order = grid.key(e), [list(e)]
        reach[label], members[label] = label, 1
        while order:
            p = order.pop()
            for n in grid.neighbors(p):
                if _open(cells, blocked, n) and grid.key(n) not in reach:
                    reach[grid.key(n)] = label
                    order.append(n)
    enclosed, labels, sources = [], set(), []
    for uid, pos in sorted(pocket.items()):
        around = [list(pos)] + grid.neighbors(list(pos))
        found = {reach[grid.key(p)] for p in around if grid.key(p) in reach}
        if not found:
            enclosed.append(uid)
            continue
        labels |= found
        sources += [p for p in around if grid.key(p) in reach]
    narrowest = _flow(reach, sources, exits) if flow else None
    return enclosed, sum(members[label] for label in labels), narrowest


def _live(u):
    return u["strength"] > 0 and u["status"] not in ("lost", "merged")


class Encircle:
    """Doc 63 §5 ``encircle``. Each interval a unit of ``pocket_units`` (the
    attacker's heavy infantry) is enclosed when ``enclosure`` finds no route
    from it to an ``exits`` hex. The defender wins at the deadline when the
    enclosed units' men plus the men the pocket units have lost reach
    ``min_enclosed_pct`` per cent (rounded up) of their starting strength;
    otherwise the attacker wins at the deadline ("army not enclosed"). The
    attacker wins at once when ``centre_break`` of ``centre_units`` (the
    defender's centre) are routed or lost, but only while enclosed and lost
    men are still below that share (``BREAK_ONLY_BELOW_SHARE``). Recorded, not scored, in
    ``s['victory']``: per interval ``record`` rows ``[turn, enclosed units,
    enclosed men, men lost, open exits, narrowest passage, pocket units in
    contact]``; ``closed_turn``, the first interval with an enclosed unit;
    ``known_closed_turn``, per side, the first interval its headquarters'
    delivered reports (``friendly_reports`` and contacts no older than
    ``recon.CONTACT_MAX_AGE``) show one; and ``exited``, each attacker unit's
    first interval and strength on an exit hex. The score reads the truth;
    ``s['victory']`` is in neither side's view. A reading of route geometry,
    not a historical result.
    Test: `test_the_centre_breaking_wins_for_the_attacker_at_once`,
    `test_the_centre_break_wins_only_while_enclosed_and_lost_are_below_the_share`,
    `test_an_enclosed_pocket_wins_for_the_defender_at_the_deadline`,
    `test_an_open_army_wins_for_the_attacker_at_the_deadline`,
    `test_headquarters_learn_of_the_pocket_from_reports_only`.
    """

    kind = KIND

    def problems(self, entry):
        problems = HoldObjective().ring_problems(entry)
        v = entry.victory
        sides = {u.id: u.side for u in entry.units}
        role = {spec.role: side for side, spec in entry.sides.items()}
        exits = [list(p) for p in v.exits]
        if not exits or len({tuple(p) for p in exits}) != len(exits) or not all(grid.valid(p) for p in exits):
            problems.append("encircle exits must be distinct hexes on the grid, at least one")
        for name, ids, side in (("pocket_units", v.pocket_units, role.get("attacker")),
                                ("centre_units", v.centre_units, role.get("defender"))):
            if not ids or len(set(ids)) != len(ids) or any(sides.get(i) != side for i in ids):
                problems.append(f"encircle {name} must be distinct {side} unit ids, at least one")
        if not (type(v.zoc) is int and 0 <= v.zoc <= 3):
            problems.append("encircle zoc must be an integer of 0 to 3")
        if not (type(v.min_enclosed_pct) is int and 1 <= v.min_enclosed_pct <= 100):
            problems.append("encircle min_enclosed_pct must be an integer of 1 to 100")
        if not (type(v.centre_break) is int and 1 <= v.centre_break <= max(1, len(v.centre_units))):
            problems.append("encircle centre_break must be an integer of 1 to the number of centre units")
        return problems + _seize_only_problems(entry)

    def setup(self, entry):
        v = entry.victory
        force = sum(_starting_strength(entry, uid) for uid in v.pocket_units)
        return {"kind": self.kind, "objective_name": v.objective_name, "exits": [list(p) for p in v.exits],
                "pocket_units": list(v.pocket_units), "centre_units": list(v.centre_units), "zoc": v.zoc,
                "force": force, "enclosed_needed": -(-force * v.min_enclosed_pct // 100),
                "centre_break": v.centre_break, "record": [], "closed_turn": None,
                "known_closed_turn": {side: None for side in entry.sides}, "exited": {}}

    def _known(self, s, v, attacker, defender):
        fresh = lambda c: s["turn"] - c["observed_turn"] <= recon.CONTACT_MAX_AGE
        for side in (attacker, defender):
            if v["known_closed_turn"][side] is not None:
                continue
            own = [u for u in s["friendly_reports"][side].values() if u.get("strength", 0) > 0
                   and u.get("status") not in INEFFECTIVE]
            seen = [c for c in s["contacts"][side].values() if fresh(c)]
            if side == attacker:
                pocket = {u["id"]: u["pos"] for u in own if u["id"] in v["pocket_units"]}
                enemies = [c["pos"] for c in seen]
            else:
                pocket = {c["id"]: c["pos"] for c in seen if c["id"] in v["pocket_units"]}
                enemies = [u["pos"] for u in own]
            if pocket and enclosure(s["cells"], pocket, enemies, v["exits"], v["zoc"], flow=False)[0]:
                v["known_closed_turn"][side] = s["turn"]

    def score(self, s):
        v = s["victory"]
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        names = {x["id"]: x["name"] for x in s["sides"]}
        units = {u["id"]: u for u in s["units"]}
        pocket = {uid: units[uid]["pos"] for uid in v["pocket_units"] if _live(units[uid])}
        enemies = [u["pos"] for u in s["units"] if u["side"] == defender and _live(u)]
        enclosed, open_exits, narrowest = enclosure(s["cells"], pocket, enemies, v["exits"], v["zoc"])
        men = sum(units[uid]["strength"] for uid in enclosed)
        lost = sum(units[uid]["initial"] - units[uid]["strength"] for uid in v["pocket_units"])
        contact = sum(1 for p in pocket.values() if any(grid.distance(p, e) <= 1 for e in enemies))
        v["record"].append([s["turn"], len(enclosed), men, lost, open_exits, narrowest, contact])
        if enclosed and v["closed_turn"] is None:
            v["closed_turn"] = s["turn"]
        self._known(s, v, attacker, defender)
        exits = {grid.key(p) for p in v["exits"]}
        for u in s["units"]:
            if u["side"] == attacker and _live(u) and grid.key(u["pos"]) in exits and u["id"] not in v["exited"]:
                v["exited"][u["id"]] = [s["turn"], u["strength"]]
        broken = [uid for uid in v["centre_units"] if units[uid]["status"] in INEFFECTIVE or units[uid]["strength"] <= 0]
        below = men + lost < v["enclosed_needed"] or not BREAK_ONLY_BELOW_SHARE  # Dd8 (Bob 2026-11-07): Q2
        if len(broken) >= v["centre_break"] and below:
            return attacker, (f"The {names[defender]} centre broke: {len(broken)} of its "
                              f"{len(v['centre_units'])} centre units routed or lost.")
        if s["turn"] < s["max_turns"]:
            return None, None
        if men + lost >= v["enclosed_needed"]:
            return defender, (f"The {names[attacker]} army was enclosed by the deadline: {men} men enclosed and "
                              f"{lost} lost, against the {v['enclosed_needed']} required.")
        return attacker, (f"The {names[attacker]} army was not enclosed by the deadline: {men} men enclosed and "
                          f"{lost} lost, short of the {v['enclosed_needed']} required.")
