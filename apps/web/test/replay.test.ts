// Commander replay (docs/research/73): the desk steps and scrubs through the recorded
// revisions of the current battle through the POC's own /api/history and /api/replay,
// in the player's commander view only, with orders closed until it returns to live.
import assert from "node:assert/strict";
import {test} from "node:test";
import {readCommanderReplay, readHistory, type CommanderView, type HistoryEntry} from "@battle/contracts";
import {createDeskApi, type DeskApi} from "../src/api.ts";
import {openReplay, ordersOpen, replayAt, replayLabel} from "../src/replay.ts";
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
