# 75 — Playable eras, slice 2: Pegasus Bridge and Hill 223 on both desks

**Date:** 2026-11-08. **Task:** bt-T10 slice 2. Follows [74](74-playable-eras-slice-1.md), the Pegasus Bridge documents [52](52-pegasus-bridge-scenario-plan.md) to [54](54-pegasus-scenario-runs.md) and the Hill 223 documents [56](56-hill-223-scenario-plan.md), [58](58-small-unit-rout-and-open-assault.md) to [61](61-hill-223-scenario-runs.md). Pegasus Bridge (`pegasus-bridge`) and Hill 223 (`hill-223-patrol`), the current entries only, are now player scenarios in the POC desk (`apps/poc/static`) and the TypeScript desk (`apps/web`). Their variants and sensitivity entries stay headless. No engine rule, rules edition, snapshot label or saved-game format changed.

## 1. What changed

| Area | Change | Files |
|---|---|---|
| Catalog | `PLAYER_SCENARIOS` is Little Round Top (still the default), Hougoumont, Concord, Pegasus Bridge, Hill 223. `HEADLESS_SCENARIOS` is written out in its old order and lists no entry twice. | `apps/poc/battle/bootstrap.py` |
| Desk opponent | Both entries set `desk_scripted_opponent`, so the computer side plays the entry's scripted control on the desk, as headless runs do: the German guard and reserve play `scripted-pegasus-guard-v1`, the German battalion plays `scripted-hill-223-german-v1`. | `apps/poc/battle/scenario_pegasus.py`, `apps/poc/battle/scenario_hill223.py` |
| Briefs | A `SideBrief` for the British player at Pegasus and for the American player at Hill 223, and a `DeskBrief` for each, every line with a provenance label (§3). Variants get no brief. | same files |
| Slice 1 review fixes | §5. | `scenario_roster.py`, `scenario_concord.py`, `concord_sensitivity.py`, `presentation.py`, `services/commander.py`, `tests/test_replay_sides.py` |
| POC checks | The DOM harness, the route and sight check and the browser harness cover both entries (§6). The harness's read-only renders are gone: no headless entry with drawn marks remains. | `apps/poc/scripts/` |
| TS desk | No source change: the desk already drew water, marsh, woods, bridges with their known state, and works, and its contracts accept both commander views (checked on every live state and sampled replays of one game each). The browser smoke plays both. | `apps/web/scripts/smoke-browser.ts`, `smoke-features.ts` |
| Fixtures | `record.py` re-recorded. Only `packages/contracts/fixtures/scenarios.json` changed: two rows added. | `packages/contracts/fixtures/scenarios.json` |

## 2. The desk opponent (default ruling bt-D08)

The ruling applied in [74](74-playable-eras-slice-1.md) §2 is applied again: an entry newly made player-facing plays its own scripted control on the desk. Little Round Top and Hougoumont are unchanged; Hougoumont's opponent is still the owner question of 74 §2.

- **Pegasus Bridge.** The German side plays `scripted-pegasus-guard-v1` ([54](54-pegasus-scenario-runs.md) §4): the guard holds its posts (entry data), the charges follow the entry's demolition rule, and the two reserve groups are ordered forward at their alarm turns. The first desk decision equals the headless runner's call from the same state (`test_each_desk_opponent_plays_its_entrys_policy_as_headless_does`). In `openrouter` mode no provider is asked (`test_each_desk_opponent_stays_scripted_in_openrouter_mode_without_a_provider_call`).
- **Hill 223.** The German side plays `scripted-hill-223-german-v1`, which sends no order: posture, facing and surrender are entry data ([61](61-hill-223-scenario-runs.md) §3). The plain fallback control would have sent the German groups orders the entry never gives them.
- **Player roles.** Pegasus: the British coup-de-main company (D Company, 2nd Ox and Bucks), as [52](52-pegasus-bridge-scenario-plan.md) §2 and the entry's `player_side` set it. Hill 223: the Company G commander, who reaches the patrol only by runner. That is [56](56-hill-223-scenario-plan.md) §2 and §9 q1, taken as the default by the Dc0 ruling in [61](61-hill-223-scenario-runs.md) §3 (the brief named "doc 61/62 §3"; doc 62 is Gergovia, so 61 §3 is the source).

