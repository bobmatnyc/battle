# Reconnaissance and standing reactions

Date: 2026-11-05. **User requirements:** sightings should progressively improve composition estimates; scouts and spies should be better estimators; units must defend themselves or retreat when attacked; commanders without orders need a plausible standing response to enemy contact.

## Implemented in poc-2

This is authored game behavior, not a historically calibrated model of Civil War identification or command psychology. No independent dice rolls or extra model calls are used. The existing higher commander can still use OpenRouter for delegated orders; local standing behavior continues without it.

### Progressive observation

Each observer retains its own target-specific observation exposure. A second scan in the same interval cannot add observation time. An interrupted sequence restarts exposure. Visibility and distance still use the scenario's LOS rules. Observer skill, sustained exposure, distance, target cover and observer suppression determine observation quality. Distance caps detail: prolonged distant observation cannot reveal everything.

The resulting report contains a strength **range**, broad type, weapon category, confidence label, source and timestamps. Initial sightings can be unidentified troops. Better observations identify infantry and, when sufficiently close and clear, weapon class. The current roster is all infantry; it does not pretend to discover a mixture of unit types that the scenario does not contain. No enemy name, exact headcount, ammunition, morale or orders are exposed.

Ranges are deterministic, quantized bands, never exact counts. Confidence labels are ordinal quality indicators, not calibrated probabilities. Under stable conditions, repeated observation tightens the bands. Distance, suppression, movement, casualties or a poorer replacement observer can broaden a new strength estimate; the UI does not promise monotonically improving intelligence regardless of conditions. Estimates describe collection time, not current enemy truth.

Identification is tracked separately from current position and strength. Recent, stronger type/weapon evidence can survive a poorer new sighting. A delayed spy report can enrich identification without overwriting a newer location or count. Each identification field retains its own source, quality and collection turn. Evidence older than six intervals is not carried into a fresh report. Contact records themselves still expire from the command view after six intervals without a new observation.

Reports obey delivery delay. A prompt warning and a slower, better estimate can both be sent, so a strong but slow spy channel does not suppress a scout's timely warning. Local commanders use their own immediate observations; headquarters, the staff adviser and the higher AI commander see only delivered reports. Local action and observation logs are authoritative audit records, not instantaneous player updates.

### Scouts and spies

New demo battles designate the existing U3 and C3 aggregate detachments as scouts. Their authored estimation skill is 80 versus 35 for line detachments. Personnel and equipment are unchanged; these assignments are not claims about historical regimental reconnaissance arrangements.

Spy estimation skill is 95 by default, with a three-interval reporting delay versus one interval for ordinary field reports. The engine supports scenario-authored aggregate `intel_assets` with an ID, side, position, `status: observing`, `recon_role: spy`, skill, optional observation range and report delay. They require actual local visibility and cannot reveal the whole map. They are observation assets, not simulated individual people.

**Scope limit:** the default demo does not deploy a spy asset, and there is no spy recruitment, infiltration, tasking or deployment interface. The spy path is exercised by granular scenario fixtures. Scouts are playable through the normal detachment movement interface; specialist mission systems remain later work.

### Standing commander policy

The deterministic `standing-contact-v1` policy evaluates each living unit before movement from its own condition and local contacts. It records the selected action, reason, target, visible estimates, under-fire state and effective mission version.

| Situation | Standing response |
|---|---|
| No contact or recent attack | Hold, or continue the received mission |
| Contact outside effective range | Observe and report; no unauthorised pursuit |
| Enemy within effective range | Defend and return fire; temporarily halt a movement mission |
| Better adjacent cover without closing on the enemy | Move to cover, retaining the mission destination |
| Failing morale, heavy suppression, less than one volley of ammunition, or serious depletion under recent fire | Attempt an orderly withdrawal before routing |
| Credible estimates indicate a substantially stronger nearby enemy | Withdraw; low-confidence silhouettes alone do not trigger this comparison |
| Scouting detachment facing a close, costly engagement | Prefer disengagement to committing the scouting formation |
| Under fire without a located shooter | Defend or fall toward known HQ, without inventing the attacker's position |
| No known safer adjacent escape | Remain in place and defend; do not teleport or stack |

Withdrawals choose adjacent ground that increases distance from observed threats, or improves cover at equal distance, with HQ direction as a tie-breaker. Known friendly/enemy occupancy constrains the proposal; actual occupancy and movement credit still adjudicate the attempt. Hidden units do not inform the decision. A short withdrawal commitment reduces oscillation, after which the unit can resume its original mission if contact and condition allow. These rules do not model formations, flanking doctrine, surrender or detailed maneuver tactics yet.

Orders still change intent only after delivery. Local reactions do not manufacture HQ orders, increment order versions, or erase a movement destination. Morale collapse remains a distinct routed status. Existing simultaneous volley resolution remains; return fire can occur during an interval before the next interval's maneuver decision reacts to newly received fire. Thus the model has 30-second reaction granularity, not continuous physics.

## Events, UI and compatibility

- `local_decision` records the standing policy decision and observed evidence; movement references its decision event sequence.
- `unit_under_fire`, `contact_observed`, report delivery and identification merge events are persisted with the rest of the atomic transition.
- The command map shows enemy estimate cards, identification source/age and strength-report confidence/age. Marker `I` means estimated infantry; `?` remains unidentified. Friendly cards show the last reported local action and its reason as a tooltip.
- New battles use `poc-2` / `little-round-top-v2`. Existing `poc-1` saves keep their old transitions through the frozen `battle/engine_v1.py`; they are not silently upgraded. The UI tells the player to start a new battle for the new behavior. Existing saved replays must continue to verify exactly.

## Verification

Granular fixtures cover sustained-observation refinement, repeated-scan protection, scout/spy advantages, occlusion and distance caps, report latency, timely warnings alongside slow intelligence, stale-location protection, separate identification provenance, no exact enemy-inventory disclosure, no-order defense, pre-rout withdrawal, better cover, retained missions, withdrawal cooldown, blocked retreat, unknown shooter behavior, hidden enemy state independence, legacy transitions and deterministic replay.

These tests verify the authored contracts, not historical realism. Coefficients, quality thresholds and behavior balance require playtesting and historical calibration separately. UI text is currently English, consistent with the POC's existing localization limit.

### Local verification record — 2026-11-05

60 component tests and the UI smoke suite passed. The full scripted-versus-scripted headless battle completed 60 intervals, wrote 2,247 events and verified identical replay across 63 revisions. This single outcome is not a balance claim. Both pre-existing poc-1 saved battles still replayed identically. Offline HTTP checks passed during integration; no live-provider evaluation was needed.

An isolated browser preview showed contact C1 changing from unidentified troops, 20–100 strength and low confidence at delivered revision 4 to infantry, 30–70 strength and moderate scout confidence at revision 5. The same preview showed U1 withdrawing under fire before routing and U3 defending without player orders. Actual reports arrived after their observation time. Preview state and gameplay were isolated from the user's saved battle.

Final visual evidence: `artifacts/battle-reconnaissance.jpg`. The isolated preview was stopped after verification. The main local demo was refreshed with the final rules and preserves the user's completed poc-1 battle; its notice directs the player to New battle for poc-2. A regression also verifies that poorer follow-up sightings do not repeatedly announce the loss of an already retained identification.
