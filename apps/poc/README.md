# battle

A playable local command-game POC: **you command Union detachments at Little Round Top; a computer commander controls the Confederate advance.** Python runs the simulation, SQLite stores the battle, and a buildless map/chat UI provides the command desk.

**Status — 2026-11-05:** local implementation authorized and built. Python + SQLite are the user's explicit POC choices, superseding the earlier research-only phase and graph-store requirement for this experiment. No deployment or Evo execution has occurred.

**Deployment:** keep serving on the workstation for now; Evo is a future option. From the monorepo root, `make package-evo` prepares the code and public assets; see the [Evo launch and verification runbook](../../docs/research/31-evo-target-and-typescript.md). Local runs below are for development.

## Run

Run these commands from `apps/poc/`. From the repository root, use `make poc` or `make poc-offline`. All code, static assets, SQLite saves, artifacts and local configuration for this experiment live here. Shared research remains in `../../docs/research/`.

Python 3.11+; no Python runtime packages or frontend build required. MapLibre GL JS 5.12.0 browser assets are bundled locally with their license. Tested here on Python 3.14.8.

```sh
python3 -m battle
```

Open **http://127.0.0.1:8874**. The server binds only to loopback. Stop it with Ctrl-C. Battles are stored in `data/battle.sqlite`; restarting loads the newest battle with the clock paused. **Reset** restarts the scenario at 16:30 with the clock paused and archives the previous game instead of deleting it. It works while running or replaying, returns the clock speed to the 10× default, and preserves only the God Mode selection.

For fully local play without inference calls:

```sh
python3 -m battle --offline
```

The supplied OpenRouter credential is stored in `.env.local` with owner-only permissions. It is excluded by `.gitignore`, loaded server-side, and never sent to the browser. `.env.example` documents the two settings. Default model: `openai/gpt-4.1-mini`. Inference sends the game's authorized observation and, for staff chat, the entered question to OpenRouter. Choose **Local scripted commander** for a no-network session; that setting also applies to chat. One commander call occurs every three turns; chat makes one call per submitted question. Failures use a visible deterministic fallback. Model availability and provider billing remain external.

## Play

1. Click a unit on the map or its detachment card to open strength, ammunition, morale, suppression, fatigue, current mission and local judgment. Enemy contacts show estimates only.
2. Choose **Move**, **Give an order**, **Hold**, **Split** or **Combine** in the unit panel. Move selects a destination hex; Give an order opens a shared order-template composer. Split chooses a troop count and adjacent hex; Combine joins an adjacent compatible formation into the selected survivor. Instructions travel through the command network. Split/combine require 60 seconds of safe regrouping after delivery; minimum 12 troops per child and maximum 80 combined. Use Reset to enable these rules in a fresh battle.
3. Drag the map to pan; use **+ / −** to zoom and **Fit** to restore the battlefield view.
4. **Start clock** to let both sides act autonomously. **Pause clock** stops after any interval already in progress. Use **− / +** to slow down or speed up (0.5×–60×; default 10×). Units keep moving and firing under their received orders.
5. You are located with **U2**, marked **YOU** on the map. Moving U2 moves headquarters. Orders to that detachment use local voice; other orders, reports and acknowledgements travel by foot courier over the terrain. Travel and forwarding take simulation time. A routed or lost headquarters cannot issue orders; subordinate units continue autonomously.
6. Use the **God Mode On/Off switch** to inspect every formation, exact strength, courier traffic and the full event timeline. It works in live play and replay. This observer view disables orders and staff chat; turn it off to command again.
7. Open **Troop analysis** before starting or at any time to review reported strength, ammunition, readiness and report age. Select a unit, review its suggested doctrine, and dispatch **Standing orders** independently of its mission. Use Reset for the latest rules.
8. Use **Staff chat** for advice or proposed orders. Proposals execute only when you review and dispatch them.

