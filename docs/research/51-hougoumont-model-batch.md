# 51 — Hougoumont model batch: Sonnet 5.5 and Astra against a scripted gate attacker

**Version:** 1 (2026-11-06). **Rules:** `poc-12`. **Scenario:** `hougoumont-north-gate-v3`. **Prompt version:** `hougoumont-side-v1`. **Player side:** `allied`. **Opponent:** `scripted-gate-attacker-v1` (French). **Response format:** `json_schema:commander_orders`. **Models:** `anthropic/claude-sonnet-5.5` (`s1`, `s2`, `s3`) and `openai/gpt-6-astra` (`a1`, `a2`), reasoning effort `high` for both. **Control:** one run with both sides scripted (the Allied side under `scripted-gate-defender-v1`). **Runs:** 5 model runs, one of them (`a1`) a failed run, and 1 control.

Machine-readable rows: [`apps/poc/experiments/hougoumont-batch/summary.json`](../../apps/poc/experiments/hougoumont-batch/summary.json). Every figure below was read from the run databases (stored events, snapshots and decision records) of a local, uncommitted archive that is listed at the end. Prompts, observations, response text and proposed orders are not reproduced. The scenario is described in [42](42-hougoumont-scenario.md), the gateway push in [44](44-poc11-gateway-push.md) and the contact rules of `poc-12` in [45](45-poc12-contact-rules.md).

## Result

- All six runs ended in an Allied win at turn 60 ("The Allied garrison held the farm until the scenario deadline."). Every run replayed with status `identical`.
- `s1`, `s2` and `s3` (Sonnet 5.5) all had 20 of 20 Allied decisions from the model. `a2` (Astra, re-run) did too.
- `a1` (Astra) is a failed run, not a model result: 16 of its 20 Allied decisions (80%) fell back to scripted orders with reason `provider_error:KeyError`. `a2` supersedes it.
- The Sonnet runs and the control show a gateway push at the north gate and no gate closing. `a2` closed and barred the gate and shows no gateway push.
- Recorded spend, the sum of `usage.cost` on the Allied decisions: $3.25 over the five model runs ($2.93 without `a1`).

## Per-run table

Strengths are final strength by unit (`A` Allied, `F` French); all runs started `A1` 15, `A2` 60, `A3` 60, `F1` 30, `F2` 80, `F3` 40. Decisions are model decisions over Allied decisions; the rest are fallbacks. Tokens are prompt / completion (reasoning, included in completion), summed over the Allied decisions. Latency is the median of the Allied decisions' `latency_ms`. Cost is the sum of `usage.cost` on those decisions. Replay and events come from the stored run result.

| Run | Player | Model, effort | Winner | Turns | Final strength | Replay | Events | Decisions (model/total) | Fallback | Tokens | Latency median | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| control | scripted | none (scripted both sides) | allied | 60 | A1 0, A2 0, A3 56, F1 0, F2 69, F3 24 | identical (64 revisions) | 2,350 | n/a | n/a | n/a | n/a | n/a |
| s1 | model | claude-sonnet-5.5, high | allied | 60 | A1 0, A2 0, A3 54, F1 0, F2 70, F3 25 | identical (81 revisions) | 2,209 | 20/20 | 0 | 150,560 / 3,839 (296) | 2.06 s | $0.340 |
| s2 | model | claude-sonnet-5.5, high | allied | 60 | A1 0, A2 0, A3 54, F1 0, F2 70, F3 25 | identical (81 revisions) | 2,191 | 20/20 | 0 | 145,966 / 4,129 (631) | 2.02 s | $0.333 |
| s3 | model | claude-sonnet-5.5, high | allied | 60 | A1 0, A2 0, A3 54, F1 0, F2 70, F3 25 | identical (81 revisions) | 2,191 | 20/20 | 0 | 145,966 / 4,220 (552) | 2.22 s | $0.334 |
| a1 | model, failed | gpt-6-astra, high | allied | 60 | A1 0, A2 0, A3 57, F1 0, F2 70, F3 23 | identical (81 revisions) | 2,187 | 4/20 | 16 | 20,014 / 1,455 (1,159) | 0.47 s (9.07 s over the 4 model decisions) | $0.323 |
| a2 | model, supersedes a1 | gpt-6-astra, high | allied | 60 | A1 0, A2 50, A3 23, F1 0, F2 56, F3 29 | identical (81 revisions) | 2,805 | 20/20 | 0 | 116,262 / 10,452 (8,883) | 14.42 s | $1.923 |

Total recorded cost over `s1`, `s2`, `s3`, `a1` and `a2`: $3.2524. The control carries no cost.

