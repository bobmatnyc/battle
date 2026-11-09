# 84 — D37 paid run: where the model games differ from the scripted control

**Date:** 2026-11-08. **Task:** bt-T25. **Base:** main `f1f4210`. **Branch:** `bt-t25-doc84`.

Read-only on the D37 artifacts. No model call, no spend, no network, no key. The run is `apps/poc/artifacts/d37-option-a-f1f4210/` (git-ignored): exit 0, 12 of 12 games, `$2.045076` of the `$14` cap, Sonnet 5.5, 0 fallbacks, every replay `identical`. Plan and guards: [69](69-model-run-cost-estimate.md), [78](78-d37-guards.md). Run tooling: [83](83-run-tooling.md).

Evidence is the `decisions` and `events` tables of the 12 databases (`seq` is `events.seq`; `idx` is `decisions.decision_index`, model calls on even `idx`). The control is `make headless-poc SCENARIO=<id>`, run locally.

**Method added here.** To test a cause, a fake provider replays the recorded model orders by call number, with one edit, through `build_headless(player_provider="openrouter", provider=<fake>)`. It costs nothing. The first line of each test reproduces the recorded winner and turn, so the harness is sound. These are single deterministic replays, not samples.

## 1. Sides, decisions and cost

The model played the first side in each row. The opponent was the scripted control. **At Little Round Top the model played the Union, so its Confederate "win" at 25 is the model losing.**

| Game | Model side | Turns | Winner (control) | Decisions | With orders | Input tok | Output tok | Cost | $ per decision |
|---|---|---|---|---|---|---|---|---|---|
| little-round-top-1 | union | 25 | confederate (union, 60) | 9 | 4 | 67,570 | 5,626 | $0.1914 | 0.0213 |
| hougoumont-north-gate-1 | allied | 60 | allied (allied, 60) | 20 | 3 | 151,124 | 4,253 | $0.3448 | 0.0172 |
| concord-north-bridge-1 | provincial | 11 | provincial (8) | 4 | 3 | 29,627 | 3,321 | $0.0925 | 0.0231 |
| concord-north-bridge-2 | provincial | 8 | provincial (8) | 3 | 2 | 22,122 | 2,290 | $0.0671 | 0.0224 |
| concord-north-bridge-3 | provincial | 8 | provincial (8) | 3 | 2 | 22,122 | 2,263 | $0.0669 | 0.0223 |
| pegasus-bridge-1 | british | 5 | german (german, 5) | 2 | 1 | 15,155 | 1,863 | $0.0489 | 0.0245 |
| pegasus-bridge-2 | british | 5 | german | 2 | 1 | 15,155 | 1,692 | $0.0472 | 0.0236 |
| pegasus-bridge-3 | british | 5 | german | 2 | 1 | 15,155 | 1,476 | $0.0451 | 0.0225 |
| gergovia-recall-1 | roman | 36 | gallic (gallic, 36) | 12 | 6 | 123,506 | 11,067 | $0.3577 | 0.0298 |
| gergovia-recall-2 | roman | 38 | roman (gallic, 36) | 13 | 6 | 140,394 | 11,397 | $0.3948 | 0.0304 |
| hill-223-patrol-1 | american | 27 | american (american, 27) | 9 | 3 | 71,874 | 5,171 | $0.1955 | 0.0217 |
| hill-223-patrol-2 | american | 27 | american | 9 | 4 | 71,274 | 5,073 | $0.1933 | 0.0215 |
| **Total** | | | | **88** | **36** | **745,078** | **55,492** | **$2.0451** | **0.0232** |

The cost sums to the `spent_usd` in `batch-summary.json`. At $2 and $10 per million tokens, input is $1.49 and output $0.56. The plan figure was $10.65 (doc 69), because it priced long games the model did not play. **52 of the 88 decisions returned no order and cost $1.15 (56 %).** Cost per decision rises with the observation: 0.017 to 0.025 on short games, 0.030 on Gergovia.

## 2. Little Round Top: why the Union lost at 25

**Rule.** The Confederates win when only they hold the summit ring (the summit hex and its six neighbours; `victory.py:79-96`, desk brief `scenario.py:73-75`) for 3 turns. The ring of `(11,15)` is `(12,15) (10,15) (11,16) (11,14) (12,16) (12,14)`. The defender needs an effective unit inside it.

**Control.** The scripted Union orders all three detachments onto ring hexes at turn 0: U1 to `(12,15)`, U2 to `(10,15)`, U3 to `(11,16)`, repeated at turn 3. It wins at turn 60.

**Model.** U1 started on a ring hex, `(11,14)`. The model ordered it off.

