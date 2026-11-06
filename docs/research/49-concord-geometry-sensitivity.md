# 49 — Concord North Bridge: bridge geometry sensitivity

**Date:** 2026-11-06. **Requirement:** [48 §7 gap 11](48-concord-historical-orders-run.md#7-gaps-and-divergences) found that the authored bridge geometry drives the outcome. The owner's sequence asks for sensitivity, counterfactual and held-out checks so that tuning does not just fit the known winner. The Architect ordered this geometry check before any fire-release change. This document adds the variants, runs them, and states what the result implies. It changes no rule, parameter, policy or baseline entry.

Simulated values quote `python3 scripts/concord_sensitivity.py` and `python3 scripts/concord_timeline.py --variant NAME` (from `apps/poc`) at commit `303d619`.

## 1. The question

`BRIDGE` (12, 10) is on an even row of the odd-row grid. Its radius-1 ring has three west-bank hexes, (11, 9), (11, 10) and (11, 11), one east-bank hex, (13, 10), and two river hexes. `APPROACH` puts P1 to P3 on the three west-bank hexes. Only B1 stands in the ring. The capture rule (`victory.py:76`, `holding == {attacker}`) is met as soon as B1 leaves. The question: does the provincial hold survive when the ring is balanced or favours the east bank?

## 2. What was built

`battle/concord_sensitivity.py` holds a `Geometry`: the bridge, the river column on each row, the approach hexes, the start hexes, the headquarters and the town. `geometry_entry` builds an entry from the baseline `concord_entry` with that geometry. Given the baseline constants, it rebuilds the baseline terrain, roads, units, sides and victory exactly (`test_baseline_geometry_rebuilds_the_baseline_entry`).

Each variant is a `scenario_concord.Variant` in `SENSITIVITY`, separate from the doc 43 `VARIANTS`. Its `question` and `reading` start `sensitivity:`. Its `source` says what it keeps. Its entry carries the provenance note `authored: sensitivity: …`, not `reconstruction:`.

| Variant | Authored geometry it changes | Ring (west / east / river) | British in the ring at start |
|---|---|---|---|
| baseline `concord-north-bridge` | none | 3 / 1 / 2 | B1 |
| `sensitivity-odd-row-bridge` | every hex one row south: bridge (12, 11) on an odd row; approach, starts, headquarters, roads and town move with it | 1 / 3 / 2 | B1, B3 |
| `sensitivity-balanced-ring` | bridge (12, 10) kept; the river steps to column 11 below the bridge; P3's approach hex (11, 11), now river, moves to (10, 11). West-bank elevations on rows 11 and below drop by 2, because `_terrain` derives the slope from the river column | 2 / 2 / 2 | B1 |
| `sensitivity-balanced-ring-full` | as `sensitivity-balanced-ring`, and B3 moves from (13, 9) to (12, 11), the ring's second east-bank hex | 2 / 2 / 2 | B1, B3 |

**Kept in every variant:** the sourced date, place, forces (Acton about 40, about 400 provincials; three British companies, about 96), missions, Barrett's hold-fire order and the British open fire (S47, S48). The weapons (`WEAPONS_1775`, one range), communications, command, victory rules and every unit's strength and override are the baseline's.

**The option of all three British in the baseline ring is not built.** That ring has one east-bank land hex and the bridge hex, and `validate` refuses two units on one start hex. A third company could only start on the west bank, which is the doc 43 `british-west-bank` variant. Its run is in the table as a reference row.

**Policies.** `concord_policy.py` reads four module constants: `APPROACH`, `BRIDGE`, `EAST_END` and `TOWN`. A moved bridge needs moved targets. In the baseline ring, (11, 9) and (11, 11) are adjacent to (12, 9) and (12, 11), so no other river keeps them on the west bank with a different ring. `concord_sensitivity.rebind` therefore copies `militia_actions` and `regulars_actions` with the same code object and only those four names rebound. It raises if a copied function, its nested code or a helper it calls reads any other upper-case constant than `FRESH` and `CLEAR_RADIUS`, so a constant added to `concord_policy` later cannot run on baseline hexes unnoticed. Each variant names its copies, for example `scripted-concord-militia-v1@sensitivity-odd-row-bridge`. `command_policy` dispatches them. Bound to the baseline constants, a copy gives the baseline's orders (`test_rebound_policies_run_the_baseline_code`).

**Validation.** Every variant passes `validate` and `dry_run`, including `water_problems` (Concord has no building, so the compound and gateway check finds nothing to refuse). It uses `WEAPONS_1775` with one range. With the bridge made impassable, no route joins the two ends, so the river cuts the map. The variants are in no catalog: Concord stays headless only.

**Baseline unchanged.** `test_baseline_run_keeps_its_pinned_digest` pins the sha256 of the run summary without `game_id` and the saved final state, taken at `d6f1748` before this change. `test_baseline_timeline_is_the_same_under_two_hash_seeds` runs `concord_timeline.py` in two processes, under `PYTHONHASHSEED=1` and `2`, masks `game_id`, and asserts equal output with a pinned digest. One process has one hash seed, so the earlier replay test could not catch an order that depends on hashing; this test can. Changing B2's start hex makes both tests fail.

## 3. The runs

Full output of `python3 scripts/concord_sensitivity.py`. Each run uses its own temporary database. "Capture turn" is the turn the decisive hold began, the final turn minus `capture` plus 1. The ring lists effective units within radius 1 after that turn's movement, rebuilt from `unit_moved` events and checked against the saved final state.

```
== baseline concord-north-bridge
{'winner': 'provincial', 'turns': 8, 'events': 568, 'strength': {'P1': 39, 'P2': 120, 'P3': 120, 'P4': 120, 'B1': 29, 'B2': 32, 'B3': 32}, 'replay': {'revisions': 12, 'turns': 8, 'status': 'identical'}}
ring at start ['B1']
ring at capture turn 7 ['P1', 'P2', 'P3']
ring at end turn 8 ['P1', 'P2', 'P3']
losses {'british': '3/96', 'provincial': '1/400'}
checks {'british fire first': 'yes', 'provincials fire only when fired upon': 'yes', 'open-fire order set': 'yes', 'british withdraw': 'yes', 'militia hold the bridge': 'yes'}
approach hexes within 2 of B1 ['P1', 'P2', 'P3']
end provincial 8 The attackers held the bridge uncontested for 60 seconds. sides in ring at end ['provincial']
== sensitivity-odd-row-bridge
{'winner': 'british', 'turns': 20, 'events': 1419, 'strength': {'P1': 31, 'P2': 120, 'P3': 120, 'P4': 120, 'B1': 22, 'B2': 32, 'B3': 32}, 'replay': {'revisions': 25, 'turns': 20, 'status': 'identical'}}
ring at start ['B1', 'B3']
ring at end turn 20 ['B1', 'P1']
losses {'british': '10/96', 'provincial': '9/400'}
checks {'british fire first': 'yes', 'provincials fire only when fired upon': 'yes', 'open-fire order set': 'yes', 'british withdraw': 'yes', 'militia hold the bridge': 'no'}
approach hexes within 2 of B1 ['P1']
end british 20 The British held out until the scenario deadline. sides in ring at end ['british', 'provincial']
== sensitivity-balanced-ring
{'winner': 'provincial', 'turns': 8, 'events': 576, 'strength': {'P1': 39, 'P2': 120, 'P3': 120, 'P4': 120, 'B1': 31, 'B2': 32, 'B3': 32}, 'replay': {'revisions': 12, 'turns': 8, 'status': 'identical'}}
ring at start ['B1']
ring at capture turn 7 ['P1', 'P2']
ring at end turn 8 ['P1', 'P2']
losses {'british': '1/96', 'provincial': '1/400'}
checks {'british fire first': 'yes', 'provincials fire only when fired upon': 'yes', 'open-fire order set': 'yes', 'british withdraw': 'yes', 'militia hold the bridge': 'yes'}
approach hexes within 2 of B1 ['P1', 'P2']
end provincial 8 The attackers held the bridge uncontested for 60 seconds. sides in ring at end ['provincial']
== sensitivity-balanced-ring-full
{'winner': 'provincial', 'turns': 9, 'events': 689, 'strength': {'P1': 37, 'P2': 120, 'P3': 120, 'P4': 120, 'B1': 30, 'B2': 32, 'B3': 28}, 'replay': {'revisions': 13, 'turns': 9, 'status': 'identical'}}
ring at start ['B1', 'B3']
ring at capture turn 8 ['P1', 'P2']
ring at end turn 9 ['P1', 'P2']
losses {'british': '6/96', 'provincial': '3/400'}
checks {'british fire first': 'yes', 'provincials fire only when fired upon': 'yes', 'open-fire order set': 'yes', 'british withdraw': 'yes', 'militia hold the bridge': 'yes'}
approach hexes within 2 of B1 ['P1', 'P2']
end provincial 9 The attackers held the bridge uncontested for 60 seconds. sides in ring at end ['provincial']
== british-west-bank (doc 43 variant, reference)
{'winner': 'provincial', 'turns': 20, 'events': 1450, 'strength': {'P1': 35, 'P2': 116, 'P3': 120, 'P4': 120, 'B1': 0, 'B2': 23, 'B3': 0}, 'replay': {'revisions': 24, 'turns': 20, 'status': 'identical'}}
ring at start ['B1', 'B2', 'B3']
ring at capture turn 19 ['P1', 'P2', 'P3']
ring at end turn 20 ['P1', 'P2', 'P3']
losses {'british': '73/96', 'provincial': '9/400'}
checks {'british fire first': 'yes', 'provincials fire only when fired upon': 'yes', 'open-fire order set': 'yes', 'british withdraw': 'yes', 'militia hold the bridge': 'yes'}
end provincial 20 The attackers held the bridge uncontested for 60 seconds. sides in ring at end ['provincial']
```

The British side of the odd-row run, from `python3 scripts/concord_timeline.py --variant sensitivity-odd-row-bridge`:

```
turn  5  local_decision    B1 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  5  local_decision    B3 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  6  local_decision    B3 withdraw: We are withdrawing because credible sightings indicate a much stronger enemy.
turn  6  unit_moved        B3 [13, 10] -> [14, 10]
turn 20  battle_ended      {'reason': 'The British held out until the scenario deadline.', 'winner': 'british'}
```

## 4. Before and after

The historical event checks are the five rows of [48 §6](48-concord-historical-orders-run.md#sequence-of-events) that the engine can show: the British fire first; the provincials fire only when fired upon (the first provincial volley comes after a British one and is `returning_fire`); Buttrick's open-fire order is set; the British withdraw; the militia hold the bridge.

| Run | Winner | End turn and reason | Ring at the capture turn | Losses, British / provincial | Historical sequence |
|---|---|---|---|---|---|
| baseline | provincial | 8: held the bridge uncontested for 60 seconds | turn 7: P1, P2, P3 | 3/96, 1/400 | holds: all five |
| `sensitivity-odd-row-bridge` | british | 20: held out until the deadline | none; at turn 20: B1, P1 | 10/96, 9/400 | breaks: four of five; B3 withdraws, B1 does not, no hold |
| `sensitivity-balanced-ring` | provincial | 8: held the bridge uncontested for 60 seconds | turn 7: P1, P2 | 1/96, 1/400 | holds: all five |
| `sensitivity-balanced-ring-full` | provincial | 9: held the bridge uncontested for 60 seconds | turn 8: P1, P2 | 6/96, 3/400 | holds: all five |
| `british-west-bank` (doc 43, reference) | provincial | 20: held the bridge uncontested for 60 seconds | turn 19: P1, P2, P3 | 73/96, 9/400 | holds: all five, but by destroying B1 and B3 |

## 5. What decides the hold

- **The count of ring hexes per bank does not decide it.** With two hexes a bank, the provincials hold at turn 8, and at turn 9 with two British companies in the ring.
- **Which west-bank hexes lie within musket range of B1 decides it.** The British guard leaves the ring by a local reaction, not by an order: `tactics_v10.decide` withdraws a unit when reliable contacts within its weapon range (2 hexes) are estimated at more than 2.5 times its strength (`enemy_ratio` of the `balanced` standing profile). B1 has 32 men. In the baseline and both balanced variants, two or three provincial companies (40 + 120 or more) stand on approach hexes within 2 hexes of B1, and B1 withdraws at turn 7. In the odd-row variant, P2 at (11, 10) and P3 at (11, 12) are 3 hexes from B1 at (13, 11). Only P1 (40) is in range, B1 never withdraws, and it fires on P1 until the deadline.
- **Moving every hex one row south is not a translation of the battlefield.** On this odd-row grid it changes hex distances: B1 to P2's approach hex is 2 in the baseline, (13, 10) to (11, 9), and 3 in the odd-row variant, (13, 11) to (11, 10). The variant changes no source fact, yet it turns a provincial hold at turn 8 into a British hold to the deadline. The provincial result therefore depends on the authored geometry: on the row parity of the bridge and the hex distances that parity gives the approach.

## 6. Conclusion

The provincial result depends on the authored ring geometry. It holds when the approach puts two or more provincial companies within 2 hexes of the British bridge-end company, and fails when it puts one. The record (S47) does not fix those hexes.

**For the next step.** The fire-release check ([48 §7 gap 1](48-concord-historical-orders-run.md#7-gaps-and-divergences)) cannot be judged on the baseline alone, because a geometry change with no source behind it flips the baseline's outcome. The variants in `SENSITIVITY` are held-out cases for that check: it should report the baseline and each variant, not only the run that matches the record.

## 7. Tests

`apps/poc/tests/test_concord_sensitivity.py`: the pinned baseline run digest; the baseline timeline under two hash seeds; the baseline geometry rebuilds the baseline entry; the variants are labelled `sensitivity` and state what they keep and change; each variant validates, dry-runs and keeps one musket range; the variants are headless only; the ring geometry of each variant and the river cut; the rebound policies share the baseline code; `rebind` refuses a function, or a helper it calls, that reads an upper-case constant it does not replace (only `FRESH` and `CLEAR_RADIUS` stay as the baseline has them); each variant names its rebound policies, whose `APPROACH`, `BRIDGE`, `EAST_END` and `TOWN` are the variant's; and one test per variant that it runs headless twice in separate databases with equal results and replays `identical`. No test asserts a winner.
