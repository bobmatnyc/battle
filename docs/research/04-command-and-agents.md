# Command, agents, and synchronous multiplayer

Proposed contracts, not a selected model provider or software framework.

**Confirmed inference boundary:** model calls serve delegated decisions and explicitly declared tie-breakers. Deterministic graph queries and rules handle eligibility, constraints, relationship propagation, and adjudication. A difficult query or missing rule is not permission to ask a model to improvise the result. See [graph and inference boundary](10-graph-and-inference.md).

## Command roles and resolution

1. **General/player:** chooses battle strategy, objectives, priorities and risk limits; may directly order reachable unit commanders.
2. **Virtual twin:** assists the player with strategic decisions and proposed orders; issues/coordinates orders only within explicit delegation. It is an assistant to the general, not an independent competing superior.
3. **Formation commander:** later decomposes missions among subordinate groups, within delegated authority.
4. **Unit commander/controller:** interprets its mission using local observations and issues executable unit orders.
5. **Simulation:** validates authority, delivery and capabilities; resolves movement, sensing, combat and condition changes. It is not a commander.

For the first duel, a fixture or system general can supply the top-level mission while one agent commander per side chooses local execution orders. Preserve the distinction between intent and execution without requiring three model calls. An active formation retains a controller context between decisions, and its local executor follows its standing order and reaction policy. This context lasts for the assignment; it is not an enduring platoon character. On disbanding or remixing, retire/rebind controllers explicitly and transfer only authorized mission and observation context, never clone all predecessor memories into every successor.

Training and remixing are commander decisions. Inference may choose a legal training objective or reorganization plan within delegated authority; deterministic rules account for time, proficiency changes, composition, equipment and readiness. No model grants free experience or creates personnel. These later lifecycle actions do not expand the first duel's implementation scope.

## Virtual twin and direct command

**Confirmed requirements:** the player chooses battle strategy, has a virtual twin to assist, and can give orders directly to unit commanders when logistically possible. The following authority and delivery rules are proposals.

The twin maintains the player's current intent, priorities, declared risk preferences and delivered reports. It can compare battle plans, identify assumptions, propose orders, and surface decisions that need attention. Strategic advice is a delegated decision-support use of inference; it does not authorize model adjudication or an extra omniscient narrator. The twin sees only information available to the player's command role and must identify estimates as estimates. A saved strategy is not a guarantee that the world will follow it.

Distinguish **advice/drafting** from **delegated execution**. Advice produces recommendations for the player's selection. A delegation permits the twin to issue specified classes of orders to specified recipients within explicit constraints, duration and reporting requirements. Choosing a strategy need not entail approving every routine subordinate order, but the scope of autonomous execution must be clear. The player may change or revoke delegation through recorded commands.

Direct command skips an intermediate planning step; it does not skip message transport. Deterministic graph rules check command authority, available voice/signal/radio/courier links for the era, distance/path, channel capacity, transmission or travel time, disruption and recipient availability. These are candidate logistics factors, not yet calibrated rules. Issuing, delivering, acknowledging and executing an order are distinct states. An unreachable commander continues its existing mission/fallback until it receives a valid change.

The player interface should show known channel availability, estimated delay and acknowledgment state. It must not reveal an unseen destroyed bridge or disabled receiver merely because the authoritative graph knows it. A send may appear pending until failure or delivery is actually reported. A courier order and any cancellation both take their own delivery time; clicking cancel cannot erase a message already received.

### One effective command, multiple possible issuers

All orders identify the human/twin/subordinate issuer, the authority under which it acts, the parent strategy/mission, sequence/version, recipient and superseded scope. Proposed precedence: a valid direct player override supersedes delegated instructions for its stated scope when received and accepted at a simulation boundary. Older in-flight orders cannot later overwrite that accepted override. Twin authority for that scope is explicitly paused or revised so it does not silently undo the intervention; unrelated delegated work may continue.

Command precedence is decided by authority and version rules, never model response speed or database traversal order. Revoking the twin's authority blocks new submissions in that scope at the command source; already transmitted orders and their cancellations follow the declared delivery rules. Both the twin and player receive acknowledgments through their authorized view. This avoids treating authority changes as instantaneous changes to distant troops.

For the first headless duel, keep the twin as a replaceable decision-support role rather than a required extra call every tick. Fixture/system strategy selection can drive baseline tests. Add a focused twin-assisted planning case and direct-order delivery/override cases without changing combat physics. Exact twin personalization and autonomy controls remain design choices; the presence of a twin grants no hidden-state advantage.

