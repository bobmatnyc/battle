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

## 12. Slice 4b as built

**Task:** bt-T20. Branch `bt-t20-slice4b` from `ae339fc`. Commits: `91d5c61` (tests and recorded fixtures, red), `6670ac8` (contracts), `f4a57cf` (relay and desk, D and E), `47f6e03` (smoke-web steps), then this section. No engine, rules, routing or scenario file changed: `git diff --stat ae339fc HEAD -- apps/poc/battle` is empty. Doc 81's claims held: the engine already takes both commands (`standing.issue`, `formations.request`) on every playable scenario (all are `poc-13`), so neither item stopped. §10's open point is answered: neither command touches a rules edition.

### Contracts added (`packages/contracts/src`)

- `requests.ts` (new): `standingOrderSubmission` is exactly `{instruction: {unit_id, profile_id}, game_id, revision}`. `formationSubmission` is `{instruction, game_id, revision}`, where the instruction's `kind` picks the key set as `formations.validate` does: a split is exactly `{kind, unit_id, count, destination}`, a combine exactly `{kind, unit_id, partner_id}` with a partner other than the unit. Readers `readStandingOrderSubmission` and `readFormationSubmission`.
- `views.ts`: `standingTemplate` types `standing_templates` (id, label, intent, version, message_key and the five thresholds; extra keys kept) in both views. `StandingOrder` now requires `unit_id`, `profile_id`, `version`, `sent_turn`, `arrival_turn` and `template_version`. `FormationOp` requires `unit_id`, `order_ids` and `sent_turn`, takes `kind` as `split` or `combine`, and types the optional `partner_id`, `count`, `destination`, `reason`, `observed_turn` and `received_turn`. Both lose their "UNCONFIRMED" note.
- `check.ts`: `nonEmpty` moved here from `api.ts` so both request modules use it.
- Fixtures: `record.py` `record_commands` plays a second Little Round Top game with the pinned id. U1 is sent Preserve the force; headquarters U2 detaches 20 troops to 14,15; once the split is reported, UD1 is combined back into U2; the clock runs until the combine and the standing order are reported. It writes the three accepted request bodies and the commander state after them (`state-commander-commands.json`, revision 9). Two runs give identical files, and re-recording rewrote no other fixture.

### Routes added (`apps/web/server/desk-server.ts`)

`ROUTES` lists ten routes: the eight before plus `POST /api/standing-orders` and `POST /api/formations`. `BODY_CONTRACTS` maps each new route to its contract. `checkedBody` parses the body, checks it, and relays the checked copy re-serialized, so no key outside the contract reaches the POC. A body that is not JSON, or fails its contract, gets a 400 naming the bad field (`The desk refused a malformed request: $.instruction.kind: …`). It is never relayed and carries no `outcome: "unknown"`. Both routes forward to the POC's existing endpoints only. The other routes are unchanged; `/api/orders` is still relayed as sent and checked only in the browser.

### D. Standing orders

- `apps/web/src/standing.ts`: the template picker is built from the view's typed `standing_templates`, so Hougoumont also offers Close the gate on a breach. `standingBody` builds the request for an own unit that can take orders and a template the view offers. `standingCurrent` gives the unit's reported template and version, then any instruction still awaiting acknowledgement. `standingListMarkup` lists the side's standing orders newest first: unit, template, battlefield send time and status.
- **Cancel.** The engine has no cancel. `standing.py` cannot recall an instruction, but a newer version supersedes an older one on arrival (`standing.deliver`). Cancel therefore sends the battle's first template, Balanced. Every unit starts with it (`scenario_entry`), and `standing.profile` falls back to it. `cancelBody` offers this only while the unit's last instruction in force or on its way, else its reported template, is another template. The help line says that a sent instruction cannot be recalled.
- `commands.ts` `sendStanding`: the same unknown-outcome path as orders. On a 504 or a dropped reply the desk re-reads, and the notice says whether the battle now holds the instruction. A plain refusal shows the engine's text.

### E. Split and combine

