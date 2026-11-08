# 71 — TypeScript command desk, slice 2: the order catalog, the unit card, dispatches and scenario choice

**Date:** 2026-11-08. Follows [70](70-ts-desk-slice-1.md). Python stays the reference: no file under `apps/poc` changed, the POC's tests pass and the headless replay is identical. `apps/poc/static` stays the playable desk.

## Fixes from the slice 1 review

1. **The relay serves only the desk's routes.** `apps/web/server/desk-server.ts` relays these and nothing else (`ROUTES`):

   | Method | Route | Use |
   |---|---|---|
   | GET | `/api/state` | commander view (no query) |
   | GET | `/api/map` | terrain and setting of the current game |
   | GET | `/api/scenarios` | player-facing scenario catalog |
   | POST | `/api/orders` | one order |
   | POST | `/api/clock` | start and pause |
   | POST | `/api/new` | start a scenario |

   Any query that asks for a God view (`view` other than `commander`, or any value `god`, case-insensitive and URL-decoded) and any path naming `export` get 403. Other `/api/*` routes get 404, and a wrong method gets 405. A refused request never reaches the POC. The relay forwards the path only and drops the query. Test: `only the routes the desk uses are relayed; others never reach the POC`, `a God view or an export is refused with 403 and never relayed`.
2. **One deadline over the whole smoke run** (`SMOKE_DEADLINE_MS`, default 240 s, `withDeadline` in `scripts/smoke-support.ts`). When the deadline passes, the run fails with exit 1. A 3 s unref'd exit timer stops work left pending after the deadline from holding the process open. Chrome starts in its own process group, and the run stops the whole group (SIGTERM and SIGCONT, then SIGKILL), so a stopped (frozen) browser and its helper processes end too. `SMOKE_FREEZE_BROWSER=1` forces this case: it sends SIGSTOP to the browser once its page is open, which leaves the DevTools socket open with no reply.
3. **The temporary Chrome profile is removed on every exit path.** It now lives in its own `battle-desk-profile.*` directory outside the artifacts. A single cleanup runs from `finally` and on SIGINT/SIGTERM. The browser is handed to cleanup as soon as it is spawned, before `launch` waits for "DevTools listening", so an interrupt or the deadline during launch stops its process group before the profile is removed; once cleanup has begun, nothing more is started. The artifacts directory keeps only the screenshots and `battle.sqlite`; the run prints what it kept.
4. **A served module that exists but fails to load or strip** gets a 500 with the reason, for example `broken.ts could not be served: TypeScript enum is not supported in strip-only mode`. A missing module is still a 404.
5. **Node >= 24.2** is declared in `engines` in both `package.json` files. `make web` and `make smoke-web` run `apps/web/scripts/check-node.mjs` first. It is plain JavaScript, so an old Node can run it, and it exits 1 with the reason. The server itself also exits 1 when `import.meta.main` is undefined.
6. **A POST that outlives the relay timeout.** The relay answers 504 with `outcome: "unknown"`. It answers 502 with the same marker when the POC drops a reply or any connection error other than a refused connection occurs; in those cases the POC may already have committed. The desk then re-reads state rather than show a plain failure (`src/commands.ts`). After an order, it reports either the order now on record (`… did take the order: O3, U1 hold_fire, en route.`) or that the outcome is unknown and no new order shows. After `/api/new`, a new game is reported as started; the same game is reported only as "the same battle so far; a new battle may still start", because the POC may still commit after a 504. If the re-read itself fails, the notice stays `unknown`, says the re-read failed, and tells the player to check the order list (or re-read the battle) before sending again. The notice has its own `unknown` style.

   The terrain is tagged with the game it belongs to. Every re-read fetches the map whenever the view's game differs from that game, so a new battle whose map read failed is repaired on the next re-read, and the header, map and counters never describe two different games.

   **Timeout: 120 s** (was 30 s). An order POST can queue behind `BattleService.clock_step`, which holds the POC's lock during the computer commander's turn. With a reasoning effort, the provider timeout is 90 s (`EFFORT_TIMEOUT` in `apps/poc/battle/config.py`; 18 s without one). 120 s covers that call plus the save. A GET does not take that lock, so in practice only a stuck POC waits the full time; the desk's poll does not start a second request while one is pending. The desk's wait for a paused clock's interval to finish is raised from 6 s to the same 120 s.

## Features

