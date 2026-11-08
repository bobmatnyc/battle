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

function fails(check: Check<unknown>, input: unknown, path: string, problem?: string): void {
  assert.throws(() => parse(check, input), (error: unknown) => {
    assert.ok(error instanceof ContractError, `expected ContractError, got ${String(error)}`);
    assert.equal(error.path, path, error.message);
    if (problem) assert.ok(error.message.includes(problem), error.message);
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
  // Python accepts an order with no destination key and stores it as given.
  assert.ok(!("destination" in fixtures.orders["orders"][1]));
  assert.ok(fixtures.commanderState["orders"].some((o: Doc) => !("destination" in o)));
  assert.ok(fixtures.godState["orders"].some((o: Doc) => !("destination" in o)));
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
    // Named as God-only, not merely unknown: the list holds even if the top level were open.
    fails(commanderState, {...fixtures.commanderState, [key]: value}, `$.${key}`, "not allowed in this view");
    fails(commanderReplay, {...fixtures.commanderReplay, [key]: value}, `$.${key}`, "not allowed in this view");
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

// Items for records the recorded game has none of, with the keys the Python code writes.
const formationOp = (side: string): Doc => ({id: "F1", side, kind: "split", unit_id: "U1", count: 20,
  destination: [11, 13], order_ids: ["O3"], sent_turn: 12, status: "awaiting_report"});
const codeword = (): Doc => ({codeword: "HAM", meaning: "Bridge taken intact.", bridge: "canal",
  sender_id: "U1", receiver_id: "U2", sent_turn: 10, delivered_turn: 12});
const ownBroadcast = (): Doc => ({id: "recall", kind: "recall", meaning: "Fall back to the camp.",
  stance: "retreat", destination: [3, 4], turn: 40, ordered_turn: null, sounded_turn: null});
const withOwn = (doc: Doc): Doc => {
  doc["formation_ops"] = [formationOp(doc["side"])];
  doc["signals"] = [codeword()];
  doc["broadcasts"] = [ownBroadcast()];
  return doc;
};

test("commander view accepts own formation operations, codewords and broadcasts", () => {
  const doc = mutated("commanderState", withOwn);
  assert.deepEqual(parse(commanderState, doc), doc);
});

// docs/research/81 §4: a recorded Pegasus Bridge commander view (the guard-only entry, whose
// bridge is not blown) after the codeword Ham arrived; record.py writes it.
test("a recorded Pegasus commander view holds a delivered codeword, with exactly the typed keys", () => {
  const recorded = fixture("replay-commander-pegasus");
  assert.deepEqual(parse(commanderReplay, recorded), recorded);
  assert.deepEqual(parse(replayResponse, recorded), recorded);
  assert.equal(recorded["side"], "british");
  assert.deepEqual(recorded["signals"], [{
    bridge: "canal-bridge", codeword: "Ham", delivered_turn: 12, meaning: "Canal bridge taken intact.",
    receiver_id: "DHQ", sender_id: "D25", sent_turn: 11,
  }]);
  assert.ok(recorded["signals"][0].delivered_turn > recorded["signals"][0].sent_turn, "delivered after it was sent");
  fails(commanderReplay, {...recorded, signals: [{...recorded["signals"][0], radius: 1}]}, "$.signals[0].radius");
  fails(commanderReplay, {...recorded, signals: [{...recorded["signals"][0], delivered_turn: undefined}]}, "$.signals[0].delivered_turn");
});

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
  ["contact with exact strength", commanderState, "commanderState", (d) => { d["contacts"][0].strength = 40; }, "$.contacts[0].strength"],
  ["order of another side", commanderState, "commanderState", (d) => { d["orders"][0].side = enemy(d); }, "$.orders[0].side"],
  ["standing order of another side", commanderReplay, "commanderReplay", (d) => { d["standing_orders"] = [{id: "S1", side: enemy(d), status: "awaiting_ack"}]; }, "$.standing_orders[0].side"],
  ["supply site of another side", commanderState, "commanderState", (d) => { d["supply_sites"][0].side = enemy(d); }, "$.supply_sites[0].side"],
  ["formation op of another side", commanderState, "commanderState", (d) => { withOwn(d)["formation_ops"][0].side = enemy(d); }, "$.formation_ops[0].side"],
  ["formation op true ready turn", commanderState, "commanderState", (d) => { withOwn(d)["formation_ops"][0].ready_turn = 14; }, "$.formation_ops[0].ready_turn"],
  ["broadcast with side", commanderState, "commanderState", (d) => { withOwn(d)["broadcasts"][0].side = d["side"]; }, "$.broadcasts[0].side"],
  ["broadcast receipts", commanderReplay, "commanderReplay", (d) => { withOwn(d)["broadcasts"][0].receipts = {}; }, "$.broadcasts[0].receipts"],
  ["codeword sender condition", commanderState, "commanderState", (d) => { withOwn(d)["signals"][0].radius = 2; }, "$.signals[0].radius"],
  ["undelivered recommendation", commanderState, "commanderState", (d) => { delete d["recommendations"][0].received_turn; }, "$.recommendations[0].received_turn"],
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
