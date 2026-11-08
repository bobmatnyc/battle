// Commander replay of the current battle (docs/research/73), apart from the DOM so it can be
// tested with a fake DeskApi. It reads the POC's own /api/history and /api/replay (the POC
// desk's replay, apps/poc/static/app.js), always for the player's side: the relay forwards
// no `side` or `view`, and a replayed view of any other side is refused here as well.
import type {BattleSetting, CommanderState, CommanderView, HistoryEntry} from "@battle/contracts";
import type {DeskApi} from "./api.ts";
import {battleClock} from "./timeline.ts";

/** A replay of `gameId`: its recorded revisions and the view at `entries[index]`. */
export interface Replay {
  readonly gameId: string; readonly side: string;
  readonly entries: readonly HistoryEntry[]; readonly index: number; readonly view: CommanderView;
}

async function load(api: DeskApi, replay: Omit<Replay, "view" | "index">, index: number): Promise<Replay> {
  const view = await api.replay(replay.gameId, replay.entries[index]!.revision);
  if (view.side !== replay.side) throw new Error(`The recorded view is not your commander view (side ${view.side}).`);
  return {...replay, index, view};
}

/** Why: the player replays the battle as their commander saw it, from the most recent record back.
 * What: reads the live game's history and loads its latest revision's commander view.
 * Test: `opening a replay reads the live game's history and shows its latest recorded commander view`,
 * `a replay that is not the player's own commander view is refused`. */
export async function openReplay(api: DeskApi, live: CommanderState): Promise<Replay> {
  const entries = await api.history(live.game_id);
  return load(api, {gameId: live.game_id, side: live.side, entries}, entries.length - 1);
}

/** What: the replay at `index` (a step or a scrub); `replay` itself when `index` is outside the record.
 * Test: `stepping back loads an earlier revision, whose header time is earlier; the ends are clamped`. */
export async function replayAt(api: DeskApi, replay: Replay, index: number): Promise<Replay> {
  if (!Number.isInteger(index) || index < 0 || index >= replay.entries.length || index === replay.index) return replay;
  return load(api, replay, index);
}

/** Why: a recorded view is read only; orders go to the live battle alone.
 * What: true only live, not busy, in an active battle whose headquarters can command.
 * Test: `orders are closed while replaying and open again live`. */
export function ordersOpen(live: CommanderState, replay: Replay | null, busy: boolean): boolean {
  return replay === null && !busy && live.status === "active" && live.command.operational;
}

/** The replay bar's text: the recorded view's calendar date and battlefield time, never a revision. */
export function replayLabel(replay: Replay, setting: BattleSetting): string {
  const at = battleClock(setting, replay.view.turn, replay.view.seconds_per_turn, replay.view.display_locale);
  return `Recorded commander view · ${at.date} · ${at.time}`;
}

// Slice 4a (docs/research/81 §2): playback at a speed, as the POC desk's scheduleReplay
// (apps/poc/static/app.js): the wait between two records is the battle time between them
// divided by the speed, never less than MIN_STEP_MS.
const MIN_STEP_MS = 100;

/** The timer pair playback uses; the desk passes the browser's, tests a fake. */
export interface Timers { set(run: () => void, ms: number): unknown; clear(handle: unknown): void }
export const browserTimers: Timers = {
  set: (run, ms) => setTimeout(run, ms),
  clear: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
};

/** What: wall milliseconds to show `replay`'s current record at `speed` before the next one;
 * null at the last record.
 * Test: `playback waits the recorded battle time divided by the speed, and never less than 100 ms`. */
export function playbackDelay(replay: Replay, speed: number): number | null {
  const here = replay.entries[replay.index], next = replay.entries[replay.index + 1];
  if (!here || !next) return null;
  const seconds = (next.turn - here.turn) * replay.view.seconds_per_turn;
  return Math.max(MIN_STEP_MS, seconds * 1000 / speed);
}

/** What playback reads and tells the desk. `current` is the replay on screen (null once closed). */
export interface PlaybackHooks {
  current(): Replay | null;
  load(replay: Replay, index: number): Promise<Replay>;
  show(replay: Replay): void;
  /** Playback stopped by itself: at the last record (`error` null) or on a failed read. */
  stopped(error: unknown): void;
}