Keep an effective formation in the summit hex or the six hexes around it (the dashed ring on the map) until the 17:00 scenario deadline, or break the attacking formations. The deadline is the Union's win condition, not a guaranteed battle length: the battle ends at once, even before 17:00, when Confederate troops hold that ground for 90 seconds (three 30-second intervals) with no effective Union formation there, or when the Union command breaks. The clock starts at 16:30 as an authored scenario choice, not a precise historical timestamp.

**Replay** pauses live time and opens recorded Union knowledge, with play/pause, speed controls and a scrubber. Returning to live leaves the clock paused. Orders and staff chat also pause this local demo before submission; start the clock again to continue. The command desk shows location, calendar date and one battlefield timeline, with matching timestamps in replay. Internally it advances in committed 30-second steps; there is no player-facing turn counter. Slow inference may lower actual playback speed. The server keeps running if you close the tab. See [clock semantics](../../docs/research/18-simulation-clock-and-replay.md). After battle completion, the full audit unlocks with all events, decisions, and replay verification. The ordinary API and agent observations preserve fog of war. The explicit local debug endpoints `GET /api/state?view=god` and `GET /api/replay?revision=N&view=god` expose omniscient observations, including during active battles. This is a trusted single-player development tool; it is not a multiplayer permission system.

## What is implemented

- A 24 × 21 hex battlefield, 50 m between adjacent centers, rendered with MapLibre as a stylized vector map, with local GeoJSON tiling, pan/zoom, terrain colors, 5 m contours and an optional hex overlay. SVG is the fallback when the vector renderer is unavailable.
- Initially three 40-person aggregate detachments per side, with ammunition, morale, fatigue, suppression, terrain cover, and deterministic accumulated casualties.
- Terrain-weighted pathfinding, elevation/woodland line of sight, conservative occupancy rules, and simultaneous fire.
- A player/controller attached to an existing command detachment (Union U2, Confederate C2), with moving headquarters, local voice, terrain-costed couriers, forwarding and disrupted command.
- Click-to-inspect units and contacts, shared hold/move/rest/retreat/resupply/reconnoiter/dig-in order templates, and delayed split/combine actions with conserved personnel/ammunition and archived formation lineage.
- Authored roads that speed troop/courier movement, buildings that add cover and block sight, and persistent fortifications. **Dig in** uses conserved tools and labor, adds fatigue, and pauses under contact; new works reach the map through observation and reports.
- Finite ammunition points, terrain travel for pickup, contact-interrupted loading/rest, and recorded mission outcomes.
- Unit commanders recommend rest, resupply, retreat or digging in using local conditions. Delivered advice raises a clickable gold flag and unit-card badge; review, dispatch or dismiss it. Suggestions and responses are logged and expire.
- Explicit God Mode with all units, both sides’ dispatches, complete event inspection, recorded decisions and message queues.
- Versioned runner orders; autonomous defense, cover-seeking and pre-rout withdrawal under standing intent; delayed friendly and enemy reports.
- Progressive strength/type/weapon estimates, source-aware identification and scout advantages. U3/C3 are authored scouting detachments in new battles; spy observer assets are supported in fixtures, without a deployment UI.
- Bounded OpenRouter orders with validation and a scripted fallback; staff proposals require player dispatch.
- Atomic SQLite state/event/decision/chat persistence, revision checks, archived battles, and replay without fresh model calls.

This is **based on the actual Little Round Top engagement**, not a calibrated recreation. The NPS identifies the 20th Maine's fight with the 15th and 47th Alabama; the six detachments, equal starting strengths, exact positions, time window, ammunition and combat coefficients are authored for this POC. The command map renders the simulation’s authored terrain as original vector cartography, using the supplied Google Maps example as a visual reference. Its contours interpolate the authored cell elevations; they are not surveyed heights. The bundled postwar Bachelder survey-based image is retained as historical reference, with no validated georeferencing or terrain extraction. See [scenario provenance and limitations](../../docs/research/16-playable-poc.md).

## Verify

