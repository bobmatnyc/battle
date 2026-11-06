# Original project brief — research phase, 2026-11-04

A proposed single-player and multiplayer battle-command game: players choose battle strategy with assistance from a virtual twin, while agent commanders execute and adapt orders under battlefield conditions. Players may also give orders directly to unit commanders when command and communication logistics permit.

**Status: research and game design only — 2026-11-04.** No application, stack, dependencies, deployment configuration, or runnable simulator exists yet. Recommendations below are proposals, not approved implementation specifications.

## The idea

**Command model:** all units in combat operate autonomously within their missions and standing orders. The player primarily receives information through a command map and dispatches. Orders to the battlefield and reports back use only the communications available to the force at that time, within the WWII ceiling. Direct orders change a commander's instructions when received; they do not put the unit into manual control. Units continue acting when communication is delayed or lost.

The central play loop is **assess with the virtual twin → choose battle strategy → issue or delegate orders → let commanders act → review reports → revise strategy**. Players choose objectives, timing, priorities and limits; their twin helps evaluate options and prepare orders. Execution authority for the twin is explicitly delegated. Unit commanders make local tactical decisions from what they can observe. Direct player orders use feasible communication channels and take effect on valid delivery, not instantaneously. The deterministic simulation resolves actions. Training, remixing and campaign management support this battle-focused game and remain secondary.

Each player or system commander controls one or more units, initially roughly platoon-sized. A unit has explicit personnel, equipment, training, morale, cohesion, fatigue, and supply state. An agent interprets orders and chooses actions; simulation rules determine what can happen and resolve the consequences. The player's authority is constrained by communications, subordinate judgment, and the troops' condition, including possible refusal or mutiny.

Units are temporary aggregate formations, not long-lived characters or collections of individually simulated soldiers. Commanders can choose to train or remix formations. Personnel quantities, equipment, proficiency and condition carry through those changes; the same unit identity need not persist across a campaign. Exact training and reorganization rules remain design work.

Battles use simultaneous orders and resolution, with terrain and weather represented on a spatial map, initially hexagonal. There can eventually be two or more sides, multiple players on a side, and subordinate commanders controlling formations. Land, sea, and amphibious operations belong in the long-term design. Civilian populations matter through their physical presence, movement, needs, and losses; political simulation is outside scope.

The ambition spans a Civil War skirmish to D-day. This requires multiple scales and domain-specific rules, not simply more soldiers on the first map. Historical and cross-era encounters should use explicit capability data and expose uncertainty; they should not imply every matchup is balanced or historically verifiable.

**WWII is the technology and communications ceiling.** Players use a digital command desk representing period maps, reports, orders, schedules and staff support. Available channels and equipment depend on the scenario's era, force and command level. The twin assists with those tools and observations; it grants no modern battlefield information network. See [period command tools](14-period-command-tools.md).

