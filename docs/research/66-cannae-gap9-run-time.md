# Cannae gap 9: run time at 6 to 82 units

Date: 2026-11-07. **Requirement:** [doc 63](63-cannae-scenario-plan.md) §10 gap 9 asks for a 160-interval run with 41 units before any feature work, because the sighting loops visit every unit (`recon.py`) and nothing over about 20 units had been run. This document records that measurement, with the counts 60 and 82 added as headroom. It is a measurement only: no engine, rule or authored value changed.

## Corrections to earlier summaries

1. **The 0.54 s (41 units) and 1.17 s (82 units) figures are first-60-interval means**, not whole-run figures. The JSON field `mean_s` averages the first `window_intervals` (60) intervals. The whole-run average is `run_s / intervals_run`: 1.279 s at 41 units and 2.970 s at 82. The quoted "about 1.28 s and 2.97 s" match the JSON to three digits. Both windows are reported for every count below.
2. **"recon.py under 1%" was self time only** (0.64% at 41 units, 0.75% at 82). The cumulative cost of the sighting code is 4.2% to 5.1% of profiled time (see Profile). The line-of-sight and recon total is the cumulative figure.
3. **The host was shared.** Other sessions' jobs ran on EVO throughout. Timings are an upper estimate (see Host load).

## Method

- **Bench:** `apps/poc/scripts/unit_count_bench.py`, with its test `apps/poc/tests/test_unit_count_bench.py`. It is a synthetic two-line battle, not a scenario.
- **Engine as it is today:** 50 m hexes, 30 s intervals, the 24 by 21 grid, ruleset `poc-13`. This is today's scale, not doc 63's option A (200 m, 180 s), which needs gap 1.
- **Layout:** flat open ground, two facing lines 4 hexes apart on columns 1 to 22, at most 4 ranks a side. Units use Gergovia's weapon classes (shock, range 1; every third unit missile, range 3), the Roman communications profile, voice reach 1 and `tactics_v11`. Fire, recon and pathing run from the first interval.
- **Run:** 160 intervals unless a side breaks first (none did; Blue held to the deadline in every count). Each count runs in its own child process (clean peak RSS) through `HeadlessRunner` with `BatchStore`, the path a real headless run takes. A closing replay check re-runs every interval.
- **Measures per count:**
  - *Window*: mean, p95 and max wall time of the first 60 intervals.
  - *Full run*: `run_s / 160`, without the replay check. With the check: `run_with_replay_check_s / 160`.
  - Peak RSS, and a SHA-256 digest of the final snapshot. The engine draws no random number, so the digest is deterministic; timings are not.
- **Profile:** one extra child per bench file runs one count for 60 intervals under cProfile, including the replay check. cProfile inflates absolute times, so only the shares are used.

## Results

Seconds per interval. Window = first 60 intervals. Every replay check ended `identical`.

| Units | Window mean | Window p95 | Window max | Full run, no replay | Full run, with replay | Run total | Run + replay total | Replay check alone | Peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| 6 | 0.032 | 0.055 | 0.077 | 0.082 | 0.138 | 13.2 s | 22.1 s | 8.9 s | 82 MB |
| 12 | 0.067 | 0.134 | 0.207 | 0.172 | 0.359 | 27.5 s | 57.4 s | 29.9 s | 137 MB |
| 24 | 0.195 | 0.313 | 0.551 | 0.484 | 1.008 | 77.4 s | 161.2 s | 83.8 s | 294 MB |
| **41** | 0.542 | 1.026 | 1.436 | **1.279** | 2.286 | 204.7 s | 365.7 s | 161.0 s | 485 MB |
| 60 | 1.004 | 2.188 | 2.527 | 1.816 | 3.460 | 290.6 s | 553.6 s | 262.9 s | 730 MB |
| 82 | 1.169 | 2.798 | 3.151 | **2.970** | 6.837 | 475.2 s | 1093.9 s | 618.7 s | 1009 MB |

Derived columns: full run is `run_s / 160`; with replay is `run_with_replay_check_s / 160`; replay check alone is the difference of the two totals. The full-run average is 1.8 to 2.6 times the window mean at every count, so later intervals cost more than the first 60. The profile does not cover intervals 61 to 160, so the cause is not measured.

