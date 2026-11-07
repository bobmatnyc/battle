# 62 — Gergovia: the scenario entry, its variants and the runs

**Date:** 2026-11-07. **Requirement:** the Gergovia scenario planned in [57](57-gergovia-scenario-plan.md), with every proposed default of 57 §8 (`gergovia-recall`: trumpet recall at interval 40, reach 8 hexes, a valley block, Roman S1, Gallic G1) and its named variants. **Ruling:** the user ruled on Dc0, "Accept all defaults; PM proceeds", so every open question of 57 §9 takes the default 57 proposes. D85 ruling (Bob, 2026-11-07 13:10Z): "Earlier recall"; per the Architect's reading (2026-11-07 16:38Z, option b) the recall moves from interval 40 to interval 20 (§3). The rules are those of [60](60-broadcast-signal-exploit-and-recover-force.md) (broadcast signal, exploit, recover-force, Roman profile and voice), [58](58-small-unit-rout-and-open-assault.md) (declared rout threshold) and [55](55-tactics-v11-threat-range.md) (`tactics_v11`).

Labels follow 57: **sourced** (S-id and locator; S60 to S64 in [09](09-sources.md#hill-223-and-gergovia-source-pass--2026-11-06)), **inferred**, **reconstruction**, **authored**. **Model result** marks what the simulation produced. No value was changed after a run.

## 1. What was built

| Part | Where | Notes |
|---|---|---|
| Entry `gergovia-recall` | `battle/scenario_gergovia.py` | Headless catalog only (`bootstrap.HEADLESS_SCENARIOS`), as Pegasus, Concord and Hill 223 (57 §9 q7) |
| Variants | `scenario_gergovia.VARIANTS` | Every 57 §8 name the engine can build (§4) |
| Scripted controls | `battle/gergovia_policy.py` | Roman S1 (`scripted-gergovia-roman-v1`), `no-cover` and `recall-by-runner` controls, Gallic G1 (`scripted-gergovia-gallic-v1`) and three `gallic-delay` controls, registered in `command_policy` |
| Runs | `scripts/gergovia_runs.py` | One JSON line a run, stored by `battle/batch_store.py` |
| Tests | `tests/test_gergovia.py`; `tests/test_scenario_catalog.py` (headless id list) | §8 |

## 2. Engine must-haves

Each 57 §10 must-have was checked on this branch (base `264709d`, on `e15bd3f`) before the entry was written. Gaps 1 to 6 are present; none was added. Gap 7 is the entry itself.

| 57 §10 gap | Present |
|---|---|
| 1 Broadcast signal with audibility | `BroadcastEntry`, `battle/broadcast.py` (60 §1); the signal's wait is recorded (`e15bd3f`) |
| 2 Small-unit rout threshold | `rout_strength` (58 §1) |
| 3 Exploit doctrine, `recall_binding` | `standing.exploit` (60 §2); an impassable `press_to` is refused (`e15bd3f`) |
| 4 Assault outside gated compounds | `press_assault` on `tactics_v11` (58 §2); not used by this entry (§7 row 13) |
| 5 Victory `recover-force` | `victory.RecoverForce` (60 §3) |
| 6 Profile and voice | `roman-republic-signal-v1`, `republic-en-v1` (60 §4) |
| 7 Map crop documented in the entry | `scenario_gergovia` module notes and `provenance["map.crop"]` |

## 3. The entry

**Default per Dc0 ruling 2026-11-07.** Each 57 §9 question takes 57's proposal. Each provenance field that carries the ruling says "default per Dc0 ruling 2026-11-07" and names its question:

| 57 §9 | Default taken | Provenance field |
|---|---|---|
| q1 Sector size | Four Eighth Legion century groups and Fabius's party, with the Tenth and Sextius's cohorts | `sector` |
| q2 Crop | The upper-slope crop; start at 12:00 with the camps taken; the approach and the valley as a lower-slope edge and signal-block hexes | `map`, `start_time`, `deadline` |
| q3 Cause of the overrun | Signal failure (the valley block) and ardour (`exploit`) are separate; neither is asserted as the truth | `signal` |
| q4 Caesar's intent | Take the camps by surprise; "also the town" is not an intent | `roman.mission` |
| q5 Player | Caesar at the Tenth's line (`roman`, attacker) | `player_side` |
| q6 Civilians and the Aedui | Left out of the default; the Aedui appear only in `aedui-misread` | `units.civilians`, `units.aedui` |
| q7 Headless only | Yes | `scope` |
| q8 Further sources | No pull before the run | `sources_pass` |

**Map** (authored, schematic, not surveyed). North is row 0, the town (`oppidum`). The town wall is row 1, with the gate at (11, 1) (S60 VII.47, VII.50). The stone wall is row 19 (VII.46), 18 rows below the town wall (57 §2: about 600 paces, inferred). Rows 2 to 18 west of the valley are the Gallic camps (VII.46). Row 20 and the ground east of column 17 are the lower slope. The valley (VII.47) is columns 16 and 17 from row 8 down. Elevation rises 2 a row to the town; the valley lies 14 lower. Both walls are terrain rows with cover and a sight height, since the engine has no free-standing wall (57 §10, later).

**Roster** (57 §6; strengths authored unless marked).

| Unit | Side | Hex | Men | Notes |
|---|---|---|---|---|
| `RX` Tenth with Caesar | roman | (21, 19) | 80 | Command unit; sounds the recall (VII.47, VII.51) |
| `R8a`–`R8d` Eighth Legion century groups | roman | (14, 17), (12, 17), (10, 17), (8, 17) | 60 each | Pursue toward the gate until they hear the recall (S1); Eighth named in VII.47, VII.50 |
| `R8f` Fabius's party | roman | (10, 16) | 4 | Sourced: VII.47; `rout_strength` 0 |
| `R13` Sextius's cohorts | roman | (0, 20) | 80 | The lesser camp corner (VII.49, VII.51) |
| `G1`–`G4` wall garrison | gallic | (7, 1), (11, 1), (13, 1), (15, 1) | 60 each | `G2`, at the gate, is the command unit |
| `GR` returning force, `GC` cavalry | gallic | (2, 0), (3, 0) | 120, 40 | The far side of the town (VII.48) |
| `AE` Aedui (variant only) | gallic | (15, 14) | 60 | Holds fire; 57 §10 workaround (VII.50) |

**Rules data** (all values authored unless marked):

| Item | Value | Basis |
|---|---|---|
| Weapons (`tactics_v11`) | Shock infantry 1 hex, effect 100; missile troops 3 hexes, effect 70 | 57 §6; Dio 40.36.3 (S61) for missiles |
| Observation | The 7-hex daylight default | 57 §6 |
| Communications | `roman-republic-signal-v1`, voice reach 2, voice `republic-en-v1` | 57 §6; trumpet VII.47, runner VII.49, voice VII.45 |
| Recall | Interval 20 (12:10:00), reach 8, stance `retreat` to (20, 19), block hexes the 26 valley hexes | Interval authored: the Architect's reading of D85 (16:38Z, option b), from the run timeline (below); reach and block 57 §8; sourced as the cause in Caesar's account (VII.47) |
| S1 pursuit | Every forward group declares `exploit`: trigger `start`, press to (11, 2) below the gate, `recall_binding` true, loss limit 50 % | Reconstruction: VII.47 (they pursued to the wall and gates); 60 §2 |
| Officers | The engine default, 2 a group | Authored |
| Succession | `RX` to `R13` | Authored; no source names one |
| Victory | `recover-force`: 50 % of the forward force (`R8a`–`R8d`, `R8f`; 244 men, so 122) within 2 hexes of (20, 19) by 14:00 (interval 240) | 57 §5, 60 §3; a "force recovered" reading, not a historical result |

**Audibility at the default geometry.** From `RX`, `R8a` stands 8 hexes off with the valley on the line (`blocked`); `R8b` to `R8d` and `R8f` stand 10 to 14 hexes off (`out_of_reach`). No forward group hears the default recall at the start; as they press upslope they move further off.

**Recall timing, D85 ruling 2026-11-07 13:10Z ("Earlier recall").** 57 §8 put the recall at interval 40 (12:20) and said the time is not sourced. In the runs of §5 the default force breaks at 36, so the recall never sounded (§9). The ruling names no interval. The value used is the Architect's reading of it (Architect 2026-11-07 16:38Z, option b): the recall sounds during the fight, after gate contact and before the break, at interval 20 (12:10:00). It is authored and is not Bob's own figure. Its basis is the default run's timeline in the EVO run `bt05p-466c33c` (`gergovia-default.sqlite`, read-only), which matches the §5 default up to 36:

| Interval | Clock | Event |
|---|---|---|
| 14 | 12:07:00 | First volley from the wall (`G2` on `R8f`) |
| 15 | 12:07:30 | `R8f`'s press stops, `shaken` |
| 16 | 12:08:00 | First Roman casualties (`R8a`) |
| 19 | 12:09:30 | `R8a` reaches the hex below the gate (`exploit_stopped`, `reached`): first contact at the gate |
| 23 | 12:11:30 | `R8a` routs, the first rout |
| 26, 28 | 12:13:00, 12:14:00 | `R8b`, `R8d` reach the gate |
| 36 | 12:18:00 | `R8b` routs; the force can no longer bring back 122 men; Gallic win |

Interval 20 is the first after `R8a` reaches the gate and three before the first rout, so every forward group is still able to obey a recall it hears (a routed group does not obey, 60 §1). It is a one-line value, `RECALL_TURN` in `battle/scenario_gergovia.py`, so the owner can move it. `recall-by-runner` sends its orders from the same `RECALL_TURN`. Reach, block, the Gallic return (still 40), Sextius (60) and every other value are unchanged.

Option not taken: interval 1, inferred from VII.47 (the retreat sounded once the camps are taken) and built at `466c33c`. In `bt05p-466c33c` (its `gergovia.log`) only `recall-audible` heard it, and there all five groups obeyed at 1 and no fight took place (Roman win at 11, 0 / 0 losses); in 11 entries the force still broke at 36, `recall-by-runner` was a Roman win at 42, and `strength-40` and `strength-80` ran to the deadline.

**Edition:** none. The change is scenario data, not a rule: a game stores the recall's interval in its revision-0 snapshot (`broadcasts[0].turn`), and replay re-applies the recorded actions to that snapshot (`replay.verify`, `replay.verify_recorded`), so a saved game replays as recorded whatever the entry now says. `scripts/gergovia_runs.py` stores its runs in a temporary directory; the only archived Gergovia games are the `bt05p-466c33c` DBs (`apps/poc/artifacts/gergovia-d85-466c33c`), which hold interval 1 in their own snapshots and so replay as recorded. The rules stay `poc-13` and the label `gergovia-recall-v1`, as for Hill 223 under D7b (60 §5).

**Scripted controls.** The recall, the forward groups' pursuit and the wall's hold are entry data. `ROMAN_ORDERS` and `GALLIC_ORDERS` list each order with its trigger and S60 locator: take the camps (before the start), the pursuit, the recall, the runner recall (variant), Sextius out at interval 60 (VII.49), the Tenth's short advance (not modelled, §7), the wall's hold, the return beneath the wall at interval 40 (VII.48), and the push down to (11, 18) once a fresh contact stands within 2 rows of the town wall (VII.50, VII.51).

## 4. Variants

| Name | Change | 57 §8 basis |
|---|---|---|
| `recall-audible` | Reach 45, no block: every group hears | Control; VII.47 (the Tenth heard) |
| `recall-by-runner` | Each forward group also gets a retreat order to (20, 19) from the recall interval (20 since D85; 40 in the §5 runs) | VII.47 (tribunes and legates) |
| `ardour` | The S1 pursuit with `recall_binding` false: a heard recall is taken up only once the press stops | Caesar's account: VII.47, VII.52; mechanism authored |
| `leaders-fall` | Each forward group has 1 officer (its centurion), not 2 | Inferred: VII.47, VII.51 |
| `sextius-cover` | The default's own reading (Sextius out at 60) | VII.49 |
| `no-cover` | Sextius is not ordered out | VII.49, the counterfactual |
| `aedui-misread` | Adds `AE` on the Gallic side, holding fire | VII.50; 57 §10 workaround |
| `gallic-delay-10`, `-20`, `-40` | The return order 10, 20 or 40 intervals later | Authored |
| `strength-40`, `strength-80` | Century groups of 40 or 80 | Authored |
| `strength-60` | The default's own reading | Authored |

`gate-forced` is not built (§7 row 4). `sextius-cover` and `strength-60` are registered as their own entries so every 57 §8 name that can be built validates and runs. `test_each_named_variant_differs_only_in_its_own_question` checks each variant's starting snapshot against the default's.

## 5. Results (model results)

**Superseded, pending re-run (D85 ruling 2026-11-07).** The results in this section and in §6 were produced with the recall at interval 40. Per D85, as the Architect reads it (16:38Z, option b), the recall now sounds at interval 20 (§3), after gate contact and before the force breaks, so the recall, its partial hearing and the `recall-audible`, `recall-by-runner` and `ardour` differences now act in the default battle. The 14 runs must be repeated on EVO; until then the table below describes the interval-40 entry only, and no new result is claimed here.

One run each, 14 runs, after the fix round of §7 rows 1 and 13 (the earlier runs, with the groups on `hold`, are superseded). Every replay is `identical`. Interval *t* is 12:00 plus *t* × 30 s. "Recovered" is the forward force's men within 2 hexes of the rally hex at the end; 122 are needed (82 for `strength-40`, 162 for `strength-80`). Total run time 240.7 s on the Mac, summed from the per-run timings.

| Run | Winner, end | Reason | Recall receipts (forward groups) | Furthest row reached | Recovered | Exploit stops (unit, turn, reason) | Roman / Gallic losses | Routed | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| default | gallic, 12:18:00 (36) | the force can no longer bring back enough | none: the battle ended before 40 | 1 (`R8b`), 2 (`R8a`, `R8c`, `R8d`), 4 (`R8f`) | 0 | `R8f` 15 shaken; `R8a` 19, `R8b` 26, `R8d` 28 reached | 42 / 2 | `R8a`, `R8b` | 5.3 |
| `recall-audible` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `recall-by-runner` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `ardour` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `leaders-fall` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.3 |
| `sextius-cover` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.3 |
| `no-cover` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `gallic-delay-10` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `gallic-delay-20` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `gallic-delay-40` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.3 |
| `strength-60` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.2 |
| `aedui-misread` | as default | as default | as default | as default | 0 | as default | 42 / 2 | `R8a`, `R8b` | 5.9 |
| `strength-40` | gallic, 14:00:00 (240) | not brought back by the deadline | `R8a` heard at 40 while routed (not obeyed); others out of reach | 2 to 4 | 0 | `R8f` 15, `R8b` 18, `R8c` 25 shaken; `R8a` 19, `R8d` 22 reached | 29 / 4 | `R8a` | 79.6 |
| `strength-80` | gallic, 14:00:00 (240) | not brought back by the deadline | all out of reach | 2 to 4 | 0 | `R8f` 15 shaken; `R8a` 19 reached | 11 / 3 | none | 97.6 |

Event counts: 3,036 for the default and for every run marked "as default", except `leaders-fall` (3,034) and `aedui-misread` (3,314); 25,213 for `strength-40`; 26,719 for `strength-80`. In the runs that end at 36 no Gallic order and no Sextius order is sent: the return (40), Sextius (60) and the recall (40) all come after the end. In `strength-40` and `strength-80` the Gallic return is first sent at 42 and Sextius at 60; only `strength-80` sends the push down (45). In `strength-40`, `R8a` routed back toward the Tenth (it ends at (21, 18)) and heard the recall at 40, but a routed group does not obey (60 §1). In `strength-80`, `R8a` to `R8d` end at the gate with 71 to 80 men each.

## 6. Reading the results

Superseded pending re-run, as §5: these readings are of the interval-40 runs.

- **Under S1 the unheard groups press on to the wall, so signal failure now produces the overrun.** At the default geometry no forward group can hear the recall, and none is ever recalled. They reach the hex below the gate in 9 to 14 minutes and take missile fire from the wall. Two groups rout; the effective force falls to 120, under the 122 needed, and the defender wins at 12:18.
- **Signal failure and ardour produce the same battle in every run.** The default and `ardour` give the same outcome, metrics and event count (3,036). The two readings differ only for a group that hears the recall: S1 stops its pursuit, ardour does not. In these runs no forward group hears the recall while able to obey it: in eleven runs the battle ends at 36, before the recall sounds at 40, and in `strength-40` and `strength-80` every pressing group is out of reach by 40. The difference is shown on the entry only with the recall moved to interval 2 (`test_a_heard_recall_stops_the_pursuit_under_signal_failure_but_not_under_ardour`). The recall stays at interval 40, reach 8, valley block, as 57 §8 authors it (PM decision in the fix round).
- **The control variants change nothing.** `recall-audible` and `recall-by-runner` are the default's battle because the recall and the runner orders (from 40) come after the end at 36. `leaders-fall`, `no-cover`, `aedui-misread` and the delays are the default's battle too: in `leaders-fall` the one-officer step is 30 losses, so no group goes leaderless before 36 (the default has one `officer_down` at a 20-loss step, `leaders-fall` none, hence 2 fewer events), and the orders the others change all fall after 36.
- **Strength decides whether the force breaks.** With groups of 40 (82 needed of 164) or 80 (162 of 324), two routs do not take the force below the share, so the battle runs to the deadline. Neither brings anyone back: the pressing groups are out of earshot, and the press ends at the gate (`reached`) or on a withdrawal (`shaken`); the group then keeps its `hold` mission where it stands.
- **Against the record (not scored).** VII.51 gives 46 centurions and about 700 men lost for the whole assault; the default loses 42 of 404 in this sector. An order-of-magnitude check only (57 §5); S61 and S64 say Caesar's figure may understate.

## 7. Deviations from doc 57

| # | Doc 57 | Entry | Why |
|---|---|---|---|
| 1 | S1: "forward groups hold the taken camps on the recall"; an unheard group "keeps its mission" (57 §10 gap 1) | Before the recall the forward groups pursue toward the gate (`exploit`, `recall_binding` true); the recall's stance is `retreat` to the Tenth's line | The hold is what the recall produces, so before it the groups do something else that an unheard group keeps (VII.47: they pursued to the wall and gates). 57 §5 puts the rally hex at the Tenth's line, so the recall brings a hearing group there. Fix round: the first version held the camps from the start, which made signal failure unable to cause the overrun |
| 2 | S1: "a group within reach of its tribune's voice obeys" | No tribune units; voice reach 2 from `RX`, used only for sent orders (`recall-by-runner`) | The engine has no sub-unit officers who relay orders |
| 3 | `recover-force` with `limit_row` | No `limit_row`; 50 % within 2 hexes | 60 §3: "engaged" has no engine definition. Share and radius authored |
| 4 | `gate-forced` variant | Not built | `gates._force` needs a unit whose ordered destination lies inside the compound. No Roman intent targets the town (57 §9 q4), and a walled compound would also shut in `GR` and `GC`, so the variant could not answer its question |
| 5 | Stone wall and town wall | Terrain rows with cover and a sight height | No free-standing wall in the engine (57 §10, later) |
| 6 | `GC` cavalry | Shock infantry class | 57 §6's table has two classes and the engine no mounted class |
| 7 | Caesar "advances a little" (VII.49) | Not modelled | The rally hex is fixed at the Tenth's line; moving `RX` would move the sounder |
| 8 | Gallic command unit not named | `G2`, at the gate | Authored; Vercingetorix's post is not given |
| 9 | No date | `date` "52 BCE" | Caesar gives no day; the entry stores the year as text |
| 10 | Officers not set | Engine default 2 a group; 1 in `leaders-fall` | Authored |
| 11 | Gallic return "at a fixed turn" | Interval 40 | Authored; VII.47 to VII.48 give the order of events. It sounded with the recall until D85 moved the recall to 20; D85 changed the recall only |
| 18 | Recall "at turn 40" (57 §8) | Interval 20 | D85 ruling 2026-11-07 13:10Z ("Earlier recall"), as the Architect reads it (2026-11-07 16:38Z, option b): after gate contact, before the break; authored from the run timeline (§3) |
| 12 | Sextius "at turn N" | Interval 60 to (6, 19) | Authored |
| 13 | Gap 4 (`press_assault`) needed, since groups on a `move` order halt near contacts | Not declared | The S1 and ardour pursuits are `exploit` presses, which go on whatever the contacts (60 §2), so no forward group is on a `move` order that could halt |
| 14 | Aedui "count in the victory test" (57 §10 workaround) | `AE` is on the Gallic side and is not in `recover_units` | `recover-force` counts only the declared forward force |
| 15 | Lesser camp off the map | `R13` at the south-west corner (0, 20) | The cohorts must be on the map to be ordered out |
| 16 | Ammunition not set | 20 rounds a man | Authored; missiles and javelins |
| 17 | S2: "carry on to the wall after a fleeing enemy until contact" (57 §3) | `exploit` trigger `start` for S1 and ardour; the press goes to the hex below the gate and does not stop at contact | 60 §2: the local success is the battle's start (the camps taken), a fleeing enemy is not detected (contacts carry no routed status) and a press stops on reaching `press_to`, a binding recall, a newer order, the loss limit or a withdrawal, not on contact |

## 8. Tests

`tests/test_gergovia.py` (17 tests):

- Registration and dry run: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`, `test_entry_takes_the_doc_57_defaults`, `test_every_basis_carries_a_kind_and_each_open_question_cites_the_ruling`.
- Variants: `test_each_named_variant_differs_only_in_its_own_question`.
- Recall, reach and block: `test_the_default_recall_sounds_before_the_forward_force_breaks` (D85: the default recall sounds at its interval while the battle is still active, after a group has reached the gate and before any group routs; no forward group hears it, and in `recall-audible` every forward group obeys; red at `5704c40`, where the battle ended at 36 with the recall unsounded), `test_the_valley_blocks_the_recall_and_reach_bounds_it`, `test_a_group_in_reach_on_the_tenths_side_hears_and_obeys`, `test_recall_audible_reaches_every_forward_group`.
- Ardour against signal failure: `test_both_readings_pursue_to_the_gate_from_the_start`, `test_a_heard_recall_stops_the_pursuit_under_signal_failure_but_not_under_ardour`, `test_an_unheard_group_presses_on_under_both_readings`. The other recall tests sound the recall at interval 2 (or 20) on the starting geometry; they were written when the default battle ended at 36, before the recall.
- Victory: `test_recover_force_scores_the_forward_force_at_the_tenths_line`.
- Controls: `test_policies_are_registered_and_chosen_for_their_sides`, `test_every_order_carries_a_source_locator_or_a_label`, `test_roman_policies_send_sextius_and_the_runner_recall_once`, `test_the_gallic_masses_return_at_their_turn_then_push_only_once_romans_reach_the_wall` (a contact with no age counts as stale; red against the earlier code).
- Determinism: `test_two_headless_runs_give_the_same_battle_and_replay_identically` (two runs, equal digests, both replays `identical`).

No test asserts a winner.

## 9. Limits and next steps

- **Signal failure and ardour need a heard recall to differ.** With the recall at 40 and the force breaking at 36, no run tested the difference. Decided by D85 ruling 2026-11-07: "Earlier recall" (§3). The lower recovery share, the loss limit and a group placed in earshot were not taken. At interval 20 no forward group stands in earshot in the default, so the default still differs from `ardour` only in a variant where a group hears it; `recall-audible` and `recall-by-runner` now act before the break. The re-run results are pending (§5).
- **Most variants act after the end** (in the interval-40 runs). `recall-audible`, `recall-by-runner`, `no-cover`, the delays and `leaders-fall` change things that happen at 40 or later (or after more losses than a group takes before it routs). Since D85, `recall-audible` and `recall-by-runner` act at interval 20.
- **Map.** Authored and schematic; no contour map was obtained (57 §7).
- **Run cost.** About 5 s for a run that ends at 36, 80 to 98 s for a run to the deadline on the Mac; 14 runs in about 4 minutes. No run went to EVO.
- Reproduce, from `apps/poc`: `python3 scripts/gergovia_runs.py` (one JSON line per run; `--only NAME`).