- `apps/web/src/formations.ts`: `splitRefusal` and `combineRefusal` repeat `formations.validate`'s checks, in its order, on what the commander view shows, and return the engine's own text. For a split: the unit takes orders and holds no captives, both parts keep at least 12, the hex is adjacent, and no reported friendly formation stands on it. For a combine: two different own units that take orders and hold no captives, with matching type, weapons, skill and reconnaissance role and skill, adjacent, at most 80 together, and the partner is not headquarters. `combinePartners` lists the units that pass, so a merged, routed or lost unit is never offered. A merged unit also leaves the commander view.
- The desk disables Send split and Send combine while its check refuses, and `formationHelp` gives the reason in the engine's words. The checks the view cannot make go to the engine, and the desk shows its text: walls and gates, impassable water on known terrain, sappers, `rout_strength`, facing, surrender and exploit keys (not in `engine.summary`), the rules edition, and an unreported unit. A test reads `apps/poc/battle/formations.py` and `engine.py` and fails if the desk's limits (12, 80, `PROFILE`) or any refusal text drift from the engine.
- The split count defaults to half the strength, as on the POC desk. The destination is the selected hex on the map. `operationsMarkup` lists operations newest first: id, kind, units, status, send time and the last notice's reason. `sendFormation` follows the unknown-outcome path. An accepted split or combine clears the selected hex.

### Deviations

- Cancel is a superseding instruction, not a recall (above). The engine supports nothing else, and doc 81 did not claim a cancel.
- The two view types were tightened, not only added. One synthetic standing order in `contracts.test.ts` (`standing order of another side`) gained the now-required keys.
- After the red commit: `formations.test.ts` expected `hexDistance([11,14],[13,15])` to be 2. That was my arithmetic; `grid.distance` gives 3, and the test was corrected. A `formationHelp` test was added. The `replay.test.ts` fake API gained the two new methods for `tsc`.
- The desk repeats engine rules (limits, matching keys, texts). This is pinned by the drift test above, not removed. Moving them into the view would be an engine change.
- Pegasus Bridge's sapper units and Hill 223's units with declared rout or exploit keys look splittable on the desk. The engine refuses them with its text, because the keys are not in the commander view.

### Digests

Doc 74's `digests.py` and doc 76's `run_digests.sh` were copied unchanged from `slice4a-64048b6`. They ran on a `git archive` of `ae339fc` and on this tree: every headless catalog entry without timings, and desk play of all five player scenarios to the end. Both comparisons are identical: `cmp desk EXIT=0` and `cmp catalog without timings EXIT=0` (8 catalog lines, 5 desk lines; `run-digests.log`, `digests/`). The scripted and headless paths never post either command, so their records are unchanged. A desk game that sends a standing order or a split or combine stores a `standing` or `formation` action in its record, so its digest differs from the same game without it. That is expected, not a regression.

### Gates

Evidence is under the git-ignored `apps/poc/artifacts/slice4b-47f6e03/` in this worktree. `MANIFEST.txt` lists the files, and each gate log ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline`, `npm run typecheck` | exit 0 |
| `npm test` | web 108 of 108, contracts 85 of 85; exit 0 |
| `make smoke-web` | `SMOKE PASSED`. At Little Round Top, U1 Preserve the force was sent (SO1) and cancelled (SO2 Balanced, a higher version), and headquarters U2 split 20 to 14,15 (F1); the POC holds each. At Hougoumont, A2 split 30 west to 9,9 across the wall: the desk sent it, and the engine's "A wall or shut gate separates that hex from the formation." is shown, with no operation added |
| `make test-poc` | `Ran 808 tests … OK`; every node check passed; exit 0 |
| `make headless-poc` | winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as before |
| `make smoke-poc` | exit 0 |

**Red first** (`red/`): at `91d5c61` on the previous sources, the contracts suite fails to load `requests.test.ts` (no `formationSubmission`; 1 of 64 fails). The web suite fails to load `commands`, `formations` and `standing` (no `sendFormation` and the rest; 6 of 85 fail).

**Mutations** (`mutations/`): each was applied at `47f6e03` and turned the suite red, then was restored.
- D: `cancelBody` offering Cancel whatever the current template: 1 of 108 fails (`cancel sends the battle's first template, and only while …`).
- D: the relay dropping the standing-order body check: 2 of 108 fail (`… a malformed one is a 400 never relayed`, `only the routes the desk uses are relayed …`).
- E: `combineRefusal` without the adjacency check: 1 of 108 fails (`combine partners are the adjacent own formations the engine would accept`).
- E: the contract accepting a combine with itself: contracts `combine: with itself` and web `a standing order and a formation post their checked body …` fail.

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

### Slice 4b (bt-T20)

