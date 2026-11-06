# 43 — Concord North Bridge: scenario build spec

**Date:** 2026-11-06 (UTC). **Requirement:** the second of the first five selections ([37](37-first-five-selection-register.md)) needs a build spec: the catalog entry, the engine gaps and the rules edition they need. This document is a proposal. It adds no code, no entry and no rule. Each section says whether it holds a finding (what a source or the code says), a proposal, or an open question.

Engine facts below were read from the `poc-10` code on this branch and are cited by file. Source facts come from [09 — sources](09-sources.md): S47 to S49 are new in this pass.

## 1. Scenario frame (proposal, with sourced facts marked)

- **Action.** The Acton minute company at the head of the provincial column against the British light infantry guarding the North Bridge over the Concord River, Concord, Massachusetts. **Date:** 19 April 1775. NPS (S47) gives 07:30 for the British securing the bridge, 09:00 for the militia reaching the ridge above it, and 09:30 for the fighting at the bridge.
- **Local time.** The proposed start is 09:25, five minutes before NPS's 09:30. That is a reconstruction: NPS gives clock times to the half hour, not to the minute.
- **Echelon.** Aggregate detachments, as in every `poc-10` entry. The default detachment is 40 troops (`scenario_entry.unit`), which matches Davis's company of about 40 (S48). One hex is 50 m (`grid.METRES_PER_HEX`); one turn is 30 seconds (`scenario_entry.SECONDS_PER_TURN`).
- **Sides.** `provincial` (role `attacker`) and `british` (role `defender`). The player commands `provincial`: the fixture asks when the front company may open fire ([six-era-cases.json](../../apps/poc/experiments/six-era-cases.json), case `concord-north-bridge`). The computer commands `british`.
- **Forces on the evidence.** British at the bridge: Captain Walter Laurie with three companies, about 96 men; two grenadier companies were sent to reinforce them (S47). The American Battlefield Trust (S49) says two companies guarded the bridge, about 90 men. Provincials: about 400 under Col. James Barrett, Major John Buttrick and Lt. Col. John Robinson leading the column, Davis's Acton company in front (S47, S48). Casualties at the bridge: British three killed or mortally wounded and nine wounded; Davis and Private Abner Hosmer of Acton killed, Fifer Luther Blanchard and three others wounded (S47).
- **Orders on the evidence.** Barrett: "Do not fire unless first fired upon." Buttrick: "Fire, for god's sake fire!" (S47). Of the British shots, three came first and "splashed harmlessly into the river"; the rest of the British then fired into the column "without an order to fire" (S47). No British order to Laurie was read.

## 2. Field-by-field table

Provenance: **sourced** (S-id), **reconstruction** (inferred; basis given), **authored** (POC choice; no source). Entry fields are those of `ScenarioEntry` in `scenario_entry.py`. Each row's note is also what the entry's `provenance` map should hold.

