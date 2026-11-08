# 74 — Playable eras, slice 1: Concord North Bridge on both desks

**Date:** 2026-11-08. **Task:** bt-T10 slice 1. Follows [43](43-concord-scenario-spec.md), [47](47-poc13-part-b-command-and-smoothbore.md) to [50](50-concord-command-fire-release.md), [64](64-map-features-evidence.md) and [70](70-ts-desk-slice-1.md) to [73](73-ts-desk-slice-3.md). Concord North Bridge (`concord-north-bridge`, the current v2 entry only) is now a player scenario in the POC desk (`apps/poc/static`) and the TypeScript desk (`apps/web`). No engine rule, rules edition, snapshot label or saved-game format changed. The v1 entry and the three doc 48 variants stay headless only.

## 1. What changed

| Area | Change | Files |
|---|---|---|
| Catalog | `PLAYER_SCENARIOS` is Little Round Top, Hougoumont, Concord. Little Round Top stays the default. The headless catalog keeps its order (Concord third, then its v1 entry, Pegasus, Hill 223, Gergovia, Cannae) and lists no entry twice. | `apps/poc/battle/bootstrap.py` |
| Desk opponent | `ScenarioEntry.desk_scripted_opponent` (default `False`). When it is `True`, `BattleService._opponent_control` asks the commander for the entry's scripted control (`command_policy.scripted_policy`) in `scripted` mode, the same call the headless runner makes for its opponent. Only Concord sets it. | `apps/poc/battle/scenario_entry.py`, `apps/poc/battle/services/battle.py`, `apps/poc/battle/scenario_concord.py` |
| Concord brief | An authored `SideBrief` for the provincial player and a `DeskBrief`, each line with a provenance label (§3). | `apps/poc/battle/scenario_concord.py` |
| 1775 staff answer | The scripted staff answer uses the voice's address from `presentation.VOICE_ADDRESS` ("Colonel" for 1775). Voices without an entry there, 1863 and 1815, keep "General". | `apps/poc/battle/services/commander.py` |
| POC desk | Report ages in unit cards, contacts and the unit panel, and the "plans every …" cadence (3 intervals), come from the view's `seconds_per_turn`. Before, they used a fixed 30 s. The empty dispatch list is scenario-neutral (§4). | `apps/poc/static/app.js` |
| TS desk | A finished battle shows the brief's outcome headline (win, loss or draw for the viewing side) and the server's reason in `#outcome`. Before, the desk said only "Battle complete." in the notice line. | `apps/web/src/panels.ts` (`outcomeText`), `apps/web/src/desk.ts`, `apps/web/index.html`, `apps/web/style.css` |
| Fixtures | `record.py` re-recorded. Only `packages/contracts/fixtures/scenarios.json` changed: the Concord row was added. | `packages/contracts/fixtures/scenarios.json` |

Both desks already drew water, the North Bridge and the two Concord roads from the commander view and the briefing cells ([72](72-roads-buildings-slice-1.md) §1, [73](73-ts-desk-slice-3.md) §1). This slice adds no rendering code for them.

## 2. Default ruling bt-D08: the desk opponent

**Default applied, pending the owner:** the desk's computer side plays an entry's scripted control only for entries newly made player-facing. The switch is data on the entry (`desk_scripted_opponent`), not a global setting.

- **Concord.** The British play `scripted-concord-regulars-v1` on the desk, as in every headless Concord run. The decision record is the one the headless runner's opponent call makes from the same state (`test_concord_desk_opponent_plays_the_regulars_policy_as_headless_does`). In `openrouter` mode the British still play the scripted policy and no provider is asked (`test_concord_desk_opponent_stays_scripted_in_openrouter_mode_without_a_provider_call`); staff chat still uses the selected mode.
- **Little Round Top and Hougoumont.** Unchanged: the desk opponent plays `scripted-fallback-v1` (`fallback_orders`), and in `openrouter` mode asks the model as before. Hougoumont's French therefore do not play the headless gate attacker on the desk. `test_little_round_top_and_hougoumont_keep_the_plain_desk_opponent` pins this. The digest comparison in §6 shows their desk play, headless runs and saved-game continuation are byte-identical to `0fadd68`.
- **Owner question.** Should Hougoumont's desk opponent also play its gate controls? That is out of scope here and changes its interactive behaviour.

## 3. The Concord brief and its sources

Desk text is display only: it is never stored in a snapshot and never put in a prompt. The British side has no brief, and the desk shows a side's brief only to that side's player (`presentation.scenario_brief`).

