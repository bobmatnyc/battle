# Simulation methods and candidate heuristics

Research synthesis and proposals; no algorithms have been implemented or calibrated.

**Updated boundary:** deterministic graph-backed rules handle state, relationships, constraints, and effects; inference is limited to delegated decisions and declared tie-breakers. The user additionally requires minimal dice rolling while retaining well-understood vagaries of war. See [the architecture clarification](10-graph-and-inference.md) and [friction model](11-friction-and-uncertainty.md). Deterministic causal mechanisms are the default; stochastic formulas below are comparison candidates or narrowly justified exceptions. Models never supply dice rolls or casualty arithmetic.

## Time and resolution alternatives

| Method | Strength | Cost or risk | Fit |
| --- | --- | --- | --- |
| Alternating turns | Easy state transitions | First-mover artifacts | Diagnostic baseline |
| One large simultaneous resolution | Small event volume | Misses intermediate contact and movement exposure | Too coarse by itself |
| Fixed-step simulation | Repeatable phase boundaries; straightforward simultaneous effects | Work grows with ticks and active entities | Recommended duel foundation |
| Pure discrete-event simulation | Efficient during long quiet intervals | Same-time event ordering and continuous movement are harder | Consider after profiling |
| Hybrid fixed steps plus scheduled events | Explicit reload/order timers without continuously reconsidering everything | Requires one authoritative scheduling convention | Recommended conceptual design |

