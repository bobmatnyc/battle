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