## 3. The briefs and their sources

Desk text is display only: never stored in a snapshot, never put in a prompt. Each label below is the entry's `provenance` key. Sources are in [09 — sources](09-sources.md): Pegasus S50 to S56, Hill 223 S40 and S57 to S59.

**Pegasus Bridge (British player; voice `wwii-1944-en-v1`, address Major).**

| Text | Value | Provenance |
|---|---|---|
| Campaign, place | NORMANDY · 6 JUNE 1944 · Caen Canal bridge · BRIDGE OBJECTIVE | sourced: S51, S52; S51 p. 1 para 2 (`desk.campaign`, `desk.place`) |
| Conditions | SUMMER · NIGHT, CLOUDY · FIXED POC CONDITION | sourced: S52 sheet 2; the fixed condition is authored (`desk.conditions`) |
| Kicker, tagline, title | COUP DE MAIN · "Take the bridge intact." · "Seize the canal bridge" | authored headings; "coup de main" is S51's title (`brief.british.headings`) |
| Subhead | You command D Company, 2nd Ox and Bucks, landed by glider beside the bridge. The computer commands the German bridge guard and the reserve that answers its alarm. | sourced: S51 p. 1 para 3, S52 sheets 1-2, S51 p. 1 para 2, S54; reconstruction: the reserve stands in for S54's German response; authored: the computer's side (`brief.british.subhead`) |
| Mission | Take the bridge intact and hold it until relieved; wired with charges, and the guard has orders to blow it; 24 Platoon carries the sappers under Capt Neilson RE, who clear the charges on the bridge; hold within one hex for one minute, keep it until relief at **03:25**; the codeword Ham. | sourced: task (S51, S52 sheet 1 §2), 24 Platoon and Neilson (S52 sheet 2), charges removed (S51), Ham (S54, secondary); inferred: wiring and the order to blow (S54, secondary); reconstruction: 03:25 is S51's "3 hours after our landing" from 00:25; authored: one hex, one minute, the clearing and the Ham trigger restate the entry (`brief.british.mission_text`) |
| Win | The bridge is held until relief. | sourced: S51 p. 1 para 3, S52 sheet 4; wording authored |
| Loss | The bridge is lost. | authored: an outcome the record does not show |

**Hill 223 (American player; voice `wwi-1918-en-v1`, address Sir).**

| Text | Value | Provenance |
|---|---|---|
| Campaign | ARGONNE · 8 OCTOBER 1918 | sourced: S57 p. 58, S40; Châtel-Chéhéry S57 p. 51-52; "Argonne" from S58 (secondary) |
| Place, objective | Command post at the shack · PATROL OBJECTIVE · key SHACK | sourced: the little shack (S40) where the commander stood (S57 p. 60); the hex is authored |
| Conditions | AUTUMN · MIST, THEN CLEAR · FIXED POC CONDITION | sourced: S40 narrative; fixed condition authored |
| Kicker, tagline, title | HILL 223 · "Silence the guns." · "Bring the patrol back" | authored headings; the tagline echoes S57 p. 60 |
| Subhead | You command Company G, 328th Infantry, on Hill 223. The computer commands the German battalion on the hill across the valley. | sourced: S57 p. 58-60; the German unit is a disclosed conflict (S57, S58), so none is named; authored: the computer's side; the role is the Dc0 default |
| Mission | Guns on the hill southwest across the valley pin the company; Acting Sergeant Early's patrol of 17 has gone round by the woods; word reaches it only by runner; stand within one hex of the command post at the shack, then bring at least 5 men and one prisoner back within one hex of the company post before the counter-attack hour, **10:30**. | sourced: S57 p. 59-62; reconstruction: the post at the shack (S40, S57 p. 60); authored: runner only (voice reach 1, doc 56 §6), one hex, 5 men, one prisoner and 10:30 as the end restate the entry's victory |
| Win | The patrol is back with prisoners. | sourced: S57 p. 61-62; wording authored |
| Loss | The patrol has not come back with prisoners. | authored |

`test_pegasus_brief_is_labelled_and_states_the_seize_and_hold` and `test_hill_223_brief_is_labelled_and_states_the_raid_and_return` check every key and label. Hill 223's `scope` provenance now says it was headless at first (Dc0, doc 56 §9 q6) and is a player scenario since this document.

