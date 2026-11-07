"""Synthetic benchmark: headless run time per interval against unit count.

Why: doc 63 §10 gap 9 asks whether today's engine can run Cannae option A
(41 units on the 24 by 21 grid, 160 intervals: 8 hours at 180 s) before any
feature work; ``recon.scan`` and ``recon.reports`` loop over every unit pair.
What: for each count in ``--counts`` it builds a SYNTHETIC BENCHMARK entry, not
a scenario and never in a catalog: today's engine as-is (50 m hexes, 30 s
intervals, the 24 by 21 grid), flat open ground, two sides split as evenly as
the count allows, two facing lines 4 hexes apart, so fire, recon and pathing
run from the first interval. Units take Gergovia's existing weapon classes
(shock, range 1; every third unit missile, range 3), the Roman communications
profile, voice reach 1 and tactics_v11, as the doc 63 entry would. Each count
runs in its own child process (a clean peak RSS) through ``HeadlessRunner``
with ``BatchStore`` in a temporary database, the path a real headless run
takes. The run lasts ``--run-intervals`` (default 160) unless a side breaks
first. It writes JSON to ``--out``: per count the wall time of the
first ``--intervals`` intervals (mean, p95, max), the full-run total with and
without the closing replay check, peak RSS, the end state and a battle digest
(sha256 of the final snapshot). With ``--profile N`` (default 41; the largest
count when 41 is not run) a further child runs that count under cProfile and
reports the top 10 ``battle/`` functions by cumulative time, the share of own
time spent in ``battle/recon.py`` and the cumulative time of ``recon.scan``,
``recon.reports`` and ``recon.sees``. Both include the closing replay check,
which re-runs every interval. The engine draws no random number; the digest is
deterministic, the timings are not.
Test: `test_quick_bench_has_the_expected_shape`,
`test_quick_bench_digest_is_deterministic`.
Usage, from apps/poc: ``python3 scripts/unit_count_bench.py --out bench.json``;
``--quick`` runs counts 6 and 12 for 5 intervals.
"""

import argparse
import cProfile
import json
import math
import platform
import pstats
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(POC))

from battle.adapters.rules import ScenarioRegistry  # noqa: E402
from battle.batch_store import BatchStore, digest  # noqa: E402
from battle.bootstrap import build_headless  # noqa: E402
from battle.grid import COLS, METRES_PER_HEX, ROWS, key  # noqa: E402
from battle.presentation import ROMAN_VOICE_PROFILE  # noqa: E402
from battle.scenario_command import ROMAN_COMMUNICATIONS, TACTICS_V11  # noqa: E402
from battle.scenario_entry import (  # noqa: E402
    ORDER_CATALOG, RULES_VERSION, MapEntry, ScenarioEntry, SideEntry, UnitEntry, VictoryEntry,
)
from battle.scenario_gergovia import MISSILE, SHOCK, WEAPONS  # noqa: E402

COUNTS = (6, 12, 24, 41, 60, 82)
QUICK_COUNTS, QUICK_INTERVALS = (6, 12), 5
# Doc 63 §3 option A: "8 hours is 160 intervals" (180 s each). The bench runs
# today's 30 s interval; only the number of engine steps is taken from option A.
OPTION_A_INTERVALS = 160
PROFILE_COUNT = 41
DEFENDER_ROWS, ATTACKER_ROWS = (8, 7, 6, 5), (12, 13, 14, 15)  # Lines 4 hexes apart.
STRENGTH = 40  # scenario_entry.unit()'s default detachment; ammo as Gergovia (20 rounds a man).


def flat_terrain():
    return {key([c, r]): {"pos": [c, r], "elevation": 150, "terrain": "open", "move_cost": 100, "cover": 10}
            for r in range(ROWS) for c in range(COLS)}


