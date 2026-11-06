# 45 — Contact rules (`poc-12`)

**Date:** 2026-11-06. **Requirement:** three approved changes to the rules of contact. (a) The gateway push of [44](44-poc11-gateway-push.md) destroyed a holder outright when no inside hex was free; grid capacity alone must not delete strength. (b) Two units wanting the same hex both waited every interval, for ever; the tie-break must be deterministic and fair. (c) Assault and gate-closing missions must not halt for an enemy within 5 hexes; self-preservation stays.

## Rules-edition decision

New games use `poc-12`. Saved `poc-1` to `poc-11` games keep their editions.

**What is frozen.** `battle/engine_v11.py` is `engine.py` at `fdd63c2`, byte for byte apart from its module docstring. `engine.py` routes `poc-11` states to it, and through it to the earlier engines. `battle/tactics_v9.py` is new; `tactics_v8.py` is unchanged and still serves `poc-8` to `poc-11` (`orders.decide` picks by edition). `gates.push` is shared: its `poc-11` branch keeps the old rule (nearest free compound hex at any distance, else overrun), and only `poc-12` states take the new one.

**Proof.** `tests/test_contact.py` pins five digests taken at `fdd63c2`: the scripted `poc-11` Little Round Top run; a `poc-11` Little Round Top save advanced 10 and then 30 intervals through `BattleService`; a `poc-11` Hougoumont save advanced 40 intervals through `BattleService`; the `poc-11` north-gate arrangement of 44 advanced 15 intervals; and the `poc-11` crowded-courtyard push (an overrun) advanced 4 intervals. All match, and the test checks that every `poc-11` service interval ran in `engine_v11.advance`. The JSON of all five states was written at `fdd63c2` and again on this branch and compared with `cmp`: identical. Replacing the `poc-11` branch of `gates.push` with the new rule makes the overrun digest fail, so the pin can detect a change.

## Rules (implemented)

| Area | Rule |
|---|---|
| (a) Give way | At the push threshold the holder steps back one hex: to a free compound hex beside the gateway, not across a wall, lowest hex first (`gates.step_back`). The lead pusher steps into the gateway as before. |
| (a) No room | When no hex beside the gateway is free, the push stalls: nobody moves, nobody loses strength, the effort stays at the threshold, and `gateway_push_stalled` (holder, pushers, effort, `reason: no_free_hex_beside_gateway`) records why, each interval. The push carries in the first interval such a hex is free. It still resets when nobody pushes. |
| (b) Contested hex | Of several units whose next step is the same free hex, the one refused most often since it last moved enters it; the lowest id wins a tie. Each other contender's `contest_wait` rises by one and it records `movement_blocked` with `reason: contested`, `winner_id` and `contest_wait`. Moving clears `contest_wait`. An occupied hex is refused as before, with no wait counted. (`engine.contest`) |
| (c) Assault | A unit on a `move` order whose destination lies in a gated compound, not yet reached, keeps `continue` when an enemy is within 5 hexes or it is under fire, instead of `defend` or `take cover`. Side does not matter, as for the push. (`tactics_v9.assault`) |
| (c) Unchanged | Any withdrawal trigger (morale floor, suppression limit, ammunition reserve, depletion, a much stronger enemy, a withdrawal in progress) still makes it withdraw; a routed unit still falls back; ordinary moves still halt; `close_gate` still holds at its work, as in 41. |

## Design choices

- **(a) Stall, not casualties.** The rules the engine has for casualties are fire, and nothing in the push models fighting. Converting the push into losses would invent a new combat result. Displacement already exists, and the stall reuses the pattern of `gate_blocked` in 41: the work is done, the outcome waits for the hex to clear. This is the smallest change that removes deletion and keeps strength conserved; fire still decides losses.
- **(a) One step only.** A displaced holder moves as any unit does: one hex, never through or onto another unit. The `poc-11` rule could put the holder two hexes back, past an occupied hex, which is a swap through a friendly unit that no movement rule allows. In the test fixture the back room is two hexes from the gateway behind the farm, so a full farm now stalls the push even with the back room free.
- **(a) Effort held at the threshold.** The attackers have done the work; holding it means the carry happens as soon as there is room, without repeating it.
- **(b) Longest-refused first.** Rotation by turn number is stateless, but a contest that recurs only on even turns would always go to the same unit. Counting refusals cannot starve: a loser's count rises and the winner's returns to 0, so among `n` contenders each unit enters within `n` contested intervals. Winners are fixed before any count changes, so the order in which proposals are read does not matter. A count is kept until the unit next moves, even if it stops contending.
- **(c) Destination decides.** The order says where the unit must go; a destination inside a gated compound is the purposeful assault (or, for the defender, the reinforcement of the walls). The gate-closing mission already overrode the halt in `orders.decide` and is not changed.

