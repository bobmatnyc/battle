# Land, sea, civilians, and campaign growth

Proposed expansion design. Shared contracts should support these domains; they do not all belong in the first prototype.

## Historical units and arbitrary comparisons

A unit type is a versioned bundle of organization, weapons, mobility, protection, training, doctrine, and support assumptions. Preserve where and when a profile applies. “Civil War infantry” or “WWII infantry” is too broad to be a calibrated unit archetype.

The supported technological ceiling is WWII, including communications and command tools. Date, force, domain, theater and echelon constrain each content profile. Cross-era comparisons stay within that ceiling; a shared command-map UI does not equip earlier forces with later communications. See [period command tools](14-period-command-tools.md).

Separate establishment strength from the actual personnel present. Distinguish technical weapon performance from sustained battlefield performance, and inventory from effective crewed weapons. The Army's Gettysburg briefing book contains organization, logistics, small-arms, tactics, and weather sections that can seed a Civil War content study; it does not validate battle's proposed coefficients. [S23](09-sources.md#s23)

Each sourced parameter should carry a citation/locator, units, applicable dates/conditions, confidence, and a plausible range. Each inferred parameter should say which evidence it depends on. Missing knowledge must stay missing or explicitly assumed. Do not ask a model to fill historical statistics and then treat them as ground truth.

| Capability family | Needs to differ by period | Avoid |
| --- | --- | --- |
| Weapons | Reload, rate, range/effect, ammunition, reliability, compatible targets | Universal attack score |
| Organization | Cohort sizes, specialist roles, command span, formations | Assuming every platoon has a modern establishment |
| Communications | Voice, signals, messengers, radios, delivery reliability | Instant omniscient allied knowledge |
| Mobility | Foot, mounted, wheeled, tracked, sail, steam; terrain and load | A single movement rule for all domains |
| Protection | Cover, armor, compartment effects, exposed crew | Generic hit points that make every weapon effective |
| Doctrine and training | Behaviors supported by the unit's documented practices | Innate faction or ethnic superiority bonuses |

Capability validation happens before a scenario runs. An infantry-versus-ship matchup can be valid but one-sided, or invalid because required effects are not supported. The engine should report this, not fabricate damage to make a matchup exciting. Cross-era comparisons are labeled counterfactual and report the fairness basis: equal personnel, mission difficulty, or another explicit rule.

## Terrain, weather and seasons

**Confirmed requirement:** terrain and weather are set ahead of time; weather may include realistic randomization, with seasonal effects included. The following contracts are proposals, not a calibrated weather model.

Before a run, fix the map, geographic/climate context, date/season, start time, initial environmental conditions and weather policy. Store their versions in the scenario manifest. Terrain setup includes elevation, surface/material, vegetation, waterways and structures. Distinguish the configured landscape from changing surface state and battle damage: a preset map can still acquire wet ground, smoke or damaged structures through supported deterministic rules.

Offer three weather policies: fixed conditions for controlled duels; a prescribed timeline for authored or historically sourced scenarios; and bounded variation from a location/date-specific profile. Start the first duel with fixed weather. For variable runs, generate and record a seeded trajectory before the battle, or record an equivalent versioned event schedule. All sides share the same underlying environment; commanders see only observed conditions and authorized forecasts, not the future schedule.

Variable weather must persist and transition coherently across time and space. Couple temperature, precipitation, wind, cloud and visibility through validated profile rules rather than independently choosing each value. Set plausible transition rates and durations, with regional correlation across the small battlefield. Do not inject a storm to balance a losing side, reroll each unit's weather, or use an LLM to determine conditions. Profile ranges and frequencies require regional climate or historical evidence before being called realistic; no such coefficients are established here.

Season selects environmental context, not a universal “winter penalty.” Candidate effects to research and calibrate:

| Environmental state | Proposed tactical connection |
| --- | --- |
| Date, latitude and time of day | Daylight and illumination affecting observation and timing |
| Vegetation/foliage state | Concealment, sightline obstruction and movement |
| Accumulated wetness, snow or ice | Surface passability, movement effort and exposure; retain initial history and recovery state |
| Temperature and exposure duration | Fatigue/readiness and equipment conditions through supported rules |
| Water level, current, wind and sea state | Crossing, vessel movement and landing constraints under domain-specific models |

Represent effects once through their causal state so rain does not incur both a generic movement penalty and the same wet-ground penalty again. Initial wetness, snow and water conditions must be configured or derived from an explicit prior-weather history; a clear sky at battle start does not automatically imply dry ground. Keep tides as a separate location/time-dependent environmental process, not a weather die roll. These are proposed model boundaries; detailed mechanisms and source-backed parameters remain follow-up research.

Weather changes resolve as environmental events, with dependent visibility, movement and capability updates applied deterministically. Log the profile, seed where used, initial state, schedule and realized effects. Preserve the same environment across paired commander-policy experiments. A short duel need not feature a weather change; seasonal starting conditions can matter without a transition during play.

## Land expansion

After the aggregate infantry duel, add subelements and formations so units can distribute exposure and fire. Add crew-served weapons, cavalry/mounted movement, vehicles/armor, indirect fire, obstacles, and urban interiors as individually tested capability families. Unsupported assault or indirect-fire orders should be rejected clearly until their resolvers exist.

Indirect fire later requires observer knowledge, request/delivery time, scatter/area effects, ammunition, and explicit friendly/civilian exposure. It should not be a model's instant damage command. Air support is an eventual external mission/effect system needed for credible D-day scenarios, even if aircraft movement is initially abstracted.

## Sea is a related but different simulation

A ship is a platform with a crew, equipment, compartments/systems, and cargo. The natural naval atomic unit is one vessel, not a platoon-shaped block of sailors. A flotilla is a command group. This deliberately generalizes the user-facing concept of a unit while retaining platoon size for the initial land model.

Shared with land: identities, side relations, commanders, orders, contacts, simulation time, resource accounts, event records, objectives, surrender, and campaign persistence.

Naval-specific candidates:

- Position, heading, speed, turning limits, momentum, draft, and grounding.
- Wind-dependent sailing versus powered propulsion; currents, sea state, visibility.
- Weapon mounts/arcs, reload, range, ammunition, and crew assignment.
- Hull integrity/buoyancy, flooding, fire, propulsion/rigging, steering, weapons and sensors as separate damage channels.
- Damage-control workload competing with weapon/propulsion crew requirements.
- Mission kill, mobility kill, abandonment, striking colors, capture, and sinking as different outcomes.

Flying Colors explicitly distinguishes hull and rigging effects and contains ship-duel rules. [S10](09-sources.md#s10) Command's platform/mission approach supplies a control-architecture reference only. [S03](09-sources.md#s03) Its post-WWII technology is outside battle's scope. Neither justifies applying one damage table to all naval eras.

Do not freeze 25 m land hexes as the universal grid. Use scenario-specific physical scale and domain maps. Naval movement may ultimately use continuous position/heading over a hex environmental index; a six-heading-only model needs testing for artificial maneuver advantages. Choose this after a naval duel experiment, not during land implementation.

**First naval experiment:** two comparable historical sailing vessels, with wind, heading, arcs, ammunition, rigging/hull damage, and surrender. Follow with powered vessels as a distinct rules extension. If WWII is prioritized, the first naval fixture can instead use a tightly researched powered-vessel pair; no era is selected yet.

## Amphibious bridge to D-day

An amphibious battle couples offshore transport, landing approach, disembarkation, beach movement, supporting fires, and inland objectives. The National WWII Museum describes D-day's interdependent command, movement, support, beachhead and logistics elements. [S22](09-sources.md#s22) This supports a linked-system design rather than enlarging the duel map alone.

Embarked troops are carried entities: they cannot simultaneously occupy a land cell or fight as disembarked infantry. Landing has position, time, capacity, readiness, and disruption consequences. Cargo loss and personnel survival must reconcile with the transport outcome. Offshore and land maps share world coordinates, clock, and transfer IDs. Effects crossing map boundaries have one owner and resolve once.

Proposed progression: one landing craft carrying one unit → one beach lane with a shore objective → supporting ships and several waves → a sector with subordinate commands → linked sectors. Whole-operation D-day additionally needs operational timing, air support, reinforcement flow, shipping/port capacity and persistent logistics. It is a long-term integration target, not the first scale benchmark.

## Local population without politics

Model civilians as noncombatant population groups with presence, mobility, shelter, immediate needs, and exposure. They are not simply a combat side and do not become military targets because they occupy a contested area.

Candidate behaviors: remain sheltered, move toward a reachable shelter, evacuate along a safe known route, stop when a route is blocked, seek assistance. A small rule-based state machine is sufficient initially; individual civilian LLMs would add cost without a clear design benefit. Use bounded perceptions and capacity limits so a civilian group cannot know hidden danger or pass through a destroyed bridge.

Physical interactions include road congestion, blocked movement, transport seats used for evacuation, shelter capacity, smoke/fire exposure, building damage, and casualty/displacement records. A civilian presence can constrain engagement orders and complicate the mission. This is a proposed game mechanic, not a calibrated forecast of human behavior.

Population accounts distinguish sheltered, exposed, displaced/on-route, evacuated, wounded and killed using non-overlapping accounting dimensions; movement state and health state must not accidentally double-count people. Maintain a population total with explicit arrivals/departures.

For P0, keep the baseline map unpopulated for isolation. Add a populated variant after the core invariants pass: one civilian group, one shelter, one evacuation route, and an explicit protection objective. Civilian losses must remain visible in results even when they are not part of the win condition.

No ideology, elections, legitimacy, diplomacy, propaganda, or population-loyalty economy. Civilian aid must not magically generate ammunition. Mutiny belongs to command authority and troop condition, not a political subsystem.

## Campaign persistence and supply

A campaign is a sequence/network of engagements with persistent force resources and elapsed time, organized into temporary formations. Carry forward aggregate personnel/equipment losses, ammunition, proficiency, fatigue, and relevant infrastructure changes. Map cohesion and command trust through explicit reorganization rules; retaining the same formation identity is not required. Rest and recovery take time; wounded personnel do not instantly refill the next battle's fit count. No individual soldier roster is required.

Commanders may choose training or remixing as later force-management actions. Training has an objective, prerequisites, duration and readiness/resource costs; remixing explicitly reallocates aggregate cohorts and equipment. Reorganization cannot heal wounds, create proficiency, erase fatigue or reset collective refusal by changing a unit name. See [unit lifecycle and training](12-unit-lifecycle-and-training.md). These choices are distinct from the deferred recruitment/purchasing/provisioning system.

Separate tactical consumption from later provisioning. An initial battle needs a loadout and consumption. A campaign later needs movement, resupply routes, throughput, transport, depots, repair, reinforcements, and perhaps force assembly. Recruitment, buying troops and equipment, and a player-facing provisioning workflow are deferred.

Represent a campaign transition as an explicit result application with an idempotent transition ID. A replayed battle cannot apply its losses twice. A counterfactual branch produces a new campaign branch; it cannot overwrite the canonical outcome silently.

Later multi-resolution simulation must conserve resources and command information when formations are aggregated or expanded. Never simulate the same soldiers in an off-map aggregate and an on-map tactical battle simultaneously. Across sector boundaries, hand off control and event ownership at a synchronized barrier. Start with one authoritative process until scale measurements justify more complexity.