- **Full player order catalog.** The order list is the view's `order_templates`, which is `orders.catalog` for the battle. Every kind there is offered, with its intent and effect. Little Round Top (poc-13) offers hold, move, rest, retreat, resupply, recon, dig in, hold fire and open fire; Hougoumont adds Close the gate. `orderBody` (`src/orders.ts`) builds the one input each kind needs. A `hex` template sends the clicked destination and waits for one; `none` templates, the fire postures among them, send `destination: null`; `supply` sends `destination: null` because the POC picks the nearest compatible ammunition point, and the form lists the briefed points. The POC's order keys are `unit_id`, `stance` and `destination` only (`engine.validate_order`), so posture is a stance, not a separate input. Every refusal shows the server's `error` text as sent; the desk checks no rule of its own beyond not sending to a unit the view reports routed, lost or merged, as the POC desk does. Standing orders, split and combine use other endpoints and are deferred.
- **Scenario choice.** The header lists `GET /api/scenarios` (new contract `scenarioList`, fixture recorded by `record.py`), which holds only `PLAYER_SCENARIOS`: Little Round Top and Hougoumont, the north gate. Headless-only entries never appear there. "Start battle" pauses the clock if needed and posts `/api/new` with the scenario id at the desk's cursor, then reads `/api/map`. The header (campaign, title, local time, calendar date, location), map, counters, order catalog and mission brief then follow the new game. Hougoumont reads `11:20`, `Sunday, June 18, 1815`, `Hougoumont · Waterloo, Belgium`.
- **Unit card and dispatches.** Selecting an own counter shows its card from the commander view: strength / initial, type, skill, energy (100 − fatigue), morale, ammunition, suppression, fatigue, entrenching tools and fire posture when reported, status, mission and target, the last mission result and local judgment, and the report's battlefield time. A Dispatches list shows `dispatches`, newest first, with receipt times. The order list adds the template label and, while en route, the expected delivery time.
- **Information boundary.** Unchanged: every state reply passes `readCommanderState`, which refuses a God view. The relay now also refuses a God-view request or an export before the POC sees it. Enemy markers still come only from `contacts`.

## Tests and the browser check

`npm test`: web 58, contracts 58. New tests cover the relay allowlist and refusals, the 500 for an unloadable module, the 504/502 unknown outcome, the Node check, every template's body, the unknown-outcome re-read (re-read succeeds, re-read fails, plain refusal, for orders and new battles, with a fake `DeskApi` in `test/commands.test.ts`), terrain following the view's game, the unit card, dispatches, the order form, the scenario options, the deadline, process-group stop, browser registration during launch, and profile removal. With `stop` changed to signal the main process only, the group test failed, because a frozen grandchild survived. The command and launch tests failed on the code before the fix round (logs below).

`make smoke-web` now also checks, with real pointer clicks on isolated SQLite and free ports:

1. the desk offers the POC's whole order catalog, and the unit card matches the POC's commander view (strength, morale, ammunition, energy, status);
2. a move and a Hold fire order are accepted and held by the POC (Hold fire with `destination: null`), and the dispatches list the order;
3. a Rest order is refused with the server's text "Pause the clock and let the current interval finish before issuing commands." after the clock is started outside the desk, as the POC desk beside it could do. The POC's order count does not change. The stale-cursor refusal ("Battle changed…") is kept;
4. a switch to Hougoumont from the desk's scenario control: the POC's game is Hougoumont, and the header, title, counters, hex count and catalog follow; the gate party's unit card matches; Close the gate is accepted.

A `validate_order` refusal (400) cannot be reached through ordinary clicks in these two scenarios: every offered kind is valid for every reported unit, every hex is passable, and both have a compatible ammunition point. The pass-through of 400 text is covered by `a server refusal keeps its status and text`.

**Evidence, run against `4a1aa52`** (git-ignored, in the main checkout): `apps/poc/artifacts/ts-desk-2-4a1aa52/` holds:

- `typecheck.log`, `npm-test.log` (web 58, contracts 58), `smoke-web.log` (`SMOKE PASSED`), `desk-accepted.png`, `desk-hougoumont.png`;
- `launch-faults.log` with its scripts `launch-faults.sh` and `fake-chrome.sh`. These are three interrupted launches: a 6 s deadline while a hung browser never opens DevTools, SIGINT during that hung launch, and SIGINT while real Chrome starts. Each run exits 1, and the process check after each finds no process with a `battle-desk-profile`, no browser helper, no smoke POC and no profile directory;
- `forced-failure.log` with `forced-failure.sh`. A frozen browser with a 20 s deadline fails in 20 s, and a POC that never reports ready fails in 3 s. A missing browser exits 3 (`SMOKE BLOCKED`), and Node 24.1.0 is refused. Nothing is left after either failure;
- before-fix logs: `launch-faults-before-fix.log` (the same interrupted launches left the fake browser and its helper running after the profile was removed), `commands-test-before-fix.log` (5 of 9 command tests failed) and `launch-test-before-fix.log` (both launch tests failed).

The first round's evidence, against `4acc325`, is in `apps/poc/artifacts/ts-desk-2-4acc325/`. It includes `test-poc.log` (744 tests OK plus the UI scripts) and `headless-poc.log` (replay `identical`); the fix round changed nothing those cover.

## How to run

As in [70](70-ts-desk-slice-1.md#how-to-run-it): `make poc-offline`, then `make web` (Node >= 24.2).

## Deferred

- Standing orders, split and combine, recommendations (accept/dismiss), staff chat and the twin.
- Replay, God Mode, export.
- Field glass, unit images, roads, buildings and works, elevation shading, MapLibre. Counters on adjacent hexes overlap (visible at Hougoumont); the click still hits the counter on top, and the smoke test checks the hit.
- Command location and disruption display, troop analysis.
- A browser check of the unknown-outcome path against a real slow POC; it is covered by relay and model tests only.
- From the review, left for a later change: `stop()`'s second group SIGKILL after exit could reach a reused process-group id; no test yet shows the relay drops the query string; while an order awaits acknowledgement, its delivery estimate shows only in the dispatches.
- Localisation beyond `display_locale`; keyboard selection of counters.
- Any port of rules out of Python.
