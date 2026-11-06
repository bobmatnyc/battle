# 42 — Hougoumont north gate: the catalog entry (`poc-10`)

**Date:** 2026-11-05. **Requirement:** add the Hougoumont north-gate scenario ([37 §2](37-first-five-selection-register.md#2-napoleonic--hougoumont)) as a player-facing catalog entry on `poc-10`, using the gate mechanism of [41](41-poc10-gates.md), with a courtyard-possession victory kind and a minimal Napoleonic voice and command profile. The browser followed in the command-desk text section below.

## What changed (implemented)

- `apps/poc/battle/scenario_hougoumont.py`: the entry `HOUGOUMONT_NORTH_GATE` (id `hougoumont-north-gate`, label `hougoumont-north-gate-v1`), registered second in `bootstrap.PLAYER_SCENARIOS`. Little Round Top stays the default.
- `apps/poc/battle/victory.py`: the kind `hold-compound`.
- `apps/poc/battle/presentation.py`: voice profile `napoleonic-en-v1`; `VOICE_PROFILES` maps each id to its instruction. `command_policy.VOICES` is that map.
- `apps/poc/battle/comms.py`: profile `napoleonic-courier-v1`, which reuses the 1863 transport rates under the label `1815 · voice / foot runner`. `comms.location` reports the profile the side's commander was built with.
- `apps/poc/battle/scenario_entry.py`: validation accepts any known voice and communications profile. A new optional field `provenance` (field name → note) must start each note with `sourced:`, `reconstruction:` or `authored:`. It is never stored in a snapshot or shown in a prompt.
- `apps/poc/battle/services/commander.py`: decision and chat records name the battle's own voice profile rather than the 1863 constant. Little Round Top records are unchanged.

## Edition decision

No new edition. `poc-10` has not been released beyond this repository. `hold-compound` is reachable only by an entry whose objective lies in a gated compound, and gates exist only in `poc-10` snapshots. Every existing snapshot names `hold-objective`, whose code is unchanged. The communications change returns the same profile for every existing save, because each stores `civil-war-courier-v1`. Evidence: the pinned `cb7faa0` digests in `tests/test_gates.py` still match, and the scripted Little Round Top headless final state on this branch has the same SHA-256 as at `5195aa1` (`042ef7d0…`, game id blanked).

## Provenance per field

Sources: S44 Wellington's dispatch; S45 Age of Revolution object pages (Wellington's fire note, the gate lock); S46 Glover on Clay; *Closing the Gates* and NAM as re-read in [37](37-first-five-selection-register.md). The same notes are in the entry's `provenance` field.

| Field | Value | Basis |
|---|---|---|
| Location | Hougoumont · Waterloo, Belgium | **Sourced** (S44) |
| Date | 1815-06-18 | **Sourced** (S44) |
| Start time | 11:20 local | **Reconstruction.** Ten minutes before the closing at about 11:30 on *Closing the Gates* (secondary, cites no primary source). S44 dates the first attacks from about ten. The time is uncertain, and Glover (S46) argues that two break-ins were merged. |
| Weather | Fixed POC condition | **Authored.** No source read gives it. |
| Sides | `allied` "Allied", defender; `french` "French", attacker | **Sourced.** A Guards garrison (S44, S45) against a French party (S45, NAM). |
| Player side | `allied` | **Authored.** The gate decision is the garrison's. |
| Allied mission | Hold the walled farm to turn 60; keep the north gate open for supply; close it on a breach | **Reconstruction.** "Keep the supply entrance open, close on a breach" is the REC entry in the 37 register. Holding the farm follows S44 (held all day) and the fire note in S45 (hold the walls). No recorded order concerns the gate. |
| French mission | Pass men through the north gate before it shuts; hold the inside of the walls for 6 turns | **Reconstruction.** Inferred from the outcome pages. No French order was found. |
| Map | Compound of 7 hexes (château and courtyards), north gate open, walled garden east, orchard east of that, wood south, three lanes | **Authored, not surveyed.** No plan or survey was read. That the north gate was open for friendly traffic is **sourced** (*Closing the Gates*, NAM). |
| Unit names | Gate party · 2nd Coldstream Guards; Coldstream companies · farm courtyard; Guards companies · château court; Legros's party; Assault group · follow-on companies; Skirmishers · wood edge | **Sourced** where named: 2nd Battalion Coldstream Guards and Sous-Lieutenant Legros (S45), Byng's Guards detachment (S44). The split into these detachments is **authored**. |
| Unit strengths | Allied 15, 60, 60; French 30, 80, 40 | **Authored**, with one exception. Legros's party is 30, set from the "about 30" who got in on *Closing the Gates* (secondary, uncited). This is a count of the men who entered, not a sourced party size. |
| Skill, morale, cartridges, tools | POC detachment defaults; 40 cartridges a man; smoothbore muskets | **Authored.** |
| Gate labour | close 45, bar 30, force 120, work cap 20 | **Authored sensitivity parameters** ([37 open question 6](37-first-five-selection-register.md#6-open-questions-for-the-user)); stored with `basis: "authored POC sensitivity parameter; not a historical estimate"`. The gate party of 15 shuts the gate in 3 intervals and bars it in 2 more. Two parties of 20 or more force a closed gate in 3. |
| Victory | `hold-compound`, 6 turns, deadline 60 turns (30 minutes) | **Authored.** |
| Voice and command profile | `napoleonic-en-v1`; `napoleonic-courier-v1` | **Authored.** Minimal, see below. |

## The `hold-compound` victory kind

Through the `victory.py` interface ([39](39-scenario-sides-and-victory-kinds.md#victory-kind-interface)):

- `problems(entry)`: needs exactly two sides, one defender and one attacker, a positive integer `hold_turns`, an `objective_name`, and an objective hex inside a building compound that declares openings. Otherwise the catalog refuses the entry.
- `setup(entry)`: stores `feature_id`, the compound's hexes, `hold_turns` and `objective_name` in the snapshot, so replay needs no catalog.
- `score(s)`: the capture counter rises in each interval in which the attacker has an effective formation (not routed, lost or merged, strength above 0) inside the compound and the defender has none. Any other interval resets it. The attacker wins at `hold_turns`. The defender wins at the deadline. Either side wins when the other has no effective formation anywhere. Both broken is a draw.
- **Fail closed.** A snapshot with missing or invalid `feature_id`, `compound`, `hold_turns` or `objective_name` raises `ValueError`; no winner is awarded.

Units cut off inside count as inside. Possession means uncontested possession: a single effective defender inside stops the count.

## Voice and command profile (minimal)

The schema required one value each for `voice_profile` and `communications`, and allowed only the 1863 ones. The Napoleonic voice copies the 1863 instruction with the period set to 1815, the player addressed as Colonel, and "companies" and "cartridges" added to the vocabulary. The communications profile changes only the label in the commander's observation. **Deferred:** period transport rates (gallopers, aides-de-camp), the scripted staff text, which still says "General" and the browser's remaining Little Round Top copy (see the command-desk text section: the mission panel, headings, side names, objective marker, outcome headlines and the `present_view` voice are done).

## Scripted-vs-scripted run

This section records the run before the gate-aware control below; it is reproduced today with `--player-policy scripted-fallback-v1`. `build_headless` with `--scenario hougoumont-north-gate` and both sides scripted ends at turn 60 with `allied`, "The Allied garrison held the farm until the scenario deadline." Replay is `identical` (62 revisions). The final strengths are A1 15, A2 38 (routed), A3 0 (lost), F1 7 (routed), F2 68 and F3 31. No French unit entered the compound. The gate stayed open, because the scripted control issues no *Close the gate* order. Legros's party routed at turn 4 under fire from the walls. The follow-on companies stayed between the lane and the wood edge, reacting locally to fire. This tests the plumbing. It is not a historical comparison.

## Gate-aware scripted defender

The fallback control moved the gate party off the gateway and never closed the gate, so the scripted baseline skipped the decision the scenario turns on. The defender now has its own control, `scripted-gate-defender-v1` (`command_policy.gate_defender_actions`):

- The gate party is the live unit nearest the gateway hex, then by id (A1 at the start). It is kept on the gateway: a move back if it is elsewhere, a hold if it is there.
- At the first decision it gets the `close_on_breach` standing order, once, through normal standing-order delivery.
- When a delivered contact stands inside the compound and the known gate is not barred, it is ordered to `close_gate` through normal order delivery. The standing order may already have started the work locally.
- Other units fill the compound ring as the fallback defender does, skipping the gateway. At most three orders a decision.

**Selection.** The headless runner picks the control for the scripted player side from the entry: the defender of an entry with `gates` gets `scripted-gate-defender-v1`; every other side and scenario keeps `scripted-fallback-v1`. `--player-policy` overrides it; the gate control is refused for a side that does not defend a gated scenario. A run under the gate control records `player_policy` in its run metadata and prints the metadata in its summary; `opponent` still names the French control. Other runs keep their metadata and output: `make headless-poc` output, game id blanked, is byte-identical (`cmp`) to `b26aa63`. The same rule picks the computer side's control: with a French player (`--player-side french`), the Allied side plays `scripted-gate-defender-v1`, and `opponent` in the run metadata names it. `--opponent` overrides it under the same refusal. A computer decision under the gate control carries `policy` and a `standing` list next to its `orders`. On replay, `record_decision` issues the stored standing instructions through `standing.issue`, then the orders through `engine.issue`, with the same validation and delivery as player actions. Replay does not re-run the policy. Decisions without `standing` are applied as before. Old saves replay unchanged, and `make headless-poc` output, game id blanked, is byte-identical to `0ddff5e`. The scripted French-player run used to end at turn 60 as an Allied win at the deadline (the gate stayed open). It now ends at turn 28 as an Allied win, "The attacking formations have broken." A1 receives `close_on_breach` at turn 0, no French unit enters the compound, and the gate stays open. Replay is `identical` (39 revisions).

**Outcome.** With the gate-aware defender, the scripted run ends at turn 28: `allied`, "The attacking formations have broken." Replay is `identical` (32 revisions). Final strengths: A1 15, A2 28 (routed), A3 57, F1 6, F2 65, F3 19, all French routed. A1 received `close_on_breach` at turn 1 and held the gateway. No French unit entered the compound, so no breach was observed, no close order was sent and the gate stayed open; the capture counter never left 0. Legros's party routed at turn 4, as before. Keeping A1 in the gateway blocks it, because units cannot stack. This tests the control; it is not a historical comparison.

**Engine-driven tests** (`HoldCompoundEngineTests`, through `RulesSimulation` and a stored game, each checking replay): French troops enter, the gate party shuts the gate under its delivered standing order after a `gate_blocked` interval, and F1 is `cut_off` inside with the capture counter at 0 while the gate party stands; a capture count of 1 to 5 reset to 0 when the Allied commander marches back in; a draw when both sides have no effective formation; a French win when the Allied side has none. The arrangements (an unarmed garrison, a relief one hex from the gate) are test set-ups, not scenario changes.

## Command-desk text from the scenario

The desk no longer carries Little Round Top copy. `ScenarioEntry.desk` (`DeskBrief`) and `SideEntry.brief` (`SideBrief`) hold the display text: campaign line, weather line, map place and objective caption, map-key entry, draw headline, and per side the heading, mission title and text, and win and loss headlines. None of it is stored in a snapshot or shown in a prompt, so saves, replay and the map hash are unchanged. An entry without them gets text derived from its required fields (the prompt mission, `Victory.`, `Defeat.`). `presentation.scenario_brief(entry, side)` builds the brief for the viewing side only: the opponent's mission is never in it. `BattleQueries.project` resolves the entry from the stored state's label and adds `scenario_brief` to every state, God view and replay; it also passes the entry to `present_view`, so `voice_profile` is the scenario's (`napoleonic-en-v1` here). A label no catalog knows keeps the 1863 voice and has no brief; the desk then says no briefing is available.

`GET /api/scenarios` lists the catalog (`id`, `title`, `location`, `date`, and the default). The desk's scenario picker feeds `POST /api/new` with `scenario`; Reset starts the picked scenario, or the one being played. After a new game with another scenario the desk fetches `/api/map` again and calls `BattleMapView.setCells`. The objective marker draws the dashed ring only for a hold-objective victory; Hougoumont shows the label alone, since possession of the compound is not a ring of hexes. Checks: `ScenarioBriefTests`, `smoke_ui.mjs` (Little Round Top copy unchanged, then a Hougoumont switch) and `smoke_http.py`. Two existing checks changed mechanically: `smoke_http.py` looks for the mission element in the page instead of the words "Little Round Top", and `test_mission_text_states_early_summit_loss_before_deadline` reads the mission from the served brief instead of `index.html`.

**Still deferred.** Drawing the compound outline, the wall and the gate (with its open, closed or barred state): the renderer draws a building as one box and label at its hex and knows nothing of `compound` or `openings`, so this is renderer work. The gate state reaches the player only through dispatches. Also: a French player's brief (the entry fixes the player as Allied; the French side has derived text only), period transport rates and scripted staff text ("General"), the product-intent panel copy under the map, and weather wording for the 1815 day (the line says `FIXED POC CONDITION`).

## Not modelled

The garden wall is cover only (cover 30), not a wall: movement and sight cross it. There is no south gate or other entrance. There is no fire in the château, no push-back at the gate ([41](41-poc10-gates.md#choices-made-where-the-spec-was-open)) and no second break-in variant (S46).

## Tests

`apps/poc/tests/test_hougoumont.py`: registration with the dry run; the authored map, compound, open gate and lanes; provenance labels, missions as reconstruction, and a refused unlabelled note; mission isolation in each side's prompt and the 1815 voice; the 1815 command label and refusal of unknown profiles; `hold-compound` registration refusals, fail-closed scoring on six kinds of missing or invalid data, uncontested possession and the deadline; the gate fixture under `hold-compound`; a scripted headless run that replays `identical`; a model-played French run (fake provider) in which the computer Allied side issues `close_on_breach` at turn 0 under `scripted-gate-defender-v1` and replays `identical` without a provider; a computer gate-defender decision that orders `close_gate` after a delivered report of a French unit inside the compound; and a `BattleService` `clock_step` with the Allied player, in which only the French receive computer orders and the decision records `napoleonic-en-v1`.
