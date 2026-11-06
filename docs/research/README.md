# Research notebook

[Historical units and their colors](32-historical-units-and-colors.md) profiles the three Little Round Top regiments, their documented companies and attachments, flag provenance, and an inferred illustration.

**Research date:** 2026-11-04. **Original phase:** discovery and proposed design. **Method:** targeted reading of publisher rules/manuals, official project documentation, original papers, and institutional historical material. During that research phase, no games were played, no simulator was built, and no Evo execution occurred.

**2026-11-05 update:** The user authorized a Python/SQLite playable POC. See [implementation, source provenance and limitations](16-playable-poc.md) and the current [project README](../../README.md). Earlier graph-store and headless-only passages below describe the original design, superseded for this POC. The [original project brief](00-original-project-brief.md) is preserved as a dated design record.

**Monorepo update (2026-11-05):** the complete playable experiment now lives in [`apps/poc/`](../../apps/poc/README.md). Run its direct commands there, or use the root Makefile. Earlier implementation notes use POC-relative code paths. Shared research remains here.

## Main finding

**Confirmed command experience:** all combat units operate autonomously. The player issues intent and receives information primarily through maps and dispatches; orders and reports both use period-limited communications. [Autonomous units and dispatch-based command](04-command-and-agents.md#autonomous-units-and-dispatch-based-command) defines the proposed message flow and behavior during silence.

The most promising design combines Combat Mission's planning/resolution rhythm, Scourge of War's delayed command, Combat Commander's separation of suppression from destruction, Fighting Formations' command constraints, and naval games' distinction between mobility and fighting damage. These are inspirations, not evidence that combining them produces a validated simulation. Sources and edition limits are in the [register](09-sources.md).

The proposed product is a **command game with a reproducible adjudicator**. Its central tension is deciding what to ask subordinates to accomplish before information and conditions change. Tactical decisions must have observable consequences: time gained, ammunition spent, positions reached, troops preserved, or an order refused.

**Confirmed gameplay priority:** the player chooses battle strategy with assistance from a virtual twin; agent commanders execute and adapt orders tactically as battlefield conditions change. The player can also order unit commanders directly when logistically possible. The [virtual twin and direct-command rules](04-command-and-agents.md#virtual-twin-and-direct-command) connect strategy to the [tactical execution loop](04-command-and-agents.md#the-tactical-execution-loop); training, remixing and campaign systems support that experience.

**Confirmed logging requirement:** record events and outcomes from the first duel, including the chain from intent through agent decisions to adjudicated effects and mission/battle results. See [logging coverage](05-state-events-outcomes.md#required-logging-coverage).

**Confirmed interface requirement:** the player receives a [command map](02-design-brief.md#the-command-map). Proposed layers support strategic planning, twin assistance, reports and commander orders while preserving limited information and communication constraints. The first prototype remains headless.

**Confirmed environment requirement:** terrain and weather are set ahead of time, with realistic optional weather randomization and seasonal effects. The [environment proposal](06-domains-and-campaigns.md#terrain-weather-and-seasons) separates initial setup, coherent weather evolution and rule-driven battlefield changes.

**Confirmed map requirement:** overlay grids on actual maps and interpret terrain. [Real maps and terrain interpretation](03-simulation-methods.md#real-maps-grid-overlays-and-terrain-interpretation) proposes source alignment, physical scale, validated terrain extraction and period-limited commander views.

**Confirmed architectural direction:** The user specified a graph database and deterministic handling of complexity, with inference reserved for delegated decisions and tie-breakers. He further specified minimal dice rolling while preserving well-understood vagaries of war. [Graph and inference boundary](10-graph-and-inference.md) and [friction and uncertainty](11-friction-and-uncertainty.md) propose the contracts. Database product selection remains deferred. The original broad stochastic candidate is retained as a research comparator, not the default design.

## Reading order

**Confirmed prototype method:** granular tests for unit, grid, agentic control, engagement, events and communications layers. [Component-first prototype](15-component-prototype-tests.md) defines the proposed fixtures and small integration scenarios before full duels. It is a test specification, not executed code.

**Confirmed period boundary:** technology and communications stop at WWII, with battle-management tools appropriate to the player's historical command context. [Period command tools](14-period-command-tools.md) defines the proposed command desk and availability constraints; modern-game precedents do not expand the content ceiling.

**Confirmed intelligence requirement:** fog of war separates complete simulation truth from player and commander knowledge. Scouts and spies give the player choices about gathering and trusting intelligence. [Fog of war, scouts and spies](03-simulation-methods.md#fog-of-war-scouts-and-spies) proposes capacity, evidence, delivery and command-map rules without expanding into individual-character or political gameplay.

**Unit lifecycle clarification:** units are temporary aggregate formations that commanders can train or remix. Campaign persistence concerns force resources, proficiency and condition rather than permanent unit characters or individual soldiers. [Unit lifecycle and training](12-unit-lifecycle-and-training.md) supersedes earlier wording implying enduring platoon identities.

1. [Comparable games](01-game-survey.md): eleven precedents across digital/online, board, and miniatures play.
2. [Design brief](02-design-brief.md): scope, player decisions, and a first duel.
3. [Simulation methods](03-simulation-methods.md): alternatives and proposed heuristics.
4. [Command and agents](04-command-and-agents.md): bounded agency and multiplayer semantics.
5. [State, events, outcomes](05-state-events-outcomes.md): data contracts and accounting.
6. [Domains and campaigns](06-domains-and-campaigns.md): sea, civilians, amphibious combat, persistence.
7. [Validation and Evo](07-validation-and-evo.md): how to test the design before deployment.
8. [Decisions and questions](08-decisions-and-questions.md): what is required, proposed, and deferred.
9. [Source register](09-sources.md): direct links and evidence limits.
10. [Graph and inference boundary](10-graph-and-inference.md): deterministic graph-backed state/rules and bounded inference requests.
11. [Friction and uncertainty](11-friction-and-uncertainty.md): causal mechanisms, limited stochastic exceptions, and minimal-dice validation.
12. [Unit lifecycle and training](12-unit-lifecycle-and-training.md): temporary formation identity, training decisions and aggregate reorganization.
13. [Specialist units](13-specialist-units.md): six additional digital/tabletop precedents for scouts, spies, quartermasters and logistics; proposed aggregate specialist model.
14. [Period command tools](14-period-command-tools.md): WWII ceiling, historical command-room evidence and proposed tools/communications profiles.
15. [Component prototype tests](15-component-prototype-tests.md): contracts, focused acceptance cases, component composition and evidence gates.

## Evidence labels

- **User requirement:** requested by the user; no external citation needed.
- **Observed precedent:** supported by the linked rulebook, documentation, or paper, within the inspected edition.
- **Proposal:** a recommendation for battle; not an existing feature or a historical finding.
- **Illustrative:** a made-up example or coefficient to clarify a contract; requires calibration before use.
- **Open:** deliberately unresolved; do not silently turn it into a decision.

All formulas, fixture sizes, performance targets, and state schemas in these notes are proposals unless expressly identified as sourced. “Deterministic” means reproducible given versioned inputs and recorded decisions; it does not mean eliminating uncertainty or claiming language-model calls reproduce exactly.

## Research limits

This is a first design survey, not an exhaustive review of the genre. Digital coverage includes network multiplayer precedents; it is not a review of today's matchmaking availability or a completed browser-game survey. Warzone browser-game references could not be retrieved. Several useful manuals are older editions, explicitly identified in the register. No proprietary game engine's internal casualty formulas were inspected.

Historical calibration is much less complete than the game-system survey. One institutional Civil War reference was inspected; detailed platoon establishments, battlefield loss distributions, civilian behavior, mutiny rates, naval damage data, and WWII weapon profiles remain follow-up research. Proposed human-behavior coefficients are therefore particularly uncertain.

16. [Playable POC](16-playable-poc.md): authorized Python/SQLite experiment, rules, source map, limitations and validation.

17. [Language, localization and multiplayer](17-language-localization-and-multiplayer.md): period unit/staff voice, i18n by default, internal player dispatches, cooperative/opposing/terrain-control scenarios, and campaign deployment across multiple fronts. Confirmed user requirements; implementation status is explicit.

18. [Simulation clock and replay](18-simulation-clock-and-replay.md): server-owned start/pause and speed controls, recorded playback, timing guarantees, local planning behavior and multiplayer limits.

**Map presentation update (2026-11-05):** the [playable POC](16-playable-poc.md#stylized-map-update--2026-11-05) now uses stylized vector terrain, based on the supplied Google Maps visual example. The historical scan remains reference material.

19. [Open-source map rendering](19-open-source-map-rendering.md): implemented MapLibre browser tiling, local assets and SVG fallback; PMTiles proposal and historical georeferencing boundaries.

20. [Reconnaissance and standing reactions](20-reconnaissance-and-standing-reactions.md): implemented progressive estimates, scout/spy profiles, independently dated identification, no-order local response, versioned compatibility and component verification.

## God Mode and physical command — 2026-11-05

[21 — God Mode and command location](21-god-mode-and-command-location.md) records the user’s observer requirement, the player’s attached command unit, period communications, implemented `poc-3` behavior and limitations. God Mode is separate from the normal fog-of-war interface and agent observations.

## Unit interaction and reorganization — 2026-11-05

[22 — Unit panel and formation actions](22-unit-panel-and-formation-actions.md) records click-to-inspect strength/options, move/hold instructions and the implemented, bounded split/combine workflow. New poc-4 battles preserve resources, lineage and communication constraints.

23. [Common order templates](23-common-order-templates.md): implemented hold/move/rest/retreat/resupply/recon missions, shared catalog, finite ammunition points, mission reports, replay and component checks.

24. [Map features and Dig in](24-map-features-and-digging-in.md): roads, building cover/visibility, persistent fieldworks, conserved tools, construction time, observer knowledge and replay.

25. [Commander recommendations](25-commander-recommendations.md): local advice, delivered map flags, review/dispatch/dismiss, expiry and replay.

26. [Standing orders and troop analysis](26-standing-orders-and-troop-analysis.md): persistent doctrine, independent delivery, readiness assessment before/during/after battle, recommendations, fog of war and replay.

27. [Service architecture and dependency injection](27-service-architecture-and-dependency-injection.md): implemented application services, ports/adapters, composition root, browser components, migration boundaries and contract tests.

28. [Monorepo and stack direction](28-monorepo-and-stack-direction.md): isolated POC, proposed TypeScript/Next.js layout, current Vercel worker/realtime capabilities and migration gates.

**Timeline clarification (2026-11-05):** [18](18-simulation-clock-and-replay.md#one-battlefield-timeline--2026-11-05) records location/calendar display and removal of player-facing turns and replay revision labels.

29. [Unit counters and readiness](29-unit-counters-and-readiness.md): troop strength/type, skill, energy, morale, observer estimates and formation actions.

30. [Will battle scale from a skirmish to a campaign?](30-design-scale-assessment.md): tactical contrasts, measured storage and reconnaissance costs, player workload and decision gates.

31. [Evo target and TypeScript portability](31-evo-target-and-typescript.md): portable release, first-host runbook and language recommendation.

[OpenRouter unit image pilot](33-openrouter-unit-images.md) records the model request, verified output and game skill contract.

[Six historical command tests](34-six-era-command-tests.md) pairs each requested era with a sourced action, a shared-engine check and the remaining historical comparison.

[Field glasses and visible unit appearance](35-field-glasses-and-appearance.md) covers the approved OpenRouter input and display evidence. [Cannae at army scale](36-cannae-army-scale.md) adds a double-envelopment experiment beside the six small actions.

[Battle photo gallery and sources](battle-gallery/README.md) provides two reconstructions for each of seven actions, including the [Cannae pack research](battle-gallery/cannae.md).

[37 — First five selections and source register](37-first-five-selection-register.md) names the five company-scale comparisons, holds Gergovia as the sixth, lists Cannae separately, proposes a Hougoumont gate state and Hill 223 reconstruction variants, and records order and outcome sources per case.

[38 — Scenario catalog](38-scenario-catalog.md) defines the scenario-entry format, how the catalog resolves new and saved games, the `poc-9` limits an entry must respect, and what each planned battle still needs beyond data.

[39 — Scenario-defined sides and victory kinds](39-scenario-sides-and-victory-kinds.md) records the `poc-9` edition: side ids, names, roles, the player side and a pluggable victory kind come from the scenario entry, with `poc-8` frozen for replay and Little Round Top unchanged.
