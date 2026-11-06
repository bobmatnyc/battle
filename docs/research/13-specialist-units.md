# Specialist units: reconnaissance, intelligence and logistics

Research date: **2026-11-04**. The user requests specialist units including scouts, spies and quartermasters. This extends the earlier intelligence design to explicit assignable specialist capabilities. Representation, mechanics and rollout below are proposals. Research used publisher/developer manuals and rules, not hands-on play or a statistical survey of the genre.

## What the games do

The inspected games use several recurring representations: field units, attached capabilities, mission assets, staff traits, and physical supply networks. These are alternatives at different scales, not one universal specialist system.

| Game / inspected source | Observed mechanism | Useful principle for battle | Limitation to avoid importing |
| --- | --- | --- | --- |
| **Civilization VI**, base manual p. 59 | Recon units emphasize movement and exploration, with sight/terrain/stealth promotions and relatively weak combat. [S26](09-sources.md#s26) | A scout has a distinct information role and opportunity cost | Promotion trees and strategic hex movement do not establish historical reconnaissance performance |
| **Undaunted: Normandy**, pp. 11–13 | Scouts open tiles to ordinary movement; exploring adds Fog of War cards, while Recon removes one from hand and draws a replacement. [S27](09-sources.md#s27) | Reconnaissance can enable a plan while consuming command capacity | Its Fog of War cards represent friction in the deck; they are not a hidden-enemy observation model. Do not require a scout token before infantry can enter any unknown area |
| **Total War: Rome II**, official spy entry | Spies may operate independently or embed in an army. Counter-intelligence reveals hidden enemies; intercepting orders reveals further locations. Skills affect effectiveness. [S28](09-sources.md#s28) | Different assignments for the same specialist, with a clear target and result | Character progression, political actions and broad army bonuses conflict with battle's aggregate tactical focus |
| **Shadow Empire**, manual §§5.11, 5.14 | Logistics separates a road/rail network from units' pickup range. Recon information varies by level and can come from units or spies. [S29](09-sources.md#s29) | Distinguish transport capacity from last-leg delivery, and source access from detail learned | Its spy dice, political systems and very broad strategic intelligence thresholds are not battle defaults |
| **Operational Combat Series**, v3.1 §§13.1–13.2 | Headquarters draw and distribute supply within defined ranges; transport counters carry bounded quantities of supply. [S30](09-sources.md#s30) | Staff, stock and transport are different dependencies; supply needs a feasible path | Operational scale and transport exemptions are deliberate abstractions, not platoon-scale physical laws |
| **Lords of the Realm III**, manual p. 29 | Quartermaster is an army-affecting special ability that improves supply state. [S31](09-sources.md#s31) | A support role can be legible without another combat formation to move | A passive trait hides the cause of improved supply; battle should expose inventory, handling and delivery effects |

The quartermaster examples are particularly instructive: the named role can be a trait, while its practical work can be distributed across headquarters and logistics pieces. For battle, separate the decision-maker from the capacity needed to carry out the decision. This is a design inference from the sources, not a claim that all games do so.

## Recommended specialist model

Use a common **specialist formation/team contract**, with three representations: an independent field unit, an attachment to a parent formation, or an abstract mission asset. All have an owner, authority, capabilities, limited resources, location or coverage, readiness, task and reports. They need not have identical headcounts or occupy a platoon-sized footprint. A specialist team can be smaller than the initial combat unit without becoming a collection of individual characters.

| Role | Proposed representation and decisions | Deterministic work and limits | Visible result |
| --- | --- | --- | --- |
| Scout / reconnaissance unit | Field formation or later detachable aggregate team; choose an observation area, route, time budget and risk limits | Movement, concealment, observation accumulation, exposure and reporting; assigned troops cannot also count at full strength elsewhere | Timestamped contacts, searched coverage and route/terrain reports |
| Spy / intelligence cell | Assignable specialist asset with bounded area/access; usually abstracted off the tactical map unless physical movement matters | Access prerequisites, collection time, task capacity and message delivery; no universal live enemy tracking | Claims with provenance, uncertainty, age and collection scope |
| Quartermaster team | Staff/support attachment or headquarters team; prioritize requests, reserve stock and schedule supported deliveries | Stock compatibility, reservations, handling capacity, communication delay and available transport; no resource creation | Allocation decisions, shortfalls, delivery estimates and reconciled receipts |
| Supply / transport unit | Physical wagon, carrier or vessel group when supported; execute a movement/delivery task | Cargo, travel/loading time, route capacity, consumption, disruption and loss | Actual transfers and remaining stock, distinct from promises |

This refines the earlier spy proposal: spies are selectable specialists with tasks and state, even when their physical activity is abstracted. A spy asset is not merely a free report button. A quartermaster is not itself the wagon carrying every requested supply. Avoid universally treating a historical job title as the same capability across eras and domains; the eventual content profiles need period-specific research.

Qualification, equipment and assignment determine capability. An ordinary unit can observe; a specialist earns its value through supported differences in observation, mobility, training or reporting rather than a magical visibility radius. A specialist may have limited defensive capability where its profile supports it; do not assume all support units are harmless or all spies are combat units.

Engineers, signal teams, medical teams and forward observers are later candidates, not additional confirmed first-duel requirements. Each would need its own evidence-backed resolver before orders become executable. Shipboard specialist teams can be attached capabilities; supply vessels remain physical platforms. Do not duplicate one crew's labor across simultaneous tasks.

## Command and map interaction

The general chooses priorities; the twin can propose specialist assignments. A formation commander may task attached specialists within authority. A quartermaster controller can choose among legal allocations and schedules, but graph rules determine feasible deliveries. Routine execution needs no model call; a delegated planning decision can use inference under the existing budget and fallback rules.

Orders identify purpose, recipient, area/target, start/deadline, resource budget, risk limits, reporting and fallback. Illustrative game tasks include “observe the objective approaches and report before the next planning window” or “reserve the available ammunition for the holding unit and report any undeliverable request.” These are scenario-level intent examples, not historical procedures.

The command map offers a support layer and task panel: assigned, available, collecting/working, awaiting transport, report pending, blocked or completed. Physical units use last-reported positions; abstract cells use authorized areas of coverage. Display estimated versus confirmed results. A quartermaster knows reported stock and route conditions; an unseen route failure may invalidate execution without instantly revealing its cause to the player.

## Graph, events and outcomes

Extend existing unit, cohort, intelligence and order records rather than create a separate rules engine for every role. Proposed records are `SpecialistAssignment`, `SupportTask`, `StockReservation` and `Transfer`. Relationships can include `ATTACHED_TO`, `QUALIFIED_FOR`, `TASKED_WITH`, `RESERVES`, `CARRIES` and `DELIVERS_TO`, with quantities, effective times and scope.

Enforce one allocation of personnel, cargo and task capacity at a time. An attachment can become a detachment only through a valid formation transition; it cannot simultaneously operate at its parent and an independent map position. A reservation reduces availability but is not delivered supply. Source stock transfers to an in-transit account before destination receipt; interruption preserves or explicitly loses the correct cargo account. Reassignment, destruction and disbanding release or transfer tasks through recorded rules.

Log task issue/acceptance, allocation, start/progress, evidence collection, report delivery, reservations, loading, transit, receipt, interruption and completion. Outcome metrics differ: intelligence measures timeliness, supported detail and coverage; logistics measures request fulfillment, delay, shortages and losses. Do not reward specialists only for kills or give them private soldier XP.

Counterfactual experiments can measure whether an assignment helped a battle plan; an event chain alone cannot prove it caused victory. Player reports preserve fog of war; privileged evaluations may compare reports to ground truth after a run.

## Headless progression and verification

1. **Keep the core duel:** two combat formations, existing observation tasks and initial inventories. No mandatory support formation, economy or additional model call every window.
2. **Scout variant:** add one specialist capability or explicit aggregate detachment; compare against ordinary observation under identical conditions. Preserve personnel accounting if detached from a combat unit.
3. **Spy variant:** one scenario-provided cell, constrained collection scope and a delayed report. Compare acting immediately, waiting and corroborating; future enemy movement must not update an old report.
4. **Quartermaster variant:** a fixed stock and request ledger; initially test prioritization and reservations. Add one transport and destination only when transfer/movement rules exist. Nothing is purchased or generated.
5. **Formation expansion:** compete for the same specialist and transport capacity across several units; test interrupted orders, stale reports and constrained delegation.

When implementation is authorized, test no double assignment or double delivery, no specialist-induced hidden-state leaks, no transport teleportation, supported fallback when communication fails, retirement/rebinding, and replay without fresh inference. Measure cost and latency alongside decision quality on Evo; no tests or benchmarks have been run yet.

Battle provisioning remains deferred: scenario fixtures provide personnel, equipment, assets and stock. Tactical allocation and eventual delivery of existing supplies can be tested separately from recruitment, purchasing or campaign resupply generation.

## Evidence limits

These six examples establish useful design patterns, not typical market prevalence or historical accuracy. The inspected OCS edition is archival v3.1, not asserted current. Civilization's inspected base manual supports the scout claim; detailed spy mission probabilities were not verified from that manual. Shadow Empire is a large updated manual containing expansion material; only the cited sections support this comparison. Steel Division's manual route failed, and TaleWorlds search results did not establish a reliable developer description of Bannerlord's quartermaster mechanics; neither is used for mechanics claims. Period-specific specialist establishment, staffing, workloads and reliability remain open research.