| Turn (idx) | Model orders | Effect |
|---|---|---|
| 0 (0) | U1 move `(11,13)`; U2, U3 dig in at `(13,15)`, `(10,13)` | U1 leaves the ring at turn 4 (`seq` 110). U2 and U3 sit two hexes out. |
| 3, 6, 9, 12 (2, 4, 6, 8) | none | The reply text says "the summit lies within two hexes of all three detachments" (idx 4). |
| 15 (10) | U3 move `(12,14)` | U3 is on the ring for turn 20 only (`seq` 1008), then withdraws on its own (`seq` 1061, 1065). |
| 18 (12) | none | |
| 21 (14) | U3 move `(11,15)` | The order cannot beat U3's local withdrawal. |
| 24 (16) | U1 retreat `(13,13)` | U1 is already withdrawing, morale 44 (idx 16 text). |

The ring held no Union unit from turn 4 to 19, and again from turn 21. C1 stepped onto `(10,15)` at turn 23 (`seq` 1163). The count reached 3 at turn 25 (`battle_ended`, `seq` 1290).

**Replays of the recorded orders** (fake provider):

| Replay | Result |
|---|---|
| all recorded orders | confederate, 25 |
| only the turn 0 U1 move | confederate, 25 |
| no orders at all | confederate, 28 |
| recorded, without the U1 move | confederate, 35 |

The turn 0 move alone reproduces the loss at 25. Doing nothing, which leaves U1 alone on the ring, loses at 28. Removing the move delays the loss to 35. No variant puts more than one unit on the ring. The control wins because it fills the ring, not because it avoids one mistake. The scripted Confederates give identical orders in the control and the model game, so they did not adapt.

**Verdict.** This is neither a rules exploit nor good play. It is a misreading of the capture radius. The Union system prompt says only "none of your formations remains effective nearby" (`scenario.py:68`). The ring text is in the desk brief, which `system_prompt` (`command_policy.py:354-370`) does not send. The Confederate prompt states "within one hex". The model chose a breastwork (cover 60) at `(11,13)` over the objective. The control is not weak: it holds 60 turns, while the same Confederate beats a single ring unit at 28.

## 3. Gergovia: why game 2 flipped to Roman at 38 and game 1 did not

**Rule.** The Romans win if 122 of the 244 forward men stand within 2 hexes of `(20,19)` by the deadline (doc 62 §3). The recall trumpet sounds at turn 20 and no forward group hears it (`signal_not_heard`, `out_of_reach`; `seq` 1259 in game 1). Only a runner can recall a group. A runner expires 20 turns after it is sent.

**Control.** No order goes to the forward groups. The Gauls win at 36.

**Game 1** matches the control event for event: R8f shaken at 15, R8a reaches the gate at 19, R8a routs at 23, R8b reaches the gate at 26, R8d at 28, R8b routs at 36 (`seq` 3022). A no-orders replay also gives gallic, 36.

**Game 2** differs at turns 17 and 18. The two orders that reached their groups stopped the press before the gate:

| Game | Call 0 sent to | Delivered | Expired undelivered |
|---|---|---|---|
| 1 | R8d, R8c, R8b ("farthest first, longest road back", idx 0) | R8f at 20; R8c at 32; R8b at 33 | the first three, at turn 20 (`seq` 1251, 1253, 1255); R8a's, at 23 |
| 2 | R8a, R8b, R8c (nearest, idx 0) | R8a at 17 (`seq` 982); R8b at 18 (`seq` 1074); R13 at 16 | R8c's, at 20 (`seq` 1282) |

`exploit_stopped` with reason `ordered` follows at `seq` 994 (R8a) and 1088 (R8b), before the gate at 19. At turn 38 R8a (58 men) and R8b (60) are home, with R8f (4): **122 men, exactly the threshold**. R8c routed at 26. Game 2 won by the smallest margin the rule allows.

**Replays.** Game 1 with game 2's call 0 gives roman, 38. Game 2 with game 1's call 0 still gives roman, but at 65, so later orders in game 2 also helped. One choice of order, nearest group first, decided game 1. It is the opposite of the model's stated reasoning in game 1. The courier expiry and the pursuit are authored scenario data (doc 62), so this is the intended difficulty, not an exploit. Two games do not show which order rule is better.

## 4. Concord: why game 1 ran to 11, not 8

The control and games 2 and 3 end at turn 8. In each, B1 withdraws once the provincials close on `(11,10)` ("credible sightings indicate a much stronger force", `seq` 430 in game 2, 437 in the control); the provincials then hold the bridge for 2 turns.

Game 1's first orders sent P2, P3 and P4 to `(10,10)`, `(9,10)`, `(8,10)` (idx 0), one hex short of games 2 and 3. P2 stopped at `(10,10)` at turn 5 (`seq` 287). The model re-sent `(11,10)` at turn 6 (idx 4). P2 is out of P1's voice reach, so the order went by runner and arrived at turn 9 (`seq` 568). P2 reached `(11,10)` at turn 9 (`seq` 580), B1 withdrew at 10 (`seq` 658) and the battle ended at 11 (`seq` 810). Games 2 and 3 did the same at 6, 7 and 8 (`seq` 367, 430, 583). The three turns are the re-order and the runner. Game 1 with game 2's call 0 gives provincial, 8. Game 1's turn 9 order repeated `(11,10)` after P2 had arrived (idx 6). No orders at all give a British win at 20, so the provincial orders do matter here.

