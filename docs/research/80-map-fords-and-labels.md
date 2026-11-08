# 80 — Map fords, and map label collisions

**Date:** 2026-11-08. **Task:** bt-T16 (Architect 16:36Z, ar-T7a item 1). Follows [72](72-roads-buildings-slice-1.md) §9 (fords as marks; label collision), [75](75-playable-eras-slice-2.md) §8 (counters over the canal bridge label; works labels colliding at Pegasus) and [76](76-objective-ring-and-order-wording.md) §4. Presentation only: no engine rule, routing, sight or terrain data, edition, contract type or saved-game format changed.

## 1. Fords: no scenario records one

The engine accepts `crossing: "ford"` on a water cell (`scenario_checks.CROSSINGS`, `grid.passable`). Searched `apps/`, `packages/` and `docs/` for every scenario source:

| Where "ford" appears | What it is |
|---|---|
| `apps/poc/tests/test_poc13.py`, `test_poc13b.py` | Synthetic river terrain built inside the tests |
| `scenario_checks.py`, `grid.py`, `orders.py` | The rule and an order-refusal message |
| `scenario_cannae.py` | The Aufidus is water cells with no `crossing`; doc 63 §3 names a ford east of the Roman camp (Polybius 110.8–110.11) but no scenario cell carries it |
| Concord, Pegasus Bridge | Their only `crossing` cells are `"bridge"` |

No shipped scenario has a ford, so there is nothing to draw and no provenance to label. A mark invented for the purpose would carry a status no source supports, which the bt-D06 default forbids (every mark needs its entry in `static/feature-sources.js`). **Not built:** the ford mark, its legend entry and the code path for it. The brief said to stop after the search in this case; the label work below is independent of it and was done.

To draw one later, a scenario must record a ford cell and a table entry (`crossing:<pos>` key, status, basis). The bridge path already reads `crossing` cells from the briefing, so the change would be a second kind beside it. Cannae's ford needs bt-D07 (BCE dates) and a map-source ruling first.

## 2. Label collisions

### What was wrong

Each mark's draw function put its label where it had always sat (below a bridge, above a building, right of works, beside a gate, along a road). Nothing compared labels with each other or with the counters, which are drawn above the features. At Pegasus the canal bridge label and three works labels met; at Little Round Top a counter covered FIELDWORKS; at Hougoumont a counter covered the chateau label.

### The rule

Both desks use the same rule (`placeLabels` in `apps/poc/static/map-features.js` and `apps/web/src/features.ts`; `test/features.test.ts` holds the two outputs byte-identical, now also with counters in the way).

1. Each label has a list of candidate places in preference order. The first is where the label has always sat, so a map with no collision draws exactly as before. The rest go round the mark (below, above, right, left, then shifted in 14 px steps). A road adds spots along its line: above, below, then on the line, at 17 points.
2. Labels are placed in order of priority, then key: bridge, gate, building, works, road (a lower number first), then the mark key in string order.
3. A label takes its first candidate whose box meets no counter box and no label already placed. The box is the text estimated at 6.4 px a character (8.2 for capitals) at 11 px, plus margin.
4. A label with no free candidate is **hidden**: no `<text>`, and `data-label="hidden"` on its mark. The tooltip and legend line still name the mark and its status.

No state outside the rule is read, so the same inputs give the same places. Counter boxes: POC desk, each card (112 × 72) and anchor dot, from `UnitIcons.layout` (the card placement itself is unchanged; `render` was split into `layout` and `render`); TS desk, the 74 × 34 box on each own unit and contact. Both are the counters the view already draws, so what a side's view shows is unchanged.

### Results

On all five playable scenarios, at the start position, no label meets another label or a counter, and no label is hidden: Little Round Top 5 labels, Hougoumont 5, Concord 3, Pegasus Bridge 9, Hill 223 1. At Pegasus the Bénouville road label moved to the line (on it, left of the cards) and the works labels fan out; the canal bridge keeps its place. A road label is the likeliest to be hidden when counters crowd its road (Concord's muster road and Pegasus' Bénouville road were hidden until the on-line and extra spots were added).

**Zoom.** The POC desk's 2× view scales the overlay SVG as one piece, so overlap is the same in SVG space and the harness measures it on screen at both views. The TS desk has no zoom; its SVG scales as one piece too.

**Limit.** Placement runs at render time against the counters then drawn. When units move into a crowded place, a label may move or hide on the next render. The rule keeps no memory.

## 3. Checks

