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
| Runs | `scripts/pegasus_runs.py` | One JSON line a run |
| Tests | `tests/test_pegasus_rules.py`, `tests/test_pegasus.py` | §6 |

## 2. Rules-edition decision

The work stays in `poc-13`, as in 53. The two new rules read snapshot data that only a new entry key writes: `bridge_demolition` (written only for a `BridgeEntry` with a `demolition`) and a `victory.kind` of `seize-and-hold`. No saved game holds either. `VictoryEntry` gains `more_objectives` and `relief_turn`; `hold-objective` and `hold-compound` refuse both, so every existing entry builds the same snapshot. `PROVENANCE` gains the `inferred:` prefix of 52; that widens what registration accepts and changes no snapshot. Little Round Top, Hougoumont and Concord pins: §6.

## 3. Rules added

**Demolition triggered by the battle** (`bridges.demolish`). 53 had only an authored schedule; "demolish on contact" and "on first crossing" need the battle to fire the charges, so a `BridgeEntry` may declare a `DemolitionEntry`:

- The bridge must start wired (`charges`). At each interval start, before anyone moves, in this order:
  1. **Arm** at the first interval whose trigger holds: `contact`, a live, unrouted unit of the guard side within `reach` hexes of the bridge sees an enemy unit (`recon.sees`: within its night range and in line of sight); `crossing`, an enemy unit stands on the bridge hex. Event `demolition_armed` with the due turn.
  2. **Fire** once armed `delay` intervals ago, if a live, unrouted guard unit is within `reach` (the firing party). The bridge is `destroyed`, cause `demolished`. With no party in reach the charges stay armed and fire when one returns.
  3. **Clear**: each interval an enemy unit stands on the bridge hex counts one interval of the sappers' work; at `removal_turns` the bridge is `intact`, cause `charges_removed`, and can no longer be fired. Charges due in the interval the clearing would end are fired first.
- Observation. The `contact` trigger reads only what the guard sees. The `crossing` trigger and the clearing read true positions on the bridge hex: they stand for the guard and the sappers being on the spot, not for a report.

**Seize, then hold** (`victory.SeizeAndHold`, doc 52 §5). The attacker seizes an objective by holding the ground within `radius` (1) of it for `hold_turns` (2) intervals with no effective defender there, the `hold-objective` count kept per objective. A seizure lapses when no effective attacker remains within the radius, and must be made again. The attacker wins at the first interval at or after `relief_turn` with every objective seized, or at the deadline when there is no relief; the defender wins at the deadline otherwise, and at once when a declared bridge on an objective is destroyed. The relief is a clause of the victory rule, not arriving units (doc 52 §8 row 2). This test reads true positions: it is the authoritative capture test, kept apart from the codeword report.

**The Ham codeword is truth-based and under review.** `signals._taken` (53, unchanged here) sends Ham when a British unit stands on the bridge with no live enemy within 1 hex, reading every true enemy position in that radius with no `recon.sees` or local-contact filter. A hidden enemy can therefore change whether Ham is sent. A reviewer has raised this; until the review settles it, this document makes no claim that the codeword report is observer-safe. Headquarters still learns Ham only when the report arrives.

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
| Demolition timing | Fires 4 intervals (2 minutes) after first sight; firing reach 1 hex; sappers clear the charges in 2 intervals on the bridge | **Authored**; no source gives any of them |
| Alarm | The guard's alarm reaches the reserve by the German scripted control | **Inferred** (S54 flare; S52 sheet 2 flare before landing) |
| Reserve | R1 from the west (30, "21st Panzer", not modelled as armour), R2 from the south (60, infantry and self-propelled guns), ordered at turns 170 (01:50) and 290 (02:50) to reach the bridge near S54's 02:00 and 03:00 | Times sourced, secondary (S54; S51 "within an hour"); groups, strengths and march allowances authored |
| Relief | Relief turn 360, 3 hours after landing; deadline 360 | Sourced: S51 p. 1 para 3 |
| Codeword | Ham, canal bridge taken; Jam for the Orne bridge in the variants that hold it | Sourced, secondary: S54. Trigger authored, truth-based, under review (§3) |
| Night sight | 2 hexes for every unit | Assumption (doc 52 §8 row 1) |
| Weapon range | One 2-hex range, rifle-baseline effect, for every unit | Assumption (doc 52 §8 row 6) |
| Radio | `wwii-1944-radio-v1`: voice 2 hexes, radio 10 hexes, runner beyond, both sides | Assumption (53) |
| Map | Canal and Orne ten hexes (500 m) apart (S54); each steps one column west below its bridge so each ring has two hexes a bank; marsh between (S54) | Authored, not surveyed |

The scripted controls (`pegasus_policy.BRITISH_ORDERS`, `GERMAN_ORDERS`) carry their own locators. British S1: 25 to the far (west) end of the bridge, 24 onto the bridge with the sapper officer, 14 to the west-bank bridgehead (S51 p. 1 para 3; S52 sheet 2), then 25 and 14 dig in once headquarters has received Ham. German G1: the guard holds (entry data) and the reserve groups are ordered forward at their alarm turns. German G2 (early alarm): both groups at the first decision at or after touchdown plus one minute.

## 5. Runs (model results)

