# 53 — Pegasus Bridge: engine and data (`poc-13`, 1944 keys)

**Date:** 2026-11-06. **Requirement:** the engine and data prerequisites of the Pegasus Bridge scenario planned in [52](52-pegasus-bridge-scenario-plan.md) §8, gaps 1, 4, 5 and 6: (1) a bridge hex with a state, where a destroyed bridge cannot be crossed; (2) a 1944 company radio profile and a British 1944 voice; (3) the success codewords as delivered reports; (4) a night observation range that fire and targeting read; (5) one authored weapon range, with a second range refused. No Pegasus catalog entry is added; that is a separate task.

Labels follow 52: **sourced** (S-id), **assumption** (a value no source gives), **authored** (a POC choice).

## Rules-edition decision

The work stays in `poc-13`. No engine is frozen and no edition is added, as in [47](47-poc13-part-b-command-and-smoothbore.md) and [50](50-concord-command-fire-release.md).

**Why.** Every new rule reads snapshot data that only a new entry key can write, and no saved `poc-13` game holds it:

| Key on `ScenarioEntry` | Written to the snapshot | Read by |
|---|---|---|
| `bridges` | a `bridge` entry in `map_features` and its feature reports; `bridge_state` on the bridge cell and its briefing cell; `bridge_schedule` when a change is scheduled | `grid.passable`, `bridges.progress`, `bridges.known_cells`, `features.report` |
| `signals` | `signals`, `signals_received` | `signals.check`, `signals.receive`, `engine.view` |
| `observation_range` | `observation_range` on each unit without its own | `recon.sees` (spotting, fire, feature reports, the rest/dig-in and regrouping safety checks) |
| `communications` `wwii-1944-radio-v1` | the profile id, as for every profile | `command.radioed`, `comms.progress`, `command.relay`, `engine.enqueue` |

`build_state` refuses any of them in an edition before `poc-13`. The new voice `wwii-1944-en-v1` changes prose and display text only, as the 1775 voice does.

**Proof.** All pinned digests and replay tests pass with no digest edit: the seven `e165371` `poc-13` digests in `test_poc13b.py`, the `poc-12` digests of [46](46-poc13-river-and-fire-discipline.md), and the Concord pins of `test_concord_sensitivity.py`. `GatingTests` checks that an entry without the keys writes none of their state. Headless runs on this branch: Little Round Top, Union at turn 60; Hougoumont, Allied at turn 60; Concord v2, provincial at turn 8; all three replay `identical`.

## Rules (implemented)

| Area | Rule |
|---|---|
| (1) Bridge state | A `BridgeEntry` names a water hex whose `crossing` is `bridge`, with `state` `intact`, `charges` (wired, still passable) or `destroyed`. `grid.passable` refuses a destroyed bridge, so neither troops nor runners cross it and an order to its hex is refused as impassable water. |
| (1) Changes | `bridges.set_state` is the one transition: it updates the feature and the cell and emits `bridge_state_changed` (from, to, cause). A destroyed bridge stays destroyed. The demolition trigger is scripted for now: `BridgeEntry.schedule` lists authored `(turn, state)` changes, applied at the start of that interval before anyone moves. |
| (1) Knowledge | Headquarters sees the briefed state in `map_features` until a unit of its side within 3 hexes and in sight reports a change by the ordinary report path, as for gates ([41](41-poc10-gates.md)). Delivery estimates, and the water checks of a move order (`orders.validate`) and a split (`formations.validate`), use the bridge states headquarters knows (`bridges.known_terrain`). An order to a bridge blown without a report is accepted and fails at execution, as an order into unknown terrain does; once the report arrives it is refused. God view shows the true state. |
| (2) Radio | Profile `wwii-1944-radio-v1`: voice to units within `voice_reach` 2 hexes of the command detachment, radio within `radio_range` 10 hexes, runner beyond. `engine.issue` chooses by headquarters' known position. A radio order is due the next interval. At delivery `comms.progress` checks the true distance; beyond range, or if the sender has fallen, it goes on by runner (`radio_out_of_range`). |
| (2) Radio reports | A unit (not an intelligence asset) within radio range of its command detachment sends its reports by radio: due the next interval, with the same runner relay. The command detachment still reports by voice. |
| (2) Voice | `wwii-1944-en-v1` addresses the player as Major and never as General. Order text: "To B3: Hold your position. Sent by wireless." Staff text stored as "General, ..." is shown as "Major, ..." (`presentation.VOICE_ADDRESS`); the scripted decision reads "Major, the platoons will carry on under their standing orders." The prompt states the voice and radio reaches. |
| (3) Codewords | A `SignalEntry` names a codeword, its meaning, a side and a bridge. When a live, unrouted unit of the side stands on the bridge, the bridge is not destroyed and no live enemy is within `radius` (1) hexes, that unit sends the codeword once to its command detachment as a `signal` report (`signal_sent`: codeword, sender, receiver, turn sent). Headquarters learns it only when the report arrives; `view['signals']` lists received codewords with sender, receiver, `sent_turn` and `delivered_turn`. A signal report that expires or reaches a disrupted command is dropped (`signal_lost`) and the signal becomes unsent, so the holder sends it again while the bridge is still taken. |
| (4) Darkness | `ScenarioEntry.observation_range` sets each unit's observation range (a unit override wins). `recon.sees` is the one test of sight: within the range and in line of sight. Fire (`engine.volley`), contacts and therefore targeting (`recon.scan`), feature and bridge reports, and the rest, dig-in and regrouping safety checks all use it. |
| (5) Single range | With a weapon table, `scenario_command.weapon_problems` refuses a table with two different `range_hexes`, and a unit whose class is not in the table (it would fire at the 5-hex baseline), with an error naming the ranges and the units. A single range of 1 or 2 hexes is allowed. `tactics_v10.threat_range` still uses the unit's own range: the enemy-maximum fix is a separate task (48 §1). |