| Field | Value or proposal | Provenance |
|---|---|---|
| `id`, `title`, `variant` | `concord-north-bridge`, "Concord North Bridge", `None` | Authored |
| `rules` | The Concord edition (§4); `poc-10` cannot run the RULE items | Authored |
| `labels` | `{edition: "concord-north-bridge-v1"}` | Authored |
| `prompt_version`, `prompt_setting` | New version id; "Concord's North Bridge, 1775" | Authored |
| `location` | North Bridge over the Concord River, Concord, Massachusetts | Sourced (S47, S49) |
| `date` | 1775-04-19 | Sourced (S47) |
| `start_time` | 09:25 | Reconstruction: five minutes before NPS's 09:30 fighting (S47); the minute is not sourced |
| `time_basis` | "Scenario local time; NPS clock times as written" | Authored; NPS does not say what clock the times are on. Unverified |
| `seconds_per_turn` | 30 | Authored; fixed by `validate` |
| `weather` | Fixed POC condition, "April, fixed POC condition" | Authored; no weather source read |
| `sides.provincial` | name "Provincials"; role `attacker`; `command_unit` the Acton unit | Sourced that Buttrick and Davis marched at the head (S47, S48); that the commander rides with Acton is reconstruction |
| `sides.british` | name "British"; role `defender`; `command_unit` the Laurie unit | Sourced that Laurie commanded the guard (S47); attachment is reconstruction |
| `player_side` | `provincial` | Authored: the fire decision is the provincial commander's |
| `sides.*.mission` | Provincial: advance to the bridge; do not fire unless fired upon; return fire when the command is given; clear the crossing. British: guard the crossing; fall back toward the town if it gives way | Provincial: sourced as to the fire instruction (S47); the objective clause is reconstruction. British: reconstruction, inferred from Laurie's post (doc 37 register); no order to him was read |
| `sides.*.charge`, `headquarters` | Authored text; rally points behind each side's start | Authored |
| `sides.*.supply` | `None` | Authored: no ammunition point is modelled |
| `units` (provincial) | Acton 40; column detachments behind it summing to about 400 in total (for example three of 120) | Acton strength about 40: sourced (S48). Total about 400: sourced (S47). The split and the other companies' names: authored; no source read names them |
| `units` (British) | Laurie's three companies as three detachments of 32 (96 total) | Total sourced (S47; S49 says about 90 in two companies); the split is authored |
| Reinforcements | None. The two grenadier companies and the four companies returning at 11:00 are left out | Authored: `poc-10` has no arrival schedule; both arrive after the exchange (S47) |
| `units.*.overrides` | `weapon_class: "smoothbore muskets"`; `ammo`; new fields `fire_discipline`, `officers` (§3); skill and morale defaults | Authored. Override keys are accepted by `build_state`, so initial values are DATA; the engine ignores unknown fields until the new edition |
| `victory` | `hold-objective` (§3, row 7): objective the bridge hex, `radius` 1, `hold_turns` 2, `objective_name` "bridge", `deadline_turns` 20 | Authored values. Historical outcome sourced (S47): the British withdrew and the militia held the bridge |
| `map.terrain` | Authored river as a column of impassable hexes with a one-hex gap at the bridge; ridge rising on the provincial bank; open ground on the British bank | Authored, not surveyed. That the militia held a ridge above the bridge is sourced (S47) |
| `map` grid | 24 x 21 hexes of 50 m | Fixed by `validate` |
| `map.features` | None needed (the bridge is a terrain hex) | Authored |
| `order_catalog` | The Concord edition's catalog (`ORDER_CATALOG` plus `open_fire` and `hold_fire`) | Authored; RULE (§3) |
| `communications` | New profile, for example `provincial-voice-v1`, with a voice reach (§3) | Authored |
| `voice_profile` | New `colonial-1775-en-v1` prose profile | Authored; no rules effect |
| `tools_per_unit` | 0 | Authored: no entrenching in a 10-minute action |
| `desk` / `SideBrief` | "CONCORD · 19 APRIL 1775", bridge caption, per-side win/loss headlines | Authored. Desk text is entry data since doc 42 |
| `gates` | `None` | The scenario declares no openings |
| `provenance` | One note per row above | Authored |

**Unverified or blocked, not used:** Gage's orders to Smith (Clements Library manuscript, HTTP 403 in doc 37); Barker's diary, the depositions and Laurie's own account (not read). Which bank each force stood on is not stated by S47, S48 or S49; see open question 1.

## 3. Engine gaps

Classes: **DATA** = expressible with today's entry fields. **RULE** = needs a new rules edition (frozen `*_v10` modules, per the pattern in [39](39-scenario-sides-and-victory-kinds.md) and [41](41-poc10-gates.md)). **UI** = display only. Evidence in the "today" column was read in `apps/poc/battle/`.