Terrain, season and initial weather are set before battle. Optional weather variation must be realistic for the place and season, evolve coherently, and remain reproducible. Seasonal conditions affect the battlefield through explicit environmental state, not a blanket seasonal combat bonus. See [environment setup](06-domains-and-campaigns.md#terrain-weather-and-seasons).

The command map supports grids over actual maps, with terrain interpreted into validated simulation data. Source maps, terrain truth and commander knowledge remain distinct. Hex scale is tied to real distance, and historical terrain must match the scenario date. See [real maps and terrain interpretation](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation).

## First playable experiment

Build confidence component by component: **units → grid → autonomous control → engagements**, with **events and period communications** tested throughout. Join them in small headless scenarios before the full duel. Exact rule tests, live-agent evaluations and historical calibration remain separate. The [component prototype specification](15-component-prototype-tests.md) defines contracts, granular fixtures and integration gates; these tests have not been implemented or run.

**Fog of war is required.** The simulation knows the complete modeled state; players, their twins and all competing commanders know only their authorized observations and delivered intelligence. Players choose whether and how to use scouts and spies, and how much to trust their reports. Intelligence gathering consumes time and available capacity; it does not reveal the whole map. See [fog of war and intelligence](03-simulation-methods.md#fog-of-war-scouts-and-spies).

The player receives a **command map** for assessing the battle, working with the virtual twin, and issuing intent to commanders. Proposed layers show known terrain and conditions, reported friendly positions, enemy contacts, objectives and order status. It is an information-limited command view, with report timestamps and uncertainty. See [command-map design](02-design-brief.md#the-command-map). The first prototype remains headless; its observation and order contracts will support the map later.

One platoon-sized unit against one platoon-sized unit on a small land map, headless, with agent commanders on both sides. Begin with a symmetric, historically inspired rifle-musket skirmish fixture, then vary one factor at a time. An objective, a deadline, ammunition limits, concealment, suppression, and withdrawal should make this more interesting than exchanging damage until one unit disappears.

The proposed foundation is:

- A graph database representing authoritative entities, relationships, and state, with deterministic rules handling simulation complexity. This architectural direction is confirmed; the database product remains open.
- Simultaneous planning, followed by fixed simulation steps.
- Deterministic resolution by default, minimizing dice rolls. Model the vagaries of war through explicit conditions, limited information, delays and persistent failures; reserve seeded chance for justified residual uncertainty.
- Inference only for delegated decisions and explicitly permitted tie-breakers among legal alternatives. All selections are validated and recorded.
- Structured orders and limited observations shared by human, scripted, and language-model controllers.
- Required structured event and outcome logging from the first duel: orders, agent decisions, battlefield effects, mission results and final battle outcomes, linked for replay and tactical review.
- A local testing path on **Evo** before selecting a deployment model. Evo's capabilities have not been inspected.

Initial ammunition and fatigue belong in the duel. Army purchasing, force assembly, reinforcement procurement, and battle provisioning come later. Fixed research fixtures are enough to start.

## Read next

Specialist units include scouts, spies and quartermasters. The proposed model supports field teams, attached support teams and abstract intelligence cells under a shared mission contract. Quartermasters coordinate existing stock and transport; procurement remains deferred. See the [six-game specialist comparison](13-specialist-units.md).

Start with the [research overview](README.md), then the [game survey](01-game-survey.md) and [recommended design](02-design-brief.md).

| Research document | Purpose |
| --- | --- |
| [Game survey](01-game-survey.md) | Digital/online and tabletop precedents; what to borrow and avoid |
| [Design brief](02-design-brief.md) | Player experience, scale, scope, and first duel |
| [Simulation methods](03-simulation-methods.md) | Time, hexes, movement, sensing, combat, morale, and randomness |
| [Command and agents](04-command-and-agents.md) | General/subordinate authority, model boundaries, multiplayer, and failure handling |
| [State, events, outcomes](05-state-events-outcomes.md) | Conceptual records, resolution transactions, replay, and result accounting |
| [Land, sea, civilians, campaigns](06-domains-and-campaigns.md) | Expansion without forcing every domain into infantry rules |
| [Headless validation and Evo](07-validation-and-evo.md) | Experiments, acceptance gates, reproducibility, and local evaluation |
| [Decisions and open questions](08-decisions-and-questions.md) | User requirements versus provisional choices and deferred work |
| [Sources and evidence limits](09-sources.md) | Versioned reading list, claim pointers, and unavailable sources |
| [Graph and inference boundary](10-graph-and-inference.md) | Confirmed graph-database direction, deterministic resolution, and bounded tie-breakers |
| [Friction and uncertainty](11-friction-and-uncertainty.md) | Minimal dice, causal battlefield friction, persistent uncertainty and validation |
| [Unit lifecycle and training](12-unit-lifecycle-and-training.md) | Temporary formations, aggregate training, remixing, and conserved force state |
| [Specialist units](13-specialist-units.md) | Scouts, spies and quartermasters across six games; proposed roles, command contracts and test progression |
| [Period command tools](14-period-command-tools.md) | WWII technology ceiling, command desk, equipment availability and period communications |
| [Component prototype tests](15-component-prototype-tests.md) | Six component contracts, granular acceptance fixtures, integration slices and Evo evidence |

See [AGENTS.md](../../AGENTS.md) for project working rules. There are no build or test commands yet.
