# 69 — Model runs: cost estimate for six entries (Cannae excluded)

**Version:** 2 (2026-11-08). **Repo:** `main` at `ff8655b`. **Status:** an estimate for the Architect's approval. No model API was called and nothing was spent. Version 1 changed no code; version 2 adds the batch driver and its guards (section 9). The spend choice is the owner's D37. **Scope:** a model player against the scripted control on Little Round Top, Hougoumont, Concord North Bridge, Pegasus Bridge, Hill 223 and Gergovia. Cannae waits on the owner ruling (D34) and is priced only as a reference line (section 6).

## Summary

- A model run is one provider call per 3 turns for the model's side. The scripted opponent costs nothing. Calls per game are `ceil(turns / 3)`.
- Cost depends on game length, because the observation grows through the game. Little Round Top and Hougoumont are fixed at 60 turns (20 calls, about $0.38 each with Sonnet 5.5). Hill 223, Gergovia and Pegasus range from a few calls to 80 to 150 calls, so one game costs from $0.04 to $6.41 with Sonnet 5.5, depending on whether the model's game ends early or runs to the deadline.
- **Smallest useful option (A):** Sonnet 5.5, 16 games, planning figure **$12.2**, proposed cap **$16**. The worst case, every game to its deadline, is $31.7.
- **Fuller option (B):** Sonnet 5.5 plus Opus 5.5 plus Astra, 65 games, planning figure **$68.1**, proposed cap **$90**. The worst case is $190.6.
- Past spend and the formula agree: the formula gives $0.38 for a Little Round Top Sonnet game, and batch A's Sonnet games averaged $0.39.

## 1. Evidence: past spend

| Run set | Games | Models | Recorded cost | Source |
|---|---|---|---|---|
| M2 | not found | not found | about $4.2 (handoff note) | Not in this repo, its artifacts or the memory palaces searched. Taken as stated; not verified here. |
| Batch A, Little Round Top (`poc-8`, `lrt-side-v2`) | 14 model games, 261 decisions | Sonnet 5.5 x10, Astra x4 | **$11.69** (sum of `usage.cost`; my sum of the table in doc 40 is $11.688) | [40](40-batch-a-lrt-model-baseline.md); `apps/poc/artifacts/batch-a-2026-11-06/` |
| Hougoumont (`poc-12`, `hougoumont-side-v1`) | 5 model games (Sonnet x3, Astra x2, one failed) | as listed | **$3.25** recorded in doc 51 ($2.93 without the failed `a1`); the handoff says $3.59 of an $8 cap | [51](51-hougoumont-model-batch.md); `apps/poc/artifacts/hougoumont-batch-2026-11-06/` |

The $0.34 between $3.59 and $3.25 is not in the archive. It is about one Sonnet game. It may be probe calls outside the archive. I did not resolve it.

**Tokens per decision, read from the run databases** (`decisions.payload.usage`, model decisions only):

| Archive | Model | Input tokens per decision | Output tokens per decision | Cost per decision | Cost per 20-decision game |
|---|---|---|---|---|---|
| Batch A, Union | Sonnet 5.5 | 7,900 | 528 | $0.021 | $0.42 |
| Batch A, Confederate | Sonnet 5.5 | 8,385 | 720 | $0.024 | $0.48 |
| Hougoumont, Allied | Sonnet 5.5 | 7,300 to 7,530 | 191 to 211 | $0.017 | $0.33 to $0.34 |
| Batch A, Union | Astra | 6,066 | 804 | $0.116 | $2.32 |
| Hougoumont, Allied | Astra (`a2`) | 5,813 | 522 | $0.096 | $1.92 |

Batch A means over its games, from doc 40: Sonnet 5.5 $0.391 per game (145,792 input and 9,944 output tokens); Astra $1.945 (110,519 and 12,560). Game length was 14 to 20 decisions.

**Prices the earlier runs used.** The provider was OpenRouter. Each decision stores `usage.cost` and `cost_details`, so the rates follow from the databases:

