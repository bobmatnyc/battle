# 70 — TypeScript command desk, slice 1: Little Round Top against the Python POC

**Date:** 2026-11-08. **Handoff item:** "Portable UI path: Build new command desk/contracts in TypeScript, retain current Python/SQLite rules and saves as reference." [67](67-typescript-contracts.md) built the contracts; this is the first desk slice on them. Python stays the reference: no file under `apps/poc` changed, and `apps/poc/static` stays the playable desk.

## What the slice covers

`apps/web` is a TypeScript desk that plays the running POC's current battle as the player's commander. It was built and checked on Little Round Top only.

- **Reads** `GET /api/state` (the commander view) and `GET /api/map` (terrain and calendar setting), each through a contract reader.
- **Draws** an SVG hex map: one hex per map cell, coloured by terrain; the objective ring; one counter per own unit (strength and type, then skill, energy and morale, with energy = 100 − fatigue, as [29](29-unit-counters-and-readiness.md)); one dashed counter per contact.
- **Header** per the AGENTS.md timeline rule: scenario location, calendar date and local battlefield time. The setting's `start_local` is read in a UTC frame and formatted in UTC, as `apps/poc/static/timeline.js` does, so the browser's time zone does not move it. Dates use the view's `display_locale` (`en`), as the POC desk does, so the date reads "Thursday, July 2, 1863". The page shows no turn counter and no revision label; order times are battlefield times.
- **Click and order.** A click on an own counter selects it. A click on a hex sets the destination. "Send move order" posts one `move` order at the cursor the desk last read. A click on a contact selects nothing and says the contact is an estimate. If the clock is running, the desk pauses it and waits for the current interval to finish, as the POC desk does, because the service takes orders only while paused.
- **Refusals.** A non-2xx reply becomes `DeskRefusal`, which keeps the HTTP status and the server's `error` text. The desk shows that text in `#notice`, then reloads the state. A reply that breaks a contract is shown the same way.
- **Clock.** Start and pause; the desk polls the state once a second while the clock runs.

### Information boundary

