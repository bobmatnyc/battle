"""Atomic SQLite snapshots, normalized current units, and append-only audit events."""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .contracts import Conflict  # Compatibility export; contract belongs to the application.

def encode(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))

class Store:
    def __init__(self,path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS clock_events (id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT NOT NULL, revision INTEGER NOT NULL, command TEXT NOT NULL, speed REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS snapshots (game_id TEXT NOT NULL, revision INTEGER NOT NULL, turn INTEGER NOT NULL, state TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(game_id,revision));
                CREATE TABLE IF NOT EXISTS events (game_id TEXT NOT NULL, seq INTEGER NOT NULL, turn INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(game_id,seq));
                CREATE TABLE IF NOT EXISTS units (game_id TEXT NOT NULL, unit_id TEXT NOT NULL, side TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(game_id,unit_id));
                CREATE TABLE IF NOT EXISTS decisions (game_id TEXT NOT NULL, decision_index INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(game_id,decision_index));
                CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT NOT NULL, turn INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, proposals TEXT NOT NULL, source TEXT NOT NULL);
            ''')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()
    def latest(self):
        with self.connect() as db:
            r=db.execute('SELECT id FROM games ORDER BY rowid DESC LIMIT 1').fetchone()
            return r['id'] if r else None
    def create(self,state):
        gid=uuid.uuid4().hex[:16]
        with self.connect() as db:
            raw=encode(state)
            db.execute('INSERT INTO games(id,revision,state) VALUES(?,?,?)',(gid,0,raw))
            self._records(db,gid,state)
        return gid
    def load(self,gid,revision=None):
        with self.connect() as db:
            if revision is None:
                r=db.execute('SELECT state FROM games WHERE id=?',(gid,)).fetchone()
            else:
                r=db.execute('SELECT state FROM snapshots WHERE game_id=? AND revision=?',(gid,revision)).fetchone()
            if not r: raise ValueError('Battle or revision not found.')
            return json.loads(r['state'])
    def save(self,gid,state,expected):
        if state['revision']!=expected+1:
            raise ValueError('Revision must advance exactly once.')
        with self.connect() as db:
            result=db.execute('UPDATE games SET revision=?,state=? WHERE id=? AND revision=?',
                              (state['revision'],encode(state),gid,expected))
            if result.rowcount!=1: raise Conflict('Battle changed. Refresh and try again.')
            self._records(db,gid,state)
    def _records(self,db,gid,state):
        raw=encode(state)
        db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?)',(gid,state['revision'],state['turn'],raw,hashlib.sha256(raw.encode()).hexdigest()))
        for u in state['units']:
            db.execute('INSERT OR REPLACE INTO units VALUES(?,?,?,?)',(gid,u['id'],u['side'],encode(u)))
        count=db.execute('SELECT COUNT(*) FROM events WHERE game_id=?',(gid,)).fetchone()[0]
        for e in state['events'][count:]:
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(gid,e['seq'],e['turn'],e['kind'],encode(e)))
        count=db.execute('SELECT COUNT(*) FROM decisions WHERE game_id=?',(gid,)).fetchone()[0]
        for i,d in enumerate(state['decisions'][count:],count):
            db.execute('INSERT INTO decisions VALUES(?,?,?)',(gid,i,encode(d)))
        action=state.get('last_action',{})
        if action.get('type')=='chat':
            decision=action['decision']
            for role,content,proposals,source in [
                ('user',decision['request'],[],'human'),
                ('assistant',decision['text'],decision['orders'],decision['source'])]:
                db.execute('INSERT INTO messages(game_id,turn,role,content,proposals,source) VALUES(?,?,?,?,?,?)',
                           (gid,state['turn'],role,content,encode(proposals),source))
    def messages(self,gid):
        with self.connect() as db:
            return [dict(r,proposals=json.loads(r['proposals'])) for r in db.execute('SELECT * FROM messages WHERE game_id=? ORDER BY id',(gid,))]
    def history(self,gid):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT revision,turn,sha256 FROM snapshots WHERE game_id=? ORDER BY revision',(gid,))]

    def clock_event(self,gid,command,speed=None):
        with self.connect() as db:
            db.execute('INSERT INTO clock_events(game_id,revision,command,speed) SELECT id,revision,?,? FROM games WHERE id=?', (command,speed,gid))
