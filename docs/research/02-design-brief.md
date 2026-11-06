# Proposed game design

Everything in this document is a proposal unless marked as a user requirement.

## The player's job

The player's primary job is to choose battle strategy, assisted by a virtual twin. **User requirements:** subordinate agents deal with battlefield conditions, and the player may give orders directly to unit commanders when logistically possible. The compelling question is: **Which battle plan should I choose, what should I delegate, and when is direct intervention worthwhile and possible?**

At every command window, the player weighs a small number of consequential choices: advance or wait, fire or conserve ammunition, press an advantage or rally, hold an objective or preserve the force. Subordinates turn that intent into local actions. Their reports may be late or incomplete; their choices must remain understandable.

The twin helps compare approaches, identify assumptions and risks, and translate the selected strategy into proposed orders. It may coordinate orders under an explicit delegation, but the player is not required to micromanage every unit. Direct command is an optional intervention through the available communication system. Here strategy means the plan for the battle; it does not introduce political simulation or a required grand-strategy economy.

Orders express purpose, a task, priorities and limits. An agent chooses a feasible local approach, monitors results, and adapts without waiting for the player whenever its authority permits. It reports material changes or requests a new mission when the existing one is no longer achievable within its limits. Training and remixing are supporting choices, not the core play loop. See [tactical execution](04-command-and-agents.md#the-tactical-execution-loop).

The simulation should generate stories through persistent consequences: a reliable platoon becomes exhausted; an apparently empty wood conceals a contact; an isolated commander continues an outdated order; a successful defense leaves too little ammunition for the next battle. Narrative text explains recorded events and never creates them.

## The command map

**User requirement:** the player is given a command map. The interaction details below are proposals.

**User requirement:** grids can overlay actual maps, with terrain reading. Proposed support includes historical map sheets and charts aligned to a physically scaled hex grid, plus a validated terrain layer for movement and visibility. The player and twin interpret only their authorized map and reports. See [real-map workflow](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation).

**User requirement:** technology and communications stop at WWII, and players receive tools available to generals by that period. The proposed interface represents a period command desk; available maps, reports, staff services and channels depend on scenario era and command context. See [period command tools](14-period-command-tools.md). Digital presentation and twin assistance cannot create modern battlefield awareness.

Use the map as the main workspace for understanding the battle, selecting strategy with the virtual twin, and directing commanders. Represent units and formations as aggregate symbols. A selectable hex overlay can expose distance and areas without requiring the player to manage every unit's hex-by-hex movement.

**Confirmed:** maps and dispatches are the primary information interface, and all units in combat execute autonomously. Pair the map with a dispatch inbox showing orders, acknowledgments, reports and requests, their evidence times and arrival times. Unit markers and status reflect received information or valid direct observation. Selecting a unit issues intent to its autonomous commander; it does not open manual combat control. See [autonomous units and dispatch-based command](04-command-and-agents.md#autonomous-units-and-dispatch-based-command).

Proposed information layers:

- Known terrain, elevation, routes, crossings and landmarks, plus observed weather and seasonal surface conditions.
- Reported friendly positions, missions and condition summaries; enemy contacts with last-known area, confidence and report age.
- Scout coverage and spy reports, distinguishing direct observations, reported claims and planning assumptions; intelligence tasking remains subject to available assets, time and communication constraints.
- Objectives, assigned areas, intended routes, boundaries and timing. Distinguish a planned route from reported actual movement.
- Known command links, estimated delivery times and order states such as drafted, sent, acknowledged, executing and completed.
- Relevant known civilian locations and constraints as those systems become supported.

Selecting a unit opens its latest report, current mission, available command channel and order history. Selecting an area or drawing a route proposes an objective, boundary or route preference for a structured order; it does not directly move troops. The player can ask the twin to compare approaches or draft an order using the same authorized view. Show whether a route is suggested, required or left to subordinate discretion.

Unknown and stale information must remain visible as uncertainty. A friendly marker can represent an old report rather than a live position. The base map may be available at setup under scenario rules, but unseen bridge damage, changing ground conditions and enemy movements cannot appear automatically. Forecasts remain distinct from observed weather and the hidden future weather schedule. Map annotations and proposed orders must not reveal hidden facts through validation messages.

An event timeline connects selected units, reports and orders to observed outcomes. A later after-action view can reveal additional facts only under the scenario's disclosure policy; full diagnostic replay is a separate privilege. The map is a projection of authorized observations and recorded orders, never a second writable source of battlefield truth.

For the first headless duel, define and validate those observation/order records without building a UI. Future land, sea and amphibious views share the command interaction while using appropriate scale and domain layers. Visual style, controls and framework remain undecided.

## Required scope and recommended boundaries

| Area | User requirement | Proposed interpretation |
| --- | --- | --- |
| Player role | Choose battle strategy with virtual-twin assistance; direct unit orders when logistically possible | Assisted planning, explicit delegation, and communication-constrained intervention |
| Command interface | Player receives a command map | Observation-scoped map, selectable formations, strategic annotations and structured orders; UI follows the headless prototype |
| Unit size | Roughly platoon-sized historical groups | An aggregate with personnel/equipment cohorts; exact establishment varies by period |
| Agency | Each platoon has agentic control using a moderate model | Controller bound to the active formation; model invoked at decisions, with rule-based reactions between calls |
| Unit lifecycle | Units are not long-lived; commanders can train or remix them; no individual combat game | Temporary formations of aggregate cohorts, with conserved resources and condition across reorganization |
| Complexity | Deterministic handling using a graph database | Explicit graph state and relationships, versioned rules, reproducible transactions |
| Inference | Delegated decisions and tie-breakers | Bounded choices with scoped observations, validation, deterministic fallback, and recorded results |
| Uncertainty | Minimize dice while capturing well-understood vagaries of war | Causal friction and hidden conditions first; documented residual chance only where needed |
| Combat | Synchronous, two or more sides eventually | Shared decision boundaries; simultaneous adjudication inside each window |
| Map | Grid, probably hexagonal, terrain and weather | Hex cells with physical units; map outline independent of tile shape |
| Players | Single/multiplayer; player or system controls units/groups | Separate side, player, commander, and unit identities from the beginning |
| Historical range | Civil War skirmishes through D-day; arbitrary comparisons | Capability-based content packs; unsupported capabilities remain explicit rather than being invented |
| Domains | Land and sea | Shared clock/orders/events, separate movement and damage mechanics |
| Civilians | Local population, no politics | Presence, shelter, movement, needs, infrastructure, and casualties |
| Campaign | Scalable beyond battles | Persistent force condition and operational movement later |
| Provisioning | Later | Fixed scenario inventory now; acquisition/economy/setup workflows deferred |
| Execution | Test everything on Evo before deployment | Self-contained local runs and evidence bundles; machine feasibility still to verify |

“Civil War” is provisionally interpreted as the American Civil War because of the contrast with D-day. This can be changed without changing the core model. “Comparing based” is ambiguous; these notes support scenario comparisons and campaign progression, and do not treat the phrase as approval for a specific campaign structure.

## First duel: a deliberately limited experiment

**Fixture P0: crossroads skirmish.** Two equal, illustrative 30-person rifle-musket detachments, on a small hex map containing open ground, a low ridge, a wood, and a road objective. The count is a synthetic test size, not a claim about an official historical platoon establishment. Initial ammunition is declared by the fixture. No resupply generation or force buying.

Start with a symmetric meeting engagement and identical baseline controllers to test fairness. Then use an asymmetric attack/delay variant: one side must reach and hold the road objective; the other must delay until the deadline while retaining an exit route. Objective rules and time limit are declared before the run, not improvised by a model.

Even in this one-unit duel, separate the superior's mission from the subordinate's execution choices. The test fixture can supply each side's top-level intent while an agent commander selects and revises legal local orders. Test different intent/risk limits against the same conditions, and changed conditions under the same intent; a fixed script that merely exchanges fire does not demonstrate the intended gameplay.

Tentative experiment settings: 25 m adjacent hex-center distance, approximately 24 by 20 axial cells, 30-second command windows, and 1-second simulation ticks. An axial parallelogram is not a rectangle in world coordinates. These values are tunable hypotheses; see [scale experiments](07-validation-and-evo.md). A roughly half-kilometer map may fit this fixture, not every platoon engagement.

Supported intent vocabulary: hold, move, observe, engage an identified contact, suppress a location, withdraw, rally, and offer surrender. Local reactions include taking cover, stopping at an impassable edge, and reacting to a newly observed threat according to the standing order. Suppression fire consumes ammunition without requiring an exact enemy entity ID.

Start with one spatial footprint per platoon and aggregate personnel cohorts by weapon/role and relevant proficiency. This cannot yet represent separate squad flanking or detailed building clearance. Later subelements remain aggregate groups; individual soldier simulation and personal progression are outside the design. See [unit lifecycle](12-unit-lifecycle-and-training.md).

## What makes the duel worth playing

- The objective creates a reason to move; it prevents two defensive agents waiting forever.
- Fire can suppress without incapacitating, creating windows for movement.
- Ammunition and fatigue turn repeated actions into commitments.
- Concealment and stale contacts make observation valuable.
- Withdrawal and surrender allow endings before annihilation.
- After-action evidence connects the result to decisions and conditions.

A model that produces colorful orders but no better or more interesting decisions than a simple policy has not earned its cost. Agent evaluation must measure both behavior and expense.

## Realism versus playability

Aim for plausible mechanisms and distributions within a declared scope. Do not aim for a single formula that predicts any battle in history. Technical weapon specifications, effective battlefield output, and command behavior are different evidence categories.

Cross-era contests are counterfactual experiments. Equal personnel is not equal combat power. Offer explicit comparison settings later: equal headcount, equal mission, historically plausible force, or designer-handicapped match. Do not silently change damage or morale to force a 50/50 result.

No universal scalar called `strength` should drive resolution. Summaries may display combat power, but it must be derived for a specified target, range, posture, and situation, and must not replace the underlying capabilities.

## Scale growth

The first scalable choice is clean interfaces and conservation, not implementing the whole campaign now. Grow through: duel → a few platoons and a subordinate commander → naval duel → amphibious micro-scenario → multiple sectors and persistent operations. A D-day beach sector is an earlier goal than all of D-day. The latter also needs air support, naval fire, landing capacity, communications, and logistics; the historical context supports treating it as a coupled operation. [S22](09-sources.md#s22)
