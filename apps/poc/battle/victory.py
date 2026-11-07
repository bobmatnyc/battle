"""Victory kinds (poc-9): a scenario entry names one; the engine scores it.

Why: later battles end in other ways than holding one objective hex (a
courtyard held, a bridge seized and then held for relief), so the engine must
not hard-code Little Round Top's rule or its side ids.
What: ``KINDS`` maps a kind id to an object with three members:

- ``problems(entry)``: reasons a scenario entry cannot use this kind; the
  catalog refuses the entry at registration.
- ``setup(entry)``: the kind's parameters, stored in the snapshot as
  ``s['victory']`` so replay never needs the catalog.
- ``score(s)``: called once at the end of every poc-9 interval. It may update
  only the kind's own counters in ``s`` and returns ``(winner, reason)``, with
  ``winner`` None while the battle goes on. Pure: snapshot in, snapshot out.

A new kind changes rule effects, so it needs a new rules edition (AGENTS.md).
``hold-compound`` arrived with poc-10 and needs that edition's walled
compounds; no earlier snapshot can name it. ``seize-and-hold`` stays in
poc-13 under docs/research/53's rule: only the new Pegasus entry names it,
so no saved snapshot holds it and every earlier battle scores as before
(docs/research/54). ``raid-and-return`` stays in poc-13 the same way: only an
entry that names it writes its fields (docs/research/59), and the other kinds
refuse them. ``recover-force`` (docs/research/60) stays in poc-13 the same way.
Test: `test_victory_kinds_refuse_unknown_kinds_and_bad_roles`,
`test_little_round_top_poc9_plays_identically_to_poc8`.
"""

from . import grid

INEFFECTIVE = ("routed", "lost", "merged")


def _side_with_role(s, role):
    return next(x["id"] for x in s["sides"] if x["role"] == role)


class HoldObjective:
    """The poc-8 rule with the scenario's sides: the attacker wins by holding
    the ground within ``radius`` of the objective for ``hold_turns`` intervals
    with no effective defender there, or when the defender has no effective
    formation; the defender wins at the deadline or when the attacker has none.
    Little Round Top's reasons are unchanged byte for byte.
    """

    kind = "hold-objective"

    def problems(self, entry):
        return self.ring_problems(entry) + _seize_only_problems(entry)

    def ring_problems(self, entry):
        """The sides, radius, hold count and name checks seize-and-hold shares."""
        problems = []
        roles = sorted(spec.role for spec in entry.sides.values())
        if roles != ["attacker", "defender"]:
            problems.append("hold-objective needs exactly two sides: one defender, one attacker")
        v = entry.victory
        if type(v.radius) is not int or v.radius < 0:
            problems.append("hold-objective radius must be an integer of 0 or more")
        if type(v.hold_turns) is not int or v.hold_turns < 1:
            problems.append("hold-objective hold_turns must be a positive integer")
        if not v.objective_name:
            problems.append("hold-objective needs an objective_name for outcome reports")
        return problems

    def setup(self, entry):
        v = entry.victory
        return {
            "kind": self.kind,
            "radius": v.radius,
            "hold_turns": v.hold_turns,
            "objective_name": v.objective_name,
        }

    def score(self, s):
        v = s["victory"]
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        names = {x["id"]: x["name"] for x in s["sides"]}
        holding = {
            u["side"]
            for u in s["units"]
            if u["status"] not in INEFFECTIVE
            and grid.distance(u["pos"], s["objective"]) <= v["radius"]
        }
        s["capture"] = s["capture"] + 1 if holding == {attacker} else 0
        active = {
            side: any(u["side"] == side and u["status"] not in INEFFECTIVE for u in s["units"])
            for side in names
        }
        if not any(active.values()):
            return "draw", "Both commands lost combat effectiveness."
        if not active[defender]:
            return attacker, f"{names[defender]} formations can no longer hold the position."
        if not active[attacker]:
            return defender, "The attacking formations have broken."
        if s["capture"] >= v["hold_turns"]:
            seconds = v["hold_turns"] * s["seconds_per_turn"]
            return attacker, (
                f"The attackers held the {v['objective_name']} uncontested for {seconds} seconds."
            )
        if s["turn"] >= s["max_turns"]:
            return defender, f"The {names[defender]} held out until the scenario deadline."
        return None, None


