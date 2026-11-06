# Headless experiments, validation, and Evo

This is a proposed evaluation plan. No tests have been run; no Evo hardware, operating system, model service, repository, or network access has been verified. Evo is the user-designated testing target, not a selected deployment architecture.

## Four different questions

1. **Rule verification:** does the code do what the declared rules say?
2. **Model credibility/calibration:** are mechanisms and outcome distributions plausible for the declared historical scope?
3. **Commander evaluation:** do policies make useful, legal, understandable decisions under their information constraints?
4. **Game quality:** do players face meaningful choices and understand their consequences?

Do not substitute one for another. Replaying exactly proves reproducibility, not historical realism. A model beating a poor baseline does not establish good tactics or an enjoyable game. The National Research Council's human-behavior report distinguishes intended-use validation, calibration, and the limits of simple explanatory models. [S24](09-sources.md#s24)

## Headless run contract

Inputs: scenario/version, rules/content version, initial-state hash, combat/environment seeds, controller assignments/configurations, command window, tick size, maximum simulated duration, wall-time/cost budgets, and predetermined failure policy.

Outputs: run manifest, initial graph state, accepted-order trace, tie-break requests/candidates/selections, controller audit, resolved event stream, snapshots/final state, structured result, metric summary, and concise after-action report. A run can execute without a UI. Scripted-policy runs and replay must work without a model endpoint.

A manifest should record engine revision, runtime/numerical mode, host characteristics relevant to reproduction, RNG/distribution version, scenario hash, model/prompt settings, start/end wall time, termination versus truncation, and all artifact hashes. Credentials do not belong in manifests or prompts.

## Prototype gates

The user specifies granular component tests, especially units, grid, agentic control, engagement algorithms, events and communications. Use the [component contracts and fixtures](15-component-prototype-tests.md) before the battle-level gates below. G0 includes isolated rules and small composition slices; graph durability must be proven against the actual chosen store, and live-model quality is evaluated separately from deterministic adapter behavior.

| Gate | Experiment | Required evidence |
| --- | --- | --- |
| G0: deterministic kernel | Fixed scripted orders on a tiny map | Repeated state/event hashes match; invariants hold; save/resume matches uninterrupted run |
| G1: symmetric duel | Equal units and symmetric controllers | No unexplained side/order bias; plausible movement/fire/resource outcomes |
| G2: tactical factors | Change cover, range, fatigue, ammunition, morale, or visibility individually | Expected direction under controlled conditions; no double counting; sensitivity plots/tables |
| G3: agent commanders | Scripted vs scripted, model vs scripted, model vs model | Legal-order rate, timeout behavior, objective outcomes, cost/latency; replay from captured decisions |
| G4: small formations / civilians | Several units, one subordinate commander; populated fixture | Authority, communication delay, no knowledge leakage, conserved population and supplies |
| G5: naval duel | One supported vessel model per side | Movement, arcs, damage and surrender; no invalid land assumptions |
| G6: amphibious sector | Transported unit, landing, shore objective, support | Embarkation/transfer conservation, one clock and effect ownership |
| G7: campaign and scale | Persistent battles and increasing active-unit counts | Idempotent transitions, resource carry-over, measured performance |

These are proposed gates, not permission to begin implementation. Deployment decisions follow demonstrated local execution, including model-controller runs on Evo with the chosen access mode.

## Verification fixtures

Logging is required for the first duel. Verify that an order and adaptation can be traced through effects to mission/battle outcomes; recorded observations match what agents actually received; player journals do not expose hidden events; outcome totals reconcile with the event record; retired unit references remain resolvable; replay needs no fresh inference; and interrupted/log-write-failed runs preserve a valid committed prefix without claiming a completed result.

