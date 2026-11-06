import tempfile
import threading
import unittest
from pathlib import Path
from battle.clock import SimulationClock
from battle.server import Application
from battle.runtime import verify_replay
from battle.storage import Conflict

class ClockTests(unittest.TestCase):
    def setUp(self):
        self.time=0
        self.steps=[]
        self.clock=SimulationClock(lambda: self.steps.append(self.time) or True,now=lambda:self.time)
    def test_pause_resume_speed_preserve_elapsed_fraction(self):
        self.clock.control('start');self.time=1
        self.clock.control('pause')
        self.assertEqual(self.clock.status()['remaining_seconds'],20)
        self.time=100;self.clock.pump();self.assertEqual(self.steps,[])
        self.clock.control('speed',2);self.clock.control('start')
        self.time=109;self.clock.pump();self.assertEqual(self.steps,[])
        self.time=110;self.clock.pump();self.assertEqual(self.steps,[110])
    def test_stall_never_catches_up_in_burst(self):
        self.clock.control('start');self.time=1000
        self.clock.pump();self.clock.pump()
        self.assertEqual(len(self.steps),1)
        self.assertEqual(self.clock.status()['remaining_seconds'],30)
    def test_pause_while_inflight_is_immediate_and_prevents_next_interval(self):
        entered,release=threading.Event(),threading.Event()
        def step(): entered.set();release.wait(2);return True
        self.clock.step=step;self.clock.control('start');self.time=3
        worker=threading.Thread(target=self.clock.pump);worker.start()
        self.assertTrue(entered.wait(1))
        self.clock.control('pause');self.clock.pump()
        self.assertTrue(self.clock.status()['inflight'])
        self.assertFalse(self.clock.status()['running'])
        release.set();worker.join(2)
        self.assertFalse(self.clock.status()['inflight'])
        self.time=100;self.clock.pump();self.assertFalse(self.clock.status()['running'])
    def test_completion_and_failure_stop(self):
        self.clock.step=lambda:False
        self.clock.control('start');self.time=3;self.clock.pump()
        self.assertFalse(self.clock.status()['running'])
        def fail():raise RuntimeError('private error')
        self.clock.step=fail;self.clock.control('start');self.time=6;self.clock.pump()
        self.assertFalse(self.clock.status()['running'])
        self.assertNotIn('private',self.clock.status()['error'])
    def test_invalid_speed_and_failed_audit(self):
        for speed in (0,-1,100,True,None,'30'):
            with self.assertRaises(ValueError):self.clock.control('speed',speed)
        self.clock.control('start')
        def fail(*args):raise OSError('disk full')
        self.clock.audit=fail
        with self.assertRaises(OSError):self.clock.control('pause')
        self.assertFalse(self.clock.status()['running'])
    def test_application_clock_records_replayable_steps_and_restarts_paused(self):
        with tempfile.TemporaryDirectory() as directory:
            app=Application(Path(directory)/'battle.sqlite',offline=True)
            now=[0];app.clock.now=lambda:now[0];app.clock.anchor=0
            gid=app.gid
            app.mutate('/api/clock',dict(game_id=gid,command='start'))
            with self.assertRaises(Conflict):app.mutate('/api/orders',dict(game_id=gid,revision=0,orders=[]))
            now[0]=3;app.clock.pump()
            self.assertEqual(app.state()['turn'],1)
            app.mutate('/api/clock',dict(game_id=gid,command='pause'))
            self.assertEqual(verify_replay(app.store,gid)['status'],'identical')
            with app.store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM clock_events').fetchone()[0],2)
            restarted=Application(Path(directory)/'battle.sqlite',offline=True)
            self.assertFalse(restarted.state()['clock']['running'])
            self.assertEqual(restarted.state()['turn'],1)
            with self.assertRaises(Conflict):app.mutate('/api/clock',dict(game_id='wrong',command='start'))

    def test_reset_starts_new_battle_at_default_speed(self):
        # Reset preserves only God Mode; pacing returns to the documented 10x default.
        with tempfile.TemporaryDirectory() as directory:
            app=Application(Path(directory)/'battle.sqlite',offline=True)
            gid=app.gid
            state=app.mutate('/api/clock',dict(game_id=gid,command='speed',speed=30))
            self.assertEqual(state['clock']['speed'],30)
            state=app.mutate('/api/new',dict(game_id=gid,revision=state['revision']))
            self.assertNotEqual(state['game_id'],gid)
            self.assertEqual(state['clock']['speed'],10)
            self.assertEqual(state['clock']['speed'],SimulationClock.DEFAULT_SPEED)
            self.assertFalse(state['clock']['running'])
            self.assertEqual(state['turn'],0)
            with app.store.connect() as db:
                reset=db.execute("SELECT game_id,speed FROM clock_events WHERE command='reset'").fetchone()
            self.assertEqual((reset['game_id'],reset['speed']),(state['game_id'],10))

if __name__=='__main__':unittest.main()