code-critic at `a0f0eb5`: **APPROVE**, no CRITICAL or HIGH. The critic re-ran `npm test` (web 108 of 108, contracts 85 of 85) and `tsc --noEmit` in both packages (clean). It confirmed:

- There is no diff under `apps/poc`.
- Cancel sends the view's own first standing template, never a hard-coded Balanced, and is not offered when the unit already holds it.
- The desk's split and combine checks follow `formations.validate` in order and use the engine's own refusal text.
- `checkedBody` forwards only the parsed contract copy and rejects unknown keys, including `__proto__`.
- A malformed body returns 400 before any upstream call, so the relay does not fail open.

Credential scan over `origin/main...HEAD`: clean.

One LOW note, not fixed (below the fix bar): the drift-guard test in `apps/web/test/formations.test.ts` falls back to a 60-character prefix match. A changed tail of a long engine refusal text would still pass. Comparing the full string would close it.

Owner-visible behaviour: the engine cannot recall a standing order. Cancel therefore sends the battle's first template, which replaces the old order when it arrives. A true recall needs an engine change.

## 13. TS desk zoom (bt-T26)

**Task:** bt-T26. Branch `bt-t26-ts-zoom` from `f1f4210`. Commits: `adfdbd4` (tests, red), `21063d2` (zoom), `71ba4e8` (smoke-web test edit, below), then this section. Presentation only: `git diff --stat f1f4210 HEAD -- apps/poc/battle packages/contracts/src` is empty.

### What was built

- `apps/web/src/zoom.ts` (new, pure): the camera is the fit view or 2×. `zoomWindow` gives the part of the map the frame shows, in scene px: the whole map at fit, and at 2× a window of half the map's width and height about a centre, kept on the map. `mapFocus` and `focusCentre` port the POC desk's rule (§11 B; `apps/poc/static/app.js` `mapFocus`, `map-view.js` `focusCentre`). `core` is the objective hex with its label as drawn at fit; `all` adds every map feature with a `pos`. Per axis, the zoom takes the least move from the map's middle that keeps `all` in frame, else `core`, else centres `core`. `pan` moves the 2× window by half its size, kept on the map. `toScreen`, `toScene` and `hexAt` state the screen transform, so the tests and smoke-web can check where a click lands.
- `apps/web/src/desk.ts`: the toolbar gains Zoom in, Zoom out, Fit, four pan buttons (West, North, South, East) and a `1× view` / `2× view` readout. The SVG `viewBox` is the zoom's window, and `mapMarkup` places every label inside that window. Clicks still reach the desk through the browser's hit-testing (`closest("[data-unit]")`, `[data-c]`), so a click at 2× selects whatever is drawn under the pointer, as at fit. The zoom resets to fit when the desk adopts a new game (scenario switch or new battle). It persists through replay and polls. The listeners are added once, in `startDesk`.
- `apps/web/src/render.ts`: `mapMarkup` takes an optional `frame` (default: the whole map) and passes it to `featureLayer` and to the objective label's `titlePlace` (doc 80 §7). `objectiveLabel` is the label's text and place; `mapFocus` reads it.
- Pan is by buttons, not drag. A drag would have to be told apart from the clicks that select counters and hexes; the buttons need no such rule.

At 2×, Pegasus Bridge's window is `270 210 540 420`. The marks run from the canal to the Orne pillbox, which is wider than the window, so the window holds the objective and its label; four labels whose marks are off screen are hidden by the rule. Hill 223's window is `20.58 243.5 540 420`: the shack (column 0), its label and the old trench are in frame. Screenshots: `screenshots/desk-pegasus-zoom2x.png`, `desk-hill-223-zoom2x.png`, the replay at 2× `desk-*-replay-zoom2x.png`, and fit `desk-*-features.png`.

### Checks added

| Check | Addition |
|---|---|
| `apps/web/test/zoom.test.ts` (5 tests) | Fit is the whole map with the old viewBox, and `mapMarkup` at the fit window equals the old call byte for byte. Zoom-in focus on Hill 223 (all in frame) and Pegasus (objective only), plus the rule's no-focus and too-wide cases. At 2× every label's rule box is inside the window, and the pillbox label is hidden. Every hex centre in the 2× window, offset a third of a radius, maps back to its hex; the same screen point names another hex at fit. Pan steps, clamping and no pan at fit |
| `apps/web/scripts/smoke-zoom.ts` (new), called from `era()` in `smoke-browser.ts` for Pegasus Bridge and Hill 223 | The battle opens at fit (Hill 223 after Pegasus was left at 2×: the reset). Zoom in gives the focus window; the objective circle and every label are inside the SVG frame (`checkLabels`). Fit restores the fit `innerHTML` byte for byte. At 2×, a real click at the transform's point of an own counter selects it. Every hex centre in frame hit-tests to that hex or a counter on it (132 at Pegasus, 125 at Hill 223), and a click sets the destination. After the outcome, the replay plays every record at the fastest speed at 2×, with the window kept and labels inside. Returning to live, reopening and closing, then one pan click moves exactly one step and the opposite click returns |

