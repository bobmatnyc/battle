# Component-first headless prototype

**Confirmed direction:** prototype through granular component tests, particularly units, grid, agentic control, engagement algorithms, events and communications. This document specifies the proposed contracts, fixtures and progression. It contains no implementation, stack selection or executed-test claim. Synthetic numbers below are test inputs, not historical coefficients.

## Boundaries before the duel

Each component needs a small versioned input/output contract, fixtures with independently specified expected behavior, and a headless way to run those fixtures. Keep rule functions independent of model calls and rendering. The graph remains authoritative; pure calculations consume a pinned snapshot and propose effects for validation and atomic commit. A test double may supply snapshots but cannot establish that the eventual graph adapter meets persistence/recovery requirements.

| Layer | Inputs | Outputs / responsibility |
| --- | --- | --- |
| Unit | Archetype, aggregate personnel/equipment/condition, validated effects | Legal capabilities and proposed state transitions; resource and lifecycle invariants |
| Grid | World coordinates, cells/edges, terrain/environment revision, movement/sensor profile | Distances, connectivity, trajectories, exposure and geometric visibility; no policy choices |
| Agentic control | Authorized observation, delivered mission, permissions, controller context, decision budget | Proposed intent/action, brief rationale or fallback; no direct state mutation |
| Engagement | Eligible actions, exposure/trajectory evidence, weapon/resource/condition snapshot | Simultaneous proposed expenditures, suppression, casualties and condition effects |
| Events | Validated effect batch, expected graph version, resolved decisions | Atomic committed state/history, replay, snapshots and outcome projections |
| Communications | Messages, period capabilities, endpoints, queues, simulation time | Scheduled delivery/relay/receipt/failure and recipient knowledge updates |

Two cross-cutting seams need explicit tests: **observation filtering** between world state and controllers, and **simulation scheduling** across component phases. Geometry can establish physical visibility; it cannot automatically publish knowledge to headquarters. Message receipt is not order execution, and a proposed engagement is not a committed effect.

## Granular acceptance fixtures

Start with these examples, then add cases when a rule or failure requires them. Test behavior and invariants rather than implementation shape or arbitrary code-coverage percentages.

### Unit layer

| ID | Fixture | Required result |
| --- | --- | --- |
| U01 | 30 fit personnel; a valid effect transfers 3 to wounded-present and 2 to killed | Fit 25, wounded-present 3, killed 2; total 30; no negative or duplicated accounts |
| U02 | Zero ammunition, or insufficient qualified crew | Fire capability unavailable; a proposed unsupported shot is rejected without expenditure or damage |
| U03 | Suppression rises without casualties, then valid recovery | Personnel unchanged; suppression transitions according to the declared rule; no automatic restoration of unrelated morale/fatigue |
| U04 | An order targets a retired formation | Explicit rejection; no silent reassignment. Later split/merge fixtures conserve personnel, equipment and active tasks |

### Grid and terrain layer

| ID | Fixture | Required result |
| --- | --- | --- |
| G01 | Axial origin and its six neighbors | Each neighbor is distance 1; reverse distances agree; origin distance is 0 |
| G02 | Two open cells, then the same pair separated by a blocking edge | Movement/visibility follow their separate profiles; removing the edge invalidates the relevant cached result |
| G03 | Two routes with authored costs; one crossing is blocked | Returned path is connected, legal and minimal for the declared cost; an isolated destination returns unreachable |
| G04 | Same world/grid with different display zoom and image resolution | Identical metric positions, routes and engagement inputs; coordinate round trips respect declared precision |
| G05 | Mirrored unobstructed or obstructed sightlines under symmetric sensor assumptions | Symmetric geometric results; edge-touch behavior follows the specified convention |

### Agentic control layer

| ID | Fixture | Required result |
| --- | --- | --- |
| A01 | A fake controller returns a legal order, then an order beyond its authority | First validates; second is rejected with the declared fallback; neither directly edits the graph |
| A02 | Standing hold mission; communications remain silent | Unit keeps observing and executing authorized local behavior; no fresh human instruction required |
| A03 | Blocked route with one permitted alternative, then no permitted alternative | Controller contract accepts bounded adaptation; otherwise use fallback and send a request without expanding authority |
| A04 | Malformed response, timeout, stale observation or late completion | Bounded repair/fallback; late output cannot overwrite a newer accepted decision or obtain a fresher view |
| A05 | Two worlds differing only in hidden enemy facts | Identical observation payloads and available-action descriptions for that observer; no hidden IDs in requests |

Use fake and scripted controllers for exact contract assertions. Live model evaluations separately measure legal-order rate, mission compliance, useful adaptation, costs and latency. Do not require exact wording or one preferred route when several plans are valid. Exact replay consumes recorded accepted decisions; repeated fresh inference is a new trial and need not match.

### Engagement layer

