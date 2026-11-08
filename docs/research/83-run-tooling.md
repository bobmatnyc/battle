# 83 — Run tooling: `make headless-poc SCENARIO=<id>` and the Cannae share-run columns

**Date:** 2026-11-08. **Task:** bt-T22. **Base:** main `56143f2`. **Branch:** `bt-t22-run-tooling`.

Tooling for model-against-control runs. No engine, rules or scenario file changed. No model, no spend, no EVO run.

## 1. What changed

| File | Change |
|---|---|
| `Makefile` | `headless-poc` passes `--scenario '$(SCENARIO)'` when `SCENARIO` is set and not empty. Unset or empty, the recipe text is byte for byte the `56143f2` recipe. |
| `apps/poc/scripts/cannae_runs.py` | `share_runs(victory)` and `breakthroughs(victory)`; every row gains `share_intervals`, `longest_share_run` and `breakthroughs`. |
| `apps/poc/tests/test_run_tooling.py` | new: 3 make-target tests, 3 column tests. |
| `apps/poc/tests/test_cannae.py` | the short-run row also asserts the three new columns. |
| `README.md` | one line for `make headless-poc SCENARIO=<id>`. |

`apps/poc/battle/__main__.py` is unchanged. The CLI already takes `--scenario`, resolves it against the headless catalog and, on an unknown id, exits 2 with the list of valid ids. The target only had to pass the variable through.

**`make headless-poc SCENARIO=<id>`.** Any id in the headless catalog runs: `little-round-top`, `hougoumont-north-gate`, `concord-north-bridge`, `concord-north-bridge-v1`, `pegasus-bridge`, `hill-223-patrol`, `gergovia-recall`, `cannae-envelopment`. The output has the same shape as before: the `Headless artifacts:` line, then the runner's summary. The Cannae variants are not catalog entries. They stay with `scripts/cannae_runs.py --only <name>`.

**The new columns.** They read only the stored victory record, so they work for every edition.

- `share_intervals`: the number of `record` rows whose enclosed men plus lost men reach `enclosed_needed`. This is the quantity the deadline test and D38 Q1 read.
- `longest_share_run`: the longest run of such rows on consecutive turns. A missing turn ends a run, as in `victory_encircle._sustained`.
- `breakthroughs`: `[unit, first interval]` from D38 Q3's `broke_through`, ordered by interval and then by unit id. The value is `[]` under `cannae-d38` with no breakthrough, and `null` for an old-edition record, which has no `broke_through`.

These replace doc 82 §7's one-line `sqlite3` read of the stored state. The script already printed the raw `broke_through` map with men; that field is unchanged.

## 2. Sample output

**Default under `cannae-d38`** (`python3 -B scripts/cannae_runs.py --only default`, on the Mac; 160.2 s, max RSS 1.57 GB, exit 0). The new and key fields of the row:

```json
{"run": "default", "entry": "cannae-envelopment", "edition": "cannae-d38", "winner": "roman", "turn": 160, "replay": "identical", "peak_enclosed": {"men": 6901, "turn": 32, "units": 2}, "share_intervals": 0, "longest_share_run": 0, "breakthroughs": [["L1", 33], ["L2", 36], ["L5", 39], ["L6", 41], ["L8", 42], ["A1", 46], ["L7", 46], ["L3", 48], ["L4", 67]], "events": 63124}
```

This matches doc 82 §9's Q1 (`5689adb`) row in every field the row shares: roman at 160, peak 6,901@32, share 0 / 0, the nine breakthroughs in the same order, 63,124 events.

**Default under the old edition** (`cannae_entry(edition=None)` through `cannae_runs.run`, a scratch driver; exit 0):

```json
{"run": "old-default", "entry": "cannae-envelopment", "edition": null, "winner": "roman", "turn": 160, "replay": "identical", "peak_enclosed": {"turn": 53, "units": 14, "men": 44616}, "share_intervals": 53, "longest_share_run": 51, "breakthroughs": null, "events": 63124}
```