Provider-reported model matched the requested model on every model decision in all five runs. For `s2` and `s3` the final strengths, event count and revision count are the same; the decision text and tokens are not (completion tokens 4,129 and 4,220).

Reading the table: the model runs differ in outcome only in the final strengths, since the winner and turn are the same everywhere. In `s1` to `s3` and `a1` the Allied units `A1` and `A2` end at 0, as in the control. In `a2` `A2` ends at 50 and the gate ends `barred` (next section).

## a1: a failed run

In `a1` 16 of 20 Allied decisions were fallbacks, all with stage `provider_error` and reason `KeyError`. The 4 model decisions were at turns 0, 42, 45 and 57; the fallbacks were at turns 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 48, 51 and 54. The run's error stream is empty. The decision record names the error class and nothing about its cause, so this report does not state one. The fallback rate is 80%, so `a1` measures a provider path that failed on most turns. Its result, token counts, latency and cost describe that mix of scripted and model orders and are not comparable with the other model runs. The cost of $0.323 comes from the 4 model decisions. `a2` is the same model, scenario, prompt and effort, run again, with 0 fallbacks; it is the Astra result of this batch.

## Gate timeline: a2 and the control

`a2` is the only run with `gate_state` events. The north gate started `open`. The unit named is the one carrying the work.

| Turn | Transition | Work unit | Units inside the farm | Gate work recorded |
|---|---|---|---|---|
| 19 | open to closing | A2 | A2, A3, F2 | close, effort 20 of 45 |
| 21 | closing to closed | A2 | A2, A3 | close, effort 45 of 45 (turns 19 to 21) |
| 23 | closed to barred | A2 | A2, A3 | bar, effort 30 of 30 (turns 22 and 23) |

`units_outside` was empty at every transition. French unit `F2` is listed inside at turn 19, the turn it moved off hex 10,9 to 11,9 (it had routed at turn 18), and is not listed at turns 21 and 23. The gate stayed `barred` to the end. There is no `gateway_push` or `gateway_carried` event in `a2`.

The control and the three Sonnet runs record no `gate_state` event; their gate was `open` at the end. They record the same sequence of `gateway_push` events and one `gateway_carried` event:

| Turn | Event | Detail |
|---|---|---|
| 15 | `gateway_push` | pusher `F2`, holder `A1`, effort 20 of 60, under fire |
| 16 | `gateway_push` | effort 40 of 60, under fire |
| 17 | `gateway_push` | effort 60 of 60, not under fire |
| 17 | `gateway_carried` | `F2` displaced `A1` from the gateway, 0 losses |

The control and `s1` to `s3` show the same turns for the push (15, 16, 17); event sequence numbers differ.

## Edition note

The batch ran under `poc-12`. `main` is now `poc-13`. [47](47-poc13-part-b-command-and-smoothbore.md) states that the Hougoumont digests are unchanged and that its model prompt is now `hougoumont-side-v2`, with a note that model runs are not comparable across the prompt change. This report claims no more than that. These runs were not repeated on `poc-13`, and `prompt_version` here is `hougoumont-side-v1`.

## Limits

- The sample is small: 3 Sonnet runs, 2 Astra runs of which one failed, and 1 control. No confidence interval or significance claim is made. The two models are not compared: `a2` is one run.
- The opponent is a scripted attacker. The Allied win in the control, which uses no model, means a win here says little about model skill.
- One scenario, one side (Allied), one prompt version, one effort.
- The authored units, positions, labour and push values are illustrative sensitivity parameters ([42](42-hougoumont-scenario.md), [44](44-poc11-gateway-push.md)). This report makes no realism or historical-accuracy claim.
- The report tunes and fits nothing and proposes no change. It records what the stored runs show, and does not say why `a2` closed the gate when the others did not.
- Cost and latency are as measured on 2026-11-06 through the provider path used; prices, routing and latency change. The control median latency is not applicable.
- Not derived: wall-clock run time per game, and anything about prompts and responses (deliberately excluded). The code commit used for the batch was not recorded in the archive.

## Artifact manifest

**Local only, not published (git-ignored archive).** The batch lives in an uncommitted archive folder under `apps/poc/artifacts/`, with an `astra-rerun/` subfolder for `a2`. It holds, for each run, the stored result line (`.out`), the error stream (`.err`) and the run database (`.sqlite`), plus the driver script `run.sh`, the analysis script `analyze.py` and a `SHA256SUMS` file; `astra-rerun/` has its own `SHA256SUMS`. The `.sqlite` files hold decision records and the message log, which this report does not publish.

**Archive verification (2026-11-06).** `shasum -a 256 -c SHA256SUMS` reported every file OK, 19 of 19 in the archive folder and 5 of 5 in `astra-rerun/`. Queries for this report ran on copies of the databases; the archive was not modified.
