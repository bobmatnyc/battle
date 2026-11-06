# 40 — Batch A: model baseline on Little Round Top

**Version:** 1 (2026-11-06). **Code commit:** 503d541. **Rules:** `poc-8`. **Scenario:** `little-round-top-v8` (Little Round Top). **Prompt version:** `lrt-side-v2`. **Models:** `anthropic/claude-sonnet-5.5` and `openai/gpt-6-astra`. **Reasoning effort:** `high`. **Opponent control:** `scripted-fallback-v1`. **Runs:** 14 live model runs (Sonnet 5.5: 5 as Union, 5 as Confederate; Astra: 2 as Union, 2 as Confederate) and 2 scripted-versus-scripted controls.

Machine-readable rows and aggregates: [`apps/poc/experiments/batch-a/summary.json`](../../apps/poc/experiments/batch-a/summary.json). Every figure below was read from the run databases (stored events, snapshots and decision records) in the artifact set listed at the end; none is estimated. Prompts and response text are not reproduced.

## Result

- The model as Union held the objective in 6 of 7 runs. The model as Confederate took it in 0 of 7 runs.
- All 261 player decisions came from the model; 0 fell back to scripted orders.
- Recorded spend: $11.69 (sum of `usage.cost`).
- Both scripted controls ended in a Union win at turn 60.

## Baseline comparability

Held fixed in every run: rules edition `poc-8`, scenario `little-round-top-v8`, prompt version `lrt-side-v2`, effort `high`, response format `json_schema:commander_orders`, the scripted opponent `scripted-fallback-v1` on the other side. The engine is deterministic and every run replayed with status `identical` (the `.analysis` files and the two control `.out` files record this), so the only source of run-to-run variation is the model's nondeterminism. Models and the side the model commands are the varied factors.

The scripted control is the comparison point because it runs the same scenario and rules with both sides scripted. It involves no model, so the engine alone produces its result. The two control runs reached the same result (Union win at turn 60; Union lost 40 strength, Confederate lost 38), which is what a deterministic engine predicts. A model run differs from the control only through the orders the model issued for its side.

## Per-run table

Casualties are starting strength minus final strength, summed over each side's three units, read from the first and last stored snapshot (start 120 per side). `a->b (n)` is start, final, lost. The mission column says whether the player's side held its objective ("held") or lost it; for a Confederate player, "lost" means the Confederates did not take the summit. The reason is the text of the `battle_ended` event. Decisions are model decisions over player decisions. Tokens are prompt / completion (reasoning, included in completion) summed over the player's decisions. Latency is the median of the player's decision `latency_ms`. For the control rows the side label is a file-name artifact: both sides were scripted.

