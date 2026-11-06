# Language, localization and multiplayer communication

**Date:** 2026-11-05. **Evidence:** The user's explicit follow-up requirements for the specs/demo. These are product requirements and proposed contracts, not a new external-source survey. “Anachronistic language … appropriate to the era” is interpreted here as **period-appropriate speech addressed to a modern player**. Examples below are original illustrative prose, not historical quotations.

## Confirmed requirements

- Units and staff speak to the player in language appropriate to the scenario's era.
- Internationalization (i18n) is a default product requirement, including the UI and generated communication.
- The app includes an internal messaging system for communication between players.
- Multiplayer supports cooperative, antagonistic and terrain-control scenarios.

**Implementation boundary:** this update adds period dispatch presentation, agent voice instructions and a visible product-intent section to the demo. It specifies the other capabilities; it does not claim translated locales, player inboxes, network multiplayer or selectable multiplayer scenarios are implemented.

## Unit and staff voice

Voice follows scenario date, command role and communication medium. The 1863 demo uses concise written military dispatches: “General,” “headquarters,” “detachment,” “position,” “ammunition,” and “runner.” It avoids modern radio idioms or contemporary slang. A later WWII scenario needs its own voice profile; Civil War wording must not become a universal historical voice.

Use natural, intelligible language, not exaggerated dialect or theatrical archaism. Names, coordinates, quantities, uncertainty and report age must remain accurate. Style must never create extra facts, hide an order's meaning or expand authority. Modern interface labels and error messages should stay clear; the entire application need not impersonate a historical document.

Illustrative speech:

| Occasion | Example |
|---|---|
| Received order | “U1 to headquarters: Order O1 received.” |
| Reached position | “U1 to headquarters: We have reached the appointed position.” |
| Forced withdrawal | “U1 to headquarters: The detachment is breaking. We are falling back toward headquarters.” |
| Staff advice | “General, the latest reports may already be out of date.” |

Proposed profile fields: `voice_profile_id`, version, era/date range, role, medium, locale and plain-language preference. The demo uses `civil-war-en-v1`. Agent requests constrain only human-readable prose; JSON command keys, unit IDs, stance values and simulation rules remain unchanged. Generated wording is not guaranteed to be historically authentic simply because it was prompted.

### Saved games and the demo

`battle/presentation.py` renders recognized legacy dispatches through keyed English templates and preserves the original text. It decorates an already authorized observation; it cannot inspect hidden state or deliver reports early. Live views and replay use the same presentation adapter. Unrecognized text falls back to its saved original.

Existing chat replies remain verbatim; they are not retroactively rewritten. New model replies and the offline adviser use the current voice instructions, with the voice-profile ID recorded in decisions. Canonical `poc-1` transitions and old saved-state replay are unchanged. A future migration should put typed message keys and arguments directly into canonical event envelopes instead of parsing legacy English text.

## Internationalization by default

**Required design intent:** player language is independent of faction, nationality, scenario date and simulation rules. Allied players may use different UI languages in the same battle. Translated dispatches should preserve period register in the recipient's language without pretending that the original historical unit spoke that language.

Proposed implementation contract:

1. Externalize UI, scenario, tutorial, dispatch and outcome strings into versioned catalogs with stable semantic keys and typed arguments. Do not make English phrases into command identifiers or concatenate translated sentence fragments.
2. Support locale fallback, plural forms, Unicode, text expansion, right-to-left layout, accessible labels and localized dates/numbers. Use locale-aware presentation for quantities while keeping simulation coordinates, units and simulation timestamps canonical.
3. Keep `ui_locale`, message `source_locale`, recipient display locale and `voice_profile_id` separate. A translated view cannot change an order, objective, collision rule or replay outcome.
4. Pass a supported output locale and era profile to the model. Validate its structured orders in the same language-independent schema. Unknown or unavailable locales fall back explicitly; never silently claim a translated locale is supported.
5. Persist original player/model prose and accepted structured decisions. Optional translated renditions carry source-message ID, target locale and renderer/model version; the original remains available. Replay uses stored decisions and text, never a new inference call required just to view history.
6. Do not automatically send private player messages to a translation model or staff adviser. Translation must respect the authorized audience and the game's configured provider settings.

**Current state:** English only. Keyed English dispatch templates are an initial seam, not complete i18n. The rest of the UI still contains English strings. No language selector or invented translation pack is displayed.

## Internal player messaging

Player-to-player correspondence is separate from **unit reports**, **orders to units**, and **player-to-staff chat**. Writing a message is not a command to the engine, nor a grant of authority to an agent.

