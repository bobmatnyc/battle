# 78 — D37 guards on the paid model batch

**Date:** 2026-11-08. **Task:** bt-T13. **Rulings:** D37 (Bob): option A of [69](69-model-run-cost-estimate.md) §5, Sonnet 5.5, 12 games, a $14 cap (planning $10.65, worst case $30.15), on a new OpenRouter key limited to $14. Architect key decision: battle project scope, secret `OPENROUTER_API_KEY_D37`, injected as `OPENROUTER_API_KEY` into the batch process only. Architect acceptance (14:45Z): items 1 to 7 below. Code head `a0fdc84`, base `b5a8c9f`. Draft PR #14's branch was rebased onto `65775a1` (code head `8bbb87c`), then, after the review round of section 3a, onto `b5a8c9f`. No model API was called, no key was read and nothing was spent.

**B62 (bt-T21):** Bob's ruling B62 ("use the current key") replaces the key-limit rule of item 2 and the key named in §5; see §8.

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

**Exit codes.** 0: every planned game finished as a model game within the cap. 2: refused before start (dirty tree, no named plan, a price override, key, key limit, flags). 3: the cap (a budget stop, or spend at the cap). 4: a failed game (fallback, missing cost, replay mismatch, interrupt). 5: an OpenRouter credit or budget refusal.

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
| 2 | `test_key_limit_check_accepts_only_a_key_limited_to_the_cap` (renamed by B62, §8; null limit, limit above the cap, remaining below it, free tier, non-numeric and boolean amounts); `test_key_info_call_is_a_get_with_the_key_and_fails_closed` (GET, URL, bearer header; HTTP 500, 401, 403, URLError, timeout, bad JSON, no `data`); `test_main_refuses_to_start_when_the_key_check_fails_and_records_a_passing_check_without_the_key` (no directory on refusal; the passing check in the manifest, no key and no `label` in any batch file) |
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

## 3a. Review round (code-critic WARN on `998063c`)

| Item | Change | Files |
|---|---|---|
| A (HIGH) | `--input-price` and `--output-price` are refused for a model listed in `battle.spend.PRICES`, so an override can no longer lower the reserve below the real price. `Price` refuses a rate of 0 or below. `--model anthropic/claude-sonnet-5.5 --cap-usd 14 --input-price 0 --output-price 0` exits 2 before any provider call | `apps/poc/scripts/model_runs.py` (`price_for`), `apps/poc/battle/spend.py` (`Price`) |
| B (MEDIUM, PM decision) | A run that would spend needs a named plan in `PAID_PLANS`. Without `--paid-plan`, `main` refuses a real run before the key-info call. `run_batch` refuses the OpenRouter adapter unless `paid_plan` names a plan whose model and cap the batch has. Dry runs and tests with fake providers keep the generic path | `apps/poc/scripts/model_runs.py` (`main`, `run_batch`) |
| C (MEDIUM) | `key_limit_check` refuses a key whose `limit_reset` is not None (daily, weekly, monthly or an unrecognised value): a reset would re-arm the key during the batch | `apps/poc/battle/paid_batch.py` |
| D (LOW) | The key is sent with `Request.add_unredirected_header("Authorization", …)` on the key-info and chat-completions requests, so urllib does not copy it to a redirect target | `apps/poc/battle/adapters/openrouter.py` |

Test fixtures that priced a side at $0 now use small positive rates (`FREE` is `Price(1e-9, 1e-9, 1)`); the exact-cap tests build reserves of exactly $0.01 and $0.02 from 1,024 overhead tokens at $0.0009765625 per million plus 9,999 or 19,999 output tokens at $1 per million.

| Item | Test | Red first on `998063c` | Mutation |
|---|---|---|---|
| A | `test_price_overrides_cannot_lower_a_listed_price_and_no_rate_is_zero` | the zero-price, $0.001 and list-price overrides reach the provider ("this opener or provider must not be called"); `Price(0.0, 10.0, 1)` and `Price(2.0, 0.0, 1)` raise nothing | mA1: the override refusal removed, red; mA2: `r <= 0` back to `r < 0`, red |
| B | `test_a_real_run_needs_a_named_plan` | the generic real run is not refused for a missing plan ("'named plan' not found") | mB1: the `main` refusal removed, red; mB2: the `run_batch` refusal removed, red |
| C | `test_key_limit_check_accepts_only_a_key_limited_to_the_cap` (cases: resets monthly, daily, unrecognised) | 3 cases fail, "True is not false" | mC: the reset refusal removed, red |
| D | `test_the_key_header_is_not_copied_on_redirect` | both requests carry the key in redirected headers ("None != 'Bearer …'") | mD1: key-info `add_unredirected_header` back to `headers=`, red; mD2: chat-completions `add_header`, red. The recorded mD2 log shows mD1's failure (stale bytecode: both mutated copies had the same size and mtime second); a re-run with `python3 -B` in a clean copy fails on the chat-completions subtest, so the test catches mD2 |