| ID | Fixture | Required result |
| --- | --- | --- |
| E01 | Both eligible sides fire from one frozen start state | Both actions contribute before the shared commit; reversing entity/action enumeration gives equivalent results |
| E02 | A unit was already incapacitated before the start state | It cannot contribute a shot; distinguish this from simultaneous incapacitation in E01 |
| E03 | Synthetic exposure accumulator below, exactly at and above a declared effect threshold | Exact boundary behavior follows the rule; residual exposure is retained; personnel losses remain bounded |
| E04 | Same scripted fire and exposure except cover | The declared exposure rule changes only its supported effects; no duplicate cover discount or unexplained outcome change |
| E05 | No rounds, incompatible target or invalid range | No valid fire effect; inventory and target state remain unchanged |
| E06 | Identical actions split into smaller time intervals | Accumulation agrees where the model promises invariance; report numerical convergence separately where it does not |

These tests verify a chosen formula; they do not select or historically validate it. Combat algorithm candidates use common inputs and metrics. Record the rule version, expected qualitative relationships and any uncertainty before tuning against historical evidence.

### Events and outcomes layer

| ID | Fixture | Required result |
| --- | --- | --- |
| V01 | Commit a valid batch, then retry its identity | Apply once; graph and history reconcile; duplicate retry creates no extra loss or expenditure |
| V02 | Stale expected version or invalid aggregate deltas | Reject the whole batch; no partially changed state or misleading success event |
| V03 | Inject interruption around persistence boundaries | Recovery produces one valid committed prefix; graph state cannot outrun its durable event history |
| V04 | Snapshot plus subsequent events versus uninterrupted execution | Same canonical state and outcome; deterministic re-simulation also matches under the pinned numeric/runtime contract |
| V05 | Hidden event, received report and final objective evaluation | Observer journal contains only authorized information; objective totals derive from committed evidence; technical abort is distinct from defeat |

A memory-only event test does not satisfy V03. Repeat adapter contract and recovery fixtures against the chosen graph database when implementation reaches that stage.

### Communications layer

| ID | Fixture | Required result |
| --- | --- | --- |
| C01 | Message sent at t=0, configured transit 3 s and processing 2 s | Recipient receives at the specified t=5 phase, never earlier; delay values are synthetic |
| C02 | Local contact at t=1, report sent at t=2, delivered at t=7 | Local unit can react from its observation; general/map learns the contact only at t=7 absent another authorized source |
| C03 | One message in service and another queued under a bounded channel | Defined priority/FIFO policy and capacity hold; model response speed cannot alter simulated message order |
| C04 | Unavailable or incompatible endpoint; broken channel | No delivery; sender learns failure only through declared evidence/timeout rules, not hidden graph inspection |
| C05 | Order delivered, acknowledgment delayed; older order arrives afterward | Local execution need not await the general receiving acknowledgment; the older order cannot undo the accepted newer order |
| C06 | Late old report after fresher evidence; cancellation crossing an in-flight order | Preserve provenance and freshness; cancellation acts only under its own delivery/precedence rules, with no retroactive erasure |

## Composition tests before a full battle

| Slice | Components joined | Decisive evidence |
| --- | --- | --- |
| I01: dispatch and autonomous movement | Grid, unit, scripted controller, comms, events | General sends move intent; unit begins on receipt, reaches the legal destination and reports later; map remains appropriately stale |
| I02: contact and simultaneous exchange | Observation filtering plus all six layers | Two fixed scripted units detect locally, exchange eligible fire and commit conserved effects; headquarters gets delayed reports |
| I03: isolation and revised orders | All six, explicit route/channel interruption | Units continue bounded behavior during silence; a delivered revision changes intent; expired/late instructions cannot undo it |
| I04: twin and general | Same contracts with advisory/delegated twin role | Advice alone has no command effect; authorized orders travel normally; no extra source of battlefield truth |

Start with tiny synthetic maps and invented coefficients explicitly marked as such. Retain the first duel as two combat units; specialist, real-map, naval and campaign cases extend the same component suites later. Do not require every future mechanic before integrating I01.

## Build and evidence sequence

When implementation is authorized: define contracts and a virtual clock; implement minimal unit/grid rules and a memory event reducer; add comms, observations and scripted autonomous control; add the smallest engagement resolver; verify real graph commit/recovery; run the composition slices; then run scripted-versus-scripted, model-versus-scripted and model-versus-model duels. State/event contracts apply from the first slice even before durable storage is chosen.

Use exact expected results for arithmetic/time fixtures, independently calculated tiny examples for geometry, and invariant/metamorphic tests for conservation, side swaps, reordered input and hidden-state separation. Fault injection is intentional test input, not an added random gameplay mechanic. No live model, UI, network sleep or external map service should be needed for deterministic component tests.

Each failure artifact records test/fixture ID, rules/content versions, initial snapshot/hash, expected versus actual behavior, accepted decisions, simulated timeline and first divergence. Each run distinguishes implemented, passed locally, passed on Evo, calibrated and still unsupported. Live-model suites add configuration, usage, latency and predetermined acceptance criteria; contract violations cannot be excused by win rate.

Evo must eventually run the component suites, graph-adapter checks, composition slices and agent duels, with replay artifacts. Verify Evo access/resources and the local-versus-remote model mode at build time. No deployment choice follows until those local results exist. The broader [validation plan](07-validation-and-evo.md) still governs historical credibility and play quality.
