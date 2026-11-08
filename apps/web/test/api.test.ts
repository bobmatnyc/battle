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

test("an order body that breaks the contract is not sent", async () => {
  const sent: Sent[] = [];
  const api = createDeskApi(transport(200, raw("state-commander"), sent));
  await assert.rejects(api.orders({...body, orders: []}), ContractError);
  assert.equal(sent.length, 0);
});