Proposed channels:

| Channel | Audience and purpose | Timing |
|---|---|---|
| Direct dispatch | Named eligible player commander | Scenario's in-battle command transport |
| Team dispatch | Eligible allied commanders, delivered separately to each | Per-recipient delivery; no automatic shared omniscience |
| Scenario correspondence | Opposing commanders when explicitly allowed by the scenario | Configured period-appropriate channel; no political/diplomatic subsystem |
| Lobby / after-action chat | Participants allowed by lobby/review rules | Outside simulated battle time |

The default in-battle coordination path respects era, distance, equipment and known delivery conditions. An instantaneous team chat would defeat the existing communications premise; it must not be introduced as an unlabelled bypass. Any future casual/social live channel requires an explicit scenario setting and a clear distinction from in-world dispatches. Staff chat is not a substitute implementation of player messaging.

A proposed persisted message envelope includes battle/thread/message IDs, sender and recipient player IDs, channel, audience, original body/source locale, optional structured report references, creation/send/arrival times, delivery state, reply-to ID and locale/voice metadata. Unit orders use their existing separate validated schema. Each send is authorized against membership and scenario relations, deduplicated by message ID, persisted and replayable. Delivery/read receipts must not reveal inaccessible recipient locations, enemy state or unseen events. Attachments can reference only reports the sender is authorized to share; no links that resolve into omniscient data.

Human correspondence may be mistaken or deceptive. It does not update terrain truth or enemy truth, and should not overwrite a confirmed contact merely because a player typed a claim. A commander can choose to act on it under the normal order-validation and delivery rules. Retained message audiences also apply to review/export; post-battle access should be an explicit scenario policy, not automatic publication of every private conversation.

## Multiplayer scenarios

**Relationship rules and objective rules are independent.** Terrain control can be competitive, cooperative, or team-versus-team; it is not a mutually exclusive third relationship type.

| Scenario family | Example | Required contract |
|---|---|---|
| Cooperative | Two allied players command separate formations defending a ridge against computer opponents | Shared victory conditions, explicit unit authority, routed team dispatches; assistance never grants command ownership automatically |
| Antagonistic | Players command opposing sides in an attack/defense battle | Fixed opposing relations, separate knowledge, simultaneous planning/resolution, deterministic outcomes |
| Terrain control | Players or coalitions contest a ridge, crossroads or harbor | Defined control areas, eligible occupants, contesting rules, capture duration, scoring/deadline and ties |

Scenario proposals should describe sides/teams, player and AI controller assignments, fixed relationships, command ownership/delegation, intelligence-sharing policy, communication channels, objectives and terminal conditions. Support more than two sides without assuming every other player is an enemy. Fixed cooperation/opposition does not add politics, diplomacy or negotiation mechanics.

For terrain objectives, define whether “control” means physical occupation, uncontested presence, continued supply/access or some other explicit condition. Specify how routing, casualties, contested occupancy and equal scores affect control; do not let model prose decide the winner. Compute control from authoritative state, but deliver battlefield control reports through the appropriate information channels. Terminal adjudication can be displayed separately as a game result. Objective declarations need their own version and stable IDs.

**Current demo:** one human Union commander against one computer Confederate commander. The summit is an existing local terrain-control objective with an asymmetric defend/hold deadline. There is no multiplayer session, shared player command, player inbox or scenario picker yet.

## Campaign play across multiple fronts

**Confirmed direction:** The user's “Risk-like” example adds a campaign map on which players deploy units or armies to different fronts. The reference describes the desired strategic experience; it does not adopt another game's combat or reinforcement rules. Campaign play can be cooperative, antagonistic or team-based, with terrain-control objectives across several regions.

The player decides **where to commit forces, what each front must accomplish, which commanders receive authority, and when to reinforce or withdraw**. Subordinate agents conduct local battles within that intent. The campaign and tactical views should share one accounted force state, rather than becoming disconnected games.

Proposed two-scale model:

| Scale | Representation | Player decisions |
|---|---|---|
| Campaign | Regions, connecting routes, contested fronts, armies/formations, reserves and objectives | Allocate existing forces, assign commanders, choose front priorities, redeploy and set strategic objectives |
| Battle | A front's selected engagement area, terrain hexes and participating aggregate units | Issue missions and movement orders through period communications; let commanders execute |

A **front** is a contested operational area linked to regions and routes; it is not necessarily a single hex or an entire region. An army is a command grouping of aggregate formations. Detachments may be assigned to different fronts only through explicit subdivision or transfer; the same troops cannot be counted in two battles. Formations remain temporary, with accounted personnel/equipment/condition, rather than permanent individual characters.

