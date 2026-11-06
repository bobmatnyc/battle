# Unit panel and formation actions

2026-11-05. **User requirement:** clicking a unit reveals strength and options such as move, give an order, split and combine. **Implemented:** the following bounded POC behavior, using new `poc-4` rules. Earlier lifecycle research remains applicable to broader future remixing/training.

## Inspection and commands

Map markers and detachment cards select a formation in the command panel. Own formations display reported troop strength, ammunition, morale, suppression, fatigue, weapon class, reconnaissance role, mission, order version, local judgment and observation age. Selecting an enemy contact displays strength ranges, composition and confidence; it exposes no actual ammunition, condition or orders. God Mode can inspect exact formations on either side; commands remain disabled there and during replay.

Move asks for a destination hex. Give an order opens a structured move/hold composer for the selected unit. Hold dispatches a hold order directly. These use the existing voice/courier route and ordinary version precedence. Free-form staff discussion remains in Staff chat; this composer does not imply support for arbitrary natural-language missions.

Split opens a troop-count field and asks for an adjacent hex. Combine lists adjacent, compatible friendly units; the selected formation is the survivor. Unavailable actions remain visible with explanations. The panel shows requested reorganization and its reported outcome.

## Formation lifecycle

The following are **authored, uncalibrated POC choices**, not historical measurements:

- A split must leave at least 12 troops in each formation. The child occupies an adjacent unoccupied hex after the regrouping period. Personnel do not appear at a distant destination.
- Combine requires adjacency, no more than 80 total troops, and identical troop type, weapon class, proficiency, reconnaissance role and reconnaissance proficiency. Mixed-cohort integration remains deferred rather than upgrading or averaging incompatible training.
- Headquarters stays with the selected surviving parent. To combine a command detachment, select it as the survivor; it cannot be silently absorbed into another ID.
- Every affected commander receives a normal versioned hold instruction. A combine therefore sends two independent messages and waits for both receipts. Once all orders arrive, two committed intervals (60 seconds) are required for regrouping. Units still defend themselves.
- Recent incoming fire, significant suppression, a withdrawal in progress, visible enemy contact within effective range, rout or destruction prevents regrouping. These are checked locally each interval and again at completion. A newer delivered order supersedes the operation. Changed strength, position, incompatible profile or occupied destination can also cause refusal.

API validation uses headquarters' reported state. Hidden changes are adjudicated when the commanders receive and execute instructions, not disclosed through immediate validation. The normal view shows **awaiting report** until completion/refusal arrives through a report. Failure to hear back is not proof of success. If no affected formation survives to send a report, the engine audit still records the outcome while headquarters remains uninformed.

## Accounting and history

A split apportions starting-strength accounting, ammunition, movement credit and fractional casualty accumulation using integer proportional allocations with the remainder retained by the parent. Both children retain their source proficiency and condition. Headquarters is not duplicated; inherited reconnaissance memory is only the parent's local evidence.

Combine sums surviving personnel, starting-strength accounting, ammunition and casualty residuals. It keeps the lower morale, higher fatigue/suppression and the more restrictive recent-fire/withdrawal state; movement credit does not improve. Existing ordinary rest can still recover condition over elapsed time. There is no healing, resupply or free readiness reset from splitting and recombining.

The absorbed predecessor becomes a zero-resource `merged` record pointing to its survivor. Its full pre-transfer state is archived in `retired_units`; old identity, causal events and orders remain auditable. It cannot fight, hold objectives, originate new reports or receive actionable orders. A late friendly report cannot resurrect it after the retirement report has arrived. Casualty accounting across changed formations follows lineage and force totals, rather than treating each successor's original ID as an independent historical roster.

`formation_requested`, `formation_regrouping`, `unit_split`, `units_combined`, `formation_completed` and `formation_refused` events connect instructions to effects. Before/after resource snapshots are recorded for transfers. Normal order/packet send, receipt and expiry events remain intact. Save failure rolls back snapshots, unit records and events together.

## Compatibility and limits

Existing games keep their rule edition. Unit inspection and ordinary orders work with old saves; Reset starts a fresh `poc-4` battle for split/combine. Frozen engine editions preserve previous replay. The UI does not reset the player's battle automatically.

The current model commander still chooses move/hold orders; split/combine are player-issued instructions executed and locally validated by subordinate rules. General force construction, mixed equipment/cohort reorganization, training, disbanding and provisioning remain deferred. Equipment is represented by the scenario's common weapon class and armed troop count; there is no separate spare-weapon inventory yet.

## Verification

Component checks cover delivery plus setup time, conservation of troops/ammunition/residuals, headquarters uniqueness, invalid counts, authority, adjacency, matching profiles and capacity, local refusal during fire, superseding orders, repeated-request safety, report delay, retired IDs, transaction rollback and exact replay of split/combine. Frozen `poc-3` transitions are compared directly against their saved engine. HTTP checks cover real action endpoints and the full split/combine sequence; browser checks cover selection, forms, order submission and observed outcomes. These are rule/UI checks, not historical calibration or Evo testing.

### Local verification record

- 97 component tests passed; UI action/reset harness, map geometry/fallback checks and offline HTTP smoke passed.
- Scripted headless game `d154100b76d0495a`: 60 turns, 2,454 events, 64 revisions, exact replay.
- Browser game `a5101a4c3e584044`: selected U2 directly on the map, split its 40 troops/1,600 rounds into 20/800 plus 20/800, then combined back to 40/1,600. Both operations completed and reported through the simulation; Give an order dispatched a selected-unit hold instruction. Enemy inspection in God Mode disabled commands. The recorded transitions replayed identically.
- Browser regression found and fixed: irrelevant numeric inputs are disabled, so a hidden Split count cannot block Combine's native form submission.
- Existing main poc-1 and poc-3 saves replayed identically. No main battle was reset.
- Screenshot: [selected-unit panel](../../apps/poc/artifacts/battle-unit-actions.jpg).

No deployment, Evo execution or additional live-provider evaluation was performed.