```sh
python3 -m unittest discover -s tests -v
python3 scripts/smoke_http.py
node scripts/check_map_geometry.mjs
node scripts/smoke_ui.mjs
python3 -m battle --headless --db /tmp/battle-check.sqlite
python3 -m battle --db /tmp/battle-check.sqlite --replay GAME_ID_FROM_HEADLESS_OUTPUT
```

The 232-test component suite covers geometry, blocked movement, communications, fog of war, combat conservation/simultaneity, hostile or failed model responses, persistence conflicts, and transaction rollback. By default the headless path runs scripted commanders for both sides and checks exact transition replay. Live inference is a separate smoke check, not part of the deterministic suite.

## Headless player runs

A model can play one chosen side headless while the other side follows the scripted control. Live runs on 2026-11-06 (OpenRouter, Little Round Top, Union player, effort `high`) confirmed the model ids `anthropic/claude-sonnet-5.5` and `openai/gpt-6-astra`, and confirmed that the `reasoning.effort` field is applied: Astra reported 3,211 reasoning tokens for one decision, and a Sonnet probe reported 47. Tests use stub providers and openers only (`tests/test_headless_player.py`, `tests/test_openrouter_adapter.py`).

The request asks for structured output as a strict JSON Schema (`response_format` type `json_schema`) that matches the order reply `{"text", "orders": [{"unit_id", "stance", "destination"}]}`. Sonnet ignored the earlier `json_object` format and answered in prose, so the adapter also accepts exactly one JSON object given bare, in a Markdown fence, after prose, or as tool-call arguments. It never repairs or invents orders: engine validation still runs, and a reply with no object or with several objects falls back with its telemetry kept. Extraction takes only a top-level object. An object inside an array (`Orders: [{...}]`) or inside an outer structure that never closes is a fragment, and the reply falls back with `JSONDecodeError`. A brace region that fails to decode, or an array holding an object, counts as a rival candidate, so a reply holding one beside a valid object falls back with `AmbiguousJSON` rather than guessing which one the model meant. Reply text above 64 KiB falls back with `ReplyTooLarge` without being scanned, and the scan below that is linear. A reply with `finish_reason` `length` falls back with `ReplyTruncated` even when its content parsed.

```sh
python3 -m battle --headless --db /tmp/player-run.sqlite \
  --player-side union --player-provider openrouter \
  --model anthropic/claude-sonnet-5.5 --effort high
python3 -m battle --db /tmp/player-run.sqlite --replay GAME_ID_FROM_OUTPUT
```

| Flag | Default | Meaning |
|---|---|---|
| `--player-side` | `union` | Side the player controller commands |
| `--player-provider` | `scripted` | `scripted` or `openrouter`. `openrouter` refuses to start without `OPENROUTER_API_KEY` |
| `--opponent` | the scenario's choice | Scripted control for the other side: `scripted-fallback-v1`, or in a gated scenario `scripted-gate-defender-v1` for the defender and `scripted-gate-attacker-v1` for the attacker. A gate control is refused for any other side |
| `--player-policy` | the scenario's choice | Scripted control for a scripted player side, by the same rule as `--opponent` |
| `--model` | `OPENROUTER_MODEL`, else `openai/gpt-4.1-mini` | Requested OpenRouter model id |
| `--effort` | none | `low`, `medium` or `high`, sent as `{"reasoning": {"effort": ...}}` in the request body. Shape confirmed live on 2026-11-06 |
| `--max-tokens` | `OPENROUTER_MAX_TOKENS`, else 4000 with an effort, else 650 | Completion token limit. Reasoning tokens count against it; Astra used 3,211 at `high` |
| `--timeout` | `OPENROUTER_TIMEOUT`, else 90 with an effort, else 18 | Provider timeout in seconds. The slowest live Astra call took 19.2 s |
| `--scenario` | `little-round-top` | Scenario id from the catalog. Also sets the scenario for new interactive games. An unknown id is refused with the list of known ids |