## 4. Played results, and what the desk cannot show

Both play offline to a result with no model or provider call (`test_a_desk_battle_at_pegasus_plays_offline_to_a_result`, `test_a_desk_battle_at_hill_223_plays_offline_to_a_readable_result`, both browser runs, §6).

- **Pegasus Bridge: German win at interval 5 (00:27:30), "The bridge is lost." Reason: "The Caen Canal bridge was destroyed before it could be held."** This holds with 24 Platoon ordered onto the bridge at the start, as the scripted British run orders it. It is the default result of [54](54-pegasus-scenario-runs.md) §5: the guard sees the platoons at touchdown, arms the charges at interval 1 and fires them at 5, and the outcome rests on the authored 4-interval delay and 2-interval clearing. This slice changes neither. A player who wants the bridge intact cannot get it on the default entry.
  Default ruling bt-D09 (pending the owner): keep the always-blown bridge on the desk and tell the player. The British brief ends with "Note: on this entry the bridge is blown at **00:27:30** whatever you order, because the charge timings are authored, not sourced." Both desks show it in the mission text before play. Its label `brief.british.note` reads "authored: bt-D09 default …" and cites the `demolition` label and [54](54-pegasus-scenario-runs.md) §5. The note is display text only: play, decisions and the recorded digests are unchanged (`test_pegasus_brief_is_labelled_and_states_the_seize_and_hold`, `smoke_ui.mjs`, both browser runs).
- **Hill 223: American win at interval 27 (06:58:30), "The patrol is back with prisoners." Reason: "The raiders reached the German command post and 10 of them came back by the deadline. They brought back 75 captives."** This equals the default headless run of [61](61-hill-223-scenario-runs.md) §5. The raid-and-return reasons of `08e7ef2`/`ec1be7b` reach the outcome line unchanged. The reason says "by the deadline" for a return made at 06:58; that is the existing reason text.

**Mechanics the desk cannot show the player** (listed here, not hidden):

1. **Demolition arming and its countdown.** The arming at interval 1 and the firing at 5 are guard-side truth. The British view still knows the bridge as `charges` when the battle ends; the destruction reaches the player only in the outcome reason. No report of the explosion arrives first. The brief's bt-D09 note (above) says before play that the bridge is blown at 00:27:30; the desk still shows no arming or countdown.
2. **Sapper clearing.** There is no sapper or charge order. The catalog (`ORDER_CATALOG`) has none, so none was added to either desk. Clearing happens only while 24 Platoon (`clears_charges`) stands on the bridge hex; the desks show no progress.
3. **Seizure and relief count.** The seize-and-hold counters (`captures`, `seized`) are in `s['victory']`, which no commander view carries. The brief states the rule; the desk shows no count.
4. **The Ham codeword.** A delivered codeword is in the view's `signals`, and the TS contract types it, but neither desk renders `signals`. Under the default no Ham is sent before the bridge is blown.
5. **The patrol's return order.** Hill 223's patrol carries its departure move and its return (`exploit`, with `resume_after_withdrawal`) as entry data. The desks show its stance and target, not the return intent, the pause on withdrawal or the return hex.
6. **Raid and return conditions.** Whether the raid is made, men home and captives held are victory state, not in the view. Captures reach the player only as the 1918 dispatch "We have taken N prisoners" once its runner arrives.
7. **The German surrender rule and gun facing** (reach, odds, rear arc, turn delay) are entry data the American player never sees, as intended.

## 5. Fixes carried from the slice 1 review

