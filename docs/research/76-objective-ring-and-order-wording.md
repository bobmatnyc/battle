# 76 — The TS desk's objective ring, and order wording from the side's own command profile

**Date:** 2026-11-08. **Task:** bt-T11 (Architect 13:48Z). Follows [75](75-playable-eras-slice-2.md) §8, which listed two desk display gaps: the TS desk draws no objective ring, and the POC desk says "dispatch a runner" and "Movement orders travel by runner" in every era. Both are fixed here from what the viewing side's commander view already carries. No engine rule, rules edition, contract type, dispatch template, snapshot label or saved-game format changed.

## 1. What changed

| Area | Change | Files |
|---|---|---|
| TS desk ring | When `scenario_brief.objective.ring` is true, the map draws a dashed, unfilled ring round the objective hex, r = 53/25.5 hex radii (the POC desk's 53 px on its 25.5 px hex), so it encloses the centres of the six neighbouring hexes. The ring has `pointer-events="none"` inside the objective group, which already had it. No brief, or `ring` false, draws no ring. No scenario id is read. | `apps/web/src/render.ts`, `apps/web/style.css` |
| POC desk wording | `static/order-wording.js` (new) builds the send button, its tooltip, the map tip, the mission help line and the standing-order note from `command.profile` (label, methods, reach flags). It never reads an order's `transport`, which only the God view carries ([`views.ts`](../../packages/contracts/src/views.ts)). | `apps/poc/static/order-wording.js`, `app.js`, `index.html`, `troop-analysis.js` |
| Not changed | The server's `order.move.sent` / `order.hold.sent` templates (`presentation.py`) and the `engine_v1.py` message still say "by runner": they are recorded state, so replay digests depend on them (§3). | — |

**Which scenarios draw the ring.** The brief sets `ring` when the victory kind is `hold-objective` (`presentation.scenario_brief`). Little Round Top and Concord: ring. Hougoumont (`hold-compound`): none. Pegasus Bridge (`seize-and-hold`) and Hill 223 (`raid-and-return`): none, following their victory kind. The POC desk draws the same set from the same flag.

**The wording rule.** The carriers are the parts of the profile label after " · ", split on " / ", in label order. A part naming a trumpet signal is dropped when the methods list `signal`: the signal is a separate broadcast, not an order carrier ([60](60-broadcast-signal-exploit-and-recover-force.md)). "voice" is dropped for an order to another detachment when the profile has no voice reach (`voice_reach` or `voice_reach_from_entry`), because voice then reaches only the command's own detachment, which keeps its "Give local order" button. The standing-order note keeps voice, since a standing order may go to the command's own detachment. A view with no command profile is a legacy headquarters, whose orders went by runner, and reads "runner".

| Profile (`comms.PROFILES`) | Send button |
|---|---|
| 1863 · voice / foot courier | Dispatch by foot courier ↗ |
| 1815 · voice / foot runner | Dispatch by foot runner ↗ |
| 1775 · voice / runner | Dispatch by voice or runner ↗ |
| 1944 · radio / voice / runner | Dispatch by radio, voice or runner ↗ |
| 1918 · voice / runner | Dispatch by voice or runner ↗ |
| 52 BCE · trumpet signal / voice / runner | Dispatch by voice or runner ↗ |
| 216 BCE · trumpet / voice / mounted messenger | Dispatch by voice or mounted messenger ↗ |
| 216 BCE · voice / mounted messenger | Dispatch by voice or mounted messenger ↗ |

The tooltip is the label and the means, for example "1944 · radio / voice / runner: orders go by radio, voice or runner, as distance allows." The help line reads "Movement orders travel by …". The map tip ends "· dispatch by …".

## 2. Checks

| Check | Addition |
|---|---|
| `apps/web/test/render.test.ts` | `a hold-objective brief rings the objective`: one ring, centred on the objective hex, r = 53/25.5 radii, larger than the neighbour-centre distance. `no ring without the brief's ring flag or without a brief`: neither draws one, and the objective mark stays |
| `apps/web/scripts/smoke-features.ts` `checkRing`, called from `smoke-browser.ts` | On each of the five scenarios: a ring drawn exactly when the POC's brief sets it. Where drawn: stroke dash `5px, 5px`, fill `none`, `pointer-events` `none`, `elementFromPoint` on its stroke does not return the ring, radius larger than the neighbour-centre distance. Little Round Top screenshot `desk-lrt-ring.png`. The existing counter and hex clicks run after it |
| `apps/poc/scripts/smoke_ui.mjs` | The send button, tooltip, map tip and help line on all five desk scenarios, and the command's own detachment still "Give local order". The standing-order note at Little Round Top. Every profile in `comms.PROFILES` (read from Python, not copied) against the table above; the 1944, 1918 and both Roman profiles never read "by runner" alone in any of the five strings |

## 3. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/eras-3-e2f9180/` in the main checkout, for code head `e2f9180` (base `60f8675`). `MANIFEST.txt` lists every file and each gate's exit code. Each log starts with its command and ends with `EXIT=`.

| Gate | Result |
|---|---|
| `npm ci --offline` | exit 0 |
| `npm run typecheck` | exit 0 |
| `npm test` | web 76 of 76 (was 74; the two ring tests), contracts 62 of 62 |
| `make test-poc` | `Ran 765 tests … OK`, then `smoke_ui.mjs` with "Order wording passed", map geometry, map features, route and sight; exit 0 |
| `make headless-poc` | Little Round Top: winner union, 60 turns, 2,573 events, the same unit strengths, replay `identical` (63 revisions), as at the base |
| `make smoke-poc` | exit 0 |
| `make smoke-web` | `SMOKE PASSED`; ring at Little Round Top and Concord (r=53 at hex radius 25.5), none at Hougoumont, Pegasus Bridge and Hill 223 |
| `node apps/poc/scripts/map_screenshots.mjs` | `HARNESS PASSED`; the POC desk loads `order-wording.js` under its CSP, and `screenshots/pegasus-order.png` shows "Dispatch by radio, voice or runner ↗" |

`git diff --stat main -- packages/contracts/src` and `-- apps/poc/battle apps/poc/tests` are empty (`diff-stat-*.log`).

**Red first.** On the pre-change sources with the new checks: `render.test.ts`, 1 of 9 fails (`a hold-objective brief rings the objective`: 0 rings, expected 1); `make smoke-web` fails at Little Round Top, "objective ring drawn 0, brief ring true"; `smoke_ui.mjs` fails at the standing-order note, "by voice or runner" where "by voice or foot courier" is expected (`red/`). The no-ring test passes on the old tree, as it should: it pins behaviour that already existed, and mutation m2 shows it can fail.

**Each new check can fail** (`mutations/`): 5 of 5 single mutations turn their check red: the ring branch removed (m1); the ring drawn always (m2); the send button back to "Dispatch runner ↗" (m3); the help line back to "Movement orders travel by runner." (m4); the trumpet signal kept as a carrier (m5).

**Digest comparison against `60f8675`** (`run_digests.sh`, doc 74's `digests.py` copied unchanged): every headless catalog entry, timings dropped, and desk play of all five player scenarios to the end; `cmp` exits 0 for each (`run-digests.log`, `digests/`).

**Screenshots.** TS desk: `smoke-web/` (with `desk-lrt-ring.png`). POC desk: `screenshots/`.

## 4. Deferred

- **Signals panel.** The desks still render no `signals`. Showing them needs a typed contract field; today they exist in fixtures only.
- **Pegasus and Hill 223 layout.** Counters overlap the canal bridge label and the works labels collide at Pegasus; the 2× view leaves Hill 223's ravine and shack off-screen ([75](75-playable-eras-slice-2.md) §8).
- **Server dispatch text.** The recorded `order.move.sent` template says "by runner" in every era. Changing it changes recorded state and replay digests, so it waits for a rules-edition decision.

## 5. Review notes

**code-critic on e2f9180: APPROVE.** No CRITICAL, HIGH or MEDIUM findings.

1. §1 said the ring encloses the six neighbouring hexes. At r = 53/25.5 ≈ 2.08 hex radii it encloses their centres (1.73 radii), not the whole hexes (2.73 radii). The POC ring has the same proportion. Fixed in this doc.
2. `apps/poc/static/order-wording.js` `means()` decides whether an order can go by voice from the profile flag `voice_reach_from_entry`, not from the entry's reach. `scenario_command._reach_problems` allows a reach of 0; such an entry would show "voice or runner" when no order travels by voice. Shipped entries are unaffected (Hill 223: 1, Cannae: 1, Gergovia: 2). The reach is already in the viewing side's own `command` object (`command.voice_reach`), so reading it there shows no other side's data.
3. `apps/poc/static/app.js` `renderControls`: when the send button reads "Give local order ↗", its tooltip still holds the dispatch means.
4. Observer safety: the wording reads only `state.command.profile`. In God Mode `command` is still the player side's own; other sides appear only under `commands`, which the wording never reads. No test proves the wording ignores God-view fields.
5. Fail-Open Check: a missing profile or a label without " · " gives "runner". These fallbacks choose display text only, record nothing and advance no state.
6. No stale ring on a scenario switch: `desk.ts` rebuilds the SVG through `mapMarkup` each render, and `make smoke-web` asserts ring count 0 after ringed scenarios.
7. The ring selector `.objective .objective-ring` outranks `.objective circle`, so the `5 5` dash applies (measured 5px, 5px).
8. Evidence in `apps/poc/artifacts/eras-3-e2f9180/` checked: mutations m1–m5 red, red-first logs fail for the stated reasons, gates as reported, contracts and POC engine diffs empty, no absolute home-directory paths in `git log -p`.
9. No mutation covers a change that reads `order.transport` or God-view data.
10. The `apps/poc/README.md` code map does not list `static/order-wording.js`; its general `static/` row covers it.

**web-qa on e2f9180: PASS** (TS ring; POC wording per era; God Mode toggle). Evidence: `apps/poc/artifacts/eras-3-e2f9180/web-qa/`.

1. Hill 223 (1918): the button says "voice or runner" while the brief says the out-of-earshot patrol is reached only by runner. The brief describes the patrol's reach and the button the side's methods, so they do not contradict, but a player could wonder why voice is offered.
2. With the command's own HQ selected, "Give local order ↗" keeps the dispatch tooltip (as critic note 3).
3. The server's recorded dispatch line "by runner" is unchanged. It reads consistently after the 1863 "foot courier" button, and in 1944 another template already says "by word of mouth".
4. Coverage limits: Cannae and the opposing side's wording are not reachable in the player UI; POC desk console errors were not captured independently.
5. The TS desk's "Start battle" resets the shared POC game (existing behaviour).

None blocks (Completion Standard fix bar). Critic note 1 is fixed here; the rest are recorded, not scheduled.
