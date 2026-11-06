# 44 — Pushing through a held gateway (`poc-11`)

**Date:** 2026-11-06. **Requirement:** units cannot share a hex, so under [41](41-poc10-gates.md) one defender standing in an open gateway kept every attacker out, and the Hougoumont break-in ([42](42-hougoumont-scenario.md)) could not happen. The Architect approved option (a): attackers push through the gateway with authored effort. Concord rules are not part of this edition.

## Rules-edition decision

New games use `poc-11`. Saved `poc-1` to `poc-10` games keep their editions.

**What is frozen.** `battle/engine_v10.py` is `engine.py` at `2e773e5`, byte for byte apart from its module docstring. `engine.py` routes `poc-10` states to it, and through it to the earlier engines. The shared modules are not copied. The only shared change in behaviour is `gates.push`, which `engine_v10` never calls and which does nothing without `push_rules`; only `poc-11` snapshots carry them.

**Proof.** `tests/test_gateway_push.py` pins four digests taken at `2e773e5`: the scripted `poc-10` Little Round Top run; a `poc-10` Little Round Top save advanced 10 and then 30 intervals through `BattleService`; a `poc-10` Hougoumont save advanced 40 intervals through `BattleService`; and the `poc-10` north-gate arrangement below advanced 15 intervals. All match, and the `BattleService` test checks that every `poc-10` interval ran in `engine_v10.advance`. The JSON of both advanced saves was compared with `cmp` against files written at `2e773e5`: identical. A `poc-11` Little Round Top game, with its labels read as `poc-10`, starts identical to the `poc-10` snapshot and ends on the same digest.

## Rule (implemented)

