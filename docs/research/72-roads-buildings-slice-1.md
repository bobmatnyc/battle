# 72 — Roads and buildings on land maps, slice 1: compound, footprints, bridges and status

**Date:** 2026-11-08. **Milestone:** roads and buildings on land maps, slice 1, in the POC desk (`apps/poc/static`). Follows [24](24-map-features-and-digging-in.md) and [64](64-map-features-evidence.md). The TypeScript desk (`apps/web`) is out of scope and unchanged.

**No engine, scenario, edition or contract change.** Every file changed is under `apps/poc/static`, `apps/poc/scripts` or the root `Makefile`. `git diff --stat 6be1819 HEAD -- apps/poc/battle apps/poc/tests packages apps/web` is empty. §7 gives the digest comparison.

## 1. What the map now draws

Everything is drawn from the commander view's `map_features` (`features.known`, `engine.py` `view`) and the briefing cells of `/api/map` (`map_document`). The renderer is `static/map-features.js` (`BattleFeatures.render`). The same function serves the desk, `scripts/check_map_features.mjs`, `scripts/check_route_sight.mjs` and the screenshot harness.

| Mark | Drawn from | How |
|---|---|---|
| Road | `points`, routed `hexes` | Unchanged: one cased line through the authored points. The label now sits at the first middle point, longest segment first, whose text box keeps 30 px from every bridge, building and works centre. Before, it sat at the second waypoint, which for a two-point road is the bridge end or the map edge. |
| Bridge | Every briefed cell with `crossing: "bridge"`, and every `kind: "bridge"` feature | A deck with two parapets and splayed wing walls across the bridge hex. A road span, drawn with the road's own casing and fill, runs from each road end beside the bridge through its centre, so the road reads as continuous. A bridge known `destroyed` gets no span and a broken deck. `charges` adds a red dot and "· charges" to the label. |
| Compound and walls | A building's `compound` and `openings` | The yard is a tint over the compound hexes. A wall is drawn on every outward hex edge of the compound except the gate edges. |
| Gate | Each `openings` entry, state as the side knows it | `open`, `closing` and `forced` (passable, `gates.PASSABLE`): two posts with the leaves swung out. `closed` and `barred`: a bar on the edge, plus a cross-bar when barred. Labelled "North gate · open" (or the known state). |
| Building | `pos`, footprint size from the sources table | A footprint scaled to the map (§2), with a darker outline, a drop shadow and a ridge line. It is centred on the building hex and lies inside it. |
| Works | `pos`, `progress` | Unchanged symbol, now with a status tooltip. |

The compound's wall edges are computed from geometry: a compound hex's neighbour direction whose centre is not another compound hex. The check compares them with the engine's own `walls` from `gates.known_cells` (§5).

Water and marsh cells now have their own fill in `static/cartography.js` and the MapLibre style: water `#b9d3e3`, marsh `#d7e3cf`. Before, they drew as open ground, so a bridge stood on grass. Little Round Top and Hougoumont have neither, so their maps are unchanged.

## 2. Footprint scale rule

`BattleFeatures.footprint(metres, metresPerHex)`:

- **px per metre = hex-centre spacing (√3 × 25.5 px) ÷ `metres_per_hex`.** At 50 m a hex this is 0.883 px/m, the same scale as the map's 100 m bar.
- Each side is at least 6 px. The tooltip then says "enlarged to stay legible".
- A footprint that would leave its hex is scaled down to fit, and the tooltip says "reduced to fit its hex". The engine gives cover and sight obstruction to that one hex. None of the current footprints needs either adjustment.

The sizes in metres are authored and illustrative: farmstead 30 × 18 m, barn 26 × 14 m, Hougoumont chateau and farm buildings 40 × 26 m. They live in the presentation table, not the scenario entry. At the fit view the footprints are small but distinct: a brown fill with a dark outline and shadow, not a terrain colour. At 2× they read clearly with the grid on or off (§6).

## 3. Status of every mark: the presentation table

**Default ruling applied (pending the owner):** status is a presentation-only table, `static/feature-sources.js` (`BattleFeatureSources.forScenario(id)`), keyed by scenario id and then mark key. Mark keys are: a feature id; `<building>#walls` and `<building>#<opening>` for a compound; `crossing:c,r` for a bridge cell that is not a feature. Nothing is added to `features.setup`, scenario entries or contracts. Anything without a cited source is **illustrative**. Works dug during a battle (`briefed: false`) are labelled **reported in battle**, since they are game state, not a historical claim.