End state per count (digest first 8 hex, events, final strength Blue/Red): 6 `b787e423`, 9965, 109/108; 12 `a687a5ab`, 21743, 218/228; 24 `033b1bf6`, 49542, 436/443; 41 `f7ecc651`, 81799, 723/792; 60 `1fcbda98`, 126884, 1091/1102; 82 `d3c99e60`, 175267, 1559/1550. Full digests are in the JSON files.

## Profile

Shares of profiled time (cumulative, 60 intervals plus replay check). Cumulative figures nest, so they do not add up.

| Function | 41 units | 82 units |
|---|---|---|
| Profiled time | 143.6 s | 422.8 s |
| `runtime.apply` | 87.1% | 87.6% |
| `headless.commit` | 50.5% | 55.6% |
| **Replay verify** (`services/replay.py` `verify`) | 49.2% | 44.2% |
| `engine.advance` | 31.6% | 31.2% |
| `grid.path` (84,238 / 243,922 calls) | 23.9% (own 5.5%) | 23.0% (own 5.4%) |
| `engine.deliver_reports` | 18.3% | 19.6% |
| `comms.progress` (133,758 / 430,944 calls) | 18.2% | 19.4% |
| `storage.encode` | 8.0% | 7.0% |
| **recon.scan** (cumulative) | 4.03% (5.79 s) | 5.00% (21.14 s) |
| recon.sees (cumulative) | 2.88% (4.13 s) | 3.55% (15.02 s) |
| recon.reports (cumulative) | 0.21% (0.29 s) | 0.14% (0.58 s) |
| **recon.py cumulative total** (scan + reports) | **4.24%** | **5.14%** |
| recon.py self time | 0.64% (0.92 s) | 0.75% (3.18 s) |

Reading:

- **The replay check is the largest single cost.** It is 49% (41 units) and 44% (82 units) of profiled time, and in the full runs it is 44% of the with-replay total at 41 units and 57% at 82. A headless run that skips it takes the "no replay" column.
- **Pathing and report delivery follow.** `grid.path` and `deliver_reports` with `comms.progress` are each about a fifth of the time; `comms.progress` is almost all of `deliver_reports` (26.2 of 26.3 s at 41 units), and the JSON does not show whether `grid.path` is called from inside it, so the two shares may overlap.
- **Recon is a minor cost.** `recon.scan` calls `recon.sees`, so `sees` is inside `scan`. Counting `scan` plus `reports` gives 4.2% to 5.1%. Self time (under 1%) understates it because the line-of-sight work sits in callees. `grid.visible` and `grid.line` are not in the top-10 list the script keeps, so their separate cumulative time is not in the data; the recon total above already includes them as callees of `sees`.
- **Scaling.** From 41 to 82 units the whole-run average rises 2.3 times (1.279 to 2.970 s) and the profile shares stay within about 5 points, so no single stage turned superlinear.

## Verdict

- **The 41-unit, 160-interval run in doc 63 gap 9 is feasible on the current engine.** It takes about 1.28 s per interval on average (205 s in all; 366 s with the replay check) on a loaded host, with a first-60-interval mean of 0.54 s and a p95 of 1.03 s. Memory is 485 MB.
- **82 units also complete**: 2.97 s per interval on average (475 s; 1094 s with the replay check), 1.0 GB peak.
- **Not an interactive speed.** No per-interval time limit is set for headless runs in this report. A live browser game at 41 units would wait over a second on average per interval, with the slowest first-60 interval at 1.4 s.
- **No feature work is blocked by run time.** If speed is later needed, the measured order is: the replay check (skip or sample it), then `grid.path` and report delivery, then recon.
- **Gap 9 is closed as a measurement.** It does not say the option A scale (200 m, 180 s) costs the same; see Limits.

## Host load

EVO ran other sessions' cargo jobs throughout. Load averages (1, 5, 15 minutes) logged by the 60/82 job:

| Moment | Load average |
|---|---|
| Before the 684-test suite (00:28 UTC) | 12.63 / 13.75 / 18.30 |
| Before the 60/82 bench (00:32 UTC) | 4.41 / 8.34 / 15.10 |
| After the 60/82 bench (01:07 UTC) | 7.34 / 14.04 / 15.07 |

