# Common order templates

**2026-11-05 — user requirement:** create reusable orders such as rest, retreat and resupply. **Implemented local POC:** `poc-5`, catalog `common-orders-v1`. These are authored game rules, not historically calibrated procedures or quoted military orders. This extends the authorized Python/SQLite demo; campaign provisioning remains deferred.

Select a friendly formation → **Give an order** → choose a template. Select a destination hex when required, send the instructions, then start the clock. The panel shows readable period phrasing, effects, mission status and the latest reported reason. Staff and computer commanders receive the same catalog with their authorized observations. Split/combine remain separate formation actions.

| Template | Player supplies | Delegated intent | Completion / interruption |
|---|---|---|---|
| Hold and defend | Unit | Hold present ground; defend and report contact. | Continues until replaced. Local cover-seeking and self-preservation remain available. |
| Move to position | Unit, hex | Proceed to the appointed position; report arrival. | Reaching the hex changes the mission to hold. Contact can temporarily interrupt travel. |
| Rest and recover | Unit | Halt and rest the men while maintaining a watch. | Zero fatigue completes the mission, then hold. Contact, recent fire, suppression or tactical movement suspend recovery. No healing, replacements or ammunition creation. |
| Retreat to position | Unit, hex | Fall back in order, preserve the detachment and report when established. | Reaching the hex changes the mission to hold. Locally observed threats constrain the next step; if no safe step is known, defend in place. Ordered retreat does not mark a unit routed. |
| Replenish ammunition | Unit | Proceed to the nearest recorded compatible friendly ammunition point and replenish cartridge boxes. | Load to the current strength-based capacity, then hold at the point. Empty stocks fail with a report; contact suspends loading. Return to the front requires another order. |
| Reconnoiter position | Unit, hex | Examine the appointed ground, observe and report; avoid a close engagement. | Remains an observation mission until replaced. On contact, fall back without closing on observed threats; resume toward the appointed ground when safe. Ordinary units retain their ordinary estimation skill. |

## Shared contract

Canonical public order: `unit_id`, `stance` (the template ID), `destination`. Move/retreat/recon require an in-bounds hex; hold/rest/resupply require null. The engine resolves the supply point from briefing knowledge at dispatch and records its identity/address in the accepted order. Unknown templates, extra action fields and commands to another side are rejected. Supply availability is checked locally on execution, not revealed by remote validation.

All orders use the existing authority, versioning, voice/courier delivery, supersession and acknowledgement rules. An order sent is not an order received. No mission begins before receipt. Commanders remain autonomous and may defend or withdraw when threatened; rest and resupply do not disable self-defense. Later delivered orders replace prior intent through the same channel. Routed/lost formations cannot take new orders; an active mission fails if its formation becomes ineffective.

`battle/orders.py` is the shared catalog and mission implementation. Stable template IDs, `message_key` and catalog version separate simulation values from English labels/phrasing. This is a localization seam; the demo is still English-only. The ordinary observation exposes only that rule edition's legal templates. Older editions retain move/hold.

## Explicit POC coefficients and logistics boundaries

- Rest removes **6 fatigue points per 30-second interval** while safe, in place of the ordinary idle recovery. It does not directly increase morale or change troop strength.
- Each side starts with one **fixed ammunition point holding 2,400 rounds**. Union: hex **14,8**; Confederate: **4,20**. Their positions and rifle compatibility are initial briefing knowledge; their current stocks are not remotely live-tracked.
- A detachment must be at or adjacent to its point to load. At most **5 rounds per current troop per interval** transfer, up to a nominal **40 rounds per current troop**. Casualties do not erase cartridges already held; quantities above that capacity are retained, and no further rounds are added.
- Loading executes after simultaneous combat. Visible enemies within five hexes, fire in the current/preceding interval, suppression over 20, or active tactical movement prevent loading/recovery.
- Stock decreases by exactly the unit's gain. Competing pickups resolve in stable unit-ID order; this is reproducible but is not a fair logistics scheduler. Empty points do not regenerate, and failed replenishment does not automatically select another point.
- Ammunition points are fixed scenario fixtures, not quartermaster units. There is no wagon dispatch, carrying-unit allocation, food/fuel delivery, depot capture/destruction, stock procurement, replenishment from off-map or reinforcement creation. Those need separate rules.

Supply icons on the map show known friendly points. God Mode can inspect both sides and exact remaining stocks. A recipient learns loading results locally; headquarters learns the unit's ammunition/mission result through delivered reports or direct observation of its command detachment.

## Outcomes, audit and replay

Mission state records template, effective order version, start/update turns, status and reason. Events record mission start, supersession, blocking, resumption, completion/failure, fatigue recovery and ammunition transfers. Transfers record source, recipient, amount and resulting quantities. Existing fire events account for ammunition spent. Every effect is committed in the same SQLite snapshot/event transaction; a failed persistence operation cannot partially debit a point or credit a unit.

Mission reports use the existing communication queue. The unit panel reads delivered friendly reports, except direct knowledge of the command detachment. It does not inspect live remote mission truth. Detailed authoritative events remain available to God Mode and the final audit. Replays use saved inputs and decisions with no new inference.

New battles use `poc-5`; `engine_v4.py` and `formations_v4.py` freeze the preceding rules, alongside the earlier rule editions. Use **Reset** to start a new battle with the new catalog. Existing saved battles are not migrated or replaced automatically.

## Validation and limits

17 focused order tests cover: shared/versioned catalog, invalid inputs and authority, delivery before rest, completion, fire interruption, ordered retreat under contact, cautious recon without skill inflation, rate/capacity/stock conservation, distant pickup travel, finite-stock failure, fog-of-war and delayed completion, supersession, persistence rollback, exact mission replay and frozen `poc-4` transitions. The full component suite now has **114 tests**. UI harness and HTTP smoke tests exercise template payloads and acceptance; browser verification checks selection, dispatch and reported completion.

The scripted-versus-scripted headless run reached 60 intervals with 2,489 events and 63 identical replay snapshots (`7a2247f1c25d44a6`, local `/tmp/battle-common-orders-headless.sqlite`). This is rule/integration evidence, not historical calibration, live-model quality evaluation, Evo execution or deployment. The scripted baseline still follows its simple positional plan; OpenRouter can select from the expanded legal catalog.

Potential later templates include rally/reorganize, entrench, screen, escort and coordinated assault. They are **not selectable placeholders**: each needs explicit authority, timing, resources, target-knowledge constraints and interruption/completion rules before becoming a working order.
