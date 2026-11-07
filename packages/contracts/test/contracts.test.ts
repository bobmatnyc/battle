// Contract tests against fixtures recorded from the Python app (docs/research/67).
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {
  ContractError, GOD_ONLY_FIELDS, LIVE_FIELDS, parse, type Check,
  clockStatus, commanderReplay, commanderState, godReplay, godState, history,
  orderSubmission, replayResponse, stateResponse,
} from "../src/index.ts";

type Doc = Record<string, any>;

function fixture(name: string): Doc {
  return JSON.parse(readFileSync(new URL(`../fixtures/${name}.json`, import.meta.url), "utf8"));
}

const fixtures = {
  commanderState: fixture("state-commander"), godState: fixture("state-god"),
  commanderReplay: fixture("replay-commander"), sideReplay: fixture("replay-side"),
  godReplay: fixture("replay-god"), history: fixture("history"), orders: fixture("orders-request"),
};

function fails(check: Check<unknown>, input: unknown, path: string): void {
  assert.throws(() => parse(check, input), (error: unknown) => {
    assert.ok(error instanceof ContractError, `expected ContractError, got ${String(error)}`);
    assert.equal(error.path, path, error.message);
    return true;
  });
}

// A deep copy of fixture `name` changed by `edit`.
function mutated(name: keyof typeof fixtures, edit: (doc: Doc) => void): Doc {
  const doc = structuredClone(fixtures[name]);
  edit(doc);
  return doc;
}

test("commander fixtures validate", () => {
  assert.deepEqual(parse(commanderState, fixtures.commanderState), fixtures.commanderState);
  assert.deepEqual(parse(stateResponse, fixtures.commanderState), fixtures.commanderState);
  for (const replay of [fixtures.commanderReplay, fixtures.sideReplay]) {
    assert.deepEqual(parse(commanderReplay, replay), replay);
    assert.deepEqual(parse(replayResponse, replay), replay);
  }
  // The recorded game reached contacts, a delivered order and staff chat.
  assert.ok(fixtures.commanderState["contacts"].length > 0);
  assert.ok(fixtures.commanderState["messages"].length > 0);
});

test("god fixtures validate", () => {
  assert.deepEqual(parse(godState, fixtures.godState), fixtures.godState);
  assert.deepEqual(parse(stateResponse, fixtures.godState), fixtures.godState);
  assert.deepEqual(parse(godReplay, fixtures.godReplay), fixtures.godReplay);
  assert.deepEqual(parse(replayResponse, fixtures.godReplay), fixtures.godReplay);
});

test("history and order fixtures validate", () => {
  assert.deepEqual(parse(history, fixtures.history), fixtures.history);
  assert.deepEqual(parse(orderSubmission, fixtures.orders), fixtures.orders);
  assert.deepEqual(parse(clockStatus, fixtures.commanderState["clock"]), fixtures.commanderState["clock"]);
});

test("a replay is the live projection without the live fields", () => {
  const live = Object.fromEntries(Object.entries(fixtures.commanderState)
    .filter(([key]) => !(LIVE_FIELDS as readonly string[]).includes(key)));
  assert.deepEqual(fixtures.commanderReplay, live);
  assert.deepEqual(fixtures.sideReplay, fixtures.commanderReplay);  // side = the player's side
  for (const key of LIVE_FIELDS) fails(commanderReplay, {...fixtures.commanderReplay, [key]: null}, `$.${key}`);
});

test("commander view refuses each God-only field", () => {
  for (const key of GOD_ONLY_FIELDS) {
    const value = key === "view_mode" ? "god" : fixtures.godState[key] ?? [];
    fails(commanderState, {...fixtures.commanderState, [key]: value}, `$.${key}`);
    fails(commanderReplay, {...fixtures.commanderReplay, [key]: value}, `$.${key}`);
  }
  // A God view never passes as a commander view, nor the reverse.
  assert.throws(() => parse(commanderState, fixtures.godState), ContractError);
  assert.throws(() => parse(godState, fixtures.commanderState), ContractError);
  assert.throws(() => parse(stateResponse, {...fixtures.commanderState, view_mode: "god"}), ContractError);
});

test("god view requires view_mode god", () => {
  fails(godState, mutated("godState", (d) => { d["view_mode"] = "commander"; }), "$.view_mode");
  fails(godReplay, mutated("godReplay", (d) => { delete d["view_mode"]; }), "$.view_mode");
  fails(stateResponse, mutated("godState", (d) => { d["view_mode"] = "commander"; }), "$.view_mode");
});

const enemy = (doc: Doc): string => doc["scenario_brief"]["opponent"]["id"];