- **Sonnet 5.5: $2 per million input, $10 per million output.** Example: 6,658 input tokens cost $0.013316 and 260 output tokens cost $0.0026 (`hougoumont-batch-2026-11-06/s1.sqlite`, decision 0). No cache was used (`cached_tokens` 0). This equals Anthropic's list price for Sonnet 5.5.
- **Astra (`openai/gpt-6-astra`): $12.50 per million input, $50 per million output.** Nearly all its input was billed as cache write at $12.50 (3,983 write tokens cost $0.0498 in `astra-union-1`, decision 0); cache reads cost $1 per million (4,618 read tokens cost $0.0046 in `a2`). Output: 693 tokens cost $0.03465. I found no price list for Astra; these rates are derived from the stored costs only.

## 2. How the model player is called

Read from `apps/poc/battle/services/headless.py`, `services/commander.py`, `adapters/openrouter.py`, `command_policy.py` and `config.py`.

- **Cadence.** `HeadlessRunner.run` makes one `commander.decide` call for the player side when `turn % 3 == 0`, which is every 90 seconds of game time. The opponent's scripted decision is issued in the same step and calls no provider. So there is one model call per decision and one commander per side. Calls per game are `ceil(turns / 3)`; all six entries use 30 seconds per turn.
- **Request.** Two messages and no history. System: the entry's shared rules, the side's own mission and the voice rules, 2,987 to 3,721 characters per side (about 1,300 to 1,650 Sonnet tokens). User: JSON of `{"task", "observation"}`, where the observation is the side's fog-limited view: units, contacts, reports, orders in transit, map features, order catalog, recommendations. Parameters: `temperature` 0.3, `max_tokens` 4,000 when an effort is set, timeout 90 s, `response_format` a strict `json_schema`, `reasoning.effort` as given (the earlier runs used `high`).
- **Reply.** `{"text": ..., "orders": [up to 3 of {unit_id, stance, destination}]}`. The reply schema holds orders only. It carries no standing instructions and no split or combine.
- **Failure.** A provider error, a bad reply or a refused order falls back to the plain scripted control for that decision and is flagged (`fallback`, `fallback_reason`). A response that was paid for but failed to parse still carries its usage and cost.
- **Observation growth.** The observation includes accumulated reports and orders, with no cap. Mean request size at the start of a game is 15,600 to 19,600 characters; late in a long game it reaches 41,000 (Pegasus), 39,000 (Gergovia) and 70,700 (Hill 223) characters. A long game therefore costs more than its call count suggests.

## 3. How the figures were made

1. **Requests measured with no network.** I ran each entry through `build_headless(player_provider="openrouter", provider=<fake>)`, where the fake provider returns the entry's scripted orders and records the exact length of each request. All six default entries completed with 0 fallbacks and replay `identical`. This gives true prompt and observation sizes, but the observation follows the scripted-control game, not a model game. The harness is in `/tmp/cost69/` and is not committed.
2. **Characters to tokens.** 2.25 characters per token for Claude (measured 2.25 to 2.26 over four archived Sonnet games on Little Round Top and Hougoumont) and 3.17 for Astra (measured 3.14 to 3.19).
3. **Output.** 450 tokens per call for Sonnet 5.5, with a 200 to 750 range. Archived runs: 191 to 211 on Hougoumont, 528 to 720 on Little Round Top. Opus 5.5: 600 (an assumption; no Opus 5.5 run exists). Astra: 650 (measured 522 to 840).
4. **Check against the past.** The method gives $0.38 for a Little Round Top Sonnet game (archived mean $0.391, range $0.23 to $0.51) and $1.95 for an Astra game (archived mean $1.945).

**Current prices, checked 2026-11-08** (Anthropic pricing page, `platform.claude.com/docs/en/about-claude/pricing`; the OpenRouter model pages list the same rates with no markup). I could not call the `claude-api` skill from this session, so I read the pricing page directly.

