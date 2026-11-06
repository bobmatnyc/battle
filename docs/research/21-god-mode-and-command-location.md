# God Mode and physical command

Updated 2026-11-05. User requirement, implemented POC behavior and proposed extensions are distinguished below.

## User requirement

Allow a God Mode in which the player observes every unit and interaction. Locate each player in a command unit; communications to and from subordinates use technology available in the scenario. This adds an explicit observer exception to normal fog of war. It does not grant omniscience to unit commanders, the opponent AI or the virtual twin.

## Implemented in new `poc-3` battles

The Union controller is attached to U2; the Confederate controller is attached to C2. These are existing aggregate detachments: there are still six formations and 240 initial combatants. Staff attachment is an authored gameplay arrangement, not a claim about historical command positions. A future dedicated headquarters formation can use the same controller-to-unit relationship.

The command unit moves and fights through the existing autonomous movement/combat rules. The player gives it intent, just like other formations. The YOU marker, physical command location, outgoing message origin and incoming message recipient follow it. Its own condition and local sightings are direct information. Other formations' condition and contacts require report delivery. Enemy local sightings remain uncertain estimates, even when directly observed from headquarters.

If that detachment routes or is lost, new orders are rejected and incoming reports are not received. Other units continue their standing missions and contact reactions. The computer side obeys the same constraint and falls back to no new orders. Routed formations use the scenario's fixed rally points, avoiding the circular instruction to retreat toward a headquarters carried by themselves. Command succession and transferring the player to another unit are deferred; command disruption does not automatically end the battle.

### Period communications

The scenario profile is `civil-war-courier-v1`: local voice within the command detachment and foot couriers between formations. No radio, automatic modern tracking, signal flags or telegraph links are granted by the map interface.

| Mechanism | POC rule |
|---|---|
| Local voice order | Applies at the next committed 30-second interval; direct acknowledgement |
| Local observation/report | Delivered within that interval from the attached command unit |
| Courier route | Terrain-weighted path to the addressed position, 200 movement-cost units per interval |
| Terrain costs | Reuses authored grid costs: open 100, woods 145, rocky 170, plus slope |
| Outgoing order address | Recipient's last reported position, not its hidden current position |
| Moving recipient | Courier reaches the address first; friendly forwarding supplies another address, requires another physical journey and is logged |
| Acknowledgement | A separate return message; order status stays awaiting acknowledgement until it arrives |
| Spy handling | Existing extra report preparation time precedes courier travel |
| Expiry | After 20 intervals plus preparation, an undelivered packet expires with an audit event; no fictitious receipt |

The rate is an **authored coefficient**, not a historical measurement. At flat open-ground cost it permits up to two adjacent hexes (100 m) per interval. Movement credit persists through rough terrain, with a bounded carry. Transport advances at most once per interval, even though local reports are collected again after movement/combat.

Friendly address knowledge and forwarding are simplified: newly sent reports can address the current command detachment; a courier at an old address obtains a forwarding location. This abstracts friendly staff/trails and does not simulate dissemination of headquarters relocation notices. There is no enemy-truth routing advantage, instant remote receipt, or direct disclosure of packet location to normal headquarters. Courier interception, contested routes, messenger staffing/capacity, signal encoding, delivery reliability and dispatch prioritization remain unimplemented. Do not describe this as a calibrated historical communications network.

Newer friendly reports cannot be overwritten by late older reports. Enemy contacts retain the existing collection-time/arrival-time and dated identification merge rules. Ordinary views exclude the transport queue and enemy orders. Events record packet IDs, send/receive times, forwarding, expiry, effects and decisions; snapshots retain pending packets for replay.

### God Mode

The explicit toggle selects an omniscient **observer presentation**, not a different simulation policy. Both sides' exact formations, positions, ammunition, condition, active orders, local actions and command locations are visible. Map envelopes and dashed lines indicate message positions and addressed destinations. The interaction inspector provides the complete event sequence, category filters, expandable details, additional older events, all orders/reports, exact unit state and recorded strategic decisions. No essential events are sampled away; the initial visible list is paginated for readability.

Clock start/pause/speed and replay remain available. Unit orders and staff chat are disabled while observing. Returning to commander view restores authorized knowledge from a fresh normal observation; it does not merge omniscient state into that side's records. A human cannot unlearn what they saw: this is a local testing/learning tool, not fair competitive play.

