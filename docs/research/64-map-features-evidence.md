# 64 — Roads and buildings on land maps: evidence and checks

**Date:** 2026-11-07. **Requirement:** named roads and tracks drawn as continuous lines and buildings as distinct footprints, with the hex grid on or off; drawn from the observer-visible features the engine uses for routing, cover and sight; for each historical action, the evidence for each feature's placement, with reconstructed or illustrative features marked. Features are those of [24](24-map-features-and-digging-in.md) (`poc-6`) and the entry format of [38](38-scenario-catalog.md) (`MapEntry.features`).

This document adds checks and an evidence table. No feature placement, value or citation changed.

## 1. What is checked

| Check | Where | What it asserts |
|---|---|---|
| Road route | `tests/test_map_features_catalog.py` `test_each_named_road_is_cheaper_than_the_off_road_route` | For every road of every entry, `grid.path` between the road's first and last routed hex follows the road hex by hex, and costs less than the `grid.path` route on the same cells with road edges removed |
| Building sight and cover | `test_each_building_blocks_a_named_sight_line_and_adds_cover` | For every building, a named line through its hex is clear by `recon.sees` with the building's obstacle height removed and blocked with it; the hex carries the building's height and at least its cover |
| Works cover | `test_briefed_works_raise_their_cell_cover` | Every briefed fortification's hex has at least the works' cover |
| Coverage | `test_every_scenario_with_roads_buildings_or_works_is_listed` | The road, building and works ids of every catalog entry match the tables in the test, so a new or removed feature fails the suite |
| Observer view | `test_hill_223_commander_and_replay_show_only_reported_works` | §3 |
| Rendering | `scripts/check_map_features.mjs` | For every entry, from the commander view the browser receives (`RulesSimulation.view`, then `present_view`): each road is one SVG subpath through its points; consecutive routed hexes are adjacent; the line crosses every routed hex and never strays from them by half the road casing width or more; each building is a closed rect centred on its hex and inside it; the only `no-grid` CSS rule hides hex outlines |
| Grid toggle in the app | `scripts/smoke_ui.mjs` `featuresSurviveGridToggle` | In `static/app.js`, for Little Round Top and Hougoumont, the hex toggle sets only `no-grid` and the drawn map contains the same feature layer with the grid off and on |

Each Python check was shown able to fail: with live works leaked into `features.known`, with road edges ignored by `grid.cost`, and with building obstacle heights removed, the matching test fails. The rendering check fails when a road path is split into two subpaths.

Feature drawing moved from `static/app.js` to `static/map-features.js` (`BattleFeatures.render`) unchanged, so the check renders the same SVG the page does.

## 2. Sight lines used

| Scenario | Building | Observer hex | Target hex | Line |
|---|---|---|---|---|
| Little Round Top | Farmstead (7, 3) | (6, 3) | (8, 3) | Across the farmstead |
| Little Round Top | Barn (17, 8) | (16, 8) | (18, 9) | Along the North farm lane past the barn; both ends are lane hexes |
| Hougoumont | Chateau and farm (11, 10) | (11, 8) | (11, 13) | From the lane outside the north gate to the end of the ride through the wood |

Concord, Pegasus, Hill 223 and Gergovia have no building feature, so no building sight line applies. Gergovia's walls are terrain rows with obstacle height, not features (entry `map.walls`).

## 3. Observer-visible features

Rule ([24](24-map-features-and-digging-in.md)): a side's map shows briefed features and the works it has a report of, at the reported progress; inference's terrain view reads `briefing_cells`, never the current modified cells.

Little Round Top already has this test: `tests/test_features.py` `test_remote_construction_requires_reports_and_does_not_leak_to_inference` (live view and inference only). The new test extends it to Hill 223 and to replay. A2 digs at (15, 3), six hexes from the Company G post, beyond the entry's 3-hex observation range. At the first revision with the works in the truth, the commander view and `BattleQueries.replay` at that revision list only the briefed `old-trench`. The American `known_terrain` cover at (15, 3) is the briefing cover. The God view lists the works. After the report arrives, the view lists the works at a lower progress than the ground. The earlier revision still does not list them.

## 4. Evidence table

Labels are copied from each entry's `provenance` (`battle/scenario*.py`). No entry labels a single road or building; the column "Feature label" says so. "Map label" is the entry's `map` key (or a narrower `map.*` key) that covers the layout as a whole.

