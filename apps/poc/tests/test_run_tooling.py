"""Model-vs-control run tooling (docs/research/83, bt-T22): ``make headless-poc
SCENARIO=<id>`` and the share-run and breakthrough columns of
``scripts/cannae_runs.py``.

The make tests run the real target; the column tests read synthetic victory
records shaped as ``victory_encircle.Encircle`` writes them, plus one short
old-edition run through the script's own path.
"""

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from battle.adapters.rules import ScenarioRegistry
from battle.bootstrap import build_headless, build_replay
from battle.scenario_cannae import cannae_entry

POC = Path(__file__).resolve().parents[1]
ROOT = POC.parents[1]
# The recipe as it stood at 56143f2; no SCENARIO must leave it byte for byte.
RECIPE = ('run_dir=$(mktemp -d "${TMPDIR:-/tmp}/battle-headless.XXXXXX") && \\\n'
          '\t  echo "Headless artifacts: $run_dir" && \\\n'
          '\t  cd apps/poc && python3 -m battle --headless --db "$run_dir/battle.sqlite"\n')


def make(*args):
    """Run ``make`` at the repository root; the target's mktemp run directory lands in a temporary TMPDIR."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": tmp}
        env.pop("SCENARIO", None)
        env.pop("MAKEFLAGS", None)
        return subprocess.run(["make", "--no-print-directory", "-C", str(ROOT), *args], capture_output=True,
                              text=True, timeout=120, env=env)


def load_runs():
    spec = importlib.util.spec_from_file_location("cannae_runs", POC / "scripts" / "cannae_runs.py")
    runs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runs)
    return runs


class HeadlessTargetTests(unittest.TestCase):
    def test_no_scenario_leaves_the_recipe_as_it_was(self):
        for args in ((), ("SCENARIO=",)):
            with self.subTest(args=args):
                dry = make("-n", "headless-poc", "PYTHON=python3", *args)
                self.assertEqual((dry.returncode, dry.stdout), (0, RECIPE))

    def test_a_named_scenario_runs_through_the_target(self):
        # The #23 pins (bt-T17): Pegasus is German at 5, Hill 223 American at 27.
        for sid, winner, turns in (("pegasus-bridge", "german", 5), ("hill-223-patrol", "american", 27)):
            with self.subTest(scenario=sid):
                done = make("headless-poc", f"SCENARIO={sid}", f"PYTHON={sys.executable}")
                self.assertEqual(done.returncode, 0, done.stderr)
                lines = done.stdout.splitlines()
                self.assertTrue(lines[0].startswith("Headless artifacts: "))
                summary = ast.literal_eval(lines[-1])
                self.assertEqual((summary["run"]["scenario_id"], summary["winner"], summary["turns"],
                                  summary["replay"]["status"]), (sid, winner, turns, "identical"))

    def test_an_unknown_scenario_exits_non_zero_and_names_the_valid_ids(self):
        done = make("headless-poc", "SCENARIO=nope", f"PYTHON={sys.executable}")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Unknown scenario 'nope'. Known scenarios: little-round-top, hougoumont-north-gate, "
                      "concord-north-bridge, concord-north-bridge-v1, pegasus-bridge, hill-223-patrol, "
                      "gergovia-recall, cannae-envelopment.", done.stderr)


def victory(needed, rows, **extra):
    """A victory record: ``rows`` are ``(turn, enclosed men, lost men)``; the other columns are filler."""
    return {"enclosed_needed": needed, "record": [[t, 1, men, lost, 3, 3, 0] for t, men, lost in rows], **extra}


class CannaeColumnsTests(unittest.TestCase):
    runs = load_runs()

    def test_share_runs_count_the_intervals_at_the_share_and_the_longest_consecutive_run(self):
        # Share 100, enclosed plus lost: at 2, 3, 4 (run of 3), 6, 7 (run of 2), 9 and 10 split by a missing turn.
        rows = [(1, 99, 0), (2, 60, 40), (3, 100, 0), (4, 0, 120), (5, 50, 49), (6, 100, 0), (7, 100, 0),
                (9, 100, 0), (11, 100, 0)]
        self.assertEqual(self.runs.share_runs(victory(100, rows)),
                         {"share_intervals": 7, "longest_share_run": 3})
        self.assertEqual(self.runs.share_runs(victory(100, [])), {"share_intervals": 0, "longest_share_run": 0})

    def test_breakthroughs_list_unit_and_first_interval_when_the_edition_records_them(self):
        # Doc 82 §9's Q3 order: by first interval, then unit id (A1 before L7 at 46).
        broke = {"L4": [67, 1200], "L1": [33, 3397], "L7": [46, 900], "A1": [46, 2000], "L2": [36, 800]}
        self.assertEqual(self.runs.breakthroughs(victory(1, [], edition="cannae-d38", broke_through=broke)),
                         [["L1", 33], ["L2", 36], ["A1", 46], ["L7", 46], ["L4", 67]])
        self.assertEqual(self.runs.breakthroughs(victory(1, [], edition="cannae-d38", broke_through={})), [])
        self.assertIsNone(self.runs.breakthroughs(victory(1, [])))  # An old-edition record has none.

    def test_an_old_edition_run_still_prints_with_the_columns_from_its_record(self):
        old = cannae_entry(edition=None)
        short = replace(old, victory=replace(old.victory, deadline_turns=12))
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cannae-old.sqlite"
            result = build_headless(db, scenario_id=short.id, scenarios=ScenarioRegistry([short]),
                                    keyframe_every=0).run()
            final = build_replay(db).repository.load(result["game_id"])
        row = self.runs.summarise("old", short, result, final, 0.0)
        self.assertEqual((row["edition"], row["broke_through"], row["breakthroughs"]), (None, None, None))
        self.assertEqual({k: row[k] for k in ("share_intervals", "longest_share_run")},
                         self.runs.share_runs(final["victory"]))
        self.assertEqual(len(final["victory"]["record"]), 12)


if __name__ == "__main__":
    unittest.main()