## 4. Gates, digests and evidence

Round 2, on the rebased head: all under the git-ignored `apps/poc/artifacts/d37-guards-a0fdc84/` in the main checkout (red first on `998063c`, mutations, gates, digests, dry run). Round 1 (`8bbb87c` on `65775a1`): `apps/poc/artifacts/d37-guards-8bbb87c/` (red first on `44babae` and mutations for items 1 to 5, as in section 3). `MANIFEST.txt` lists every file and each log's exit code. Each log starts with its command and ends with `EXIT=`. The gates ran one at a time.

| Gate | Result |
|---|---|
| `make test-poc` | `Ran 795 tests … OK` (766 at `b5a8c9f`, plus the branch's 15 in `test_model_runs.py` and 14 in `test_d37_guards.py`), then `smoke_ui.mjs`, map geometry, map features, route and sight; exit 0 |
| `make headless-poc` | Little Round Top: winner union, 60 turns, 2,573 events, the same unit strengths, replay `identical` (63 revisions), as at `b5a8c9f` (`headless-poc-main.log`) |
| `make smoke-poc` | exit 0 |
| `npm ci --offline`, `npm run typecheck`, `npm test` | not run: nothing under `packages/` or `apps/web` changed |
| dry run | `python3 scripts/model_runs.py --paid-plan d37-option-a --dry-run`, exit 0 (`dry-run.log`) |

**Digest comparison against `b5a8c9f`** (`digests.py`, on a `git archive` export of `b5a8c9f` and the head tree): a scripted headless run of every headless catalog entry and every named variant of Concord, Pegasus (with its range and crossed sensitivities), Hill 223 and Gergovia, the sha256 of the result without `game_id` and the final state. 59 of 59 digests are identical (`digests-compare.log`, `digests-main.log`, `digests-head.log`; the head run is six shards, `digests-head-shard0.log` to `shard5.log`). The guards change no scripted play.

In round 1 a `make test-poc` run made while two digest runs loaded the machine failed one wall-clock test, `test_degenerate_reply_under_cap_stays_fast` (0.27 s against 0.25 s, in reply parsing this change does not touch); see section 7.

## 5. The paid run (not run)

B62 replaces the key and the key check below; §8 has the current command.

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

- **Generic path (PM decision, review item B).** A run that would spend needs a named plan in `PAID_PLANS`; only `d37-option-a` exists. Without `--paid-plan`, `model_runs.py` accepts `--plan`, `--model`, `--games` and `--cap-usd` only for `--dry-run` and for tests with fake providers. Another batch (doc 69 stage 1, option B) needs its plan approved and added to `PAID_PLANS` first.
- **The generic path no longer reads `.env.local`.** Doc 69 §9 said the driver loaded `Settings.load()` (environment, then `.env.local`). Item 3 requires the environment only, so a generic batch now also needs the key in its environment. The desk and `python3 -m battle` are unchanged.
- **`limit_reset`.** A key whose limit resets (daily, weekly, monthly, or an unrecognised value) is refused (review item C). The D37 key must be created with a limit that never resets.
- **Base.** Round 1 was on `65775a1`, as the brief named. `main` moved to `b5a8c9f` (#18, doc 77) during that round; round 2 rebased onto it. The only conflict was the `docs/research/README.md` index, where docs 77 and 78 both ended the file; the resolution keeps 77, then 78.

## 7. Review notes

**Round 1, code-critic on `998063c`: WARN.**

| Severity | Finding | Disposition |
|---|---|---|
| HIGH | Generic-path price overrides could set a $0 reserve and allow a one-call overshoot past $14 | fixed in round 2, item A |
| MEDIUM | The generic path could spend the D37 key on any model | fixed, item B: a real run needs a named plan |
| MEDIUM | The key-limit check accepted a resetting limit | fixed, item C |
| MEDIUM | A crash outside `runner.run()` (`build_headless`, repository load, rename, sha256, the `runs.jsonl` write) leaves no `runs.jsonl` line, summary or manifest `closed` block, and the DB stays `.partial.sqlite`. Spend stops, so no money is at risk | recorded, not fixed |
| LOW | `CommanderService.chat` calls the provider without `before_request`; the batch cannot reach it | recorded |
| LOW | The returned decision model is recorded but not compared with the pinned model | recorded |
| LOW | The Authorization header was copied on redirect | fixed, item D |

Notes:

1. Only `CommanderService.decide` reaches the provider in a batch, with `before_request` on the same instruction and payload. There is no adapter retry, repair or second request, and `BudgetExhausted` is re-raised before the generic except.
2. The reserve is an upper bound: input counted as UTF-8 bytes of the exact request body, 1,024 authored overhead tokens, output charged at the full `max_tokens` of 4,000.
3. The $2/$10 Sonnet 5.5 rate is backed by a stored bill (doc 69 §3).
4. The reserve is 2 to 3 times more conservative than doc 69's $30.15 worst case (450 output tokens per call there). A batch can stop with up to one reserve (about $0.20) unspent below $14.
5. The cap path is Decimal throughout; floats appear only in reporting.
6. Fail-open check: every key-info, cost, provider, 200-with-error-body, interrupt and fallback branch fails closed. The only gap is the crash-record MEDIUM.
7. Provider-limit detection: 402, or 403/429 with a listed `limit_source`, gives exit 5 and keeps `.stopped.sqlite`. Any other limit-like response falls back and stops with exit 4. The `limit_source` names are not checked against OpenRouter's docs (needs network).
8. No key or `label` is written anywhere; `Settings.api_key` has `repr=False`.
9. The paid plan reads only the key from the environment. A stale shell key is still stopped by the key-limit check unless it is also a $14 key with $14 left.
10. The section 5 `tm secrets exec --env …` command matches the `tm` CLI source (exec: `--env NAME=KEY`, command after `--`). A key that does not resolve runs nothing and exits 1. Output is scrubbed only when stdout is not a terminal.
11. The flaky wall-clock test `test_degenerate_reply_under_cap_stays_fast` (`test_openrouter_adapter.py:235-240`, 0.25 s bound) predates this branch; fix it separately.
12. A successful call with no `usage.cost` raises `CostUnreadable` before the decision is committed, so that decision's record is lost. A 402/403 limit stop reports `spend_complete: false`.
13. Evidence checked: red-first items 1 to 5 fail, 6 of 6 mutations red, `test-poc` OK.

**Round 2 (delta), code-critic on `a0fdc84`: APPROVE.** A, B, C and D hold. No remaining path spends past $14, uses the wrong key or model, or leaks the key. The rebase changed no guard code (`git range-diff` all `=`). The fixture changes (CENT and TWO_CENTS exact reserves; `request_size` patched to 0 only in the exact-cap test) do not weaken the tests. Every new error branch exits 2 before any directory, key-info or provider call.

Notes:

1. The mD2 log issue in section 3a; run mutations with `python3 -B` or `PYTHONDONTWRITEBYTECODE=1`.
2. `run_batch` checks only the named plan's model and cap, not its items, games, effort, `max_tokens` or timeout. Only `main` sets those from the plan, so the CLI cannot reach the gap, and the cap and key limit still bound spend.
3. `battle/bootstrap.py` and `battle/inference.py` still call `Settings.load()` (reads `.env.local`); they are outside the batch path.

**Disposition.** Nothing blocks after round 2 (Completion Standard fix bar). Recorded, not scheduled: the crash-record gap, `chat`'s missing `before_request`, the returned-model check, the flaky timing test, `run_batch`'s partial plan check.

## 8. B62: the current key, with no credit limit (bt-T21)

**Ruling.** B62 (Bob): "use the current key". No new key limited to $14 is made. The Architect cleared bt-T21 under it. Base `ae339fc`. No model API was called, no key was read and nothing was spent.

**Rule change** (`apps/poc/battle/paid_batch.py`, `key_limit_check`):

- A key whose `limit` and `limit_remaining` are both present and null is unlimited. It passes, and the `key_check` record in `manifest.json` carries `unlimited: true` (never the key, never `label`).
- Any other key needs both amounts as numbers and `limit_remaining` >= the cap. The `limit` > cap refusal is gone: a limited key may have a limit above $14.
- Still refused: `limit_reset` not null; `is_free_tier` true or not a boolean; a non-numeric amount; only one of `limit` and `limit_remaining` null; either field absent (absent is not null); a reply missing `is_free_tier` or `limit_reset`, unlimited or not (review round 1); any key-info call error (fail closed, exit 2 before any file is written).

**What bounds the $14 now.** The key no longer backstops the cap. Three controls do:

1. The reservation (`battle.spend.SpendGuard`): before every call, spend so far plus one worst-case call (the full request body, 1,024 overhead tokens and 4,000 output tokens, at $2 and $10 per million) must not pass $14. For a Pegasus call that reserve is $0.078 to $0.085.
2. Cost reconciliation: each call's `usage.cost` is charged after it returns; a call with no readable cost fails the game (exit 4).
3. The provider-limit stop: an OpenRouter credit or budget refusal (402, or a 403 or 429 naming a limit source) stops the batch with exit 5.

**Known limits.**

- The guard starts at $0 in each process and does not read the key's earlier `usage`. Two runs on the same key each get their own $14. The manifest's `key_check.usage` records the key's spend at start, so a reviewer can add it up.
- A call that times out returns no usage. The batch stops (the decision falls back, exit 4), but OpenRouter may still bill that call. Its cost is not in the recorded spend (`spend_complete: false`). Its reserve was checked against the cap before the call, so the real total stays within $14 as long as the reserve bounds the bill.
- The dry run's fake opener still answers as a key limited to the cap (`unlimited: false`); it does not model the current key.

**The paid command.** From `apps/poc` in the main checkout, on a clean tree at the commit to be pinned, with the vault secret `OPENROUTER_API_KEY_BATTLE` injected as `OPENROUTER_API_KEY` into this process only:

```
tm secrets exec --env OPENROUTER_API_KEY=OPENROUTER_API_KEY_BATTLE -- python3 scripts/model_runs.py --paid-plan d37-option-a --dir artifacts/d37-option-a-<commit>
```

**Tests** (`apps/poc/tests/test_d37_guards.py`):

| Test | Proves |
|---|---|
| `test_key_limit_check_accepts_an_unlimited_key_or_one_with_the_cap_remaining` (renamed from `…_accepts_only_a_key_limited_to_the_cap`) | both null passes with `unlimited: true`; limits of $14.01, $20 and $500 pass with the cap remaining; one null, absent fields, remaining below the cap, free tier, reset and non-numeric amounts refuse |
| `test_main_refuses_to_start_when_the_key_check_fails_and_records_a_passing_check_without_the_key` (changed) | the $20 case left the refusal list; `limit_remaining` null and a monthly reset joined it |
| `test_the_call_whose_real_sonnet_reserve_would_pass_the_cap_is_never_sent` | a Pegasus batch at the real Sonnet 5.5 plan settings and the adapter's real body size (18,092 and 21,260 bytes): with $14 minus the second call's reserve ($0.084568, worked by hand from the basis) spent first, the second call is sent and spend lands on $14.00; with $0.000001 more, it is never sent, exit 3, spend <= $14 |
| `test_a_402_through_main_stops_the_paid_batch_with_exit_5_and_closes_the_manifest` | `main --paid-plan d37-option-a` over a fake chat opener that refuses the third call with 402: exit 5, `little-round-top-1.stopped.sqlite` kept, manifest `closed` with status `provider_limit`, exit 5, the reason, $0.02 spent, 11 games not started |
| `test_a_key_with_no_limit_passes_through_main_and_the_manifest_says_unlimited` | `main` with a fake key-info opener answering both null: the batch runs (exit 0), `key_check` has `ok` and `unlimited` true and the key's usage, and no batch file holds the key or `label` |

**Red first** (commit `278732e`, tests only, on `ae339fc` code): the check table and the null-limit `main` test fail (`KeyError: 'unlimited'`; `PaidRunRefused: key-limit check failed: the key has no credit limit`). The exact-cap and exit-5 tests pass there: they pin behaviour B62 keeps, and mutations m1 and m6 show they can fail.

**Mutations** (`python3 -B`, one at a time, restored from `HEAD` after each): 6 of 6 red.

| Mutation | Change | Red |
|---|---|---|
| m1 | the reserve's output term priced at 0 tokens instead of `max_tokens` | the real-rate exact-cap test: the second call is sent, "2 != 1" |
| m2 | the free-tier refusal removed | the check table (free tier, unlimited but free tier) and the `main` refusal test |
| m3 | one null field accepted as unlimited | the check table (both one-null cases, absent `limit_remaining`) and the `main` refusal test |
| m4 | an absent field counted as null | the check table (absent fields, `{}`, non-dict data) |
| m5 | `unlimited` always recorded false | the null-limit `main` test |
| m6 | the `provider_limit` stop in `run_batch` removed | the exit-5 `main` test, "3 != 5" |

**Gates** (on `2834a8a`): `make test-poc` exit 0 (`Ran 811 tests … OK`, then the UI smoke and the map, feature, route and sight checks); `make headless-poc` exit 0 (Little Round Top: union, 60 turns, 2,573 events, replay `identical`, 63 revisions); `make smoke-poc` exit 0; the dry run `python3 scripts/model_runs.py --paid-plan d37-option-a --dry-run --dir <tmp>` with no key in the environment exit 0, Sonnet 5.5, $14 cap, 12 games, the fake key check `ok`, nothing written. The diff touches no rules, engine or scenario file, so engine outcomes and digests are unchanged.

## Review notes (B62)

pending PM