### Deviations

- Two zoom levels. Zoom out from 2× is the fit view, the same as Fit. The brief asked for 2×; the POC desk allows about 5.7×.
- Full-page smoke screenshots are not byte-identical to `f1f4210`: the toolbar now has the zoom buttons. They are not byte-stable between runs of the same tree either. Two runs of this head differ by scattered anti-aliased pixels on 5 of 12 fit screenshots (`fit-diff-head-vs-head.log`); against `f1f4210`, 6 of 12 are identical below the toolbar (`fit-diff.log`). The byte-for-byte evidence for the fit view is the markup instead: `fit_markup.ts` renders the map of the five playable scenarios (with and without a selection) through `f1f4210`'s `render.ts` and through this head's, with the fit window. The outputs are identical (`cmp EXIT=0`, 11 lines, 1,055,283 bytes). The page's viewBox string is the same, `0 0 1080 840`, and smoke-web checks that Fit restores the fit `innerHTML`.
- The first zoom build labelled the pan buttons ◀ ▲ ▼ ▶. Those glyphs came from a fallback font and made the toolbar 6 px taller, so the map moved down. The buttons now carry text labels, and the toolbar keeps its height.
- After the red commit, one test edit (`71ba4e8`): at Hill 223 no own counter starts inside the 2× window, so smoke-web now pans with the desk's buttons until the first own counter is in frame (one click east), then clicks it. This adds a check and weakens none.
- At 2× on Hill 223, the fieldworks symbol (drawn 24 px below its hex centre) is cut at the bottom edge, and its label is inside. The focus box counts each mark's hex (± radius), as on the POC desk. Labels are what the frame rule covers.

### Gates

Evidence under the git-ignored `apps/poc/artifacts/ts-zoom-71ba4e8/` in this worktree; `MANIFEST.txt` lists the files and each gate log ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline`, `npm run typecheck` | exit 0 |
| `npm test` | web 117 of 117 (was 112), contracts 85 of 85 |
| `make smoke-web` | `SMOKE PASSED`, with the zoom lines above for Pegasus Bridge and Hill 223 |
| `make test-poc` | `Ran 818 tests … OK`; exit 0 |
| `make headless-poc` | winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as before |
| `make smoke-poc` | exit 0 |

**Digests against `f1f4210`**: doc 80's `run_digests.sh` and doc 74's `digests.py`, copied unchanged from `label-edge-5f553f4`, ran on a `git archive` of `f1f4210`'s `apps/poc` and on this tree. They cover every headless catalog entry without timings (8) and desk play of all five player scenarios to the end. Both comparisons are identical: `cmp desk EXIT=0` and `cmp catalog without timings EXIT=0` (`run-digests.log`, `digests/`).

**Red first** (`red/`), the tests of `adfdbd4` on `f1f4210`'s sources: `npm test` cannot load `zoom.test.ts` (no `src/zoom.ts`), 1 of 113 fail; smoke-web cannot load `smoke-zoom.ts` for the same reason.

**Mutations** (`mutations/`), each applied, red, then restored byte for byte:
- Focus ignored (`focusCentre` returns the map's middle): web 2 of 117 fail (the focus test and the 2× labels test).
- Frame ignored (`mapMarkup` places labels in the whole map): 1 of 117 fails (`at 2x every label is placed inside the zoomed window …`).
- Transform without the window's origin (`toScreen`): 1 of 117 fails (`a click at 2x maps to the hex under the pointer`).
- Fit window one pixel wider: 1 of 117 fails (`the fit view is the whole map …`).
- Zoom not reset on a new game: `make smoke-web` fails at Hill 223: `objective "PATROL OBJECTIVE" … is cut by the map frame`. Pegasus's 2× window was still applied.

### Review notes (bt-T26)

pending PM