| Category | Cases and expected property |
| --- | --- |
| Time | Exactly due orders, expiry, reload across windows, no frame-rate dependence |
| Simultaneous combat | Both eligible shooters fire; prior casualties cannot; reversing entity iteration does not alter resolved state |
| Movement | Hostile same-cell entry, edge swap, narrow bridge, friendly congestion, unreachable objective, partial movement |
| Geometry | Hex neighbors/distance, edge-touch LOS, cover versus concealment, elevation, moving exposure |
| Real maps | Control-point alignment, coordinate round trips, source units/dates, unknown-data handling and reproducible terrain compilation; roads/bridges remain connected and narrow obstacles survive grid conversion; pan/zoom cannot affect physics; basemap and terrain queries do not leak unauthorized features |
| Environment | Fixed-weather baseline; prescribed and seeded schedules replay identically; location/season profile bounds and transition persistence hold; initial wetness/snow survives unrelated weather changes; shared weather is consistent across units; future schedules do not leak to agents |
| Conservation | No negative ammunition; casualties bounded by personnel; split/merge and embark/disembark reconcile |
| Information | Unseen enemy moves do not update contacts; agents cannot target hidden IDs; legal-action lists do not leak hidden state |
| Scouts and spies | Collection does not imply delivery; reports cannot exceed source access; stale contacts do not track hidden movement; duplicate reports do not count as independent evidence; unsuccessful searches do not prove absence; task allocations conserve unit/asset capacity; twin and opponent AI receive no privileged truth |
| Specialist support | No double assignment of attachments/detachments, labor or cargo; reservations reduce availability without implying delivery; interrupted transport preserves cargo accounting; quartermaster decisions cannot create stock; task/controller retirement and receipts replay exactly |
| Command-map contract | Markers retain report timestamps and uncertainty; hidden movement/damage does not update the player's projection; drawn plans produce orders rather than state mutations; orders retain normal authority and delivery checks |
| Condition | Suppression without casualties, recovery under cover, hysteresis, rout versus surrender/refusal |
| Orders | Duplicate, late, invalid, stale-observation, lost-target, commander loss, bounded fallback |
| Autonomous command | Human-owned and system-owned units continue within standing intent during silence, channel loss, pending clarification and inference timeout; direct orders alter mission on valid receipt without bypassing the unit controller |
| Dispatches | Separate event, send and arrival times; no headquarters update on local detection alone; acknowledgments obey return-path delay; late old reports do not silently replace fresher observations; map markers link only to delivered evidence or valid direct observation |
| Period command tools | Reject unsupported/post-WWII capabilities; no automatic later-era equipment for earlier forces; enforce endpoint compatibility, staff/channel capacity and delay; map/twin conveniences reveal no hidden truth or instant allied reports |
| Virtual twin | Advice uses only delivered information; drafts have no command effect; execution requires an effective grant; strategic assistance and accepted orders replay from recorded inputs |
| Direct intervention | Reachable, delayed, disrupted and unreachable channels; delivery differs from execution; scoped override cannot be undone by stale in-flight orders or silently overwritten by the twin; cancellation obeys transport rules |
| Termination | Simultaneous victory, both routed, accepted surrender, timeout draw, three sides, technical truncation |
| Persistence | Interrupted tick recovery, snapshot+events, old schema rejection/migration, no double campaign application |
| Graph determinism | Same facts inserted in different orders yield the same canonical state/results; query order and worker count cannot decide combat |
| Inference boundary | No call without a delegated decision or declared tie; candidate selection cannot change constraints; expired/invalid selection uses recorded fallback |
| Graph/event consistency | Stale-version commit rejected; crash cannot leave updated graph with missing events or applied events with stale graph |
| Formation lifecycle | Form/split/merge/remix/disband conserves allocations; retired unit IDs reject orders; personnel are not both assigned and available; repeated reorganization cannot improve condition for free |
| Aggregate training | Prerequisites, elapsed time and availability costs enforced; no instant completion, duplicate gains or specialist skills created by averaging; interruption/resumption and cohort transfers preserve progress correctly |

Information tests compare two worlds that differ only in facts inaccessible to an observer: that observer's observation and legal-action representation should remain the same until evidence reaches it. Audit reports remain privileged; final result visibility follows the scenario's disclosure policy.

## Distributional and sensitivity experiments

Begin with a zero-draw baseline, then controlled causal-friction fixtures. Vary explicit scenario inputs and accepted decision traces; repeating identical inputs must produce identical results. Seeded batches below apply only to justified residual mechanisms or a separately labeled stochastic comparator. They are not a requirement for routine combat rolls. See [friction and uncertainty](11-friction-and-uncertainty.md).

Add exposure/timestep-invariance tests for faults, persistence and repair tests, shared-cause correlation checks, no-double-counting checks, and tests for casualty-threshold exploits. Attribute outcome variation separately to decisions, hidden initial conditions, and residual events. A count of RNG calls alone is not a measure of how much luck drives the battle.

