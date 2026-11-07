# TypeScript contracts for state, replay, history and orders

Date: 2026-11-07. **Handoff item:** "Portable UI path: Build new command desk/contracts in TypeScript, retain current Python/SQLite rules and saves as reference." This document covers the contracts part only. The desk, the map-counter click, bundling and the serving choice are not in it. The Python app stays the reference: no rule, response or saved game changes.

## What the package holds

`packages/contracts` exports types and runtime validators with no runtime dependency. `src/check.ts` holds the checks (string, integer, hex, array, object, and so on). Each check returns a typed copy of its input and throws `ContractError`, whose `path` names the first bad field, for example `$.units[2].side`. `src/views.ts` holds the presented view. `src/api.ts` holds the HTTP responses and the order body. The only new dependency is `@types/node` (with its own dependency `undici-types`), development-only type declarations, so that `tsc` checks the tests that use `node:test`. Only `tsconfig.test.json` (the contracts and the tests) loads them; `tsconfig.json` (the contracts and `apps/web`) sets `types: []`, so the browser code is checked without Node globals. `npm run typecheck` runs both.

| Wire shape | Validator | Python source |
|---|---|---|
| `GET /api/state` | `commanderState`, `readCommanderState` | `BattleService.state` = `BattleQueries.project` + live fields |
| `GET /api/state?view=god` | `godState`, `readGodState` | the same, from `engine.god_view` |
| either of the above | `stateResponse`, `readStateResponse` | told apart by `view_mode: "god"` |
| `GET /api/replay?revision=N[&side=<id>]` | `commanderReplay`, `readCommanderReplay` | `BattleQueries.replay` (doc 65) |
| `GET /api/replay?revision=N&view=god` | `godReplay`, `readGodReplay` | the same, `god=True` |
| either replay | `replayResponse`, `readReplayResponse` | told apart by `view_mode` |
| clock fields (`clock`) | `clockStatus`, `readClockStatus` | `SimulationClock.status` |
| `GET /api/history` | `history`, `readHistory` | `Store.history`: `revision`, `turn`, `sha256` |
| `POST /api/orders` body | `orderSubmission`, `readOrderSubmission` | `BattleService._action`, `engine.validate_order` |

A replay response is the projection with no live fields (`clock`, `game_id`, `mode`, `model`, `inference_available`, `messages`, `last_commander_source`, `last_fallback_reason`; `LIVE_FIELDS`). A state response is the projection plus all of them. Each validator refuses the other's shape.

## The information boundary in the contract

The commander view is the boundary of [21](21-god-mode-and-command-location.md) and [65](65-replay-by-side-and-god-view.md). The commander validators refuse:

- any God-only top-level field: `view_mode`, `reports`, `events`, `decisions`, `headquarters`, `commands`, `retired_units`, `captives` (`GOD_ONLY_FIELDS`, the same list as `GOD_ONLY` in `tests/test_replay_sides.py`), and any other unknown top-level field;
- a unit, order, standing order, recommendation, formation operation or supply site of a side other than the view's `side`;
- a contact of the view's own side (a contact is an enemy sighting), and a contact carrying an exact enemy value: `strength`, `initial`, `ammo`, `morale`, `suppression` or `fatigue` (`CONTACT_FORBIDDEN`; a contact holds an estimate, a confidence and a `strength_range`);
- a recommendation without `received_turn` (`recommendations.visible` returns only advice that reached headquarters);
- a formation operation's true `ready_turn` or `completed_turn` (`formations.observed` drops them; its status is the last notice received);
- a delivered codeword (`signals`) with any key but `codeword`, `meaning`, `bridge`, `sender_id`, `receiver_id`, `sent_turn` and `delivered_turn` (`signals.receive`), so the sender's `side`, `condition` and `radius` are refused;
- a broadcast signal with any key but the eight of `broadcast.visible`: `id`, `kind`, `meaning`, `stance`, `destination`, `turn`, `ordered_turn`, `sounded_turn`, so `side`, `reach`, `block_hexes`, `sounder_id` and `receipts` (who heard) are refused;
- a `transport` on an order or standing order (the messenger packet), an `ammo` stock on a supply site, and a `side` tag on a dispatch;
- an assessment (`analysis.side`) or brief (`scenario_brief.side.id`) of another side.

The God validators require `view_mode: "god"` and every God-only field except the scenario-dependent `captives`. They also require an empty `contacts` list, a `side` on every dispatch and a `transport` on every order. They still require the brief and the assessment to be the player's, because God Mode never shows the opponent's mission (doc 65). These checks run in the browser. They do not replace the server's checks: a client that skips them still sees only what the server sends.

Strictness: the top-level views, the dispatches, the clock, history entries, chat messages, the brief, supply sites, commander codewords and broadcasts, and the order body refuse unknown keys. A God-only top-level field is refused by name ("not allowed in this view"), separately from the unknown-key rule. A new Python field there fails the fixture test until the contract names it. Units, contacts, orders, recommendations, standing orders, commander formation operations, order templates, the command location and the assessment check the fields listed below and keep any other key as plain JSON, because their keys vary by rules edition and scenario (`engine.summary` adds optional keys per unit).

## Fields checked, and fields not confirmed

Every field was read from the Python code and checked against the recorded fixtures. Fields marked UNCONFIRMED come from the code only, because the recorded game has no instance of them.

