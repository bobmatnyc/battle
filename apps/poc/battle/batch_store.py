"""Opt-in batch recording: inputs and digests per revision, full snapshots only at keyframes.

Why: ``Store`` writes the full snapshot, events included, for every revision,
so a 360-turn Pegasus run takes about 1.2 GB and a 90-run sensitivity batch
about 60 GB. Batch and sensitivity runs need the result and a replay proof,
not every intermediate state.
What: ``BatchStore`` keeps the ``Store`` schema and audit records (games,
units, events, decisions, messages) and adds a ``revisions`` table with each
revision's recorded action (``last_action``) and the sha256 of its full
snapshot, the same digest ``Store`` writes. Full snapshots are kept only for
revision 0, the first revision that is no longer ``active`` (the final state)
and, with ``keyframe_every`` K > 0, every K-th revision. ``games`` holds the
latest state as in ``Store``. ``inputs`` returns what ``replay.verify_recorded``
re-runs. The default ``Store``, the HTTP game and saved games do not use it.
Test: `test_batch_run_keeps_the_pinned_digest_and_only_the_end_snapshots`,
`test_batch_run_history_matches_the_full_snapshot_run`,
`test_tampered_action_or_final_state_fails_verification`,
`test_keyframes_are_kept_and_checked`.
"""
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

from .contracts import Conflict
from .storage import Store, encode

REVISIONS = ('CREATE TABLE IF NOT EXISTS revisions (game_id TEXT NOT NULL, revision INTEGER NOT NULL, '
             'turn INTEGER NOT NULL, action TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(game_id,revision))')


def digest(state):
    """The sha256 ``Store`` records for ``state``'s snapshot."""
    return hashlib.sha256(encode(state).encode()).hexdigest()


def recorded_in(path):
    """True when the database at ``path`` exists and holds batch-recorded inputs.
    Never creates the file."""
    if not Path(path).exists():
        return False
    db = sqlite3.connect(str(path), timeout=10)
    try:
        row = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='revisions'").fetchone()
    finally:
        db.close()
    return row is not None


class BatchStore(Store):
    """``Store`` that records inputs per revision and full snapshots at keyframes only."""

    def __init__(self, path, keyframe_every=0):
        if not isinstance(keyframe_every, int) or isinstance(keyframe_every, bool) or keyframe_every < 0:
            raise ValueError('keyframe_every must be a whole number of revisions, 0 or more.')
        super().__init__(path)
        self.keyframe_every = keyframe_every
        with self.connect() as db:
            db.execute(REVISIONS)

    def create(self, state):
        gid = uuid.uuid4().hex[:16]
        raw = encode(state)
        with self.connect() as db:
            db.execute('INSERT INTO games(id,revision,state) VALUES(?,?,?)', (gid, 0, raw))
            self._recorded(db, gid, state, raw)
        return gid

    def save(self, gid, state, expected):
        if state['revision'] != expected + 1:
            raise ValueError('Revision must advance exactly once.')
        raw = encode(state)  # Encoded once for the game row, the digest and any keyframe.
        with self.connect() as db:
            result = db.execute('UPDATE games SET revision=?,state=? WHERE id=? AND revision=?',
                                (state['revision'], raw, gid, expected))
            if result.rowcount != 1:
                raise Conflict('Battle changed. Refresh and try again.')
            self._recorded(db, gid, state, raw)

    def _keyframe(self, state):
        revision = state['revision']
        every = self.keyframe_every
        return revision == 0 or state.get('status', 'active') != 'active' or bool(every and revision % every == 0)

    def _recorded(self, db, gid, state, raw):
        sha = hashlib.sha256(raw.encode()).hexdigest()
        db.execute('INSERT INTO revisions VALUES(?,?,?,?,?)',
                   (gid, state['revision'], state['turn'], encode(state.get('last_action')), sha))
        if self._keyframe(state):
            db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?)', (gid, state['revision'], state['turn'], raw, sha))
        self._audit(db, gid, state)

    def history(self, gid):
        with self.connect() as db:
            rows = [dict(r) for r in db.execute(
                'SELECT revision,turn,sha256 FROM revisions WHERE game_id=? ORDER BY revision', (gid,))]
        return rows or super().history(gid)

    def inputs(self, gid):
        """Why: replay of a batch game re-runs its recorded actions.
        What: one entry per revision, in order: ``revision``, ``turn``,
        ``sha256``, the recorded ``action`` and ``keyframe`` (a full snapshot
        is stored). None for a game recorded by ``Store``.
        Test: `test_keyframes_are_kept_and_checked`."""
        with self.connect() as db:
            keyframes = {r[0] for r in db.execute('SELECT revision FROM snapshots WHERE game_id=?', (gid,))}
            rows = [dict(revision=r['revision'], turn=r['turn'], sha256=r['sha256'],
                         action=json.loads(r['action']), keyframe=r['revision'] in keyframes)
                    for r in db.execute('SELECT * FROM revisions WHERE game_id=? ORDER BY revision', (gid,))]
        return rows or None

    digest = staticmethod(digest)