The campaign loop is **review map and dispatches → allocate forces and delegate missions → resolve movement and engagements → apply battle outcomes → revise front priorities**. The general can concentrate forces on one front while leaving a subordinate to hold another. The twin may help compare these choices using authorized knowledge; autonomous campaign orders still require explicit delegation.

Proposed consistency rules:

- Deployment and redeployment consume scenario-defined travel time and route/transport capacity. Assignment is not arrival. A force in transit cannot simultaneously defend its old front or fight at its destination.
- Preserve strength, equipment, ammunition, fatigue and morale when entering or leaving an engagement. Losses do not reset between battles. A result commits once, with battle/front IDs and a versioned campaign-state reference.
- Regional control changes only under explicit occupation, contesting and victory rules. A tactical win does not automatically award a whole region unless the scenario defines that consequence.
- Resolve concurrent fronts against a shared simulation clock. Define command windows, transit arrivals and battle-result barriers so one engagement cannot advance campaign time independently or reuse already committed forces.
- Keep the player's campaign map distinct from ground truth. Front reports, reinforcement requests and orders between headquarters obey the scenario's communication technology and delivery delays. Allied players receive information through configured sharing channels, not an automatic omniscient team map.
- Initial armies and reserves may be scenario-provided. Allocating existing forces does not introduce army purchasing, recruitment or battle provisioning; those remain later work. Any eventual reinforcement generation needs its own explicit resource rules.

Illustrative scenario: one allied player defends a river crossing while another commands the ridge front; their general decides whether to transfer a reserve detachment to the crossing. The reserve arrives only after the modeled journey, and the ridge's reduced force must hold meanwhile. This is an authored design example, not a historical claim.

**Status:** campaign/front allocation is now part of the specs and demo intent. The current Little Round Top POC remains one local engagement; no campaign map, inter-front movement or campaign persistence loop is implemented yet.

## Acceptance plan for later implementation

- Two locales render equivalent received information and produce identical accepted orders/outcomes; missing keys and unsupported locales fall back explicitly. Check plurals, right-to-left rendering, text expansion and non-Latin player messages.
- Switching voice/locale does not mutate saved truth, leak hidden contacts, change report receipt times or call a model during deterministic replay.
- Direct/team messages reach only eligible recipients, exactly once, at their permitted arrival times; reconnect and resend preserve identity and audience. Unauthorized history access and unit-command injection through player prose fail.
- Two cooperative players retain separate unit authority and receive shared reports only under the configured sharing/delivery rules.
- Antagonistic players resolve the same planning window fairly without seeing each other's hidden orders.
- Terrain-control fixtures cover contested ground, capture timers, alliances, three sides, routing, deadline ties and delayed reports, with explicit deterministic victory rules.
- Campaign fixtures cover two simultaneous fronts, a reserve transfer, delayed arrival/reporting, conservation through formation subdivision, duplicate battle-result rejection, and deterministic campaign replay. A unit cannot be deployed or fight in two places at once.

These are specifications, not claims of passed multiplayer or localization tests.

## Validation of this update

### Copy for the Little Round Top recommendation card

Original English copy for a Civil War infantry commander requesting a Dig in order:

> **Request to throw up breastworks**  
> General, all is quiet here. With your leave, I shall set the men to throwing up breastworks along our line.

For the example report, the clerk’s line reads “Written at 4:31 p.m. · Received at headquarters at 4:32:30 p.m.” Keep the separate action deadline explicit: “Reply before 4:37 p.m.” Render that deadline with the same inclusive or exclusive boundary as the validation rule. Label the two actions **Decline request** and **Send the order**. Sending dispatches an ordinary Dig in order through the existing transport.

Display ammunition as “1,600 rounds on hand” and retain the exact fatigue and morale figures under **Condition when reported**. Select these strings through the scenario voice profile and locale for both the recommendation card and the dispatch feed. Historicize new prose at presentation time when possible; display archived original dispatch text faithfully on replay. Use only the source facts available to the reporting commander. Do not invent a signature, courier, sighting or completed work.

All 33 component tests passed, including non-mutating dispatch presentation and fallback for unknown saved prose. HTTP and JavaScript smoke checks passed. Both existing SQLite battles still replayed identically. The new voice prompt was installed without making another paid inference call; historical style remains an instruction, not a guarantee of every model response. No translated locale or multiplayer runtime was tested or added.