## The tactical execution loop

### Autonomous units and dispatch-based command

**Confirmed requirement:** all units in combat are autonomous. Information reaches the player primarily through the command map and dispatches, and communication in both directions is limited to the technology available to the force at that time. This applies to human-owned and system-owned units alike. The following details are proposed contracts.

Every active combat unit starts with a mission or declared standing behavior, local observations, permitted discretion, reporting policy and fallback. It continues to observe, act and adapt between higher-command messages. Receiving a direct order changes that mission or its constraints after delivery and validation; it does not replace the unit commander with a player-controlled movement/fire loop. A commander requesting clarification continues the authorized fallback while awaiting a reply. Holding position can be a deliberate fallback, but the unit still observes and responds under its standing rules.

Autonomy does not require a fresh model call every tick. Deterministic executors handle routine actions; delegated decisions trigger bounded inference at shared checkpoints. A timeout follows the recorded fallback. Communication failure does not pause local simulation or expand authority. Autonomy remains limited by capability, condition, trust and mission scope; it does not guarantee obedience or success.

A **dispatch** is a player-facing record of an order, acknowledgment, situation report, intelligence report, request or outcome report. It can represent information delivered by courier, voice, signal, wire or radio; displaying it as text does not mean every era had identical message transport. Record sender, intended recipient, message type, mission/order references, priority, evidence/event time, dispatch time, receipt time and authorized content. Forwarding has its own delay and preserves provenance.

Proposed flow: local observation/event → commander report → feasible communication path → recipient processing → delivered dispatch → authorized map/status update. The return path for a new order is separately resolved. Acknowledgment may arrive after the subordinate has already begun executing; the map should distinguish reported execution from merely sent instructions. Missing reports leave stale markers and pending orders rather than exposing the cause of silence. The general's own direct observation can also update the view where scenario position and visibility permit it.

The dispatch inbox and map cross-reference one another: selecting a marker shows its supporting reports, and selecting a dispatch highlights its reported area or subject. Distinguish latest received from latest observed information, so a late old report cannot silently overwrite a newer observation. Contradictory accounts remain inspectable. The twin can prioritize delivered dispatches and propose a response from their evidence; it cannot read the authoritative event stream.

These contracts also support headless testing: fixture/system generals issue intent and consume dispatch records, while unit controllers act from their own observations. Live player views and after-action diagnostic truth remain separate. Full report templates and processing capacities are still design work.

**Confirmed gameplay:** the player chooses battle strategy with twin assistance and issues or delegates orders; receiving agent commanders deal with battlefield conditions. Direct player intervention is available when command logistics permit. The following interaction and authority rules are proposals implementing that priority.

1. **Assess and choose:** the player and twin use delivered reports to compare and choose a battle strategy, not ground truth.
2. **Order or delegate:** translate strategy into purpose, task/objective, priority, area, timing, risk/resource limits, permitted initiative, and reporting/fallback conditions. The player may issue orders directly over feasible channels; sensible defaults keep routine orders short.
3. **Interpret:** the agent acknowledges its understanding and selects a feasible local plan from its authorized view. It can report an infeasible order without pretending it executed it.
4. **Execute and adapt:** the agent issues local orders, observes results and revises its plan within authority. Deterministic executors handle routine movement, reloads, taking cover and other prescribed reactions between decisions.
5. **Report:** communicate progress, changed conditions, deviations and requests with timestamps and evidence. Receipt of a report can lag the underlying event.
6. **Revise:** the player continues, redirects, reinforces or cancels the mission through the same communication and precedence rules.

Agent judgment is used for genuine delegated tactical choices, even when deterministic scores are not tied. The simulation can determine that two routes are legal without deciding which better fulfills the commander's intent under uncertain information. Inference may make that choice; it cannot invent a route, capability or successful outcome.

| Situation | Proposed agent responsibility | Escalation boundary |
| --- | --- | --- |
| Route becomes blocked | Choose another authorized route or use the standing fallback | Request permission if every viable route leaves the assigned area or violates timing/risk limits |
| New contact changes the local situation | Reassess movement, observation or engagement within the mission's permissions | Report material changes; seek new intent when the mission is no longer feasible |
| Ammunition or readiness reaches an order limit | Conserve, halt, rally or withdraw as authorized | Cannot ignore the limit merely to complete the objective |
| Objective is achieved | Hold, regroup or follow the declared next task | Cannot invent a new pursuit or expand the mission |
| Communications are interrupted | Continue within existing authority and fallback rules | No assumed permission from silence |

