# 46 — River, fire discipline and contact age (`poc-13`, part A)

**Date:** 2026-11-06. **Requirement:** the rule prerequisites of the Concord North Bridge scenario ([43](43-concord-scenario-spec.md), R1 and R2), plus the stale-contact finding left open in [45](45-poc12-contact-rules.md). (1) Terrain can declare impassable water that blocks troops and couriers but not sight, crossed only at a bridge or ford. (2) A unit has a fire posture, `hold_fire` or `open_fire`, set by delivered orders; a unit holding fire returns fire once fired upon. (3) The assault check of `poc-12` reads headquarters contacts of any age; it must use the age limit of the commander view. Part A adds no Concord catalog entry.

## Rules-edition decision

New games use `poc-13`. Saved `poc-1` to `poc-12` games keep their editions.

**What is frozen.** `battle/engine_v12.py` is `engine.py` at `b2d93bd`, byte for byte apart from its module docstring. `engine.py` routes `poc-12` states to it, and through it to the earlier engines. `battle/tactics_v10.py` is new; `tactics_v9.py` is unchanged and still serves `poc-12` (`orders.decide` picks by edition). The shared modules change only in ways that are inert without the new data: `grid.passable` and `grid.path` read a `water` field that no earlier map has, and `build_state` refuses to build a map with water before `poc-13`. `orders.catalog` and `orders.available` add the fire orders only for `poc-13`. `orders.validate`, the retreat and reconnaissance fall-back in `orders.decide`, and the split check in `formations` refuse water hexes, which earlier maps do not have.

**Proof.** `tests/test_poc13.py` pins six digests taken at `b2d93bd`: the scripted `poc-12` Little Round Top run; a `poc-12` Little Round Top save advanced 10 and then 30 intervals through `BattleService` (it ends at turn 28); a `poc-12` Hougoumont save advanced 40 intervals through `BattleService` (it ends at turn 29); the `poc-12` north-gate arrangement of 44 (it ends at turn 12); the crowded-courtyard stall of 45 advanced 4 intervals; and the three-way corridor contest of 45 advanced 24 intervals. All match, and the test checks that every `poc-12` service interval ran in `engine_v12.advance`. The JSON of all six states was written at `b2d93bd` and again on this branch and compared with `cmp`: identical. Changing the suppression recovery in `engine_v12` from 8 to 9 makes the run digest fail, so the pin can detect a change.

## Rules (implemented)

| Area | Rule |
|---|---|
| (1) Water | A terrain cell may carry `water: true`. Such a hex is impassable (`grid.passable`), unless it also carries `crossing`, `bridge` or `ford`. `grid.path` never enters an impassable hex, so units, couriers and reports cannot cross. A move order to an impassable hex is refused. Withdrawal, cover and fall-back steps never choose one. |
| (1) Sight | Water does not change `grid.visible`. Units see, report and fire across it as before. |
| (1) Estimates | `engine.issue` always plans the courier over headquarters' known cells: the gate states it knows (`gates.known_cells`), else the briefed cells. The river is briefed terrain, so known and true water are the same. A recipient beyond water with no known crossing gets "expected delivery time unknown", not a one-interval guess. |
| (1) Registration | `dry_run` refuses `water` that is not `true`, a `crossing` that is not `bridge` or `ford` or that is not on a water cell, and any unit, headquarters, supply point or objective on impassable water (`scenario_checks.water_problems`). |
| (2) Posture | Each unit has `fire_posture`. The scenario entry's `FireEntry.default_posture` sets it (default `open_fire`); a unit override may name its own. The snapshot stores `fire_rules`. |
| (2) Orders | `hold_fire` and `open_fire` are order templates (catalog `common-orders-v5`, or `common-orders-v6` with a gate). They travel and are acknowledged like other orders. On delivery they set `fire_posture` and emit `fire_posture_set`. They keep the unit's stance, destination, mission and `order_version`. Two posture orders apply in version order (`fire_posture_version`). |
| (2) Fire | An `open_fire` unit fires as before. A `hold_fire` unit fires only when it was fired upon in the previous interval (its `casualties` event) or in this one. Fire in an interval is simultaneous: units that may fire do so first; then each holding unit that those volleys struck fires back at the nearest enemy in range, from the same pre-damage state. The set that returns fire is fixed before any return volley. A volley by a holding unit is marked `returning_fire`. |
| (2) Warning shots | Enemy fire that causes a unit no casualties in an interval is a warning shot. Whether it releases a holding unit is the authored flag `FireEntry.warning_shots_release`, default `false`. With the flag on, any enemy volley at the unit (`unit_under_fire`) releases it. |
| (2) Unchanged | Self-preservation is unchanged: a holding unit still halts, takes cover and withdraws as its standing orders say. |
| (2) Reports | `fire_posture` is in the unit summary, so headquarters sees it only in delivered friendly reports, as with any other field. The commander's own detachment is seen directly. |
| (3) Contact age | `tactics_v10.assault` counts a contact inside the compound only if it was observed at most `recon.CONTACT_MAX_AGE` (6) intervals ago, the limit `engine.view` uses. `poc-12` keeps `tactics_v9`, which reads contacts of any age. |