For a symmetric duel, run mirrored scenarios and swap side assignments over predeclared seeds. When testing identity symmetry, remap RNG identities consistently; arbitrary ID changes can otherwise change valid random samples. Compare win/loss/draw rates, losses, duration and ammunition use. Report sample size and confidence intervals, not “looks balanced.”

A candidate exploration batch is 200 seeds per scripted fixture, followed by more runs only where uncertainty matters. Under independent Bernoulli trials, 200 observations near a 50% rate give roughly ±7 percentage points at 95% confidence; 1,000 give roughly ±3 points. Draws, paired seeds, and correlated model behavior require suitable paired or multinomial analysis. These counts are suggested budgets, not acceptance thresholds or evidence already collected.

Use separate seed sets for calibration and evaluation. Fix terrain/controllers and vary one factor at a time before factorial interactions. Check distributions of time to contact, rounds fired, casualty fraction, rout time, objective completion, and final condition. Cover should reduce exposure under fixed behavior; it need not increase win rate under every autonomous policy because it can change behavior and timing.

Compare 10/25/50 m candidate cell spacing, 10/30/60-second command windows, and 0.5/1/2-second ticks on equivalent physical scenarios. Do not alter map extent or weapon range accidentally when changing resolution. Report which results converge and which remain artifacts. Finer spatial detail without better input data may add false precision.

Historical data need comparable force size, duration, terrain, objectives, support, and starting condition. A famous battle's winner is not enough to identify all coefficients. Maintain uncertain parameter ranges and sensitivity ranking; do not tune many parameters to reproduce one outcome. Reserve historical cases not used in fitting, and label counterfactual matchups as extrapolation.

## Agent experiments and budgets

Start with hold, advance-to-objective, and conservative utility policies. Give all controllers the same observation contract and available orders. Compare one policy change at a time; separate prompt changes from physics changes. Use isolated RNG for planning rollouts so search cannot peek at or consume actual combat draws.

Record legal-order fraction, repairs, fallbacks, objective progress, loss/resource vector, avoidable idle windows, order churn, explanation fidelity, decision latency, calls, and token usage. Human review should assess whether different missions generate different sensible behavior; win rate alone is not enough.

Illustrative load: a 20-minute battle at 30-second windows has 40 decision windows. Two units called every window require up to 80 model decisions before repairs. One hundred units would require up to 4,000, plus formation-command calls. This arithmetic motivates persistent orders and event-triggered decisions; it is not a measured cost or performance estimate.

Use equal per-controller call/repair budgets and a predeclared wall-time deadline. Deadline-triggered fallback is part of the observed decision trace. Report technical failures separately so one provider outage does not look like a tactical defeat. An entirely local-model mode and a local-simulation/remote-model mode are different Evo tests; do not describe the latter as offline.

## Evo readiness checklist for the future build

When authorized to implement, identify the Evo machine and verify CPU, RAM, storage, OS, available acceleration, model endpoint/runtime, credentials mechanism, and execution access. Do not infer these from older project memories. Determine whether “everything on Evo” means local model inference as well as local simulation and tests.

Then prove, in order:

1. A scripted duel executes locally and saves the full bundle.
2. Replay and checkpoint recovery work locally without model service access.
3. Both sides can be agent-controlled in a complete run.
4. Batches expose distributions and failures, and stop within declared budgets.
5. Multi-unit, naval, amphibious, and campaign gates are tested there as those capabilities are built.

Measure tick throughput, graph query/commit cost, peak memory, event volume, run duration, model latency and total cost at 2, 10, 100, and eventually larger unit counts. No performance target is established before measuring Evo. The graph-database architecture is confirmed; its product, partitioning, distributed workers, cloud hosting, and web frameworks remain unselected.

## Human playtest questions

The first duel must also demonstrate delegated execution: change the superior's objective/risk limits while holding conditions fixed, then change observed conditions while keeping the mission fixed. Verify sensible local adaptation without a new player order, compliance with authority limits, reporting/escalation when required, and deterministic fallback between shared decision checkpoints. Judge decision quality and causal trace, not whether a model always wins.

Can a player explain why a unit stopped? Can they trade ammunition or time for a mission advantage? Is retreat sometimes preferable? Do information delays create decisions instead of confusion? Do agents execute intent without constant babysitting? Does a change in tactics matter more than an unexplained modifier? Does the after-action report accurately distinguish known causes from uncertain ones?

These questions determine whether the simulator is becoming a compelling game, not just a reproducible spreadsheet.
