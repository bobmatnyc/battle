# 73 — TypeScript command desk, slice 3: map features, the grid toggle and commander replay

**Date:** 2026-11-08. Follows [71](71-ts-desk-slice-2.md) and [72](72-roads-buildings-slice-1.md). Python stays the reference: no file under `apps/poc` changed (`git diff --stat e3a8ec4 HEAD -- apps/poc` is empty), the POC's tests pass and the headless replay is identical. No engine, scenario or edition change.

## 1. Map features

The desk draws the commander view's `map_features` as the POC desk does after doc 72: one cased line per road with its label, a bridge deck carrying the road span, the Hougoumont compound (yard and walls on every outward hex edge except the gate), the gate in the state the side knows, building footprints scaled from `metres_per_hex`, works, and the water and marsh fills. Each mark has its status (sourced, reconstructed, illustrative, or reported in battle for works dug in battle) in its own tooltip, in each hex tooltip it covers, and in a legend under the map (`#feature-legend`): a symbol key, a status key and one line per mark with its basis.

- **Renderer.** `apps/web/src/features.ts` is a typed port of `apps/poc/static/map-features.js`. `test/features.test.ts` loads the POC's renderer and table with `node:vm` and asserts that the TypeScript layer, legend and hex notes are byte-identical to the POC's for every catalog entry (Little Round Top, Hougoumont, both Concord entries, Pegasus Bridge, Hill 223, Gergovia, Cannae), for the gate shut and barred, for works dug in battle and for a blown bridge. A change to either renderer fails that test. With the gate leaf length changed by 1 px, two of its four tests failed (`mutation-features-gate-leaf.log`).
- **Status table: one copy.** The table stays `apps/poc/static/feature-sources.js`, unchanged in shape and content. The desk server serves that one file at `/poc/feature-sources.js`, and `index.html` loads it as a classic script before the desk module. Its top-level `const BattleFeatureSources` is a global binding, which `src/main.ts` reads and passes to the desk. `src/feature-sources.ts` reads each scenario's table through a checked reader that refuses an unknown status, an unknown key or a bad footprint size. A test checks that no basis text from the table appears in `apps/web/src`. If the script does not load, the desk says so in the notice and every mark reads "Status not recorded"; it does not guess a status.
- **Order.** Hexes, objective, features, route, contacts, counters. Counters stay on top, as in the POC (doc 72 §8 finding 3).

### Contract: `map_features`

`packages/contracts/src/features.ts` types the commander view's `map_features` as a union by `kind`: `road` (`points`, `hexes`), `building` (`pos`, `cover`, `height`, and `compound` with `openings` for a walled building), `fortification` (`pos`, `cover`, `progress` 0–100, and the effort keys and `base_cover` of works dug in battle), and `bridge` (`state` in `intact`, `charges`, `destroyed`). Gate `state` must be one of `gates.STATES`. Each kind's keys are fixed: an unknown kind, an unknown key, a missing key or a gate without its compound is refused with the JSON path. `commanderView` now uses it; the God view's `map_features` stay untyped JSON, because the desk never reads a God view.

`record.py` now also writes `fixtures/map-features.json`: each catalog entry's opening commander `map_features`, read the way `apps/poc/scripts/check_map_features.mjs` reads them, with the map's `metres_per_hex` and its bridge cells. Re-recording rewrote no other fixture. `test/features.test.ts` (contracts) checks every entry, the 12-interval state fixture, one mutation per rule, and works dug in battle with a gate in each of the five states.

## 2. Grid toggle

"Hex grid" (`#grid-toggle`, `aria-pressed`) adds `no-grid` to the map. The one rule it selects, `#map.no-grid .hex:not(.destination)`, sets `stroke-opacity: 0`. Fills, features and counters stay. The chosen destination keeps its outline.

## 3. Commander replay

"Replay battle" replays the current battle in the player's commander view only. It uses the POC's own `GET /api/history?game_id=` and `GET /api/replay?game_id=&revision=`, the endpoints the POC desk's replay uses.

- **Opening.** The desk pauses the live clock and waits for the interval to finish, as the POC desk does. It then reads the history and shows the most recent record.
- **Stepping and scrubbing.** "Step back" and "Step forward" move one recorded revision; the slider scrubs to any revision. The header (time, date, location) follows the replayed view's interval under the timeline rule. The replay bar reads "Recorded commander view · Thursday, July 2, 1863 · 16:30:30", and the slider's `aria-valuetext` is the same; no revision or turn is shown. The map, features, counters, orders, dispatches, contacts and mission are the recorded view's.
- **Orders closed.** While replaying, Send order, the order kind, the clock, the scenario choice and Start battle are disabled. A map click selects a counter to read its card but sets no destination; a hex click says orders are disabled. `ordersOpen` (`src/replay.ts`) is the single test of whether orders are allowed.
- **Leaving.** "Return to live" re-reads the live state and redraws it; the live controls return.
- **Boundary.** The relay forwards `game_id` and `revision` only (`QUERY_KEYS` in `server/desk-server.ts`). A `side` or `view` key on these routes is refused with 403. A missing, repeated or malformed key, or any other key, is refused with 400, and a refused request never reaches the POC. The POC would otherwise serve the opponent's commander view after the battle ends (doc 65); the desk never asks for it. Each replay reply passes `readCommanderReplay`, which refuses a God view, and `src/replay.ts` refuses a view whose `side` is not the player's.

Playing the replay at a speed is not in this slice (§7).

## 4. Fixes carried from earlier reviews

