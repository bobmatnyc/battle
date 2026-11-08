# 78 — D37 guards on the paid model batch

**Date:** 2026-11-08. **Task:** bt-T13. **Rulings:** D37 (Bob): option A of [69](69-model-run-cost-estimate.md) §5, Sonnet 5.5, 12 games, a $14 cap (planning $10.65, worst case $30.15), on a new OpenRouter key limited to $14. Architect key decision: battle project scope, secret `OPENROUTER_API_KEY_D37`, injected as `OPENROUTER_API_KEY` into the batch process only. Architect acceptance (14:45Z): items 1 to 7 below. Code head `8bbb87c`, base `65775a1` (draft PR #14's branch rebased onto it). No model API was called, no key was read and nothing was spent.

This doc closes what [69](69-model-run-cost-estimate.md) §9 left open: "the third control of section 5 (the OpenRouter key's credit limit equal to the cap) stays open, pending D37".

## 1. What changed

| Item | Change | Files |
|---|---|---|
| 1. No overshoot | `SpendGuard` sums spend and reserve as exact decimals of each amount's float repr and refuses a call only when spend so far + its reserve > cap. A call landing exactly on the cap is allowed; one cent over is refused, before the provider is called. The float check refused the exact-cap call: 14 - 13.99 - 0.01 = -2.1e-16 | `apps/poc/battle/spend.py` |
| 2. Key limit | Before any spend the batch calls OpenRouter's key-info endpoint (`GET https://openrouter.ai/api/v1/key`) through an injectable opener. It refuses to start unless `limit` is set, `limit` <= cap, `limit_remaining` >= cap and `is_free_tier` is not true. A network, HTTP, decode or shape error refuses (fail closed). The check (limit, remaining, reset, free tier, usage; never `label`, which can show part of the key) is pinned in `manifest.json` as `key_check` | `apps/poc/battle/adapters/openrouter.py` (`fetch_key_info`), `apps/poc/battle/paid_batch.py` (`key_limit_check`, `check_key`), `apps/poc/scripts/model_runs.py` |
| 3. Key from the environment | `model_runs.py` takes the key only from `OPENROUTER_API_KEY` in its own process environment. Missing, empty, or rejected by the key-info call (401 or 403) refuses to start, before any file is written. It never reads `apps/poc/.env.local`: `Settings.load(None, environ)` reads no file. `run_batch` itself refuses the OpenRouter adapter without a key or a passing key check. The desk and `python3 -m battle --headless` keep their `.env.local` behaviour (the default `path` is unchanged) | `apps/poc/battle/config.py`, `apps/poc/battle/paid_batch.py`, `apps/poc/scripts/model_runs.py` |
| 4. Model pinned | `--paid-plan d37-option-a` fixes the model `anthropic/claude-sonnet-5.5`, effort `high`, 4,000 output tokens, 90 s timeout, prices $2 / $10 per million, the $14 cap and the 12-game plan. It refuses `--model` (any value, including Sonnet), `--plan`, `--games`, `--cap-usd`, `--effort`, `--max-tokens`, `--timeout` and the price flags. It reads no other `OPENROUTER_*` variable. The same `Settings` builds the request body, sizes the reserve and fills the manifest | `apps/poc/battle/paid_batch.py` (`D37_OPTION_A`, `plan_settings`), `apps/poc/scripts/model_runs.py` |
| 5. Provider-limit stop | An OpenRouter refusal for credit or a spend limit (HTTP 402; a 403 or 429 whose `error.metadata.limit_source` names a credit or budget source; the same in an HTTP 200 body) is recorded on the fallback decision as `provider_limit` (`{"status", "limit_source"}`, no message text). The runner already aborts at that fallback, before it is stored. The game is kept as `*.stopped.sqlite`, the batch stops with exit 5 (`provider_limit`), and the reason and spend so far go to `runs.jsonl`, `batch-summary.json` (`reason`) and the manifest (`closed`). Other 403 and 429 refusals fail the game as before (exit 4) | `apps/poc/battle/adapters/openrouter.py` (`limit_refusal`), `apps/poc/battle/services/commander.py` (`record_response`), `apps/poc/scripts/model_runs.py` (`play`, `run_batch`) |
| 7. Plan and dry run | `ENTRY[/VARIANT]:N` gives a plan item its own game count. `--paid-plan d37-option-a --dry-run` prints the plan, play order, model, limits, prices, cap, source pin and a key-limit check made through a fake opener. It reads no key, makes no network call and writes no file | `apps/poc/scripts/model_runs.py` (`dry_run`), `apps/poc/battle/paid_batch.py` (`fake_key_opener`) |
| Manifest | `manifest.json` adds `games_per_item`, `paid_plan`, `key_check`, and at the end `closed` (status, exit, reason, spend, spend complete, played, not started). `batch-summary.json` adds `reason` | `apps/poc/scripts/model_runs.py` |

Item 6 (the existing guards) is unchanged code; section 3 lists its tests.

**Exit codes.** 0: every planned game finished as a model game within the cap. 2: refused before start (dirty tree, key, key limit, flags). 3: the cap (a budget stop, or spend at the cap). 4: a failed game (fallback, missing cost, replay mismatch, interrupt). 5: an OpenRouter credit or budget refusal.

## 2. OpenRouter behaviour the guards rely on

From OpenRouter's limits page (`openrouter.ai/docs/api/reference/limits`, read 2026-11-08):

- `GET https://openrouter.ai/api/v1/key` with the key returns `data` with `limit` (null if unlimited), `limit_reset`, `limit_remaining` (null if unlimited), `usage`, `is_free_tier`, `label`, and budget fields. The check reads the first five.
- A per-key credit limit or a low balance refuses with 402, `error.metadata.limit_source` `openrouter_key_limit`, `openrouter_credits` or `openrouter_in_flight_budget`. The in-flight case is transient; the batch still stops, since it cannot tell it apart without the message.
- A guardrail, workspace or spent key budget refuses with 403, `limit_source` `openrouter_guardrail_budget`, `openrouter_workspace_budget` or `openrouter_key_limit`. A 403 without a `limit_source` (for example a moderation refusal) is not a limit.
- 429 is a rate limit (`error_type` `rate_limit_exceeded`), not a credit limit. It is a limit stop only if its body names a `limit_source`.

The 402 and 403 limit refusals come before a provider is called, so they carry no `usage.cost`. The stopped game's `cost_complete` is then false and `spend_complete` false: the recorded spend is a floor.

## 3. Checks

New: `apps/poc/tests/test_d37_guards.py` (11 tests). Changed: three `main()` tests in `apps/poc/tests/test_model_runs.py` now give a placeholder key in the environment and a fake key opener.

| Item | Tests |
|---|---|
| 1 | `test_a_call_landing_exactly_on_the_cap_is_allowed_and_one_cent_over_is_refused` (13.99 + 0.01 allowed, 13.99 + 0.02 refused, spend at the cap refused); `test_the_exact_cap_call_is_sent_and_the_cent_over_call_is_never_sent` (a Pegasus game: the second call is sent at $0.01 reserve, never sent at $0.02) |
| 2 | `test_key_limit_check_accepts_only_a_key_limited_to_the_cap` (null limit, limit above the cap, remaining below it, free tier, non-numeric and boolean amounts); `test_key_info_call_is_a_get_with_the_key_and_fails_closed` (GET, URL, bearer header; HTTP 500, 401, 403, URLError, timeout, bad JSON, no `data`); `test_main_refuses_to_start_when_the_key_check_fails_and_records_a_passing_check_without_the_key` (no directory on refusal; the passing check in the manifest, no key and no `label` in any batch file) |
| 3 | `test_a_key_only_in_env_local_is_refused` (a key only in a dotenv file that `Settings.load()` would read is refused, for the generic and the paid plan); `test_missing_empty_or_rejected_key_refuses_to_start` (missing, blank, 401, 403; `run_batch` without a key or a key check) |
| 4 | `test_paid_plan_pins_sonnet_in_body_price_and_manifest_and_refuses_overrides` (every fixed flag refused; every request body's `model` is Sonnet 5.5 with 4,000 tokens and effort high, even with `OPENROUTER_MODEL` set; manifest model, prices, cap, plan of 12); `test_dry_run_prints_the_plan_and_a_fake_key_check_with_no_key_or_network` |
| 5 | `test_a_provider_credit_refusal_stops_the_batch_and_keeps_the_partial_game` (402 with and without a source, 403 guardrail budget, in-body 402: three bodies sent and no fourth, `.stopped.sqlite` kept with two model decisions and no fallback, exit 5, reason and spend in runs, summary and manifest, game 2 not started); `test_other_refusals_fail_the_game_as_before` (403 moderation, 429 rate limit: exit 4) |
| 6 | The 15 tests of `apps/poc/tests/test_model_runs.py` (per-call reservation, cap exit 3, interrupt, abort on fallback, stopped and failed records) all pass |

These go through the real adapter (`OpenRouterProvider` and `fetch_key_info`) with fake openers that never reach a network; the item 1 batch test uses a fake provider.

**Red first** (`red/`), on the pre-change sources (`44babae`) with the new tests:

| Item | Reverted | Result |
|---|---|---|
| 1 | `spend.py`, `model_runs.py` | both tests fail: `BudgetExhausted: cap $14.0000 - spent $13.9900 < reserve $0.0100`, and 1 call sent where 2 are expected |
| 2 | `model_runs.py` | the `main` test fails (`main()` takes no `environ`, no key check); the two unit tests pass, as their functions are new; with `adapters/openrouter.py` reverted the module does not import (`KEY_INFO_URL`) |
| 3 | `model_runs.py`, `config.py` | the `.env.local` test fails, "SystemExit not raised": the old driver ran on the dotenv key |
| 4 | `model_runs.py` | both fail: no `--paid-plan`, no dry run |
| 5 | `services/commander.py` | the stop test fails 4 of 4 cases, exit 4 where 5 is expected; the "other refusals" test passes, as it pins kept behaviour (mutation m5 shows the stop test can fail) |

**Each guard can fail** (`mutations/`, one change each, restored after): 6 of 6 turn their tests red.

| Mutation | Change | Red |
|---|---|---|
| m1 | the cap check `>` becomes `>=` | both item 1 tests |
| m2 | the `limit <= cap` check removed | the check table (limit above the cap) and the `main` test (a $20 key starts the batch) |
| m3 | `environment_settings` reads `Settings.load()` (with `.env.local`) | the `.env.local` test |
| m4a | the paid plan's model replaced by Opus 5.5 | the body, manifest and dry-run assertions |
| m4b | the flag refusal removed | the override test, "SystemExit not raised" |
| m5 | the `provider_limit` branch in `play` removed | the stop test, 4 of 4 cases |

## 4. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/d37-guards-8bbb87c/` in the main checkout. `MANIFEST.txt` lists every file and each gate's exit code. Each log starts with its command and ends with `EXIT=`.

| Gate | Result |
|---|---|
| `make test-poc` | `Ran 791 tests … OK` (765 at `65775a1`, plus the branch's 15 and the 11 above), then `smoke_ui.mjs`, map geometry, map features, route and sight; exit 0 |
| `make headless-poc` | Little Round Top: winner union, 60 turns, 2,573 events, the same unit strengths, replay `identical` (63 revisions), as at `65775a1` (`headless-poc-main.log`) |
| `make smoke-poc` | exit 0 |
| `npm ci --offline`, `npm run typecheck`, `npm test` | not run: nothing under `packages/` or `apps/web` changed |
| dry run | `python3 scripts/model_runs.py --paid-plan d37-option-a --dry-run`, exit 0 (`dry-run.log`) |

**Digest comparison against `65775a1`** (`digests.py`, on a `git archive` export of `65775a1` and the head tree): a scripted headless run of every headless catalog entry and every named variant of Concord, Pegasus (with its range and crossed sensitivities), Hill 223 and Gergovia, the sha256 of the result without `game_id` and the final state. 59 of 59 digests are identical (`digests-compare.log`, `digests-main.log`, `digests-head.log`). The head run used the tree at `c60e3f1`, whose `apps/poc/battle` is the same as `8bbb87c` (`diff-battle-since-digest-run.log` is empty); `digests.py` imports only `battle`. The guards change no scripted play.

A first `make test-poc` run, made while both digest runs loaded the machine, failed one wall-clock test, `test_degenerate_reply_under_cap_stays_fast` (0.27 s against a 0.25 s bound, in reply parsing that this change does not touch). The recorded run was made after the digest runs ended (`test-poc-under-load.log` keeps the first).

## 5. The paid run (not run)

Run from `apps/poc` in the main checkout, on a clean tree at the commit to be pinned, with the D37 key (`secret://battle/OPENROUTER_API_KEY_D37`) injected as `OPENROUTER_API_KEY` into this process only:

```
tm secrets exec --env OPENROUTER_API_KEY=OPENROUTER_API_KEY_D37 -- python3 scripts/model_runs.py --paid-plan d37-option-a --dir artifacts/d37-option-a-<commit>
```

First, the same command with `--dry-run` in place of `--dir …` and no `tm secrets exec` prints the plan and checks nothing real. Play order: Little Round Top 1, Hougoumont 1, Concord 3, Pegasus 3, Gergovia 2, Hill 223 2 (doc 69 §5, cheap entries first). The batch then:

1. refuses a dirty tree, a missing or empty key, and any fixed flag;
2. calls `GET /api/v1/key` once and refuses unless the key shows a limit of at most $14 with at least $14 remaining, not free tier;
3. plays the 12 games under the $14 cap, stopping before any call whose reserve would pass it (exit 3), at the first fallback or unreadable cost (exit 4), or at an OpenRouter credit refusal (exit 5).

`tm secrets exec` scrubs injected values from captured output; its grant lasts at most 3,600 s, but the variable stays in the batch's environment for the whole run. Any process of the same user can read that environment while the batch runs.

## 6. Deviations and open points

- **Generic path.** Without `--paid-plan`, `model_runs.py` still takes `--plan`, `--model`, `--games` and `--cap-usd` for other approved batches (doc 69 stage 1, option B). It has the same key, key-limit, cap and provider-limit guards, but not the model pin. With the D37 key, its key check passes only with `--cap-usd 14`, because the key's limit must not exceed the cap and its remaining credit must cover it.
- **The generic path no longer reads `.env.local`.** Doc 69 §9 said the driver loaded `Settings.load()` (environment, then `.env.local`). Item 3 requires the environment only, so a generic batch now also needs the key in its environment. The desk and `python3 -m battle` are unchanged.
- **`limit_reset`.** A key whose limit resets (daily, weekly, monthly) passes the check; the reset is recorded. A reset during the batch could re-arm the key, but the $14 cap still bounds the batch.
- **Base.** The brief named `65775a1`. `main` moved to `b5a8c9f` (#18, doc 77) during the task; that commit touches Cannae files, docs 68 and 77 and the README index. A test merge of this branch onto it (`merge-tree-onto-b5a8c9f.log`) conflicts only in the `docs/research/README.md` index, where doc 77's entry and this doc's both end the file; the resolution keeps both, 77 then 78. The code merges cleanly.

## 7. Review notes

Pending review.