| Model | Input per million | Output per million | Note |
|---|---|---|---|
| Claude Sonnet 5.5 (`anthropic/claude-sonnet-5.5`) | $2 | $10 | Used before. Cache hit $0.10. |
| Claude Opus 5.5 (`anthropic/claude-opus-5.5`) | $4 | $20 | Not run before. OpenRouter lists `response_format` and `reasoning` as accepted fields; I did not test them. |
| Claude Haiku 5.5 | $0.10 (prompts up to 100,000 tokens) | $0.50 | About one twentieth of Sonnet. Not planned; quality for this task is unknown. |
| Claude Fable 5.1 | $10 | $50 | Not planned. |
| Astra | $12.50 | $50 | Derived from stored costs (section 1). Used for the fuller option only. |

The code supports any OpenRouter model id (`--model`); it has no direct Anthropic path. "Current Claude models" therefore means an OpenRouter id, and only Sonnet 5.5 has been run through this adapter.

## 4. Cost per game, by entry

"Base" is the game length of the entry's scripted control. "Deadline" is the game run to its limit. The model decides which one happens; the control fixes only the base. Player side as in the entry (the defender or attacker the entry names).

**Base length** (the control's end turn):

| Entry (player side) | Turns | Model calls | Request characters | Sonnet input / output tokens | Sonnet 5.5 | Opus 5.5 | Astra (input tokens) |
|---|---|---|---|---|---|---|---|
| `little-round-top` (union) | 60 | 20 | 328,361 | 145.9k / 9.0k | $0.38 | $0.82 | $1.95 (103.6k) |
| `hougoumont-north-gate` (allied) | 60 | 20 | 338,709 | 150.5k / 9.0k | $0.39 | $0.84 | $1.99 (106.8k) |
| `concord-north-bridge` (provincial) | 8 | 3 | 51,289 | 22.8k / 1.4k | $0.06 | $0.13 | $0.30 (16.2k) |
| `pegasus-bridge` (british) | 5 | 2 | 34,596 | 15.4k / 0.9k | $0.04 | $0.09 | $0.20 (10.9k) |
| `hill-223-patrol` (american) | 27 | 9 | 153,678 | 68.3k / 4.1k | $0.18 | $0.38 | $0.90 (48.5k) |
| `gergovia-recall` (roman) | 36 | 12 | 258,490 | 114.9k / 5.4k | $0.28 | $0.60 | $1.41 (81.5k) |

**Deadline length:**

| Entry | Turns | Model calls | Request characters | Sonnet input / output tokens | Sonnet 5.5 | Opus 5.5 | Astra |
|---|---|---|---|---|---|---|---|
| `little-round-top`, `hougoumont-north-gate` | 60 | 20 | as above | as above | $0.38 / $0.39 | $0.82 / $0.84 | $1.95 / $1.99 |
| `concord-north-bridge` | 20 | 7 | about 133,000 (estimate: 7 x 19,000) | 59.1k / 3.2k | $0.15 | $0.32 | $0.75 |
| `pegasus-bridge`, variant `guard-only` | 360 | 120 | 3,504,458 | 1.56M / 54k | $3.66 | $7.67 | $17.72 |
| `hill-223-patrol`, variant `surrender-on-threat` | 450 | 150 | 6,455,284 | 2.87M / 67.5k | $6.41 | $13.28 | $30.33 |
| `gergovia-recall`, variant `strength-40` | 240 | 80 | 2,480,745 | 1.10M / 36k | $2.57 | $5.37 | $12.38 |

How the base lengths arise (scripted control, latest archives):

- **Pegasus default** ends at turn 5: the guard fires the bridge at 00:27:30 on contact, a German win ([54](54-pegasus-scenario-runs.md)). The model sees two observations. Only a model that avoids contact gets a longer game; the `guard-only` variants run to turn 360 (relief) or 480.
- **Hill 223 default** ends at turn 27 (an American win, 9 decisions). Eleven of 12 scripted runs end between turn 21 and 36; `surrender-on-threat` runs to the 450-turn deadline.
- **Gergovia default** ends at turn 36 (a Gallic win, 12 decisions); `recall-audible` ends at 41. `strength-40` and `strength-80` run to the 240-turn deadline.
- **Concord** ends at turn 8 in three of four archived runs and at 20 in `british-west-bank`.
- A scripted American or Roman side wins or loses early because it follows authored scripts; a model that does not make the same moves will probably play longer. I cannot say how much longer.

## 5. Proposed run plan

Every game is one model side against the scripted control, with the entry's scripted opponent. The scripted control itself costs nothing and is deterministic; one control run per entry (already recorded for each) is enough. The model baselines of Little Round Top (`lrt-side-v2`, `poc-8`) and Hougoumont (`hougoumont-side-v1`, `poc-12`) were made under older rules and prompts; doc 51 (citing doc 47) says model runs are not comparable across the prompt change. They must be re-run on `poc-13` for a like-for-like comparison, and that cost is in the plan.

**Planning figure per game** (Sonnet 5.5, then Opus and Astra on the same basis): the base cost for Little Round Top, Hougoumont and Pegasus (which is the control's length and cheap); the midpoint of base and deadline for Concord, Hill 223 and Gergovia. The midpoint is a guess about how often a model game runs long, not a measurement.

| Entry | Planning, Sonnet | Planning, Opus | Planning, Astra | Worst case, Sonnet |
|---|---|---|---|---|
| `little-round-top` | $0.38 | $0.82 | $1.95 | $0.38 |
| `hougoumont-north-gate` | $0.39 | $0.84 | $1.99 | $0.39 |
| `concord-north-bridge` | $0.10 | $0.22 | $0.53 | $0.15 |
| `pegasus-bridge` | $0.04 | $0.09 | $0.20 | $3.66 |
| `hill-223-patrol` | $3.30 | $6.83 | $15.61 | $6.41 |
| `gergovia-recall` | $1.42 | $2.99 | $6.90 | $2.57 |

### Option A: smallest useful

Sonnet 5.5, effort `high`, the entry's player side, against the scripted control.

| Block | Games | Planning | Worst case |
|---|---|---|---|
| Little Round Top, Hougoumont, Concord, Pegasus, 3 games each | 12 | $2.75 | $13.73 |
| Gergovia and Hill 223, 2 games each | 4 | $9.44 | $17.96 |
| **Total** | **16** | **$12.19** | **$31.69** |

**Proposed cap: $16** (planning plus 25 percent for output variance and failed or repeated calls, rounded up). It sits below the worst case, so the order of work matters (below). Stage 1 (the first block, $2.75 planning) can be approved alone with a $4 cap; its worst case needs a Pegasus game to run to turn 360.

### Option B: fuller

| Block | Games | Planning | Worst case |
|---|---|---|---|
| B1: Sonnet 5.5, player side, 5 games on each of the six entries | 30 | $28.18 | $67.78 |
| B2: Sonnet 5.5, other side (the opponent role), 3 games on each entry except Hill 223 | 15 | $7.02 | $21.43 |
| B3: Opus 5.5, player side, 2 games on each of the six entries | 12 | $23.58 | $56.61 |
| B4: Astra, player side, 2 games on Little Round Top, Hougoumont, Concord, Pegasus | 8 | $9.32 | $44.80 |
| **Total** | **65** | **$68.10** | **$190.62** |

**Proposed cap: $90** (planning plus 25 percent, rounded up). The blocks are separable: B1 adds sample size for the Sonnet baseline; B2 adds the second side; B3 and B4 add a second and third model. Drop B3 or B4 to save $23.6 or $9.3 of planning.

### Controls that keep the cap real

- The runner has no spend limit and no decision limit. The only bounds are per request: `max_tokens` 4,000 and a 90-second timeout. A game in flight cannot be stopped by the cap. In the worst case a single Hill 223 game costs $6.41 (Sonnet) or $30.33 (Astra).
- Run the cheap entries first, one game at a time, and run Hill 223, Gergovia and Pegasus variants one game at a time. After each game, sum `usage.cost` from the run database and stop when the running total reaches the cap. The runner's summary reports `player_decisions` (total, model, fallback), so a run that fell back is visible without opening the database.
- Set the OpenRouter key's credit limit to the cap. A limit hit mid-run gives HTTP errors, which become scripted fallbacks; the run completes but is not a model result (as `a1` in doc 51: 16 of 20 decisions fell back).
- Check each finished game for `fallback > 0` and drop it from the comparison.
- Wall clock: Sonnet's median decision latency was 2 to 7 seconds, Astra's 13 to 23. A 20-call game takes about 2 minutes (Sonnet). A 150-call Hill 223 game takes about 20 minutes plus about 3 minutes of simulation.

## 6. Cannae (excluded; reference only)

The scripted Carthaginian side's 54 observations average 86,000 characters (26,000 to 119,000), against 3,600 for the prompt. A Sonnet 5.5 game at 54 calls would carry about 2.2M input tokens and cost about **$4.7** ($4.4 input, $0.2 output). This is from the scripted opponent's observation, not a Roman one, and the model path was not run on Cannae. It is not in either option.

## 7. Assumptions and uncertainty

- **Game length is the largest unknown.** Little Round Top and Hougoumont are fixed (20 calls). For Hill 223, Gergovia and Pegasus the model, not the control, decides when the game ends. The planning figures take the midpoint for Concord, Hill 223 and Gergovia and the base for Pegasus. If every model game ran to its deadline, option A costs $31.7 and option B costs $190.6.
- **Observation size comes from scripted games.** A model that issues more orders produces more order and report entries, so its observation may be larger. Pegasus, Hill 223 and Gergovia deadline rows come from the `guard-only`, `surrender-on-threat` and `strength-40` scripted variants, not from the default entries run long. Concord's deadline row is an estimate (7 calls at 19,000 characters), not a dry run.
- **Output tokens are the second-largest error.** Sonnet output ranged from 191 to 720 per decision in archived runs; the 200 to 750 range changes a Little Round Top game by about $0.05 and a Hill 223 deadline game by about $0.45. Reasoning at `high` effort is included in completion tokens. Opus 5.5 output (600) is a guess.
- **Token ratio.** 2.25 characters per token is measured on Sonnet 5.5. I assumed Opus 5.5 tokenises like Sonnet 5.5; I did not check.
- **Prices.** Sonnet 5.5 and Opus 5.5 are Anthropic list prices as of 2026-11-08, carried by OpenRouter at no markup per its pages. Astra's rates are derived, not published. OpenRouter routing and cached-input behaviour can change the bill; archived Sonnet runs showed no cached input. Caching the 3,000-character system prompt would save little, since it is under a fifth of a request.
- **Archive gaps.** M2's cost and the $0.34 in the Hougoumont total were not found. The Hougoumont archive did not record the code commit.
- **Sample size.** Three to five games per cell show a spread, not a significance level; doc 40 and doc 51 make the same point. Temperature is 0.3, so repeated games differ (Little Round Top Union held 4 of 5).
- **Outcome interpretation.** Little Round Top and Hougoumont favour the defender even under the control (docs 40, 51), and the Pegasus default is decided in 5 turns. A cost estimate does not make these runs informative; it prices them.

## 8. Code gaps for model runs

None blocks a model run on a default entry. All six completed a model-path run (fake provider) with 0 fallbacks and replay `identical`. The gaps below limit what the runs can show.

1. **The command-line runner reaches only default entries.** `python3 -m battle --headless --scenario ID --player-provider openrouter` takes ids from `HEADLESS_SCENARIOS`; the named variants (Pegasus `guard-only`, Gergovia `recall-audible`, Hill 223 `surrender-on-threat`) are not registered. `build_headless` accepts `scenarios=ScenarioRegistry([entry])`, and `scripts/*_runs.py` use it for scripted runs only. A model run on a variant needs a new driver script (the dry-run harness in `/tmp/cost69/dry.py` is one). Needed for Option A's Pegasus value and Option B's variants.
2. **No model-path test exists for Concord, Pegasus, Hill 223 or Gergovia.** `tests/test_headless_player.py` and `tests/test_hougoumont.py` cover Little Round Top and Hougoumont. My fake-provider run shows the path completes on the other four, but no committed test pins it.
3. **No spend or decision cap in the runner** (section 5). A limit needs a driver or a key-level credit limit.
4. **Fallback hides a degraded run.** On a provider error the decision becomes the plain `scripted-fallback-v1` order set, not the entry's scripted control, and the run still finishes. Doc 51's `a1` shows an 80 percent fallback rate. A driver must check `player_decisions.fallback`.
5. **The reply carries orders only.** The model cannot issue the standing instructions that Hougoumont's scripted controls use (`close_on_breach`, `firm`) or split and combine. The model and the control therefore do not have the same action set on Hougoumont; I did not check the other entries' controls for the same difference.
6. **Prompts changed since the old baselines** (`lrt-side-v3`, `hougoumont-side-v2`; poc-13 adds `hold_fire` and `open_fire`). Old results cannot stand in for new ones; the plan re-runs both.
7. **Pegasus default is nearly decided before the model acts** (2 decisions, bridge destroyed at turn 5). A model run on it prices at $0.04 and says little; the informative Pegasus runs are the `guard-only` variants, at up to $3.66 per game (Sonnet).
8. **Every entry has a prompt for both sides** (2,987 to 3,721 characters), so no entry lacks a side prompt. Headless-only status is not a blocker: the model path is the headless runner.

## 9. The batch driver and its guards

`apps/poc/scripts/model_runs.py` runs a batch of model games. It closes gaps 1, 2 and 3 of section 8 and makes gap 4 stop the batch. It does not set the key's credit limit: the third control of section 5 (the OpenRouter key's credit limit equal to the cap) stays open, pending D37.

- **Plan.** `--plan ENTRY[/VARIANT]`, repeatable, names the games; `--games N` plays each item N times in plan order; `--model`, `--effort`, `--cap-usd` and `--dir` (a new directory per batch) complete the run. Items reach the six entries above and their named variants (Concord's 3, Pegasus's 7 plus its range and crossed sensitivities, Hill 223's 11, Gergovia's 13), for example `pegasus-bridge/guard-only`. Cannae is not offered. An unknown name is refused before any game starts. Each game is one model side (the entry's player) against the entry's scripted control, in its own `BatchStore` database.
- **Cap.** After each game the driver adds the recorded `usage.cost` of every player decision to a running total. It starts no game once the total reaches the cap and exits 3. A game in flight is not stopped, so one game can pass the cap by its own cost.
- **Cost fails closed.** A player decision with no `usage.cost`, or a cost that is not a finite number of zero or more, fails the game. It is never counted as $0. The batch stops with exit 4.
- **Fallback fails the game.** Fallbacks are made in `services/commander.py`, `CommanderService.decide`: a provider error or timeout (line 198), a reply that is not an object (line 205) and orders that fail validation (line 215), all through `_fallback` (line 260). The record has `fallback` true and the run goes on. The driver builds the runner with `abort_on_fallback`, a new opt-in on `HeadlessRunner` and `build_headless`: at the first player decision that is not the model's own, the run raises `ModelFallback` before that decision is committed, so no later call is made. A finished game is checked again (any fallback, any non-model decision, replay not `identical`). A failed game's database is renamed `*.failed.sqlite`, the cost already paid is still added, and the batch stops with exit 4. The option is off by default, so scripted runs, earlier model runs and replay are unchanged.
- **Output.** One JSON line per game, then a summary (status, exit, spend, games played, model games, games not started, failures), also written to `batch-summary.json`. `spend_complete` false means a failed call had no readable cost and the spend shown is a floor. Exit 0 means every planned game finished as a model game below the cap.
- **Tests.** `apps/poc/tests/test_model_runs.py`, fake providers only: one short model game each on Concord, Pegasus, Hill 223, Gergovia and Concord `two-companies`, each replay `identical` with 0 fallbacks; the stop at the cap; a missing cost; and a provider error, a timeout and a junk reply.

## Source files read

`apps/poc/battle/services/headless.py`, `services/commander.py`, `adapters/openrouter.py`, `command_policy.py`, `config.py`, `bootstrap.py`, `inference.py`; the scenario modules for the six entries; `docs/research/40`, `51`, `54`, `61`, `62`, `68`; archives `batch-a-2026-11-06`, `hougoumont-batch-2026-11-06`, `pegasus-d2-2026-11-07`, `hill223-d7b-679b637`, `gergovia-d85-d7b6838`, `concord-baseline-2026-11-06`, `cannae-d86-d829763-single` (read-only, `immutable` mode).