Illustrative game order: “Secure the road objective before the scenario deadline. Preserve the unit; do not pursue beyond the marked area. Choose the route and firing positions. Report if the objective cannot be reached within those limits.” If a route is blocked, the agent can select an authorized alternative and report the delay. It does not ask the player which adjacent hex to enter. If no legal approach remains, it follows fallback and requests revised intent.

The player's intervention changes intent or constraints; it is not an instantaneous override of physical state. Orders remain subject to transmission, receipt and precedence. Routine adaptation within discretion is not disobedience; inability, refusal, rout and mutiny remain distinct.

### Decision timing under synchronous play

Use declared shared decision checkpoints. A material observation can mark an agent for replanning at the next checkpoint; routine reactions continue under deterministic standing rules in the meantime. The initial candidate is one decision opportunity per unit per command window. If this proves too coarse, test additional shared sub-window checkpoints under a fixed budget, rather than letting the fastest model react first.

At every checkpoint, freeze authorized observations before collecting decisions and resolve accepted choices together. An agent does not need a fresh player order to use existing delegated authority. If it cannot obtain a decision within budget, the recorded deterministic fallback applies. Model response time never grants a later battlefield view.

## Control methods researched

| Controller | What it offers | Main weakness | Role in battle |
| --- | --- | --- | --- |
| Finite state machine | Inspectable state and transitions | Many interacting states become awkward | Small condition/reaction machines |
| Behavior tree | Hierarchical, reusable action selection | Priority ordering requires design and debugging | Candidate local executor; see survey [S18](09-sources.md#s18) |
| Utility scoring | Transparent comparison of actions | Bad scales/weights cause strange behavior | Preferred first scripted commander |
| Goal/plan decomposition | Missions into subgoals | Invalid assumptions become stale | Later formation command |
| MCTS / belief-state planning | Search consequences under uncertainty | Branching, simulator cost, and belief quality | Later experimental baseline |
| Moderate language model | Interprets intent and tradeoffs; expresses concise reasons | Latency, inconsistent output, hallucinated capabilities | Bounded decision controller after scripted baseline |
| Learned policy / self-play | Potentially low-cost repeated decisions | Training cost, distribution shift, reward exploitation | Deferred experiment |

POMCP combines belief-state sampling with Monte Carlo search using a simulator. [S19](09-sources.md#s19) Its original POMDP formulation is not a drop-in solution to adversarial, simultaneous multiplayer: opponent policy and uncertainty require additional treatment. An agent may not search true hidden state just because the test harness has it.

## Shared controller contract

Conceptually: `decide(observation, mission, legal_actions, controller_memory) -> proposed_order`.

Observation includes simulation time, own known state, delivered friendly reports, perceived contacts, known terrain/weather, objective status as known, active order, and feedback on previous orders. Unknown enemy statistics remain unknown or explicitly estimated. Legal-action feedback itself must not leak hidden enemies or unseen terrain changes.

An order contains:

- Unique order ID, commander identity, controlled unit ID, observation version, and intended decision window.
- Parent mission/order reference, purpose, delegated scope and reporting triggers, distinguishing the superior's intent from executable local orders.
- Action type, destination or contact/location reference, posture, and optional route constraints.
- Start/expiry rules, completion condition, disengagement conditions, ammunition budget, and permitted reactions.
- A short player-facing rationale based on visible evidence; this is not private chain-of-thought.

Example, illustrative and not an executable schema:

```text
order: A-17
unit: A-platoon-1
based_on: observation-A-12
intent: hold
area: road-objective
posture: covered
fire_policy: identified_hostile_only
ammunition_budget: 60 rounds
expiry: end_of_window_14
withdraw_if: mission-defined loss or condition threshold is reached
fallback: remain in cover and report
```

The simulator validates ownership, delegation, action syntax, time, inventory, compatible weapons, target knowledge, path constraints, and condition limits. A model's text cannot override an invalid action. Validity at submission does not guarantee later execution; new damage or lost contact can cause an execution failure with a recorded reason.

Baseline utility can compare objective progress, survival risk, expected delay, ammunition use, fatigue, and commander's risk tolerance. All quantities use believed information. Log the components to make policy debugging possible. Avoid perfect knowledge of future outcomes or using the actual combat random stream for planning rollouts.

## Language-model use

At a command boundary, first evaluate whether a delegated decision or permitted tie requires inference. Continue valid standing orders deterministically when no decision is due. Initially allow at most one bounded decision request per active unit per window, plus the declared repair allowance. Keep a compact structured history, a current mission, and observation deltas; do not indefinitely append the entire battle transcript.

Model configuration is a replaceable adapter. Record provider/model identifier, version when exposed, generation settings, prompt template hash, request/response, parsed order, validation result, latency, and usage. A low temperature or provider seed is not a guarantee of reproducibility.

Reject unknown fields/capabilities and oversized output. Treat unit names, received free text, and scenario descriptions as data, not instructions that can change the controller's authority. Models get no filesystem/network tools and no access to hidden-state debug interfaces during play.

Failure policy, frozen before a run:

| Failure | Simulation behavior |
| --- | --- |
| Invalid order | Optionally one bounded repair within the same decision deadline; otherwise fallback |
| Timeout/provider unavailable | Continue last valid standing order if still safe/legal; otherwise deterministic hold/cover policy |
| Stale or duplicate submission | Reject stale versions; make duplicate order IDs idempotent |
| Lost target or blocked path after acceptance | Use declared reaction/fallback and record why |
| No commander response after casualty | Existing mission persists until explicit succession rules apply |

Record both proposed and accepted orders, plus tie-break requests, candidate sets and accepted selections. Replays consume accepted orders and selections; renewed calls are a new policy experiment with a different run ID.

## Command friction and hierarchy

All communication and staff capabilities follow the [WWII ceiling and period profiles](14-period-command-tools.md). Radio availability is equipment- and echelon-specific, not a blanket property of every WWII unit. Shared simulation checkpoints do not give the player instantaneous reports, synchronized in-world clocks or unlimited staff processing. Direct orders must use the scenario's feasible channels.

Make communications a timed delivery system: issued, queued, transmitted, received, accepted, executing, completed/failed. A delivered order is not a completed task. Radios, couriers, signals, and local voice use era-specific availability and delays; courier delay is a documented game precedent. [S02](09-sources.md#s02)

A command tree has one authoritative parent per controlled entity at a time and cannot contain cycles. Temporary attachments have explicit effective times. General orders supersede subordinate missions only through a versioned precedence rule, not because one message happened to finish later. A formation commander spends its attention coordinating missions, not issuing a new movement order to every soldier.

Friendly information sharing is not automatically instantaneous. Observation delivery and command delivery may have different delays. A general can authorize a platoon to retreat, but cannot force a pinned or mutinous unit to execute an impossible action. Subordinate initiative is bounded by objective, area, time, rules of engagement, and risk limits.

## Refusal, rout, and mutiny

**Refusal** is declining a particular order. **Rout** is loss of organized willingness/capacity under threat. **Surrender** ends resistance to an enemy. **Mutiny** is persistent collective rejection of the current command authority. These should not share one random “low morale” branch.

Initial prototype: support inability, orderly withdrawal, rout, and surrender; preserve command-trust state for later. A mutiny test extension should use declared preconditions, sustained trust/condition history, warning reports, and an explicit authority transition. Do not add a per-turn surprise chance to every healthy platoon. Coefficients and frequency need research; no historical rates are established here.

On mutiny, control becomes restricted or transfers to a scenario-defined autonomous controller. The unit does not magically change nation, teleport, replenish, or join an enemy. Reinstatement is a separate scenario-supported transition. This handles command breakdown without a political simulation.

## Multiplayer semantics

Represent `sides[]`, `players[]`, `commanders[]`, `units[]`, and a fixed scenario relationship matrix, not `red` and `blue` fields. Relationships can be hostile, allied, or neutral; there is no diplomacy loop. Ownership, command authority, hostility, and information sharing are different relationships.

Each window follows observe → submit/revise → seal → resolve → report. All participants face the same simulation boundary and policy for missing orders. Pending opposing submissions stay private. One authoritative adjudicator resolves the battle; rendering clients must not receive hidden truth merely to support deterministic lockstep.

Single-player uses a human controller plus system controllers. Automated testing uses system controllers for every side. Multiple players may control different branches of one side; exclusive unit authority prevents conflicting orders. Late joins and reconnects get authorized snapshots, not omniscient logs. Cryptographic commit/reveal is a possible later requirement for an untrusted peer architecture, not necessary for a trusted local prototype.

The simultaneous observation/action shape has a useful precedent in PettingZoo's Parallel API. [S16](09-sources.md#s16) Borrow the separation of agents, actions, observations, rewards, and terminal/truncated status; adopting that library or reinforcement learning is not decided.