| Run | Model | Player side | Winner | Turns | Mission outcome and reason | Union strength | Confederate strength | Decisions | Tokens | Latency median | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| astra-confederate-1 | gpt-6-astra | confederate | union | 60 | lost: The Union held out until the scenario deadline. | 120->89 (31) | 120->79 (41) | 20/20 | 124,871 / 16,791 (14,946) | 22.8 s | $2.400 |
| astra-confederate-2 | gpt-6-astra | confederate | union | 50 | lost: The attacking formations have broken. | 120->93 (27) | 120->68 (52) | 17/17 | 80,535 / 5,650 (4,496) | 7.1 s | $1.242 |
| astra-union-1 | gpt-6-astra | union | union | 60 | held: The Union held out until the scenario deadline. | 120->84 (36) | 120->97 (23) | 20/20 | 121,323 / 16,093 (14,240) | 18.6 s | $2.321 |
| astra-union-2 | gpt-6-astra | union | union | 60 | held: The Union held out until the scenario deadline. | 120->101 (19) | 120->104 (16) | 20/20 | 115,346 / 11,705 (10,054) | 13.3 s | $1.815 |
| sonnet-confederate-1 | claude-sonnet-5.5 | confederate | union | 42 | lost: The attacking formations have broken. | 120->98 (22) | 120->65 (55) | 14/14 | 96,711 / 3,654 (1,266) | 2.1 s | $0.230 |
| sonnet-confederate-2 | claude-sonnet-5.5 | confederate | union | 60 | lost: The Union held out until the scenario deadline. | 120->98 (22) | 120->75 (45) | 20/20 | 167,707 / 14,404 (8,587) | 7.3 s | $0.479 |
| sonnet-confederate-3 | claude-sonnet-5.5 | confederate | union | 43 | lost: The attacking formations have broken. | 120->99 (21) | 120->65 (55) | 15/15 | 101,267 / 3,562 (1,136) | 2.0 s | $0.238 |
| sonnet-confederate-4 | claude-sonnet-5.5 | confederate | union | 60 | lost: The Union held out until the scenario deadline. | 120->98 (22) | 120->77 (43) | 20/20 | 169,781 / 14,304 (8,397) | 7.1 s | $0.483 |
| sonnet-confederate-5 | claude-sonnet-5.5 | confederate | union | 60 | lost: The Union held out until the scenario deadline. | 120->101 (19) | 120->82 (38) | 20/20 | 177,870 / 15,333 (9,297) | 7.1 s | $0.509 |
| sonnet-union-1 | claude-sonnet-5.5 | union | union | 60 | held: The Union held out until the scenario deadline. | 120->94 (26) | 120->99 (21) | 20/20 | 158,007 / 10,574 (6,397) | 5.0 s | $0.422 |
| sonnet-union-2 | claude-sonnet-5.5 | union | union | 60 | held: The Union held out until the scenario deadline. | 120->83 (37) | 120->91 (29) | 20/20 | 152,337 / 7,877 (3,975) | 2.8 s | $0.383 |
| sonnet-union-3 | claude-sonnet-5.5 | union | union | 60 | held: The Union held out until the scenario deadline. | 120->89 (31) | 120->100 (20) | 20/20 | 160,728 / 12,347 (7,821) | 5.0 s | $0.445 |
| sonnet-union-4 | claude-sonnet-5.5 | union | confederate | 43 | lost: The attackers held the summit uncontested for 90 seconds. | 120->80 (40) | 120->87 (33) | 15/15 | 112,918 / 7,306 (4,109) | 4.2 s | $0.299 |
| sonnet-union-5 | claude-sonnet-5.5 | union | union | 60 | held: The Union held out until the scenario deadline. | 120->92 (28) | 120->64 (56) | 20/20 | 160,591 / 10,078 (5,676) | 5.0 s | $0.422 |
| scripted-confederate-1 | scripted | none (both scripted) | union | 60 | Union held: The Union held out until the scenario deadline. | 120->80 (40) | 120->82 (38) | n/a | n/a | n/a | n/a |
| scripted-union-1 | scripted | none (both scripted) | union | 60 | Union held: The Union held out until the scenario deadline. | 120->80 (40) | 120->82 (38) | n/a | n/a | n/a | n/a |

Per-unit start and final strength with final status, from the last stored snapshot. Every unit started at 40.