## 5. Where the model equals the control

A no-orders replay of each game gives the same winner and turn as the recorded game.

| Entry | Recorded | No orders | Why the orders did not matter |
|---|---|---|---|
| hougoumont-north-gate | allied, 60 | allied, 60 | The same four routs (F1 turn 4, A2 8, A1 15, F3 19) and the same gate push (carried at 17, `seq` 1361 control, 1397 model) happen with 3 of 20 calls giving orders. A3 survives with 54 to 56 men. The scripted French do not press on after F2 enters. |
| pegasus-bridge | german, 5 | german, 5 | Contact arms the demolition at turn 1 with the fuse due at 5 (`seq` 6, `demolition_armed`). The bridge falls at 5 (`seq` 254) in all three games and the control. The platoons halt at first contact. D24, D25 and B14 end on the same hexes with the same strengths in all four runs, whatever the orders. |
| hill-223-patrol | american, 27 | american, 27 | The patrol's raid and return are entry data. The orders that arrived were dig-in for the rear units (turns 4 to 10). The two orders to A1 were sent at 18 and 21 and due at 28 and 29, after the end at 27 (`seq` 977). Report age is 8 to 10 turns at the post (idx 14 text). |

In these three the outcome is fixed by the scenario. In Hougoumont the model is also at an action-set disadvantage: the control uses the standing instruction `close_on_breach`, which the reply cannot carry (doc 69 §10). It made no difference here. 17 of 20 Hougoumont calls returned no order and cost $0.28 of $0.34.

## 6. Options for bt-G01 tuning (no rule change)

The repo does not define bt-G01. These are options for the owner, each a prompt, plan or driver change.

1. **Put the capture radius in the Union Little Round Top prompt** (the ring text the Confederate prompt already has). This is a new prompt version, `lrt-side-v4`, and a new baseline; docs 47 and 51 say results do not carry across a prompt change. It would test whether the loss is the reading or the play.
2. **Add a no-orders replay as a second control.** It costs nothing and separates "the model decided" from "the scenario decided". Here it shows Little Round Top is a model effect (28 against 60), Concord a model effect (20 against 8), and the other three no effect.
3. **Sample before concluding on Gergovia and Concord.** One game each flipped on one choice. At about $0.39 and $0.07 a game, five games of each cost about $2.3, within the $11.95 left.
4. **Drop or replace the inert entries.** Default Pegasus, Hill 223 and Hougoumont cost $0.88 and showed nothing. Doc 69 §8 gap 7 already named the Pegasus default; the `guard-only` and `surrender-on-threat` variants give the model leverage.
5. **Skip calls with nothing new to decide.** 52 of 88 calls returned no order ($1.15). A driver rule that skips a call when no new report has arrived would cut spend and leave the rules alone. It changes the decision cadence the control uses, so it needs a new baseline.
6. **Tell the model the runner rules.** The Gergovia prompt does not say that a runner order expires after 20 turns or that a chased group may never be reached. A prompt line would test whether the Gergovia order choice improves.

**Limits.** One game per cell except Concord, Pegasus and Hill 223. Temperature 0.3, so repeats differ (doc 69 §7). The replays hold later orders fixed while the state changes. The control databases are local re-runs, not archived.

## Review notes

code-critic fact-check at `23ea365`: **APPROVE**, no BLOCK or HIGH. The critic checked the doc against the `d37-option-a-f1f4210` artifacts, read-only, with no model call. These claims match the records:

- **Totals:** 88 decisions, 36 of them with orders. 745,078 input and 55,492 output tokens. $2.045076, equal to `spent_usd`. The 52 no-order decisions cost $1.15028.
- **Side:** `manifest.json` shows the model played the Union at Little Round Top. `battle_ended` shows a Confederate win at turn 25, so the model lost.
- **Little Round Top:** U1 left its ring hex at seq 110, and no Union unit entered the ring from turn 4 to 19. The Union mission at `scenario.py:66` does not state the one-hex radius, while the Confederate mission at `scenario.py:80` does.
- **Gergovia:** game 1's orders expired at turn 20. Game 2 delivered orders at turns 16, 17 and 18, and won with "122 of the forward force" at turn 38.
- **Concord game 1:** the re-order was delivered at turn 9, and the battle ended at turn 11.
- **Pegasus and Hill 223:** the scenario events match the doc.
- **Tuning:** the options are framed for the owner, with no rule change.

Credential scan over `origin/main...HEAD`: clean. The doc names the provider only as a code argument, with no key, key label or request id.

One WARN, not fixed: the critic did not re-run the replay and control results. These are the control wins, the Little Round Top variants at 28 and 35, the Gergovia swaps and the Concord no-orders British win at 20. Nothing the critic could check contradicts them. The replay scripts were scratch files in `/tmp` and are not committed.
