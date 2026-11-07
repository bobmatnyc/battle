"""Batch recording (``battle/batch_store.py``): inputs and digests per revision,
full snapshots at keyframes only, and a replay that re-runs the inputs."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from battle.adapters.rules import RulesSimulation
from battle.batch_store import BatchStore, recorded_in
from battle.bootstrap import build_headless, build_replay
from battle.scenario_pegasus import PEGASUS_BRIDGE as ENTRY
from battle.storage import Store
from test_pegasus import BASELINE_RUN_SHA256
from test_services import RepositoryContract


def batch_run(tmp, keyframe_every=0, name="batch.sqlite"):
    db = Path(tmp) / name
    result = build_headless(db, scenario_id=ENTRY.id, keyframe_every=keyframe_every).run()
    return db, result


def snapshot_revisions(db, gid):
    with closing(sqlite3.connect(db)) as conn, conn:
        return [r[0] for r in conn.execute(
            "SELECT revision FROM snapshots WHERE game_id=? ORDER BY revision", (gid,))]


class BatchStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_batch_run_keeps_the_pinned_digest_and_only_the_end_snapshots(self):
        db, result = batch_run(self.tmp.name)
        final = build_replay(db).repository.load(result["game_id"])
        summary = {k: v for k, v in result.items() if k != "game_id"}
        pinned = hashlib.sha256(json.dumps({"result": summary, "final": final}, sort_keys=True).encode()).hexdigest()
        self.assertEqual(pinned, BASELINE_RUN_SHA256)
        self.assertEqual(result["replay"]["status"], "identical")
        last = result["replay"]["revisions"] - 1
        self.assertEqual(snapshot_revisions(db, result["game_id"]), [0, last])
        # A fresh process detects the batch database and re-runs its inputs.
        self.assertEqual(build_replay(db).verify(result["game_id"]), result["replay"])

    def test_batch_run_history_matches_the_full_snapshot_run(self):
        db, result = batch_run(self.tmp.name)
        full_db = Path(self.tmp.name) / "full.sqlite"
        full = build_headless(full_db, scenario_id=ENTRY.id).run()
        self.assertFalse(recorded_in(full_db))  # The default store writes no batch table.
        self.assertIsInstance(build_replay(full_db).repository, Store)
        self.assertNotIsInstance(build_replay(full_db).repository, BatchStore)
        self.assertEqual(build_replay(db).repository.history(result["game_id"]),
                         build_replay(full_db).repository.history(full["game_id"]))
        self.assertEqual({k: v for k, v in result.items() if k != "game_id"},
                         {k: v for k, v in full.items() if k != "game_id"})

    def test_tampered_action_or_final_state_fails_verification(self):
        db, result = batch_run(self.tmp.name)
        gid = result["game_id"]
        with closing(sqlite3.connect(db)) as conn, conn:
            row = conn.execute("SELECT revision, action FROM revisions WHERE game_id=? AND action LIKE "
                               "'%\"advance\"%' ORDER BY revision LIMIT 1", (gid,)).fetchone()
            action = json.loads(row[1])
            action["decision"] = None if action.get("decision") else {"source": "tampered"}
            conn.execute("UPDATE revisions SET action=? WHERE game_id=? AND revision=?",
                         (json.dumps(action), gid, row[0]))
        with self.assertRaisesRegex(ValueError, "Replay diverged"):
            build_replay(db).verify(gid)

        db, result = batch_run(self.tmp.name, name="final.sqlite")
        gid = result["game_id"]
        repository = build_replay(db).repository
        final = repository.load(gid)
        final["turn"] += 1
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("UPDATE games SET state=? WHERE id=?", (json.dumps(final), gid))
        with self.assertRaisesRegex(ValueError, "Replay diverged"):
            build_replay(db).verify(gid)

    def test_keyframes_are_kept_and_checked(self):
        db, result = batch_run(self.tmp.name, keyframe_every=2)
        gid = result["game_id"]
        last = result["replay"]["revisions"] - 1
        expected = sorted({0, last, *range(2, last + 1, 2)})
        self.assertEqual(snapshot_revisions(db, gid), expected)
        inputs = build_replay(db).repository.inputs(gid)
        self.assertEqual([i["revision"] for i in inputs if i["keyframe"]], expected)
        # A keyframe that differs from the replayed state fails, though every digest matches.
        repository = build_replay(db).repository
        frame = repository.load(gid, 2)
        frame["turn"] += 100
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("UPDATE snapshots SET state=? WHERE game_id=? AND revision=2", (json.dumps(frame), gid))
        with self.assertRaisesRegex(ValueError, "Replay diverged at revision 2"):
            build_replay(db).verify(gid)

    def test_refuses_a_negative_or_fractional_keyframe_interval(self):
        for bad in (-1, 1.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                BatchStore(Path(self.tmp.name) / "bad.sqlite", bad)

    def test_a_missing_database_is_not_batch_recorded_and_is_not_created(self):
        path = Path(self.tmp.name) / "absent.sqlite"
        self.assertFalse(recorded_in(path))
        self.assertFalse(path.exists())


class BatchStoreContractTests(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = BatchStore(Path(self.tmp.name) / "contract.sqlite")

    def test_non_keyframe_revision_is_not_stored(self):
        from battle import scenario
        state = scenario.create()
        gid = self.repo.create(state)
        updated = RulesSimulation().apply(state, {"type": "advance", "decision": None})
        self.repo.save(gid, updated, 0)
        self.assertEqual(self.repo.load(gid), updated)
        with self.assertRaisesRegex(ValueError, "not found"):
            self.repo.load(gid, 1)
        self.assertEqual([h["revision"] for h in self.repo.history(gid)], [0, 1])


if __name__ == "__main__":
    unittest.main()