The status appears in the hex tooltip (`BattleFeatures.notes`, in each hex `<title>`), in each mark's own `<title>` and `data-status`, and in a legend under the map (`#feature-legend`, `BattleFeatures.legend`). The legend has a symbol key, a status key and one line per mark with its basis.

| Scenario | Mark key | Status | Basis (abridged; the full text is in the table) |
|---|---|---|---|
| Little Round Top | `north-lane`, `south-track`, `farmstead`, `barn`, `prepared-works` | illustrative | Authored POC content, doc 24; footprints authored |
| Hougoumont | `north-lane`, `west-lane`, `wood-ride` | illustrative | Entry map is illustrative, doc 42 |
| Hougoumont | `hougoumont` (footprint) | illustrative | No plan or survey read (doc 42); S44 names Hougoumont but places no building |
| Hougoumont | `hougoumont#walls` | illustrative | 7-hex compound authored (doc 42); no source gives the wall line |
| Hougoumont | `hougoumont#north-gate` | **sourced** | Open for friendly traffic: Age of Revolution, *Closing the Gates at Hougoumont, 1815*; NAM, *Battle of Waterloo* (doc 37 §2), both secondary and uncited; hex edge authored |
| Concord (both entries) | `muster-road`, `town-road` | illustrative | Entry map illustrative, doc 43 |
| Concord (both entries) | `crossing:12,10` North Bridge | **reconstructed** | S47, S49; planks intact is a reconstruction (entry `map.bridge`) |
| Pegasus Bridge | `benouville-road`, `bridges-road`, `ranville-road` | illustrative | No map sheet read, doc 52 §7 |
| Pegasus Bridge | `west-mg-posts`, `west-trenches`, `east-mg-post` | **sourced** | S54 (secondary); hexes and cover authored |
| Pegasus Bridge | `orne-pillbox` | illustrative | Unlabelled; doc 64 §6 question 4 |
| Pegasus Bridge | `canal-bridge` | **reconstructed** | Location S51 p. 1 para 2; charges inferred (S54, secondary; S51 p. 1 para 3) |
| Pegasus Bridge | `crossing:19,10` Orne bridge | **sourced** | Location S51 p. 1 para 2; not a bridge feature in this variant, so no state; hex authored |
| Hill 223 | `old-trench` | **sourced** | S40 narrative (doc 56 §7); hex and cover authored |

Gergovia and Cannae have no drawn mark. Gergovia's walls (S60 VII.46, VII.47, VII.50) are terrain rows with obstacle height, not features (doc 64 §4), so they are not drawn yet (§9).

"Sourced" here means a source attests the feature. In every case the hex, cover and drawn size are authored, and each basis says so.

## 4. Only the commander view is drawn

The renderer receives only the commander view and the briefing cells. The check builds a state where the truth differs from what the side knows. Every gate is `barred`, every bridge `destroyed`, and an unbriefed `works-secret` is dug, none of it reported. The drawn layer is byte-identical to the briefed layer. `tests/test_map_features_catalog.py` `test_hill_223_commander_and_replay_show_only_reported_works` still covers delayed works reports in the view and replay. The renderer adds no data path.

## 5. Checks

| Check | What it asserts |
|---|---|
| `scripts/check_map_features.mjs` (extended) | For every catalog entry, from the commander view: road checks as in doc 64, read from the full layer. Each footprint equals `footprint_m × spacing / metres_per_hex` (6 px floor), is centred on and inside its hex, is not a terrain fill, and halves when `metres_per_hex` doubles. At Hougoumont: one yard ring per compound hex. The drawn walls plus any shut gate equal the engine's `walls` for the known gate state, both as briefed (open: 17 wall edges, gate gap) and with the report set to `closed` (18). The gate is drawn and labelled in the known state on the edge between its inside and outside hexes. Every crossing and bridge feature has a deck. Two road ends sit beside it, and a span drawn like the road joins them through the bridge centre; a destroyed bridge has no span. Every mark has a sources entry, and the table lists exactly the drawn marks. Status and basis appear in each tooltip and in the legend. Sourced and reconstructed marks cite an S-id or named source. Unseen truth is not drawn. The grid toggle styles hex outlines only. |
| `scripts/check_route_sight.mjs` (new; in `make test-poc`) | Per player scenario, through `RulesSimulation`: §5.1 |
| `scripts/smoke_ui.mjs` (updated) | The desk loads `feature-sources.js`, draws footprints and the legend, and the grid-toggle test uses the page's own `renderFeatures()`. At Hougoumont the compound wall, the sourced open north gate and its legend line are drawn. |

