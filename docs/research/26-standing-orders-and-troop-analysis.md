# Standing orders and troop analysis

Date: 2026-11-05. Status: implemented local POC, rules `poc-8`. This is an original design and implementation record; thresholds are authored tuning values, not historical measurements.

## User requirement

Players can set or request recommended standing orders and assess a unit or their troops before starting and at any time during battle. This extends the existing autonomous contact behavior and commander recommendation flags.

## Implemented command contract

Standing doctrine persists independently of the current mission. Sending “Preserve the force” does not cancel a movement destination, rest, resupply, or digging assignment. Each unit has a `standing_profile` and independently increasing `standing_version`. The separate `standing_orders` queue uses the same physical voice/courier transport, expiry, command authority and acknowledgement rules as mission orders. A newer doctrine delivered first cannot be overwritten by a late older one.

The player chooses a template, reviews its intent and explicitly dispatches. “Use recommendation” fills a draft only. Orders may be dispatched at turn zero, but transmission and adoption require the clock to run. Local voice delivery occurs on the next interval; distant orders require a journey. The recipient can refuse if routed, lost or merged when delivery occurs. An undelivered order cannot change a local commander's judgment. Headquarters sees adoption only through direct observation or delivered information. Loss of headquarters does not revoke already dispatched instructions.

| Template | Morale withdrawal threshold | Suppression threshold | Estimated enemy / own strength | Cartridge reserve | Firing range |
|---|---:|---:|---:|---:|---:|
| Balanced | below 45 | at least 70 | greater than 2.5 | below 1 volley | 5 hexes |
| Preserve the force | below 60 | at least 50 | greater than 1.5 | below 3 volleys | 5 hexes |
| Hold ground firmly | below 35 | at least 85 | greater than 3.5 | below 1 volley | 5 hexes |
| Observe and screen | below 60 | at least 50 | at least 1 | below 3 volleys | 3 hexes |

Condition thresholds are evaluated on local contact, recent fire or an ongoing withdrawal. Enemy strength comes from credible local estimates, never exact enemy totals. Existing hard rout, depletion under fire, scout caution, cover seeking and withdrawal persistence still apply. Firm doctrine cannot prohibit panic or guarantee obedience. Explicit retreat/recon missions retain their safer mission-specific behavior. These are four bounded heuristics, not arbitrary executable player rules or new combat abilities. Screen doctrine changes firing range but does not grant scout skill.

A split child inherits the parent's doctrine with its own version counter starting at zero. Combining preserves the survivor's doctrine; the retired formation's instructions cannot silently retarget the survivor. Formation events retain before/after state. Both sides use the same engine contract. The current strategic model/scripted command interface still produces mission orders; automatic strategic doctrine changes are not implemented.

## Assessment and recommendations

**Troop analysis** opens a headquarters assessment; **Standing orders & analysis** on a selected friendly unit opens the same screen with that unit selected. Available at turn zero, while paused or running, after battle and during replay. Reading it never advances or pauses simulation time, calls inference, or mutates canonical state. Dispatching instructions follows the normal pause-and-commit UI flow.

The assessment reports aggregate personnel and ammunition, formations reported available, oldest report age, and per-unit strength, volleys available, proficiency, role, morale, suppression, fatigue, mission, doctrine and observation/receipt times. Concerns and suggestions follow deterministic, versioned rules. Depleted, shaken, suppressed, tired or low-ammunition reports suggest Preserve the force; otherwise scouts/recon missions suggest Observe and screen; otherwise Balanced is suggested. Firm is a player's strategic choice, not a generic readiness recommendation.

`analysis.assess` takes only the authorized `engine.view` projection. It does not accept an omniscient observer view. Even in God Mode the staff analysis is built from headquarters knowledge and its send controls are disabled. Hidden enemy movement, exact inventory and undelivered friendly conditions do not change an assessment. Enemy estimates remain separate, dated contacts rather than an asserted enemy total or combat-power ratio. Report-based totals may combine different observation times, particularly around losses or reorganization. This limitation is shown explicitly.

The screen updates as new state/report snapshots arrive; draft choices remain drafts. In replay it assesses the recorded headquarters knowledge at that revision and disables sending. Legacy battles can be assessed, but require Reset into `poc-8` to configure doctrine. Reset archives existing games; no silent rule migration.

## Persistence and interfaces

- `POST /api/standing-orders`: `{game_id, revision, instruction: {unit_id, profile_id}}`; strict template/ownership validation and revision checks.
- `standing_order_sent`, `standing_order_delivered`, `standing_order_refused`, `standing_order_superseded`, and `standing_order_expired` events record command lifecycles. Transport and incoming acknowledgement events retain timing and causation. Local decisions record the effective doctrine/version.
- `GET /api/state` and recorded `/api/replay` include an observer-derived `analysis`, not a writable new simulation state. Analysis reading produces no audit mutation; accepted commands and their effects are logged.
- Template IDs, message keys and version identifiers are stable localization seams. UI and analysis text remain English in this demo; full i18n remains a product requirement.
- SQLite stores accepted actions atomically with their events and snapshots. Replay applies recorded inputs without model requests.

## Verification

The component suite now contains 160 passing tests. New checks cover turn-zero dispatch, courier versus acknowledgement delay, independent command versions, late-order supersession, doctrine effects and hard rout, screen fire range, authority, arrival-time refusal, both sides, split/combine inheritance, failed-save rollback, replay, observer isolation, timestamps, legacy and completed assessments. HTTP and UI harnesses exercise explicit recommendation review/dispatch and observer controls.

Browser verification used an isolated offline battle: U3's suggested screening doctrine was dispatched before time started; headquarters initially retained Balanced, then displayed Observe and screen after reports arrived. A later assessment showed U1's reported casualties, suppression, aged intelligence and revised Preserve-the-force recommendation. The main saved battle remains untouched. These checks establish local rule behavior, not historical calibration, live-model quality, Evo execution or deployment readiness.

Local run evidence: offline headless game `9104d6ab1700428e` completed 60 turns with 2,562 events and 63 identical replay revisions in `/tmp/battle-standing-headless.sqlite`. Browser test game `99443907f3c746af` in `/tmp/battle-standing-preview.sqlite` stopped at turn 13 and replayed all 15 revisions identically. [Review screenshot](../../apps/poc/artifacts/battle-standing-analysis.png). Existing main game `1dc13035e2844411` remains paused at turn 4/revision 4, with its earlier rules preserved. The temporary preview server was stopped after verification.
