# 48 — Concord North Bridge: the historical orders against the record

**Date:** 2026-11-06. **Requirement:** the owner asked to "run Concord with the historical orders and compare the outcome. Make sure the musket range issue is addressed before tuning." This document records the Concord entry built from [43](43-concord-scenario-spec.md), the scripted historical-order run on `poc-13`, and its comparison with the record. It makes no tuning change. Tuning comes after this document is committed.

Historical claims cite S47 to S49 ([09 — sources](09-sources.md#concord-north-bridge-spec--2026-11-06)). Those pages were read through a summarising fetch ([43 §7](43-concord-scenario-spec.md#7-sources-used-in-this-pass)), so quoted phrases may be paraphrased. Simulated values quote the run output of `python3 scripts/concord_timeline.py` (from `apps/poc`), at commit `454b1a2`.

## 1. The musket range guard (finding)

- Concord and every variant use `WEAPONS_1775` only: one weapon class, `smoothbore muskets`, with one range, 2 hexes (100 m), and effect 60 per cent. Both values are assumptions ([47](47-poc13-part-b-command-and-smoothbore.md#values-sources-and-assumptions)).
- `tactics_v10.threat_range` uses the unit's own weapon range. With one range on the field, every unit halts on contacts at the distance at which the enemy can also fire. `test_musket_range_guard_one_weapon_range_only` refuses a Concord entry or variant with a second range or a unit outside the table. `SmoothboreApproachMechanicsCheck` (`tests/test_poc13b.py`) still passes.
- **Open item, not addressed:** with mixed ranges, a unit halts at its own range, not at the range of the enemy that can hit it. Concord does not need mixed ranges.

## 2. What was built (finding)

- **Entry** `concord-north-bridge` (`battle/scenario_concord.py`), edition `poc-13`, label `concord-north-bridge-v1`. It declares `command_rules` (two officers a company; successors P2, P3, P4 and B1, B3), `weapon_rules` (`WEAPONS_1775`), the `colonial-1775-voice-v1` communications (voice reach 2 hexes) and the `colonial-1775-en-v1` voice. Start 09:25, 30 seconds a turn, deadline 20 turns (09:35). Victory: `hold-objective` on the bridge, radius 1, 2 turns.
- **Forces.** Provincials: P1, the Acton minute company of 40 with the command, and three column detachments of 120 (P2 to P4), 400 in all. British: three light companies of 32 (B1 at the east end, B2 with Laurie, B3 north of the road), 96 in all.
- **Map.** Authored, not surveyed. The river is column 12, impassable water except the bridge hex (12, 10). The ridge rises west of it; the east bank is level ground toward the town. The bridge hex has three west-bank neighbours and one east-bank neighbour, a property of the odd-row grid.
- **Headless only.** The entry is in the headless catalog (`bootstrap.HEADLESS_SCENARIOS`), not on the command desk. The desk draws water as open ground (43 row 8), so a player would see no river.
- **Seed.** The engine draws no random number, and no seed parameter exists. The run is a function of the entry and the two policies. `test_headless_run_records_the_policies_and_replays_identically` runs it twice in separate temporary databases and asserts equal summaries, equal event digests and replay `identical`.

## 3. Reconstruction choices and variants

Each of the three open questions in [43 §6](43-concord-scenario-spec.md#6-open-questions-not-findings) takes the reading best supported by S47 to S49, labelled `reconstruction` in the entry's `provenance`. Each alternative is a variant in `scenario_concord.VARIANTS`. Each variant is a separate entry that validates, dry-runs and builds, but is not in any catalog. `scripts/concord_timeline.py --variant NAME` runs one.

| Question | Entry reading (provenance key) | Variant | Source locator |
|---|---|---|---|
| 1. Which bank | British on the town (east) bank, militia on the ridge west of it (`map.banks`). S47, S48 and S49 do not say. S47's ridge above the bridge and the first shots into the river put the forces on opposite banks. | `british-west-bank`: an authored counterfactual, the guard at the west end of the bridge with the river behind it. The sources are silent on the banks, so no source supports it either | S47, S48, S49 silent; web snippets not read (43 §6, unverified) |
| 2. Planks | Planks intact, bridge hex move cost 100 (`map.bridge`) | `planks-lifted`: bridge hex move cost 300. A fully lifted bridge would put the objective on impassable water, which `validate` refuses | S47: an officer suggested lifting them; not confirmed |
| 3. Companies | Three companies, about 96 (`units.british`) | `two-companies`: two of 45, about 90 | S47 three, about 96; S49 two, about 90 |

Other authored or reconstructed choices: the start minute (09:25), the split of the column into three detachments of 120, the approach hexes, and the command riding with Acton (S47, S48 place Buttrick and Davis at the head). Warning shots release no one (43 §6 question 5; `FireEntry` default). Reinforcements are left out: the grenadier companies and the 11:00 return (S47) arrive after the exchange, and `poc-13` has no arrival schedule. Scenario validation passes, including the check that refuses water in compound or gateway hexes. Concord has no building, so that check finds nothing to refuse.

## 4. The scripted historical orders

`battle/concord_policy.py` holds the orders as data (`MILITIA_ORDERS`, `REGULARS_ORDERS`), each with a trigger, a `source` locator and a `provenance` label. No policy chooses a winner. The policies read only the side's `engine.view`, with one exception that matters: headquarters rides with P1, the provincial command unit, and `engine.view` gives the command unit's own detachment its true current state. Headquarters therefore knows P1's losses at once, without a report.

| Policy | Order | Trigger | Source |
|---|---|---|---|
| `scripted-concord-militia-v1` | hold fire | Initial posture of every provincial unit (entry data) | S47, Barrett: "Do not fire unless first fired upon" |
| | advance (P1) / follow (P2 to P4) | Start, once per company, at most 3 orders a decision | S47, S48; "the rest follow" is doc 43 §5 S1 (reconstruction) |
| | open fire | Headquarters knows of a provincial loss | S47, Buttrick: "Fire, for god's sake fire!" |
| | cross | Fire released, no contact 1 interval old or less within 2 hexes of the far end | Doc 43 §5 S1 (reconstruction) |
| `scripted-concord-regulars-v1` | open fire | Initial posture of every British unit (entry data) | S47: fired "without an order to fire" |
| | guard (hold) | Start, once per company | Reconstruction: no order to Laurie was read (43 §1) |
| | fall back to the town | Two of three companies routed, lost or below half strength | Doc 43 §5 S1 (reconstruction); S47: the British withdrew |

## 5. The run

The full output of `python3 scripts/concord_timeline.py` (from `apps/poc`, commit `454b1a2`). Only the `game_id`, which differs on every run, is replaced by `…`. Every event the comparison cites is in this block.

```
{'game_id': '…', 'winner': 'provincial', 'turns': 8, 'events': 568, 'strength': {'P1': 39, 'P2': 120, 'P3': 120, 'P4': 120, 'B1': 29, 'B2': 32, 'B3': 32}, 'replay': {'revisions': 12, 'turns': 8, 'status': 'identical'}, 'run': {'rules': 'poc-13', 'scenario': 'concord-north-bridge-v1', 'scenario_id': 'concord-north-bridge', 'variant': None, 'prompt_version': 'concord-side-v1', 'player_side': 'provincial', 'player_provider': 'scripted', 'model': None, 'effort': None, 'response_format': None, 'opponent_side': 'british', 'opponent': 'scripted-concord-regulars-v1', 'player_policy': 'scripted-concord-militia-v1'}}
turn  0  order_sent        {'arrival_turn': 1, 'destination': [11, 10], 'order_id': 'O1', 'side': 'provincial', 'unit_id': 'P1', 'version': 1}
turn  0  order_sent        {'arrival_turn': 1, 'destination': [11, 9], 'order_id': 'O2', 'side': 'provincial', 'unit_id': 'P2', 'version': 1}
turn  0  order_sent        {'arrival_turn': 1, 'destination': [11, 11], 'order_id': 'O3', 'side': 'provincial', 'unit_id': 'P3', 'version': 1}
turn  0  order_sent        {'arrival_turn': 1, 'destination': None, 'order_id': 'O4', 'side': 'british', 'unit_id': 'B1', 'version': 1}
turn  0  order_sent        {'arrival_turn': 1, 'destination': None, 'order_id': 'O5', 'side': 'british', 'unit_id': 'B2', 'version': 1}
turn  0  order_sent        {'arrival_turn': 1, 'destination': None, 'order_id': 'O6', 'side': 'british', 'unit_id': 'B3', 'version': 1}
turn  1  order_delivered   {'order_id': 'O1', 'unit_id': 'P1', 'version': 1}
turn  1  order_delivered   {'order_id': 'O2', 'unit_id': 'P2', 'version': 1}
turn  1  order_delivered   {'order_id': 'O3', 'unit_id': 'P3', 'version': 1}
turn  1  order_delivered   {'order_id': 'O4', 'unit_id': 'B1', 'version': 1}
turn  1  order_delivered   {'order_id': 'O5', 'unit_id': 'B2', 'version': 1}
turn  1  order_delivered   {'order_id': 'O6', 'unit_id': 'B3', 'version': 1}
turn  1  local_decision    B1 observe: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  1  local_decision    B2 observe: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  1  local_decision    B3 observe: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  1  local_decision    P1 continue: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  1  local_decision    P2 continue: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  1  local_decision    P3 continue: No enemy within effective range; maintain the assigned mission.
turn  1  local_decision    P4 hold: No enemy within effective range; maintain the assigned mission.
turn  1  unit_moved        P1 [7, 10] -> [8, 10]
turn  1  unit_moved        P2 [6, 10] -> [6, 9]
turn  1  unit_moved        P3 [5, 10] -> [5, 11]
turn  2  unit_moved        P1 [8, 10] -> [9, 10]
turn  2  unit_moved        P2 [6, 9] -> [7, 9]
turn  2  unit_moved        P3 [5, 11] -> [6, 11]
turn  3  unit_moved        P1 [9, 10] -> [10, 10]
turn  3  unit_moved        P2 [7, 9] -> [8, 9]
turn  3  unit_moved        P3 [6, 11] -> [7, 11]
turn  3  order_sent        {'arrival_turn': 6, 'destination': [10, 10], 'order_id': 'O7', 'side': 'provincial', 'unit_id': 'P4', 'version': 1}
turn  4  unit_moved        P1 [10, 10] -> [11, 10]
turn  4  unit_moved        P2 [8, 9] -> [9, 9]
turn  4  unit_moved        P3 [7, 11] -> [8, 11]
turn  4  volley            {'exposure': 57, 'rounds': 32, 'target_id': 'P1', 'unit_id': 'B1'}
turn  5  local_decision    B1 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  5  local_decision    P1 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  5  unit_moved        P2 [9, 9] -> [10, 9]
turn  5  unit_moved        P3 [8, 11] -> [9, 11]
turn  5  volley            {'exposure': 57, 'rounds': 32, 'target_id': 'P1', 'unit_id': 'B1'}
turn  5  volley            {'exposure': 72, 'returning_fire': True, 'rounds': 40, 'target_id': 'B1', 'unit_id': 'P1'}
turn  5  casualties        {'count': 1, 'remaining': 39, 'unit_id': 'P1'}
turn  6  order_delivered   {'order_id': 'O7', 'unit_id': 'P4', 'version': 1}
turn  6  local_decision    P4 continue: No enemy within effective range; maintain the assigned mission.
turn  6  unit_moved        P2 [10, 9] -> [11, 9]
turn  6  unit_moved        P3 [9, 11] -> [10, 11]
turn  6  unit_moved        P4 [4, 10] -> [5, 10]
turn  6  volley            {'exposure': 57, 'rounds': 32, 'target_id': 'P1', 'unit_id': 'B1'}
turn  6  volley            {'exposure': 57, 'rounds': 32, 'target_id': 'P2', 'unit_id': 'B3'}
turn  6  volley            {'exposure': 70, 'returning_fire': True, 'rounds': 39, 'target_id': 'B1', 'unit_id': 'P1'}
turn  6  casualties        {'count': 1, 'remaining': 31, 'unit_id': 'B1'}
turn  6  order_sent        {'arrival_turn': 7, 'destination': None, 'order_id': 'O8', 'side': 'provincial', 'unit_id': 'P1', 'version': 2}
turn  6  order_sent        {'arrival_turn': 7, 'destination': None, 'order_id': 'O9', 'side': 'provincial', 'unit_id': 'P2', 'version': 2}
turn  6  order_sent        {'arrival_turn': 7, 'destination': None, 'order_id': 'O10', 'side': 'provincial', 'unit_id': 'P3', 'version': 2}
turn  7  fire_posture_set  {'fire_posture': 'open_fire', 'order_id': 'O8', 'unit_id': 'P1'}
turn  7  order_delivered   {'order_id': 'O8', 'unit_id': 'P1', 'version': 2}
turn  7  fire_posture_set  {'fire_posture': 'open_fire', 'order_id': 'O9', 'unit_id': 'P2'}
turn  7  order_delivered   {'order_id': 'O9', 'unit_id': 'P2', 'version': 2}
turn  7  fire_posture_set  {'fire_posture': 'open_fire', 'order_id': 'O10', 'unit_id': 'P3'}
turn  7  order_delivered   {'order_id': 'O10', 'unit_id': 'P3', 'version': 2}
turn  7  local_decision    B1 withdraw: We are withdrawing because credible sightings indicate a much stronger enemy.
turn  7  local_decision    B3 withdraw: We are withdrawing because credible sightings indicate a much stronger enemy.
turn  7  local_decision    P2 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  7  unit_moved        B1 [13, 10] -> [13, 11]
turn  7  unit_moved        B3 [13, 9] -> [14, 9]
turn  7  unit_moved        P3 [10, 11] -> [11, 11]
turn  7  unit_moved        P4 [5, 10] -> [6, 10]
turn  7  volley            {'exposure': 55, 'rounds': 31, 'target_id': 'P3', 'unit_id': 'B1'}
turn  7  volley            {'exposure': 216, 'rounds': 120, 'target_id': 'B1', 'unit_id': 'P3'}
turn  7  casualties        {'count': 2, 'remaining': 29, 'unit_id': 'B1'}
turn  8  local_decision    P1 observe: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  8  local_decision    P2 observe: Enemy sighted beyond effective range; observe, report and maintain mission.
turn  8  local_decision    P3 defend: Enemy within effective range; halt locally, use cover and return fire.
turn  8  unit_moved        B1 [13, 11] -> [14, 11]
turn  8  unit_moved        P4 [6, 10] -> [7, 10]
turn  8  battle_ended      {'reason': 'The attackers held the bridge uncontested for 60 seconds.', 'winner': 'provincial'}
capture 2 reason The attackers held the bridge uncontested for 60 seconds.
```

Scenario time is 09:25 plus 30 seconds a turn: turn 4 is 09:27:00 and turn 8 is 09:29:00.

## 6. Comparison

### Sequence of events

| Record | Simulated (turn, event) |
|---|---|
| British secure the bridge at 07:30; militia reach the ridge at 09:00 (S47) | Start state at turn 0: British on the east bank, militia on the ridge |
| Barrett: do not fire unless first fired upon (S47) | Every provincial unit starts `hold_fire` |
| The militia advance on the bridge, Davis's Acton company in front (S47, S48) | Turn 0: O1 to O3 send P1 to (11, 10), P2 to (11, 9), P3 to (11, 11). Turn 3: O7 sends P4 by runner; delivered turn 6. P1 reaches (11, 10) at turn 4 |
| Three British shots first, into the river (S47) | Turn 4: B1's first volley at P1, exposure 57, no casualty. The British fire first. The no-casualty volley comes from loss credit below 100, not from a modelled warning shot |
| The rest of the British fire into the column without an order; Davis and Hosmer fall (S47, S48) | Turn 5: B1's second volley; P1 loses 1 (39 left). No `officer_down`: P1's officer step is 13 losses |
| Buttrick: "Fire, for god's sake fire!" (S47) | Turn 5: P1 returns fire on its own under the hold-fire rule (`returning_fire`). Turn 6: the policy sends `open_fire` to P1 to P3 (O8 to O10); set turn 7 |
| The British withdraw; the militia hold the bridge (S47) | Turn 7: B1 and B3 withdraw by local standing reaction ("much stronger enemy"). Turn 8: provincial win, "held the bridge uncontested for 60 seconds" |
| Fighting at 09:30 (S47) | Exchange 09:27:00 to 09:29:00 (turns 4 to 8). S47 gives times to the half hour, so the minutes are not comparable |

### Objectives

- **Provincial: hold the bridge.** Record: held (S47). Simulated: held at turn 8 with P1 on the west end, inside radius 1. No provincial unit stood on the bridge hex or crossed it. The `cross` order was never sent, because the battle ended before the next decision at turn 9.
- **British: guard the crossing, fall back toward the town if it gives way.** Record: the guard withdrew (S47). The order behind it was not read (43 §1). Simulated: B1 and B3 withdrew one or two hexes east, out of radius 1. The policy's `fall-back` order never fired, because no British company was routed, lost or below half strength. The withdrawal came from the standing doctrine's enemy-ratio trigger, not from an order.

### Losses

Doc 43 §5 says not to score body counts against the history: the record is an order-of-magnitude check only. The engine counts casualties without separating killed from wounded.

| | Record (S47) | Simulated |
|---|---|---|
| British | 3 killed or mortally wounded, 9 wounded: 12 of about 96 | 3 of 96 (B1: 1 at turn 6, 2 at turn 7) |
| Provincial | Davis and Hosmer killed; Blanchard and 3 others wounded: 6 of about 400 | 1 of 400 (P1, turn 5) |

In both, the British lose more than the provincials. The simulated totals are a quarter (British) and a sixth (provincial) of the record.

### Variant runs (sensitivity only, not tuning)

| Variant | Winner, turn | Strength at the end |
|---|---|---|
| `planks-lifted` | provincial, 8 | Same as the entry: 568 events. No unit entered the bridge hex, so its cost never applied |
| `two-companies` | provincial, 8 | P1 38, B1 42, B2 45: provincial 2, British 3 |
| `british-west-bank` | provincial, 20 | P1 35, P2 116, B1 0, B2 23, B3 0: provincial 9, British 73. B1 routed turn 7, B3 turn 15 |

`british-west-bank` is an authored counterfactual, not a sourced reading: S47, S48 and S49 are silent on the banks. The policies were written for the entry's geometry. In it the British stand on the militia's approach hexes, so this run tests the variant's data, not a reconstruction of the orders.

## 7. Gaps and divergences

1. **Fire release order.** The hold-fire rule released the front company at turn 5, one interval before Buttrick's order went out and two before it arrived. In the record, his order released the fire (S47). The policy's trigger is a provincial loss known to headquarters. Headquarters rides with P1, the command unit, and `engine.view` gives it P1's true state, so it knew of P1's loss at turn 5 at once. The order still waited for the next decision at turn 6 (decisions come every 3 turns) and one interval of delivery, while the rule releases a unit in the interval it takes losses.
2. **Warning shots.** S47's three shots into the river are not modelled. The no-casualty volley at turn 4 resembles them only through loss credit.
3. **Davis and Hosmer.** No officer fell: P1 lost 1 man against an officer step of 13. Doc 47 records that a single early volley cannot kill an officer.
4. **The British withdrawal.** The guard gave way by local doctrine before any company broke, so the reconstructed fall-back order played no part. Whether S47's withdrawal was ordered is not known (43 §1).
5. **No crossing.** Radius 1 counts the west end, so the provincials won without reaching the bridge. The planks question therefore cannot affect this run. Doc 43 R6 (`force-withdrawal`) is not needed to score the recorded outcome here.
6. **Engagement width.** Only B1, B3, P1 and P3 fired; B2 (Laurie) never came within 2 hexes of a provincial. One detachment per hex and three west-bank hexes within range of the far end limit the front.
7. **Order cap.** At most 3 orders a decision sent P4 by runner three turns late. This is a POC limit, not a period one.
8. **Losses** are low against S47 (section 6), with the assumed smoothbore effect of 60 per cent.
9. **Not modelled:** the grenadier companies and the 11:00 return (S47), and the sources 43 §6 question 8 lists as not read (Gage's orders, Barker's diary, the depositions, Laurie's account).
10. **Desk.** The command desk cannot draw the river (43 row 8), so Concord is headless only.
11. **Authored bridge geometry drives the outcome.** `BRIDGE` (12, 10) is on an even row of the odd-row grid. Its radius-1 ring has three west-bank hexes, (11, 9), (11, 10) and (11, 11), and one east-bank hex, (13, 10). `APPROACH` sends P1 to P3 onto those three west-bank hexes. Only B1 stands inside the ring: B2 at (14, 10) and B3 at (13, 9) are 2 hexes from the bridge, and the guard order holds them there. The capture rule (`victory.py:76`, `holding == {attacker}`) is therefore met as soon as one company, B1, leaves the ring, as it did at turn 7. The geometry is authored, not sourced. A sensitivity variant with the bridge on an odd row, for example (12, 11), where the ring has one west-bank hex and three east-bank hexes, is future work and not part of this run. Doc [49](49-concord-geometry-sensitivity.md) runs that variant and two balanced rings: the provincial hold depends on the geometry.

## 8. Tests

`apps/poc/tests/test_concord.py`: the entry registers in the headless catalog and dry-runs; it declares command rules, `WEAPONS_1775` and the 1775 voice; the musket range guard; the river is impassable except at the bridge; the open questions are labelled and each alternative is a variant that validates; variants differ in their own question; fire postures follow the recorded orders; the policies are registered and chosen for their sides; every order carries a source; the militia advance, fire and cross triggers; the regulars' guard and fall-back; nothing while command is disrupted; two headless runs give the same battle and replay `identical`.
