// The desk's command flows with a fake DeskApi (bt-T07 fix round): an unconfirmed order or
// new battle stays "unknown" even when the re-read fails, and terrain always belongs to the
// view's game.
import assert from "node:assert/strict";
import {test} from "node:test";
import type {CommanderState, MapDocument, OrderSubmission} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "../src/api.ts";
import {reread, sendOrder, startBattle, type Loaded} from "../src/commands.ts";
import {commander, map} from "./fixtures.ts";

const unknown = (): DeskRefusal => new DeskRefusal(504, "The local simulation did not answer within 120000 ms.", true);
const refused = (): DeskRefusal => new DeskRefusal(502, "The local simulation is not reachable at http://127.0.0.1:8874.");
const fail = (error: Error) => async (): Promise<never> => { throw error; };

function fakeApi(overrides: Partial<DeskApi>): DeskApi & {calls: string[]} {
  const calls: string[] = [];
  const track = <A extends unknown[], R>(name: string, fn: (...args: A) => Promise<R>) =>
    async (...args: A): Promise<R> => { calls.push(name); return fn(...args); };
  const never = (name: string) => async (): Promise<never> => { throw new Error(`unexpected ${name}`); };
  return {
    calls,
    state: track("state", overrides.state ?? never("state")),
    map: track("map", overrides.map ?? never("map")),
    scenarios: track("scenarios", overrides.scenarios ?? never("scenarios")),
    orders: track("orders", overrides.orders ?? never("orders")),
    clock: track("clock", overrides.clock ?? never("clock")),
    newBattle: track("newBattle", overrides.newBattle ?? never("newBattle")),
    history: track("history", overrides.history ?? never("history")),
    replay: track("replay", overrides.replay ?? never("replay")),
  };
}

const loaded = (): Loaded => {
  const view = commander();
  return {view, terrain: map(), terrainGame: view.game_id};
};
const body = (view: CommanderState): OrderSubmission =>
  ({orders: [{unit_id: "U2", stance: "hold_fire", destination: null}], game_id: view.game_id, revision: view.revision});
const withNewOrder = (view: CommanderState): CommanderState => ({
  ...view, revision: view.revision + 1,
  orders: [...view.orders, {...view.orders[0]!, id: "O9", unit_id: "U2", stance: "hold_fire", status: "en_route"}],
});
const otherGame = (view: CommanderState): CommanderState => ({...view, game_id: "hougoumont-game", turn: 0});
const otherMap = (): MapDocument => {
  const terrain = map();
  return {...terrain, setting: {...terrain.setting, location: "Hougoumont · Waterloo, Belgium", start_local: "1815-06-18T11:20:00"}};
};

test("an order whose outcome is unknown is re-read, and the re-read decides the notice", async () => {
  const start = loaded();
  const api = fakeApi({orders: fail(unknown()), state: async () => withNewOrder(start.view)});
  const step = await sendOrder(api, start, body(start.view));
  assert.equal(step.notice.kind, "unknown");
  assert.match(step.notice.text, /did take the order: O9/);
  assert.equal(step.loaded.view.revision, start.view.revision + 1);
});

