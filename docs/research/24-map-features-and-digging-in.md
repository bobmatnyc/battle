# Roads, buildings, fortifications and Dig in

**2026-11-05 — user requirement:** the map includes roads, fortifications and buildings, and units can receive a “dig in” order. **Implemented:** local `poc-6`, shared order catalog `common-orders-v2`. Locations, dimensions, work rates and effects below are authored POC choices; they are not reconstructed or calibrated Little Round Top features.

## Map and simulation contract

| Feature | Presentation | Deterministic effect |
|---|---|---|
| Roads/tracks | Named pale road lines with contrasting edges | Connected road-hex edges cost 70 movement points plus the existing uphill cost, versus normal open-ground cost 100. Troops and couriers share this rule. Entering from off-road does not receive the road discount. |
| Buildings | Labeled farmstead and barn footprints | Building hexes provide cover 45/40, cost at least 140 to enter, and have obstacle heights 8/6 m that obstruct intermediate sight lines. These are aggregate occupied compounds, with no individual room/floor combat. |
| Prepared fortification | Breastwork symbol | One briefed prepared position at hex 11,13 provides cover 60. It can be used by either side; it is a physical feature, not a faction bonus. |
| New fieldworks | Persistent symbol, reported completion percentage and hex tooltip | Construction progressively raises the hex's cover; abandoned partial works remain and can be resumed or used by another formation. Maximum added cover is 30, capped at total cover 70 without reducing preexisting cover. |

The north farm lane, southern track, farmstead, barn and prepared breastwork are original authored scenario content. Their positions and widths are illustrative. Building heights and the initial road/fortification briefing are likewise authored. Historical georeferencing, authentic building footprints and verified 1863 roads remain separate work.

The SVG feature overlay stays aligned with the MapLibre terrain, camera and hex grid and also works with the SVG terrain fallback. Features are taken from the selected observer/replay view. Map zoom never changes movement, sight or cover. Roads follow authored waypoints; their rasterized connected hex edges define the simulation route. The pathfinding heuristic accounts for the cheaper road edges and is checked against Dijkstra's shortest-path cost.

## Dig in template

**Player flow:** select a friendly unit → **Give an order → Dig in → Send order**, then start the clock. No destination is supplied: the commander improves the ground occupied when work can be performed. Local tactical relocation may change where subsequent work occurs; works at the former position remain.

**Period intent:** “Strengthen your present position with hasty fieldworks. Keep watch and report when ready.” This is original game prose, not a historical quotation.

- The order uses ordinary authority, versioning, voice/courier delivery, acknowledgements and supersession. Dispatch alone creates no cover.
- Initial formations receive 20 aggregate entrenching tools each. Tools are reusable equipment, recorded in the unit panel; split apportions them and combine conserves them without leaving duplicate equipment on retired units.
- Work per 30-second interval is `min(current strength, tools × 2, remaining work)`. Completion needs 400 labor units on ordinary ground or 800 on rocky ground. A fresh 40-person formation with 20 tools therefore needs five or ten minutes of uninterrupted work, respectively. These deliberately compressed POC rates are **not historical estimates**.
- Each working interval adds two fatigue points. Fatigue at least 80 blocks construction until the player arranges rest. Digging receives no simultaneous idle-fatigue recovery.
- Recent/current fire, visible enemy contact within five hexes, suppression above 20 or tactical movement suspends work. The engine checks after simultaneous combat, so incoming fire in the same interval prevents construction credit. Autonomous self-defense continues.
- Occupied road/building hexes cannot be excavated. No tools means refusal. These conditions are adjudicated locally, with a report, rather than exposing hidden current state through command validation.
- Partial work raises cover gradually; completed work changes the unit mission to hold. Repeating Dig in cannot stack cover indefinitely. Existing complete fortifications can be occupied immediately without rebuilding.
- The feature belongs to the ground. Moving, retreating, splitting, combining or losing a formation does not carry the cover to another hex.

There are no siege forts, directional parapets, digging animations, tool wear, trench connections, demolition, building destruction, doors, artillery penetration or civilian occupancy rules yet. Hasty works abstract local earth/stone improvements; logistics for imported construction materials remains deferred.

## Knowledge and reports

Initial roads/buildings/prepared works are in both sides' briefing. Dynamic construction is ground truth until locally observed. Living formations can observe works within three hexes with line of sight; changed observations travel to their headquarters through normal reports. The command detachment's direct observations arrive locally. Distant work does not update the player's map merely because its unit was given an order.

Each side retains last-observed feature state, with observation and receipt times. Older delayed reports cannot overwrite newer observations. Inference receives the same reported features and the initial briefing terrain, avoiding a hidden-state leak from construction-modified canonical cover. God Mode explicitly shows current features everywhere. No builder identity or side ownership is inferred from a fieldwork sighting.

## Events, versions and validation

`fieldworks_progress` events link unit, order version, feature, position, labor, cumulative effort, completion, cover and fatigue. Shared mission events record start, blocking, resumption, failure, completion and replacement. Terrain reports retain observation/arrival times. State, terrain cover, tool inventory and events commit atomically in SQLite. A failed write cannot leave partially applied construction.

New battles use `poc-6`. `engine_v5.py`, `orders_v5.py` and `formations_v5.py` freeze the previous common-order edition; earlier editions remain intact. **Reset** starts the new scenario and archives the old game. Existing saves are not migrated automatically.

The full suite passes **129 component tests**, including 15 focused feature tests: road routing, sight-blocking buildings, construction timing and fatigue, fire interruption/resumption, tool/rock/exhaustion limits, unsuitable ground, abandoned/reused work, bounded cover, delayed feature knowledge, stale-report rejection, combat effects, tool conservation, transaction rollback and exact replay. UI and HTTP smoke checks cover feature presence and the new order. Browser verification observed initial roads/buildings/works and live 5% construction at U2 after one interval, with fatigue and a terrain dispatch.

The headless run `1ae5419dd1624d13` reached 60 intervals with 2,496 events and 63 identical replay snapshots in `/tmp/battle-features-headless.sqlite`. Existing local saves from preceding editions also replay identically. These are local rule and integration checks, not historical calibration, a live-model evaluation, Evo execution or deployment evidence.
