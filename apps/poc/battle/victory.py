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


KINDS = {kind.kind: kind for kind in (HoldObjective(),)}


def score(s):
    """Scores the snapshot's own victory kind; see the module docstring."""
    return KINDS[s["victory"]["kind"]].score(s)
