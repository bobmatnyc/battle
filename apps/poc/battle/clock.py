"""Wall-time pacing for atomic simulation intervals; never part of battle physics."""
import threading
import time

class SimulationClock:
    SPEEDS = (0.5, 1, 2, 5, 10, 30, 60)
    DEFAULT_SPEED = 10

    def __init__(self, step, now=time.monotonic, audit=None):
        self.step, self.now, self.audit = step, now, audit
        self.lock = threading.RLock()
        self.running = self.inflight = False
        self.speed = self.DEFAULT_SPEED
        self.remaining = 30.0
        self.anchor = now()
        self.error = None
        self.closed = threading.Event()
        self.worker = None

    def _accrue(self):
        now = self.now()
        if self.running and not self.inflight:
            self.remaining = max(0, self.remaining - (now-self.anchor)*self.speed)
        self.anchor = now

    def status(self):
        with self.lock:
            self._accrue()
            return dict(running=self.running, inflight=self.inflight, speed=self.speed,
                        remaining_seconds=round(self.remaining, 2), speeds=list(self.SPEEDS), error=self.error)

    def control(self, command, speed=None):
        with self.lock:
            if command not in ('start', 'pause', 'speed', 'reset'):
                raise ValueError('Unknown clock command.')
            if command == 'speed' and (isinstance(speed, bool) or speed not in self.SPEEDS):
                raise ValueError('Unsupported clock speed.')
            self._accrue()
            # A failed audit must not leave the battle running without a record.
            try:
                # A reset audit records the rate the new battle starts at.
                if self.audit: self.audit(command, self.DEFAULT_SPEED if command == 'reset' else speed)
            except Exception:
                self.running = False
                raise
            if command == 'start': self.running, self.error = True, None
            elif command == 'pause': self.running = False
            elif command == 'speed': self.speed = speed
            elif command == 'reset':
                # A new battle starts paused at the default rate; only God Mode survives Reset.
                self.running, self.remaining, self.error = False, 30.0, None
                self.speed = self.DEFAULT_SPEED
            return self.status()

    def pump(self):
        with self.lock:
            self._accrue()
            if not self.running or self.inflight or self.remaining > 0: return
            self.inflight = True
        active, error = False, None
        try:
            active = self.step()
        except Exception:
            error = 'Clock paused: interval could not be completed. Inspect the saved battle before restarting.'
        finally:
            with self.lock:
                self.inflight = False
                self.remaining, self.anchor = 30.0, self.now()
                self.error = error
                if not active or error: self.running = False
                # No accumulated catch-up after slow inference or a suspended host.

    def start_worker(self):
        def work():
            while not self.closed.wait(0.05): self.pump()
        self.worker = threading.Thread(target=work, name='battle-clock', daemon=True)
        self.worker.start()

    def close(self):
        with self.lock: self.running = False
        self.closed.set()
        if self.worker: self.worker.join(timeout=22)