Fixed steps decouple simulated time from wall-clock/model latency. This adapts the principle in [Fix Your Timestep](https://gafferongames.com/post/fix_your_timestep/) [S14]. It does not prescribe a graphics update rate. Begin with a candidate 1-second tick and compare finer/coarser resolutions.

Within each command window, all controllers observe the same boundary time, subject to their distinct information. Collect and seal their orders before advancing. A slow model must not give its side later battlefield information. Details of submission and fallback are in [command and agents](04-command-and-agents.md).

## Proposed microstep transaction

At each tick:

1. Deliver orders/messages whose simulation timestamps are due; apply already-due environment changes under a documented boundary convention.
2. Freeze the eligible start state. Derive all movement intents and deterministic local reactions from that state and available observations.
3. Resolve movement capacity/conflicts together, producing trajectories and a provisional geometry view. Do not make one side move first because its ID sorts earlier.
4. Determine observations and possible engagements along those trajectories, including exposure while crossing open ground. A unit that ends behind a wall was not necessarily protected throughout the tick.
5. Reserve each unit's personnel activity, ammunition, reload time, and weapon capacity once. Derive all same-time fire/melee effects from the shared eligibility/geometry view.
6. Combine effects by target, resolve them under the declared rules, then commit ammunition, casualties, suppression, and other deltas together. Draw only when an explicitly enabled residual-uncertainty mechanism requires it. A unit hit at the same adjudication instant can return fire if eligible; previously incapacitated personnel cannot.
7. Update cohesion, fatigue, morale, and enforced reactions; these affect the next tick. Derive surrender/capture and objective transitions using explicit timing rules.
8. Append the atomic tick's events, verify invariants, compute a state hash, and publish authorized observations.

This is a chosen approximation, not literally continuous physics. At coarse steps it can permit too much simultaneous action. Step-size convergence tests must measure the distortion. If finer timing becomes necessary, batch equal-time events and use trajectory crossing times rather than sequentially mutating opponents.

Movement conflicts: hostile units trying to enter the same cell stop at a contested boundary unless an assault is valid; hostile edge swaps cannot pass through each other. Friendly traffic is limited by footprint and terrain capacity. Use declared deterministic priorities for routine congestion. A designated commander may resolve a genuine scheduling tie among legal alternatives through the bounded inference contract; absent a valid choice, use a deterministic fair fallback such as rotating priority. Do not permanently privilege low IDs. Collision/queue policies need explicit fixtures.

## Spatial representation

Use axial `(q,r)` cell coordinates, with derived cube coordinate `s=-q-r`. Hex distance is `(abs(dq)+abs(dr)+abs(ds))/2`. Store physical scale separately; render orientation and map outline are presentation choices. Red Blob's guide provides the coordinate, neighbor, line, and range foundation. [S12](09-sources.md#s12)

Proposed data layers:

- **Cell:** terrain, elevation in meters, surface condition, vegetation/structure obstruction, concealment, cover, occupancy capacity.
- **Edge:** wall, hedge, stream, road connection, bridge, crossing cost, and passability by movement type.
- **Environment:** light, precipitation, visibility, wind, temperature and, at sea, depth/current/sea state.
- **Dynamic overlays:** smoke, fire, debris, damaged bridges, footprints, civilians, and known hazards.

Keep concealment (harder to detect), cover (less exposed/vulnerable), and obstruction (blocks a sightline or path) distinct. Terrain changes have versioned timestamps so cached visibility/path results can be invalidated.

Use A* for a unit's route with nonnegative movement-time costs. An admissible lower bound can use hex distance times the cheapest possible legal step cost. Use Dijkstra when computing reachable regions or many destinations; shared flow fields become useful only when many units share goals. [S13](09-sources.md#s13) Risk-aware route selection is a separate utility preference: penalize *believed* exposure, not secret enemy positions. A cache key includes movement capability and terrain revision.

For the duel, trace a consistent line through hexes and compare interpolated sight height to terrain/structure occlusion. Define edge-touch behavior symmetrically; test `LOS(a,b)=LOS(b,a)` when heights and sensor rules are symmetric. A simple center ray cannot model partial visibility across a large formation; later sample footprint points or use exposure fractions. Movement progress should be metric, retaining fractional distance across ticks rather than hopping a whole hex per tick.

## Real maps, grid overlays and terrain interpretation

**Confirmed requirement:** support grids over actual maps and reading terrain from them. The following preparation and interpretation pipeline is proposed; no map importer or geographic library has been selected or built.

Keep three layers distinct: the source map/chart, the authoritative simulation terrain, and the map/terrain knowledge available to each commander. A historical map can be useful even when incomplete or inaccurate; the simulator may use a separately curated reconstruction. A grid overlay alone does not turn map artwork into terrain data.

1. **Register the source:** retain map title, creator, survey/publication dates, geographic extent, scale, coordinate system if known, attribution/use terms and file hash. Historical sheets, topographic maps and nautical charts are candidate inputs. USGS's historical collection provides an example of scanned/georeferenced maps, but its stated 1884–2006 coverage does not directly supply a Civil War-era map. [S35](09-sources.md#s35)
2. **Align to physical space:** use embedded georeferencing or validated control points to locate the sheet in a suitable metric scenario coordinate system. Record transformations and positional uncertainty. GDAL documents how an affine geotransform maps raster pixels to geographic/projected coordinates; that is a mathematical reference, not a library choice or proof a distorted historical sheet fits one affine transform. [S36](09-sources.md#s36)
3. **Overlay the grid:** anchor hex origin, orientation, physical center spacing and extent in those world coordinates. Panning, zooming or changing display resolution cannot change cell size or simulation distances. Grid references on the original map need an explicit mapping to simulation coordinates. Other grid shapes remain a future option; hexes are still preferred.
4. **Interpret terrain:** combine structured elevation/feature data where available with reviewed tracing of contours, roads, woods, settlements, rivers and crossings. Record source, confidence and scenario-date corrections per feature. A printed symbol is evidence requiring interpretation, not a combat modifier by itself. Unknown elevation, bridge capacity or building protection remains unknown or explicitly assumed rather than defaulting to zero or an invented exact value.
5. **Compile and validate:** deterministically derive cell/edge properties, preserve source-feature links and freeze a versioned terrain snapshot before the run. Retain mixed terrain fractions or subcell geometry where needed; a single majority label must not erase a narrow river, road, wall or crossing. Bridges and connected routes need explicit topology. Cover, concealment, slope and passability remain separate rule inputs.

“Reading terrain” has two contexts. During scenario preparation, an author validates the reconstruction before it becomes authoritative. During play, the player/twin reads only the issued map and delivered terrain reports, and can mark a route or ask for an assessment with its assumptions shown. A future delegated map-interpretation assistant could suggest annotations for review, but must not write unvalidated terrain into the graph or generate hidden ground truth during a battle. The first path can use manual annotation and deterministic conversion without adding model inference.

Historical consistency matters: a current road, coastline, forest or building footprint is not automatically correct for an older battle. Modern data may assist authoring only with explicit date reconciliation; it does not entitle commanders to modern imagery or precision. Terrain resolution cannot exceed source accuracy merely because the hexes are small. Keep local map error distinct from display alignment error, and retain their effects on the commander's estimates.

For naval/amphibious expansion, use compatible chart coordinates, depth units and reference levels, shoreline and crossing/landing geometry. Tides and changing water levels modify the configured environment under separate rules; chart depth is not automatically current water depth. A land elevation model cannot substitute for missing seabed data.

First map experiment after implementation is authorized: one small, dated map crop with a known scale, an anchored hex overlay and a reviewed terrain layer. Test control-point alignment, coordinate round trips, metric distance, cell/edge assignment, connected crossings and stable terrain hashes. A second run changes only the display scale and must yield identical physics. Map import remains scenario preparation; recruitment and provisioning stay deferred.

## Detection and knowledge

Ground truth does not go into a controller prompt. Each observer maintains contacts with a location or uncertainty region, last observation time, estimated category/strength, confidence, and source. Contacts can be lost, merged, or misidentified; target IDs exposed to agents are contact IDs, not hidden entity handles.

Preferred detection candidate: accumulate perceptual evidence from visible exposure, distance, light, observation time, motion and observer condition, with decay when evidence is lost. Cross explicit acquisition/identification thresholds; retain contact state and expand uncertainty after contact loss. This is a proposed abstraction, not a calibrated human-perception model. Observations never follow a hidden target automatically.

Research comparator only: a detection rate `lambda` can yield `P(detect during dt)=1-exp(-lambda*dt)`. This hazard model is not the default and needs evidence before any residual stochastic use; do not roll independently each frame.

## Fog of war, scouts and spies

**Confirmed requirement:** the system knows everything in the modeled battlefield, but the player operates under fog of war and chooses how to factor scouts and spies into the battle plan. The following intelligence mechanics are proposals.

Separate authoritative truth, locally observed evidence, delivered reports and the commander's assessment. A scout detecting something does not instantly inform the general or every ally. Each recipient receives reports through its communication rules. System-controlled opponents and the virtual twin use the same observation boundaries as players; omniscience belongs only to adjudication and privileged diagnostics.

The player's choices include what question to investigate, where to assign reconnaissance, how long to wait, what capacity/risk to commit, and whether to act on, discount or corroborate a report. Routine observation continues without a special order, but dedicated intelligence tasks can improve coverage or evidence at a cost. Taking no reconnaissance action is a valid choice with consequences, not a hidden automatic disadvantage roll.

| Capability | Proposed abstraction | Limits and tradeoffs |
| --- | --- | --- |
| Scouts | A reconnaissance task for a capable aggregate unit; later a conserved detachment if splitting is supported | Position, terrain, visibility, observation time, exposure, fatigue and report delivery; troops assigned elsewhere cannot also provide full combat capacity |
| Spies | Scenario-provided abstract intelligence assets with bounded access, subject/area coverage and report schedules | Reports reflect accessible evidence at collection time, can arrive late or remain incomplete, and require declared task capacity and lead time; no omniscient live tracking |

Spies concern military intelligence within this game, without adding politics, civilian-loyalty mechanics or named individual-character play. Their recruitment and purchase remain part of deferred provisioning. A fixture can provide an asset or an initial report without implementing a spy-management economy. Specific historical access, reliability and compromise mechanisms require further research; none are calibrated here.

The subsequent requirement for specialist units makes scouts, spy cells and quartermaster teams explicit assignable capabilities. Abstract spy representation still has staffing/capacity, tasks and lifecycle; it is not a free report button. See [specialist research and proposed representations](13-specialist-units.md).

Reports preserve source/provenance, collection time, delivery time, estimated location/strength, scope and confidence. Source reliability and confidence in a particular claim are distinct, and displayed confidence must not be an oracle for truth. Preserve contradictions and shared provenance: two relayed copies of one report are not independent corroboration. Reports can become stale, and an unsuccessful search means only that nothing was detected within its coverage and conditions, not that no enemy exists.

The default is deterministic evidence production from access, visibility, observation duration and reporting rules. Do not add a generic per-turn spy-success die roll or let a model fabricate intelligence. Misidentification or misleading reports require an explicit supported mechanism or authored scenario evidence, with privileged provenance retained for audit. The twin may interpret the delivered evidence and suggest reconnaissance as delegated decision support; it cannot silently replace an estimate with hidden truth.

On the command map, distinguish observed contacts, reported claims and planning assumptions. Show uncertainty regions, report age and known coverage; show unseen terrain or changes according to scenario knowledge rules. A distant report need not grant a precise target or permission to attack an unseen entity. Log intelligence assignments, collections, transmissions, receipts, assessments and resulting orders so after-action review can distinguish what was true from what each commander knew.

Start the headless duel with ordinary unit observation and an explicit observe/reconnaissance task using the existing unit footprint. Add a delayed intelligence-report fixture to test spies' information contract before implementing a broader asset system. This preserves the single-unit baseline and does not require individual scouts or extra autonomous model calls.

## Combat model choices

| Approach | Use | Limitation |
| --- | --- | --- |
| Combat-results table / odds ratio | Fast prototype checks | Coarse discontinuities; hides equipment and exposure |
| Lanchester-style aggregate attrition | Baseline scaling and gross sanity checks | Assumptions omit many local conditions; not a universal duel resolver |
| Cohort stochastic effects | Explainable rates and bounded casualties without individual soldiers | Requires careful calibration and treatment of correlated exposure |
| Deterministic cohort accumulation | Minimal dice; effects derive from time, exposure and capacity | Threshold/rounding artifacts and unrealistically smooth losses require testing |
| Individual projectile/person simulation | Fine geometry and detailed evidence | Expensive data and validation burden; unnecessary initially |

Prefer **deterministic cohort-level accumulation** for the first duel, with explicit exposure and condition state. The following stochastic alternative is preserved for comparison and possible limited exceptions, not routine resolution. Research on Civil War numbers explicitly cautions against indiscriminate use of the square law. [S20](09-sources.md#s20) “Older era = linear law, newer era = square law” is not an acceptable general ruleset.

### Illustrative ranged-fire pipeline

Partition ready personnel by weapon/role and position exposure. For cohort `c`:

`attempted_rounds_c <= min(available_ammunition_c, ready_weapons_c * sustainable_rate_c * dt)`

Rates are rounds per weapon per second; keep fractional firing/reload progress so small timesteps do not round every action to zero. Muzzle-loading and magazine weapons need explicit reload cycles or equivalent accumulated work. A listed technical rate is a prior/ceiling, not an effective battlefield rate.

Allocate rounds to eligible targets before damage. Do not multiply total firepower by each visible enemy. Derive an effect rate from the allocated rounds, range, aim, target movement/exposure, protection, weapon compatibility, training, fatigue, and suppression. Zero committed rounds means zero new direct-fire hazard from that action; already-in-flight effects are separately scheduled. A later armor model must first determine whether a weapon can meaningfully affect that target; unsupported combinations cannot be rescued by a universal strength ratio.

Default prototype candidate: accumulate a calibrated casualty-equivalent effect against each exposed cohort, carry fractional residual across steps, and transfer whole-person losses only at declared thresholds, bounded by eligible personnel. This accumulator is a numerical abstraction, not fractional wounds to particular soldiers. Define how residuals behave on disengagement and cohort split/merge; prevent exact-threshold exploits and duplicate losses. Aggregate simultaneous incoming effects before applying transfers. This may suppress genuine outcome variability, so it requires comparison with historical ranges before claiming realism.

Stochastic comparator only: `p_i = 1-exp(-hazard_i*dt)`, then `new_incapacitated_i ~ Binomial(eligible_people_i, p_i)`. It is not the recommended per-tick resolution loop. Account for wounded versus killed using separately sourced assumptions; avoid representing all casualties as deaths in either model.

Suppression is a separate response to incoming threat and near misses. Do not require a casualty before troops seek cover. Melee is a later distinct close-contact resolver; a first duel can stop or disengage at contact until that capability is supported, with the limitation reported rather than resolved by invented numbers.

### Human condition

| Quantity | Meaning | Timescale / candidate drivers |
| --- | --- | --- |
| Suppression | Immediate inability to expose oneself effectively | Incoming threat; decays when protected and not under fire |
| Morale | Willingness to continue the mission | Recent losses, isolation, leadership, perceived support and escape |
| Cohesion | Ability to act together | Formation disruption, movement, casualties, communication, rally |
| Fatigue | Physical depletion | Movement, load, exertion, time, rest |
| Skill | Learned proficiency | Stable scenario attribute initially; slow campaign development |
| Trust/obedience | Willingness to accept this commander's authority | Persistent command history and severe conditions; mutiny extension |

Illustrative suppression update: `S_next=clamp(S*exp(-dt/tau)+incoming_pressure,0,1)`. Pressure must scale with elapsed exposure; `tau` is a recovery timescale. This is a hypothesis, not a psychological law.

Use explicit condition transitions such as steady → shaken → pinned → routing, with recovery thresholds lower than escalation thresholds, minimum dwell time, and bounded recovery. That hysteresis prevents oscillating between panic and perfect readiness. Rout, voluntary withdrawal, surrender, and mutiny remain separate transitions. Do not repeatedly apply the same “morale penalty” to fire, movement, and survival without checking double-counting.

## Supply without provisioning

Declare ammunition by compatible type, carried load/capacity, initial fatigue and readiness. Consume inventory when the action commits. A unit cannot fire when ammunition or crew capacity is exhausted. Food/water need not meaningfully change during a brief duel; those stocks belong to longer scenarios. Resupply routes, depots, buying forces, and procurement are later systems.

## Randomness and reproducibility

Only for justified stochastic exceptions, use a pinned random algorithm and stable named draw domains, conceptually keyed by `(run_seed, mechanism, entity_or_shared_cause, episode_id, draw_index)`. Use event/exposure identity rather than a new draw each tick, so changing tick size does not itself create more failure chances. Counter-based generators support independent keyed draws; Random123 is a reference, not a selected dependency. [S17](09-sources.md#s17)

Keep combat, weather, sensing, and policy randomness separate. Specify encoding, unique keys, integer conversion and distribution sampling; merely hashing a key is not a complete statistical design. An unrelated weather draw must not shift all future casualty draws. Parallel execution must not change reduction order or random identities.

Exact replay initially targets the same pinned engine/runtime. Fixed timesteps alone do not guarantee cross-machine equality; floating-point behavior can differ. [S15](09-sources.md#s15) Choose fixed-point/quantization or a documented numerical contract later if cross-platform bit equality is needed. Replay uses archived accepted orders, never fresh model calls.