| Item | Fix | Test |
|---|---|---|
| (a) `_opponent_control`'s `except UnknownScenario` branch | A duel save opened by the Little Round Top catalog: in scripted mode the decision records no `policy`; in `openrouter` mode the advance still raises `UnknownScenario`, asks no provider and commits nothing, as at `0fadd68`. | `test_a_label_the_desk_catalog_does_not_know_keeps_the_call_made_before_the_opt_in` |
| (b) Derived entries inheriting the flag | `scenario_concord.before` (so Concord v1), `concord_sensitivity.earshot` and Pegasus's `_relabel` (the crossed and delay runs) set `desk_scripted_opponent=False`. A test lists every entry the catalogs, variant and sensitivity tables build; only Concord, Pegasus and Hill 223 carry the flag. | `test_only_the_intended_entries_carry_the_desk_opponent_flag` |
| (c) `validate()` | Refuses `desk_scripted_opponent=True` unless `scripted` names a control for every side, or the entry has gates. | `test_the_desk_opponent_flag_needs_a_scripted_control_for_every_side` |
| (d) 1775 staff closing | `presentation.staff_orders_text(voice)`: 1775 "Give your orders by word of mouth to the companies within earshot, or send them by runner;", 1944 "Send your orders by wireless, by word of mouth close by, or by runner;", 1918 "Pass your orders by word of mouth close by, or send them by runner;". 1863 and 1815 keep "Send your instructions by runner;". | `test_the_closing_follows_each_voice_and_its_transport` |
| (e) Concord subhead provenance | Cites S49 for the companies guarding the bridge and labels "light" as authored (the spec's word, doc 43 §1, not in S47 to S49 as read). The displayed text is unchanged. | `test_concord_subhead_cites_s49_for_the_guard_and_labels_light` |
| (f) Works check skip | `test_replay_sides` skips by id (`NO_DUG_WORKS`, Concord only) and asserts no works hide there. | `test_no_side_replay_shows_the_other_sides_unseen_units_or_works` |
| Scenario-list tests | `test_presentation`, `smoke_http.py`, the DOM harness mock, `api.test.ts` and `orders.test.ts` read `PLAYER_SCENARIOS` or `scenarios.json`. The ids are pinned once each: `test_pegasus_and_hill_223_follow_the_three_and_the_default_stays` and the contracts fixture test. | |

The active-battle case of `test_replay_sides` runs 4 intervals at Pegasus (`ACTIVE_INTERVALS`), because the default demolition ends that battle at the fifth.

## 6. Checks

| Check | Addition |
|---|---|
| `tests/test_playable_eras_2.py` (new, 13 tests) | Catalog order and listing; headless order; flag on intended entries only; both desk opponents equal the headless call; no provider call in `openrouter` mode; the unknown-label branch; `validate`; both briefs and labels; the Concord subhead note; the staff closing per voice; both played to a result |
| `tests/test_pegasus.py`, `tests/test_hill_223.py` | Flipped: each is a player scenario with the flag |
| `tests/test_playable_concord.py`, `test_concord.py`, `test_presentation.py` | Read the catalog; the opt-in test lists three ids and is renamed `test_only_the_newly_playable_entries_opt_in` |
| `tests/test_replay_sides.py` | Loops over `PLAYER_SCENARIOS`, so it covers both. Run time: see §7 |
| `scripts/smoke_ui.mjs` | Both through the picker and Reset: header (00:25, 6 June 1944; 06:45, 8 October 1918), no turn or revision label, brief, canal and marsh fills, three roads, the canal bridge with its charges dot and "· charges" label, the Orne bridge, the shack objective and old trench, an order sent, the outcome headlines |
| `scripts/check_route_sight.mjs` | Pegasus: R1 marches the Bénouville road 7 steps over road edges. Test arrangement: the state has no demolition rule, since the default battle ends at interval 5. Hill 223 has no road or building, so no case |
| `scripts/map_screenshots.mjs` (real browser, POC desk) | Both on the desk: screenshots at fit and 2×, grid on and off, legend, tooltips; header; marks drawn; an order on record; the clock at 60× to the outcome headline and reason; every German decision the entry's policy |
| `make smoke-web` (real browser, TS desk) | Both from the picker: header, marks (canal bridge as known with charges, Orne bridge, water and marsh counts; old trench and woods count), unit card, a move order accepted, the clock to the headline and reason, every German decision the entry's policy |
| TS tests | `api.test.ts`, `orders.test.ts` read the fixture; contracts `scenarios.test.ts` pins five ids and now uses `gergovia-recall` for the `$.default` refusal |

## 7. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/eras-2-827d06a/` in the main checkout, for code head `827d06a`; `MANIFEST.txt` lists every file and each gate's exit code.

| Gate | Result |
|---|---|
| `npm ci --offline` | exit 0 |
| `npm run typecheck` | exit 0 |
| `npm test` | web 74 of 74, contracts 62 of 62 (unchanged counts: the changed tests assert more, none were added) |
| `make test-poc` | `Ran 765 tests … OK` (was 752), then `smoke_ui.mjs` (Pegasus and Hill 223 UI passed), map geometry, map features, route and sight; exit 0 |
| `make headless-poc` | Little Round Top unchanged: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions) |
| `make smoke-poc` | exit 0 |
| `make smoke-web` | `SMOKE PASSED`: Concord to "The regulars hold the bridge." (20 intervals); Pegasus to "The bridge is lost." (5 intervals, 2 German decisions, all the guard policy); Hill 223 to "The patrol is back with prisoners." (27 intervals, 9 German decisions, all the German policy) |
| `node scripts/map_screenshots.mjs` | `HARNESS PASSED`; the same three results through the POC desk |
| `test_replay_sides` run time | 36.0 s at `f2db2bb`, 46.3 s here (+10.3 s, two scenarios added), run one after the other |