Each check was shown able to fail. Nine single mutations each made their check exit 1 (`mutations.log`):

- `check_map_features.mjs`: one wall edge dropped; gate always drawn open; span stopping at the bridge centre; the old fixed 32 × 22 px box; a sources entry removed; status removed from the tooltip.
- `check_route_sight.mjs`: footprint drawn 40 px off its hex; `grid.cost` ignoring road edges; building obstacle height set to 0.

### 5.1 Route and sight result

```
Route and sight passed:
  little-round-top: U1 22,10->12,7 along north-lane in 11 steps (11 over road edges) by turn 16; sight 6,3->8,3 blocked by farmstead at 7,3, clear without it
  hougoumont-north-gate: A1 11,9->12,1 along north-lane in 8 steps (7 over road edges) by turn 13; sight 11,8->11,13 blocked by hougoumont at 11,10, clear without it
```

- **Route.** A move order goes through normal delivery, and the clock advances through `RulesSimulation.apply`. Every `unit_moved` step after joining the road goes to the next road hex over a `road_neighbors` edge. At Hougoumont the first step, gateway (11, 9) to the lane (11, 8), is ordinary ground: entering a road from off it earns no discount (doc 24). At Hougoumont the route also equals `grid.path` on the briefing cells. At Little Round Top, U1 is placed at the lane's east end as a test arrangement; the scenario is unchanged. The drawn road line crosses every hex the unit moved through.
- **Sight.** `recon.sees` is false along each line and true with the building hex's obstacle height removed. The building hex is the only obstacle on the line. The drawn sight segment crosses the drawn footprint, which is centred on that hex, and no other footprint.
- Annotated renders: `little-round-top-route-sight.svg` and `hougoumont-north-gate-route-sight.svg` (§6).

## 6. Evidence

All under the git-ignored `apps/poc/artifacts/roads-buildings-1-9a193a2/`, for code head `9a193a2`; `MANIFEST.txt` lists every file.

- Gate logs: `make-test-poc.log`, `make-headless-poc.log`, `make-smoke-poc.log`, `npm-ci-offline.log`, `npm-typecheck.log`, `npm-test.log`, `make-smoke-web.log`, `harness.log`, `route-sight.log`.
- Screenshots (`screenshots/`, headless Chrome, device scale 2, MapLibre active):
  - `little-round-top-{fit,zoom2x}-grid-{on,off}.png` and `hougoumont-{fit,zoom2x}-grid-{on,off}.png`;
  - `*-legend.png` and `*-hex-tooltips.txt`, the native tooltip text a screenshot cannot show;
  - read-only renders `concord-north-bridge-render.{png,html}`, `pegasus-bridge-render.{png,html}`, `hill-223-patrol-render.{png,html}`;
  - the route/sight SVGs.
- Fault cleanup (`faults/`; rerun after the review fix, §6.1): `throw`, `sigint`, `poc-not-ready` (exit 1); `deadline` at 3 s (exit 1); `no-browser` (exit 3, BLOCKED). Every run ends with `cleanup: POC pid … gone; browser group … gone; profile removed; database dir removed`. The first deadline attempt used 8 s; the whole run finished inside it and passed, so it was rerun at 3 s.
- `mutations.log` with `mutate.py`; `digests-base-6be1819.txt`, `digests-head-9a193a2.txt` with `digests.py`.

The harness is `scripts/map_screenshots.mjs <dir>`. It runs offline on a temporary SQLite file and a free port. No provider credentials reach the POC; `--offline` uses the scripted commander. It switches to Hougoumont through the desk's own picker and Reset. The picker still lists only `little-round-top` and `hougoumont-north-gate`, and the harness asserts this. The headless maps are rendered from self-contained pages that inline the shipped `cartography.js`, `feature-sources.js`, `map-features.js` and `style.css`. Exit 3 means no browser ran: BLOCKED, never a pass. It shares the TS smoke's approach (process group, one deadline, profile removal), reimplemented in plain JS so `apps/poc` stays independent of `apps/web`.

### 6.1 Review fix: signals during cleanup (`6f210a6`)

The review found that `process.once` for SIGINT and SIGTERM let a second signal during cleanup kill the harness before the detached browser group stopped. SIGHUP had no handler at all. The harness now listens with `process.on` for SIGINT, SIGTERM and SIGHUP for the whole run. The first signal starts cleanup; later ones are ignored while it runs. Write errors on stdout and stderr are ignored, so a closed terminal cannot end the run before cleanup. The synchronous `python3` child that builds the headless map data has a 60 s `timeout` and fails on `r.error`, because it blocks the deadline and the signal handlers while it runs.