def _walled_compound(entry):
    """The gated building whose compound holds the entry's objective, and
    that compound's hexes; None when there is none."""
    objective = list(entry.victory.objective)
    for b in entry.map.features.get("buildings", ()):
        compound = [list(p) for p in b.get("compound", [b["pos"]])]
        if b.get("openings") and objective in compound:
            return b, compound
    return None


class HoldCompound:
    """Courtyard possession (poc-10; docs/research/42): the attacker wins by
    holding the inside of a walled compound with at least one effective
    formation, and no effective defender inside, for ``hold_turns``
    consecutive intervals; the defender wins at the deadline. Either side
    also wins when the other has no effective formation left.

    The compound is the gated building whose compound holds the objective;
    its hexes are stored in the snapshot, so replay needs no catalog. Missing
    data fails closed: registration refuses the entry, and ``score`` raises
    rather than award a result from an incomplete snapshot.
    Test: `test_hold_compound_refuses_entries_without_a_walled_objective`,
    `test_hold_compound_fails_closed_on_missing_snapshot_data`,
    `test_hold_compound_attacker_wins_by_uncontested_possession`.
    """

    kind = "hold-compound"
    FIELDS = ("feature_id", "compound", "hold_turns", "objective_name")

    def problems(self, entry):
        problems = []
        roles = sorted(spec.role for spec in entry.sides.values())
        if roles != ["attacker", "defender"]:
            problems.append("hold-compound needs exactly two sides: one defender, one attacker")
        v = entry.victory
        if type(v.hold_turns) is not int or v.hold_turns < 1:
            problems.append("hold-compound hold_turns must be a positive integer")
        if not v.objective_name:
            problems.append("hold-compound needs an objective_name for outcome reports")
        if _walled_compound(entry) is None:
            problems.append("hold-compound objective must lie in a building compound with openings")
        return problems + _seize_only_problems(entry)

    def setup(self, entry):
        building, compound = _walled_compound(entry)
        v = entry.victory
        return {
            "kind": self.kind,
            "feature_id": building["id"],
            "compound": compound,
            "hold_turns": v.hold_turns,
            "objective_name": v.objective_name,
        }

    def score(self, s):
        v = s.get("victory") or {}
        missing = [f for f in self.FIELDS if not v.get(f)]
        if missing or type(v["hold_turns"]) is not int or v["hold_turns"] < 1 or not all(
            grid.valid(list(p)) for p in v["compound"]
        ):
            raise ValueError(f"hold-compound victory data is missing or invalid: {missing or 'values'}")
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        names = {x["id"]: x["name"] for x in s["sides"]}
        inside = {grid.key(p) for p in v["compound"]}
        holding = {
            u["side"]
            for u in s["units"]
            if u["status"] not in INEFFECTIVE and u["strength"] > 0 and grid.key(u["pos"]) in inside
        }
        s["capture"] = s["capture"] + 1 if holding == {attacker} else 0
        active = {
            side: any(u["side"] == side and u["status"] not in INEFFECTIVE for u in s["units"])
            for side in names
        }
        if not any(active.values()):
            return "draw", "Both commands lost combat effectiveness."
        if not active[defender]:
            return attacker, f"{names[defender]} formations can no longer hold the {v['objective_name']}."
        if not active[attacker]:
            return defender, "The attacking formations have broken."
        if s["capture"] >= v["hold_turns"]:
            seconds = v["hold_turns"] * s["seconds_per_turn"]
            return attacker, (
                f"The attackers held the inside of the {v['objective_name']} for {seconds} seconds "
                "with no effective defender within the walls."
            )
        if s["turn"] >= s["max_turns"]:
            return defender, (
                f"The {names[defender]} garrison held the {v['objective_name']} until the scenario deadline."
            )
        return None, None


def _seize_only_problems(entry):
    """docs/research/54: relief and further objectives belong to seize-and-hold."""
    v = entry.victory
    if v.relief_turn is not None or tuple(v.more_objectives):
        return [f"{v.kind} does not read relief_turn and more_objectives; use seize-and-hold"]
    return _raid_only_problems(entry)


