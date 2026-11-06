# Deterministic graph simulation and bounded inference

## Confirmed direction

The user's clarification: complexity should be handled deterministically using a graph database; inference should be for delegated decisions and tie-breakers.

This confirms an architectural category, not a database product or permission to implement. The contracts below are design proposals interpreting that requirement. No graph software has been selected, installed, or tested. This document records a user decision and original design work; it adds no externally sourced research claims.

## Responsibility boundary

| Responsibility | Proposed owner |
| --- | --- |
| Canonical entities, properties and relationships | Graph database |
| Authority, reachability, resource availability, constraints and eligibility | Deterministic queries/rules over a specified graph version |
| Movement, detection, combat, condition changes and objectives | Versioned deterministic simulation rules |
| Following a valid standing order | Deterministic unit executor |
| Choosing how to fulfill a delegated mission | Scoped commander inference when a decision is due |
| Choosing among alternatives that a declared policy leaves tied | Scoped inference, or deterministic fallback |
| Applying decisions and effects | Validated simulation transaction |
| Replay, result accounting and reports | Saved events/decisions and deterministic projections |

A graph database represents and queries complexity. Determinism also requires defined rule ordering, arithmetic, snapshot boundaries, conflict handling and commits; it is not an automatic property of choosing graph storage. Logical rule evaluation is deterministic computation, distinct from language-model inference.

## Proposed graph vocabulary

Nodes include battle, scenario, side, player, commander, unit, personnel cohort, equipment, ammunition stock, terrain cell, terrain edge, objective, observation/contact, order, decision request and resolved event. Later add vessel systems, transports, civilian groups, supply locations and campaign transitions.

Units are temporary formation instances; personnel cohorts are aggregate counts, not individual people. Add force pools, training orders and formation transitions for the later lifecycle model. Allocation/provenance edges record quantities transferred between pools and formations, while controller-assignment edges have explicit effective periods. An archived unit node supports replay without implying a long-lived unit character. See [unit lifecycle](12-unit-lifecycle-and-training.md).

Relationships can include:

| Relationship | Meaning / important constraint |
| --- | --- |
| `COMMANDS`, `DELEGATES_TO` | Effective authority and permitted scope; no command cycles |
| `ASSISTS`, `ACTS_FOR` | Twin/player relationship and represented authority; assistance alone grants no execution permission |
| `CAN_COMMUNICATE_VIA` | Candidate command/report channel with range, route, capacity, timing and disruption rules; independent of command authority |
| `BELONGS_TO`, `HOSTILE_TO` | Side membership and fixed scenario relationships; distinct from command authority |
| `LOCATED_AT`, `ADJACENT_TO`, `CONNECTS` | Spatial presence, terrain adjacency and crossing structure |
| `EQUIPPED_WITH`, `CONSUMES`, `REQUIRES_CREW` | Capabilities and resource dependencies |
| `OBSERVED_BY`, `REPORTS_TO` | Knowledge provenance and delivery; does not expose hidden unit state |
| `ASSIGNED_TO`, `CONSTRAINED_BY` | Missions, objectives and order restrictions |
| `CARRIED_BY`, `SUPPLIED_BY` | Later transport/logistics relationships with capacity and timing |
| `CAUSED_BY`, `DERIVED_FROM`, `SUPERSEDES` | Audit and provenance relationships |

Names are illustrative. Represent physical quantities as typed properties with units; not every scalar needs a node. Relationships need battle/branch scope and effective time where applicable. Graph presence alone does not establish eligibility: a supply link may exist while a bridge is unusable or transport capacity is exhausted.

Strategy intents and scoped delegation grants connect the player, twin and commanders. Direct command requires both valid authority and a feasible delivery mechanism. Deterministic rules resolve order versions, override scopes and delivery events; inference may propose a strategy or order but cannot create a communication path, grant itself authority or choose which conflicting order counts as valid.

Authoritative truth and observer knowledge remain separate. An observation node exposed to an agent must not expose traversable links into hidden enemy state. Models receive a materialized authorized view, not arbitrary graph query access. Provenance needed for diagnostics can remain privileged.