- **View, both variants:** `rules`, `turn`, `revision`, `status` (`active` or `complete`), `winner`, `reason`, `objective`, `max_turns`, `seconds_per_turn`, `side`, `weather`, `hq`, `command`, `units`, `contacts`, `orders`, `dispatches`, `order_templates`, `standing_templates`, `standing_orders`, `recommendations`, `map_features`, `supply_sites`, `formation_ops`, `display_locale` (`en`), `voice_profile`, `analysis`, and optional `scenario_brief`.
- **Unit:** `id`, `side`, `name`, `pos`, `initial`, `strength`, `ammo`, `morale`, `suppression`, `fatigue`, `status`, `stance`, `target`, `order_version`, `observed_turn`, `received_turn`.
- **Contact:** `id`, `side`, `pos`, `observed_turn`, `received_turn`, `age`, `confidence`, `estimate`.
- **Order:** `id`, `side`, `unit_id`, `stance`, `source`, `version`, `sent_turn`, `arrival_turn`, `status`, and `destination` (hex or null) when the order body had it: `engine.validate_order` accepts an order with no `destination` key for a template that selects its own position, and `engine.issue` stores the order as given. The fixture holds one such order (O2). God adds `transport`.
- **Recommendation:** `id`, `side`, `unit_id`, `status`, `text`, optional `display_text`; the commander view also requires `received_turn`.
- **Dispatch:** `turn`, `observed_turn`, `kind`, `text`, `display_text`, optional `message_key` and `message_args`; God adds `side`.
- **Clock:** `running`, `inflight`, `speed` (one of `speeds`), `remaining_seconds`, `speeds`, `error`.
- **History entry:** `revision`, `turn`, `sha256` (64 lowercase hex digits). The list starts at revision 0, revisions ascend, turns never decrease.
- **Order body:** `orders` (one to three of `unit_id`, `stance`, optional `destination` hex or null; no other key), `game_id`, `revision`. The grid bounds, the template list and the unit's eligibility are rules, checked by Python only.
- **UNCONFIRMED:** the `standing_orders` items (none issued; checked are `id`, `side`, `status` and no `transport`); the commander `formation_ops` items (none requested; checked are `id`, `side`, `kind`, `status`); the items of a chat message's `proposals` (scripted chat proposes none); the commander `signals` and `broadcasts` items, whose keys come from `signals.py` and `broadcast.py`, and `captives` (Pegasus, Gergovia and Hill 223 only, headless scenarios). The tests use synthetic items with those keys; `ammo` on a God supply site is confirmed, other God-only stock keys are not; `scenario_brief` absent (a save whose label no catalog knows); any `rules` edition other than `poc-13` (older saves use frozen views in `engine_v1`..`engine_v12`); the Hougoumont player scenario; the opponent's replay after completion, which uses `commanderReplay` but has no fixture.
- **Shape not pinned:** `weather`, `command.profile`, `analysis.summary` and the items of `map_features`, God `formation_ops`, `signals` and `broadcasts`, `standing_templates`, `reports`, `events`, `decisions`, `retired_units`, `analysis.contacts`, `analysis.units` are checked as JSON objects or values only.

## Fixtures

`packages/contracts/fixtures/` holds JSON recorded from the Python app at commit `c733662` (`main`), Python 3.14.8, by `packages/contracts/fixtures/record.py`. The script builds the app with `build_application(offline=True)` on a temporary SQLite file and reads every response through `HttpApi`, as the HTTP handler does, without starting a server. The game is Little Round Top (scripted commander): one order body with a hold for U1 (`destination: null`) and a hold for U3 (no `destination` key), one staff chat message, then 12 clock intervals (revision 14, turn 12, about 0.3 s of CPU). By then contacts have arrived and both orders are delivered.

| File | Request |
|---|---|
| `orders-request.json` | the `POST /api/orders` body sent at revision 0 |
| `state-commander.json` | `GET /api/state` |
| `state-god.json` | `GET /api/state?view=god` |
| `history.json` | `GET /api/history` |
| `replay-commander.json` | `GET /api/replay?revision=14` |
| `replay-side.json` | `GET /api/replay?revision=14&side=union` (the player's side, so equal to the default) |
| `replay-god.json` | `GET /api/replay?revision=14&view=god` |

The game id is pinned: the script patches `uuid.uuid4` while it builds the app, so `Store.create` gives `f1c7f1c7f1c7f1c7`. The scripted game is deterministic, so two runs write byte-identical files, and a refresh rewrites only what the Python app changed. The JSON stays indented for readable diffs.

**Refresh:** from the repository root, `python3 -I packages/contracts/fixtures/record.py` (optional argument: the number of intervals, default 12), then `npm test`. A failing fixture test after a refresh means the Python response changed: update the contract, or confirm the Python change was intended. Under a CPU hold, run the script on the designated host.

## Tests

`npm test` runs `npm test` in each workspace that defines it; `packages/contracts` runs `node --test` over `test/**/*.test.ts` with Node's built-in type stripping (Node 26), so no build step or test runner is added. The tests check that each fixture passes its validator and the combined validator, unchanged; that the replay equals the live state at the same revision without the live fields; that each commander validator refuses each God-only field; that a God view needs `view_mode: "god"`; and, per validator, that a mutated fixture fails with the path of the changed field. Each boundary rule was removed in turn and the named case failed: the contact, orders, standing-order, supply-site and formation side or key rules, the broadcast and codeword key lists, the recommendation `received_turn` rule and the God-only name list each failed only their own case. Requiring `destination` on orders failed the fixture tests.

## Not covered

The desk UI, the map-counter click, bundling, serving and the deployment target. Other endpoints: `/api/scenarios`, `/api/map`, `/api/export`, `/api/clock`, `/api/new`, `/api/mode`, `/api/standing-orders`, `/api/recommendations`, `/api/formations`, `/api/advance`, `/api/chat` bodies, and the `{error}` body of a 4xx or 5xx response. `apps/web` still reads only the cursor (`readBattleCursor`).