The provider flags need `--player-provider openrouter`; `OPENROUTER_EFFORT` sets the effort from the environment or `.env.local`. With no flags, the run is the scripted baseline: the Union uses the direct scripted orders path, and its output and replay are unchanged.

The player receives its own side's mission (`command_policy.system_prompt`, text and prompt version from the scenario entry; `lrt-side-v2` for Little Round Top) and the side's authorized, fog-limited observation. Version `lrt-side-v2` covers the strict `json_schema` reply contract and order acceptance; runs before it recorded `lrt-side-v1`. In `poc-8` games each observed unit carries `accepts_orders` and `order_refusal`, and `order_contract.orderable_units` lists the units that accept orders now. The refusal is `command_disrupted` when the side's command detachment is routed or lost, `not_reported` without a delivered report, or `reported_routed`, `reported_lost` or `reported_merged` from headquarters' latest delivered report; the prompt tells the model to order only listed units. These are the same checks `engine.validate_order` applies, read from delivered reports, so a unit that has broken but not yet reported stays orderable, exactly as the engine would accept the order. The fields are observation-only with no rule effect, so the rules edition stays `poc-8`; games in earlier editions get no such fields. It never receives the opponent's objective, plan or ground truth. Each player decision is committed as a `decision` action before the next interval, and its orders are issued for the side named in `decision.side`. Decisions saved before this field existed carry no side and replay as Confederate decisions, so old saves replay unchanged. This is command plumbing with no rule effect, so the rules edition stays `poc-8`.

Every decision record, stored in the `decisions` table with the state snapshot, carries:

| Field | Meaning |
|---|---|
| `side`, `source` | Commanding side; `openrouter` for an accepted model decision, `scripted` otherwise |
| `requested_model`, `model` | Model asked for; model the provider reported (null if not reported) |
| `effort`, `prompt_version` | Requested reasoning effort; player prompt version |
| `latency_ms`, `usage`, `response_id` | Provider round trip measured in the commander service; provider token usage and response id |
| `finish_reason` | Provider stop reason; `length` means the reply was cut off at the token limit |
| `reply_format` | How the order object was found: `json` (the content parsed whole), `extracted` (from prose or a fence), `tool_call` (tool-call arguments), or `none` when no object was parsed |
| `proposed_orders` | Raw orders the model proposed |
| `validation` | `{"valid": bool, "error": str}`; null when the provider returned nothing |
| `rejected_proposal` | The proposed orders when validation rejected them |
| `fallback`, `fallback_stage`, `fallback_reason` | True when scripted orders replaced the model; stage `provider_error`, `invalid_response` or `validation_failed`. For a provider failure, the adapter's safe reason (`HTTP 429`, `TimeoutError`, `JSONDecodeError`, `AmbiguousJSON`, `NoContent`, `ReplyTooLarge`, `ReplyTruncated`); a reason that is neither `HTTP` plus three digits nor in the allowlist `services/commander.py` `KNOWN_REASONS` is replaced by the exception type. Otherwise the exception type. Never response content or credentials |

A fallback is recorded with `source: "scripted"` and `fallback: true`, never as a model decision. Prompts and credentials are not stored. The initial snapshot's `run` object records the rules edition, scenario label, scenario id and variant, prompt version, player side, provider, model, effort, response format (`json_schema:commander_orders` for OpenRouter, null for scripted runs) and opponent control. Replay re-applies the recorded decisions and never calls a provider.

## Architecture

The demo now uses explicit service boundaries and constructor dependency injection. `battle/bootstrap.py` wires simulation, repository, commander/provider, clock and scenario interfaces. Command/query/replay services are independent of HTTP and SQLite; the browser has an injected API client and assessment component. Services run in one process, with unchanged battle rules and saves. [Architecture, contracts and migration guide](../../docs/research/27-service-architecture-and-dependency-injection.md).