The desk reads every state reply through `readCommanderState`. That reader refuses a God view and every God-only field, so the desk cannot hold omniscient state ([67](67-typescript-contracts.md#the-information-boundary-in-the-contract)). Enemy markers come only from `contacts`, which the contract already keeps free of exact enemy values. The counter shows the reported `strength_range` and the composition type when present, and `S? E? M?` for skill, energy and morale. Unknown contact attributes stay unknown. The desk has no God Mode and no replay.

### Contract addition

`packages/contracts/src/map.ts` adds `mapDocument` / `readMapDocument` for `GET /api/map`, the one wire shape the desk needed that 67 left out. It checks:

- the setting (`location`, `start_local`, `time_basis`), with `start_local` refused if it carries an offset or `Z`;
- the cells (`pos`, `elevation`, `terrain`, `move_cost`, `cover`; other keys such as Hougoumont's `area` are kept), each inside `cols` by `rows`;
- the drawing sizes (`radius`, `width`, `height`, `metres_per_hex`) and `source` / `source_url` (`null` for Hougoumont).

`record.py` now also writes `fixtures/map.json`. Re-running the recorder rewrote no existing fixture; `packages/contracts/test/map.test.ts` checks the fixture and one mutation per rule.

## How it is served

The POC accepts only its own `Host` and `Origin` and sends no CORS headers. A page on another origin therefore cannot post orders to it. `apps/web/server/desk-server.ts` serves the desk and relays `/api/*` to a loopback POC, so the page and the API share one origin:

- It listens on 127.0.0.1. It accepts a `pocUrl` only on `http://127.0.0.1` or `http://localhost`.
- It refuses, with 403, a request whose `Host` or `Origin` is not its own. This is the POC's own rule. A refused request is not relayed. A request it relays carries the POC's own `Host` and `Origin`.
- It serves `apps/web/src/*.ts` and `packages/contracts/src/*.ts` as JavaScript, with types removed by Node's `stripTypeScriptTypes` and the `@battle/contracts` import mapped to `/contracts/index.ts`. Only names matching `[a-z0-9-]+.ts` under those two directories are served. It adds no build step, bundler or dependency. `tsconfig.json` now sets `erasableSyntaxOnly`, so `tsc` refuses syntax that type stripping cannot remove, such as parameter properties.
- The CSP is `default-src 'self'; script-src 'self'; …; connect-src 'self'`.

This is a local development server. It is not a deployment or serving decision for Evo or Vercel ([31](31-evo-target-and-typescript.md)).

## How to run it

```
make poc-offline                 # POC on 127.0.0.1:8874, scripted commanders, no model calls
make web                         # desk on http://127.0.0.1:8875/ (WEB_ARGS="--port N --poc http://127.0.0.1:M")
```

Use `make poc` instead of `make poc-offline` for the usual commander; the desk itself never calls a model. The POC desk at `http://127.0.0.1:8874/` keeps working beside it on the same battle.

## Tests and the browser check

- `npm test` runs `apps/web/test` (model, markup, transport, server; 20 tests) and the contracts tests. No test uses the network beyond 127.0.0.1.
- `make smoke-web` (`apps/web/scripts/smoke-browser.ts`) is the real-browser check. It starts an offline POC on a temporary SQLite file and a free port, the desk server on another free port, and headless Chrome with its own profile and `TZ=Pacific/Kiritimati` (UTC+14). It drives Chrome through the DevTools protocol over Node's built-in WebSocket, so no dependency is added. It checks:
  1. The header reads `16:30`, `Thursday, July 2, 1863`, `Little Round Top · Gettysburg, Pennsylvania`, and the page text has no "turn" or "revision".
  2. One counter is drawn per own unit, and one enemy marker per contact.
  3. A pointer click at a friendly counter's centre, hit-tested by the browser, marks it selected (`class`, `aria-pressed`, the selection panel).
  4. Clicks on an open hex and on "Send move order" give an accepted notice. The POC's own `/api/state` then holds the `move` order with that destination, and the desk's order list shows it.
  5. Start clock moves the header time on (16:30:30), and Pause stops the clock.
  6. The test advances the POC directly, which makes the desk's cursor stale. The desk's next order is then refused, the notice shows the server's "Battle changed. Refresh before issuing another order.", and the POC's order count does not change.

  Exit 0 means passed, 1 means failed, and 3 means blocked (no runnable browser), which is never reported as a pass. The browser is chosen from `BATTLE_BROWSER`, then an installed Chrome or Chromium, then a Playwright Chromium. The test removes provider keys from the environment of the POC and the browser. Chrome runs with background networking, component updates and sync disabled.

**Result, 2026-11-08, Chrome on macOS:** `SMOKE PASSED`. With selection disabled in `selection.ts`, the test failed at the selection check. With `BATTLE_BROWSER` set to a missing path, it exited 3 (`SMOKE BLOCKED`). The first run failed on the date format, which led to the `display_locale` choice above.

**Limit:** the opening Little Round Top state has no contacts, so the browser run draws no enemy marker. Contact markers and the contact list are checked only against the recorded 12-interval fixture, in `render.test.ts`.

## Deferred

- Other scenarios. A Hougoumont map passes the contract, but no desk check covers it. Switching scenarios (`/api/new`, `/api/scenarios`) is not in the desk.
- Staff chat, the twin, and recommendations.
- Replay and God Mode.
- Field glass, unit images, terrain features (roads, buildings, works), elevation shading and the MapLibre renderer.
- Orders other than `move`: hold, rest, retreat, resupply, recon, standing orders, split and combine.
- Unit cards, the mission brief panel, dispatches, troop analysis, and command location and disruption display.
- Localisation beyond the view's `display_locale`, and accessibility beyond button roles and `aria-pressed` on counters.
- Any port of rules out of Python. Python stays the authority for every legality check.
