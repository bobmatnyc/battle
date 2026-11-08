// Commander replay (docs/research/73): the desk steps and scrubs through the recorded
// revisions of the current battle through the POC's own /api/history and /api/replay,
// in the player's commander view only, with orders closed until it returns to live.
import assert from "node:assert/strict";
import {test} from "node:test";
import {readCommanderReplay, readHistory, type CommanderView, type HistoryEntry} from "@battle/contracts";
import {createDeskApi, type DeskApi} from "../src/api.ts";
import {
  openReplay, ordersClosedReason, ordersOpen, Playback, playbackDelay, replayAt, replayHelp, replayLabel, speedOptions,
  type Replay, type Timers,
} from "../src/replay.ts";
import {commander, map, raw} from "./fixtures.ts";

const entries = (): HistoryEntry[] => readHistory(raw("history"));
// The recorded view at `entry`, as the POC would replay it (turn from the history).
const recorded = (entry: HistoryEntry, side = "union"): CommanderView =>
  ({...readCommanderReplay(raw("replay-commander")), revision: entry.revision, turn: entry.turn, side});

function replayApi(side = "union"): DeskApi & {asked: string[]} {
  const asked: string[] = [];
  const never = async (): Promise<never> => { throw new Error("not used by replay"); };
  return {
    asked, state: never, map: never, scenarios: never, orders: never, clock: never, newBattle: never,
    history: async (gameId) => { asked.push(`history ${gameId}`); return entries(); },
    replay: async (gameId, revision) => {
      asked.push(`replay ${gameId} ${revision}`);
      return recorded(entries().find((e) => e.revision === revision)!, side);
    },
  };
}

test("opening a replay reads the live game's history and shows its latest recorded commander view", async () => {
  const live = commander();
  const api = replayApi();
  const replay = await openReplay(api, live);
  const last = entries().at(-1)!;
  assert.deepEqual(api.asked, [`history ${live.game_id}`, `replay ${live.game_id} ${last.revision}`]);
  assert.equal(replay.index, entries().length - 1);
  assert.equal(replay.view.turn, last.turn);
});

test("stepping back loads an earlier revision, whose header time is earlier; the ends are clamped", async () => {
  const live = commander();
  const api = replayApi();
  const latest = await openReplay(api, live);
  const first = await replayAt(api, latest, 0);
  assert.equal(first.index, 0);
  assert.equal(first.view.turn, 0);
  assert.ok(first.view.turn < latest.view.turn);
  const setting = map().setting;
  assert.equal(replayLabel(first, setting), "Recorded commander view · Thursday, July 2, 1863 · 16:30");
  assert.match(replayLabel(latest, setting), /^Recorded commander view · Thursday, July 2, 1863 · 16:36$/);
  assert.doesNotMatch(replayLabel(latest, setting), /turn|revision/i, "no turn counter or revision label");
  api.asked.length = 0;
  assert.equal(await replayAt(api, first, -1), first, "before the first revision: nothing to load");
  assert.equal(await replayAt(api, latest, latest.entries.length), latest);
  assert.deepEqual(api.asked, []);
});

test("a replay that is not the player's own commander view is refused", async () => {
  const live = commander();
  await assert.rejects(openReplay(replayApi("confederate"), live), /not your commander view/);
  const god = createDeskApi((async () => new Response(JSON.stringify(raw("replay-god")), {status: 200})) as typeof fetch);
  await assert.rejects(god.replay(live.game_id, 14), /view_mode|God|not allowed/);
});

test("orders are closed while replaying and open again live", async () => {
  const live = commander();
  assert.equal(ordersOpen(live, null, false), true);
  const replay = await openReplay(replayApi(), live);
  assert.equal(ordersOpen(live, replay, false), false);
  assert.equal(ordersOpen(live, null, true), false, "busy");
  assert.equal(ordersOpen({...live, status: "complete"}, null, false), false);
});