This matches doc 82 §6's base row (`d4e3ac7`): 53 intervals at the share, longest run 51 (43 to 93), peak 44,616@53 (14 units).

**`make headless-poc SCENARIO=pegasus-bridge`** (summary cut after `replay`):

```text
Headless artifacts: /var/folders/…/battle-headless.v8M0kp
{'game_id': 'd78318f9d6b3436c', 'winner': 'german', 'turns': 5, 'events': 306, 'strength': {…}, 'replay': {'revisions': 7, 'turns': 5, 'status': 'identical'}, 'run': {…, 'scenario_id': 'pegasus-bridge', …}}
```

**`make headless-poc SCENARIO=nope`** exits 2. The last lines of stderr:

```text
python3.14 -m battle: error: Unknown scenario 'nope'. Known scenarios: little-round-top, hougoumont-north-gate, concord-north-bridge, concord-north-bridge-v1, pegasus-bridge, hill-223-patrol, gergovia-recall, cannae-envelopment.
make: *** [headless-poc] Error 2
```

## 3. Gates

Run in the worktree, in the foreground, each with its own exit code.

| Gate | Result |
|---|---|
| `make test-poc` | `Ran 817 tests in 262.646s`, `OK`, then the four JavaScript checks pass; exit 0 |
| `make headless-poc` | exit 0: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions) |
| `make headless-poc SCENARIO=pegasus-bridge` | exit 0: winner german, 5 turns, replay `identical` |
| `make headless-poc SCENARIO=hill-223-patrol` | exit 0: winner american, 27 turns, replay `identical` |
| `make headless-poc SCENARIO=nope` | exit 2, names the eight valid ids |
| `make smoke-poc` | exit 0 |

The Pegasus and Hill 223 results are the #23 pins (bt-T17).

**No SCENARIO is unchanged.** `make -n headless-poc` prints the same recipe under the base Makefile and under this one (`cmp` exit 0). The default run's output equals a `56143f2` run once the temporary directory name and the random `game_id` are masked (`cmp` exit 0).

**Red first.** Commit `f2c2b81` holds the tests alone. Against that tree 7 tests ran: 1 failure and 6 errors. `share_runs` and `breakthroughs` did not exist, the rows had no `share_intervals` or `breakthroughs`, the named-scenario runs printed Little Round Top's summary (no `run` key), and `SCENARIO=nope` exited 0. The recipe test passed at the base, as it should: it pins the base recipe.

**Mutations** (`python3 -B`, one change at a time, the bt-T22 tests run, the file restored):

| Item | Mutation | Red tests |
|---|---|---|
| 1 | `SCENARIO` not passed on | the named-scenario test (both subtests), the unknown-id test |
| 1 | the no-SCENARIO recipe gains a trailing space | the recipe test (both subtests) |
| 2 | the share ignores lost men | `test_share_runs_count_the_intervals_at_the_share_and_the_longest_consecutive_run` |
| 2 | the longest run ignores a missing turn | the same test |
| 2 | breakthroughs sorted by unit only | `test_breakthroughs_list_unit_and_first_interval_when_the_edition_records_them` |
| 2 | the three columns dropped from the row | the old-edition run test and `test_a_short_headless_run_replays_identically_and_summarises` |

**Digests against `56143f2`.** Doc 74's `digests.py` and doc 76's `run_digests.sh`, copied unchanged from `fords-labels-29cfd3e`, ran on `git archive` exports of `56143f2` and `b1103fd`: every headless catalog entry (timings dropped) and desk play of the five player scenarios to the end. Both comparisons are identical: `cmp desk EXIT=0` and `cmp catalog without timings EXIT=0` (8 catalog lines, 5 desk lines). `apps/poc/battle` is identical between the two exports (`diff -r` exit 0).

Evidence is git-ignored under `apps/poc/artifacts/run-tooling-bt22/` in the task worktree: `red.log`, `mutations.log`, `mutate.py`, `test-poc.log`, `smoke-poc.log`, the `make` outputs, `default.jsonl`, `old-default.json`, `run-digests.log` and `digests/`.

## Review notes

pending PM