RAID_FIELDS = (("raiders", ()), ("return_hex", None), ("return_radius", 0), ("return_strength", None),
               ("return_pct", None), ("min_captives", None))


def _raid_only_problems(entry):
    """docs/research/59: the raid fields belong to raid-and-return."""
    v = entry.victory
    if v.kind != RaidAndReturn.kind and any(getattr(v, name) != empty for name, empty in RAID_FIELDS):
        return [f"{v.kind} does not read {', '.join(name for name, _ in RAID_FIELDS)}; use raid-and-return"]
    return _recover_only_problems(entry)


RECOVER_FIELDS = (("recover_units", ()), ("rally_hex", None), ("rally_radius", 0), ("recover_strength", None),
                  ("recover_pct", None))


def _recover_only_problems(entry):
    """docs/research/60: the recovery fields belong to recover-force."""
    v = entry.victory
    if v.kind != RecoverForce.kind and any(getattr(v, name) != empty for name, empty in RECOVER_FIELDS):
        return [f"{v.kind} does not read {', '.join(name for name, _ in RECOVER_FIELDS)}; use recover-force"]
    return []


class SeizeAndHold:
    """Seize a crossing, then hold it until relieved (docs/research/52 §5, 54).

    The attacker seizes an objective by holding the ground within ``radius``
    of it for ``hold_turns`` intervals with no effective defender there (the
    ``hold-objective`` count, kept per objective). A seized objective stays
    seized while an effective attacker formation remains within ``radius``;
    when none does the seizure lapses and must be made again. The attacker
    wins at the first interval at or after ``relief_turn`` with every
    objective seized; with no relief, at the deadline with every objective
    seized. The defender wins at the deadline otherwise, or at once when a
    declared bridge on an objective is destroyed. Either side also wins when
    the other has no effective formation left. ``s['victory']`` holds the
    parameters plus the kind's own state: ``captures`` and ``seized`` (the
    turn each objective was seized, or None) and ``history`` (seized and
    lapsed records), so replay needs no catalog.
    Test: `test_seized_objective_held_until_relief_wins_at_the_relief_turn`,
    `test_seizure_lapses_when_no_attacker_remains_and_the_defender_wins_at_the_deadline`,
    `test_without_relief_the_seizure_must_last_to_the_deadline`,
    `test_destroyed_objective_bridge_is_a_defender_win`.
    """

    kind = "seize-and-hold"

    def problems(self, entry):
        problems = HoldObjective().ring_problems(entry)
        v = entry.victory
        if v.relief_turn is not None and not (type(v.relief_turn) is int and 1 <= v.relief_turn <= v.deadline_turns):
            problems.append("seize-and-hold relief_turn must be None or an integer from 1 to the deadline")
        objectives = [tuple(v.objective)] + [tuple(p) for p in v.more_objectives]
        if len(set(objectives)) != len(objectives) or not all(grid.valid(list(p)) for p in objectives):
            problems.append("seize-and-hold more_objectives must be distinct hexes on the grid")
        return problems + _raid_only_problems(entry)

    def setup(self, entry):
        v = entry.victory
        objectives = [list(v.objective)] + [list(p) for p in v.more_objectives]
        return {
            "kind": self.kind,
            "radius": v.radius,
            "hold_turns": v.hold_turns,
            "objective_name": v.objective_name,
            "objectives": objectives,
            "relief_turn": v.relief_turn,
            "captures": [0] * len(objectives),
            "seized": [None] * len(objectives),
            "history": [],
        }

    def score(self, s):
        v = s["victory"]
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        names = {x["id"]: x["name"] for x in s["sides"]}
        bridges = {tuple(f["pos"]): f for f in s.get("map_features", ()) if f.get("kind") == "bridge"}
        for p in v["objectives"]:
            bridge = bridges.get(tuple(p))
            if bridge and bridge["state"] == "destroyed":
                return defender, f"The {bridge['name']} was destroyed before it could be held."
        effective = [u for u in s["units"] if u["status"] not in INEFFECTIVE]
        for i, p in enumerate(v["objectives"]):
            near = {u["side"] for u in effective if grid.distance(u["pos"], p) <= v["radius"]}
            v["captures"][i] = v["captures"][i] + 1 if near == {attacker} else 0
            if v["seized"][i] is None and v["captures"][i] >= v["hold_turns"]:
                v["seized"][i] = s["turn"]
                v["history"].append({"objective": i, "event": "seized", "turn": s["turn"]})
            elif v["seized"][i] is not None and attacker not in near:
                v["seized"][i] = None
                v["history"].append({"objective": i, "event": "lapsed", "turn": s["turn"]})
        s["capture"] = min(v["captures"])
        active = {side: any(u["side"] == side for u in effective) for side in names}
        if not any(active.values()):
            return "draw", "Both commands lost combat effectiveness."
        if not active[defender]:
            return attacker, f"{names[defender]} formations can no longer hold the position."
        if not active[attacker]:
            return defender, "The attacking formations have broken."
        held = all(t is not None for t in v["seized"])
        relief = v["relief_turn"]
        if held and relief is not None and s["turn"] >= relief:
            return attacker, f"The attackers seized the {v['objective_name']} and held it until relieved."
        if s["turn"] >= s["max_turns"]:
            if held:
                return attacker, f"The attackers seized the {v['objective_name']} and held it to the deadline."
            return defender, f"The {names[defender]} kept the {v['objective_name']} from being held until the deadline."
        return None, None