| # | Mechanic | Class | Today |
|---|---|---|---|
| 1 | River crossable only at the bridge | RULE | `grid.path` skips only `walls` edges drawn by `gates._draw` from compounds with openings. Terrain cost slows a hex but never forbids it. Encoding the river as barred one-hex buildings would block movement, but `features.py` gives each building an `obstacle_height`, so `grid.visible` would stop fire across the river, and the order catalog would gain `close_gate`. |
| 2 | Hold fire until fired upon | RULE | `engine.advance` fires every unit at the nearest visible enemy within `fire_range` every interval. No discipline exists; initial values can be set as unit overrides but are not read. |
| 3 | Succession after an officer falls | RULE | `comms.operational` is false when the command unit is `lost` or `routed`; `engine.issue` then refuses orders. There is no officer, no second-in-command and no gap with recovery. |
| 4 | Spoken-order reach, 1775 | RULE | `comms.progress` and `engine.issue` treat voice as instant for the commander's own detachment only. Every other recipient gets a courier at 200 movement cost per turn. |
| 5 | Smoothbore fire | RULE | `weapon_class` is a label (Hougoumont set it and used the same model, doc 42). The fire formula is `rounds * (8 - d) * ...` with a range of 5 hexes (`standing.profile`), the same for every weapon. |
| 6 | A 1775 voice | UI | A new prose constant in `presentation.VOICE_PROFILES`, as for the 1815 voice. No rules effect; doc 42 added its voice without a new edition. |
| 7 | Victory: hold or cross the bridge, force withdrawal | DATA, with a RULE option | `hold-objective` with `radius` 1 scores the attacker holding the bridge area with no effective defender in it. It matches the recorded outcome. The gap: if the British leave but no provincial reaches the radius, only the deadline ends the game and the defender wins "held out". A kind `force-withdrawal` would close that. |
| 8 | Draw the river, bridge and ridge on the desk | UI | The renderer draws terrain kinds and buildings; whether it can show an impassable river and a bridge was not read. To confirm. |
| 9 | Arrival schedule for reinforcements | RULE (deferred) | Every unit is present at turn 0 (doc 38). Not needed for the exchange; recorded as out of scope. |

### Smallest deterministic designs (proposals)

Every design is a pure function of the snapshot, uses integers, and draws no random number. Every authored value is a sensitivity parameter, labelled as such in a `basis` string like `GateEntry.basis`.

**R1 River (impassable hexes).** *Design:* terrain cells may carry `no_entry: true`. `grid.path` treats such a hex as a wall from every neighbour, as it treats `walls`. Sight and fire are unchanged. The bridge is an ordinary hex in the gap. Units still cannot stack, so the bridge hex admits one detachment at a time. *Inputs:* the cell flag only. *Parameters:* which hexes carry the flag, and the bridge's hex count. *Note:* on this offset grid a one-hex-wide column is a barrier, but a bridge hex has one neighbour on one bank and up to three on the other, depending on row parity (`grid.neighbors`). The map build should choose a layout and record the asymmetry. The British plank removal (S47: suggested, not confirmed) is not modelled.

**R2 Fire discipline.** *Design:* a unit field `fire_discipline` in `free` (today), `hold` or `return`. A `hold` unit does not fire. A `return` unit does not fire until it is released; it is released when (a) a unit of its side within `release_reach` hexes was the target of an enemy volley in the previous interval, or (b) an `open_fire` order is delivered to it. After release it fires as `free` until a delivered `hold_fire`. Release takes effect from the next interval. The unit emits `fire_released`. *Inputs:* enemy volley targets of the last interval (`last_attacked_turn`), distance between units, delivered orders. *Parameters:* `release_reach` (0 = own unit only, 2, side-wide), `release_delay_turns` (0 or 1), the initial discipline per unit. *New orders:* `open_fire`, `hold_fire`, in a new catalog (`common-orders-v5`); they go through normal delivery (R4).

