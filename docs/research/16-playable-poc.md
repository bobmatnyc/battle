# Little Round Top playable POC

**Current layout:** POC code and commands below are relative to `apps/poc/`. See [monorepo layout](28-monorepo-and-stack-direction.md) and the [POC run guide](../../apps/poc/README.md).

**Date:** 2026-11-05. **Authority:** The user's explicit request to implement a Python simulation with SQLite, human-versus-computer play, a Civil War battle, historical topography/hex overlay, movement control and a throwaway map/chat UI. This is an implementation record, not historical calibration.

## Historical basis and map provenance

The National Park Service describes the 20th Maine's July 2, 1863 defense against the 15th and 47th Alabama at Little Round Top. This supplies the setting and unit-name inspiration, not the prototype's personnel counts or tactical placements. [NPS monument account](https://www.nps.gov/places/20th-maine-monument.htm), accessed 2026-11-05.

The backdrop is a crop of John B. Bachelder's **Map of the battle field of Gettysburg. July 1st, 2nd, 3rd, 1863**, LOC item 99447491, resource `g3824g.cw0325000a` (first-day sheet). The LOC publication field says **1876**, while its generated citation/date fields say **1879**; the interface uses the publication-field date. This is a postwar historical map, not an in-battle live position feed. Static printed positions belong to the source sheet, not the running game's units. [LOC record and rights](https://www.loc.gov/resource/g3824g.cw0325000a/), accessed 2026-11-05 through indexed official metadata; direct page retrieval returned 403. The 1600-pixel map image was successfully retrieved from LOC's image service and inspected.

Credit: **Library of Congress, Geography and Map Division.** LOC says its digitized geography/map collections are free to use and reuse unless an item has a restrictive rights advisory. No such advisory was present in the inspected metadata. No proprietary game art or tables are included.

Asset lineage:

- Source: `https://tile.loc.gov/image-services/iiif/service:gmd:gmd382:g3824:g3824g:cw0325000a/full/1600,/0/default.jpg`
- Bundled source: `static/assets/gettysburg-source.jpg`, 1600 × 2075 pixels.
- Crop rectangle in that image: `(790, 1380, 1060, 1590)`, then resized to 1080 × 840 with Lanczos and saved as `static/assets/little-round-top.jpg`.
- The crop has a manually chosen summit anchor near canvas `(530,600)`. This is approximate visual registration, not surveyed GIS control.
- Physics uses 50 m center spacing independently of screen size. Its approximate 1.2 × 0.9 km extent is an authored working scale. A fixed grid does not prove that the image's geographic scale or elevation alignment is accurate.
- Cell elevations, woods, rocky ground and cover are authored mathematical zones. They are **not extracted contour measurements**. The Terrain toggle exposes the actual simulation zones.

A high-resolution whole-map/crop request returned 403; the POC retains the successfully retrieved low-resolution crop. No remote map request occurs when playing.

## Playable scope and abstractions

Three Union and three Confederate detachments start with 40 personnel and 1,600 rounds each. Names refer to parent regiments; suffixes A/B/C are synthetic detachments, not claims about actual Civil War company establishments. All have identical baseline skill; there are no national/ethnic ability bonuses. Fixed summer/dry/clear conditions and the 16:30–17:00 window are scenario choices.

The Union wins if it retains an effective command through turn 60, or all attacking formations break. Confederates win by holding within one hex of the summit for three consecutive turns with no effective Union unit there, or by breaking the Union command. Both commands losing effectiveness in the same interval produces a draw. The terminal result is presented as adjudication, not a secretly instantaneous battlefield report.

Movement orders persist until arrival, replacement or routing. Units automatically engage visible enemies within five hexes. Routed units withdraw toward headquarters; aggregate casualties and morale can make a formation ineffective. Routing is not mutiny, and mutiny is not implemented. Weather variation, naval combat, spies, quartermasters, supply delivery, unit remixing and civilian behavior remain deferred.

## Deterministic rules

All numeric coefficients below are POC tuning values, not researched weapon statistics.

- **Space/time:** odd-row pointy hex grid, 24 × 21 cells; adjacent centers 50 m apart; 30-second simulation steps. Terrain and initial weather are fixed.
- **Movement:** A* route cost uses open/woods/rocky costs of 100/145/170 plus three cost points per meter uphill. Per-turn movement credit starts at 115 and falls with fatigue/suppression, minimum 45. At most one hex is traversed per turn. Accumulated credit is capped at 400. Occupied intermediate hexes are avoided. Occupied destinations and conflicting proposals wait; swaps/stacking are forbidden. This conservative conflict resolution can cause congestion and requires new orders to resolve some standoffs.
- **Observation:** range limit seven hexes; intermediate elevations can occlude line of sight; four intervening woodland cells block sight. There is no light/smoke model. Delivered enemy contacts contain location and a coarse size estimate, not exact strength/ammo; stale contacts disappear after six turns.
  - *Grid edge (Architect ruling 2026-11-07, option c):* a sight line between two hexes in the first or last column can pass through a point one column outside the grid. `grid.visible` skips such a point: it adds no elevation, obstacle or woodland. Treating it as a block (option a) and clamping it to the nearest grid hex (option b) were not taken. Before this rule the off-grid point raised `KeyError`, so only lines that crashed change.
- **Comms:** runner orders take one plus `floor(distance(HQ, last reported unit position)/8)` turns. Reports and acknowledgements take one turn. Runners are abstract message delays, not physical vulnerable couriers. Communications do not stop when an HQ marker is occupied; physical HQ capture is deferred.
- **Fire:** each eligible formation fires up to one round per effective troop per turn. Engine-visible enemy selection uses nearest range with a stable identifier tie break. Range, target cover and shooter suppression generate integer exposure. Exposure accumulates to aggregate casualties at each hundred points. All volleys use the same pre-casualty troop strengths. Models cannot choose casualties or alter these coefficients.
- **Condition:** morale falls with casualties and severe suppression; fatigue rises on movement and recovers while stationary. Suppression decays every turn. Morale below 28 or fewer than 12 effective troops triggers routing. Cohesion, command trust and detailed weapon inventories remain design work; the `skill` datum is reserved and does not yet modify fire.

Local sensing/engagement occurs in the engine. Headquarters and model commanders see delayed reports. Thus a unit can fire before its commander learns that contact occurred. Detailed terrain is assumed known for this small POC; unmapped/incorrect cartography is deferred.

## Inference boundary

OpenRouter's documented chat-completions endpoint is used server-side with JSON output and the configured moderate model (`openai/gpt-4.1-mini` by default). [OpenRouter API overview](https://openrouter.ai/docs/api_reference/overview), accessed 2026-11-05.

The computer commander plans every three turns. Its request contains its own delivered unit reports, stale enemy contacts, orders, objective, and local known terrain. The engine validates side ownership, coordinate bounds, move/hold shape, one order per unit and a three-order maximum. Unexpected fields, nonexistent units and invented effects are rejected. Timeout, provider error, malformed response or illegal orders selects a deterministic standing-mission fallback. Accepted model decisions, input observations, usage, model identity and fallback reason are logged; credentials and raw error bodies are not.

The staff adviser receives only the Union view and its known terrain. It can suggest orders, but only the player's explicit dispatch sends them. Chat is a single-turn adviser in this POC: previous messages remain visible and stored but are not automatically included in later inference prompts. Natural-language advice can still be mistaken; it never directly changes simulation state.

Live outputs are not deterministic. Replay reuses archived decisions without contacting the provider. `--offline` prevents inference in both command and chat. Provider usage is bounded per request to 650 completion tokens, with an 18-second network timeout; those are ceilings, not a full-session spend budget.

## Persistence and failure behavior

`games` stores latest state; `units` gives normalized current unit records; `events` and `decisions` retain append-only audit entries; `snapshots` records each revision; `messages` stores staff chat. Snapshot JSON also contains terrain, orders and pending reports. This is intentionally redundant and can grow rapidly; it is suitable for short POC battles, not a production persistence design.

A state transition and its events/decisions/chat records commit in one SQLite transaction. Revision and game-ID checks reject stale mutations. One process serializes mutations; GET requests can read the last committed snapshot while inference runs. There is no multi-process server support, authentication system or internet multiplayer lobby. Localhost-only binding and origin checks are appropriate to this local experiment, not deployment security.

Replay reconstructs each state from the previous snapshot and recorded action, comparing exact equality. Order IDs/versions, event sequence, simulation turns and decision indices support audit; the full general causal-event graph remains future work. Screens show observer-filtered replay. The authoritative export is locked until battle completion. Old games remain in SQLite and can be verified by ID using the CLI.

Rules/scenario version: `poc-1` / `little-round-top-v1`. There is no migration framework. Changing transition rules requires a compatibility decision for old saves; replay under arbitrary newer rules is not guaranteed.

## Validation record

- Component suite: **31 tests passed** on Python 3.14.8, including atomic chat/decision commits and fault-injected chat storage rollback.
- Full scripted headless run: completed after 22 turns with 714 events, Union result; 24 stored revisions replayed identically. This is a smoke fixture, not balance or historical evidence.
- Live OpenRouter: one computer decision and one staff assessment returned successfully using `openai/gpt-4.1-mini`, with server-side validation and logged usage. No fallback was needed in those checks.
- Browser: map rendered; a Union unit was selected, a destination clicked and a runner order dispatched. Advancing time completed with an OpenRouter commander decision. Replay was opened, restored to revision 0, and correctly disabled live orders. The persisted battle resumed after server restart. No narrow-screen emulation was performed.
- Offline HTTP smoke: map, movement order, turn advance, chat persistence and replay passed; hidden-state export, secret-file paths, foreign origins/hosts and stale revisions were rejected.
- **Not performed:** historical calibration, Evo execution, deployment, multiplayer load testing or claims of optimal tactics.

### Final UI follow-up

The in-app browser stalled on a native JavaScript confirmation during reset. Native confirmations were removed from both reset and staff-order dispatch. Reset now uses a two-click inline control; staff proposals show their exact order list with an explicit dispatch button. An isolated JavaScript DOM harness (`node scripts/smoke_ui.mjs`) verified the two-click reset without a native dialog, and the HTTP API reset successfully archived the test battle and created a fresh turn-zero game. Subsequent browser clicks remained unresponsive in that session, so the updated reset click sequence was not reverified in-browser. The fresh page rendered successfully and a full-page screenshot is saved in `artifacts/battle-poc.jpg`. Earlier movement, live inference, chat, report delivery and replay interactions were verified in the browser.

### Language and multiplayer intent update — 2026-11-05

The demo now includes a visible product-intent panel for era-specific unit/staff speech, default i18n support, internal player messaging and cooperative/opposing/terrain-control scenarios. A non-mutating presentation adapter renders recognized existing dispatches through English message keys and arguments; future agent/fallback prose uses the `civil-war-en-v1` voice profile. Existing model messages remain verbatim and canonical `poc-1` replay inputs remain unchanged. English is the only shipped locale; player messaging and network multiplayer remain specifications. See [requirements and contracts](17-language-localization-and-multiplayer.md).

## Clock update — 2026-11-05

The manual Advance UI has been superseded by server-owned start/pause and speed controls, plus recorded replay playback. See [clock and replay semantics](18-simulation-clock-and-replay.md). Earlier turn-based descriptions refer to the unchanged internal 30-second resolution, not the current player control.

## Summit-loss wording fix — 2026-11-05

A browser smoke test on a fresh `poc-8` battle moved U1 from hex 11,14 to 11,9 and ran the scripted commander with no other orders. The battle ended at 16:38 (turn 16) with a Confederate win, "held the summit uncontested for 90 seconds". U1 was the only Union formation within one hex of the summit at 11,15; U2 at 13,15 is two hexes away. C2 reached 12,16 at turn 14 and held it for three intervals.

That result is the rule recorded above: the Union wins by keeping an effective formation through turn 60 (17:00), and the Confederates win at once by holding within one hex of the summit for three consecutive turns. The 17:00 deadline is the defender's win condition, not a guaranteed battle length. The engine (`battle/engine.py`), the computer-commander policy and this record agreed; the player-facing text did not. The mission panel said "on the high ground", which does not identify the one-hex ring, and neither it nor the README said that the capture ends the battle before 17:00.

Decision: the rule stands and the rules edition stays `poc-8`. Only the mission panel (`static/index.html`) and the README changed. They now name the summit hex and its six neighbours (the dashed ring on the map), the 90-second uncontested hold, and the immediate end even before 17:00. No transition, event text or saved battle changed, so existing saves replay unchanged. `tests/test_presentation.py::MissionTextTests` reproduces the smoke-test battle and checks that both texts state the rule. The ring, hold window and deadline remain authored POC values, not historical measurements.

## Stylized map update — 2026-11-05

**User requirement:** use a stylized map rather than photographic imagery, with the supplied Google Maps screenshot as a visual template. The live map now uses original SVG cartography: muted open-ground/woodland/rock colors, clean labels, terrain symbols, a measured scale bar, subtle hexes and 5 m contours. Elevation toggles stronger relief and contour labels. The historical raster is retained only as reference.

Terrain fills come from the existing scenario cells; contour segments interpolate their elevations on triangles connecting neighboring cell centers. These are authored POC heights, not surveyed contours. No Google tiles, service integration, modern roads, hotels or tourist POIs are included. Roads/watercourses will require validated scenario geography before rendering them as tactical features. The map palette and annotation style are presentation choices; rules, terrain classifications, movement costs and saved battles are unchanged.

Implementation: `static/cartography.js`, consumed by the existing SVG map. Rendering uses public scenario terrain only and adds no enemy observations. The current scenario exposes all terrain to the commander as a setup assumption. JavaScript syntax and existing UI smoke checks passed.

Browser verification: loaded the new renderer, toggled elevation and hex visibility, selected U1 and targeted hex 12,13 with Dispatch runner enabled. No order was submitted and the paused battle was unchanged. Browser console reported no errors. Visual evidence: `artifacts/battle-stylized-map.jpg`.