1. **The query string is dropped** on the desk's live routes. Test: `the query string is dropped on the desk's live routes`. With the relay changed to forward the query, that test failed (`mutation-relay-forwards-query.log`).
2. **A new battle whose map read fails** is reported as started, not refused: "New battle started: … Its map could not be read (…); the desk will read it again." The desk holds the new view with the old terrain still tagged with the old game. Until the map is read, it draws no map or header for that terrain (`--:--`), keeps orders and replay closed, and polls once a second until the re-read succeeds. Test: `after a new battle whose map read fails, the next re-read fetches the new game's terrain` (it failed on the code before the fix: `red-web-replay-commands.log`).
3. **The hung-browser tests remove their temporary directory in `finally`** (`withHungBrowser`), and the silent-browser test does the same. Test: `the hung-browser helper removes its directory even when the test body fails`. `$TMPDIR` held 31 `battle-hung-browser.*` and `battle-silent-browser.*` directories from earlier runs; a full `npm test` now adds none.

The smoke run's signal handling now matches the POC harness after doc 72 §6.1: `process.on` for SIGINT, SIGTERM and SIGHUP for the whole run, and write errors on stdout and stderr ignored.

## 5. Tests and the browser check

`npm test`: web 73, contracts 62. New or changed web tests cover the feature layer, legend and notes (POC parity), footprints, the status reader, features in the map markup and hex tooltips, water and marsh fills, the relay's replay allowlist and query dropping, the served status table, replay opening, stepping, clamping and side refusal, `ordersOpen`, the history and replay request URLs, and the new-battle map failure.

`make smoke-web` (real Chrome, its own POC on a temporary SQLite file and free ports, `TZ=Pacific/Kiritimati`) now also checks:

1. **Little Round Top features.** Every road the POC's view holds is drawn as one line through its points. Each footprint's width equals `footprint_m × √3 × radius ÷ metres_per_hex` from the page's own table. Each building hex's tooltip names the building and its status. The legend has one line per drawn mark, in order, with the table's status. Each mark's `data-status` and tooltip agree.
2. **Grid toggle.** A real click turns the hex stroke opacity to 0 and keeps every mark drawn with a non-zero box; a second click restores it.
3. **Replay.** After the clock has run and the POC has moved on, the desk opens the replay at the live time (16:31). It steps back until the header reads an earlier interval (16:30:30); the counters there are the POC's own `/api/replay` units for that revision. It scrubs to 16:30, steps forward, and checks that orders, clock and new battles are disabled and that a hex click sets no destination. It returns to live at 16:31. The POC's revision, order count and paused clock are unchanged, and the page shows no turn or revision.
4. **Hougoumont features.** The three lanes and the chateau footprint are drawn. The compound wall has 17 outward edges with the gate edge open. The gate is drawn `open` and labelled "North gate · open". Its legend line reads Sourced. The grid toggle keeps all six marks.

Both smoke additions were shown able to fail. With a CSS rule hiding the features when the grid is off, the run failed at "north-lane still visible". With the desk drawing the live view during replay, it failed waiting for header 16:30:30 (`smoke-mutation-*.log`).

## 6. Evidence

Git-ignored, in the main checkout: `apps/poc/artifacts/ts-desk-3-932492a/`, for code head `932492a`. `MANIFEST.txt` lists each file, its command and exit code.

- `npm-ci-offline.log`, `npm-typecheck.log` (exit 0), `npm-test.log` (web 73/73, contracts 62/62), `make-test-poc.log` (`Ran 744 tests … OK` plus the JS checks), `make-headless-poc.log` (replay `identical`, 63 revisions), `make-smoke-web.log` (`SMOKE PASSED`), `poc-unchanged.log` (empty diff under `apps/poc`).
- `screenshots/`: `desk-lrt-features.png`, `desk-lrt-grid-off.png`, `desk-replay.png`, `desk-hougoumont-features.png`, `desk-hougoumont-grid-off.png`, and the slice 2 shots `desk-accepted.png` and `desk-hougoumont.png`.
- `fault-cleanup.log` with its script `scripts/fault-cleanup.sh`: a 4 s deadline mid-run, an 8 s deadline on a frozen browser, SIGINT 3 s after the browser starts, two SIGINTs 5 ms apart, SIGHUP, and SIGINT during the browser launch. Each run exits 1. The check before each signal finds the run's processes (13, or 3 during launch); the check after finds no POC, browser or smoke process and no profile directory left.
- Before-fix and mutation logs: `red-contracts-features.log`, `red-web-features.log`, `red-web-render.log`, `red-web-server.log`, `red-web-replay-commands.log`, `mutation-features-gate-leaf.log`, `mutation-relay-forwards-query.log`, `smoke-mutation-grid-hides-features.log`, `smoke-mutation-replay-draws-live.log`.

## 7. Deferred

- Replay playback at a speed (the POC desk's play button); this slice steps and scrubs only. The opponent's replay after the battle ends stays out of the desk by design.
- While replaying, the order help still describes the selected kind ("Click a destination hex…"), although sending is disabled.
- From doc 72: fords as marks, Gergovia's walls, label collisions with counters and between works labels, moving the status table into scenario data (owner question 6).
- From doc 71: standing orders, split and combine, recommendations, staff chat and the twin; God Mode and export; field glass, unit images, elevation shading and MapLibre; command location and disruption display, troop analysis; a browser check of the unknown-outcome path against a slow POC; `stop()`'s second group SIGKILL after exit; the delivery estimate while an order awaits acknowledgement; localisation beyond `display_locale`; keyboard selection of counters.
- Any port of rules out of Python.
