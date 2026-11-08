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

pending PM
