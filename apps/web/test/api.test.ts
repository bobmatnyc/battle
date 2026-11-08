// The desk's transport: commander view only, refusals surfaced with the server's text.
import assert from "node:assert/strict";
import {test} from "node:test";
import {ContractError} from "@battle/contracts";
import {createDeskApi, DeskRefusal} from "../src/api.ts";
import {raw} from "./fixtures.ts";

interface Sent { url: string; init: RequestInit | undefined }

function transport(status: number, body: unknown, sent: Sent[] = []): typeof fetch {
  return (async (url: string | URL | Request, init?: RequestInit) => {
    sent.push({url: String(url), init});
    const text = typeof body === "string" ? body : JSON.stringify(body);
    return new Response(text, {status, headers: {"Content-Type": "application/json"}});
  }) as typeof fetch;
}

const body = {orders: [{unit_id: "U1", stance: "move", destination: [12, 14] as [number, number]}], game_id: "g", revision: 3};

test("state reads the commander view and posts orders as JSON", async () => {
  const sent: Sent[] = [];
  const api = createDeskApi(transport(200, raw("state-commander"), sent));
  const state = await api.state();
  assert.equal(state.side, "union");
  await api.orders(body);
  assert.equal(sent[0]!.url, "/api/state");
  assert.equal(sent[1]!.url, "/api/orders");
  assert.equal(sent[1]!.init?.method, "POST");
  assert.deepEqual(JSON.parse(String(sent[1]!.init?.body)), body);
  assert.equal(new Headers(sent[1]!.init?.headers).get("Content-Type"), "application/json");
});

test("a God view is refused, so the desk cannot draw omniscient state", async () => {
  const api = createDeskApi(transport(200, raw("state-god")));
  await assert.rejects(api.state(), ContractError);
});

test("a server refusal keeps its status and text", async () => {
  for (const [status, text] of [[400, "Unit cannot move there."], [409, "Battle changed. Refresh before issuing another order."]] as const) {
    const api = createDeskApi(transport(status, {error: text}));
    await assert.rejects(api.orders(body), (error: unknown) => {
      assert.ok(error instanceof DeskRefusal);
      assert.equal(error.status, status);
      assert.equal(error.message, text);
      return true;
    });
  }
});

test("a refusal without a JSON error still reports the status", async () => {
  const api = createDeskApi(transport(502, "<html>bad gateway</html>"));
  await assert.rejects(api.state(), (error: unknown) =>
    error instanceof DeskRefusal && error.status === 502 && /502/.test(error.message));
});

test("a relay reply marked outcome unknown is a refusal the desk can tell apart", async () => {
  const unknown = createDeskApi(transport(504, {error: "The local simulation did not answer within 120000 ms.", outcome: "unknown"}));
  await assert.rejects(unknown.orders(body), (error: unknown) =>
    error instanceof DeskRefusal && error.status === 504 && error.outcomeUnknown && /did not answer/.test(error.message));
  const plain = createDeskApi(transport(400, {error: "Choose an available order template."}));
  await assert.rejects(plain.orders(body), (error: unknown) => error instanceof DeskRefusal && !error.outcomeUnknown);
});

test("the scenario catalog is read through its contract, and a new battle posts the chosen id at the cursor", async () => {
  const sent: Sent[] = [];
  const list = await createDeskApi(transport(200, raw("scenarios"), sent)).scenarios();
  // docs/research/75: every recorded scenario passes the contract, in order (the contracts test pins the ids).
  assert.deepEqual(list.scenarios.map((s) => s.id), (raw("scenarios") as {scenarios: {id: string}[]}).scenarios.map((s) => s.id));
  assert.equal(list.scenarios[0]!.id, "little-round-top");
  await assert.rejects(createDeskApi(transport(200, {default: "x", scenarios: []})).scenarios(), ContractError);
  const state = await createDeskApi(transport(200, raw("state-commander"), sent)).newBattle("hougoumont-north-gate", {game_id: "g", revision: 4});
  assert.equal(state.side, "union");
  assert.equal(sent[0]!.url, "/api/scenarios");
  assert.equal(sent[1]!.url, "/api/new");
  assert.deepEqual(JSON.parse(String(sent[1]!.init?.body)), {scenario: "hougoumont-north-gate", game_id: "g", revision: 4});
});

test("an order body that breaks the contract is not sent", async () => {
  const sent: Sent[] = [];
  const api = createDeskApi(transport(200, raw("state-commander"), sent));
  await assert.rejects(api.orders({...body, orders: []}), ContractError);
  assert.equal(sent.length, 0);
});

// docs/research/81 §12: the two command routes, each body checked before it is sent.
test("a standing order and a formation post their checked body; a malformed one is not sent", async () => {
  const sent: Sent[] = [];
  const api = createDeskApi(transport(200, raw("state-commander"), sent));
  const standing = raw("standing-request") as Parameters<typeof api.standingOrder>[0];
  const split = raw("formation-request-split") as Parameters<typeof api.formation>[0];
  assert.equal((await api.standingOrder(standing)).side, "union");
  assert.equal((await api.formation(split)).side, "union");
  assert.deepEqual(sent.map((s) => [s.url, s.init?.method]), [["/api/standing-orders", "POST"], ["/api/formations", "POST"]]);
  assert.deepEqual(JSON.parse(String(sent[0]!.init?.body)), standing);
  assert.deepEqual(JSON.parse(String(sent[1]!.init?.body)), split);
  await assert.rejects(api.standingOrder({...standing, instruction: {...standing.instruction, profile_id: ""}}), ContractError);
  await assert.rejects(api.formation({...split, instruction: {kind: "combine", unit_id: "U2", partner_id: "U2"}}), ContractError);
  assert.equal(sent.length, 2);
});