Explicit endpoints: `/api/state?view=god` and `/api/replay?revision=N&view=god`, with the existing optional replay `game_id`. Default endpoints remain restricted commander views. The API is loopback-only and trusts its local operator. It does not implement authenticated multiplayer observer permission. Future multiplayer must authorize this mode at the scenario/host level, distinguish spectators from competing controllers, and record that omniscient assistance was enabled. Active-battle full export remains locked; God Mode intentionally allows active inspection through its separate view.

## Historical evidence and future profiles

NPS documents Civil War flags/torches, equipped signal parties, and communication where telegraph wires were absent. This supports treating equipment, endpoints and line of sight as requirements, rather than granting every formation every technology invented by 1863. [The Signal Corps](https://www.nps.gov/anti/learn/historyculture/signal.htm), updated September 15, 2023; accessed 2026-11-05.

At Harpers Ferry, terrain impeded courier/telegraph communication, and signaling itself took time and was affected by fog or mist. These are reasons to model constraints separately by method. [Flag Talk](https://www.nps.gov/places/000/information-panel-flag-talk.htm), updated March 8, 2023; accessed 2026-11-05.

**Proposed next contract, not implemented:** each command formation has a dated equipment profile. A message chooses only available methods and endpoints. Courier movement depends on routes; flags need staffed visible endpoints and suitable light/weather; wired communications need connected intact lines; later radio needs appropriate sets, operators and scenario-specific range. The WWII ceiling does not imply universal access to all wartime equipment. Land/sea headquarters, multiple allied controllers and hierarchical subordinates share the controller attachment and message lifecycle contracts.

## Versioning and verification

New battles use `poc-3`. Frozen `engine_v1.py` and `engine_v2.py` preserve existing games and exact replay. God Mode works on those saved games without inventing a command attachment retroactively. Select Reset to use a physical command unit.

`tests/test_command_observer.py` covers physical attachment and movement, voice, distance/terrain delay, moving-recipient forwarding, one transport step per interval, independent return acknowledgements, disrupted command with autonomous combat, direct versus remote observation, stale reports, expiry, God Mode isolation, resource conservation and exact replay. Earlier rules retain their edition-specific regression fixtures. HTTP checks exercise explicit observer selection and verify that both normal responses and model decision inputs remain restricted. Browser checks exercise live observation, command-unit movement and replay. These are rule/UI checks, not historical calibration, model-quality evaluation or Evo execution.

### Recorded local checks — 2026-11-05

- 80 component tests passed; offline HTTP smoke passed God Mode opt-in, ordinary/model view isolation, command attachment, replay and existing endpoint boundaries. UI reset/clock harness and map geometry/fallback checks passed.
- Final scripted-versus-scripted run: game `b06590674db54520`, 60 turns, 2,454 events, 64 stored revisions, exact replay; database `/tmp/battle-command-final.sqlite`. This is an authored-rule result, not evidence of historical balance.
- Existing main saves `6e0ca36658cb45f5` and `c8fd3e92f2034bcb` replayed identically under poc-1. Existing poc-2 fixture `961bedfe14e44b82` replayed identically.
- Isolated browser game `5769d25c15ba4cdc`: issued U2 a local movement order, observed headquarters move from hex 13,15 to 15,15, inspected all six formations and 346 events at turn 10, verified disabled orders/chat in God Mode, viewed omniscient revision 0, switched to the three-unit commander view, and returned live. Twelve revisions replayed identically. No browser console errors were observed.
- Screenshot: [God Mode at turn 10](../../apps/poc/artifacts/battle-god-mode.jpg). The main demo was restarted and checked with its original completed save; no new main battle was created. Temporary preview server/tab were closed.

No remote deployment, Evo run or new live-model evaluation was performed for this change.

### Control clarification — 2026-11-05

The user requested a toggle and Reset. God Mode now has an accessible on/off switch with visible state. Reset is a single-click scenario restart available in live play and replay: it pauses any running interval, archives the old battle, starts at 16:30 paused, clears pending UI selections and keeps the observer preference. No saved history is deleted.

Verification: updated UI harness passed. Browser checks confirmed the accessible switch, Reset while the clock runs, Reset from replay, paused 16:30 state, and retained God Mode. All three isolated test battles remained in SQLite after two resets. The main tab was refreshed without resetting its saved game.
