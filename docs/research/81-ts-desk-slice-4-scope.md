# 81 — TypeScript desk slice 4: scope and cut

**Date:** 2026-11-08. Base `130a6e5`. Research only: no code, contract, engine or fixture changed. The scope covers the six items the Architect ordered (A to F), read against docs 70, 71, 73, 76 and 80. Line references are to the base commit.

## 1. Summary

Three items are presentation only and can ship together as slice 4a: replay playback at a speed with help text (A), the Hill 223 2× centring in the POC desk (B), and a signals panel (C). The other three wait. Standing orders (D) and split/combine (E) need request contracts, a wider relay allowlist and typed templates, but no engine change. Staff chat (F) needs an owner decision on the model provider and its spend. No item needs an engine change, and none changes a scripted digest.

## 2. A. Replay playback at a speed, and help text

**Exists.** The TS replay steps and scrubs only. `apps/web/src/replay.ts` (48 lines) holds `openReplay`, `replayAt`, `ordersOpen` and `replayLabel`. The wiring is in `apps/web/src/desk.ts:61-66` and `:104-114`. The bar in `apps/web/index.html:30-36` has Step back, a slider, Step forward and Return to live. It has no play button, no speed control and no help text. The POC desk has all three: `replaySpeed` and `scheduleReplay` in `apps/poc/static/app.js:8` and `:263-271`, and `changeSpeed` at `:235-240`. Its delay is the battle seconds between two records divided by the speed, with a floor of 100 ms. The speeds are the clock's own `speeds` list, which `packages/contracts/src/api.ts:14-20` already types.

**Missing.** A timer that steps to the next revision. A Play/Pause button and a speed control built from `clock.speeds`. Stop on slider input, on Return to live and at the last record. A generation counter so a late reply cannot move a stopped replay. Help text on the bar: what Step, the slider and Play do, that the view is the player's own recorded commander view, and that orders are closed. The order help under the form still describes the selected kind while replaying (doc 73 §7); it should say that orders are closed.

**Contract:** none. **Engine:** none. **Digests:** identical; the desk only reads `/api/history` and `/api/replay`. **Owner decision:** none. **Size:** S to M. The relay allowlist is unchanged.

## 3. B. Pegasus and Hill 223 layout