The 8f5a39c manifest note gives the after-bench figure as "8.55 at 5-min value 14.07"; the logged line reads 7.34 / 14.04, which is used here. The bench is single-threaded. The 6 to 41 run was not load-logged, and it overlapped an 82-unit diagnostic (it died with the edge-column error under Provenance) and the failed default-count run. Treat every timing as an upper estimate under shared load.

## Limits

- **Shared host** (above). No repeat runs: each timing is one sample, so differences of a few percent are noise. The 60-unit window mean (1.004 s) against the 82-unit one (1.169 s) shows this: the full-run figures rise steadily, the windows do not.
- **Synthetic layout.** Two straight lines on flat ground. A real Cannae battle has terrain, uneven contact and wider spread, which change path and sight work.
- **Today's scale.** The engine still runs 50 m hexes and 30 s intervals. Option A (200 m, 180 s, 41 units on the same grid) changes distances, unit speeds and the number of sight and path calls per interval. The time per interval at that scale is not measured and needs gap 1 first.
- **Profile covers 60 intervals**, one count per bench file (41 and 82), with cProfile overhead; shares are indicative.
- **Counts 60 and 82 come from a later script version** (see Provenance); the 6 to 41 placement is identical in both.

## Provenance

- **6 to 41 units:** script at commit `29aea86` (branch `bt-t05-cannae-gap9-bench`, local only). Its default counts failed at 60 and 82 with `KeyError '-1,9'` (`grid.visible`, via `recon.sees`): units on edge columns 0 and 23 let a sight line leave the grid.
- **60 and 82 units:** script at `8f5a39c`, which keeps units on columns 1 to 22 and left the 6 to 41 placement identical.
- **Both commits were rebased onto main as `d011a28` (the bench) and `e99f3b5` (the edge-column fix) with no content change.** Engine as on main at `efe085f` / `33fbb4b`; no engine change in this work.
- Python 3.14.4, x86_64 Linux (WSL2) on the EVO host. No credentials, no model calls.

## Manifest

Data files (kept under `apps/poc/artifacts/`, which is gitignored; not committed):

| File | Source run | SHA-256 |
|---|---|---|
| `unit-count-bench-29aea86.json` (counts 6, 12, 24, 41; profile at 41) | `bt05g-29aea86`, gate 3 | `dda7a71fc961d40da082015f1d19bc5df04ae62bdf776e87c861dd108f15dba9` |
| `unit-count-bench-8f5a39c-60-82.json` (counts 60, 82; profile at 82) | `bt05i-8f5a39c`, gate 2 | `1244a2fa8da18bca494f31ded19a8f0c166d207965e15df77e5914f8221976cf` |

Run directories on EVO (archives of the source tree at each commit):

| Run dir | Commit | Archive SHA-256 |
|---|---|---|
| `bt05g-29aea86` | `29aea86` | `5124abc8bc9ef73192dcf1e3cddb56fb8b07c6269b64ca9c94a6340eae919303` |
| `bt05i-8f5a39c` | `8f5a39c3f66dec397fb204b07c459f1b728fc61f` | `382dee1b7e99a62563526278ed013b7c5c619f6e4921e4b71007563d204bf0a7` |

Gates recorded in the manifests:

| Run dir | Gate | Result |
|---|---|---|
| `bt05g-29aea86` | `python3 -m unittest tests.test_unit_count_bench -v` | exit 0, 2 tests OK |
| `bt05g-29aea86` | bench, default counts | exit 1, `KeyError '-1,9'` at count 60, no JSON |
| `bt05g-29aea86` | bench `--counts 6,12,24,41` | exit 0, replay identical for all 4 |
| `bt05g-29aea86` | child 82 diagnostic (`--child 82 --intervals 60 --run-intervals 160`) | exit 1, same `KeyError` |
| `bt05i-8f5a39c` | full suite `python3 -m unittest discover -s tests -q` | exit 0, 684 tests OK in 214.9 s |
| `bt05i-8f5a39c` | bench `--counts 60,82` | exit 0, replay identical for both |

Neither run modified tracked repo files. To reproduce a count, run `python3 scripts/unit_count_bench.py --counts <n,...> --out <file>` from `apps/poc`; expect the same digests and different timings. This document's figures were computed from the two JSON files above, with no new run.
