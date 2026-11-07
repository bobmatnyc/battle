# 62 — Gergovia: the scenario entry, its variants and the runs

**Date:** 2026-11-07. **Requirement:** the Gergovia scenario planned in [57](57-gergovia-scenario-plan.md), with every proposed default of 57 §8 (`gergovia-recall`: trumpet recall at interval 40, reach 8 hexes, a valley block, Roman S1, Gallic G1) and its named variants. **Ruling:** the user ruled on Dc0, "Accept all defaults; PM proceeds", so every open question of 57 §9 takes the default 57 proposes. The rules are those of [60](60-broadcast-signal-exploit-and-recover-force.md) (broadcast signal, exploit, recover-force, Roman profile and voice), [58](58-small-unit-rout-and-open-assault.md) (declared rout threshold) and [55](55-tactics-v11-threat-range.md) (`tactics_v11`).

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
| `R8a`–`R8d` Eighth Legion century groups | roman | (14, 17), (12, 17), (10, 17), (8, 17) | 60 each | Hold the taken camps (S1); Eighth named in VII.47, VII.50 |
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
| Recall | Interval 40 (12:20), reach 8, stance `retreat` to (20, 19), block hexes the 26 valley hexes | 57 §8; sourced as the cause in Caesar's account (VII.47) |
| Officers | The engine default, 2 a group | Authored |
| Succession | `RX` to `R13` | Authored; no source names one |
| Victory | `recover-force`: 50 % of the forward force (`R8a`–`R8d`, `R8f`; 244 men, so 122) within 2 hexes of (20, 19) by 14:00 (interval 240) | 57 §5, 60 §3; a "force recovered" reading, not a historical result |

**Audibility at the default geometry.** From `RX`, `R8a` stands 8 hexes off with the valley on the line (`blocked`); `R8b` to `R8d` and `R8f` stand 10 to 14 hexes off (`out_of_reach`). No forward group hears the default recall.

**Scripted controls.** The recall, the forward groups' hold and the wall's hold are entry data. `ROMAN_ORDERS` and `GALLIC_ORDERS` list each order with its trigger and S60 locator: take the camps (before the start), hold the camps, the recall, the runner recall (variant), Sextius out at interval 60 (VII.49), the Tenth's short advance (not modelled, §7), the wall's hold, the return beneath the wall at interval 40 (VII.48), and the push down to (11, 18) once a fresh contact stands within 2 rows of the town wall (VII.50, VII.51).

## 4. Variants

| Name | Change | 57 §8 basis |
|---|---|---|
| `recall-audible` | Reach 45, no block: every group hears | Control; VII.47 (the Tenth heard) |
| `recall-by-runner` | Each forward group also gets a retreat order to (20, 19) from interval 40 | VII.47 (tribunes and legates) |
| `ardour` | Forward groups declare `exploit`: trigger `start`, press to (11, 2) below the gate, `recall_binding` false, loss limit 50 % | Caesar's account: VII.47, VII.52; mechanism authored |
| `leaders-fall` | Each forward group has 1 officer (its centurion), not 2 | Inferred: VII.47, VII.51 |
| `sextius-cover` | The default's own reading (Sextius out at 60) | VII.49 |
| `no-cover` | Sextius is not ordered out | VII.49, the counterfactual |
| `aedui-misread` | Adds `AE` on the Gallic side, holding fire | VII.50; 57 §10 workaround |
| `gallic-delay-10`, `-20`, `-40` | The return order 10, 20 or 40 intervals later | Authored |
| `strength-40`, `strength-80` | Century groups of 40 or 80 | Authored |
| `strength-60` | The default's own reading | Authored |

`gate-forced` is not built (§7 row 4). `sextius-cover` and `strength-60` are registered as their own entries so every 57 §8 name that can be built validates and runs. `test_each_named_variant_differs_only_in_its_own_question` checks each variant's starting snapshot against the default's.

## 5. Results (model results)

One run each, 14 runs. Every replay is `identical`. Interval *t* is 12:00 plus *t* × 30 s. "Recovered" is the forward force's men within 2 hexes of the rally hex at the end; 122 are needed (82 for `strength-40`, 162 for `strength-80`).

