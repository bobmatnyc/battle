# 55 — `tactics_v11`: the threat range reads the observed enemy's weapon

**Date:** 2026-11-06. **Requirement:** before Hill 223 and Gergovia ([34](34-six-era-command-tests.md)) can declare mixed weapon ranges, the local threat check must stop judging danger by the unit's own range alone ([48](48-concord-historical-orders-run.md) §1 open item; [53](53-pegasus-engine-and-data.md) row 5). The decision may depend only on enemies the unit observes, the observer rule of [54](54-pegasus-scenario-runs.md) §3.

## 1. The rule

`tactics_v10.threat_range` returns the unit's own `range_hexes` when the snapshot has a weapon table, else 5 ([47](47-poc13-part-b-command-and-smoothbore.md)). A unit with a 1-hex weapon therefore ignores a 3-hex enemy at 3 hexes and keeps moving into its fire.

`tactics_v11` (`battle/tactics_v11.py`) changes that one check. Everything else in `decide` is `tactics_v10` unchanged.

- **Which enemies count.** The contacts the unit itself observes this interval: the local sightings `recon.scan` passes to `decide` (within `observation_range` and in line of sight, `recon.sees`). Delivered headquarters contacts, other units' sightings and true positions are not read.
- **A contact's range** (`contact_range`). The range of the weapon class the observer has made out (`composition.weapons`, set by `recon.estimate` only at quality 80 or more within 2 hexes). A contact whose weapon is not established, or seen only as "long arms", counts at the longest range in the weapon table: the worst case the briefed rules allow. The enemy's true weapon class is not read.
- **The threat range** (`threat_range(s, u, contacts)`). Without a weapon table: 5 hexes, as before. With one: the longer of the unit's own range and the longest contact range among `contacts`. `decide` applies it per contact, so a contact is nearby when it is within the longer of the unit's range and its own range; a short-range contact is not made a threat by a long-range one elsewhere.
- **Unchanged.** Being fired upon still triggers a reaction at any range. The assault check, cover and withdrawal choices, and the 5-hex retreat, reconnaissance and rest checks in `orders.py` are as in `tactics_v10`.

Keeping the unit's own range as a floor is a design choice, not a sourced rule: without it a long-range unit would close inside its own reach before halting, which `tactics_v10` never did.

## 2. Observer basis

An enemy the unit cannot observe is not in its contacts and cannot change the decision. `test_a_hidden_longer_range_enemy_does_not_change_the_decision` builds two states that differ only in a 3-hex machine-gun unit 9 hexes off, beyond the 7-hex sight: both give the same `decide` result (`observe`) and a threat range of 1. Adding the true enemy roster's ranges to the maximum turns the second state's decision into `defend` and fails that test (checked on this branch, then restored).

The worst case for an unidentified contact reads only the snapshot's weapon table, which is rules data in both sides' briefing. It counts every class in the table, own side included; it does not reveal which classes the enemy fields.

## 3. Selection and the mixed-range guard

- `ScenarioEntry.tactics` is `None` (`tactics_v10`) or `"tactics_v11"`. Only an entry that names `tactics_v11` writes `s['tactics']`, and `orders.decide` serves `tactics_v11` only to a `poc-13` snapshot holding it. `build_state` refuses the key in an edition before `poc-13`.
- `scenario_command.weapon_problems`: an entry on `tactics_v10` still needs one `range_hexes` for every class (`test_mixed_ranges_are_refused_on_tactics_v10`). An entry on `tactics_v11` may declare mixed ranges (`test_mixed_ranges_are_accepted_on_tactics_v11`). On both, every unit's class must be in the table, so the unidentified worst case is the longest range any unit can fire (`test_tactics_v11_still_refuses_a_unit_outside_the_table`). Any other `tactics` value is refused.

## 4. Rules-edition decision

The work stays in `poc-13`, as in 47, 53 and 54: the new rule reads snapshot data (`tactics`) that only a new entry key writes, and no saved `poc-13` game holds it. `tactics_v10` is not edited and still serves every existing entry. No entry selects `tactics_v11` yet; Hill 223 and Gergovia are later tasks.

## 5. What stays unchanged (verified on this branch)

- `make test-poc`: 503 tests pass, including the seven `e165371` `poc-13` digests (`test_poc13b.py`), the `poc-12` digests and the Concord pins; no digest was edited.
- Headless runs before and after the change give the same winner, turn, event count, final strengths and an `identical` replay: Little Round Top (Union, turn 60), Hougoumont north gate (Allied, turn 60), Concord north bridge (provincial, turn 8), Pegasus Bridge (German, turn 5).

## 6. Tests

`apps/poc/tests/test_tactics_v11.py`, written to fail first: a short-range unit uses an identified enemy's longer range and halts for it where `tactics_v10` observes; an unidentified contact counts at the table's longest range; the unit's own longer range is kept; no weapon table gives 5; a hidden longer-range enemy does not change the decision; the snapshot names `tactics_v11` only when selected and the engine reacts by it only then; an edition before `poc-13` and an unknown tactics value are refused; mixed ranges refused on `tactics_v10`, accepted on `tactics_v11`; a unit outside the table still refused on `tactics_v11`.

## 7. Limits

- Identification is rare: `recon.estimate` names a weapon class only at high quality within 2 hexes, so most contacts count at the table's longest range. A scenario whose longest range belongs to a few units makes everyone cautious against every unidentified contact.
- The check is per unit and per interval. A unit does not remember a contact's weapon after it leaves sight, and headquarters' contact estimates are not read.
- Engine fire is unchanged: it still reaches at most 5 hexes and the unit's own range.