## Probes before the fix

`tests/test_contact.py`, run on this branch before each fix (edition plumbing in place, behaviour unchanged): 10 failures and 2 errors in 15 tests.

- (a) Crowded courtyard, holder 100 vs pusher 10, 10 vs 100, 40 vs 40: total strength fell by 100, 10 and 40 (`130 != 230`, `220 != 230`, `160 != 200`); the holder was overrun. Only the back room free: the holder went to `[9, 10]`, two hexes back (`[9, 10] != [11, 10]`). A stalled push that later finds room: carried to the back room, not the farm. In play: an `overrun` outcome at turn 2.
- (b) Two units and three units contending for the junction: no unit ever entered it (`[] != ['C1', 'C2']`, `[] != ['C1', 'C2', 'C3']`). The rotation test errored: `engine.contest` did not exist.
- (c) Assault ordered into the farm 4 hexes from the held gateway: `'defend' != 'continue'`, and after 4 intervals still at `[15, 10]`, not at the gate.
- Passing before and after, as they should: one free hex beside the gateway; an ordinary move halts; an assault with ammunition below its reserve withdraws; `poc-11` keeps the overrun, the deadlock and the halt.

## Outcome changes

**Little Round Top**, scripted run (`test_scenario_sides.play`). Only (b) applies: the map has no gates. Two contested hexes are resolved during the run. The outcome is unchanged: `union` wins at turn 60, "The Union held out until the scenario deadline." Final strengths change:

| Unit | `poc-11` | `poc-12` |
|---|---|---|
| U1 | 30 ready | 34 ready |
| U2 | 26 routed | 26 routed |
| U3 | 24 routed | 24 routed |
| C1 | 24 routed, 6,18 | 23 routed, 4,19 |
| C2 | 23 routed | 23 routed |
| C3 | 35 ready | 37 ready |

**Hougoumont**, both sides scripted and gate-aware, authored start: `french` wins at turn 40 (`poc-11`: turn 58), "Allied formations can no longer hold the farm." Replay is `identical` (44 revisions). Legros's party (F1) now presses on under fire from the walls at turn 1, falls from 30 to 12 in three intervals and routs at turn 3, short of the gate. Nobody reaches the outside hex while the gateway is held, so there is no push and no stall; the gate stays open, nobody is cut off, the capture counter stays at 0. The French win by fire from outside the walls, 18 turns sooner. Final strengths: A1 0 (lost), A2 39 (routed), A3 0 (lost), F1 1 (routed), F2 72, F3 23 (routed). The scripted French-player run gives the same result (54 revisions, `identical`).

**Engine-driven set-ups** in `test_hougoumont.py`, which are test arrangements, not scenario changes:

- *Gate closes with the French inside.* In `poc-12` F2 presses onto the outside hex, F1 wins the gateway hex both want and stands in it, and the gate stays `closing` and blocked through turn 12. In `poc-11` the two stalled over that hex and F1 stayed inside, so the gate shut and cut it off. The test is pinned to `poc-11`.
- *Gate attacker pushes after delivery.* In `poc-12` A1 and A2 no longer stall over one hex, so A1 leaves the gateway for cover at turn 2 and F1 walks in at turn 3 with no push. Pinned to `poc-11`.
- *Capture counter resets.* A2's move back into the walls presses on, so the counter resets after 4 intervals instead of 5.
- *Model French run.* The French get inside, and the gate defender policy gives A2 *Close the gate on a breach* at turn 9 as well as A1 at turn 0.

- *North-gate arrangement of 44* (not a test in `poc-12`): the French win at turn 11 with the capture counter at 6 (`poc-11`: turn 15). Legros's party pushes for one interval, then the gate party leaves the gateway and the French walk in; no gateway is carried.

The `poc-12` push is covered at the `gates.push` level and by the crowded-courtyard run in `test_contact.py`; the push tests of 44 stay on `poc-11`.

## Tests

`apps/poc/tests/test_contact.py`: the push stalls in a crowded courtyard with strength conserved for larger, smaller and equal holders; one free hex beside the gateway takes the holder, at no loss; displacement is one step to the nearest legal hex; a stalled push carries once a hex frees; in play the holder is never destroyed; `poc-11` keeps the overrun; two and three units contending for one hex all get through; priority rotates (C1, C2, C1, C2 and C1, C2, C3, C1, C2, C3) on repeated contests; `poc-11` contenders still wait; an assault continues within 5 hexes and reaches the gate under fire; an ordinary move halts; an assault below its ammunition reserve withdraws; a `poc-11` assault halts; new games use `poc-12`; the five `fdd63c2` digests.