| Text | Value | Provenance (entry `provenance` key) |
|---|---|---|
| Campaign | CONCORD · 19 APRIL 1775 | sourced: S47 (`desk.campaign`) |
| Place, objective | North Bridge · BRIDGE OBJECTIVE · key BRIDGE, ring shown | sourced: S47, S49 (`desk.place`) |
| Conditions | SPRING · APRIL · FIXED POC CONDITION | authored: no weather source read (`desk.conditions`) |
| Kicker, tagline, title | THE NORTH BRIDGE · "Advance to the bridge." · "Clear the bridge" | authored headings, not quotations (`brief.provincial.headings`) |
| Subhead | You command the provincial companies. The computer commands the British light companies guarding the bridge. | sourced: S47, S48; that the computer commands the British is authored (`brief.provincial.subhead`) |
| Mission | March the column down from the ridge to the North Bridge. Colonel Barrett's order stands: do not fire unless first fired upon. … Hold the bridge and the ground around it (the dashed ring) for 60 seconds with no effective British company there, before **09:35**. | sourced: Barrett's order (S47, read through a summarising fetch, so the wording may be paraphrased); reconstruction: the command's word to fire stands for Buttrick's order (S47, [50](50-concord-command-fire-release.md)); authored: the ring, 60 seconds (2 intervals) and 09:35 (20 intervals from 09:25) restate the entry's victory, doc 43 §2 (`brief.provincial.mission_text`) |
| Win | The bridge is carried. | sourced: the British withdrew and the militia held the bridge (S47); wording authored (`brief.provincial.win`) |
| Loss | The regulars hold the bridge. | authored: an outcome the record does not show (`brief.provincial.loss`) |
| Draw | The battle ends in a draw. | the shared draw line of the other entries |

S47 to S49 are in [09 — sources](09-sources.md#concord-north-bridge-spec--2026-11-06). The address and voice are the entry's own: `colonial-1775-en-v1`, which addresses the player as Colonel ([47](47-poc13-part-b-command-and-smoothbore.md)). The mission text quotes no order verbatim; it states Barrett's order in the desk's words and names him.

## 4. POC desk: interval length and the empty dispatch list

- Every report age now multiplies by `state.seconds_per_turn`: the unit list ("…s AGO"), contact cards ("…s old", "Identified … ago"), the unit panel ("…s old") and the commander status ("plans every …s", three intervals). Little Round Top, Hougoumont and Concord all use 30 s, so their display is unchanged; `smoke_ui.mjs` checks the derivation with a 60 s view (120 s ages, "plans every 180s").
- The empty dispatch list said "**General, the line awaits your orders.** Three detachments stand ready. … dispatch a runner". It now says "**The command awaits your orders.** Your detachments stand ready. We await word of the enemy from the field. Select a blue unit on the map or below it. Choose a destination hex and send the order, then start the clock." This is the only text change at Little Round Top and Hougoumont. Concord has four companies, a Colonel and spoken orders within reach, so the old text was wrong there.

## 5. Checks

| Check | Concord addition |
|---|---|
| `tests/test_playable_concord.py` (new, 8 tests) | desk opponent equals the headless call; no provider call in `openrouter` mode; Little Round Top and Hougoumont keep the plain opponent; only Concord opts in; catalog list; brief and provenance keys; the 1775 staff answer says "Colonel"; a desk battle plays offline to a result within 20 intervals |
| `tests/test_concord.py` | flipped: Concord is a player scenario, third; no duplicate headless ids |
| `tests/test_replay_sides.py` | loops over `PLAYER_SCENARIOS`, so it now covers Concord. Concord's companies carry no tools, so its no-leak case checks hidden units only, not works. Run time of the module (6 tests): 31.7 s at `0fadd68`, 37.1 s here, +5.3 s |
| `tests/test_presentation.py`, `scripts/smoke_http.py` | the scenario list has three ids |
| `scripts/smoke_ui.mjs` (DOM harness, in `make test-poc`) | switches to Concord through the picker and Reset; header 09:25, 19 April 1775, North Bridge · Concord, Massachusetts, no turn or revision label; brief; water fill, both roads and the North Bridge with its reconstructed status; a move order sent; report ages from `seconds_per_turn`; outcome headlines |
| `scripts/check_route_sight.mjs` | a Concord road case: B2 marches the town road over road edges (9 steps); Concord has no building, so no sight case |
| `scripts/map_screenshots.mjs` (real browser, POC desk) | Concord through the desk's picker: screenshots at fit and 2×, grid on and off, legend; header; 21 water hexes; roads and bridge; P1's move order on record; clock at 60× to the outcome headline; every British decision `scripted-concord-regulars-v1` |
| `make smoke-web` (real browser, TS desk) | switches to Concord: header, bridge with road span, water hexes, unit card, a move order accepted, the clock run to the outcome headline, every British decision the regulars' policy |
| TS tests | `api.test.ts`, `orders.test.ts`, contracts `scenarios.test.ts` expect three ids; the `$.default` refusal now uses `pegasus-bridge`; new `outcomeText` test |

## 6. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/eras-1-c3beab5/` in the main checkout, for code head `c3beab5`; `MANIFEST.txt` lists every file with its command and exit code.

| Gate | Result |
|---|---|
| `npm ci --offline` | exit 0 |
| `npm run typecheck` | exit 0 |
| `npm test` | web 74 of 74, contracts 62 of 62 (was 73 and 62) |
| `make test-poc` | `Ran 752 tests … OK` (was 744), then `smoke_ui.mjs` (Concord UI passed), map geometry, map features and route and sight, exit 0 |
| `make headless-poc` | Little Round Top unchanged: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions) |
| `make smoke-poc` | exit 0 (after `c3beab5`, which updated its scenario-list assertion) |
| `make smoke-web` | `SMOKE PASSED`, including the Concord switch: British won at the 09:35 deadline, "The regulars hold the bridge.", 7 British decisions, all `scripted-concord-regulars-v1` |
| `node scripts/map_screenshots.mjs` (POC desk, real browser) | `HARNESS PASSED`; Concord played to the deadline through the desk |