## Design choices

- **(1) A cell field, not walls.** Water is a property of the hex, like `move_cost`. A gate in [41](41-poc10-gates.md) is an edge with a changing state; the river does not change in part A. A cell flag needs one test in `grid.path`, and it gives the same result from every neighbour. The bridge is a water hex with `crossing`, so the map still shows it as part of the river.
- **(1) Known terrain.** The poc-10 pattern plans over what headquarters knows. In part A the river and its crossings are in the briefing and never change, so known and true cells agree. The planning call now always passes known cells, so a crossing that a later part can destroy or remove would need only a reported copy of the cell, as gates have.
- **(2) Casualties as the evidence.** "Fired upon" must come from something the unit observes. The engine already records two events per interval: `unit_under_fire` (any volley at the unit) and `casualties` (losses). Using these keeps the rule inside existing evidence. Concord's three British shots "splashed harmlessly into the river" (S47, through 43); whether such shots count is not settled by the sources, so it is a flag, and the default is the narrower reading.
- **(2) Current and previous interval.** Fire is simultaneous, so a unit fired upon in this interval would otherwise lose a full interval before replying. The second pass lets it reply in the same interval. Releasing on the previous interval as well means a unit that was hit keeps returning fire while the exchange continues, without a new state field.
- **(2) Posture separate from mission.** A posture order that replaced the stance would cancel a march. A separate version counter stops a posture order from superseding a movement order, and the reverse.
- **(3) One constant.** `recon.CONTACT_MAX_AGE` is the limit of the commander view, now read by both the view and the assault check, so they cannot drift apart.

## Probes before the fix

`tests/test_poc13.py`, run on a copy of the branch with the edition plumbing and the `FireEntry` data field only (`b213a13` plus the field): 10 failures and 5 errors in 17 tests.

- (1) No bridge: the unit walked into the river at `[5, 10]` and across it, and `grid.path` across returned `[[5, 10], [5, 9]]`, not `[]`. The courier estimate to a unit across the river was 3 intervals, not unknown. A move order into the water was accepted, and the bad water data registered. Bridge and ford: the unit crossed at `[4, 10]`, not at the bridge `[12, 10]`.
- (2) Two `hold_fire` units 3 hexes apart exchanged volleys at turn 1. With warning shots off, the holding unit fired although it had taken no casualties (`True != False`). The return-fire volley had no `returning_fire` mark (`KeyError`). The three order tests errored: `Choose an available order template.` A new game had no `fire_posture`.
- (3) A 7-interval-old contact still made the move an assault (`'continue' == 'continue'`).
- Passing before and after, as they should: a fresh contact makes an assault; `poc-12` reads contacts of any age; the warning-shot flag on; the `poc-12` digests.

## Outcome changes

None. Little Round Top and Hougoumont units start `open_fire`, and neither map has water or a scripted posture order, so `poc-13` plays as `poc-12`. Compared state by state, with the edition labels, `fire_rules`, `fire_posture` and the order catalogs in recorded observations set aside, these are identical between `poc-12` and `poc-13`: the scripted Little Round Top run (Union wins at turn 60, "The Union held out until the scenario deadline."); the Little Round Top service run of 40 steps (Confederates win at turn 28); the Hougoumont service run of 40 steps (French win at turn 29); and the north-gate arrangement (French win at turn 12). The headless runs on `poc-13`: Little Round Top, Union at turn 60; Hougoumont, Allied at turn 60; both replay `identical`.

The catalogs differ: every `poc-13` observation lists *Hold fire* and *Open fire*, so a model commander's prompt is longer, and its runs are not comparable with `poc-12` model runs.

## Tests

`apps/poc/tests/test_poc13.py`: no crossing without a bridge; a courier estimate across water is unknown; a unit crosses at a bridge and at a ford; sight and fire cross water that troops cannot; registration refuses bad water data and a river before `poc-13`; a move order into water is refused; `hold_fire` units do not fire first; a holding unit returns fire when fired upon; the warning-shot flag; a later `open_fire` order changes the posture, shown at headquarters after the report; the view shows the posture only as reported; registration refuses unknown postures; a posture order keeps the mission; a fresh contact still makes an assault; a 7-interval-old contact does not; `poc-12` reads contacts of any age; new games use `poc-13`; the six `b2d93bd` digests.

## Limits

- The river is static. Plank removal at Concord (S47: suggested, not confirmed) is not modelled.
- A holding unit returns fire at the nearest enemy in range, not necessarily at the unit that fired on it.
- Fire posture is not a standing-order choice and the scripted commanders never issue posture orders.