Scenarios are data. Each is one `ScenarioEntry` (side ids, names and roles, missions, player side, units and command attachment, map, setting, victory kind, rules edition, prompt version, order catalog, variant); `bootstrap.py` builds the catalog from `PLAYER_SCENARIOS`, and only Little Round Top is player-facing. `POST /api/new` accepts an optional `"scenario"` id. `--player-side` takes a side id of the chosen scenario. [Entry format and `poc-9` limits](../../docs/research/38-scenario-catalog.md); [sides and victory kinds](../../docs/research/39-scenario-sides-and-victory-kinds.md).

New code should use these interfaces and the composition root. Preserve atomic event/state commits, authorized observations and inference-free replay when replacing adapters.

## Code map

| File | Responsibility |
|---|---|
| `battle/contracts.py`, `battle/bootstrap.py` | Service contracts and dependency composition |
| `battle/services/` | Battle commands, queries, commander decisions, replay and headless use cases |
| `battle/adapters/` | Rules/scenario, OpenRouter and HTTP resource adapters |
| `battle/config.py` | Startup configuration with secret-safe representation |
| `static/api-client.js`, `static/troop-analysis.js` | Injected browser transport and assessment component |
| `battle/scenario_entry.py`, `battle/scenario.py` | Scenario-entry format and builder; the Little Round Top entry (authored terrain, forces, missions) |
| `battle/standing.py`, `battle/tactics_v8.py` | Persistent doctrine, independent courier delivery and bounded contact reactions |
| `battle/analysis.py` | Read-only troop assessment from headquarters knowledge |
| `battle/recommendations.py` | Local commander advice, delivered flags, acceptance/dismissal and expiry |
| `battle/features.py` | Roads, buildings, persistent fieldworks and observer reports |
| `battle/grid.py` | Hex geometry, pathfinding, line of sight |
| `battle/clock.py` | Server clock, pacing, pause/resume and speed |
| `battle/engine.py` | Orders, movement, combat, reports, outcomes |
| `battle/formations.py` | Delayed split/combine, conservation, lineage and reporting |
| `battle/comms.py` | Physical command location, voice and courier transport |
| `battle/recon.py` | Observation quality, estimate ranges and dated identification |
| `battle/tactics.py` | Standing local contact reactions |
| `battle/engine_v1.py`, `battle/engine_v2.py`, `battle/engine_v3.py` | Frozen transitions for existing poc-1/poc-2/poc-3 battles |
| `battle/presentation.py` | Period dispatch voice and initial localization keys |
| `battle/inference.py` | Compatibility facade for earlier callers |
| `battle/runtime.py` | Recorded transitions and deterministic replay |
| `battle/orders.py` | Versioned order catalog, bounded missions, recovery and finite ammunition pickup |
| `battle/storage.py` | SQLite transactions, snapshots and audit records |
| `battle/server.py` | Local HTTP API and static UI |
| `static/map-view.js` | MapLibre camera, local projection, vector terrain and fallback |
| `static/cartography.js` | Shared terrain geometry and SVG annotations/fallback |
| `static/` | Throwaway command map and chat UI |
| `tests/` | Granular component and persistence tests |

## Product requirements reflected in the demo

Units and staff address the player in **period-appropriate language**. The current Civil War demo uses keyed English dispatch templates and era-specific agent instructions. Saved facts, delivery times and structured commands retain their original meaning.

**Internationalization is a default requirement:** UI, scenario text, dispatches and staff advice must support player locales independently of faction and simulation rules. The current demo remains English-only; its dispatch catalog is an initial foundation, not complete localization.

**Internal player messaging** will provide direct and team correspondence, separate from staff chat. In-battle dispatches must obey scenario communication limits and recipient permissions.

**Multiplayer scenarios** include cooperative missions, antagonistic engagements and terrain control. Terrain objectives can combine with either allied or opposing teams. These multiplayer capabilities are specified, not implemented in the current human-versus-computer demo.

