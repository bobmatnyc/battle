# 54 — Pegasus Bridge: the scenario entry, its variants and the runs

**Date:** 2026-11-06. **Requirement:** the Pegasus Bridge scenario planned in [52](52-pegasus-bridge-scenario-plan.md), built on the 1944 rules of [53](53-pegasus-engine-and-data.md): a catalog entry (canal bridge only by default), scripted intents for both sides, a seize-then-hold victory, doc 52's named variants, a 1/2/3-hex weapon-range sensitivity, headless runs with replay, and this comparison. No outcome is fitted: no value below was changed after a run to move a result toward the record.

Labels follow 52: **sourced** (S-id and locator; Sources S50 to S56 in [09](09-sources.md#pegasus-bridge-source-pass--2026-11-06)), **inferred** (a reading from sourced facts), **reconstruction** (an authored behaviour standing in for what no source states), **authored** (a POC choice with no source). **Model result** marks what the simulation produced.

## 1. What was built

| Part | Where | Notes |
|---|---|---|
| Entry `pegasus-bridge` | `battle/scenario_pegasus.py` | Headless catalog only (`bootstrap.HEADLESS_SCENARIOS`); the command desk cannot draw water yet, as for Concord |
| Variants | `scenario_pegasus.VARIANTS` | The seven named in the brief, each with its doc 52 question and source |
| Range sensitivity | `scenario_pegasus.RANGE_SENSITIVITY` | One weapon range of 1 or 3 hexes; the baseline is 2 |
| Crossed sensitivity | `scenario_pegasus.CROSSED_SENSITIVITY` | Added after the first runs (§5): the relief, alarm and range questions on the guard-only bridge, and a demolition-delay sweep. In no catalog |
| Scripted controls | `battle/pegasus_policy.py` | British S1 coup de main; German G1 guard and alarm; German G2 early alarm |
| Demolition trigger | `bridges.demolish`, `scenario_wwii.DemolitionEntry` | New rule, off unless a bridge declares it (§3) |
| Victory kind `seize-and-hold` | `victory.SeizeAndHold` | New kind, named only by this entry (§3) |
| Runs | `scripts/pegasus_runs.py` | One JSON line a run. Since bt-T02 each run is stored by `battle/batch_store.py` (inputs and a digest per revision, full snapshots at start and end; `--full-snapshots` for the old store); a 360-turn run fell from 1.2 GB to 26 MB, and the JSON line is byte-identical |
| Tests | `tests/test_pegasus_rules.py`, `tests/test_pegasus.py` | §6 |

## 2. Rules-edition decision

The work stays in `poc-13`, as in 53. The two new rules read snapshot data that only a new entry key writes: `bridge_demolition` (written only for a `BridgeEntry` with a `demolition`) and a `victory.kind` of `seize-and-hold`. No saved game holds either. `VictoryEntry` gains `more_objectives` and `relief_turn`; `hold-objective` and `hold-compound` refuse both, so every existing entry builds the same snapshot. `PROVENANCE` gains the `inferred:` prefix of 52; that widens what registration accepts and changes no snapshot. Little Round Top, Hougoumont and Concord pins: §6.

## 3. Rules added

**Demolition triggered by the battle** (`bridges.demolish`). 53 had only an authored schedule; "demolish on contact" and "on first crossing" need the battle to fire the charges, so a `BridgeEntry` may declare a `DemolitionEntry`:

- The bridge must start wired (`charges`). At each interval start, before anyone moves, in this order:
  1. **Arm** at the first interval whose trigger holds, as seen by a live, unrouted unit of the guard side within `reach` hexes of the bridge (`recon.sees`: within its night range and in line of sight): `contact`, it sees any enemy unit; `crossing`, it sees an enemy unit on the bridge hex. Event `demolition_armed` with the due turn.
  2. **Fire** once armed `delay` intervals ago, if any live, unrouted unit of the guard side is within `reach` (the firing party). The party need not be the unit that saw the trigger or any post of the bridge guard: a reserve group that comes within reach later fires charges armed earlier. The bridge is `destroyed`, cause `demolished`. With no party in reach the charges stay armed, with no time limit, and fire when any unit of that side comes within reach. **Authored** rule: no source says who could fire the charges, or whether a unit that arrived later knew they were armed. The `orne-platoons` result rests on it (§5, "Orne alone").
  3. **Clear**: each interval an enemy unit that declares `clears_charges` stands on the bridge hex counts one interval of the sappers' work. `clears_charges` is a unit override, off unless declared and refused unless true or false; a unit without it never clears the charges (`test_a_unit_without_sappers_never_clears_the_charges`). Before the fix round any enemy unit on the bridge cleared them; at `removal_turns` the bridge is `intact`, cause `charges_removed`, and can no longer be fired. Charges due in the interval the clearing would end are fired first.
- Observation. Both triggers read only what a guard within reach sees: an enemy the guard cannot observe does not change the arming decision (`test_crossing_with_no_guard_within_reach_arms_nothing`, `test_crossing_the_guard_cannot_see_arms_nothing`, `test_an_enemy_the_guard_cannot_observe_does_not_change_the_arming_decision`). Firing needs a guard in reach, not a sighting. The clearing reads true positions on the bridge hex: it is the sappers' own work, not a decision by either side. (Fix round on `ee9dd07`: the crossing trigger had armed on any enemy on the bridge, with no guard in reach and no sighting.)

**Seize, then hold** (`victory.SeizeAndHold`, doc 52 §5). The attacker seizes an objective by holding the ground within `radius` (1) of it for `hold_turns` (2) intervals with no effective defender there, the `hold-objective` count kept per objective. A seizure lapses when no effective attacker remains within the radius, and must be made again. The attacker wins at the first interval at or after `relief_turn` with every objective seized, or at the deadline when there is no relief; the defender wins at the deadline otherwise, and at once when a declared bridge on an objective is destroyed. The relief is a clause of the victory rule, not arriving units (doc 52 §8 row 2). This test reads true positions: it is the authoritative capture test, kept apart from the codeword report.

**The Ham report decision reads only what the holder sees.** `signals._taken` picks the holder (the lowest-id live, unrouted British unit on the bridge) and then counts an enemy within the signal's radius only if the holder sees it (`recon.sees`). Two states that differ only in an enemy the holder cannot observe give the same Ham decision (`test_an_enemy_the_holder_cannot_observe_does_not_change_the_ham_decision`); an enemy it does see still stops Ham (`test_an_enemy_the_holder_sees_within_the_radius_still_stops_ham`). Before the fix round, `_taken` (53) read every true enemy position in the radius. Headquarters still learns Ham only when the report arrives. The codeword is what the holder believes and reports; the capture test above stays truth-based.

## 4. The entry: sourced facts, inferred defaults, authored values

| Item | Value | Label |
|---|---|---|
| Place, date, start | Caen Canal bridge, Bénouville; 6 June 1944; 00:25, the first glider down | Sourced: S51 p. 1 paras 2-3 |
| Weather | A cloudy night | Sourced: S52 sheet 2 |
| British task | Seize the bridge intact; hold until relieved | Sourced: S51 p. 1 paras 2-3; S52 sheet 1 §2; S54 |
| Platoons | 25 (Brotheridge), 24 (Wood, with Capt Neilson RE), 14 (B Coy, Smith); 17 (Fox) and 23 (Sweeney) at the Orne | Sourced: S51 p. 1 para 3; S52 sheets 2-3 |
| Platoon strength | 30 each; headquarters detachment 15 | Authored (doc 52 §6) |
| Placement | At touchdown, turn 0: 25 beside the bridge, 24 and 14 within two hexes; the landing order is not modelled | Reconstruction: S51 (80 ft, 50 yards); doc 52 §8 row 2 |
| German guard | 50 men in all: posts of 14, 12, 12 at the canal bridge, 12 at the Orne | Sourced as to 50 (S51 p. 1 para 2, S54); split authored |
| German defences | Machine-gun posts and trenches on the west bank, machine gun and anti-tank gun on the east bank, Orne pillbox east bank; hexes and cover authored; the pillbox "to the north" of the canal bridge not placed | Sourced: S54; positions authored |
| Guard intent | Hold the posts; fire the charges on contact | **Inferred** (S54 secondary, no primary; Architect default) |
| Sappers | Only 24 Platoon declares `clears_charges`: glider No. 92 carried 24 Platoon and Capt Neilson RE (S52 sheet 2), and sappers "cut wires and removed charges" at the canal bridge (S51 p. 1 para 3). S51 and S52 name no sappers with the other platoons, so none is declared; in `orne-platoons` no unit can clear the Orne charges | Sourced as to who carried them; the clearing behaviour and time are authored and not validated |
| Demolition timing | Fires 4 intervals (2 minutes) after first sight; firing reach 1 hex; sappers clear the charges in 2 intervals on the bridge | **Authored**; no source gives any of them |
| Firing party | Any live, unrouted German unit within reach fires armed charges, not only the guard that armed them, with no time limit (§3 step 2) | **Authored**; no source. The `orne-platoons` result rests on it |
| Alarm | The guard's alarm reaches the reserve by the German scripted control | **Inferred** (S54 flare; S52 sheet 2 flare before landing) |
| Reserve | R1 from the west (30, "21st Panzer", not modelled as armour), R2 from the south (60, infantry and self-propelled guns), ordered at turns 170 (01:50) and 290 (02:50) to reach the bridge near S54's 02:00 and 03:00 | Times sourced, secondary (S54; S51 "within an hour"); groups, strengths and march allowances authored |
| Relief | Relief turn 360, 3 hours after landing; deadline 360 | Sourced: S51 p. 1 para 3 |
| Codeword | Ham, canal bridge taken; Jam for the Orne bridge in the variants that hold it | Sourced, secondary: S54. Trigger authored; counts only enemies the holder sees (§3) |
| Night sight | 2 hexes for every unit | Assumption (doc 52 §8 row 1) |
| Weapon range | One 2-hex range, rifle-baseline effect, for every unit | Assumption (doc 52 §8 row 6) |
| Radio | `wwii-1944-radio-v1`: voice 2 hexes, radio 10 hexes, runner beyond, both sides | Assumption (53) |
| Map | Canal and Orne ten hexes (500 m) apart (S54); each steps one column west below its bridge so each ring has two hexes a bank; marsh between (S54) | Authored, not surveyed |

The scripted controls (`pegasus_policy.BRITISH_ORDERS`, `GERMAN_ORDERS`) carry their own locators. British S1: 25 to the far (west) end of the bridge, 24 onto the bridge with the sapper officer, 14 to the west-bank bridgehead (S51 p. 1 para 3; S52 sheet 2), then 25 and 14 dig in once headquarters has received Ham. German G1: the guard holds (entry data) and the reserve groups are ordered forward at their alarm turns. German G2 (early alarm): both groups at the first decision at or after touchdown plus one minute.

## 5. Runs (model results)

Every run is headless on its own SQLite database on EVO (`python3 scripts/pegasus_runs.py --only <name> --dir <dir>`, branch `d2-pegasus-scenario`, after the fix round), scripted against scripted, and every one replays `identical`. The engine draws no random number, so the scenario is not stochastic; each run was made under two Python hash seeds (`PYTHONHASHSEED` 1 and 2) and the JSON lines compared (§6). Times are scenario local time (turn 0 = 00:25:00, 30 seconds a turn).

**Named variants and range sensitivity** (the brief's set):

| Run | Winner | Ends | Canal (or Orne) bridge | Seized | Codeword sent → heard (turn) | Losses British / German | Reserve first fires R1 / R2 |
|---|---|---|---|---|---|---|---|
| baseline | German | turn 5, 00:27:30 | armed 1 (contact), destroyed 5 | never | none | 3/105, 12/143 | not engaged |
| both-bridges | German | turn 5, 00:27:30 | canal armed 1, destroyed 5; Orne armed 5 | never | none | 3/165, 12/155 | not engaged |
| orne-platoons | German | turn 191, 02:00:30 | Orne armed 2, never cleared, destroyed 191 | turn 4 | Jam 8 → 9 | 2/75, 8/117 | 188 / not engaged |
| guard-only | British | turn 360, 03:25 | wired, never fired | turn 10 | Ham 11 → 12 | 35/105, 47/143 | 177 / 299 |
| demolish-on-crossing | British | turn 360, 03:25 | never armed; cleared 15 | turn 10 | Ham 11 → 12 | 35/105, 47/143 | 177 / 299 |
| relief-1h | German | turn 5 | as baseline | never | none | 3/105, 12/143 | not engaged |
| no-relief | German | turn 5 | as baseline | never | none | 3/105, 12/143 | not engaged |
| early-alarm | German | turn 5 | as baseline | never | none | 3/105, 12/143 | not engaged |
| range-1 | German | turn 5 | as baseline | never | none | 0/105, 11/143 | not engaged |
| range 2 (baseline) | German | turn 5 | armed 1, destroyed 5 | never | none | 3/105, 12/143 | not engaged |
| range-3 | German | turn 5 | as baseline | never | none | 5/105, 12/143 | not engaged |

**Finding.** Under the binding default the guard sees the platoons at touchdown (they land one hex from its posts, inside the 2-hex night sight), the charges are armed at turn 1 and fired at turn 5 by the west-bank posts, which the platoons cannot reach across the canal in two minutes. The relief, alarm and range variants change nothing that happens before turn 5, so they end the same way. The outcome is set by two authored numbers, the 4-interval delay and the 2-interval clearing, not by any sourced fact.

**Crossed sensitivity** (added after the runs above; labelled `sensitivity`, in no catalog). The same questions on the guard-only bridge, and a sweep of the demolition delay with the contact trigger:

| Run | Winner | Ends | Bridge | Seized | Ham sent → heard | Losses British / German | R1 / R2 first fire |
|---|---|---|---|---|---|---|---|
| guard-only+range-1 | British | turn 360 | never fired | turn 11 | 12 → 13 (sent by D24) | 45/105, 38/143 | 178 / 301 |
| guard-only (range 2) | British | turn 360 | never fired | turn 10 | 11 → 12 | 35/105, 47/143 | 177 / 299 |
| guard-only+range-3 | British | turn 360 | never fired | turn 10 | 10 → 11 | 37/105, 48/143 | 177 / 299 |
| guard-only+relief-1h | British | turn 120, 01:25 | never fired | turn 10 | 11 → 12 | 5/105, 15/143 | not engaged |
| guard-only+no-relief | British | turn 480, 04:25 (held to the deadline) | never fired | turn 10 | 11 → 12 | 35/105, 47/143 | 177 / 299 |
| guard-only+early-alarm | German | turn 360 | never fired | turn 10; lapsed 34 | 11 → 12 | 45/105, 37/143 | 12 / 14 |
| delay-8 | German | turn 9, 00:29:30 | armed 1, destroyed 9 | never | none | 5/105, 15/143 | not engaged |
| delay-9 to delay-16 (8 runs), delay-32 | British | turn 360 | armed 1, cleared 15 | turn 10 | 11 → 12 | 35/105, 47/143 | 177 / 299 |

What the crossed runs show (model results):
- **The race.** Measured with the contact trigger armed at turn 1: delays 4 and 8 fire the bridge (turns 5 and 9); every delay from 9 to 16, and 32, leaves it unfired and 24 Platoon's sappers clear it at turn 15 (turn 14 before the fix round, when any unit on the bridge could clear it). The boundary lies between 8 and 9. The charges fire only while a guard is within reach; the seizure at turn 10 means no effective German remains in the ring by then, so a charge due at turn 10 or later finds no firing party. (The first version of this document gave 13/14, derived from four runs and the clearing turn alone; it was wrong.) `demolish-on-crossing` now never arms: when a British platoon first stands on the bridge, no guard within reach is left to see it. Once cleared, the run is the guard-only run: same losses, same seizure.
- **Weapon range.** On the guard-only bridge all three ranges seize at turn 10 or 11 and hold to relief. Range 3 differs from range 2 only through the local threat check (`tactics_v10.threat_range`), because fire cannot reach past the 2-hex night sight. Range 1 costs the platoons more (45 against 35) and two platoons rout.
- **Alarm.** With the alarm at the S54 times the reserve arrives after the bridge is seized and dug in, and both groups rout. With the alarm at touchdown plus one minute it fires at turns 12 and 14, routs 25 and 14 Platoons and retakes the ring at turn 34; the British do not seize it again. This is the one run where the timing of the German reaction decides the outcome on an intact bridge.
- **Relief.** Relief at one hour wins at 01:25 before either reserve group fires. No relief: the bridge is still held at 04:25.
- **Orne alone.** 17 and 23 Platoons seize the Orne bridge at turn 4 and Jam reaches headquarters at turn 9. The charges were armed at turn 2, but the Orne guard routs at once, so no firing party remains. Neither platoon carries sappers (S51 and S52 name none with them), so the charges stay in place. The west group, ordered forward at its alarm turn, first fires at turn 188 near the Orne bridge; once it is within reach it fires the charges the Orne guard armed 189 intervals earlier, at turn 191 (02:00:30), and the Germans win. That rests on the authored firing rule of §3 step 2: any live, unrouted German unit within reach fires armed charges, however long ago they were armed and whichever unit saw the trigger. Under a rule that let only the arming guard, or only a unit present when they were armed, fire them, no firing party would remain after the Orne guard routs, and the result would turn on the fight with the reserve instead; that alternative was not run. Before the fix round any unit on the bridge cleared the charges at turn 10 and the British held to relief. This variant shows the result resting on who may clear the charges and on who may fire them.
- **The codeword is not a capture test.** In `guard-only+early-alarm` headquarters holds Ham from turn 12 while the seizure lapses at turn 34: the codeword says the bridge was taken, and nothing tells headquarters it was lost ("Jack" and "Lard" are not modelled, 53). The victory test reads the ground; the codeword is only what the holder reported.

## 6. Comparison with the record (no fitting)

The fixture's `comparison` asks when each bank is secured, whether the bridge stays passable, and when headquarters learns the outcome.

| Question | Record | Model, default | Model, guard-only |
|---|---|---|---|
| Bridge passable | Both bridges taken intact (S51 p. 1 para 3; S52 sheet 4) | No: fired at 00:27:30 | Yes |
| Canal bridge secured | Captured and consolidated "within 15 mins" of 00:25 (S51) | Never | Seized 00:30 (turn 10) |
| Headquarters learns | Ham sent (S54, secondary; time not stated) | Never | Ham heard at 00:31 (turn 12), by radio |
| Armour attack | "Within an hour" (S51) or 02:00 (S54); one tank disabled, the rest withdrew | Not reached | First fire 01:53:30; the group routs. **Set by the authored alarm turn, not a result** |
| Relief | About 3 hours after landing (S51) | Not reached | Held to 03:25 |
| British losses | 1 officer and 3 other ranks killed, 2 officers and 15 wounded, 3 missing, for both bridges (S51 p. 2) | 3 of 105 at the canal bridge | 35 of 105. An order-of-magnitude check only; the model has no wounded/killed split and the reserve is authored |

The default disagrees with the record on the one question the scenario turns on, and it does so through authored timings. Doc 52 §3 notes S51's outcome: the sappers removed the charges in the first minutes. Whether the guard could have fired them sooner is not in any source read; this document does not change the delay to match the record.

## 7. Verification

- Probes first: `tests/test_pegasus_rules.py` was written before the rules. Against the entry records only (`DemolitionEntry`, the two `VictoryEntry` fields), 15 of 15 tests failed (18 failures, 6 errors counting subtests). They pass after.
- Fix round (review of `ee9dd07` and `de11056`): the sight, sapper and formation tests were written first. Against `ee9dd07` on EVO, 10 checks fail (counting subtests); the two controls (an enemy the holder sees still stops Ham; a unit without sappers still splits) pass there and after, as they should.
- Pins: the Little Round Top, Hougoumont and Concord digests and replays are untouched (`test_poc13b.py`, `test_poc13.py`, `test_concord_sensitivity.py`; no digest edited). `test_scenario_sides` lists the new kind. A new pin, `BASELINE_RUN_SHA256` in `tests/test_pegasus.py`, fixes the Pegasus baseline run; it was re-pinned in the fix round because 24 Platoon's unit record gained `clears_charges` (the outcome is unchanged: German, turn 5).
- Two hash seeds: all 25 runs of §5 were made under `PYTHONHASHSEED=1` and `=2` at `de11056`; the 25 pairs of JSON lines are byte-identical and all 50 replay `identical`. `a541b03` changes only split/combine, which no Pegasus run uses; the baseline digest test passes at `a541b03`.
- Gates on EVO at `a541b03`: `npm run typecheck` exit 0; `make test-poc` exit 0 (490 Python tests OK, both JavaScript checks passed); `make smoke-poc` exit 0; headless Little Round Top (Union, turn 60), Hougoumont (Allied, turn 60), Concord (provincial, turn 8) and Pegasus (German, turn 5) all replay `identical`.

## 8. Limits and open items

- The sapper capability is a declared flag on one platoon; it has no strength, loss or tool model of its own, and its behaviour is not validated against any source.
- **D2 restriction:** a unit with `clears_charges` can neither split nor combine, in either direction, until attachments can be allocated: a split would copy the capability to both halves and a combine could drop it. `formations.validate` refuses the request and `formations.progress` refuses it again at execution (`test_split_of_a_sapper_unit_is_refused_at_request`, `test_combine_is_refused_at_request_whichever_unit_carries_sappers`, `test_split_applied_after_the_unit_gained_sappers_is_refused_at_execution`). Units without the key reorganize as before.
- The default outcome rests on authored demolition timings (§5). A source for the guard's firing arrangements, or for whether the charges were fitted, would replace them.
- The `orne-platoons` outcome rests on the authored firing-party rule (§3 step 2): armed charges stay armed with no time limit and any unit of the guard side within reach fires them. A rule that tied firing to the arming guard, or to a unit that knew the charges were armed, would change that result.
- No report tells headquarters that a bridge it heard Ham for has been lost (§5; "Jack" and "Lard" are not modelled).
- The reserve is two authored groups ordered at authored turns so they arrive near the S54 times. Their arrival time is an input, not a result. Armour and the PIAT are not modelled apart (one weapon range).
- Units are all on the map at turn 0; the landing order (S2 of doc 52 §9) and the gliders' arrival are not modelled. 22 Platoon (landed near the Dives) is left out.
- The relief is a victory clause. 7 Para does not appear on the map and cannot fight the 03:00 attack.
- A unit on a bridge when it is destroyed stays on the hex (53).
- The scripted British control sends at most three orders a decision; in `both-bridges` the Orne platoons get theirs at turn 3.
- The map is authored. The café, the pillbox "to the north" and the canal-bank heights are not placed.
- A 360-turn run takes about 2.5 minutes on EVO and a 480-turn run about 5, because each revision stores the whole snapshot.