| Run | Winner, end | Reason | Recall receipts (forward groups) | Furthest row reached | Recovered | Withdrawing groups, spread | Roman / Gallic losses | Routed | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| default | gallic, 14:00:00 (240) | not brought back by the deadline | `R8a` blocked; others out of reach | 17 (16 for `R8f`) | 0 | 0 | 0 / 0 | none | 30.6 |
| `recall-audible` | roman, 12:25:00 (50) | brought 180 back | all heard and obeyed at 40 | 17 | 180 | 4, 6 intervals | 0 / 0 | none | 2.9 |
| `recall-by-runner` | roman, 12:30:00 (60) | brought 180 back | as default (none heard) | 17 | 180 | 4, 7 intervals | 0 / 0 | none | 3.6 |
| `ardour` | gallic, 12:18:00 (36) | the force can no longer bring back enough | none: the battle ended before 40 | 1 (`R8b`), 2 (`R8a`, `R8c`, `R8d`), 4 (`R8f`) | 0 | 2 (routing), 10 intervals | 42 / 2 | `R8a`, `R8b` | 4.9 |
| `leaders-fall` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.0 |
| `sextius-cover` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.0 |
| `no-cover` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.7 |
| `aedui-misread` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 48.6 |
| `gallic-delay-10` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 32.4 |
| `gallic-delay-20` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.7 |
| `gallic-delay-40` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 30.9 |
| `strength-40` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.5 |
| `strength-80` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 31.6 |
| `strength-60` | as default | as default | as default | as default | 0 | 0 | 0 / 0 | none | 32.1 |

The Gallic return order was first sent at interval 42 (51, 60 and 81 in the delay variants: the first decision at or after the set interval). No push-down order was sent in any run, because no Roman was reported within 2 rows of the town wall at or after the return. In `recall-audible` and `recall-by-runner` the force reached the rally area before Sextius's interval, so `R13` was never ordered out. In `ardour`, `R8f` stopped pressing at 15 (`shaken`); `R8a`, `R8b` and `R8d` reached the hex below the gate at 19, 26 and 28; `R8c` was still pressing at the end. Total run time 374.5 s (6 min 15 s) on the Mac, summed from the per-run timings.

## 6. Reading the results

- **Under S1, signal failure strands the force; it does not cause the overrun.** The forward groups hold the taken camps. None hears the recall, so none moves. No Gaul comes within sight, and no shot is fired in 120 minutes. The defender wins at the deadline because the force is not back. The overrun of VII.47 appears only under `ardour`.
- **Ardour ends the battle before the recall.** The forward groups reach the gate in 9 to 14 minutes and take missile fire from the wall. Two groups rout. The effective force falls to 120, under the 122 needed, and the defender wins at 12:18. The recall at 12:20 is never sounded, so the `ardour` run does not test whether a heard recall is obeyed late. `test_a_heard_recall_binds_under_signal_failure_but_not_under_ardour` tests that rule on the entry with the recall moved to interval 2.
- **Any recall that arrives brings the force back.** `recall-audible` (by trumpet) and `recall-by-runner` (by order) both recover 180 men without contact. The runner is 10 minutes slower.
- **Eight variants change nothing under S1.** `leaders-fall`, `no-cover`, `aedui-misread`, the three delays and both strengths give the default's battle: no contact, so no officer falls, no Gaul returns into contact, and no Roman fires on the Aedui 3 hexes off with a 1-hex weapon. Event counts differ only by Sextius's order (`no-cover`, 10,634 against 10,654), the delay timings (10,656) and the Aedui unit (14,783). These questions bear on the overrun, so they test something only on an `ardour` base. A combined run is an owner decision (§9).
- **Against the record (not scored).** VII.51 gives 46 centurions and about 700 men lost for the whole assault; `ardour` loses 42 of 404 in this sector. That is an order-of-magnitude check only (57 §5), and S61 and S64 say Caesar's figure may understate.

## 7. Deviations from doc 57

