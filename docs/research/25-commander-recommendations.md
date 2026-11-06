# Commander recommendations and flags

**2026-11-05 — user requirement:** unit commanders recommend actions, with a flag or a runner as the notification. **Implemented:** `poc-7` uses a clickable gold flag on the unit's reported map location and an **ADVICE** badge on its unit card. Recommendations are generated locally and delivered through the existing voice/courier system. The flag is a UI notification of receipt, not an in-world long-distance signaling device.

Click the flag (or focus it and press Enter/Space) to inspect the commander's suggestion, supporting condition at report time, observation/receipt timestamps, expiry and status. **Dispatch suggested order** sends the saved proposal through the ordinary authority, versioning and transport system. **Dismiss** records a response and leaves the effective mission alone. Accepting is not instantaneous execution; a runner may need to carry instructions back to the unit. Opening or reading advice never executes it. The unit continues autonomous tactical behavior while waiting.

## Current local advice policy

The first POC uses a deterministic, bounded heuristic (`commander-advice-v1`), with no extra inference calls. These priorities and thresholds are authored rules, not historical measurements:

| Priority | Local trigger | Proposal |
|---|---|---|
| 1 | Commander is already withdrawing locally, without a retreat mission | Retreat to the scenario's known friendly rally point |
| 2 | Ammunition below ten rounds per current troop, without a resupply mission | Replenish ammunition |
| 3 | Fatigue at least 55, with no close observed contact/recent fire and no rest mission | Rest |
| 4 | Holding after the first minute, quiet ground, tools available, fatigue below 55, no complete fieldworks and no building/road excavation conflict | Dig in |

A commander uses its effective mission, own condition, locally observed contacts and ground at its occupied hex. It cannot know orders still travelling from headquarters. Advice can therefore cross a newer order in transit; headquarters marks that advice superseded when received. No hidden enemy inventory, exact unseen position or global intelligence is consulted to generate the suggestion.

Both sides can generate recommendations. Human-facing observations expose only recommendations received by that side; the computer's model observations obey the same boundary. The existing computer commander can consider received advice, but the scripted baseline still follows its simple positional plan. A richer model-generated recommendation policy is not implemented here.

## Delivery, staleness and choices

- Recommendations from the attached command detachment arrive locally by voice; remote formations send ordinary terrain-costed couriers, including forwarding if headquarters moves. Headquarters disruption can prevent receipt. No flag or proposal payload is revealed before receipt in the normal view.
- The map flag uses the unit's **reported** position, not its live hidden location. God Mode can inspect recommendation records and courier packets, and the existing courier overlay shows their movement; it cannot dispatch or dismiss through its UI. Replay is likewise read-only.
- Advice expires after **12 intervals / six simulation minutes**, including delivery time. A unit waits at least **16 intervals / eight minutes** between recommendations. These bounds prevent per-tick nagging; quiet units may offer another suggestion later if their circumstances still warrant it.
- Newer orders already sent by headquarters supersede the old advice immediately in the headquarters view, even before those orders reach the unit. Expired/superseded advice remains inspectable but cannot be accepted. It may be dismissed.
- Proposal acceptance revalidates current authority and delivered friendly knowledge using the normal order validator. Subsequent field conditions may still cause local refusal or adaptation. The API takes a recommendation ID and accept/dismiss response; it never executes a client-substituted proposal.
- Accepted or dismissed IDs cannot be processed twice. Flags clear when advice is accepted, dismissed, expired or superseded. Only actionable, delivered advice has a flag. Dismissal does not issue a hold or cancel the unit's current order.

## Persistence and replay

Each record stores side, sender, creation/expiry time, effective mission version, policy, exact proposed order, period prose, supporting observation, receipt time and response. Events record creation, receipt, acceptance/dismissal, expiration and supersession; acceptance links the resulting order ID. Courier report events preserve the transport chain. State and essential events are persisted atomically with revision checks, so a failed save cannot leave an accepted recommendation without its order or vice versa.

New battles use `poc-7`. `engine_v6.py`, `orders_v6.py`, `formations_v6.py` and `features_v6.py` freeze the previous edition alongside earlier versions. Existing saves keep their behavior and have no new recommendations; use **Reset** to start the new rules. Replay reuses recorded generation and responses without fresh model calls.

## Validation

The **144-test** suite includes 15 focused recommendation tests: local and remote delivery, headquarters disruption, explicit acceptance versus execution, duplicate rejection, dismissal/cooldown, expiration, supersession, ignorance of undelivered orders, side/receipt permissions, local evidence, ineffective units, transaction rollback, exact replay and old-save compatibility. API and UI harness checks cover flag/card rendering, review, accept/dismiss payloads, observer guards and normal order delivery.

Browser verification confirmed a flag opens its panel, accepted U2 advice becomes a delivered Dig in mission, and a remote U1 recommendation dated 16:31 arrives at 16:32:30. A pointer-event issue in the map overlay was found and corrected during this check. The isolated test battle remains separate from the user's current battle.

Headless run `3190f6f08d3742d2` completed 60 intervals with 2,562 events and 63 identical replay snapshots in `/tmp/battle-recommendations-headless.sqlite`. Previous local rule editions also replayed identically. This is local rule/integration evidence, not historical calibration, model-quality evaluation, Evo testing or deployment.