**R3 Succession.** *Design:* a unit field `officers` (a count). A deterministic threshold stands in for a hit: each time a unit's cumulative losses pass a multiple of `max(1, initial // (officers + 1))`, one officer falls (event `officer_down`) and `officers` drops by one. For `leaderless_turns` intervals the unit keeps its current stance, accepts no new order and loses `leaderless_morale` morale once. If it has no officer left it stays leaderless. If the side's command unit has no officer left, or is `lost` or `routed`, `comms.operational` is false for `succession_delay` intervals; then the side's entry `succession` list names the next unit that is operational and the commander moves to it. *Inputs:* losses per unit, `officers`, the ordered `succession` list. *Parameters:* `officers` per unit, `leaderless_turns`, `leaderless_morale`, `succession_delay`. *Honesty note:* an individual (Davis, Hosmer) is not a modelled entity. The rule says "an officer fell", not who; S48 does not name Davis's successor.

**R4 Spoken-order reach.** *Design:* the communications profile carries `voice_reach` hexes. In `engine.issue`, an order to a unit within `voice_reach` of the commander's detachment is sent by voice (ready the same interval, as the commander's own is today). `comms.progress` keeps the voice packet on the recipient; a recipient that moves out of reach before delivery has the packet fall back to a courier from its position. *Inputs:* `grid.distance` between the commander's detachment and the recipient, at issue and at each progress step; optional suppression of the recipient. *Parameters:* `voice_reach` (1, 2 or 3 hexes), `din_penalty` (reach reduced by 1 when the commander or recipient has `suppression` at or above a threshold, default off). The same reach drives the R2 release distance if the authored scenario wants Buttrick's command to be heard only nearby.

**R5 Smoothbore fire.** *Design:* a weapon table stored in the snapshot, keyed by `weapon_class`, with `range_hexes`, `rounds_per_man` and `effect_pct`. The fire loop reads the unit's class: targets are limited to `range_hexes`, the exposure term `(8 - d)` becomes `max(0, range_hexes + 1 - d)` scaled to the same 0 to 7 range, and the result is multiplied by `effect_pct / 100`. Classes absent from the table keep today's values, so earlier editions replay. *Inputs:* `weapon_class`, distance, cover, suppression. *Parameters:* `range_hexes` (2 and 3), `effect_pct` (50 to 100), `rounds_per_man` (1). No source read gives smoothbore range or rate of fire; all are authored.

**R6 Victory option `force-withdrawal`.** *Design:* `hold-objective` plus one rule: the attacker also wins when no effective defender stands within `radius` of the objective for `hold_turns` consecutive intervals, whether or not an attacker has reached it, provided an attacker is effective. The defender wins as before. Same interface as other kinds (`problems`, `setup`, `score`, [39](39-scenario-sides-and-victory-kinds.md)). *Parameters:* `radius`, `hold_turns`. Add it only if the scripted runs of §5 show the DATA kind mis-scoring.

### Limits to record, not to fix here

- A 30-second turn means the whole exchange at the bridge resolves in a few intervals. `seconds_per_turn` is fixed at 30 by `validate`.
- One detachment per hex makes the bridge a single-file crossing. This is a property of the engine, not a source fact.

## 4. Edition plan (proposal)

**One edition for the five RULE items R1 to R5** (R6 only if needed, R9 deferred). They touch the same modules: `engine.advance` and `engine.issue`, `grid.path`, `comms`, `orders` (catalog v5), `standing`, and `scenario_entry` (`COMMUNICATIONS`, the order-catalog check, new unit and side fields). Splitting them across editions would freeze the same files twice. Following [39](39-scenario-sides-and-victory-kinds.md) and [41](41-poc10-gates.md): `engine_v10.py` byte-for-byte, the shared modules inert for snapshots without the new fields, tests that pin earlier digests, and the old-save decision stated in the edition's document.

**The gateway rule.** [41](41-poc10-gates.md) records that push-back at the Hougoumont gate is not modelled, and a gateway-contest rule would change `gates.progress` and so also needs an edition. Neither choice is assumed here. Two orders are possible:

- *Gateway first* (`poc-11` gateway, `poc-12` Concord): the Concord edition then freezes `engine_v11` on top of the gateway rule. It costs Concord one slot of waiting, and gains a settled `gates` module.
- *Concord first* (`poc-11` Concord, `poc-12` gateway): the gateway edition then freezes the Concord engine.