| # | Doc 57 | Entry | Why |
|---|---|---|---|
| 1 | S1: "forward groups hold the taken camps on the recall" | The forward groups hold the camps from the start; the recall's stance is `retreat` to the Tenth's line | 57 §5 puts the rally hex at the Tenth's line, so the recall must bring the groups there. Holding the camps is read as the restraint order (VII.45) |
| 2 | S1: "a group within reach of its tribune's voice obeys" | No tribune units; voice reach 2 from `RX`, used only for sent orders (`recall-by-runner`) | The engine has no sub-unit officers who relay orders |
| 3 | `recover-force` with `limit_row` | No `limit_row`; 50 % within 2 hexes | 60 §3: "engaged" has no engine definition. Share and radius authored |
| 4 | `gate-forced` variant | Not built | `gates._force` needs a unit whose ordered destination lies inside the compound. No Roman intent targets the town (57 §9 q4), and a walled compound would also shut in `GR` and `GC`, so the variant could not answer its question |
| 5 | Stone wall and town wall | Terrain rows with cover and a sight height | No free-standing wall in the engine (57 §10, later) |
| 6 | `GC` cavalry | Shock infantry class | 57 §6's table has two classes and the engine no mounted class |
| 7 | Caesar "advances a little" (VII.49) | Not modelled | The rally hex is fixed at the Tenth's line; moving `RX` would move the sounder |
| 8 | Gallic command unit not named | `G2`, at the gate | Authored; Vercingetorix's post is not given |
| 9 | No date | `date` "52 BCE" | Caesar gives no day; the entry stores the year as text |
| 10 | Officers not set | Engine default 2 a group; 1 in `leaders-fall` | Authored |
| 11 | Gallic return "at a fixed turn" | Interval 40, with the recall | Authored; VII.47 to VII.48 give the order of events |
| 12 | Sextius "at turn N" | Interval 60 to (6, 19) | Authored |
| 13 | Gap 4 (`press_assault`) needed | Not declared | Under S1 no group is on a `move` order; under `ardour` the press ignores contacts (60 §2) |
| 14 | Aedui "count in the victory test" (57 §10 workaround) | `AE` is on the Gallic side and is not in `recover_units` | `recover-force` counts only the declared forward force |
| 15 | Lesser camp off the map | `R13` at the south-west corner (0, 20) | The cohorts must be on the map to be ordered out |
| 16 | Ammunition not set | 20 rounds a man | Authored; missiles and javelins |

## 8. Tests

`tests/test_gergovia.py` (16 tests):

- Registration and dry run: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`, `test_entry_takes_the_doc_57_defaults`, `test_every_basis_carries_a_kind_and_each_open_question_cites_the_ruling`.
- Variants: `test_each_named_variant_differs_only_in_its_own_question`.
- Recall, reach and block: `test_the_valley_blocks_the_recall_and_reach_bounds_it`, `test_a_group_in_reach_on_the_tenths_side_hears_and_obeys`, `test_recall_audible_reaches_every_forward_group`.
- Ardour against signal failure: `test_ardour_presses_to_the_gate_from_the_start`, `test_a_heard_recall_binds_under_signal_failure_but_not_under_ardour`, `test_an_unheard_group_keeps_its_hold_under_signal_failure_and_presses_under_ardour`.
- Victory: `test_recover_force_scores_the_forward_force_at_the_tenths_line`.
- Controls: `test_policies_are_registered_and_chosen_for_their_sides`, `test_every_order_carries_a_source_locator_or_a_label`, `test_roman_policies_send_sextius_and_the_runner_recall_once`, `test_the_gallic_masses_return_at_their_turn_then_push_only_once_romans_reach_the_wall`.
- Determinism: `test_two_headless_runs_give_the_same_battle_and_replay_identically` (two runs, equal digests, both replays `identical`; about 60 s).

No test asserts a winner.

## 9. Limits and next steps

- **The variants that bear on the overrun need an `ardour` base.** `leaders-fall`, `gallic-delay`, `strength-sweep`, `aedui-misread` and `no-cover` test nothing under S1, because S1 has no contact. Running them on `ardour` is a change to the variant design, so it is an owner decision.
- **Ardour and the recall.** With the recall at 40 and a 50 % recovery share, `ardour` ends at 36. An earlier recall, a lower share, or a loss limit that stops the press before a group routs would let the run test a late-obeyed recall. Each is an authored value, so it is an owner decision.
- **Map.** Authored and schematic; no contour map was obtained (57 §7).
- **Run cost.** About 31 s per 240-interval run that reaches the deadline on the Mac; 14 runs in about 6.3 minutes. No run went to EVO.
- Reproduce, from `apps/poc`: `python3 scripts/gergovia_runs.py` (one JSON line per run; `--only NAME`).
