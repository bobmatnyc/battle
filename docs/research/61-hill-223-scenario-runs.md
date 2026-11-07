# 61 — Hill 223: the scenario entry, its variants and the runs

**Date:** 2026-11-07. **Requirement:** the Hill 223 scenario planned in [56](56-hill-223-scenario-plan.md), with every proposed default of 56 §8 (`hill-223-patrol`: deadline 10:30, observation 3, valley 500 yd = 10 hexes, German G1, American S1) and its named variants. **Ruling:** the user ruled on Dc0, "Accept all defaults; PM proceeds", so every open question of 56 §9 takes the default 56 proposes. The rules are those of [58](58-small-unit-rout-and-open-assault.md), [59](59-surrender-facing-raid-and-1918-comms.md) and [55](55-tactics-v11-threat-range.md), with the exploit doctrine of [60](60-broadcast-signal-exploit-and-recover-force.md) for the return.

Labels follow 56: **sourced** (S-id and locator; Sources S40 to S43 and S57 to S59 in [09](09-sources.md#hill-223-and-gergovia-source-pass--2026-11-06)), **inferred**, **reconstruction**, **authored**. **Model result** marks what the simulation produced. No value was changed after a run to move a result toward the record. One value was changed after the first run to fix a defect (§7, row 10). The patrol's result was the same before and after that change.

## 1. What was built

| Part | Where | Notes |
|---|---|---|
| Entry `hill-223-patrol` | `battle/scenario_hill223.py` | Headless catalog only (`bootstrap.HEADLESS_SCENARIOS`), as Pegasus and Concord (56 §9 q6) |
| Variants | `scenario_hill223.VARIANTS` | Every 56 §8 name that the engine can build (§4) |
| Scripted controls | `battle/hill223_policy.py` | American S1 (`scripted-hill-223-company-g-v1`), the reinforcement variant (`scripted-hill-223-company-reinforces-v1`) and German G1 (`scripted-hill-223-german-v1`), registered in `command_policy` |
| Runs | `scripts/hill223_runs.py` | One JSON line a run, stored by `battle/batch_store.py` |
| Engine fix | `scenario_entry.build_state` | A side's starting reports are now deep copies of the units (§2) |
| Tests | `tests/test_hill_223.py`; `tests/test_scenario_catalog.py` (headless id list) | §8 |

## 2. Engine must-haves and one fix

Each 56 §10 must-have was checked on `main` at `e15bd3f` before the entry was written. All are present, and none was added here:

| 56 §10 gap | On main |
|---|---|
| 1 Small-unit rout threshold | `rout_strength` (58 §1, `768f4e4`) |
| 2 Surrender and captives | `surrender`, `battle/captives.py` (59 §1, `c07a642`) |
| 3 Gun facing and delay | `facing`, `arc`, `reorient_turns`, `battle/facing.py` (59 §2) |
| 4 Assault outside compounds | `press_assault` on `tactics_v11` (58 §2) |
| 5 Victory `raid-and-return` | `victory.py` (59 §3); refused before `poc-13` (`POC13_VICTORY_KINDS`) |
| 6 Profile and voice | `wwi-1918-voice-runner-v1`, `wwi-1918-en-v1` (59 §4) |

The entry is in `poc-13` (`RULES_VERSION`), the edition these rules need.

**Fix: starting reports shared nested data with the units.** The first headless run failed replay at revision 9. `build_state` built each side's `friendly_reports` with a shallow copy of each unit. The patrol's departure order is a nested override (`mission_result`), so the American report and the true unit held the same object. When the patrol reached the ravine, the engine completed the mission in the truth, and the report changed with no delivery. After a storage round trip the two are separate objects, so the replay differed. The live run also broke the observer rule: a side's report changed without a report arriving. `build_state` now deep-copies each unit for the reports. No earlier entry had a nested override that the engine changes in place, so the values written are the same. The suite's pinned digests are unchanged (§8). `test_a_sides_report_does_not_share_nested_unit_data` failed before the fix (`'completed' != 'active'`) and passes after it.

## 3. The entry: sourced facts, defaults and authored values

**Default per Dc0 ruling 2026-11-07.** Each 56 §9 question takes 56's proposal. Each provenance field that carries a ruling says "default per Dc0 ruling 2026-11-07" and names its question:

| 56 §9 | Default taken | Provenance field |
|---|---|---|
| q1 Player role | The Company G commander (`american`, attacker), who can reach the patrol only by runner | `player_side` |
| q2 R1 and R2 | Recast as the mechanism variants of 56 §8; no individual credit | `credit` |
| q3 Terrain L1 and L2 | One authored, schematic map; no archive pull | `map` |
| q4 Deadline and start | Start 06:45 (authored), deadline 10:30 (S57 p. 60), 450 intervals | `start_time`, `deadline` |
| q5 Gun reach | The 5-hex fire cap; the case tests facing, surprise and surrender | `weapons` |
| q6 Headless only | Yes | `scope` |
| q7 German unit | Left as a disclosed conflict (S57 "45th Reserve Division"; S58 120th Landwehr) | `sides` |

**Roster** (56 §6). Patrol `A1`, 17 men (sourced: S57 p. 60, S40), with 4 officers for the 4 NCOs, so one falls every 3 losses. Its rout threshold is 4 men (authored). It holds fire and returns fire when struck (sourced: S40 diary). It declares `press_assault` (reconstruction: it kept its route on contact). Company G line `A2` and `A3`, 40 men each, hold (authored). The post `AHQ` has 6 men and `rout_strength` 0 (authored). The German command group `D1` has 75 men (sourced as an estimate: S57 p. 60) and holds fire (inferred: "receiving final instructions"). The gun groups are `D2` (40, west slope, 1 hex from the shack), `D3` (30, north and northeast slopes) and `D4` (60, laid on the valley), all authored strengths.

**Rules data** (all values authored unless marked):

| Item | Value | Basis |
|---|---|---|
| Weapons (`tactics_v11`) | Rifles and pistols: 3 hexes, effect 67. Machine guns: 5 hexes, effect 100 | 56 §6, scaled to the engine's 100 cap (§7 row 1) |
| Observation | 3 hexes for every unit | 56 §6 |
| Communications | `wwi-1918-voice-runner-v1`, voice reach 1, voice `wwi-1918-en-v1` | 56 §6; S57 p. 57-58 records only a runner |
| Facing | All four German groups face 45° (north-east, down the valley toward the American attack), arc 120°, turn 1 interval | Sourced as posture: S40 (guns "masked and the muzzles pointed down into the valley", "rapidly turning them around"); S57 p. 60 ("quickly reversed their guns") |
| Surrender (G1, `D1` only) | Reach 3, odds 50 %, support within 1 hex, rear only | Inferred: S57 p. 60 ("supposing" a large American force); 59 §1 mapping |
| Departure order | `A1` starts with a move order to the ravine beside the shack, already received | Reconstruction: S57 p. 60, S58 (Parson); 56 §6, intent set at departure |
| Return | `exploit`, trigger `arrival`, press to the post hex, recall binding, loss limit 100 %, `resume_after_withdrawal` true | Reconstruction: S57 p. 61-62, S40 diary (the prisoners brought back); the resume is per D7b ruling 2026-11-07 |
| Victory | `raid-and-return`: within 1 hex of the shack for 1 interval, then 5 men (25 % of 17, rounded up) within 1 hex of the post holding at least 1 captive, by 10:30 | 56 §5; the thresholds are authored; no count is scored against S57 (doc 37) |
| Command | Succession `AHQ` to `A2` to `A3`; no German successor | Authored; S57 p. 61 names none |

**Map** (authored, schematic, not surveyed). Columns 0 to 4 are the German hill: the wooded ravine on its west side (column 0, rows 6 to 16; S57 p. 60), the crest, and heavy woods on the east crest (columns 3 and 4, rows 12 to 20; S57 p. 60). The shack is at (0, 11) (S40). An old trench is at (3, 16) (S40). The valley follows for 10 hexes (S57 p. 59). Hill 223 fills the rest. The patrol starts at (4, 18), at the east crest entering the woods (56 §2).

**Scripted controls.** Almost every historical order is entry data, because the patrol's intent was set at departure and voice reaches 1 hex. `AMERICAN_ORDERS` and `GERMAN_ORDERS` list each order with its trigger and source: the departure move, hold fire, press on, return, the line's hold, the German stand, guns on the valley, turning the guns, the yield, and the 10:30 counter-attack as the deadline. The S1 and G1 controls send no order. The reinforcement control sends one.

## 4. Variants

| Name | Change | 56 §8 basis |
|---|---|---|
| `valley-narrow` | Valley 5 hexes | Sourced conflict: S40 |
| `valley-wide` | Valley 18 hexes; Hill 223 keeps only the map's east column | Sourced conflict: S58, capped by the 24-column map |
| `surrender-on-threat` | `D1` yields only to an adjacent party, on any side (G2) | Inferred: S40 diary |
| `surrender-on-surprise` | G1, the default reading | Inferred: S57 p. 60 |
| `gun-turn-delay-1`, `-2`, `-4` | Gun groups `D2` to `D4` turn in 1 (default), 2 or 4 intervals | Authored: S40 "rapidly" |
| `no-shield` | Prisoners are no fire shield, the default reading | S40 affidavits, S57 "careful shooting" |
| `observation-2`, `observation-4` | Every unit sees 2 or 4 hexes | Authored |
| `company-reinforces` | `A3` is ordered to the patrol's start hex at interval 60 (07:15) | Authored; no source |

`shield` is not built: the engine has no prisoner shield (56 §10, later). `surrender-on-surprise`, `gun-turn-delay-1` and `no-shield` are the default's own readings. Each is registered as its own entry so that every 56 §8 name validates and runs. `test_each_named_variant_differs_only_in_its_own_question` checks that each variant's starting snapshot differs from the default's only in the fields of its own question, and that these three differ in none.

## 5. Results (model results)

Run on EVO at commit `679b637` (run directory `bt05n-679b637`), after the D7b ruling 2026-11-07: the entry declares `resume_after_withdrawal` (§7 row 5; 60 §2), so the patrol's press home pauses at a withdrawal and resumes when it clears. Before D7b (run `bt05e-0b636d5`) all 12 runs were German wins: the patrol took 75 captives and never returned, because the exploit stopped for good at the first withdrawal, at interval 13.

All 12 replays are `identical`. `return_on_approach_route` is false in all 12. Eleven runs are American wins: the raiders reached the German command post and returned by the deadline with 75 captives. `surrender-on-threat` is a German win at the deadline, 10:30:00 (interval 450), with no captives held. The run at 679b637 recorded the reason "The German kept the raiders from returning by the deadline", which is wrong: the patrol was home. After the code fix (Architect ruling 2026-11-07 14:47Z) the reason is "The raiders reached the German command post and 12 of them came back by the deadline, but they brought back 0 captives against the 1 required." That text comes from the code fix and a unit test on the entry, not from a run; it is pending the EVO re-run. Interval *t* is 06:45 plus *t* × 30 s.

Note on replay: the 679b637 `surrender-on-threat` replay no longer verifies under ec1be7b and later, because its stored reason is the old text. It is waived per the Architect ruling of 2026-11-07 14:55Z (doc 60 §5). It verifies under its 679b637 tarball, and the EVO re-run at the final commit replaces it.

| Run | `D1` yields (turn, to, count) | Raid made | Gun turns (unit: start→ready) | Patrol first struck / first volley (return fire) | Exploit: started, paused (withdrawal), resumed | Patrol at end | US / German losses | Result, end turn |
|---|---|---|---|---|---|---|---|---|
| default | 9, A1, 75 | 9 | D1 8→9; D2 9→10, 13→14; D4 13→14 | 10 / 10 (yes) | 10; 13; 16 | 10 men at (14, 10), 75 captives | 7 / 76 | American, 27 |
| `valley-narrow` | as default | 9 | as default | as default | as default | 10 men at (9, 10), 75 captives | 7 / 76 | American, 21 |
| `valley-wide` | as default | 9 | as default | as default | as default | 10 men at (22, 10), 75 captives | 7 / 76 | American, 36 |
| `surrender-on-threat` | none | 9 | D1 8→9; D2 9→10, 18→19 | 15 / 15 (yes) | 10; 10, 18; 14, 21 (stopped at 34, `reached`) | 12 men at (15, 10), 0 captives | 5 / 0 | German, 450 |
| `surrender-on-surprise` | as default | 9 | as default | as default | as default | as default | 7 / 76 | American, 27 |
| `gun-turn-delay-1` | as default | 9 | as default | as default | as default | as default | 7 / 76 | American, 27 |
| `gun-turn-delay-2` | 9, A1, 75 | 9 | D1 8→9; D2 9→11, 18→20; D4 18→20 | 11 / 11 (yes) | 10; 11, 18; 15, 22 | 9 men at (14, 10), 75 captives | 8 / 76 | American, 33 |
| `gun-turn-delay-4` | 9, A1, 75 | 9 | D1 8→9; D2 9→13, 18→22; D4 18→22 | 13 / 13 (yes) | 10; 11, 18; 15, 22 | 11 men at (14, 10), 75 captives | 6 / 76 | American, 33 |
| `observation-2` | 9, A1, 75 | 9 | D1 8→9; D2 9→10, 13→14 | 10 / 10 (yes) | 10; 13; 16 | 11 men at (14, 10), 75 captives | 6 / 76 | American, 27 |
| `observation-4` | 9, A1, 75 | 9 | D2 6→7; D1 8→9; D4 14→15, 21→22 | 9 / 9 (yes) | 10; 10, 14; 13, 18 | 7 men at (14, 10), 75 captives | 10 / 76 | American, 28 |
| `company-reinforces` | as default | 9 | as default | as default | as default | as default | 7 / 76 | American, 27 |
| `no-shield` | as default | 9 | as default | as default | as default | as default | 7 / 76 | American, 27 |

German losses count the 75 captives. No captive escaped in any run, and no unit routed.

**How the default runs** (events at turns 8 to 27). At the start of interval 9 the patrol is at (0, 13), two hexes due south of the shack, in `D1`'s rear arc. `D1`'s first estimate of it (quality 20) is 1 to 60 men. The high end, 60, is at least 50 % of `D1`'s 75 plus `D2`'s 40 (6,000 against 5,750), so `D1` yields at 9. The patrol enters (0, 12) the same interval, and the raid is made at 9. The press home starts at 10. `D2`, turned since 10, fires on the patrol from 10 to 14 and causes 7 losses. At 13 the patrol's own withdrawal trigger holds ("credible sightings indicate a much stronger enemy"): it estimates `D2` at 10 to 50 men, a mean of 30, against 11 men × 2.5 = 27.5. The press pauses. It resumes at 16, and the patrol ends turn 27 at (14, 10) with 10 men and 75 captives. The log records the pause and the resume but not why the withdrawal cleared at 16.

## 6. Reading the results

- **The resume decides the result.** Before D7b the stop of the return press at the first withdrawal decided all 12 runs (German wins). With the resume, 11 runs are American wins. The press pauses once in the default and in the valley, `surrender-on-surprise`, `gun-turn-delay-1`, `observation-2`, `company-reinforces` and `no-shield` runs, and twice in `gun-turn-delay-2`, `gun-turn-delay-4`, `observation-4` and `surrender-on-threat`.
- **`surrender-on-threat` is the one German win.** `D1` does not yield, so the patrol holds no captive. The exploit stops at turn 34 with reason `reached`, with 12 men at (15, 10). The victory rule needs at least 1 captive at the post (§3), so the run is not an American win. The unmet condition is the captive count, not the return. The reason recorded at 679b637 said the German kept the raiders from returning; after the code fix the deadline reason names each unmet condition (no raid, no man home, too few men home, too few captives), so this run reads "... 12 of them came back by the deadline, but they brought back 0 captives against the 1 required." The winner and end turn do not change. This text is from the code fix, pending the EVO re-run.
- **The valley width sets the end turn and the end hex.** The three valley runs end at turns 21, 27 and 36, at columns 9, 14 and 22, for valleys of 5, 10 and 18 hexes. Event counts are 664, 808 and 1,042. The patrol's losses and the exploit events are the same in all three.
- **G2 never yields.** At interval 9 the patrol is 2 hexes off, beyond reach 1. At 10 it is adjacent, but `D1` has now watched it for a second interval: the estimate's quality is 26 and its high end has fallen to 30 (3,000 against 5,750). The patrol's own trigger (`D1` estimated at 50 to 90, `D2` at 20 to 100) pauses the press at 10. The first volley is at 15 and the patrol takes 5 losses. Under these rules a yield needs surprise: the first, poorest estimate.
- **Gun turn delay.** Patrol losses are 7, 8 and 6 for turn delays of 1, 2 and 4. With a delay of 2 or 4, `D2` and `D4` turn again at 18, and the exploit pauses a second time at 18.
- **Observation.** Wider sight lets `D2` turn three intervals earlier (observation 4: turn starts at 6). The patrol takes 10 losses and ends with 7 men. Narrower sight (observation 2) keeps `D4` from turning, and the patrol ends with 11 men.
- **The surrender turns on a thin margin.** `D1` yields because 60 × 100 ≥ 50 × (75 + 40), that is 6,000 against 5,750. An odds value of 53 % or more, or a support reach that took in another group, would stop the G1 surrender in the default. That follows from the arithmetic, not from a run.
- **Against the record (not scored).** S57 p. 60 records 6 killed and 3 wounded when the guns turned; the default gives 7 patrol losses. S57 p. 61-62 records 132 prisoners counted at the post; the model holds 75, all from `D1`, because no gun group declares surrender (§7 row 9). The record has the patrol return; 11 of 12 runs do.

## 7. Deviations from doc 56

| # | Doc 56 | Entry | Why |
|---|---|---|---|
| 1 | Effects 100 (rifles) and 150 (machine guns) | 67 and 100 | `WeaponEntry.effect_pct` is 1 to 100; the 2:3 ratio is kept |
| 2 | Sight 3 in woods; 7 across the open valley | 3 everywhere | `observation_range` is one value per unit; the engine has no per-terrain sight |
| 3 | `shield` variant | Not built | No prisoner shield in the engine (56 §10, later; 59 §7) |
| 4 | §8 lists G1, delay 1 and no shield as variants | Registered as entries identical to the default apart from their labels | So that every §8 name validates and runs |
| 5 | Return "by the way it came" (S1); no mechanism named | `exploit` doctrine (60 §2), trigger `arrival`, with `resume_after_withdrawal` true per D7b ruling 2026-11-07: a local withdrawal pauses the press home, which resumes once the withdrawal clears; the engine's shortest path | The only engine rule that lets a unit carry an intent past its first order. Before D7b a withdrawal ended the return for good, and no run returned. Under D7b, 11 of 12 runs return, and `return_on_approach_route` is false in all 12 (§5) |
| 6 | Departure order not specified | A move order already received at the start (`mission_result` in the unit's overrides) | A runner order at turn 0 would leave the patrol idle for intervals it was not idle |
| 7 | Guns face the valley | 45° (north-east) for `D1` to `D4`; `D1` also turns in 1 interval in every variant | `rear_only` needs a declared facing on `D1`; `gun-turn-delay` changes the gun groups only |
| 8 | `valley-wide` 18 hexes | Hill 223 keeps one column | The map has 24 columns; the German hill takes 5 |
| 9 | §8 G1 names only the command group | Only `D1` declares surrender | 56 §3 G1. The engine has no cascade from a commander's yield to his command (S57 p. 61) |
| 10 | AHQ 6 men | `rout_strength` 0 | Without it the post routed in interval 1 under the 12-man default (a defect of the first run; the patrol's metrics were the same before and after) |
| 11 | `company-reinforces` turn and party not set | `A3`, interval 60, to the patrol's start hex | Authored |
| 12 | min strength and min captives not set | 25 % (5 men) and 1 captive | Authored; doc 37 keeps counts out of pass criteria |
| 13 | `D2`, the gun and rifle group, has rifles and pistols and machine guns (56 §6) | Machine guns only | The engine allows one `weapon_class` per unit. `D2` is the group that causes every patrol loss in the default run (§5), at machine-gun range 5 and effect 100; rifles would give range 3 and effect 67 |

## 8. Tests

`tests/test_hill_223.py` (13 tests):

- Registration and dry run: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`, `test_entry_takes_the_doc_56_defaults`, `test_every_basis_carries_a_kind_and_each_open_question_cites_the_ruling`, `test_the_return_resumes_after_a_local_withdrawal_per_the_d7b_ruling` (the default and every variant declare the field; the provenance cites D7b).
- Variants: `test_each_named_variant_differs_only_in_its_own_question`.
- The aliasing fix: `test_a_sides_report_does_not_share_nested_unit_data` (red before the fix, §2).
- Controls: `test_policies_are_registered_and_chosen_for_their_sides`, `test_every_order_carries_a_source_locator_or_a_label`, `test_only_the_reinforcement_variant_sends_an_order_and_only_once`.
- Mechanisms on the entry: `test_the_patrol_holds_fire_until_struck_then_returns_fire`, `test_the_command_group_yields_to_the_patrol_and_the_captives_are_conserved`, `test_raid_and_return_scores_the_entrys_raid`.
- Determinism: `test_two_headless_runs_give_the_same_battle_and_replay_identically` (two runs, equal digests, both replays `identical`; about 90 s).

No test asserts a winner. No run digest is pinned: `facing.bearing` rounds floating-point angles, which 59 §7 calls deterministic on one platform only.

## 9. Limits and next steps

- **The return.** Decided by D7b ruling 2026-11-07: "Return resumes after a local withdrawal clears." The entry now declares `resume_after_withdrawal` (60 §2; §7 row 5). The commander's runner order on the captives report was not taken. A press that pauses and resumes can repeat the cycle each time the patrol comes back into sight of a stronger group. In the EVO re-run it paused once or twice per run (§6).
- **The surrender cascade.** S57 has the commander yield his command and more prisoners taken on the north and northeast slopes. Each group yields only on its own sightings here.
- **Map.** Authored and schematic. The valley width changes the end turn and end hex of the returns (§6).
- **Run cost.** The 12 runs of §5 took from 14:25:45Z to 14:29:14Z on EVO (about 3.5 minutes), after `make test-poc` (701 tests OK, exit 0).
- Reproduce, from `apps/poc`: `python3 scripts/hill223_runs.py --dir RUNS_DIR` (one JSON line per run; `--only NAME`).