**Counter and label overlap: already fixed.** Doc 80 (PR #22) gives both desks one rule: priority, then first free place, else hidden. It was measured on all five playable scenarios at fit and at 2×, with no label meeting a label or a counter and none hidden (Pegasus 9 labels, Hill 223 1). Nothing remains to fix there.

**The 2× view off-centre: open, and POC desk only.** Doc 80 §5 defers "2× view centring (Hill 223's ravine and shack off screen)". The TS desk has no zoom: its SVG is fit-only (doc 80 §4). The 2× view is the POC desk's MapLibre camera in `apps/poc/static/map-view.js`. `fit()` at `:61` fits the bounds, and the zoom buttons at `:73-74` zoom about the current centre. I did not run the harness, so the size of the offset is as doc 80 reports it. `apps/poc/scripts/map_screenshots.mjs` already renders Hill 223 at 2×; the builder should start from its screenshot.

**Missing.** A zoom that keeps the scenario's features and objective inside the frame: centre on the briefing cells and map features, or clamp the pan to their bounds. A check that the ravine and shack boxes lie inside the viewport at 2×.

**Contract:** none. **Engine:** none. **Digests:** identical (camera and overlay only, as in docs 72 and 80). **Owner decision:** none. **Size:** S. **TS desk:** nothing to build. Adding zoom to the TS desk is a separate, larger item outside this slice.

## 4. C. Signals panel

**Exists.** The engine already sends delivered codewords in the commander view: `apps/poc/battle/engine.py:525` (`signals.visible`, delivered codewords only), from `signals.py:74-79`. The contract already types them as optional: `ReceivedSignal` and `receivedSignal` at `packages/contracts/src/views.ts:102-110`, and `signals?` on the commander view at `:216` and `:256`. The God view keeps `signals` as untyped JSON (`:227`, `:284`). Doc 76 §8 says the desks render none and that showing them "needs a typed contract field".

**What that means now.** The field is typed, but its comment reads "UNCONFIRMED by fixture (Pegasus Bridge only)". The fixtures come from Little Round Top (`packages/contracts/fixtures/record.py`), so none holds a delivered signal. A panel built on an unconfirmed type could fail on the first Pegasus delivery. The missing piece is a recorded Pegasus commander state with a delivered codeword, a test that checks it, and removal of the "unconfirmed" note. `CommanderBroadcast` (`views.ts:216`) is in the same case.

**Missing on the desk.** A panel in `apps/web/src/panels.ts` listing codeword, meaning, bridge and delivery time, in battlefield time with no turn number (the timeline rule). It must read only the commander field. The only authored signal in the shipped scenarios that I found is Pegasus Bridge's Ham (`scenario_pegasus.py:208`, `:260`).

**Contract:** additive (fixture, test, confirm or correct the type). **Engine:** none. **Digests:** identical. **Owner decision:** none. **Size:** S to M. The fixture is the long part: `record.py` has no path to a Pegasus game that reaches a delivery.

## 5. D. Standing orders

**Exists.** The POC route `/api/standing-orders` (`apps/poc/battle/adapters/http_api.py:9`) takes `{instruction: {unit_id, profile_id}}` (`standing.py:44-49`), and the battle service passes it on (`services/battle.py:216-217`). The commander view carries `standing_templates` and `standing_orders`. The contract types `standing_orders` per item (`views.ts:125-129`, `:254`) but leaves `standing_templates` as untyped JSON (`:180-195`). The relay refuses the route: `ROUTES` in `apps/web/server/desk-server.ts:38-41` lists eight routes, not this one.

**Missing.** A `standingTemplate` contract and a request-body contract. The route in `ROUTES` with a body check. A template picker and a list of standing orders with status in the unit card. The unknown-outcome re-read that orders already use (`apps/web/src/commands.ts`). Tests and a smoke step.

**Contract:** yes (templates, request). **Engine:** none. **Digests:** scripted runs identical, since they never use the desk path; a desk game that issues one adds a `standing` action to its own record. **Owner decision:** none found. **Size:** M. **Depends on:** nothing, but it shares the relay and request plumbing with E.

## 6. E. Split and combine units

**Exists.** The route `/api/formations` (`http_api.py:11`) takes `{instruction: {kind, unit_id, count, destination}}` for a split and `{kind, unit_id, partner_id}` for a combine (POC desk, `apps/poc/static/app.js:206-214`). The rules are in `formations.py:49-89`; the POC's own message says regrouping takes sixty seconds after receipt. The view carries `formation_ops`, typed by `commanderFormationOp` (`views.ts:95-99`), which keeps extra keys.

**Missing.** A request contract. The route in `ROUTES`. Split and combine forms in the unit card: split count (the POC defaults to half the strength) and destination by map click, and a combine partner list. The operations list with the last notice. The detail keys the desk would read (`unit_id`, `partner_id`, `reason`) must be typed first. The POC also records `merged_into` and `retired_units`; the desk must not offer a merged unit as a target.

**Contract:** yes. **Engine:** none. **Digests:** as D. **Owner decision:** none found. **Size:** M to L (selection state, map targeting, merged-unit cases). **Depends on:** D for the relay and request plumbing; build both in one slice.

## 7. F. Staff chat

**Exists.** `/api/chat` takes `{text}` of 1 to 2000 characters (`services/battle.py:224-237`). The state carries `messages`, `mode`, `model` and `inference_available` (`packages/contracts/src/api.ts:23-51`); `ChatMessage.proposals` is UNCONFIRMED because the recorded game has none. The POC chat form is `apps/poc/static/app.js:257`. The reply comes from `commander.chat` (`inference.py:49`), which calls the model provider in `openrouter` mode.

**Missing.** A chat panel, the request contract, the route in `ROUTES`, display of `proposals`, a visible `source` per reply so a scripted fallback is not read as the model, and a fixture with a real proposal.

**Owner decision: yes.** Chat from the desk could spend on the model provider outside the D37 guards of doc 78, which cover `scripts/model_runs.py` only. The owner must say whether the desk may call the provider, with whose key and what limit, and whether a scripted fallback may be shown. **Contract:** yes. **Engine:** none expected. A chat action is stored in the game record, so a game with chat gets a different digest from one without. **Size:** M, after the decision. **Depends on:** the decision, then the D and E plumbing.

## 8. Dependencies

- A, B and C are independent of each other and of D to F.
- D and E share the relay widening, request-body checks and the unknown-outcome path; build them together.
- F needs the owner decision first, then the same plumbing.
- Every item keeps the boundary of docs 21 and 65: commander view only, the relay refusing `side`, `view` and God routes.

## 9. Recommended cut

**Slice 4a, one builder, now: A, B (POC 2× centring only) and C.** All three leave every digest unchanged, need no engine edit and need no owner decision. The only contract work is C's fixture and test. Order: A (largest user-visible gain), B (small, with its screenshot check), then C (record the Pegasus fixture first; if that proves long, ship A and B and carry C). Acceptance: `npm test`; `make smoke-web` with a playback step shown able to fail; `map_screenshots.mjs` with the Hill 223 2× check; headless digests identical to `130a6e5`.

**Slice 4b, next: D and E together.** Nothing blocks them. They are held back only to keep 4a presentation only, because they add write routes.

**Slice 4c, waits on the owner: F.** It waits on the provider and spend decision. Recommendations (accept or dismiss) and the twin stay deferred, as in doc 71.

## 10. Open points

- C needs a new `record.py` path to reach a Pegasus signal; the effort is unmeasured.
- B's offset is as doc 80 reports it; no harness was run here.
- Whether D and E touch a rules edition is unchecked beyond the code paths cited.

## 11. Slice 4a as built

**Task:** bt-T18. Branch `bt-t18-slice4a` from `b214cd1`. Commits: `4edb3f2` (tests, red), `04abe95` (B), `8d6fb99` (A and C), `64048b6` (smoke-web step), then this section. No engine, rules, routing or scenario file changed: `git diff --stat 130a6e5 HEAD -- apps/poc/battle` is empty. Under `packages/contracts/src` one comment line changed (below). No desk-server route was added.

### A. Replay playback and help

- `apps/web/src/replay.ts`: `Playback` holds at most one timer. Each tick reads the next record (`replayAt`), shows it and waits `playbackDelay`: the battle seconds between the two records divided by the speed, never under 100 ms (the POC desk's rule). `stop` clears the timer and bumps a generation counter, so a read in flight when the player steps, scrubs, pauses or returns to live is dropped. A tick that finds no replay stops. Play at the last record starts again from the first, as the POC desk does. A speed change while playing re-times the pending wait.
- The speed list is the live clock's typed `clock.speeds`; the replay opens at the live clock's speed (POC desk behaviour).
- `apps/web/src/desk.ts` and `index.html`: a Play/Pause button, a Speed select and a help line on the bar (`replayHelp`). Step, slider, Return to live and opening a replay call `stop` first. New battles and the clock stay disabled while replaying, as in slice 3.
- Order help: `ordersClosedReason` gives the reason orders are closed. While replaying the order help shows only "Orders are closed while you replay the recorded commander view. Return to live to command." Live, a finished battle or a headquarters that cannot command adds a reason line above the template help.

### B. POC desk 2× view

- `apps/poc/static/map-view.js`: the + button now eases to `focusCentre` instead of zooming about the current centre. The focus comes from `app.js` `mapFocus`: `core` is the objective hex with its place label; `all` adds every mark with a hex (`map_features[].pos`). Per axis, the zoom takes the least move that keeps `all` in frame; if `all` is larger than the frame, the least move that keeps `core` in frame; then the frame is kept on the 1080 × 840 scene. With no focus the zoom is the old one. `fit()` and the − button are unchanged.
- Hill 223 at 2×: the shack and all ten ravine hexes are now in frame (`screenshots/hill-223-zoom2x-grid-on.png`). Before, at `130a6e5`, all eleven were off the left edge (`red/map_screenshots.log`; the before picture is doc 80's `fords-labels-29cfd3e/screenshots/hill-223-zoom2x-grid-on.png`, copied to `before/`).
- Fit view unchanged: the ten fit screenshots (five scenarios, grid on and off) are byte-identical before and after (`cmp`, `fit-cmp.log`). At 2×, Hougoumont and Little Round Top keep their camera (Little Round Top's grid-on file differs by rendering only: its grid-off file is identical and the picture matches); Concord and Pegasus move a little to bring their marks in (Pegasus shifts east to take in the Orne pillbox), with the objective still in frame.
- The place label "Command post at the shack" is still cut at the left edge, at fit and at 2×, because the objective sits in column 0. Fixing it needs a label rule, not a camera change.

### C. Signals panel

- **Fixture.** The catalog's Pegasus Bridge blows its bridge at interval 5 (bt-D09 default) before Ham can be sent, so no desk game of the catalog entry reaches a delivery. `record.py` `record_pegasus_signal` runs the headless-only `guard-only+relief-1h` entry (no demolition, relief at one hour; the run `test_a_held_bridge_run_sends_ham_by_report_and_replays_identically` already uses), scripted on both sides, about 10 s. It writes the British commander replay (`BattleQueries.replay`, the `/api/replay` path) at revision 13, the first holding a received codeword: Ham, sent turn 11 by D25, delivered turn 12 to DHQ. The game id is pinned; two runs give the same file. Re-recording rewrote no other fixture.
- **Contract.** The fixture matches `receivedSignal` as typed; no type was tightened or loosened. The only change under `packages/contracts/src` is the comment on `ReceivedSignal` in `views.ts`: "UNCONFIRMED by fixture (Pegasus Bridge only); keys from signals.py." became "Confirmed by fixture `replay-commander-pegasus.json` (Pegasus Bridge, docs/research/81 §4)." `CommanderBroadcast` stays unconfirmed (Gergovia).
- **Panel.** `panels.ts` `signalsMarkup` lists received codewords newest first: codeword, meaning, the bridge by the name in the view's `map_features`, battlefield arrival time and sender; no turn number. The Signals section is hidden when the view has no `signals` field (a battle with no authored codeword) and reads "No codeword received." when the list is empty. It reads only the commander view, live or replayed.

### Deviations

- C is confirmed on a recorded replay of a headless-only Pegasus entry, not on a desk game of the catalog entry, which cannot deliver Ham (above).
- After the red commit, two test edits: `check_map_geometry.mjs` passes results through JSON (a vm-made array is not deep-strict-equal to a local one) and its focus cases take `{core, all}`, because the first rule (box middle when too large) put Little Round Top's objective out of frame at 2×. The smoke-web step-stops-playback check was strengthened in `64048b6` after the first green run showed the second play ending on its own before the step.
- smoke-web shows the Signals panel nowhere: its games (Little Round Top, Hougoumont, Concord) have no authored codeword. The panel is covered by `apps/web/test/signals.test.ts` on the fixture.

### Gates

Evidence under the git-ignored `apps/poc/artifacts/slice4a-64048b6/` in this worktree; `MANIFEST.txt` lists the files and each gate log ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline`, `npm run typecheck` | exit 0 |
| `npm test` | web 89 of 89 (was 79), contracts 63 of 63 (was 62); exit 0 |
| `make smoke-web` | `SMOKE PASSED`; replay played 5 records at 60× to the latest and stopped; at 30× a step back from record 3 stopped playback for 2.5 s |
| `make test-poc` | `Ran 797 tests … OK`; `Zoom focus passed`; every smoke_ui and map check; exit 0 |
| `make headless-poc` | winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as before |
| `make smoke-poc` | exit 0 |
| `node apps/poc/scripts/map_screenshots.mjs` | `HARNESS PASSED`; objective in frame on all five scenarios at fit and 2×, Hill 223 also its 11 ravine and shack hexes; labels none meet, 0 hidden |

**Digests against `130a6e5`** (doc 80's `run_digests.sh` and doc 74's `digests.py`, copied unchanged), on a `git archive` of `130a6e5` and on this tree: every headless catalog entry without timings (8) and desk play of all five player scenarios to the end; `cmp desk EXIT=0`, `cmp catalog without timings EXIT=0` (`run-digests.log`, `digests/`).

**Red first** (`red/`), the tests of `4edb3f2` on the previous sources: `npm test` fails to load the replay and signals test files (no `Playback`, no `signalsMarkup`) and the contract test (no fixture); with stub exports added for the run (not committed), web 10 of 89 and contracts 1 of 63 fail. `check_map_geometry.mjs`: `BattleMapView.focusCentre is not a function`. `map_screenshots.mjs`: "hill-223 2x: hexes outside the map frame: objective 0,11; ravine 0,6 … shack 0,11 …".

**Mutations** (`mutations/`), each red, then restored: `Playback.stop` not bumping the generation, `npm test` 1 of 89 fails (`pausing, a step or a scrub stops playback, and a reply that arrives after it is not shown`); the desk's step handler not stopping playback, `make smoke-web` fails, "timed out waiting for the step to stop playback".

## Review notes

code-critic at `e1dbd58`: **APPROVE**, no CRITICAL or HIGH. The critic re-ran `npm test` in `apps/web` (89 of 89), `tsc --noEmit` (clean) and `check_map_geometry.mjs` (pass). It re-ran `record.py`; `git status` stayed clean, so every fixture regenerates byte-identically. It confirmed:

- `Playback` keeps at most one timer pending, and a read that is in flight after `stop()` is dropped.
- Playback stops on reopen, step, scrub, return to live and pause.
- There is no diff under `apps/poc/battle`, and `views.ts` changes a comment only.
- The two test-helper edits made after the red commit strengthen `check_map_geometry.mjs`.

Credential scan over `origin/main...HEAD`: clean.

Two LOW notes, not fixed (below the fix bar):

- `apps/web/src/desk.ts:274` sets the replay speed from the live `clock.speed`. If that value is not in `clock.speeds`, the select shows no option while playback runs at that speed. A fallback to the first listed speed would close it.
- `apps/poc/scripts/check_map_geometry.mjs` runs only with `PYTHONPATH=.` from `apps/poc`. This predates the branch.

Also carried from §11: the signals panel is confirmed on a headless-only Pegasus variant, not on a playable game. Hill 223's shack label is still cut off at the left edge and needs a label rule.