Both browser runs exit 3 (BLOCKED, never a pass) when no browser runs, and stop the POC, the browser group and the profile on every exit path, as before; this slice did not change that code.

**Digest comparison against `0fadd68`.** `digests.py` extends doc 72's script. It ran on a `git archive` of `0fadd68` and on this tree, and `cmp` exits 0 for every comparison (`run-digests.log`, `digests/`):

- **Every headless catalog entry** (Little Round Top, Hougoumont, both Concord entries, Pegasus Bridge, Hill 223, Gergovia, Cannae): opening state, commander view, doc 72's generic scripted play (Concord `n/a`, as before), the full headless run summary and its final state. Replay `identical` everywhere. Timings differ and are dropped before `cmp`.
- **Desk play** of Little Round Top and Hougoumont: one player hold order, then clock intervals to the end; the final state and the digest of every revision. Both opponents still record no `policy` (the plain fallback control).
- **Saved games:** a Little Round Top and a Hougoumont desk game written by `0fadd68` at interval 9, then continued to the end by `0fadd68` and by this tree. Final states and every revision are identical.
- **Concord desk play (head only):** British win at 20 intervals; every opponent decision is `scripted-concord-regulars-v1`.

**Each new check can fail** (`mutations.log`, `mutate.py`): Concord without `desk_scripted_opponent`; Hougoumont with it; the contact age back to a fixed 30 s; the old empty dispatch text; the TS outcome always the win line; the 1775 staff answer back to "General". Each mutation turns its check red.

**Finding.** Without the opt-in, a Concord desk battle cannot advance: the plain fallback control orders a British company onto the river (`InvalidOrder: That hex is impassable water`), and the first decision interval fails. The scripted opponent is what makes Concord playable on the desk, not only closer to the headless runs.

**Screenshots.** POC desk: `screenshots/concord-{fit,zoom2x}-grid-{on,off}.png`, `concord-legend.png`, `concord-order.png`, `concord-outcome.png`, with the Little Round Top and Hougoumont sets regenerated and `concord-hex-tooltips.txt`. TS desk: `smoke-web/desk-concord-features.png`, `smoke-web/desk-concord-outcome.png`, with the existing set. Pegasus Bridge and Hill 223 keep their read-only renders; Concord's moved to the desk.

**Evidence for main `6b648a6`** (git-ignored, in the main checkout): `apps/poc/artifacts/eras-1-main-6b648a6/` holds the gate run on main after `npm ci --offline`: `npm-typecheck.log` (exit 0), `npm-test.log` (web 74/74, contracts 62/62), `make-test-poc.log` (752 tests OK plus the JS checks), `make-headless-poc.log` (replay `identical`), `make-smoke-poc.log`, `make-smoke-web.log` (`SMOKE PASSED`, Concord to "The regulars hold the bridge."), `harness.log` (`HARNESS PASSED`) with `screenshots-map/` and `screenshots-smoke-web/`, and two fault runs: `fault-smoke-web-deadline.log` (3 s deadline) and `fault-map-sigint.log` (SIGINT), each failing the run with a leftover check showing no process or profile left. `MANIFEST.txt` lists the commands and exit codes. The independent browser check of `6b648a6` is in `apps/poc/artifacts/eras-1-6b648a6/web-qa/`; it found the British hold the bridge for the whole game, as `scripted-concord-regulars-v1` guards it and falls back only when two of three companies break.

## 7. Deferred and next slices

- **Next playable entries:** Pegasus Bridge ([52](52-pegasus-bridge-scenario-plan.md) to [54](54-pegasus-scenario-runs.md)) and Hill 223 ([56](56-hill-223-scenario-plan.md), [61](61-hill-223-scenario-runs.md)). Each needs a brief with sources, the `desk_scripted_opponent` decision and its own smoke steps.
- **Gergovia and Cannae** wait on the BCE date ruling bt-D07 (how the desks show a 52 BCE or 216 BCE date). Cannae's outcome also waits on D34.
- **Hougoumont's desk opponent** (gate controls on the desk) is an owner question (§2), not part of this slice.
- **Concord's variants and v1 entry** stay headless. A variant on the desk would need its own policy check: the scripted policies are written for the catalog geometry (doc 48).
- **TS desk text.** The TS desk shows no staff chat and no empty-dispatch prose, so §4's text change has no TS counterpart.
- **TS desk display gaps seen in `smoke-web/desk-concord-outcome.png`.** The brief says "the dashed ring", as Little Round Top's does, but the TS desk draws the objective as a small circle with no ring. Adjacent counters on one row overlap (P2 to P4 on the muster road), so their labels are partly hidden. Neither is new to Concord.
