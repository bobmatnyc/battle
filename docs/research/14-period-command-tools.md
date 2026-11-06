# Period command tools and the WWII ceiling

**Confirmed requirement, 2026-11-04:** simulation technology and communications extend through WWII, and players receive battle-management tools that generals could have used by that time. This limits simulated capabilities, not the software used to build the game. The contracts below are proposals interpreting that requirement.

## Scope and availability

Use the end of WWII in 1945 as the proposed outer content cutoff. Each scenario specifies date, force, theater, domain, command echelon and issued equipment. A technology existing somewhere before the cutoff does not make it available to every commander. Earlier historical forces keep their own period capabilities; counterfactual matchups declare each side's equipment and communication profile explicitly.

Postwar systems are outside the simulation scope, including satellite reconnaissance, GPS, modern digital battlefield networks and contemporary live tracking. WWII capabilities are eligible only where supported by the scenario and implemented rules. The ceiling does not require implementing every late-war invention, weapon or experimental system. Existing research into modern games remains useful for interface/control principles, not as permission to import their technology.

## Historical grounding

The U.S. Army's Signal Corps history describes WWII field radio, radio relay, radar, photography and continued pigeon communications. This supports a mixed capability model; it does not establish universal equipment availability or numerical reliability. [S32](09-sources.md#s32)

IWM's Duxford operations-block material describes radar reports reaching Fighter Command and Observer Corps information being processed through the command system. This is a useful precedent for turning reports into a shared operational picture. It is an air-defense example, not evidence that an infantry platoon possessed an equivalent network. Only the official indexed excerpt was accessible. [S33](09-sources.md#s33)

An Army historical article on amphibious signals describes radio, field-wire and switchboard arrangements and damaged circuits. It supports treating D-day communications as infrastructure and coordination work. The full page was blocked; only official indexed excerpts were inspected, so no numerical capacities are adopted. [S34](09-sources.md#s34)

## Proposed player's command desk

| Tool | Player function | Simulation constraint |
| --- | --- | --- |
| Map table and overlays | Mark objectives, boundaries, routes, phase lines and last-reported positions | Terrain knowledge and markers come from authorized maps/reports; annotations are plans, not truth |
| Orders and message register | Draft, dispatch, revise and track written/verbal orders | Transmission, receipt, acknowledgment and execution remain distinct; missing acknowledgment is not proof of failure |
| Clock, timetable and phase plan | Coordinate start times and conditional next tasks | Common simulation time does not imply perfect in-world synchronization; scenario rules define known timing and permitted triggers |
| Situation and intelligence board | Review scout/spy reports, estimates and conflicting accounts | Collection and delivery timestamps, coverage, source and uncertainty remain visible |
| Strength and supply returns | Review reported readiness, ammunition and support requests | General sees the latest delivered return; only the simulator necessarily knows current exact stock and casualties |
| Communication desk | Choose among available messenger, visual, wire/telegraph/telephone or radio channels | Era, equipment, compatible endpoints, staffing, route/range, setup, capacity and disruption govern feasibility |
| Staff and liaison support | Delegate analysis, coordination and specialist tasking | Staff capacity, authority and communication determine what can be accomplished and when |
| Naval chart / plotting view | Work with bearings, courses, contacts and scheduled movements | Use period observation and reporting capabilities; eligible radar or acoustic reports require suitable equipment and domain rules |

The table defines proposed game affordances, not a claim that every historical headquarters had every item. Specific establishments, signal equipment, procedures and timing need era-specific content research. A scout report, aerial observation, photograph or sensor contact can have a different processing and delivery chain. None grants an unlimited live map feed.

Use a readable digital interface for these tools: zooming, sorting delivered messages and drafting annotations are conveniences. They must not create extra military knowledge or instantaneous communications. A calculated route or estimate uses known map data and stated assumptions. Do not expose ground-truth line-of-sight, hidden obstruction checks, future weather, exact enemy strength or omniscient win probabilities as planning tools.

The virtual twin remains the requested modern game assistant, presented as support for the general's judgment and staff work. It can explain available reports, compare feasible plans and prepare orders. It does not give in-world units modern equipment or bypass the scenario's channels and staff-processing limits. Commands are still transmitted through the period system. Deterministic rules enforce these limits; the model cannot invent historical equipment or substitute external knowledge of a famous battle for scenario intelligence.

## Graph and evaluation contracts

Add a versioned `CommandCapabilityProfile` referencing date/force/echelon, tools, equipment and staffing. A communication link records endpoints, medium, compatibility, setup/operating state, capacity, travel/transmission/processing delay and visibility policy. Separate the physical network from each commander's knowledge of its condition. A shared user interface does not imply a shared instantaneous network between allied players.

Scenario validation rejects unsupported or out-of-period equipment, and flags explicitly counterfactual allocations. Events record dispatch, relaying, delay, processing, receipt and failure evidence; the player's map updates only when authorized information arrives. Local commander knowledge may legitimately be fresher than the general's picture.

Test matched orders through different period profiles, channel loss and fallback, stale returns, unknown failures, compatible versus incompatible endpoints, and twin/map leakage. Verify that new UI conveniences cannot change the information available to a controller. The first headless duel can use a small, explicit messenger/voice profile; WWII networks, naval plotting and staff capacity arrive as separate validated extensions. No UI, communications simulator or historical equipment pack has been built.
