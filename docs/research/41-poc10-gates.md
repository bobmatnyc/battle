# 41 — Building gates (`poc-10`)

**Date:** 2026-11-05. **Requirement:** the gate mechanism proposed for Hougoumont in [37, Option A](37-first-five-selection-register.md#option-a--model-the-gate-proposal), extending the building model of [24](24-map-features-and-digging-in.md). This change adds the mechanism and a test-only fixture. It adds no historical scenario.

## Rules-edition decision

New games use `poc-10`. Saved `poc-1` to `poc-9` games keep their editions and replay through frozen modules.

**What is frozen.** `battle/engine_v9.py` is the `poc-9` `engine.py` at commit `cb7faa0`, byte for byte apart from its module docstring. `engine.py` routes `poc-9` states to it, and through it to the earlier engines. As in [39](39-scenario-sides-and-victory-kinds.md#rules-edition-decision), the shared modules (`grid`, `features`, `orders`, `standing`, `analysis`) are not copied: each change is inert for a snapshot without gates, and only `poc-10` snapshots can have gates (`build_state` refuses openings in an earlier edition).

**Proof.** `tests/test_gates.py` pins two digests taken at `cb7faa0`: the scripted `poc-9` Little Round Top run, and a `poc-9` save advanced 10 and then 30 intervals through `BattleService`. Both still match. A `poc-10` Little Round Top game, with its labels read as `poc-9`, starts identical to the `poc-9` snapshot and ends on the same digest. The JSON of the advanced `poc-9` save was also compared with `cmp` against the file written at `cb7faa0`: identical. `make headless-poc` output, with the game id blanked, is identical to `cb7faa0`.

## Model (implemented)

| Area | Rule |
|---|---|
| Compound | A building feature may declare `compound` (its hexes, default its own hex) and `openings`. Every edge from a compound hex to a hex outside it is a wall. |
| Opening | `{id, name, inside, outside, state}`: the edge between the gateway hex `inside` (in the compound) and its neighbour `outside`. State is one of `open`, `closing`, `closed`, `barred`, `forced`, and belongs to the ground. |
| Movement and couriers | `open`, `closing` and `forced` openings can be crossed; walls, `closed` and `barred` openings cannot. Each cell stores the neighbours it is walled from (`walls`), and `grid.path` skips them, so troops and couriers obey the same edges. |
| *Close the gate* | Order template `close_gate` (catalog `common-orders-v4` = v3 plus this template), offered only in battles with a gate. It goes through normal authority, voice or courier delivery and acknowledgement. The receiving unit, if inside a compound, works on the nearest closable opening; outside a compound the mission fails locally. |
| Standing order | `close_on_breach` (`standing-orders-v2`, offered only in battles with a gate). Thresholds as *Hold ground firmly*. Delivered like any standing order. When an enemy unit is inside the compound and an opening can still be closed, the unit takes a local `close_gate` mission and reports it, with no courier from headquarters. |
| Labour | Per interval a party adds `min(strength, work_cap)`. `close_labour` takes the opening from `closing` to `closed`; a further `bar_labour` takes it to `barred`, which completes the mission. |
| Contact | Closing continues under fire; the party holds at its work. When the labour is done but an enemy unit stands in the gateway hex, the mission is `blocked` and a `gate_blocked` event names the units; it completes in the first interval the gateway is clear. |
| Forcing | Units on the outside hex of a `closed` gate whose ordered destination lies in the compound add `min(strength, work_cap)` each per interval. At `force_labour` the gate becomes `forced`. A `barred` gate cannot be forced. |
| Cut off | When a gate shuts and the compound has no passable opening, units of other sides than the closer's inside it are marked `cut_off`. They stay inside, cannot move or send couriers out, and a resupply mission to a depot outside fails locally. Their report of being cut off is a normal courier report, so it cannot leave the walls. A `forced` gate clears the mark. |
| Knowledge | Gate buildings are briefed in their initial state. A change is reported like fieldworks: a unit within three hexes with sight of the building reports it by voice or courier. Headquarters sees the change only on delivery, or at once when its own command detachment observes it. God Mode shows the current state. |
| Events | `gate_state` (feature, opening, before, after, unit, order version, labour, effort, pushers, units inside and on the outside hex), `gate_work`, `gate_blocked`, `standing_gate_close`, `units_cut_off`, `units_reconnected`. |

## Authored values

The scenario entry carries `gates: GateEntry(close_labour, bar_labour, force_labour, work_cap)`, stored in the snapshot as `gate_rules` with the label `basis: "authored POC sensitivity parameter; not a historical estimate"`. No source gives these numbers. Treat them as tuning parameters for the comparison ([37, open question 6](37-first-five-selection-register.md#6-open-questions-for-the-user)). An entry with openings must supply them, and an entry without openings must not. The test fixture uses 60, 40, 80 and 20: closing takes three intervals, barring two more, forcing four.

## Choices made where the spec was open

- **Gateway hex** is the opening's inside hex. An enemy on the outside hex does not block completion.
- **Push-back** ([37 item 5](37-first-five-selection-register.md#option-a--model-the-gate-proposal)) is not modelled: defenders inside do not subtract from forcing labour, and attackers outside do not slow closing.
- **Who pushes** is decided by intent, not side: a unit pushes when its ordered destination lies inside the compound. Gates have no owning side.
- **`closing` is passable**, so troops can still cross while the gate is being shut; this is what makes the gateway rule matter.
- **Re-closing** a `forced` gate starts its labour from zero. Closing labour adds no fatigue.
- **Sight** is unchanged: the building hex's obstacle height already blocks sight through the compound.
- **Cut-off** applies to every side other than the closing unit's side, at the moment the compound becomes sealed.

## Not done

No historical Hougoumont entry, courtyard-possession victory kind, browser drawing of walls and gate state, or Napoleonic voice and command profile. Split and combine can still place a new unit across a wall.

## Tests

`tests/test_gates.py`, on `tests/scenario_fixtures.gate_entry` (test-only, not in the player catalog): one test per transition (open→closing, closing→closed, closed→barred, closed→forced, forced→closing, and barred not forced), gateway contact under fire, cut-off with failed resupply and an undeliverable report and order, the standing order firing on a breach, delayed knowledge, entry validation, a headless run that replays `identical`, and the two `cb7faa0` digests.
