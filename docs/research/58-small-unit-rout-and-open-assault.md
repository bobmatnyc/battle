# 58 — Declared rout threshold and assault in open ground

**Date:** 2026-11-06. **Requirement:** two engine gaps that Hill 223 and Gergovia share: the fixed 12-man rout threshold ([56](56-hill-223-scenario-plan.md) §10 gap 1, [57](57-gergovia-scenario-plan.md) §10 gap 2) and assault outside gated compounds (56 gap 4, 57 gap 4). This doc covers engine work and test fixtures only. No Hill 223 or Gergovia entry is added, and no existing entry declares either key.

Both are unit overrides on `UnitEntry.overrides`, checked by `battle/scenario_units.py`. A key reaches the snapshot only when an entry declares it on a unit.

## 1. Declared rout threshold (`rout_strength`)

- **Rule.** `engine.advance` routs a unit when its morale is below 28 or its strength is below its `rout_strength`. A unit without the key uses 12, as before.
- **Validation** (`scenario_units.problems`). The value is an integer, not a boolean, of 0 or more and below the unit's starting strength (its `strength` override, else the default 40). A unit therefore cannot rout before it loses a man. 0 means strength never routs the unit; morale still can.
- **Split and combine.** A unit that declares the key neither splits nor combines (`formations.declares_rout`). The request is refused, and so is a queued operation at execution. A split would copy one absolute threshold to two smaller halves, and a combine would keep only one unit's threshold. This follows the sapper precedent of [54](54-pegasus-scenario-runs.md). `formations.MIN_STRENGTH` (12) is unchanged, so a party under 24 men could not split anyway.
- **Not changed.** The morale threshold (28), the effect of losses on morale, and how a routed unit behaves.

## 2. Assault in open ground (`press_assault`)

Under `tactics_v11` ([55](55-tactics-v11-threat-range.md)) an unidentified contact counts at the weapon table's longest range. A unit on a `move` order therefore halts at its first unidentified contact. `tactics_v11.assault` exempts only a move into a gated compound.

- **Rule.** A unit that declares `press_assault: true` and is on a `move` order with a destination keeps its order (`continue`) when a contact is within threat range. It returns fire as it goes, the same treatment `assault` gives an attack on walls. The decision reads `Enemy within effective range; pressing the assault toward the objective and returning fire.`
- **Reactions are kept.** The press applies only when no withdrawal trigger holds: failing morale, pinning suppression, low ammunition, a depleted formation under fire, a much stronger credible enemy, or a withdrawal in progress. A routed unit still falls back. Without a move order, the unit defends or takes cover as before.
- **Observer basis.** `tactics_v11.presses` reads only the unit's own fields. The triggers read only the contacts the unit itself observes, so a hidden enemy cannot change the decision. `test_a_hidden_enemy_does_not_change_the_decision` builds two states that differ only in an 80-man enemy 9 hexes off, beyond sight. Both states give `continue`. When a ground-truth strength check was added to the press for a trial run, that test failed; the check was then removed.
- **Validation.** The value must be a boolean. Only an entry that selects `tactics_v11` may declare it, so `tactics_v10` entries are refused.
- **Not changed.** `tactics_v10`. The `tactics_v11` decisions of every unit without the key, the gated-compound assault included. The orders, the catalog and the UI. The key is scenario data that the player cannot set by order.

## 3. Rules edition and gating

The work stays in `poc-13`, as in [53](53-pegasus-engine-and-data.md) and 55. Both rules read unit keys that only a new entry writes, and no saved `poc-13` game holds them. `build_state` refuses either key in an edition before `poc-13` (`scenario_units.declares`).

## 4. Tests

- `apps/poc/tests/test_rout_strength.py`. A declared unit with 8 men does not rout at threshold 4 and routs at 3. An undeclared unit routs under 12 and not at 12. Registration refuses bad values. An edition before `poc-13` refuses the key. Split and combine are refused at request and at execution.
- `apps/poc/tests/test_press_assault.py`. Without the key the unit halts. With the key it presses, through the engine closes to 1 hex and fires, and still withdraws on failing morale or falls back when routed. A hidden enemy does not change the decision. The key is refused on `tactics_v10`, refused when it is not a boolean, and refused before `poc-13`. An undeclared snapshot carries no key.

All of these tests were written first and run red. Each test that pins old behaviour was also shown able to fail: the undeclared rout test fails when the default changes, and the hidden-enemy test fails when the press reads enemy truth.

## 5. Limits

- `rout_strength` is a fixed head count. It is not a fraction of the starting strength and does not change with officers or losses. Values belong to the scenario entry and are authored, not sourced.
- `press_assault` holds for the whole battle. No order or standing doctrine sets or clears it, and a new move order keeps it. Neither scenario design has chosen yet which units declare it.
- A pressing unit moves to its destination, not to the contact. Engine fire still decides what it hits.