const cases: [string, Check<unknown>, keyof typeof fixtures, (doc: Doc) => void, string][] = [
  ["unit of another side", commanderState, "commanderState", (d) => { d["units"][0].side = enemy(d); }, "$.units[0].side"],
  ["order transport", commanderState, "commanderState", (d) => { d["orders"][0].transport = {}; }, "$.orders[0].transport"],
  ["dispatch side tag", commanderState, "commanderState", (d) => { d["dispatches"][0].side = d["side"]; }, "$.dispatches[0].side"],
  ["supply stock", commanderState, "commanderState", (d) => { d["supply_sites"][0].ammo = 2400; }, "$.supply_sites[0].ammo"],
  ["own side as contact", commanderState, "commanderState", (d) => { d["contacts"][0].side = d["side"]; }, "$.contacts[0].side"],
  ["recommendation of another side", commanderState, "commanderState", (d) => { d["recommendations"][0].side = enemy(d); }, "$.recommendations[0].side"],
  ["opponent's brief", commanderState, "commanderState", (d) => { d["scenario_brief"].side.id = enemy(d); }, "$.scenario_brief.side.id"],
  ["opponent's assessment", commanderReplay, "commanderReplay", (d) => { d["analysis"].side = enemy(d); }, "$.analysis.side"],
  ["clock speed type", commanderState, "commanderState", (d) => { d["clock"].speed = "fast"; }, "$.clock.speed"],
  ["clock speed not offered", commanderState, "commanderState", (d) => { d["clock"].speed = 3; }, "$.clock.speed"],
  ["missing game_id", commanderState, "commanderState", (d) => { delete d["game_id"]; }, "$.game_id"],
  ["negative revision", commanderState, "commanderState", (d) => { d["revision"] = -1; }, "$.revision"],
  ["status value", commanderReplay, "commanderReplay", (d) => { d["status"] = "paused"; }, "$.status"],
  ["hex length", commanderState, "commanderState", (d) => { d["units"][1].pos = [1]; }, "$.units[1].pos"],
  ["unknown top field", commanderState, "commanderState", (d) => { d["debug"] = true; }, "$.debug"],
  ["message role", commanderState, "commanderState", (d) => { d["messages"][0].role = "system"; }, "$.messages[0].role"],
  ["template destination", commanderReplay, "commanderReplay", (d) => { d["order_templates"][0].destination = "map"; }, "$.order_templates[0].destination"],
  ["missing God events", godState, "godState", (d) => { delete d["events"]; }, "$.events"],
  ["God dispatch without side", godState, "godState", (d) => { delete d["dispatches"][0].side; }, "$.dispatches[0].side"],
  ["God contacts", godState, "godState", (d) => { d["contacts"] = [{}]; }, "$.contacts"],
  ["God order without transport", godReplay, "godReplay", (d) => { delete d["orders"][0].transport; }, "$.orders[0].transport"],
  ["God headquarters hex", godReplay, "godReplay", (d) => { d["headquarters"][d["side"]] = "13,15"; }, `$.headquarters.${fixtures.godReplay["side"]}`],
  ["God brief of the opponent", godReplay, "godReplay", (d) => { d["scenario_brief"].side.id = enemy(d); }, "$.scenario_brief.side.id"],
  ["replay response unit", replayResponse, "godReplay", (d) => { d["units"][0].strength = "40"; }, "$.units[0].strength"],
  ["state response live field", stateResponse, "godState", (d) => { d["inference_available"] = "no"; }, "$.inference_available"],
  ["history digest", history, "history", (d) => { d[1].sha256 = "zz"; }, "$[1].sha256"],
  ["history order", history, "history", (d) => { d[2].revision = d[1].revision; }, "$[2].revision"],
  ["history start", history, "history", (d) => { d.shift(); }, "$[0].revision"],
  ["no orders", orderSubmission, "orders", (d) => { d["orders"] = []; }, "$.orders"],
  ["four orders", orderSubmission, "orders", (d) => { d["orders"] = Array(4).fill(d["orders"][0]); }, "$.orders"],
  ["extra order key", orderSubmission, "orders", (d) => { d["orders"][0].priority = 1; }, "$.orders[0].priority"],
  ["destination as text", orderSubmission, "orders", (d) => { d["orders"][0].destination = "11,14"; }, "$.orders[0].destination"],
  ["empty unit id", orderSubmission, "orders", (d) => { d["orders"][0].unit_id = ""; }, "$.orders[0].unit_id"],
  ["missing cursor", orderSubmission, "orders", (d) => { delete d["revision"]; }, "$.revision"],
];

test("every validator rejects a mutated fixture with the path of the bad field", async (t) => {
  for (const [name, check, source, edit, path] of cases) {
    await t.test(name, () => {
      parse(check, fixtures[source]);  // the unmutated fixture passes
      fails(check, mutated(source, edit), path);
    });
  }
});

test("prototype keys in the input are fields, not prototype members", () => {
  const body = JSON.parse(JSON.stringify(fixtures.orders).replace('"stance"', '"toString":1,"stance"'));
  fails(orderSubmission, body, "$.orders[0].toString");
  const proto = JSON.parse('{"__proto__": {"orders": []}, "game_id": "g", "revision": 0}');
  fails(orderSubmission, proto, "$.orders");
});