def _starting_strength(entry, uid):
    from .scenario_entry import unit

    spec = next(u for u in entry.units if u.id == uid)
    return spec.overrides.get("strength", unit(spec.id, spec.side, spec.name, list(spec.pos))["strength"])


class RaidAndReturn:
    """Reach an objective, then bring the force back (docs/research/59 §3).

    The raid is made when an effective formation of ``raiders`` has stood
    within ``radius`` of the objective for ``hold_turns`` consecutive
    intervals (``raided_turn``). At any later interval, the attacker wins
    when the effective raiders within ``return_radius`` of ``return_hex``
    number at least ``return_needed`` men: ``return_strength``, or
    ``return_pct`` per cent (rounded up) of the raiders' starting strength
    (``force``). With ``min_captives`` set, those returned raiders must also
    hold at least that many captives (``s['captives']``, status ``held``).
    The defender wins when no raider is effective, or at the deadline. The
    score reads the truth; ``s['victory']`` is not in either side's view.
    Test: `test_raid_then_return_wins_for_the_attacker`,
    `test_too_few_returning_men_do_not_win`,
    `test_min_captives_counts_captives_held_by_the_returning_raiders`,
    `test_min_captives_is_refused_when_no_defender_declares_surrender`,
    `test_the_deadline_reason_names_the_unmet_condition`,
    `test_nothing_of_the_raid_state_reaches_either_view`.
    """

    kind = "raid-and-return"

    def problems(self, entry):
        problems = HoldObjective().ring_problems(entry)
        v = entry.victory
        units = {u.id: u.side for u in entry.units}
        attacker = next((side for side, spec in entry.sides.items() if spec.role == "attacker"), None)
        raiders = tuple(v.raiders)
        if not raiders or len(set(raiders)) != len(raiders) or any(units.get(r) != attacker for r in raiders):
            problems.append("raid-and-return raiders must be distinct attacker unit ids, at least one")
        if v.return_hex is None or not grid.valid(list(v.return_hex)):
            problems.append("raid-and-return return_hex must be a hex on the grid")
        if type(v.return_radius) is not int or v.return_radius < 0:
            problems.append("raid-and-return return_radius must be an integer of 0 or more")
        force = sum(_starting_strength(entry, r) for r in raiders if r in units)
        by_count = v.return_strength is not None
        if by_count == (v.return_pct is not None):
            problems.append("raid-and-return needs exactly one of return_strength and return_pct")
        elif by_count and not (type(v.return_strength) is int and 1 <= v.return_strength <= force):
            problems.append(f"raid-and-return return_strength must be an integer of 1 to the raiders' {force}")
        elif not by_count and not (type(v.return_pct) is int and 1 <= v.return_pct <= 100):
            problems.append("raid-and-return return_pct must be an integer of 1 to 100")
        if v.min_captives is not None and not (type(v.min_captives) is int and v.min_captives >= 1):
            problems.append("raid-and-return min_captives must be None or a positive integer")
        # bt-T02: captives come only from units that declare surrender (captives.check).
        elif v.min_captives is not None and not any(
                u.side != attacker and "surrender" in u.overrides for u in entry.units):
            problems.append("raid-and-return min_captives needs a defending unit that declares surrender")
        if v.relief_turn is not None or tuple(v.more_objectives):
            problems.append("raid-and-return does not read relief_turn and more_objectives; use seize-and-hold")
        return problems + _recover_only_problems(entry)

    def setup(self, entry):
        v = entry.victory
        force = sum(_starting_strength(entry, r) for r in v.raiders)
        needed = v.return_strength if v.return_strength is not None else -(-force * v.return_pct // 100)
        return {
            "kind": self.kind,
            "objective": list(v.objective),
            "radius": v.radius,
            "hold_turns": v.hold_turns,
            "objective_name": v.objective_name,
            "raiders": list(v.raiders),
            "force": force,
            "return_hex": list(v.return_hex),
            "return_radius": v.return_radius,
            "return_needed": needed,
            "min_captives": v.min_captives,
            "captures": 0,
            "raided_turn": None,
        }

    def score(self, s):
        v = s["victory"]
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        names = {x["id"]: x["name"] for x in s["sides"]}
        raiders = [u for u in s["units"] if u["id"] in v["raiders"]
                   and u["status"] not in INEFFECTIVE and u["strength"] > 0]
        if v["raided_turn"] is None:
            near = any(grid.distance(u["pos"], v["objective"]) <= v["radius"] for u in raiders)
            v["captures"] = v["captures"] + 1 if near else 0
            if v["captures"] >= v["hold_turns"]:
                v["raided_turn"] = s["turn"]
        elif s["turn"] > v["raided_turn"]:
            men, held = _returned(s, v, raiders)
            if men >= v["return_needed"] and (v["min_captives"] is None or held >= v["min_captives"]):
                brought = f" They brought back {held} captives." if v["min_captives"] is not None else ""
                return attacker, (f"The raiders reached the {v['objective_name']} and {men} of them came back "
                                  f"by the deadline.{brought}")
        if not raiders:
            return defender, "The raiding force is no longer effective."
        if s["turn"] >= s["max_turns"]:
            return defender, _deadline_reason(s, v, raiders, names[defender])
        return None, None


def _returned(s, v, raiders):
    """Men of the effective ``raiders`` within ``return_radius`` of
    ``return_hex``, and the captives those men hold (status ``held``)."""
    home = [u for u in raiders if grid.distance(u["pos"], v["return_hex"]) <= v["return_radius"]]
    ids = {u["id"] for u in home}
    held = sum(k["count"] for k in s.get("captives", ()) if k["status"] == "held" and k["holder_id"] in ids)
    return sum(u["strength"] for u in home), held


def _deadline_reason(s, v, raiders, defender):
    """Why: the deadline reason must name the condition the raid missed.
    What: reads the counters ``score`` reads: no raid, no man home (the
    poc-13 text), too few men home, or too few captives held.
    Test: `test_the_deadline_reason_names_the_unmet_condition`,
    `test_raid_and_return_scores_the_entrys_raid`."""
    # Architect 2026-11-07 14:47Z: name the unmet win conditions, not "kept from returning" alone.
    if v["raided_turn"] is None:
        return f"The {defender} kept the raiders from reaching the {v['objective_name']} by the deadline."
    men, held = _returned(s, v, raiders)
    needed, wanted = v["return_needed"], v["min_captives"]
    short = wanted is not None and held < wanted
    if men == 0 or (men >= needed and not short):
        return f"The {defender} kept the raiders from returning by the deadline."
    captives = f"they brought back {held} captives against the {wanted} required"
    if men >= needed:
        return (f"The raiders reached the {v['objective_name']} and {men} of them came back by the deadline, "
                f"but {captives}.")
    return (f"The raiders reached the {v['objective_name']}, but only {men} of them came back by the deadline "
            f"against the {needed} needed" + (f", and {captives}." if short else "."))


def _needed(entry, force):
    v = entry.victory
    return v.recover_strength if v.recover_strength is not None else -(-force * v.recover_pct // 100)


class RecoverForce:
    """Bring a declared share of a forward force back to a rally area
    (docs/research/57 §5, 60 §3).

    The attacker wins at the first interval at which the effective formations
    of ``recover_units`` within ``rally_radius`` of ``rally_hex`` number at
    least ``recover_needed`` men: ``recover_strength``, or ``recover_pct``
    per cent (rounded up) of the force's starting strength (``force``). The
    defender wins when the force's effective men fall below that number, or
    at the deadline. Registration refuses a force that would already be
    recovered at the start. The score reads the truth; ``s['victory']`` is in
    neither side's view. The attacker's win reads "force recovered", not a
    historical result.
    Test: `test_bringing_the_force_back_wins_for_the_attacker`,
    `test_too_few_returning_men_do_not_win`,
    `test_the_defender_wins_when_the_force_can_no_longer_bring_back_enough`,
    `test_nothing_of_the_recovery_state_reaches_either_view`.
    """

    kind = "recover-force"

    def problems(self, entry):
        problems = HoldObjective().ring_problems(entry)
        v = entry.victory
        units = {u.id: u for u in entry.units}
        attacker = next((side for side, spec in entry.sides.items() if spec.role == "attacker"), None)
        ids = tuple(v.recover_units)
        if not ids or len(set(ids)) != len(ids) or any(units.get(r) is None or units[r].side != attacker for r in ids):
            return problems + ["recover-force recover_units must be distinct attacker unit ids, at least one"]
        if v.rally_hex is None or not grid.valid(list(v.rally_hex)):
            return problems + ["recover-force rally_hex must be a hex on the grid"]
        if type(v.rally_radius) is not int or v.rally_radius < 0:
            problems.append("recover-force rally_radius must be an integer of 0 or more")
        force = sum(_starting_strength(entry, r) for r in ids)
        by_count = v.recover_strength is not None
        if by_count == (v.recover_pct is not None):
            problems.append("recover-force needs exactly one of recover_strength and recover_pct")
        elif by_count and not (type(v.recover_strength) is int and 1 <= v.recover_strength <= force):
            problems.append(f"recover-force recover_strength must be an integer of 1 to the force's {force}")
        elif not by_count and not (type(v.recover_pct) is int and 1 <= v.recover_pct <= 100):
            problems.append("recover-force recover_pct must be an integer of 1 to 100")
        elif type(v.rally_radius) is int:
            home = sum(_starting_strength(entry, r) for r in ids
                       if grid.distance(list(units[r].pos), list(v.rally_hex)) <= v.rally_radius)
            if home >= _needed(entry, force):
                problems.append("recover-force force already stands recovered at the start")
        return problems + _seize_only_problems(entry)

    def setup(self, entry):
        v = entry.victory
        force = sum(_starting_strength(entry, r) for r in v.recover_units)
        return {
            "kind": self.kind,
            "objective_name": v.objective_name,
            "recover_units": list(v.recover_units),
            "force": force,
            "rally_hex": list(v.rally_hex),
            "rally_radius": v.rally_radius,
            "recover_needed": _needed(entry, force),
            "recovered_turn": None,
        }

    def score(self, s):
        v = s["victory"]
        defender = _side_with_role(s, "defender")
        attacker = _side_with_role(s, "attacker")
        force = [u for u in s["units"] if u["id"] in v["recover_units"]
                 and u["status"] not in INEFFECTIVE and u["strength"] > 0]
        men = sum(u["strength"] for u in force if grid.distance(u["pos"], v["rally_hex"]) <= v["rally_radius"])
        if men >= v["recover_needed"]:
            v["recovered_turn"] = s["turn"]
            return attacker, f"The commander brought {men} of the forward force back to the rally point by the deadline."
        if sum(u["strength"] for u in force) < v["recover_needed"]:
            return defender, "The forward force can no longer bring back the men required."
        if s["turn"] >= s["max_turns"]:
            return defender, "The forward force was not brought back to the rally point by the deadline."
        return None, None


KINDS = {kind.kind: kind for kind in (HoldObjective(), HoldCompound(), SeizeAndHold(), RaidAndReturn(),
                                     RecoverForce())}


def score(s):
    """Scores the snapshot's own victory kind; see the module docstring."""
    return KINDS[s["victory"]["kind"]].score(s)