Both orderings are serial. The two editions edit `engine.py` and `scenario_entry.py`, so they should not be developed in parallel branches. The Concord RULE items do not depend on the gateway rule, and the reverse holds; the order can follow whichever decision the owner makes first.

## 5. Scripted controls (labelled reconstruction)

The scripted baseline must exercise the first-volley decision. These are labelled reconstructions of what the recorded orders imply, not recorded behaviour.

| Control | Provincial | British | What it exercises |
|---|---|---|---|
| **S1 historical-order** | Acton leads the column to the bridge approach under `return`; the rest follow; on release, fire and cross when the guard is broken | `free` fire at `range_hexes`, in the guard's position east of the river; fall back toward the town when two of three detachments are `routed` or below a strength floor | Reconstruction of Barrett's instruction (S47) against the guard's mission. British firing first without an order (S47) is the `free` setting |
| **S2 provincial first fire** | `free`: opens fire at maximum range as the column arrives | As S1 | Whether firing first changes the outcome or the casualties |
| **S3 British hold** | As S1 | `hold` until fired upon, then `free` | Whether a restrained guard prevents the exchange or loses the bridge |
| **S4 release lag** | As S1 with `release_delay_turns` 1 and `release_reach` 0 | As S1 | The cost of waiting for the command (Buttrick's order, S47) to reach the front company |

Compare what the fixture's `comparison` asks: the first-fire sequence, who heard the command, and who controlled the crossing after the exchange. Do not score body counts against the history: the NPS figures (S47) are a check on order of magnitude only. A result that appears under one parameter value and not another is reported as sensitive. The computer side in a live run follows the pattern of `scripted-gate-defender-v1` ([42](42-hougoumont-scenario.md)): the controller reads delivered reports and issues only orders the catalog offers.

## 6. Open questions (not findings)

1. **Which bank held which force?** S47, S48 and S49 do not say. Web search snippets from pages not read suggest the British stood on the town (east) bank when they fired; this is unverified. The map orientation depends on it.
2. **Was the plank removal done?** S47 says an officer suggested it and the page does not confirm it. Model it (a gate-like state on the bridge hex) or leave it out?
3. **How many British companies guarded the bridge?** S47 gives three (about 96), S49 gives two (about 90). Which should the entry use? The proposal uses S47.
4. **Is the 30-second turn acceptable?** The exchange fits in a few intervals. A shorter turn is a global rules change and a separate decision.
5. **Should the three warning shots count as "fired upon"?** S47 says they splashed into the river. R2 releases on a volley that targets a unit; whether an ineffective shot releases fire is an authored choice.
6. **Edition order:** gateway first, or Concord first (§4)? Does the owner want the gateway rule at all?
7. **Is R6 needed?** Decide after the S1 to S4 runs.
8. **Sources not yet read:** Gage's orders, Barker's diary, the depositions, Laurie's account. Are library or archive pulls wanted before the comparison runs?
9. **Authored numbers:** fix `voice_reach`, `range_hexes`, `effect_pct`, the officer thresholds and the succession delay in advance, or leave them as sensitivity parameters in the tuning step (compare [37 question 6](37-first-five-selection-register.md#6-open-questions-for-the-user))?

## 7. Sources used in this pass

Access date for every entry: **2026-11-06 (UTC)**, recorded in [09 — sources](09-sources.md#concord-north-bridge-spec--2026-11-06) as S47 to S49. The pages were read through a summarising fetch, so quoted phrases may be paraphrased; re-read the page itself before quoting it in an outward document.

- S47: Minute Man National Historical Park, *The events of April 19*, page updated 2025-05-17.
- S48: National Park Service, *Captain Isaac Davis*, page updated 2023-01-17.
- S49: American Battlefield Trust, *Old North Bridge*, published 2023-03-04, updated 2024-04-19.