**Campaign play** adds a “Risk-like” strategic map: deploy armies and units to different fronts, assign subordinate commanders, and redeploy reserves. Local battle results feed back into territory control and force condition. Travel, communications and force accounting connect the scales; campaign allocation remains planned.

Open **Command language & multiplayer design** below the unit cards to see this intent in the app. Full contracts and acceptance criteria: [language, localization and multiplayer](../../docs/research/17-language-localization-and-multiplayer.md).

## Scope after the POC

The broader design remains a strategy and tactical-command game with aggregate units, historical communications through WWII, fog of war, expanded specialist missions, land/sea/amphibious battles, and larger command hierarchies. Training, general force remixing, civilians, mutiny, mobile supply delivery, weather variation, multiplayer networking and campaign provisioning are **not implemented** here. Personnel losses are aggregated; no individual characters or soldier progression exist.

The original [project brief](../../docs/research/00-original-project-brief.md) and [research notebook](../../docs/research/README.md) preserve the long-term design. SQLite is the current POC store; a future graph implementation remains a separate decision. Evo host/resources/model access must be verified before running there.

Map rendering uses bundled [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js), with no external tile service or API key. [Research and implementation notes](../../docs/research/19-open-source-map-rendering.md) distinguish the current browser tiling from proposed PMTiles archives for larger, georeferenced maps.

**New battle rules:** new games use `poc-11` ([building gates](../../docs/research/41-poc10-gates.md) on scenario maps that declare them, with a [push through a held gateway](../../docs/research/44-poc11-gateway-push.md); Little Round Top plays as in `poc-9`, which added scenario-defined sides and victory kinds) with [map features and Dig in](../../docs/research/24-map-features-and-digging-in.md), [common order templates](../../docs/research/23-common-order-templates.md), finite ammunition points and recorded mission outcomes, plus [unit details and split/combine](../../docs/research/22-unit-panel-and-formation-actions.md), command units, God Mode and standing contact reactions. Existing `poc-1` through `poc-8` battles keep their original behavior for exact replay; use **Reset** to try the new orders. God Mode can inspect all rule editions. No orders are required for a unit to defend itself. Courier rates and friendly forwarding are authored approximations; signal flags, wired networks, interception, messenger capacity and command succession are not yet implemented.

**Common orders:** click a friendly unit → **Give an order** → choose **Hold**, **Move**, **Rest**, **Retreat**, **Replenish ammunition** **Reconnoiter** or **Dig in**. Move/retreat/recon need a destination hex. Rest recovers fatigue without healing; replenishment requires travel to a marked friendly ammunition point and draws from finite stocks. Send the order and start the clock. Completion and interruptions return through dispatches and the unit panel.

Roads, building footprints and fortifications in this POC are authored examples, not surveyed historical placements. Digging improves the occupied hex over time and leaves cover behind. See [feature rules, knowledge and limitations](../../docs/research/24-map-features-and-digging-in.md).

**Commander advice:** use **Reset** for the new rules, then start the clock. A gold flag appears when a recommendation reaches headquarters. Click it to review the dated advice and choose **Dispatch suggested order** or **Dismiss**. Units act autonomously while awaiting your response. See [recommendation rules and delivery](../../docs/research/25-commander-recommendations.md).

**Standing orders and assessments:** Balanced, Preserve the force, Hold ground firmly, and Observe and screen define persistent local discretion. Recommendations use reported condition and role; they become orders only when dispatched. Reading analysis leaves the clock alone; sending instructions pauses it. Assessments also work in old saves and replay. [Contract and verification](../../docs/research/26-standing-orders-and-troop-analysis.md).

**Unit counters:** map icons show strength/type and S/E/M ratings (skill, energy, morale); energy is 100 minus fatigue. Cards spell out the same attributes. Enemy contacts retain estimates and unknown ratings. Select an icon for orders and split/combine; old saves need Reset for formation actions. [Display contract](../../docs/research/29-unit-counters-and-readiness.md).