## Deterministic tick contract

1. Pin the committed graph version and rule version at the tick boundary.
2. Derive eligible actions, dependencies and rule consequences using defined phases. Order query results explicitly wherever sequence affects calculation; canonicalize graph serialization for hashes.
3. Compute simultaneous effects from the same eligible snapshot, using working projections where useful. No model resolves distance, line of sight, inventory, casualties or objective arithmetic.
4. Validate all graph mutations and conservation constraints together.
5. Commit the next graph version and its resolved event batch at one logical boundary. Reject a stale expected version rather than silently applying a late result.
6. Publish authorized observations and deterministic reports from that committed version.

Derived arrays, spatial indexes and caches may accelerate computation but cannot become independently writable sources of truth. Bound graph traversals, define cycle handling, and invalidate derived facts when dependencies change. Future graph product evaluation must prove snapshot/transaction and recovery requirements; no particular transaction mechanism is assumed yet.

## Delegated decisions

Inference receives a mission, authority scope, observation version, legal action space, constraints, deadline and decision budget. It may propose an intent within that scope. The deterministic layer validates and executes it. Continuing an unchanged order or calculating consequences does not require a model call.

Example: the general delegates “hold the crossing while preserving the platoon.” Rules compute reachable positions, available ammunition and known contact constraints. The platoon commander chooses a legal position and engagement policy. Movement, firing, suppression and objective progress follow the rules.

Model-generated narrative outside a delegated decision is not part of the current inference budget. After-action reports can use deterministic templates; any future narrative-model feature needs a separate scope decision.

## Tie-breaker contract

“Tie” must be defined by a versioned rule, not by a model claiming uncertainty. Examples include two legal routes with equal declared utility, or equal-priority friendly units competing for a crossing slot. A near-tie tolerance, if used, must be explicit in the rules.

Create a `DecisionRequest` containing:

- Request ID, battle/tick/window and graph/observation version.
- Decision owner and delegated authority; one owner or a declared joint arbitration policy.
- Triggering rule and tie criterion.
- Engine-generated candidate IDs, with legal consequences/constraints and authorized supporting evidence.
- Deadline, cost limit, and deterministic fallback policy.

The model returns one candidate ID and an optional brief rationale. It cannot add candidates, change scores, alter constraints or write graph state. Revalidate the response against the recorded candidate set and version; reject stale/invalid output and record the fallback. Do not silently retry with a later battlefield view.

For friendly crossing contention, a common commander can choose among equally eligible schedules. Without a common authority or an authorized arbitration policy, deterministic conflict rules apply. Hostile movement collisions, damage calculation and tied victory scores remain scenario rules by default. This is a proposed scope for “tie-breakers,” not an assumption that every equality should trigger inference.

Retain the full decision request, authorized evidence, selected candidate, model/configuration reference, validation result, and fallback reason. Once accepted, the selection is an explicit simulation input. Replay consumes it without querying a model. A missing historical selection is a replay error, not permission to generate a replacement silently.

## Minimal randomness and causal friction

The user further specified minimizing dice while accounting for well-understood vagaries of war. The preferred design now uses explicit causal state, imperfect information, delays and deterministic accumulation. The earlier broad stochastic formulas remain research comparators. A narrowly justified residual event may use reproducible sampling; inference cannot act as a random-number generator. See [friction and uncertainty](11-friction-and-uncertainty.md) for evidence requirements and persistent event handling.

Either way, the reproducibility contract includes initial graph state, versions, accepted orders, and recorded tie selections. Graph evaluation or database traversal order must never serve as accidental randomness.

## Required validation when building

Equivalent graph facts inserted in different orders must resolve identically. Changing query plans or worker schedules must not decide a battle. State and events must recover together after interruption. An invalid model selection cannot mutate the graph. Standing-order and replay runs must work with inference disabled. Every model call must reference a delegated decision or declared tie request. These checks extend the [Evo validation plan](07-validation-and-evo.md).