| Area | Rule |
|---|---|
| Who pushes | A unit on the outside hex of an `open`, `closing` or `forced` opening whose ordered destination lies in the compound, not routed, lost or merged, when a unit of another side with strength above 0 holds the gateway hex. As with forcing, intent decides, not side. |
| Effort | After fire and gate labour, once per interval, the pushers add `min(strength, push_cap)` each. The effort is kept per opening in the snapshot's `push_effort`, not on the map feature. |
| Threshold | At `push_labour` the holder gives way. It moves to the free compound hex nearest the gateway (by distance, then hex). With no free hex it is overrun: strength 0, status `lost`. The lead pusher (lowest id) then steps into the gateway, and the effort returns to 0. |
| Interruption | Any interval in which nobody pushes resets the effort to 0 (`gateway_push_interrupted`): the pushers left the hex or broke, the holder left the gateway, or the gate shut. |
| Under fire | Fire does not stop the push. A pusher stays only while its local decisions keep it on the hex; a standing order that makes it withdraw interrupts the push. |
| Stacking | Unchanged. The holder moves only to a free hex, and the attacker enters only the gateway it vacated. |
| Knowledge | The holder and the lead attacker each send a normal physical report (`reaction`). The holder's courier travels from its new hex; an overrun unit sends none, as with any destroyed formation. Headquarters keeps its last delivered positions until a report arrives, and orders are addressed and estimated from them. `push_effort` is not in any commander view or feature report. |
| Events | `gateway_push` (holder, pushers, labour, effort, required, under fire), `gateway_push_interrupted`, `gateway_carried` (attacker, holder, `displaced` or `overrun`, holder's hex, losses), and `unit_moved` for the attacker. |

## Authored values

The entry carries `gateway_push: GatewayPushEntry(push_labour, push_cap)`, stored in the snapshot as `push_rules` with `basis: "authored sensitivity parameter; not a historical estimate"`. An entry with openings must supply it; an entry without openings must not. Hougoumont uses 60 and 20: a party of 20 or more carries a held gateway in 3 intervals, the time the gate party of 15 needs to shut the gate. The test fixture uses 40 and 20 (2 intervals). Hougoumont's `provenance` labels the field `authored:`.

## Choices made where the spec was open

- **Overrun, not partial loss.** "Reduced" is read as the holder destroyed: a partly reduced holder would still block the hex, and the attacker could not advance.
- **Nearest free hex** by hex distance from the gateway, then by hex coordinates. Walls inside a compound do not exist, so any compound hex is reachable.
- **No defender push-back.** Defenders do not subtract from the push, as attackers do not slow closing in 41.
- **The attacker's move costs no movement credit**; it gains the 3 fatigue of a normal step.
- **Effort is per opening, not per holder.** A fresh unit stepping into the gateway inherits the effort already spent; the effort resets only when nobody pushes.
- **The push is adjudicated after gate labour.** A gate that shuts in the same interval ends the push.

## Hougoumont outcomes (`poc-11`)

**Scripted run** (both sides scripted, `scripted-gate-defender-v1` for the Allies and `scripted-fallback-v1` for the French, authored start; superseded by the gate-aware attacker below): unchanged from `poc-10`. `allied` wins at turn 28, "The attacking formations have broken." No French unit reaches the gate's outside hex, so there is no push and no breach; the gate stays open, no unit is cut off, the capture counter stays at 0. Replay is `identical`.

**Engine-driven north-gate arrangement** (`test_french_carry_the_held_north_gate`): Legros's party on the outside hex and the follow-on companies near the gate, both ordered into the farm under *Hold ground firmly*; the gate party and A2 without cartridges; A3 away on the ridge; A1 under `close_on_breach`. Legros's party pushes 20 a turn and carries the gateway at turn 3, displacing the gate party to the château hex, which routs in the same interval and so never closes the gate. The French win at turn 15 with the capture counter at 6; the gate stays open and nobody is cut off. Replay is `identical`. In `poc-10` the same start never breaches by turn 15. These are test set-ups, not scenario changes.

**Observed limit.** With the authored garrison and its fire, the push seldom completes: in trial runs the French party withdrew under its standing order ("a much stronger enemy") or the holder left the gateway for cover before the third interval. The gate-closing sequence after a push (French inside, gate shut behind them) is therefore possible but not reached in these runs.

## Gate-aware scripted attacker

Under `scripted-fallback-v1` the French never reached the gate, so live runs with a model as the Allies met no assault. The attacker now has its own control, `scripted-gate-attacker-v1` (`command_policy.gate_attacker_actions`). It reads only the French headquarters view: reported positions, delivered contacts and orders in transit. Ties break by distance, then by id or hex.

- **Opening.** The known opening whose outside hex is nearest a live unit.
- **Assault group.** Two units: those already ordered into the compound first, then the nearest to the outside hex. Each gets the *Hold ground firmly* standing instruction once.
- **Lead.** Ordered to the gateway hex. The engine routes it to the outside hex, and once the order is delivered the push rule engages there. The second unit waits by the walls until the lead is inside, because two units moving into one hex both wait every interval.
- **Inside.** A unit reported inside holds. One in the gateway steps to a free compound hex, so the next can enter.
- **Support.** Other units hold a hex by the walls, or take the free one nearest them, as fire positions.
- At most three orders a decision. An order still in transit is not sent again.

**Selection.** `scripted_policy` gives the attacker of a gated entry `scripted-gate-attacker-v1`, as the computer side and as a scripted player side (`--player-side french`, which now runs under it instead of the fallback). `--opponent` and `--player-policy` accept it and refuse it for any other side or scenario ("needs the attacking side of a gated scenario"). Run metadata records it as `opponent` or `player_policy`. Its decisions carry `policy` and `standing` like the defender's. Replay applies the stored instructions and does not re-run the policy, so old saves replay unchanged. Other decisions keep their shape. `make headless-poc` output, game id and artifact path blanked, is byte-identical (`cmp`) to `e557d5d`.

**Outcome** (both sides scripted, both gate-aware, authored start): `french` wins at turn 58, "Allied formations can no longer hold the farm." Replay is `identical` (64 revisions). The gateway is never pushed, the gate stays open, no unit is cut off and the capture counter stays at 0. Final strengths: A1 0 (lost), A2 37 (routed), A3 0 (lost), F1 0 (lost), F2 69, F3 28. The French win by fire from outside the walls, not by entry. The scripted French-player run gives the same result (79 revisions, `identical`).

**Why no push.** The French are ordered in but halt short of the gate. `tactics.decide` stops a unit (*defend*, *take cover* or *withdraw*) whenever an enemy is within 5 hexes. The gateway hex can be seen from every hex north of the gate, so a unit cannot march onto the outside hex while the gateway is held. A push can start only from a unit that is already on the outside hex, or that gets there before the holder arrives. This is local-tactics behaviour, not a gate or push rule; this change does not alter it.

**Engine-driven tests** (`GateAttackerPolicyTests` in `test_hougoumont.py`): with the garrison out of sight, F1 marches from 11,5 to the outside hex and into the farm. With A1 holding the gateway and F1 on the outside hex, F1 pushes only from the turn its order is delivered, and it carries the gateway at turn 5. A defender that has truly moved but sent no report does not change the orders. Selection and refusal are covered through `build_headless` and the CLI. These are test set-ups, not scenario changes.

## Tests

`apps/poc/tests/test_gateway_push.py`: push accumulates under fire; the holder is displaced to the free back room at the threshold; it is overrun with no free hex; the push resets when the holder leaves the gateway; headquarters sees the old position, holds the report in transit and addresses a new order to the old hex until delivery; a stored push run replays `identical`; the scripted Hougoumont run; the north-gate arrangement; `poc-11` Little Round Top against the `poc-10` digest; `poc-10` saves through the frozen engine with three digests; the `poc-10` north-gate arrangement with no push; entry validation and the stored label.