| Check | Addition |
|---|---|
| `apps/web/test/features.test.ts` | `label placement is deterministic, takes the first free place and hides a label with none`; `no feature label meets another label or a counter on the five playable scenarios` (also with a counter on every mark's hex); `the POC desk and this desk place labels alike with the same counters in the way` |
| `apps/poc/scripts/check_map_features.mjs` | The same rule cases through `BattleFeatures.placeLabels`; on the five scenarios, the real start counters (`UnitIcons`) against the drawn label text, with an independent narrower width estimate. A mark drawn alone now equals the mark in the full layer except for its label position |
| `apps/web/scripts/smoke-features.ts` `checkLabels`, called from `smoke-browser.ts` | Label and counter boxes measured in the page on each of the five scenarios; none meet; hidden count printed |
| `apps/poc/scripts/map_screenshots.mjs` `checkLabels` | The same at the fit view and 2× on each of the five scenarios, MapLibre active |

## 4. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/fords-labels-29cfd3e/` in the main checkout, for code head `29cfd3e` (base `fc3f9d6`). `MANIFEST.txt` lists the files; each gate log ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline`, `npm run typecheck` | exit 0 |
| `npm test` | web 79 of 79 (was 76), contracts 62 of 62 |
| `make smoke-web` | `SMOKE PASSED`; `labels: … none meet; 0 label(s) hidden` on all five scenarios |
| `make test-poc` | `Ran 795 tests … OK`, then every `smoke_ui` and map check; exit 0 |
| `make headless-poc` | winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as before |
| `make smoke-poc` | exit 0 |
| `node apps/poc/scripts/map_screenshots.mjs` | `HARNESS PASSED`; 10 of 10 views (5 scenarios, fit and 2×) none meet, 0 hidden |

`git diff --stat fc3f9d6 HEAD -- apps/poc/battle apps/poc/tests packages/contracts/src` is empty (`diff-stat-engine-contracts.log`).

**Digest comparison against `fc3f9d6`** (doc 74's `digests.py` and doc 76's `run_digests.sh`, unchanged): every headless catalog entry without timings, and desk play of all five scenarios to the end; `cmp` exits 0 for both (`run-digests.log`).

**Red first** (`red/`), the new checks on the previous sources: `npm test` 2 of 79 fail (`label placement …`: the shared first place was not taken in priority order; `no feature label meets …`: "a counter covers Southern track"); `check_map_features.mjs`: "a counter covers FIELDWORKS" at Little Round Top; `make smoke-web` fails at Hougoumont, "counter A1 meets label Hougoumont chateau and farm"; `map_screenshots.mjs` fails at Little Round Top, "counter U1 meets label FIELDWORKS". The red run added a stub `placeLabels` export to the old TS source so the test file would load; the stub is not committed.

**Mutations** (`mutations/`), both red, then restored: placed labels not recorded (TS), 5 of 79 fail; obstacles ignored (POC), `check_map_features.mjs` fails at "a counter covers FIELDWORKS".

**Screenshots.** POC desk: `screenshots/` (`pegasus-fit-grid-on.png`, `pegasus-zoom2x-grid-on.png` and the rest). TS desk: `smoke-web/` (`desk-pegasus-features.png` and the rest).

## 5. Deferred

- Fords as marks, until a scenario records one (§1).
- 2× view centring (Hill 223's ravine and shack off screen), as the task said.
- Gergovia's walls (bt-D07).
- Non-feature text (place labels, the HQ box, supply labels) is outside the rule.
- Roads whose label is hidden have no on-map name; if the owner wants one always shown, a short form is needed.

## 6. Review notes

code-critic at `6bd7718`: **APPROVE**, no CRITICAL or HIGH. The critic re-ran `npm test` (79 of 79), `tsc --noEmit` (exit 0) and `check_map_features.mjs` (all eight scenarios pass). It confirmed the engine and contracts diff is empty, the two desks share priority, candidates and hide rule, and `check_map_features.mjs` still fails on an added, removed or re-typed feature. A grep finds no ford code. Credential scan over `origin/main...HEAD`: clean.

Three LOW notes, not fixed (below the fix bar):

- The desk-parity test in `apps/web/test/features.test.ts` (lines 152-159) uses one scenario and two hand-placed boxes. Parity under each desk's real counter layout is not asserted.
- `wall` has a `PRIORITY` entry in both desks (`map-features.js:29`, `features.ts:69`), but walls carry no label, so the entry is unused.
- The evidence in `apps/poc/artifacts/fords-labels-29cfd3e/` is git-ignored and exists only in the main checkout.

## 7. Labels inside the map frame (bt-T23)

**Date:** 2026-11-08. **Task:** bt-T23. Branch `bt-t23-label-edge` from `774eaae`. Commits: `0d4339b` (tests, red), `5f553f4` (the rule), then this section. Presentation only: `git diff --stat 774eaae HEAD -- apps/poc/battle packages/contracts/src` is empty.

### What was wrong

The rule of §2 tested each candidate against counters and earlier labels, never against the map's edge. Doc 81 §11 found Hill 223's objective title, "Command post at the shack", cut at the left edge at the fit view and at 2×: the shack is in column 0 and the title was centred over it. Measured in the browser at `774eaae`, the edge also cut:

| Desk, view | Cut labels |
|---|---|
| POC, fit | Hill 223 title and subtitle (left edge); Pegasus "Road from the Orne bridge to Ranville" (right edge) |
| POC, 2× | Hill 223 title, subtitle and FIELDWORKS; Little Round Top North farm lane, Southern track, Farmstead; Hougoumont "Lane from the north gate to the ridge", "Ride through the wood"; Concord town road; Pegasus Bénouville road, Ranville road, FIELDWORKS |
| TS, fit | Pegasus Ranville road (right edge); Hill 223 "PATROL OBJECTIVE" (left edge, by the unit test on its markup) |

### The rule, extended

Both desks, the same code shape (`placeLabels`, `titlePlace`, `labelBox` in `apps/poc/static/map-features.js` and `apps/web/src/features.ts`):

1. `placeLabels(specs, obstacles, frame)`: a candidate is taken only if its box lies wholly inside `frame` {x0, y0, x1, y1}, besides meeting no obstacle and no earlier label. A label with no such candidate is hidden as before (`data-label="hidden"`, tooltip and legend kept). No frame, no test: the old behaviour.
2. Roads gain candidates, appended after all the old ones: the text ending 12 px left of each spot, above then below the line. Other marks already had places on each side (`around`).
3. The objective's title is not a feature label and is never hidden. `titlePlace(lines, x, hw, frame)` gives the place shared by its lines: centred (the old place), else starting at `x − hw`, else ending at `x + hw`; the first at which every line's box is inside the frame; centred if none is. `labelBox` takes a font size and letter spacing for it (21 px title and 10 px subtitle with 1.4 px spacing on the POC desk; the 11 px objective label on the TS desk). With the defaults it gives the same boxes as before.

Frames. TS desk: the map document's `0 0 width height` (the SVG viewBox); fit only. POC desk: feature labels use `BattleMapView.frame()`, the part of the 1080 × 840 scene the map frame shows. That is the whole scene at the fit view and in the SVG fallback, and the zoomed window at 2×. The desk now renders the map again on MapLibre's `moveend`, so after a zoom or pan the labels are placed for the new frame; a label whose mark is off screen is hidden by the rule instead of drawn cut. The POC title uses the whole scene; `mapFocus` keeps the moved title in the 2× focus box, so the camera keeps it in frame.

### Before and after

The first candidate is unchanged, so a label that fitted before has not moved. Fit screenshots byte-identical before and after: Little Round Top and Hougoumont. Changed at fit: Hill 223 (title and subtitle now start at the shack hex's left edge, `x − 25.5`), Pegasus (the Ranville road label moves onto the line), Concord (the town road label's estimated box ended 1.6 px past the right edge, so it took its next place). On the TS desk the Hill 223 objective label starts at the circle's left edge.

`before/` holds `774eaae`'s Hill 223 screenshots (fit and 2×; title cut), `after/` this head's. In the harness after the change: at fit and 2× on all five scenarios the title, subtitle and every drawn feature label lie inside the frame. Hidden by the rule: 0 at fit everywhere; at 2×, Little Round Top 1 and Pegasus 2 (marks off screen at that camera).

### Checks added

| Check | Addition |
|---|---|
| `apps/web/test/features.test.ts` | `a place outside the map frame is not taken, and a label with no place inside it is hidden`; `every feature label lies inside the map frame on the five playable scenarios, with and without counters`; `the objective's title stays centred where it fits and moves inside the frame at an edge`. The parity test now also runs Pegasus (the Ranville road at the east edge) with no counters and with a counter on the line, which sends the label to a flipped place, and compares `titlePlace` on Hill 223. Every catalog layer-parity comparison now passes the frame |
| `apps/web/test/render.test.ts` | `the objective label stays inside the map when the objective is in an edge column` (columns 0 and 23, and a middle one unchanged) |
| `apps/poc/scripts/check_map_features.mjs` | Frame cases through `BattleFeatures.placeLabels`; the five scenarios' labels, with their real start counters, inside 1080 × 840; Hill 223's title inside |
| `apps/web/scripts/smoke-features.ts` `checkLabels` | Every feature label and the objective label inside the SVG's content box, on all five scenarios |
| `apps/poc/scripts/map_screenshots.mjs` `checkEdges` | At fit and 2×, the title, subtitle and every drawn feature label inside `#map-wrap` clipped to the SVG |

### Gates

Evidence under the git-ignored `apps/poc/artifacts/label-edge-5f553f4/` in this worktree; `MANIFEST.txt` lists the files and each gate log ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline`, `npm run typecheck` | exit 0 |
| `npm test` | web 112 of 112 (was 108), contracts 85 of 85 |
| `make smoke-web` | `SMOKE PASSED`; on all five scenarios "every feature label and the objective label inside the map frame", 0 hidden |
| `make test-poc` | `Ran 817 tests … OK`; `Map features passed`; every smoke_ui and map check; exit 0 |
| `make headless-poc` | winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as before |
| `make smoke-poc` | exit 0 |
| `node apps/poc/scripts/map_screenshots.mjs` | `HARNESS PASSED`; 10 of 10 views inside the frame (above) |

**Digests against `774eaae`** (§4's `run_digests.sh` and doc 74's `digests.py`, copied unchanged), on a `git archive` of `774eaae` and on this tree: every headless catalog entry without timings (8) and desk play of all five player scenarios to the end; `cmp desk EXIT=0`, `cmp catalog without timings EXIT=0` (`run-digests.log`, `digests/`).

**Red first** (`red/`), the tests of `0d4339b` on `774eaae`'s sources: `npm test` cannot load `features.test.ts` (no `titlePlace` export); with a stub `titlePlace` that always centres (the old behaviour, not committed), 5 of 112 fail, among them "Road from the Orne bridge to Ranville crosses the map frame" and "objective 0,11". `check_map_features.mjs`: pegasus-bridge "Road from the Orne bridge to Ranville" crosses the map frame. `make smoke-web`: label "Road from the Orne bridge to Ranville" is cut by the map frame (at Pegasus). `map_screenshots.mjs`: "hougoumont 2x: feature label cut by the map frame: Ride through the wood". The table above comes from the final harness run on `774eaae`'s tree with its assertions turned into log lines (`before/map_screenshots.log`).

**Mutations** (`mutations/`), each red, then restored: TS, the frame test removed from `placeLabels`, `npm test` 5 of 112 fail; POC, the same in `map-features.js`, `check_map_features.mjs` fails, "pegasus-bridge: Road from the Orne bridge to Ranville crosses the map frame".

### Deviations

- The objective's title is outside the feature-label rule (§5): it has no priority and is never hidden. It shares the frame test and candidate idea through `titlePlace`, the same on both desks.
- The POC desk's 2× frame is the zoomed window, so the desk re-renders on `moveend`, and placement at 2× differs from fit. The brief named the frame test only; without it, nine labels were cut at 2× on four scenarios.
- After the red commit, three test edits. The harness's 2× check first allowed a label wholly off screen; with the zoomed frame it now requires every drawn label inside, and the "layer unchanged with the grid" baseline is taken per view. The parity test's Ranville case used the bt-T16 hand-placed boxes, under which the label is rightly hidden; it now uses one counter on the line. `smoke_ui.mjs`'s `BattleMapView` stub gained `frame`.
- Concord's town road label moved at fit although the browser drew it inside (the rule's width estimate is deliberately wide).
- At 2× on Hill 223, FIELDWORKS lies inside the frame but under the map's help strip ("Select a blue unit…"). Overlays inside the frame are not obstacles to the rule.

### Review notes (bt-T23)

code-critic at `958a9e4`: **APPROVE**, no CRITICAL or HIGH. The critic ran three checks, all passing: `apps/web` `npm test` (112 of 112), root `npm run typecheck`, and `check_map_features.mjs`. It confirmed:

- Both desks use the same frame test, the same candidates and the same order. The new road candidates come last, so a label that fits today does not move.
- `titlePlace` falls back to the centred place when no candidate fits. It never throws and never hides the title, which is the old behaviour.
- The POC re-render on `moveend` cannot loop, because `update` never moves the camera. The listener is added once in `init` and is removed by `map.remove()`.
- There is no diff under `apps/poc/battle` or `packages/contracts/src`.
- No test-helper edit made after the red commit weakens a check. The 2× check in `map_screenshots.mjs` is now stricter.

Credential scan over `origin/main...HEAD`: clean.

Two LOW notes, not fixed (below the fix bar):

- `apps/poc/static/app.js:83-87` places the objective title against the full scene, not the zoomed view. At 2× the title stays on screen because `mapFocus` keeps it in view, and `map_screenshots.mjs` checks that.
- `apps/poc/static/map-view.js:110` re-renders the whole map layer after each pan or zoom ends. This happens once per gesture, not once per move event.

Carried forward: overlay strips are not obstacles, so a label can sit inside the frame under the help strip. One example is FIELDWORKS at 2× on Hill 223.