test("history and replay requests name the game and revision only", async () => {
  const sent: string[] = [];
  const reply = (body: unknown): Response => new Response(JSON.stringify(body), {status: 200});
  const api = createDeskApi((async (url: string | URL | Request) => {
    sent.push(String(url));
    return reply(String(url).startsWith("/api/history") ? raw("history") : raw("replay-side"));
  }) as typeof fetch);
  assert.equal((await api.history("f1c7f1c7f1c7f1c7")).length, entries().length);
  assert.equal((await api.replay("f1c7f1c7f1c7f1c7", 14)).side, "union");
  assert.deepEqual(sent, ["/api/history?game_id=f1c7f1c7f1c7f1c7", "/api/replay?game_id=f1c7f1c7f1c7f1c7&revision=14"]);
});

// Slice 4a (docs/research/81 §2): playback at a speed from the clock's own list, with
// help text, stopping at the last record, on a step or scrub, and when the replay closes.
class FakeTimers implements Timers {
  readonly pending = new Map<number, {run: () => void; ms: number}>();
  private next = 1;
  set(run: () => void, ms: number): number { this.pending.set(this.next, {run, ms}); return this.next++; }
  clear(handle: unknown): void { this.pending.delete(handle as number); }
  /** Runs the one pending timer, then lets the replay read it starts settle. */
  async fire(): Promise<number> {
    assert.equal(this.pending.size, 1, "exactly one playback timer is pending");
    const [[id, timer]] = [...this.pending];
    this.pending.delete(id);
    timer.run();
    await settle();
    return timer.ms;
  }
}
const settle = (): Promise<void> => new Promise((done) => setImmediate(done));

interface Harness { timers: FakeTimers; playback: Playback; shown: number[]; stopped: unknown[]; loads: number[]; replay: Replay | null }
function harness(start: Replay, speed = 10, load?: (replay: Replay, index: number) => Promise<Replay>): Harness {
  const api = replayApi();
  const timers = new FakeTimers();
  const h = {timers, shown: [] as number[], stopped: [] as unknown[], loads: [] as number[], replay: start as Replay | null} as Harness;
  h.playback = new Playback({
    current: () => h.replay,
    load: (replay, index) => { h.loads.push(index); return load ? load(replay, index) : replayAt(api, replay, index); },
    show: (replay) => { h.replay = replay; h.shown.push(replay.index); },
    stopped: (error) => { h.stopped.push(error); },
  }, timers, speed);
  return h;
}

test("playback waits the recorded battle time divided by the speed, and never less than 100 ms", async () => {
  const first = await replayAt(replayApi(), await openReplay(replayApi(), commander()), 2);
  const spt = first.view.seconds_per_turn;
  assert.equal(spt, 30);
  // entries[2] is turn 0, entries[3] turn 1: one 30 s interval.
  assert.equal(playbackDelay(first, 10), 3000);
  assert.equal(playbackDelay(first, 0.5), 60000);
  assert.equal(playbackDelay(first, 60), 500);
  const start = await replayAt(replayApi(), first, 0);  // entries[0] and [1] are both turn 0
  assert.equal(playbackDelay(start, 10), 100, "two records of one interval still take 100 ms");
  const last = await openReplay(replayApi(), commander());
  assert.equal(playbackDelay(last, 10), null, "nothing follows the last record");
});

test("playing steps one record per timer and stops at the last record with no timer left", async () => {
  const start = await replayAt(replayApi(), await openReplay(replayApi(), commander()), 0);
  const h = harness(start, 60);
  h.playback.play();
  assert.equal(h.playback.playing, true);
  const waits: number[] = [];
  while (h.timers.pending.size) waits.push(await h.timers.fire());
  const last = start.entries.length - 1;
  assert.deepEqual(h.shown, Array.from({length: last}, (_, i) => i + 1), "every record in order, once");
  assert.deepEqual(waits, [100, 100, ...Array(last - 2).fill(500)]);
  assert.equal(h.playback.playing, false, "stopped at the end");
  assert.deepEqual(h.stopped, [null], "the end is reported once, with no error");
  assert.equal(h.timers.pending.size, 0);
});