/** Why: the player watches the battle unfold at a chosen pace, and a step, scrub, pause or
 * closed replay must never be overtaken by a timer or a late reply.
 * What: one pending timer at most. Each tick reads the next record and shows it, then waits
 * `playbackDelay`. `stop` clears the timer and bumps a generation, so a read already in flight
 * is dropped. A tick that finds no replay stops; play at the last record starts from the first.
 * Test: `playing steps one record per timer and stops at the last record with no timer left`,
 * `pausing, a step or a scrub stops playback, and a reply that arrives after it is not shown`,
 * `play at the last record starts again from the first`,
 * `a speed change while playing re-times the pending step; the speeds are the clock's own`,
 * `closing the replay leaves no timer, and a reopened replay plays afresh`. */
export class Playback {
  #playing = false;
  #generation = 0;
  #handle: unknown = null;
  #speed: number;
  readonly #hooks: PlaybackHooks;
  readonly #timers: Timers;

  constructor(hooks: PlaybackHooks, timers: Timers, speed: number) {
    this.#hooks = hooks;
    this.#timers = timers;
    this.#speed = speed;
  }

  get playing(): boolean { return this.#playing; }
  get speed(): number { return this.#speed; }

  play(): void {
    const replay = this.#hooks.current();
    if (!replay || this.#playing) return;
    this.#playing = true;
    const generation = ++this.#generation;
    if (replay.index >= replay.entries.length - 1) void this.#advance(generation, 0);
    else this.#schedule(generation);
  }

  stop(): void {
    this.#playing = false;
    this.#generation += 1;
    this.#clear();
  }

  setSpeed(speed: number): void {
    this.#speed = speed;
    if (!this.#playing) return;
    this.#clear();
    this.#schedule(++this.#generation);
  }

  #clear(): void {
    if (this.#handle !== null) this.#timers.clear(this.#handle);
    this.#handle = null;
  }

  #schedule(generation: number): void {
    const replay = this.#hooks.current();
    const delay = replay ? playbackDelay(replay, this.#speed) : null;
    if (!replay || delay === null) {
      this.stop();
      if (replay) this.#hooks.stopped(null);
      return;
    }
    this.#handle = this.#timers.set(() => {
      this.#handle = null;
      void this.#advance(generation, replay.index + 1);
    }, delay);
  }

  async #advance(generation: number, index: number): Promise<void> {
    if (generation !== this.#generation) return;
    const replay = this.#hooks.current();
    if (!replay) { this.stop(); return; }
    let next: Replay;
    try {
      next = await this.#hooks.load(replay, index);
    } catch (error) {
      if (generation === this.#generation) { this.stop(); this.#hooks.stopped(error); }
      return;
    }
    if (generation !== this.#generation || this.#hooks.current() !== replay) return;
    this.#hooks.show(next);
    this.#schedule(generation);
  }
}

/** The replay speeds as `<option>`s: the clock's own `speeds` list, `chosen` selected. */
export function speedOptions(speeds: readonly number[], chosen: number): string {
  return speeds.map((s) => `<option value="${s}"${s === chosen ? " selected" : ""}>${s}×</option>`).join("");
}

/** Why: the replay bar's controls, and what the recorded view is, are not self-evident.
 * What: the bar's help text.
 * Test: `the replay bar explains its controls, and the order help says why orders are closed`. */
export function replayHelp(): string {
  return "Step back and Step forward move one record; the slider jumps to any record. "
    + "Play runs the record forward at the chosen speed (at 10×, a battlefield minute takes six seconds) "
    + "and stops at the latest record; a step or the slider stops it. "
    + "This is your own commander view as it was recorded: what your headquarters knew then, not what was true. "
    + "Orders are closed while replaying; Return to live to command.";
}

/** What: why orders cannot be sent now, or null when they can (a pending request aside):
 * replaying, the battle over, or headquarters unable to command.
 * Test: `the replay bar explains its controls, and the order help says why orders are closed`. */
export function ordersClosedReason(live: CommanderState, replay: Replay | null): string | null {
  if (replay) return "Orders are closed while you replay the recorded commander view. Return to live to command.";
  if (live.status !== "active") return "The battle is over; orders are closed.";
  if (!live.command.operational) return "Orders are closed: your headquarters cannot command at present.";
  return null;
}