Every run is headless on its own SQLite database on EVO (`python3 scripts/pegasus_runs.py --only <name> --dir <dir>`, branch `d2-pegasus-scenario`), scripted against scripted, and every one replays `identical`. The engine draws no random number, so the scenario is not stochastic; each run was made under two Python hash seeds (`PYTHONHASHSEED` 1 and 2) and the JSON lines compared (§6). Times are scenario local time (turn 0 = 00:25:00, 30 seconds a turn).

**Named variants and range sensitivity** (the brief's set):

| Run | Winner | Ends | Canal (or Orne) bridge | Seized | Codeword sent → heard (turn) | Losses British / German | Reserve first fires R1 / R2 |
|---|---|---|---|---|---|---|---|
| baseline | German | turn 5, 00:27:30 | armed 1 (contact), destroyed 5 | never | none | 3/105, 12/143 | not engaged |
| both-bridges | German | turn 5, 00:27:30 | canal armed 1, destroyed 5; Orne armed 5 | never | none | 3/165, 12/155 | not engaged |
| orne-platoons | British | turn 360, 03:25 | Orne armed 2, cleared 10 | turn 4; lapsed 326; seized again 330 | Jam 8 → 9 | 23/75, 28/117 | 188 / 310 |
| guard-only | British | turn 360, 03:25 | wired, never fired | turn 10 | Ham 11 → 12 | 35/105, 47/143 | 177 / 299 |
| demolish-on-crossing | British | turn 360, 03:25 | armed 12 (crossing), cleared 14 | turn 10 | Ham 11 → 12 | 35/105, 47/143 | 177 / 299 |
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
| delay-16 | British | turn 360 | armed 1, cleared 14 | turn 10 | 11 → 12 | 35/105, 47/143 | 177 / 299 |
| delay-32 | British | turn 360 | armed 1, cleared 14 | turn 10 | 11 → 12 | 35/105, 47/143 | 177 / 299 |

What the crossed runs show (model results):
- **The race.** The sappers' clearing ends at turn 14 in every run that gets that far. With the contact trigger armed at turn 1 and fire-first ordering, a delay of 13 intervals or less fires the bridge while a guard post is still in reach (delay-8: turn 9), and 14 or more lets it be cleared (derived from the runs at 4, 8, 16 and 32; 9 to 15 were not run). `demolish-on-crossing` arms only when a British platoon is on the bridge, at turn 12, so the clearing always wins with the default delay. Once cleared, the run is the guard-only run: same losses, same seizure.
- **Weapon range.** On the guard-only bridge all three ranges seize at turn 10 or 11 and hold to relief. Range 3 differs from range 2 only through the local threat check (`tactics_v10.threat_range`), because fire cannot reach past the 2-hex night sight. Range 1 costs the platoons more (45 against 35) and two platoons rout.
- **Alarm.** With the alarm at the S54 times the reserve arrives after the bridge is seized and dug in, and both groups rout. With the alarm at touchdown plus one minute it fires at turns 12 and 14, routs 25 and 14 Platoons and retakes the ring at turn 34; the British do not seize it again. This is the one run where the timing of the German reaction decides the outcome on an intact bridge.
- **Relief.** Relief at one hour wins at 01:25 before either reserve group fires. No relief: the bridge is still held at 04:25.
- **Orne alone.** 17 and 23 Platoons seize the Orne bridge at turn 4 and the sappers clear it at turn 10 (the Orne guard routs at once, so no firing party remains); the south group retakes the ring for four intervals near 03:08 (turns 326 to 330).
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
- Pins: the Little Round Top, Hougoumont and Concord digests and replays are untouched (`test_poc13b.py`, `test_poc13.py`, `test_concord_sensitivity.py`; no digest edited). `test_scenario_sides` lists the new kind. A new pin, `BASELINE_RUN_SHA256` in `tests/test_pegasus.py`, fixes the Pegasus baseline run.
- Two hash seeds: all 18 runs of §5 were made under `PYTHONHASHSEED=1` and `=2`; the 18 pairs of JSON lines are byte-identical.
- Gates on EVO: `npm run typecheck` exit 0; `make test-poc` exit 0 (479 Python tests OK, both JavaScript checks passed); `make smoke-poc` exit 0; headless Little Round Top (Union, turn 60), Hougoumont (Allied, turn 60), Concord (provincial, turn 8) and Pegasus (German, turn 5) all replay `identical`.

## 8. Limits and open items

- The default outcome rests on authored demolition timings (§5). A source for the guard's firing arrangements, or for whether the charges were fitted, would replace them.
- The Ham trigger reads true enemy positions within 1 hex of the holder (§3); under review.
- The reserve is two authored groups ordered at authored turns so they arrive near the S54 times. Their arrival time is an input, not a result. Armour and the PIAT are not modelled apart (one weapon range).
- Units are all on the map at turn 0; the landing order (S2 of doc 52 §9) and the gliders' arrival are not modelled. 22 Platoon (landed near the Dives) is left out.
- The relief is a victory clause. 7 Para does not appear on the map and cannot fight the 03:00 attack.
- A unit on a bridge when it is destroyed stays on the hex (53).
- The scripted British control sends at most three orders a decision; in `both-bridges` the Orne platoons get theirs at turn 3.
- The map is authored. The café, the pillbox "to the north" and the canal-bank heights are not placed.
- A 360-turn run takes about 2.5 minutes on EVO and a 480-turn run about 5, because each revision stores the whole snapshot.
