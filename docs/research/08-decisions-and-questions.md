# Requirements, proposals, and unresolved choices

As of 2026-11-04. This is a design ledger, not an implementation task queue or an authorization to execute work.

## Confirmed requirements from the user

- Name: **battle**; eventual web application with single-player and multiplayer play.
- All units in combat are autonomous, including player-owned units. Players direct commanders through orders rather than manual combat control. Maps and dispatches are the primary information channels; communication both to and from battle is constrained by the force's period technology. See [autonomous command](04-command-and-agents.md#autonomous-units-and-dispatch-based-command).
- The player receives a command map. Its [proposed interaction](02-design-brief.md#the-command-map) supports strategy and commander orders through authorized observations; this does not change the headless-first scope.
- The player's primary job is choosing battle strategy, assisted by a virtual twin. The player may also order unit commanders directly when logistically possible. Subordinate agents adapt tactical execution to battlefield conditions; training, remixing and campaign management support this loop.
- Log events and outcomes from the first headless duel, supporting tactical review, agent evaluation, debugging and reproducible replay. Capture both intermediate mission outcomes and final battle results.
- Historically inspired, roughly platoon-sized groups with explicit capabilities/state and agentic control.
- Synchronous battles; terrain/weather grid, likely hexagonal.
- Grid overlays on actual maps, with terrain reading. [Proposed map preparation](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation) ties the grid to physical scale and distinguishes source maps, validated terrain and commander knowledge; tools and implementation remain unselected.
- Fog of war: the simulation knows complete modeled state; player and commander knowledge is limited. Players choose how to use scouts and spies and factor their intelligence into strategy. See [proposed intelligence mechanics](03-simulation-methods.md#fog-of-war-scouts-and-spies).
- Terrain and weather are set ahead of time. Weather may have realistic randomization; seasonal effects are included. Location-specific profiles, evolution and validation are proposed in [environment setup](06-domains-and-campaigns.md#terrain-weather-and-seasons).
- Supply, morale, skill, and local population matter; no politics.
- Player is the general; subordinate agents can command groups; mutiny is possible.
- Two or more sides, with people or system controllers commanding one or more units.
- Start headless with one unit versus one unit; agent commanders can run both sides for testing.
- Long-term land and sea scope, from a Civil War skirmish to D-day-scale operations and campaigns.
- WWII is the technology and communications ceiling. Players receive battle-management tools available to generals by that time. Proposed scenario-specific availability and a 1945 outer content cutoff are detailed in [period command tools](14-period-command-tools.md); earlier forces do not automatically receive WWII equipment.
- Battle provisioning later.
- Include specialist units such as scouts, spies and quartermasters. [Research and proposed representation](13-specialist-units.md) distinguish field teams, attachments, abstract intelligence assets and transport; exact organization is not yet selected.
- Test on Evo before choosing a deployment model.
- Prototype with granular component tests for units, grid, agentic control, engagement algorithms, events and communications. [The test specification](15-component-prototype-tests.md) proposes independent fixtures and integration gates; no tests are implemented or executed yet.
- Current deliverable is research, README and AGENTS guidance; **no stack work yet**.
- Complexity is handled deterministically using a graph database. Inference is reserved for delegated decisions and tie-breakers; [the detailed contract](10-graph-and-inference.md) is proposed within that confirmed boundary.
- Minimize dice rolling while representing well-understood vagaries of war. Prefer causal friction and hidden conditions; stochastic exceptions need justification. See [friction and uncertainty](11-friction-and-uncertainty.md).
- Units are temporary aggregate formations. Commanders can choose to train or remix them; this is not an individual combat game. Persistent soldier identities and long-lived unit-character progression are outside scope. See [unit lifecycle](12-unit-lifecycle-and-training.md).

## Provisional recommendations

| ID | Proposal | Reason | Alternative / revisit trigger |
| --- | --- | --- | --- |
| P01 | WEGO command windows with fixed simulation ticks | Fair synchronous decisions and replayable consequences | Adjust windows if playtests feel unresponsive |
| P02 | Versioned graph state, deterministic effect rules and causal friction | Minimal dice with explicit, replayable dependencies | Add only evidence-backed residual stochastic mechanisms |
| P03 | Inference chooses delegated orders or permitted tie selections; kernel resolves effects | Implements the confirmed inference boundary | Candidate/tie policy requires explicit rules |
| P04 | Temporary formation composed of aggregate role/proficiency cohorts | Training and remixing without individual soldier simulation | Add aggregate subelements only when maneuver detail requires it |
| P05 | Axial hex terrain with metric scale and progress | Clear neighborhood geometry; simple first implementation | Naval heading/continuous-position experiment later |
| P06 | Separate side, controller, commander, unit, and contact | Supports more than two sides and hierarchy without hidden knowledge leaks | Do not collapse these solely to simplify P0 |
| P07 | Resolved event batches plus snapshots and accepted orders | Playback, debugging, recovery and counterfactual comparison | Storage product remains open |
| P08 | Scripted policies before/alongside moderate models | Establish baseline and isolate agent value | Model/provider selected through Evo evaluation |
| P09 | Scenario objectives plus result vectors | Allows delay, withdrawal and partial success | Numeric scoring stays scenario-specific |
| P10 | Distinct naval domain connected through shared contracts | Movement/damage differ from land | Choose first naval era after land results |
| P11 | Rule-based civilian groups | Physical consequences without political simulation or excessive calls | Add detail only when decisions require it |
| P12 | Mutiny extension after core condition model | Persistent authority rejection needs more than a morale roll | Research mechanisms before setting rates |

## Working assumptions used in this research

American Civil War for the first historical family; 30-person synthetic detachments for symmetric tests; 25 m adjacent-center spacing, 30-second command windows and 1-second ticks as experimental starting points. None is a historical claim, final design decision, or user-approved constant.

Initial duel supports movement, observation, fire/suppression, rally, withdrawal, rout and surrender. Detailed melee, multiple subelements, civilians, resupply, and mutiny are separate test extensions. Their inclusion in the long-term design does not mean the first duel must implement them all.

## Questions to resolve before the relevant build stage

1. Does “comparing based” mean campaign-based, comparison-based, or both? Both directions are preserved here.
2. Is the American Civil War the intended first era, and should the first historical fixture use a named unit or generic documented detachment?
3. Does “everything on Evo” require local model inference, or is a local simulator with remote model calls acceptable? What is Evo's actual resource budget?
4. What initial channel delays, capacities and reporting policy should the first fixture use? Period-limited two-way communications, autonomous execution, and map/dispatch feedback are already required; instantaneous direct control is not an open option.
5. Should cross-era encounters prioritize historical constraints or an optional competitive handicap system? Default proposal: preserve constraints and expose asymmetry.
6. Which naval era comes first: sail, Civil War steam/ironclads, or WWII? Each changes the minimal damage/movement experiment.
7. What should multiplayer deadlines feel like: untimed local planning, short live windows, or asynchronous submission with simultaneous adjudication? The simulation supports separation of wall-clock and simulation time.
8. Which campaign persistence matters first: surviving personnel/condition, ammunition and supply routes, or operational maneuver? Procurement remains deferred.
9. Which residual uncertainties demonstrably require sampling after causal state and information limits are modeled? The direction is settled: minimize dice. Exact exceptions, evidence and thresholds remain design work; there is no blanket approval for stochastic combat.

None of these prevented the requested research. They should not be silently answered by picking a framework or provisioning a machine.

## Deliberately deferred

Programming language, frontend, server/runtime, graph database product/query language, model vendor, cloud provider, authentication, deployment, network transport, paid services, force-builder UI, procurement economy, procedural historical armies, full world maps, and distributed simulation. The graph database architectural category is confirmed. Individual soldier simulation and personal progression are excluded, not deferred features. Training/remix choices are in the design scope; their implementation remains beyond the initial duel.

The [component behavioral specification](15-component-prototype-tests.md) now supplies initial acceptance fixtures. Before implementation, pin the smallest action/effect rules and fixture parameters needed for the first composition slice; subsequent component and battle gates expand from that evidence. No web stack has been selected.