| Scenario | Feature (id) | Kind | Feature label | Map label (key) | Source locator |
|---|---|---|---|---|---|
| Little Round Top | North farm lane (`north-lane`) | road | unlabelled | unlabelled (the entry has no `provenance`) | None. [24](24-map-features-and-digging-in.md) line 14: "original authored scenario content … illustrative". The engine tags every briefed feature `authored-poc` at build (`features.setup`) |
| Little Round Top | Southern track (`south-track`) | road | unlabelled | unlabelled | As above |
| Little Round Top | Farmstead (`farmstead`) | building | unlabelled | unlabelled | As above |
| Little Round Top | Barn (`barn`) | building | unlabelled | unlabelled | As above |
| Little Round Top | Prepared breastwork (`prepared-works`) | works | unlabelled | unlabelled | As above |
| Hougoumont | Lane from the north gate to the ridge (`north-lane`) | road | unlabelled | authored: illustrative layout, not surveyed (`map`) | None |
| Hougoumont | Western lane round the farm (`west-lane`) | road | unlabelled | authored (`map`) | None |
| Hougoumont | Ride through the wood (`wood-ride`) | road | unlabelled | authored (`map`) | None |
| Hougoumont | Chateau and farm (`hougoumont`), compound of 7 hexes | building | unlabelled | authored (`map`) | None for the footprint |
| Hougoumont | North gate (`north-gate` opening, open) | gate | sourced, inside the `map` label: "the open north gate is sourced" | `map` | Age of Revolution, *Closing the Gates at Hougoumont*; NAM, *Battle of Waterloo* ([37](37-first-five-selection-register.md) §2); both secondary and uncited |
| Concord | Road from the muster field to the North Bridge (`muster-road`) | road | unlabelled | authored: illustrative layout, not surveyed (`map`) | None |
| Concord | Road from the North Bridge to the town (`town-road`) | road | unlabelled | authored (`map`) | None. Which bank each force holds is reconstruction (`map.banks`, S47, S48, S49) |
| Concord | North Bridge (crossing cell, not a feature) | bridge | reconstruction: planks intact (`map.bridge`) | `map.bridge` | S47 |
| Pegasus Bridge | Road from Bénouville to the canal bridge (`benouville-road`) | road | unlabelled | authored: illustrative layout, not surveyed; no map sheet was read (`map`) | None ([52](52-pegasus-bridge-scenario-plan.md) §7) |
| Pegasus Bridge | Road between the bridges (`bridges-road`) | road | unlabelled | authored (`map`) | None |
| Pegasus Bridge | Road from the Orne bridge to Ranville (`ranville-road`) | road | unlabelled | authored (`map`) | None |
| Pegasus Bridge | Machine-gun emplacements, west bank (`west-mg-posts`) | works | sourced (`map.defences`); hex and cover authored | `map.defences` | S54 |
| Pegasus Bridge | Trench system, west bank (`west-trenches`) | works | sourced (`map.defences`); hex and cover authored | `map.defences` | S54 |
| Pegasus Bridge | Machine gun and anti-tank gun, east bank (`east-mg-post`) | works | sourced (`map.defences`); hex and cover authored | `map.defences` | S54 |
| Pegasus Bridge | Pillbox, east bank of the Orne (`orne-pillbox`) | works | unlabelled | `map.defences` says "the pillbox 'to the north' is not placed" | None |
| Pegasus Bridge | Canal bridge (`canal-bridge`, charges) | bridge | inferred: wired with charges (`bridge`) | `bridge` | S54, secondary |
| Hill 223 | Old trench on the hillside (`old-trench`) | works | unlabelled in `provenance`; a code comment in `battle/scenario_hill223.py` cites S40 and says hex and cover are authored | authored: schematic, not surveyed (`map`) | S40 narrative ([56](56-hill-223-scenario-plan.md) §7, "An old trench on the hillside") |
| Gergovia | Town wall and gates; midslope stone wall (terrain rows, not features) | wall | sourced (`map.walls`); values authored | `map.walls` | S60 VII.46, VII.47, VII.50 |

Every road in the catalog is illustrative: each entry's `map` label is authored, and no source locator places a road. The only sourced placements are the Hougoumont north gate (secondary, uncited), the Pegasus west- and east-bank defences (S54, hexes authored) and the Gergovia walls (S60, as terrain).

## 5. Findings

1. **No rendering or route defect in roads or buildings.** Every road draws as one continuous line, every routed road hex chain is gap-free, and `grid.path` keeps to every named road. Where a road's waypoints are not on one hex axis (Little Round Top's two roads, Hougoumont's north lane), a straight drawn segment clips the corner of a hex beside the routed chain by up to 3.0 px (about 3.4 m), under the 5 px half-width of the drawn casing.
2. **Bridges are not drawn.** Concord's and Pegasus's roads stop at each end of a bridge hex. The renderer draws no bridge (the Pegasus `bridge` feature has no branch in `BattleFeatures.render`; Concord's bridge is a crossing cell) and no water, so the road shows a one-hex gap at each crossing. Both entries are headless-only for that reason ([43](43-concord-scenario-spec.md) row 8, [54](54-pegasus-scenario-runs.md) §1).
3. **The Hougoumont compound, wall and gate are not drawn**; the building is one box at the chateau hex. This is already recorded as deferred in [42](42-hougoumont-scenario.md).
4. **Only Little Round Top and Hougoumont can be shown on the command desk** (`bootstrap.PLAYER_SCENARIOS`); the other entries' features are checked through the same data path, but no browser can open them.

## 6. Open questions for the owner

Features with no label in their entry's `provenance`:

1. Little Round Top: the entry has no `provenance` at all. Should its roads, buildings and breastwork carry an `authored:` label (doc 24 already calls them authored and illustrative)?
2. Hougoumont: the three lanes and the chateau footprint carry only the map-wide `authored` label. Is a source for the lanes or the compound outline wanted, or is the map-wide label enough?
3. Concord: both roads carry only the map-wide `authored` label.
4. Pegasus Bridge: the three roads carry only the map-wide label. The `orne-pillbox` works stand on the default map although the `scope` label says the Orne bridge belongs to the both-bridges variants, and `map.defences` says the pillbox "to the north" is not placed. Which pillbox is this, and what is its label?
5. Hill 223: `old-trench` is cited only in a code comment (S40). Should the entry's `provenance` carry it?