| Run | C1 | C2 | C3 | U1 | U2 | U3 |
|---|---|---|---|---|---|---|
| astra-confederate-1 | 40->24 (ready) | 40->27 (ready) | 40->28 (ready) | 40->37 (ready) | 40->24 (routed) | 40->28 (ready) |
| astra-confederate-2 | 40->25 (routed) | 40->19 (routed) | 40->24 (routed) | 40->39 (ready) | 40->25 (routed) | 40->29 (ready) |
| astra-union-1 | 40->32 (ready) | 40->25 (routed) | 40->40 (ready) | 40->26 (routed) | 40->29 (ready) | 40->29 (ready) |
| astra-union-2 | 40->40 (ready) | 40->24 (routed) | 40->40 (ready) | 40->26 (routed) | 40->39 (ready) | 40->36 (ready) |
| sonnet-confederate-1 | 40->25 (routed) | 40->16 (routed) | 40->24 (routed) | 40->33 (ready) | 40->31 (ready) | 40->34 (ready) |
| sonnet-confederate-2 | 40->25 (ready) | 40->25 (ready) | 40->25 (routed) | 40->36 (ready) | 40->26 (ready) | 40->36 (ready) |
| sonnet-confederate-3 | 40->25 (routed) | 40->16 (routed) | 40->24 (routed) | 40->35 (ready) | 40->29 (ready) | 40->35 (ready) |
| sonnet-confederate-4 | 40->24 (routed) | 40->25 (ready) | 40->28 (ready) | 40->36 (ready) | 40->26 (ready) | 40->36 (ready) |
| sonnet-confederate-5 | 40->27 (ready) | 40->27 (ready) | 40->28 (ready) | 40->36 (ready) | 40->28 (ready) | 40->37 (ready) |
| sonnet-union-1 | 40->35 (ready) | 40->24 (routed) | 40->40 (ready) | 40->26 (routed) | 40->39 (ready) | 40->29 (ready) |
| sonnet-union-2 | 40->32 (ready) | 40->19 (routed) | 40->40 (ready) | 40->24 (routed) | 40->27 (routed) | 40->32 (ready) |
| sonnet-union-3 | 40->38 (ready) | 40->22 (routed) | 40->40 (ready) | 40->24 (routed) | 40->29 (ready) | 40->36 (ready) |
| sonnet-union-4 | 40->29 (ready) | 40->19 (routed) | 40->39 (ready) | 40->24 (routed) | 40->27 (routed) | 40->29 (ready) |
| sonnet-union-5 | 40->24 (routed) | 40->15 (routed) | 40->25 (ready) | 40->27 (ready) | 40->32 (ready) | 40->33 (ready) |
| scripted-confederate-1 | 40->24 (routed) | 40->23 (routed) | 40->35 (ready) | 40->30 (ready) | 40->26 (routed) | 40->24 (routed) |
| scripted-union-1 | 40->24 (routed) | 40->23 (routed) | 40->35 (ready) | 40->30 (ready) | 40->26 (routed) | 40->24 (routed) |

## Aggregates