Both browser runs keep their BLOCKED rule (exit 3 when no browser runs, never a pass) and their cleanup of the POC, the browser group and the profile on every exit path; this slice did not change that code.

**Red first.** `test_playable_eras_2.py` run on a `git archive` of `f2db2bb`: 13 tests, 8 failures and 8 errors (`red/`). The unknown-label test passes there, as it should: it pins behaviour that already existed; its mutation below shows it can fail.

**Digest comparison against `f2db2bb`** (`run_digests.zsh`, doc 74's `digests.py` unchanged). `cmp` exits 0 for each:

- every headless catalog entry (Little Round Top, Hougoumont, both Concord entries, Pegasus Bridge, Hill 223, Gergovia, Cannae): opening state, commander view, the generic scripted play, the full headless run and its final state, timings dropped. Replay `identical` everywhere;
- desk play of Little Round Top, Hougoumont and Concord to the end: final state and every revision. Little Round Top and Hougoumont still record no `policy`; Concord records `scripted-concord-regulars-v1`;
- saved games: a Little Round Top, a Hougoumont and a Concord desk game written by `f2db2bb` at interval 9, continued to the end by `f2db2bb` and by this tree: final state and every revision identical.

Desk play of the two new entries (head only): Pegasus, German at 5 intervals, 2 decisions of `scripted-pegasus-guard-v1`; Hill 223, American at 27, 9 decisions of `scripted-hill-223-german-v1`.

**Each new check can fail** (`mutations.log`, `mutate.py`): 11 of 11 single mutations turn their check red: either entry without the flag; `_opponent_control` without its `except UnknownScenario`; `before()` or the Pegasus relabel keeping the flag; `validate` accepting partial coverage; the 1775 closing back to runner only; the Concord note without S49; the works check skipping Pegasus; the POC desk dropping the charges dot; the Hill 223 brief without its deadline.

**Screenshots.** POC desk: `screenshots/pegasus-*` and `screenshots/hill-223-*` (fit and 2×, grid on and off, legend, order, outcome) with the other three sets regenerated and `*-hex-tooltips.txt`. TS desk: `smoke-web/desk-pegasus-{features,outcome}.png`, `smoke-web/desk-hill-223-{features,outcome}.png`, with the existing set.

## 8. Deferred and next

- **Gergovia and Cannae** wait on bt-D07 (BCE dates); Cannae's outcome also on D34. Their read-only renders were never needed: neither has a drawn mark.
- **Hougoumont's desk opponent** stays the owner question of 74 §2.
- **Pegasus playability.** On the default entry the bridge is blown at 00:27:30 whatever the opening order sent here; the outcome rests on two authored timings ([54](54-pegasus-scenario-runs.md) §5, §8). Whether the desk should offer the `guard-only` reading, or the timings need a source, is an owner question. Until the owner rules, the bt-D09 default is applied on both desks: the entry is kept as it is and the brief tells the player (§4). bt-D09 stays open.
- **Variants** stay headless, as for Concord.
- **Desk display gaps seen in the screenshots** (none new to this slice): counters overlap the canal bridge label and the works labels collide at Pegasus; the 2× view centres the map, so Hill 223's ravine and shack are off-screen there; the TS desk draws no objective ring. The POC order summary says "dispatch a runner" and the help panel "Movement orders travel by runner" in every era, wrong where orders go by wireless or voice. The desks render no `signals`.