Evidence is under `apps/poc/artifacts/roads-buildings-1-6f210a6/` (`MANIFEST.txt`):

- `make-test-poc.log`: `Ran 744 tests … OK`, all JS checks passed, `EXIT=0`. `harness.log`: passed, `EXIT=0`, with fresh screenshots in `screenshots/`.
- `faults-{throw,sigint,poc-not-ready,deadline,no-browser}.log`: the same five fault runs as §6; every one reports its processes gone and the profile removed.
- `signals/`: `signal_driver.mjs` starts the harness, waits for its browser, sends signals, then lists leftover processes and checks the profile.
  - Against the old code (`de26550`): a second SIGINT 5 ms after the first killed the harness by signal, leaving the POC and the profile (`old-double-sigint.log`). SIGHUP killed it, leaving the POC, the browser and the profile (`old-sighup.log`). The driver then removed what was left.
  - With the fix: double SIGINT at 5 ms and at 0 ms, and SIGHUP, each exit 1 after `cleanup: … gone; … gone; profile removed; database dir removed`, with no leftover process (`new-*.log`).
  - At 50 ms the old code's cleanup had already finished, so that gap shows nothing; the 5 ms runs are the ones recorded.

`make headless-poc`, `make smoke-poc`, the npm gates and `make smoke-web` were not rerun: the fix changes only the harness script. Their logs for `9a193a2` stand.

## 7. Editions, replay digests and fixtures unchanged

- No file under `apps/poc/battle`, `apps/poc/tests`, `packages` or `apps/web` changed. The pinned digest tests (`test_contact`, `test_gates`, `test_batch_store` and others) pass in `make test-poc`: `Ran 744 tests … OK`.
- `digests.py` hashes each headless entry's opening state, commander view and, where the generic scripted loop fits, full scripted play. It ran on a `git archive` of `6be1819` and on `9a193a2`. The outputs are byte-identical (`cmp` exit 0). Concord's play is `n/a`: the generic loop orders a water hex, at base and head alike.
- `make headless-poc`: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions).

## 8. Findings

1. **Walls do not block sight in the engine.** Only the chateau hex carries obstacle height (8 m). The other six compound hexes and the wall edges stop movement and couriers (`gates.walls`) but not `grid.visible`. The drawn wall is a movement barrier, not a sight barrier. The sight check therefore uses the building.
2. **A bridge hex is not road for movement.** Roads stop at each bank, and the bridge hex costs its own `move_cost` (100 at Concord and Pegasus, 300 in the lifted-planks variant). The drawn span shows the road's continuity only; the bridge tooltip at Concord says so.
3. **Counters can cover feature labels.** At 2× zoom the Hougoumont counters cover part of the "North gate · open" label, and at Little Round Top U1 covers "FIELDWORKS". The legend and hex tooltips still carry each mark's name and state. Unit counters are drawn above features by design.
4. **The Orne bridge is drawn from its crossing cell** in the default Pegasus variant, which declares only the canal bridge as a feature. It has no state and stays passable.

## 9. Deferred

- The TypeScript desk (`apps/web`): no map features yet.
- Fords as features: `crossing: "ford"` cells are not drawn as a mark.
- Redrawing the illustrative headless roads (Concord, Pegasus) from a map source.
- Gergovia's walls as features: they are terrain rows (`map.walls`, S60), not `map_features`. Drawing them needs a feature form or a renderer branch for wall rows.
- Label collision with unit counters, and between works labels (three Pegasus works sit within two hexes).
- Moving the status table into scenario data if the owner rules so; that would need an edition and fixture decision.

## 10. Owner questions

Doc 64 §6 questions 1 to 5 stay open: Little Round Top provenance labels; sources for the Hougoumont lanes and compound outline; the Concord roads; the Pegasus roads and which pillbox `orne-pillbox` is; whether Hill 223's `provenance` should carry S40. New:

6. Should status live in scenario data, the default ruling's alternative, rather than the presentation table?
7. Are the authored footprint sizes (30 × 18, 26 × 14, 40 × 26 m) acceptable as illustrative, or should a building be drawn as several footprints, for example Hougoumont's chateau, barn and chapel?
8. Should compound walls block sight (an engine rule and edition change), given that the map now shows them?
