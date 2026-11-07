"""The unit-count bench (scripts/unit_count_bench.py, doc 63 §10 gap 9) in
``--quick`` mode: its JSON shape and a deterministic battle digest. Timings
vary from run to run and are not compared."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

POC = Path(__file__).resolve().parent.parent
SCRIPT = POC / "scripts" / "unit_count_bench.py"
TIMING = {"window_intervals", "mean_s", "p95_s", "max_s", "run_s", "run_with_replay_check_s", "peak_rss_mb"}


def quick(directory, name):
    out = Path(directory) / name
    subprocess.run([sys.executable, str(SCRIPT), "--quick", "--out", str(out)], check=True, cwd=POC,
                   capture_output=True, text=True)
    return json.loads(out.read_text())


class UnitCountBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.first, cls.second = quick(tmp, "a.json"), quick(tmp, "b.json")

    def test_quick_bench_has_the_expected_shape(self):
        report = self.first
        self.assertIn("synthetic", report["benchmark"])
        self.assertEqual((report["intervals"], report["run_intervals"]), (5, 5))
        self.assertEqual([r["count"] for r in report["results"]], [6, 12])
        for r in report["results"]:
            self.assertEqual(sum(r["units"].values()), r["count"])
            self.assertEqual(r["intervals_run"], 5)
            self.assertEqual(set(r["timing"]), TIMING)
            self.assertEqual(r["timing"]["window_intervals"], 5)
            self.assertLessEqual(r["timing"]["mean_s"], r["timing"]["p95_s"])
            self.assertGreater(r["timing"]["peak_rss_mb"], 0)
            self.assertEqual(r["battle"]["replay"], "identical")
            self.assertGreater(r["battle"]["volleys"], 0)  # The lines are in contact.
            self.assertEqual(len(r["battle"]["digest"]), 64)
        profile = report["profile"]
        self.assertEqual(profile["count"], 12)  # 41 is not run in --quick: the largest count.
        self.assertEqual(len(profile["top10_cumulative"]), 10)
        self.assertGreaterEqual(profile["recon_py_share"], 0)

    def test_quick_bench_digest_is_deterministic(self):
        def battles(report):
            return [(r["count"], r["intervals_run"], r["battle"]) for r in report["results"]]

        self.assertEqual(battles(self.first), battles(self.second))


if __name__ == "__main__":
    unittest.main()