Columns: runs; player-side wins (the model's side held its objective); mean strength lost by the Union and by the Confederates; mean turns; mean cost per run; median latency pooled over all decisions in the group.

| Group | Runs | Player-side wins | Mean Union lost | Mean Confederate lost | Mean turns | Mean cost per run | Latency median |
|---|---|---|---|---|---|---|---|
| All model runs | 14 | 6/14 | 27.21 | 37.64 | 55.57 | $0.835 | 6.4 s |
| Model as Union | 7 | 6/7 | 31.0 | 28.29 | 57.57 | $0.873 | 5.8 s |
| Model as Confederate | 7 | 0/7 | 23.43 | 47.0 | 53.57 | $0.797 | 7.0 s |
| Sonnet 5.5 as Union | 5 | 4/5 | 32.4 | 31.8 | 56.6 | $0.394 | 4.9 s |
| Sonnet 5.5 as Confederate | 5 | 0/5 | 21.2 | 47.2 | 53.0 | $0.388 | 6.1 s |
| Astra as Union | 2 | 2/2 | 27.5 | 19.5 | 60.0 | $2.068 | 15.7 s |
| Astra as Confederate | 2 | 0/2 | 29.0 | 46.5 | 55.0 | $1.821 | 13.3 s |
| Sonnet 5.5, both sides | 10 | 4/10 | 26.8 | 39.5 | 54.8 | $0.391 | 5.2 s |
| Astra, both sides | 4 | 2/4 | 28.25 | 33.0 | 57.5 | $1.945 | 14.8 s |
| Scripted control | 2 | n/a (Union won 2/2) | 40.0 | 38.0 | 60.0 | n/a | n/a |

Mean cost per run across all 14 model runs: $0.835. Mean per-run cost by model: Sonnet 5.5 $0.391, Astra $1.945. Mean tokens per run (prompt / completion): Sonnet 5.5 145,792 / 9,944; Astra 110,519 / 12,560.

Casualties against the control (Union lost 40, Confederate lost 38):

- Model as Union: Union lost 31.0 on average, Confederates lost 28.29. Union losses were lower than the control, and Confederate losses were lower than the control.
- Model as Confederate: Confederates lost 47.0 on average, Union lost 23.43. Confederate losses were higher than the control, and Union losses were lower.

Observed outcome mix: the 7 Confederate-player runs ended in two ways. Three ended early with "The attacking formations have broken" (`sonnet-confederate-1` at turn 42, `sonnet-confederate-3` at 43, `astra-confederate-2` at 50) and four ran to the turn-60 deadline. The only model loss as Union (`sonnet-union-4`) ended at turn 43 when the attackers held the summit uncontested for 90 seconds.

## Limits

- Little Round Top as authored strongly favours the defender. The scripted control, which uses no model, already gives the Union the win at the deadline in both control runs. A Union win therefore says little about model skill, and a Confederate loss says little about model weakness.
- The sample is small: 14 model runs, split 5, 5, 2, 2 across model and side. The counts are counts. No confidence interval or significance claim is made, and the Astra cells (2 runs each) should not be compared with the Sonnet cells (5 runs each).
- The authored units, positions and combat coefficients are illustrative. They are not drawn from historical order-of-battle or loss data. This note makes no realism claim and no historical-accuracy claim, and nothing here should be read as a statement about how the real action would have gone.
- Cost and latency are as measured on 2026-11-06 through the provider path used for these runs. Prices, routing and latency change; do not reuse them as current figures. Cost is the sum of recorded `usage.cost` and every one of the 261 player decisions carried a cost value.
- The scripted control gives one result, repeated twice. It describes the scripted pair only; it is not a distribution.
- The provider-reported model matched the requested model on every decision (the `model` field of each stored decision record).
- Not derived: wall-clock run time per game (not stored in the database), and anything about prompts and responses (deliberately excluded).

## Artifact manifest

**Local only, not published (git-ignored archive).** The files live in `apps/poc/artifacts/batch-a-2026-11-06/`. Each row gives the file name, size in bytes and sha256. For a `.sqlite` file, the last column is the `game_id`. To replay one:

```sh
cd apps/poc && cp artifacts/batch-a-2026-11-06/<run>.sqlite /tmp/<run>.sqlite && python3 -m battle --db /tmp/<run>.sqlite --replay <game_id>
```

Replay can modify the database, so run it on a copy, as above, and never on the archived file. Replay re-applies the recorded decisions and never calls a provider. The `.out` file of each run holds the stored result line, `.exit` the process exit code (0 for all 16 runs), `.analysis` a per-run token and cost summary, and `.err` the error stream. `driver-*.log` and `gate-*.log` are driver and check logs. The `-shm` and `-wal` files for `scripted-union-1` were present with the set; the other databases had none.

**Archive verification (2026-11-06).** 86 of 86 files match the sha256 values in the manifest below. All 16 databases replay `identical` from scratch copies. The archived hashes are unchanged after the replays: `shasum -c SHA256SUMS` reports 86 OK. The `SHA256SUMS` file sits in the archive folder with the files.

| File | Bytes | sha256 | game_id |
|---|---|---|---|
| astra-confederate-1.analysis | 363 | ae5edb1d9c55c697f9ede2bc9f33ad8eea925d612741256482323c4944b97811 |  |
| astra-confederate-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| astra-confederate-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| astra-confederate-1.out | 602 | c399b1247d0bbc9830e0e2b8f4b8ef6ab4c5f06ed19131bdd98958eebb10e389 |  |
| astra-confederate-1.sqlite | 74,276,864 | cd856f4009edf89a0363f78bbe2915d6c379d952a5bd34f90f642a1b4b7298c6 | 2110ca78022f4927 |
| astra-confederate-2.analysis | 359 | ecb7553919b8d0f7131a9bbffd3297e0af22e53424a3429a344b5d032c3dc8b4 |  |
| astra-confederate-2.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| astra-confederate-2.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| astra-confederate-2.out | 602 | 0b29cd66579c2af7d332146603ce94c1b52a15b151f49654fa88da61c43d96f8 |  |
| astra-confederate-2.sqlite | 51,580,928 | fc3207b1efd2bfa9dac31629bdc01ad8a17bd1c74439e45a1d2a58a8f219b1bc | 1f671c4b20894061 |
| astra-union-1.analysis | 364 | 5e2db4629610d9f6d686bdd4c066914c0f3f9cc5e9bf97626874e3d80076488e |  |
| astra-union-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| astra-union-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| astra-union-1.out | 602 | 1dbece1e594407116f2f30173d972fda86d655897594747e7ac1fd293ef32351 |  |
| astra-union-1.sqlite | 67,186,688 | a95b73e34bc7b6d5818da6fb3c30db12b96814249dfc2233f0123312ac7da0e5 | 186c84e0b9b5492f |
| astra-union-2.analysis | 363 | 3c88e8fc511c1666c9c6bd8a591f7093cc36810fbdd78ced3a6f8004b746cce6 |  |
| astra-union-2.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| astra-union-2.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| astra-union-2.out | 602 | 79a42671182eda1d4ae1db39f3fa2474a0312fa464487192ca07083014417679 |  |
| astra-union-2.sqlite | 63,762,432 | 882a69ac0a9c9cfd3f0b7d5e113e1923568d53059478e73a2956b914af09d547 | 8ecb59c605fc44cf |
| driver-astra.log | 4,041 | a8f2ea5fa32ce414a27182d9ffdeb3dae160aca015e121bad671ca6578209cc2 |  |
| driver-sonnet-b.log | 4,052 | 61fcb19d8e1ae35673329902aefe2105a2db5b7be8d24752c93a2ab8e1a436bb |  |
| gate-headless.log | 312 | f632d8bd5862966734fd6fa6040981826900e607791744101b982f6e6dbdfd87 |  |
| gate-smoke.log | 692 | 05d03cf9584f3205d9df70be52efb1c5573d23c66593b1ea95e9cceb4e0f4a0d |  |
| gate-test.log | 1,467 | c5cd8e10b5861abcc99cd1ffccce421d6edb4e6ec0dc469040c6e2babbbe025b |  |
| gate-typecheck.log | 44 | 26f167e6f67a2399c17e88c7bded1eb9ed65900cbac1ef8dcc0525b4971f9cf7 |  |
| scripted-confederate-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| scripted-confederate-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| scripted-confederate-1.out | 555 | 69873917ffee440b25521edf37aff4e21be16404fd2f8aefc74dc7db0a43601b |  |
| scripted-confederate-1.sqlite | 64,856,064 | 0894b2e14d0584632474781ff49cd6ad5b4e6dbd300ece0e1617ca1939f542f8 | 5cc9b75ca81c4485 |
| scripted-union-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| scripted-union-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| scripted-union-1.out | 219 | 0b1aa5304520000cc53c41aaa6ff682ccb3d1dd37047a28c24464e9844ac337e |  |
| scripted-union-1.sqlite | 42,106,880 | a19c066e160c0bf10675a2d91766a2d267f4f13517f797ac06c24dee93b5f0be | 7f630c1726154f7b |
| scripted-union-1.sqlite-shm | 32,768 | fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb |  |
| scripted-union-1.sqlite-wal | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-1.analysis | 358 | a164f3e46ae80aeaa1d6d5cc349aaa365ebc7dd4a855aa560c579dc082d9cd3f |  |
| sonnet-confederate-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-confederate-1.out | 611 | c48c88a638f0e029b66b0a02196c3b1196650df7302c6b2ab564b8de0f9fee38 |  |
| sonnet-confederate-1.sqlite | 37,314,560 | a646d375bf3c624bbdb20746c67240a7732eae6e4625ff4d6165d52158c4fe7c | d50608cd28fe4c64 |
| sonnet-confederate-2.analysis | 360 | 4b7c79fb6da7ef1999b63625bca50bef0c2a0c4da8a6d7947eab935f071ddc13 |  |
| sonnet-confederate-2.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-2.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-confederate-2.out | 611 | 43e571db46bfb4c46d1ef89931ab473352cf73257646fa38408c3f839551dca1 |  |
| sonnet-confederate-2.sqlite | 70,144,000 | c106fdba50243af4d7c66371e7e0e8462c4dcd9da6f959bd49664e6a427b6ff5 | b344cfcc925944a4 |
| sonnet-confederate-3.analysis | 359 | 7563b264940d6cce14ca5208baedeee1521374b6592f690f7aeb6bc4e8e3cfac |  |
| sonnet-confederate-3.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-3.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-confederate-3.out | 611 | 05e833a3171ef2a13ba2f0cadc465ac29f8233527ca37c5917807bc40541f29b |  |
| sonnet-confederate-3.sqlite | 39,514,112 | 230352ba80657f8e25aedfdf9ef18b0fa241d81ea2a721f6c2b49858c96d469b | 16a77351fdcc426a |
| sonnet-confederate-4.analysis | 361 | ce3a68b9dce12e0ca69f961a0ce4a13d0bfb0bb4d878973bdd19329312cea6ae |  |
| sonnet-confederate-4.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-4.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-confederate-4.out | 611 | 83ae1a44b0256bf2858769df9f3b780d295dddddfa7361bbeb0df872ee854906 |  |
| sonnet-confederate-4.sqlite | 71,118,848 | b9d00ca5a605f1f082b19e9c00476b42eca3be638c91c2830eb1608c1c531479 | 8e38de3fae9c465b |
| sonnet-confederate-5.analysis | 371 | 6fe05be7d6ad0924245a1105679d2126af02cde1cc03df7685766cfd762934c5 |  |
| sonnet-confederate-5.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-confederate-5.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-confederate-5.out | 611 | 68eba645c9192ca3be8b8c968fc68f6551917c0c4948dd8998022b22cfe861bb |  |
| sonnet-confederate-5.sqlite | 71,630,848 | 0a6645e28de68a372345155320ae2bc6c6b447058d64392c159a4674db28d58b | 7927c778a4754379 |
| sonnet-union-1.analysis | 360 | f208737e04d6497b301a90ae3810834cd07104462ea03a3a95954cc297b79ffc |  |
| sonnet-union-1.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-union-1.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-union-1.out | 611 | a7488f6afb36f40f79bd25e3f9c462ad1c760fa4e3d151ef233e026bb10283bf |  |
| sonnet-union-1.sqlite | 65,257,472 | 19658c5e6d9b6c7cabcd373826cf9309328dab8fb711199067bde0279f0f42c4 | 639c6265b6064f80 |
| sonnet-union-2.analysis | 360 | e650ae5327bc99814724b6b5b68c36487d3ccf028276a857fb867267c9eeb99e |  |
| sonnet-union-2.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-union-2.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-union-2.out | 611 | acf66896d67f45ce6720ae3f242d7ddda25affb09af9d75360326326700a7419 |  |
| sonnet-union-2.sqlite | 64,253,952 | 986573c959c2a9521beeb0e98127b7a5a4893be8d261e39e1f805acd41d9e6d1 | e93682a6ece745ae |
| sonnet-union-3.analysis | 371 | 11a29858806e5d8eb0560a74bc9d17cba8c617899b0b6613a5d54ccc9fd8534e |  |
| sonnet-union-3.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-union-3.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-union-3.out | 611 | 1c33991d08d41e2661bfda0734f3b68119b46ddfa5a27b06a4a5e6cbd22d70c9 |  |
| sonnet-union-3.sqlite | 64,536,576 | 37e5ef26d3cd5f0a033b0932c355fd3ac87ccb59351e043b9e6ff99f3c6f02fd | 519efe7f1f9641b6 |
| sonnet-union-4.analysis | 364 | e54c044ee2a22926433714dd7f6c960c6ef14e84bb8faae31bfcc5e995ab78c8 |  |
| sonnet-union-4.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-union-4.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-union-4.out | 617 | 9ca2ef586b309ec1a5e1f4a38d9beec0cf1951da0df7001f76d0189967a67d75 |  |
| sonnet-union-4.sqlite | 38,166,528 | 3ff9786344626c3dab8018e20f07bae7db4d2705a0c7980868c570d2aac884fd | ab8e9f14088b4853 |
| sonnet-union-5.analysis | 360 | 0a79f49a0267d934d01840f86566d5a1f2c47aae8c7bcf8f289baf4b842b5753 |  |
| sonnet-union-5.err | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |  |
| sonnet-union-5.exit | 2 | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |  |
| sonnet-union-5.out | 611 | c084cf7a8de2e8479628622b56a982e7187e9d38f5ae15c9a67bfaf7deea6b59 |  |
| sonnet-union-5.sqlite | 71,843,840 | b4cfd13af523bc4c2066d352576a9536657942094970992bed6197591e014a55 | 79f12e60aa154227 |