test("pausing, a step or a scrub stops playback, and a reply that arrives after it is not shown", async () => {
  const start = await replayAt(replayApi(), await openReplay(replayApi(), commander()), 3);
  let release: (value: Replay) => void = () => {};
  const h = harness(start, 10, (replay, index) => {
    const answer = replayAt(replayApi(), replay, index);
    return new Promise((done) => { release = (v) => done(v); void answer.then((v) => { pendingReply = v; }); });
  });
  let pendingReply: Replay | null = null;
  h.playback.play();
  await h.timers.fire();                      // the read of record 4 is in flight
  assert.deepEqual(h.loads, [4]);
  h.playback.stop();                          // the player steps, scrubs or presses Pause
  await settle();
  release(pendingReply!);
  await settle();
  assert.deepEqual(h.shown, [], "the late reply does not move the stopped replay");
  assert.equal(h.timers.pending.size, 0, "no timer is left after the stop");
  assert.equal(h.playback.playing, false);
  // Pause while waiting: the pending timer is cleared.
  const again = harness(start, 10);
  again.playback.play();
  assert.equal(again.timers.pending.size, 1);
  again.playback.stop();
  assert.equal(again.timers.pending.size, 0);
});

test("play at the last record starts again from the first", async () => {
  const latest = await openReplay(replayApi(), commander());
  const h = harness(latest, 60);
  h.playback.play();
  await settle();
  assert.deepEqual(h.loads, [0]);
  assert.deepEqual(h.shown, [0]);
  assert.equal(h.timers.pending.size, 1, "then it waits for the next record");
  h.playback.stop();
});

test("a speed change while playing re-times the pending step; the speeds are the clock's own", async () => {
  const start = await replayAt(replayApi(), await openReplay(replayApi(), commander()), 3);
  const h = harness(start, 10);
  h.playback.play();
  assert.equal([...h.timers.pending.values()][0]!.ms, 3000);
  h.playback.setSpeed(30);
  assert.equal(h.timers.pending.size, 1, "the old timer is cleared");
  assert.equal([...h.timers.pending.values()][0]!.ms, 1000);
  assert.equal(h.playback.speed, 30);
  h.playback.stop();
  const speeds = commander().clock.speeds;
  const options = speedOptions(speeds, 30);
  assert.equal((options.match(/<option /g) ?? []).length, speeds.length);
  for (const s of speeds) assert.match(options, new RegExp(`<option value="${s}"`));
  assert.match(options, /<option value="30" selected>30×<\/option>/);
});

test("closing the replay leaves no timer, and a reopened replay plays afresh", async () => {
  const start = await replayAt(replayApi(), await openReplay(replayApi(), commander()), 3);
  const h = harness(start, 10);
  h.playback.play();
  h.replay = null;                            // Return to live, or a new battle, without a stop
  await h.timers.fire();
  assert.deepEqual(h.loads, [], "a tick with no replay reads nothing");
  assert.equal(h.timers.pending.size, 0);
  assert.equal(h.playback.playing, false);
  h.replay = start;                           // reopened
  h.playback.play();
  await h.timers.fire();
  assert.deepEqual(h.shown, [4]);
  h.playback.stop();
  assert.equal(h.timers.pending.size, 0);
});

test("the replay bar explains its controls, and the order help says why orders are closed", async () => {
  const help = replayHelp();
  for (const part of [/Step back/, /Step forward/, /slider/, /Play/, /speed/, /your own commander view/i, /Orders are closed/, /Return to live/]) {
    assert.match(help, part);
  }
  assert.doesNotMatch(help, /\bturn\b|revision/i, "no turn or revision wording");
  const live = commander();
  const replay = await openReplay(replayApi(), live);
  assert.equal(ordersClosedReason(live, null), null, "open live");
  assert.match(ordersClosedReason(live, replay)!, /Orders are closed while you replay/);
  assert.match(ordersClosedReason({...live, status: "complete"}, null)!, /battle is over/);
  assert.match(ordersClosedReason({...live, command: {...live.command, operational: false}}, null)!, /headquarters cannot/);
});