test("an order whose outcome is unknown stays unknown when the re-read also fails", async () => {
  const start = loaded();
  const api = fakeApi({orders: fail(unknown()), state: fail(refused())});
  const step = await sendOrder(api, start, body(start.view));
  assert.equal(step.notice.kind, "unknown");
  assert.match(step.notice.text, /outcome of U2 hold_fire is unknown/);
  assert.match(step.notice.text, /re-reading the battle failed \(The local simulation is not reachable/);
  assert.match(step.notice.text, /Check the order list before sending it again/);
  assert.equal(step.loaded, start, "the last known battle is kept");
});

test("a plain refusal is not turned into an unknown outcome", async () => {
  const start = loaded();
  const api = fakeApi({orders: fail(new DeskRefusal(409, "Battle changed. Refresh before issuing another order."))});
  await assert.rejects(sendOrder(api, start, body(start.view)), /Battle changed/);
  assert.deepEqual(api.calls, ["orders"], "no re-read is mistaken for an answer");
});

test("an accepted order says so", async () => {
  const start = loaded();
  const api = fakeApi({orders: async () => withNewOrder(start.view)});
  const step = await sendOrder(api, start, body(start.view));
  assert.equal(step.notice.kind, "accepted");
  assert.match(step.notice.text, /Order accepted: U2 Hold fire/);
});

test("an unknown new battle that re-reads as the same game is still unknown: it may yet start", async () => {
  const start = loaded();
  const api = fakeApi({newBattle: fail(unknown()), state: async () => start.view});
  const step = await startBattle(api, start, {id: "hougoumont-north-gate", title: "Hougoumont: the north gate"});
  assert.equal(step.notice.kind, "unknown");
  assert.doesNotMatch(step.notice.text, /no new one was started/);
  assert.match(step.notice.text, /same battle so far; a new battle may still start/);
  assert.match(step.notice.text, /Re-read before starting another/);
});

test("an unknown new battle whose re-read fails stays unknown and says so", async () => {
  const start = loaded();
  const api = fakeApi({newBattle: fail(unknown()), state: fail(refused())});
  const step = await startBattle(api, start, {id: "hougoumont-north-gate", title: "Hougoumont: the north gate"});
  assert.equal(step.notice.kind, "unknown");
  assert.match(step.notice.text, /outcome is unknown/);
  assert.match(step.notice.text, /re-reading the battle failed/);
  assert.equal(step.loaded, start);
});

test("an unknown new battle that re-reads as a new game loads that game's terrain", async () => {
  const start = loaded();
  const api = fakeApi({newBattle: fail(unknown()), state: async () => otherGame(start.view), map: async () => otherMap()});
  const step = await startBattle(api, start, {id: "hougoumont-north-gate", title: "Hougoumont: the north gate"});
  assert.equal(step.notice.kind, "unknown");
  assert.match(step.notice.text, /did start a new battle/);
  assert.equal(step.loaded.terrainGame, "hougoumont-game");
  assert.equal(step.loaded.terrain.setting.location, "Hougoumont · Waterloo, Belgium");
});

test("after a new battle whose map read fails, the next re-read fetches the new game's terrain", async () => {
  const start = loaded();
  let maps = 0;
  const api = fakeApi({
    newBattle: async () => otherGame(start.view),
    state: async () => otherGame(start.view),
    map: async () => { maps++; if (maps === 1) throw refused(); return otherMap(); },
  });
  // Slice 2 review: the battle did start, so this is no refusal; the desk holds the new view,
  // keeps the old terrain tagged with the old game, and says the map will be read again.
  const step = await startBattle(api, start, {id: "hougoumont-north-gate", title: "Hougoumont: the north gate"});
  assert.equal(step.notice.kind, "accepted");
  // The title is the new view's own brief (this fake new game reuses the fixture's).
  assert.match(step.notice.text, new RegExp(`^New battle started: ${step.loaded.view.scenario_brief!.title}\\. `));
  assert.match(step.notice.text, /could not be read \(The local simulation is not reachable[^)]*\); the desk will read it again/);
  assert.equal(step.loaded.view.game_id, "hougoumont-game");
  assert.equal(step.loaded.terrainGame, start.view.game_id, "the old terrain is never taken for the new game's");
  const next = await reread(api, step.loaded);
  assert.equal(next.view.game_id, "hougoumont-game");
  assert.equal(next.terrainGame, "hougoumont-game");
  assert.equal(next.terrain.setting.location, "Hougoumont · Waterloo, Belgium");
  assert.equal(maps, 2);
});

test("a re-read of the same game does not fetch the map again, and a new game's view never pairs with old terrain", async () => {
  const start = loaded();
  const same = fakeApi({state: async () => start.view});
  assert.equal((await reread(same, start)).terrain, start.terrain);
  assert.deepEqual(same.calls, ["state"]);
  const broken = fakeApi({state: async () => otherGame(start.view), map: fail(refused())});
  await assert.rejects(reread(broken, start), /not reachable/);
});