def placements(n, rows):
    """``n`` hexes filling ``rows`` in order, each row centred on the grid."""
    out = []
    for row in rows:
        k = min(COLS, n - len(out))
        out += [(start + i, row) for start in [(COLS - k) // 2] for i in range(k)]
        if len(out) == n:
            return out
    raise ValueError(f"{n} units do not fit in rows {rows}")


def side_units(prefix, side, n, rows):
    units = []
    for i, pos in enumerate(placements(n, rows)):
        weapon = MISSILE if i % 3 == 2 else SHOCK
        units.append(UnitEntry(f"{prefix}{i + 1}", side, f"Bench {side} {i + 1}", pos,
                               {"initial": STRENGTH, "strength": STRENGTH, "ammo": STRENGTH * 20,
                                "weapon_class": weapon}))
    return tuple(units)


def bench_entry(count, intervals):
    """The synthetic benchmark entry for ``count`` units (attacker gets the odd one)."""
    defenders, attackers = count // 2, count - count // 2
    centre = placements(defenders, DEFENDER_ROWS)[defenders // 2]
    return ScenarioEntry(
        id=f"bench-units-{count}", title=f"Synthetic benchmark, {count} units", variant=None,
        rules=RULES_VERSION, prompt_version="bench-v1", prompt_setting="synthetic benchmark ground",
        labels={RULES_VERSION: f"bench-units-{count}-v1"},
        location="Synthetic benchmark ground (not a scenario)", date="216 BCE", start_time="08:00:00",
        time_basis="synthetic benchmark; no historical basis", seconds_per_turn=30,
        weather={"season": "summer", "conditions": "synthetic benchmark"},
        sides={
            "blue": SideEntry(name="Blue", role="defender", command_unit="B1", headquarters=(12, 2),
                              mission="Benchmark: hold the line.", charge="hold the line"),
            "red": SideEntry(name="Red", role="attacker", command_unit="R1", headquarters=(12, 18),
                             mission="Benchmark: take the centre.", charge="take the centre"),
        },
        units=side_units("B", "blue", defenders, DEFENDER_ROWS) + side_units("R", "red", attackers, ATTACKER_ROWS),
        # A capture longer than the run, so only the deadline or a broken side ends it.
        victory=VictoryEntry(kind="hold-objective", objective=centre, deadline_turns=intervals,
                             radius=0, hold_turns=intervals + 1, objective_name="centre"),
        map=MapEntry(terrain=flat_terrain, features={"roads": (), "buildings": (), "works": ()}, cols=COLS,
                     rows=ROWS, metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                     source="Synthetic flat benchmark ground", source_url=None),
        order_catalog=ORDER_CATALOG, communications=ROMAN_COMMUNICATIONS, voice_profile=ROMAN_VOICE_PROFILE,
        voice_reach=1, weapons=WEAPONS, tactics=TACTICS_V11,
    )


class TimedStore(BatchStore):
    """``BatchStore`` that stamps the wall clock as each advance is stored."""

    def __init__(self, path):
        super().__init__(path, 0)
        self.stamps = []

    def create(self, state):
        gid = super().create(state)
        self.stamps.append(time.perf_counter())
        return gid

    def save(self, gid, state, expected):
        super().save(gid, state, expected)
        if state["last_action"]["type"] == "advance":
            self.stamps.append(time.perf_counter())


def run_count(count, intervals, run_intervals):
    """One timed headless run of ``count`` units in this process."""
    entry = bench_entry(count, run_intervals)
    with tempfile.TemporaryDirectory() as tmp:
        runner = build_headless(Path(tmp) / "bench.sqlite", scenario_id=entry.id,
                                scenarios=ScenarioRegistry([entry]), keyframe_every=0)
        store = runner.repository = TimedStore(Path(tmp) / "timed.sqlite")
        runner.replay.repository = store
        start = time.perf_counter()
        result = runner.run()
        total = time.perf_counter() - start
        final = store.load(result["game_id"])
    steps = [b - a for a, b in zip(store.stamps, store.stamps[1:])]
    window = sorted(steps[:intervals])
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = rss / 2**20 if sys.platform == "darwin" else rss / 2**10  # bytes on macOS, KiB on Linux.
    events = {}
    for e in final["events"]:
        events[e["kind"]] = events.get(e["kind"], 0) + 1
    return {
        "count": count,
        "units": {side: sum(u["side"] == side for u in final["units"]) for side in ("blue", "red")},
        "intervals_run": len(steps),
        "battle": {"digest": digest(final), "winner": final["winner"], "turn": final["turn"],
                   "reason": final["reason"], "replay": result["replay"]["status"],
                   "strength": {s: sum(u["strength"] for u in final["units"] if u["side"] == s)
                                for s in ("blue", "red")},
                   "volleys": events.get("volley", 0), "moves": events.get("unit_moved", 0),
                   "events": len(final["events"])},
        "timing": {
            "window_intervals": len(window),
            "mean_s": statistics.fmean(window) if window else None,
            "p95_s": window[max(0, math.ceil(0.95 * len(window)) - 1)] if window else None,
            "max_s": window[-1] if window else None,
            "run_s": store.stamps[-1] - store.stamps[0],
            "run_with_replay_check_s": total,
            "peak_rss_mb": round(rss_mb, 1),
        },
    }


def profile_count(count, intervals):
    """Top 10 by cumulative time over ``intervals`` intervals of ``count`` units."""
    profiler = cProfile.Profile()
    profiler.enable()
    run_count(count, intervals, intervals)
    profiler.disable()
    stats = pstats.Stats(profiler)
    total = max(v[3] for v in stats.stats.values())  # The outermost call's cumulative time.
    rows = sorted(stats.stats.items(), key=lambda kv: kv[1][3], reverse=True)
    recon = sum(v[2] for (path, _, _), v in stats.stats.items() if path.endswith("battle/recon.py"))

    def label(fn):
        path, line, name = fn
        return f"{Path(path).relative_to(POC) if path.startswith(str(POC)) else path}:{line}({name})"

    battle = [kv for kv in rows if kv[0][0].startswith(str(POC / "battle"))]
    return {
        "count": count, "intervals": intervals, "profiled_s": total,
        "recon_py_own_time_s": recon, "recon_py_share": recon / total if total else None,
        # Cumulative includes the callees (grid.visible for line of sight).
        "recon_py_cumulative_s": {name: v[3] for (path, _, name), v in stats.stats.items()
                                  if path.endswith("battle/recon.py") and name in ("scan", "reports", "sees")},
        "top10_cumulative": [{"function": label(fn), "calls": v[1], "cumulative_s": v[3], "own_s": v[2]}
                             for fn, v in battle[:10]],
    }


def child(*extra):
    """Run this script for one measurement in a fresh interpreter; returns its JSON."""
    cmd = [sys.executable, __file__, *extra]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=POC).stdout
    return json.loads(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--counts", type=lambda v: tuple(int(n) for n in v.split(",")), default=COUNTS,
                        help="comma-separated unit counts (default 6,12,24,41,60,82)")
    parser.add_argument("--intervals", type=int, default=60, help="intervals in the per-interval window")
    parser.add_argument("--run-intervals", type=int, default=OPTION_A_INTERVALS,
                        help="deadline of each run (default 160, doc 63 option A)")
    parser.add_argument("--profile", type=int, default=PROFILE_COUNT,
                        help="count to profile (default 41; the largest count when absent; 0: none)")
    parser.add_argument("--quick", action="store_true", help="counts 6 and 12, 5 intervals")
    parser.add_argument("--out", help="write the JSON results here (default: stdout)")
    parser.add_argument("--child", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--child-profile", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.quick:
        args.counts, args.intervals, args.run_intervals = QUICK_COUNTS, QUICK_INTERVALS, QUICK_INTERVALS
    if args.child is not None:
        print(json.dumps(run_count(args.child, args.intervals, args.run_intervals)))
        return
    if args.child_profile is not None:
        print(json.dumps(profile_count(args.child_profile, args.intervals)))
        return
    timing = ["--intervals", str(args.intervals), "--run-intervals", str(args.run_intervals)]
    results = []
    for count in args.counts:
        results.append(child("--child", str(count), *timing))
        print(f"{count} units: mean {results[-1]['timing']['mean_s']:.4f} s/interval", file=sys.stderr)
    target = args.profile if args.profile in args.counts else max(args.counts)
    profile = child("--child-profile", str(target), *timing) if args.profile else None
    report = {
        "benchmark": "synthetic unit-count benchmark (not a scenario; doc 63 §10 gap 9)",
        "engine": {"rules": RULES_VERSION, "metres_per_hex": METRES_PER_HEX, "seconds_per_turn": 30,
                   "grid": [COLS, ROWS]},
        "host": {"python": platform.python_version(), "platform": platform.platform(),
                 "machine": platform.machine()},
        "intervals": args.intervals, "run_intervals": args.run_intervals,
        "results": results, "profile": profile,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
