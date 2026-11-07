# Replay as either side or as God, in every player scenario

Date: 2026-11-07. **User requirement:** replay works for each side and for God Mode in every player scenario, not only the Union view of Little Round Top. This document records what existed, what changed and how it is checked. It is a POC interface change. No rule, rules edition, scenario value or saved game changes.

## What existed before this change

Player scenarios are `PLAYER_SCENARIOS` in `apps/poc/battle/bootstrap.py`: Little Round Top and Hougoumont. Headless-only scenarios are out of scope.

| Scenario | Player's commander replay | God replay | Opponent's commander replay |
|---|---|---|---|
| Little Round Top (Union player) | worked: `/api/replay?revision=N` | worked: `&view=god` | missing |
| Hougoumont (Allied player) | worked: the default endpoint is the snapshot's player side, not a fixed Union | worked | missing |

`BattleQueries.project` always called `simulation.view(state)`, which is the snapshot's player side. The engine's `view(state, side)` already accepted any side, in every frozen edition, but nothing above it passed one. The HTTP adapter read no `side` parameter, so `&side=french` was ignored and returned the Allied view. The browser had only the God Mode switch, so a replay showed the player's records or God's, never the opponent's. Doc 18 described replay as "recorded Union knowledge", which was true only for Little Round Top.

## What changed

- **Query.** `BattleQueries.project(state, god=False, side=None)` and `replay(game_id, revision, god=False, side=None)` show the commander view of `side`, with that side's brief (`scenario_brief`) and assessment. `side=None` keeps the player side, so every existing caller gets the same result as before. A side the snapshot does not have, or a side named together with `god`, raises `ValueError`. While the game is active (its latest state, not the replayed snapshot), `replay` also refuses any side other than the player's, so every adapter gets the lock.
- **HTTP.** `/api/replay?revision=N&side=<id>`, with the existing optional `game_id`. An unknown side, `side` with `view=god`, or the opponent's side while the battle is active, answers 400. `/api/state` does not change: the live desk stays the player's commander view or God's.
- **Browser.** Replay mode has a view selector in the replay bar: the player's side and God view, plus the opponent once the battle is complete. While the battle is active the opponent is not offered. Side names come from the battle's brief. The player's side requests the default endpoint. The opponent's side adds `&side=`. God view sets God Mode, and the God Mode switch and the selector stay in step. Seeking and playback keep the selected view. Return to live, and Reset, close the selector. From a side's replay, live shows the player's commander view. From a God replay, God Mode stays on and live opens in God view, as the switch shows; this matches the God Mode switch in replay since doc 21. Orders, chat and advice stay disabled in every replay view. The control uses no native dialog.

Read-only: the views come from `engine.view` and `engine.god_view`, which copy what they return. No replay request writes a snapshot, event, decision or report.

## Information boundary

A side's replay at revision N is that side's commander view at N: its delivered unit reports, its contacts (subject to the usual age limit), its own orders and acknowledgements, its dispatches and the map features it was briefed on or has a report of. It does not show the other side's units it has no contact with, the other side's works it has no report of, the other side's mission text, or any God field (events, reports in transit, decisions, true headquarters). God view shows everything, as in [21](21-god-mode-and-command-location.md). Choosing a side in replay changes only which records are read. It never merges God's state, or one side's records, into another side's records. The [24](24-map-features-and-digging-in.md) no-leak rule therefore holds for every replay view.

**Lock while active.** The opponent's view carries the opponent's brief, including its mission text. No live endpoint shows that text, God Mode included: the God view carries the player's brief. Opening the opponent's replay during an active battle would therefore show more than God Mode, with no opt-in. So, like the full export ([21](21-god-mode-and-command-location.md)), the opponent's replay is locked until the battle is complete: the query service refuses it with 400 and the browser does not offer it. The player's own replay and God replay stay available during the battle, as before. After completion the opponent's replay shows only that side's commander view, never God data; it is not routed through God Mode. This lock is a PM decision (2026-11-07); the owner may loosen it later. Future multiplayer must also restrict the opponent's view and the God view by host or scenario permission.

## Verification

`apps/poc/tests/test_replay_sides.py`, per player scenario:

- `test_each_side_replay_equals_its_live_view_at_every_revision`: plays an offline game (one player order, then clock intervals) through `BattleService`. At each revision it records the player's live `/api/state`, the live God view, a digest of each side's projection of the live game row, and each side's commander observation (`command_policy.observation_for`, the computer's decision input). Replays through `HttpApi` then match all of them at every revision: the default and `side=<player>` views equal the player's live state field for field; each side's view matches its digest and the units and contacts it decided from; God view equals the live God view.
- `test_no_side_replay_shows_the_other_sides_unseen_units_or_works`: for each side, that side's units dig in so that new works exist which the other side has not seen. At every revision and for both sides: only the viewer's own units and orders; contacts only from the viewer's own contact records; every enemy unit without a contact is absent; every map feature without a report is absent, though God view has it; no God field; no text of the other side's mission. The test also asserts that some unseen unit and some unseen works existed, so the checks ran against something to hide.
- `test_switching_replay_views_leaves_stored_records_byte_identical`: dumps every SQLite table, switches between God, each side and the default at every revision, reads live God state, and dumps again. The dumps are identical. The player's live commander view afterwards equals the one before.
- `test_replay_refuses_an_unknown_side_and_side_with_god`, including an empty side sent straight to the query (HTTP parsing drops `side=`).
- `test_opponent_replay_is_locked_until_the_battle_is_complete`: at every revision of every interval while active, the opponent's replay is refused and the player's is served; after completion the opponent's replay at every revision equals that side's projection and its commander view's units, contacts, orders and map features.
- `test_no_endpoint_shows_the_opponent_mission_during_an_active_battle`: in an active battle, live state, live God state, history, and the default, God, player and opponent replays at every revision never contain the opponent's mission text.

The first three tests now play each battle to completion, so the opponent's replay is unlocked. Against the first version of this change (no `side`), these tests failed with 7 failures and 4 errors. Against `d1aab83` (side without the lock), the last two failed in both scenarios: the opponent replay was served while active and carried the opponent's mission.

`scripts/smoke_ui.mjs` first opens Replay on an active Little Round Top battle and checks that only the Union and God views are offered. For a completed battle it replays as the Union, then the Confederates (only Confederate units, the Confederate mission, "recorded Confederate commander view"), then God (every unit, God Mode on), then the Union again. It checks that seeking keeps the view, that Return to live from a side's replay shows the Union commander view, that Return to live from a God replay opens live God view, and that no command was posted. `scripts/smoke_http.py` checks the player's replay at every revision of a short active Little Round Top game and the 400 for the Confederate side, the 400 for the French side of an active Hougoumont game, the French replay after that battle is played out, and the unknown-side and side-with-God refusals.

## Limits

Two-sided scenarios only, as the catalog requires. The selector names sides from the brief; a saved game whose label no catalog knows offers only its player side and God view. No model-decision replay, field-glass replay, or outcome-comparison report is added, and the TypeScript desk is untouched.