## Finding on fire before the change

Before this change `engine.volley` tested only `grid.visible`, which has a fixed 7-hex cap, and 5 hexes; it did not read `observation_range`. With both units' `observation_range` set to 2 and the units 3 hexes apart, B1 saw no contact (its local decision listed none) and still fired at G1, which returned fire. Spotting and targeting read the range; fire did not. 52 §8 row 1 had left this untraced.

## Values, sources and assumptions

| Value | Where | Status |
|---|---|---|
| `radio_range` 10 hexes (500 m) | `comms.WWII` | **Assumption.** S51 and S52 state no signals equipment, range or procedure (52 §1). Not a measured set range; no failure, jamming or net discipline is modelled. |
| `voice_reach` 2 hexes | `comms.WWII` | **Assumption**, reused from the 1775 profile ([47](47-poc13-part-b-command-and-smoothbore.md)); no new number. |
| Radio reports from units in range | `engine.enqueue` | **Authored.** No source says platoons reported by radio. |
| Address "Major" | `presentation` | **Sourced** as to rank: S51 is the report "by Major Howard", the company commander. The register and every phrase are **authored** and quote no historical message. |
| "Wireless" for radio | `presentation.WWII_DISPATCH` | **Authored** period wording; not taken from S50 to S56. |
| Codeword trigger: on the bridge, not destroyed, no enemy within 1 hex | `SignalEntry` | **Authored.** The codewords Ham and Jam are **sourced, secondary** (S54 only); S54 does not say when or how they were sent. |
| Bridge states and the schedule | `BridgeEntry` | **Authored.** The demolition intent is S54 secondary (52 §3); the charges' removal is S51 as to outcome. Timings belong to the scenario entry. |
| Night `observation_range` | entry data | **Assumption** when an entry sets it; 52 proposes 2 hexes with a 1 to 3 sensitivity. No source gives night visibility in hexes. |

## Tests

`apps/poc/tests/test_pegasus_engine.py`, 25 tests at `c6c4217`, 28 after the review fix round:

- **Bridge.** A destroyed bridge cannot be crossed and a wired or intact one can; an order to a destroyed bridge is refused; a scheduled demolition emits two events and replays `identical`; headquarters learns the state by report while God view shows it; the delivery estimate uses the known state; a move to a bridge blown without a report is accepted, fails to path, and is refused once the report arrives; bad bridge data is refused.
- **Radio and voice.** An order within radio range goes by radio and arrives the next interval; voice and runner remain; a unit out of range at delivery gets a runner; reports in range travel by radio; the 1944 prompt; order and staff text address the Major; scripted text.
- **Signals.** The codeword is a report with sender, receiver and two turns, sent once, unseen by the other side; not sent with an enemy adjacent or the bridge down; a codeword dropped by a disrupted command, or whose runner expires, is re-sent and arrives; bad signal data is refused.
- **Darkness.** A target beyond the night range is not fired on and targeting sees no contact; one within it is; the range is written only when declared; a bad range is refused.
- **Single range.** A 1-hex range fires at 1 hex only; a second range is refused; a unit outside the table is refused; `threat_range` still reads the unit's own range.
- **Gating.** An entry without the keys writes none of their state.

**Probes before the change** (entry records, profile ids and the voice instruction only): 18 of 25 tests failed, with 24 failures and 5 errors counting subtests. The 7 that passed assert preserved or negative behaviour: a 1-hex range already fired only at 1 hex (the weapon table existed), a target inside the night range was already fired on, `threat_range` reads the own range, voice and runner remain, the gating test, and two that pass vacuously with no bridge or signal rule. Those two were shown able to fail: planning over the true cells fails the delivery-estimate test (`unexpectedly None`), and removing the enemy-radius check fails the codeword test (a `signal_sent` with G1 adjacent).

## Limits

- No Pegasus entry exists, so none of these rules runs in a catalog scenario.
- The demolition is scheduled by the entry, not triggered by the guard or prevented by sappers; a sapper action is for the scenario task.
- A unit standing on a bridge when it is destroyed stays on the hex and may step off; no casualty is applied.
- A codeword whose report is dropped is re-sent only while the bridge is still taken; if it is lost in the meantime, headquarters never hears it. A command disrupted for a long time gets one re-sent report per runner trip, each dropped.
- The voice is scenario-wide: a German player would also be addressed as Major in British register.
- Only the condition `taken` exists; "Jack" and "Lard" (taken and destroyed, S54) are not modelled.
- The command detachment's conditional fire release ([50](50-concord-command-fire-release.md)) still uses voice reach only, not radio.
- The UI draws no bridge symbol; the state is in the view, God view and events.
