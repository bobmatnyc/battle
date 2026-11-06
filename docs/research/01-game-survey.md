# Comparable games: control, friction, and useful abstractions

Research date: 2026-11-04. These are document-based observations, not hands-on reviews. Source editions and access limitations appear in the [source register](09-sources.md). Recommendations in the last two columns are our design judgments.

The confirmed simulation ceiling is WWII. Modern and science-fiction game references inform abstractions and control design only; their technology is outside battle's content scope. See [period command tools](14-period-command-tools.md).

## Digital and online multiplayer precedents

| System | Observed control mechanism | What battle can borrow | What should not carry over automatically |
| --- | --- | --- | --- |
| **Combat Mission: Shock Force 2** | WEGO pauses for orders, resolves 60 seconds, and permits replay before the next orders phase. The manual also describes real-time play. [S01](09-sources.md#s01) | Commit orders, watch consequences, reassess; useful for simultaneous human/agent play | A 60-second window is a precedent, not evidence it fits every weapon era or map |
| **Scourge of War: Gettysburg** | Command hierarchy, subordinate movement/stance orders, and optional courier delays at specified command levels. [S02](09-sources.md#s02) | General's intent, limited communications, and persistent subordinate tasks | Its regimental scale is not a platoon simulation; larger hierarchy should arrive after the duel works |
| **Command: Modern Operations** | Units, groups, and missions have doctrine/engagement settings; patrols can autonomously investigate and engage within their mission constraints. [S03](09-sources.md#s03) | Separate mission, permissions, local action, and platform capability; particularly useful for naval expansion | Contemporary sensor/weapon detail would overwhelm the first infantry prototype |
| **The Battle for Wesnoth** | Official project documentation separates terrain-related hit avoidance from resistance to damage types. [S04](09-sources.md#s04) | Show how terrain and weapon/target interaction affect outcomes; make probabilities legible | Fantasy balance and hit points are not historical calibration; a single defense statistic hides detection, exposure, and protection |

Scourge's manual explicitly covers network multiplayer as well as AI command. That is a useful precedent for multiple people occupying different levels of an army. These notes do not verify whether its present online services are available. Wesnoth's main website blocked retrieval; its official mechanics wiki was readable. Browser-native Warzone pages failed retrieval and are not used as evidence.

## Board and miniatures precedents

| System | Observed control mechanism | What battle can borrow | What should not carry over automatically |
| --- | --- | --- | --- |
| **Combat Commander: Europe** | Fate cards activate orders; suppression affects capabilities and is recoverable; broken units, recovery, and rout have separate rules. [S05](09-sources.md#s05) | Fire can stop a unit acting without killing it; recovery is a meaningful command decision | Card availability is an effective game abstraction, but does not by itself explain radio failure or order delay |
| **Fighting Formations** | Platoon/squad scale; initiative spent on orders and activations, command influence, and reactive fire. The US 29th product describes 75 m hexes and roughly five-minute turns. [S06](09-sources.md#s06) | Explicit opportunity cost for command attention; immediate reactions within an order system | Copying its alternating initiative would conflict with battle's synchronous requirement; five-minute turns are not a recommended physics step |
| **Commands & Colors: Napoleonics** | Command cards constrain activation; blocks track losses; terrain, retreat, and combined-arms mechanisms shape combat. Scenario unit scale varies. [S07](09-sources.md#s07) | Few understandable orders; force preservation; capability interactions that make position matter | Section cards and variable counter scale are abstractions, not measured command bandwidth or a universal troop unit |
| **Chain of Command** | Publisher's 2024 development discussion retains command dice while emphasizing additional reactions in the then-proposed second edition. [S08](09-sources.md#s08) | Uncertainty about what command can accomplish, with local responsiveness | This is a development statement, not a full inspection of final second-edition rules; do not infer exact dice or shock rules from it |
| **Musket & Pike** | Inspected v6 rules organize initiative, leader orders, facing/formation, reactions, morale, and rally/reform separately. [S09](09-sources.md#s09) | Formation and cohesion can be distinct from casualties; era-specific behavior matters | This is early-modern warfare, including English Civil War material, not an American Civil War unit-data source; v7 is listed elsewhere |
| **Flying Colors Deluxe** | Hex-based naval movement with wind and command activation; different hull/rigging effects, firing arcs, striking colors, and a ship-duel section. [S10](09-sources.md#s10) | Begin naval testing with a duel; distinguish losing mobility, firepower, and willingness to continue | Its sailing model cannot cover steamships or WWII vessels unchanged; board tables should not become universal physical laws |
| **Black Seas** | Designer FAQ describes wind-sensitive movement and campaign connections to land battles. [S11](09-sources.md#s11) | Weather as a decision constraint; sea outcomes that alter later land engagements | FAQ-level coverage supports broad concepts only, not a detailed reconstruction of its rules |

## Control-system synthesis

| Option | Benefit | Failure mode for battle | Recommendation |
| --- | --- | --- | --- |
| Alternating full turns | Simple to explain and debug | One side exploits an entire turn before the other can respond | Useful test baseline only |
| Random activations/cards | Creates uncertainty with few rules | Players may experience arbitrary inability to act | Adapt uncertainty into explicit delay, availability, and cohesion |
| Real-time direct control | Responsive and familiar | Reflex advantage, model latency, difficult synchronized testing | Defer |
| Simultaneous orders / WEGO | Intent matters; both sides act from the same boundary | Long windows can feel unresponsive; conflict resolution must be explicit | Preferred prototype structure |
| Mission-based autonomy | Scales the player's attention | Subordinate behavior can appear inexplicable | Use bounded missions and report reasons for deviation |
| Full language-model adjudication | Easy to improvise stories | Unstable arithmetic, rules, and outcomes; hard to audit | Reject as authoritative resolution |

## Heuristics worth adopting

1. **Make inability to act explainable.** Distinguish no ammunition, no sighting, suppressed troops, delayed orders, blocked movement, and deliberate refusal.
2. **Spend time as well as resources.** Movement, reload, reforming, observation, and command transmission create commitments.
3. **Make retreat a possible success.** A delaying unit that escapes after holding a road may win despite losing ground.
4. **Separate morale from losses.** A unit can have most of its personnel and still be unable or unwilling to advance.
5. **Build uncertainty into information.** A last-seen contact is not a continuously tracked target.
6. **Reward a mission, not a kill counter.** Time, territory, escape, protection, and force preservation can conflict.
7. **Expose causality after resolution.** A player should understand why an order did not become the expected action.

These are proposed design principles synthesized from the survey. They are not claims that the surveyed games use identical mechanisms.

## Follow-up research with highest value

The [specialist follow-up](13-specialist-units.md) adds Civilization VI, Undaunted: Normandy, Total War: Rome II, Shadow Empire, Operational Combat Series and Lords of the Realm III, comparing field reconnaissance, intelligence assignments, staff traits and physical supply systems. It distinguishes observed mechanics from battle's proposed specialist roles.

Study a final Chain of Command rulebook if available to the project; compare a detailed squad system such as Advanced Squad Leader against the proposed abstractions; inspect a WWII naval system before defining that era's damage rules; add a verified browser-native multiplayer example for submission/deadline UX. These are evidence gaps, not prerequisites for discussing the current design.
