# 68 — Cannae: the scenario entry, its defaults and deviations

**Date:** 2026-11-07. **Requirement:** the army-scale Cannae planned in [63](63-cannae-scenario-plan.md), with every default of 63 §8 except row 17 and the named variants of 63 §8 that the engine can build. **Ruling:** D86 (Bob 2026-11-07 13:10Z), "Accept doc 63 defaults (A, designed yield, scripted orders, sources in parallel)": scale option A (63 §9 q1), the designed yield C1 as the default and no design C2 as a variant (q5), scripted controls issuing each sector's orders before sector commanders exist (q10), and the source pull in parallel with the runs, not before them (q11). Every other 63 §9 question takes 63's proposal. **Results** are in §6 and §6.1, from the EVO runs `bt05r-d829763` at `d829763`.

Labels follow 63: **sourced** (S65 to S70, [09](09-sources.md#cannae-source-pass--2026-11-07)), **inferred**, **reconstruction**, **authored**. A value 63 leaves open is an authored default; its change site carries `# D86 (Bob 2026-11-07 13:10Z): doc 63 defaults` or a provenance field that names D86.

## 1. What was built

| Part | Where | Notes |
|---|---|---|
| Entry `cannae-envelopment` | `battle/scenario_cannae.py` | Headless catalog only (`bootstrap.HEADLESS_SCENARIOS`), as Pegasus, Hill 223 and Gergovia (63 §9 q12) |
| Variants | `scenario_cannae.VARIANTS` | 13 entries (§5) |
| Scripted controls | `battle/cannae_policy.py` | Roman R1 and R2, Carthaginian C1, three `cavalry-delayed` controls and `deserters`, registered in `command_policy`; every order has a source locator or a label |
| Army-scale rules | `battle/army.py`, `battle/scenario_army.py` | 63 §10 gaps 1 to 4 and 6 (§2) |
| Victory `encircle` | `battle/victory_encircle.py` | 63 §5 and gap 7 |
| Profiles | `comms.ROMAN_216`, `comms.CARTHAGE_216`; `SideEntry.communications` | 63 gap 8 |
| Runs | `scripts/cannae_runs.py` | One JSON line a run, stored by `battle/batch_store.py`, with the closing replay check |
| Tests | `tests/test_army.py`, `tests/test_cannae.py`; `tests/test_scenario_catalog.py` (headless id list), `tests/test_scenario_sides.py` (kind list) | §7 |

## 2. Engine changes, all opt-in

Every rule below is read only when the snapshot carries `army_rules` (written by `scenario_army.setup` for an entry that declares `army`), or when the entry names `encircle`, or a side names its own profile. No saved poc-13 game has any of these, so every one replays as recorded (AGENTS.md, [60](60-broadcast-signal-exploit-and-recover-force.md) §5). No new rules edition: as in 53, 59 and 60, only a new entry declares the data.

| 63 §10 gap | Change | Where |
|---|---|---|
| 1 Declared scale | The validator accepts 200 m and 180 s (`ARMY_SCALES`) for an entry with army rules; any other scale is refused. The delivery estimate reads the snapshot's `seconds_per_turn` (30 in every other battle, so its text is unchanged). The snapshot stores `metres_per_hex` only under army rules. The other readers already took the entry's values (`analysis.py`, `static/app.js`, the prompt) | `scenario_army.problems`, `engine.estimate` |
| 2 Per-unit speed | Unit key `move_rate` (1 to 3). A unit earns its move credit times its rate and takes up to that many steps an interval; each further step has its own contest for free hexes | `engine.step`, `engine.relocate`, `army.rate` |
| 3 Losses and morale | A volley fires `engaged_pct` of the unit's strength; a shock class (`shock_classes`) spends no ammunition; suppression grows with the engaged men as a share of the target's strength; morale falls `morale_per_pct` points per per cent of starting strength lost, the remainder carried in `morale_credit`; a move under an ordered retreat keeps the front | `army.volley`, `army.morale_loss` |
| 4 Flank and rear | Every unit has a `front` (each side's bearing at the start; a forward move, an attack or a flight turns it; a yield or other step back keeps it). A blow from 60 degrees or less is frontal, 150 or more is in the rear, the rest a flank; the loss is multiplied by `flank_pct` or `rear_pct` and the extra share counts again toward morale | `army.aspect`, `army.moved` |
| 5 Sector commanders | **Not built** (D86: scripted orders; 63 §9 q10) | — |
| 6 Wheel and yield | Unit keys `yield` {`limit`, `rear_step`} and `wheel` {`reach`, `front_row`, `rear_step`}, read from the unit's own sightings (§3) | `army.doctrine` |
| 7 Enclosure and `encircle` | §4 | `victory_encircle` |
| 8 Profiles | `roman-216-v1` (trumpet, voice, mounted messenger) and `carthage-216-v1` (voice, mounted messenger), both at the engine's messenger rates with the entry's voice reach; a side may name its own profile | `comms.py`, `scenario_command.side_profile_problems` |
| 9 Run time | Measured in [66](66-cannae-gap9-run-time.md); §6 | — |

One change beyond 63's list: under army rules a contact of a routed enemy carries `routed: true` (`recon.scan`), so that Hasdrubal's trigger, "the Roman right cavalry routed or lost" (63 §8 row 20), can be read from the Carthaginian side's delivered view.

**Opt-in proof.** `test_every_saved_poc13_entry_plays_as_recorded` plays each of the seven earlier poc-13 headless entries for 40 engine intervals and compares the SHA-256 of the snapshot with the value recorded at `5704c40`, before any change. All seven are equal. Against the pre-change `engine.py` and `recon.py`, 9 of the 25 tests then present in `test_army.py` fail (the behaviours above); against the pre-change `scenario_entry.py` the module cannot load (no `communications` side field).

## 3. The entry and its defaults

Every value 63 §8 sets is used as written, except row 17 (§3.2).

| 63 §8 | Value | Where it is used |
|---|---|---|
| 1-3 | 200 m, 180 s, 24 by 21 | `METRES_PER_HEX`, `SECONDS_PER_TURN`, `MapEntry` |
| 4-5 | 08:00 to 16:00, 160 intervals | `start_time`, `DEADLINE` |
| 6-7 | Roman 16 × 3,550, 4 × 3,500, 1,600, 2 × 2,400; Carthaginian 2 × 5,000, 8 × 2,750, 3 × 2,670, 3 × 2,170, 2 × 1,750 (40,010 foot) | `roman_units`, `carthaginian_units` |
| 8 | Block 8 wide (columns 13 to 20), 2 deep, legions in front (row 11), *alae* behind (row 12) | `BLOCK_COLS` |
| 9 | Crescent C3 to C6 one hex ahead (row 8) of C1, C2, C7, C8 (row 7) | `CRESCENT` |
| 10 | 3 hexes from the Roman front row to the crescent | rows 11 and 8 |
| 11 | River lane 2 hexes (columns 21 and 22) beside an impassable river (column 23) | `LANE_COLS`, `RIVER_COL` |
| 12 | Heavy 100, light 40, every class range 1 | `WEAPONS` |
| 13 | Cavalry 3 hexes an interval | `move_rate` 3 |
| 14 | Sight 7 hexes | the engine cap; no override |
| 15-16 | Voice 1 hex; messenger 2 open hexes an interval, expiry 20 | `voice_reach`, the profiles |
| 17 | Battle signal reach 6 hexes | recorded as `SIGNAL_REACH`, not sounded (§3.2) |
| 18 | Yield limit 3 | `YIELD` on C1 to C8 |
| 19 | Wheel: a Roman unit past the African's front row within 2 hexes | `wheel()` on AF1 and AF2 |
| 20 | Hasdrubal's trigger: the Roman right cavalry routed or lost | `cannae_policy._horse_gone` |
| 21 | Roman press: `exploit` to the Carthaginian rear row, `recall_binding` false, `max_loss_pct` 50 | `press()` on the 16 heavy units |
| 22-24 | `zoc` 1, `min_enclosed_pct` 50, `centre_break` 5 of 8 | `VictoryEntry` |
| 25 | Three exits on the Roman edge | `EXITS` |
| 26 | Morale and loss scaling, values set at implementation | `ARMY` (§3.1) |
| 27 | Roman player, Varro at SC1 | `player_side`, `command_unit` |

### 3.1 Authored defaults (63 leaves the value open)

Each is labelled in the entry's `provenance` or at its change site with the D86 line.

| Value | Default | Basis |
|---|---|---|
| Engaged share of a volley (`engaged_pct`) | 13 per cent | A 200 m front of a block about 35 deep fights with a few ranks; two equal heavy units then lose about 1 per cent an interval, so a frontal fight lasts hours (63 gap 3's target) |
| Morale per per cent lost (`morale_per_pct`) | 2 | From 85 a unit routs below 28, 58 points: about 29 per cent of its strength lost frontally, less any recovery between fights. The remainder below a point carries to the next interval (`morale_credit`), so small losses add up |
| Flank and rear (`flank_pct`, `rear_pct`) | 150 and 200 per cent, in men and again in morale | Authored; S65 III.115-116 give the effect, not a ratio |
| Aspect bounds | front within 60 degrees, rear from 150 | Two front, two flank and two rear hexes for a unit facing up or down the map |
| Fronts | Roman 0, Carthaginian 180 | Up and down the map; no compass bearing (63 §7) |
| Suppression at army scale | `max(2, 25 × engaged men ÷ target strength)` | The company rule (`rounds ÷ 4`) would pin every unit in contact at once (70 is the pin) |
| Ammunition | heavy classes 2 per man (never spent), light classes 3 per man | Light troops skirmish about 15 volleys before their reserve trigger |
| "Pressed" for a yield | under fire last interval with an enemy it sees adjacent | Authored reading of 63 §3 C1 |
| "Past the front row" for a wheel | the enemy's row lies beyond the African's starting row (row 6) toward the Carthaginian rear | Authored reading of 63 §8 row 19 |
| Carthaginian rear row (press target) | row 0, the Carthaginian map edge, in each unit's own column | §8 question 1 |
| Light troops fall back | at interval 10 (08:30), to row 15 (Roman) or row 3 (Carthaginian) in their own column | S65 III.115 gives no time |
| Heavy advance | one row forward, once the Roman command's reports show every light unit behind row 12, or 10 intervals later; its arrival starts the press | R1 "once the light troops have cleared" |
| Hasdrubal's opening charge | down the river lane to (21, 16), past the Roman right cavalry, with `press_assault` | S65 III.115; the hex is authored |
| Numidians | open with a move to the allied cavalry's hexes and halt at first contact | C1 "skirmish and pin" |
| Ride and charge | ride to (11, 13), (12, 14), (10, 14) behind the Roman left; once one is reported within 1 hex of its ride hex, charge the three rearmost Roman heavy contacts | S65 III.116; hexes and targets authored |
| Hasdrubal's trigger, read | the Roman right cavalry's contact is reported routed, or no contact of it is left in the view after interval 7 | Read from delivered reports only |
| Exits | smaller camp (22, 20), larger camp (16, 20), Cannae village (6, 20); the larger camp is the Roman rally point | 63 §8 row 25 |
| Carthaginian rally point | (16, 0) | Authored |
| Unit hexes | `roman_units`, `carthaginian_units` | 63 §6 order, authored hexes |
| Succession | none: if C4 or SC1 is lost or routed, that side's units go on under standing doctrine | No successor is sourced; 63 does not set one |
| `cavalry-delayed` | the horse first gets a hold order at the trigger; the ride is sent the given intervals later | Authored marker for a stateless control |
| `roman-reserve` | A7 and A8 at (21, 16) and (22, 16), holding, with no exploit and no advance order | 63 §3 R2 names two *alae*, not which |
| `deserters` | 500 light cavalry at (16, 16) holding fire; open fire at interval 60, then move on the rearmost Roman heavy contact | 63 §8 sets "a scripted interval" |

### 3.2 Deviations from 63

1. **The battle signal is not sounded (row 17).** The sources place Varro's signal before the crossing (S66 XXII.45; 63 §4 step 2), before the 08:00 start (63 §2: the first light-infantry contact). The engine's signal kinds are `recall` only, with a hold or retreat stance. The Roman profile carries the trumpet, and the 6-hex reach is recorded; no signal sounds. §8 question 4.
2. **No sector commanders (gap 5)**, per D86. Each side's orders go from one command detachment by voice within 1 hex or by mounted messenger.
3. **`scale-b` is not built.** The validator accepts only option A; option B needs its own layout (63 §2.2: the block does not divide evenly).
4. **Records.** 63 §5's records are kept as: `s['victory']['record']` per interval (enclosed units and men, men lost, open exits, narrowest passage, heavy units in contact as the frontage); `closed_turn` on the ground; `known_closed_turn` per headquarters from delivered reports; `exited` per unit; events for every order, delivery, yield, wheel and exploit. Not kept per interval: each unit's morale and front (end state only), a frontage per sector (no sectors exist). The narrowest passage is a hex-disjoint path count to the exit hexes, so it never exceeds the number of open exits (3).
5. **Losses counted toward the enclosure measure** are every man the 16 heavy units have lost, plus the men of enclosed units. No surrender rule is declared, so the surrendered count is 0.
6. **Numidian pursuit** of the allied horse (S65 III.116) is not modelled; the Numidians hold and fight.

## 4. The `encircle` kind

Each interval `enclosure` blocks every hex held by a live Carthaginian unit and every hex within `zoc` of one, floods the open hexes from each open exit, and counts a Roman heavy unit enclosed when neither its hex nor a neighbour is reached. The Carthaginian side wins at the deadline when enclosed men plus men lost reach 50 per cent (28,400) of the heavy infantry's 56,800; otherwise the Roman side wins at the deadline. The Roman side wins at once when 5 of C1 to C8 are routed or lost, but only while enclosed and lost men are still below that 50 per cent (Dd8, §8 question 2). The reasons read "army enclosed", "army not enclosed" or "centre broke", not a historical result. `s['victory']` is in neither side's view.

## 5. Variants

| Name | Change | 63 §8 |
|---|---|---|
| `no-design` | C1 to C8 have no `yield` (C2) | no-design |
| `cavalry-delayed-10`, `-20`, `-40` | The ride waits 10, 20 or 40 intervals after the trigger | cavalry-delayed |
| `one-wing-fixed-af1`, `-af2` | AF1, then AF2, has no `wheel` | one-wing-fixed |
| `roman-reserve` | R2: A7 and A8 held on the lane | roman-reserve |
| `aemilius-commands` | Command detachment and player at EQ | aemilius-commands |
| `roman-horse-holds` | EQ, SC1 and SC2 at double strength | roman-horse-holds |
| `dust` | Roman sight 3 hexes | dust |
| `deserters` | Livy's 500 in the Roman rear | deserters |
| `wide-front` | The Roman block 16 wide and 1 deep (columns 5 to 20); the allied cavalry moves to columns 3 and 4 | wide-front |
| `zoc-0` | Only occupied hexes block an exit path | zoc-0 |

`test_each_named_variant_differs_only_in_its_own_question` checks that each variant's snapshot differs from the default only in its own fields.

## 6. Runs and run time

`python3 scripts/cannae_runs.py` runs the default and the 13 variants, 14 runs, each with its closing replay check. A 12-interval run through the runs script's own path (BatchStore and replay check) replays `identical` (`test_a_short_headless_run_replays_identically_and_summarises`).

### 6.1 Results: EVO run `bt05r-d829763` at `d829763`

EVO run dir `bt05r-d829763`, from `git archive d829763` (sha256 `dbf45dffe4b32c70f491ceba5d9e0008851abc65eb7b38c383a28c77f198b457`), serial, under `nohup`. Reproduce from `apps/poc`:

```
python3 scripts/cannae_runs.py --dir <run dir>/runs
python3 scripts/cannae_runs.py --only <entry> --dir <run dir>/runs
```

All 14 runs exit 0 and replay `identical`. Every run is a Roman win at turn 160 (16:00:00), the deadline. The table is built from each run's result JSON (`run.log` for the default, `run-<entry>.log` for the rest). "Enclosed / lost" are the two counts in the reason, "The Roman army was not enclosed by the deadline: E men enclosed and L lost, short of the 28400 required."

| Entry | Winner, end | Enclosed / lost (reason) | Peak enclosed (men, turn, units) | Closed turn | Known closed (Carth. / Roman) | Exited (unit, turn, men) | Losses (Carth.; Roman) | Events |
|---|---|---|---|---|---|---|---|---|
| `default` | Roman, 160 (16:00:00) | 0 / 5700 | 26465, 56, 8 | 36 | 25 / 33 | L1 62 2634 | 21699/50020; 6525/77200 | 69079 |
| `no-design` | Roman, 160 (16:00:00) | 0 / 4303 | 12984, 47, 4 | 26 | 25 / 28 | A1 73 2849 | 16137/50020; 5128/77200 | 69879 |
| `cavalry-delayed-10` | Roman, 160 (16:00:00) | 0 / 5700 | 26465, 56, 8 | 36 | 25 / 33 | L1 62 2634 | 21699/50020; 6525/77200 | 69079 |
| `cavalry-delayed-20` | Roman, 160 (16:00:00) | 0 / 5700 | 26465, 56, 8 | 36 | 25 / 33 | L1 62 2634 | 21699/50020; 6525/77200 | 69079 |
| `cavalry-delayed-40` | Roman, 160 (16:00:00) | 0 / 5700 | 26465, 56, 8 | 36 | 25 / 33 | L1 62 2634 | 21699/50020; 6525/77200 | 69079 |
| `one-wing-fixed-af1` | Roman, 160 (16:00:00) | 0 / 4601 | 23627, 56, 7 | 36 | 25 / 33 | L1 62 2634 | 17543/50020; 5426/77200 | 67226 |
| `one-wing-fixed-af2` | Roman, 160 (16:00:00) | 0 / 3665 | 22895, 48, 7 | 31 | 25 / 36 | A6 71 2628 | 12165/50020; 4490/77200 | 69115 |
| `roman-reserve` | Roman, 160 (16:00:00) | 0 / 5137 | 26907, 66, 8 | 26 | 25 / 26 | A6 62 2506 | 19277/50020; 5954/77200 | 59918 |
| `aemilius-commands` | Roman, 160 (16:00:00) | 0 / 6618 | 23585, 42, 7 | 29 | 29 / 35 | L3 61 2717 | 23075/50020; 7439/77200 | 65912 |
| `roman-horse-holds` | Roman, 160 (16:00:00) | 0 / 5714 | 16383, 43, 5 | 24 | 24 / 25 | L4 55 2564 | 15899/50020; 6371/83600 | 68229 |
| `dust` | Roman, 160 (16:00:00) | 0 / 5030 | 29677, 52, 9 | 36 | 25 / 28 | L1 71 2750 | 16722/50020; 5855/77200 | 60823 |
| `deserters` | Roman, 160 (16:00:00) | 0 / 5155 | 36553, 51, 11 | 36 | 25 / 33 | L1 62 2702 | 19331/50520; 5980/77200 | 73109 |
| `wide-front` | Roman, 160 (16:00:00) | 16845 / 3387 | 20002, 51, 6 | 38 | 40 / none | L6 64 2640 | 8814/50020; 3777/77200 | 56481 |
| `zoc-0` | Roman, 160 (16:00:00) | 0 / 5700 | 0, 1, 0 | none | none / none | L1 62 2634 | 21699/50020; 6525/77200 | 69079 |

Cost: the default took 5:46 wall (345.9 s as the script reports it) and 437,172 kB peak RSS. The 13 others took 4:28 (`wide-front`) to 8:12 (`no-design`) each and 361 to 464 MB, 71 min 40 s in all (04:30:21 to 05:42:01 UTC, 2026-11-08), one at a time with a load guard that never had to wait. The 14 runs took about 77 min, against the planning estimate of about 85 min. The artifacts (logs, per-run `time -v`, manifests, `SHA256SUMS-all`) are in `apps/poc/artifacts/cannae-d86-d829763/`, with `evo-gates-d829763-MANIFEST.txt` beside it.

### 6.2 Readings

a. No entry reaches the 28,400 share. The largest enclosed-plus-lost count at the deadline is 20,232 (`wide-front`: 16,845 enclosed, 3,387 lost); every other entry has 0 enclosed and 3,665 to 6,618 lost. The Romans win all 14 at the deadline.

b. In the default the pocket closes at interval 36 on the ground (interval 25 in the Carthaginian headquarters' reports, 33 in the Roman). Enclosure peaks at 26,465 men in 8 units at interval 56, short of 28,400 at its best, and is 0 at interval 160 (last record `[160, 0, 0, 5700, 3, 3, 0]`). L1 leaves by an exit at interval 62 with 2,634 men.

c. Negative baseline: the ride never fired. In all 14 runs the `ride` and `charge` fields are `null` for HC1, HC2 and HC3, so no order was sent to a Hasdrubal horse unit, with the ride hexes or any other destination. The three `cavalry-delayed` entries match the default in every game field (winner, reason, enclosure peak, closed turns, exit, losses, 69,079 events). The cavalry record varies only by entry: HC3 fights at intervals 5 to 6 in `roman-horse-holds` and 7 to 9 in `roman-reserve`, against 7 to 8 in the default, which has HC1 at 1 to 2. The delay variants and `roman-horse-holds` therefore do not test the ride: the controls never exercise it, and these runs show nothing about sensitivity or insensitivity to the delay. The three units end at (21,16), (20,15) and (21,15), `ready`, with HC1 in a fight from interval 1 to 2 and HC3 from interval 7 to 8 in the default (`cavalry_fight`).

   Cause, from a read-only diagnosis at `dcfc0d2` (60 intervals of default and `zoc-0` headless, replay identical and matching the EVO run). The ride never fires under the Dd8 q5 reading. The trigger (`cannae_policy.py:173-176`, gated at `:192`) needs the Roman right cavalry EQ to be seen routed, or to be out of the Carthaginian view. Neither happens. At interval 60 EQ is on its start hex (21,11) with 1,470 of 1,600 men, status ready; the Carthaginian contact of EQ is fresh (age 0) and not routed, and EQ was seen on 60 of 60 intervals. The cause is the authored opening order of Hasdrubal's horse: a charge down the lane to (21,16) with `press_assault` (`scenario_cannae.py:45`, `:182`). The 2-hex lane leaves a free column beside EQ, so the horse rides past it after a few volleys (EQ is under fire only on intervals 1, 3, 4 and 7). While engaged, one horse unit costs EQ about 22 men and 2.7 morale a volley, so a rout would need about 20 intervals of contact. Ruled out: the trigger not being evaluated, a wrong unit id or view key, and a ride order built but dropped. No ride order is ever built. The fix changes outcomes; see §9.

d. Closed: `zoc-0` behaves as defined. It plays the same battle as the default (same events, losses, exit and reason counts) and reads 0 enclosed. Under `zoc` 0, `_blocked` (`victory_encircle.py:35-38`) blocks only occupied hexes, so one-unit-per-hex lines leave gaps and every Roman unit has an open path to an exit (`:125`). The records match the default except in the enclosure columns: at interval 36 the default has 2 units and 6,537 men enclosed, `zoc-0` has 0; at interval 56 the default has 8 units and 26,465, `zoc-0` has 0. This is the doc 63 §8 definition of the measure. The result follows from the zoc 0 definition. It does not test the S67 claim. 63 §8 states the variant's purpose as testing S67 p. 25's claim that the cavalry could not seal the rear.

## 7. Tests

`tests/test_army.py` (27 tests) covers the declared scale, the army data and unit-key checks, the side profiles, the delivery estimate, the engaged-share volley, the rear multiplier, morale by share and its carried remainder, the front, the cavalry's three steps, the routed contact, the yield and its limit, the wheel and its trigger, the enclosure measure with `zoc` 1 and 0, the three `encircle` outcomes, the centre break only below the share (Dd8 q2), headquarters knowledge, the field refusal by other kinds, and the opt-in digests. `tests/test_cannae.py` (13 tests) covers the registration, every default of 63 §8 except row 17, the D86 labels, the designed yield against `no-design`, each variant's difference, the policy registration, each scripted order's locator or label, the light-troops and advance sequence, Hasdrubal's trigger, the charge, the cavalry delay, the deserters, and a 12-interval headless run with its replay check.

## 8. Readings ruled by the owner (Dd8)

Six readings of 63 change outcomes. Bob ruled on all six in Dd8 (2026-11-07, relayed 23:47Z), accepting the PM's recommendation on each: keep the built reading for questions 1 and 3 to 6, take the option for question 2. None is open. Each is one constant.

| # | Question | Dd8 ruling | Rejected reading |
|---|---|---|---|
| 1 | The Carthaginian rear row (63 §8 row 21) | **Built:** row 0, the Carthaginian map edge (`PRESS_ROW`) | Row 6, the Africans' row: a pressing unit would stop there and never be "past the African's front row" (row 19), so the wheel could not fire |
| 2 | "Before that" in the centre-break win (63 §5) | **Option, the literal reading:** the centre break wins only while enclosed and lost men are below 50 per cent (`victory_encircle.BREAK_ONLY_BELOW_SHARE`, `# Dd8 (Bob 2026-11-07): Q2 literal reading`) | At any interval before the deadline (the first build) |
| 3 | Yield and rout (63 §3 C1, "without routing") | **Built:** the step back is not a rout; the ordinary morale rout still applies | A unit within its yield limit cannot rout |
| 4 | The battle signal (row 17) | **Built:** before the start, not sounded (§3.2 item 1) | A new signal kind sounded at the start that begins the press of the units in reach (6 hexes from Varro, so the two right-hand columns would not hear it) |
| 5 | Hasdrubal's trigger (row 20) | **Built:** read from the Carthaginian view (a routed contact, or no contact after interval 7) | Read from the truth, or a local doctrine on the horse |
| 6 | Line spacing (row 10) | **Built:** 3 hexes from the Roman front row to the crescent, so the two light lines start adjacent | From the Roman front to the Carthaginian base row, which puts both light lines in one row |

## 9. Open owner question: the Cannae ride

The default is left as built until the owner rules. The ride never fires (§6.2 c) because EQ is neither routed nor out of view. Three fixes, each of which changes outcomes:

| Option | Change |
|---|---|
| (i) | The horse pursues EQ's reported hex while EQ is in view and not routed, so the opening charge no longer rides past it |
| (ii) | The trigger fires after N intervals with no Carthaginian unit adjacent to EQ, a different reading of 63 §8 row 20 (which would revise Dd8 q5) |
| (iii) | Raise the cavalry's combat effect, so one horse unit routs EQ in fewer than about 20 intervals of contact |
