// The local desk server: serves the TypeScript desk as JavaScript and relays /api to a loopback POC.
import assert from "node:assert/strict";
import {createServer, request, type IncomingHttpHeaders, type Server} from "node:http";
import {mkdirSync, mkdtempSync, readFileSync, writeFileSync} from "node:fs";
import type {AddressInfo} from "node:net";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {after, before, test} from "node:test";
import {createDeskServer, type DeskServer} from "../server/desk-server.ts";

interface Seen { method: string; url: string; headers: IncomingHttpHeaders; body: string }
const seen: Seen[] = [];
let upstream: Server;
let upstreamPort = 0;
let desk: DeskServer;
let behaviour: "normal" | "partial" | "silent" | "late" = "normal";

before(async () => {
  upstream = createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      // #4: a POC that drops the socket mid-body, and one that never answers.
      if (behaviour === "partial") { res.writeHead(200, {"Content-Type": "application/json"}); res.write("{\"ok\":"); req.socket.destroy(); return; }
      if (behaviour === "silent") return;
      seen.push({method: req.method ?? "", url: req.url ?? "", headers: req.headers, body});
      const answer = (): void => {
        res.writeHead(req.url === "/api/orders" ? 409 : 200, {"Content-Type": "application/json"});
        res.end(JSON.stringify(req.url === "/api/orders" ? {error: "Battle changed."} : {ok: true}));
      };
      // A POC that takes the order, then answers after the relay has given up.
      if (behaviour === "late") { setTimeout(answer, 900); return; }
      answer();
    });
  });
  await new Promise<void>((resolve) => upstream.listen(0, "127.0.0.1", resolve));
  upstreamPort = (upstream.address() as AddressInfo).port;
  desk = await createDeskServer({pocUrl: `http://127.0.0.1:${upstreamPort}`, port: 0, relayTimeoutMs: 500});
});

after(async () => {
  await desk.close();
  upstream.closeAllConnections();
  await new Promise<void>((resolve) => upstream.close(() => resolve()));
});

interface Reply { status: number; headers: IncomingHttpHeaders; body: string }

type Options = {method?: string; headers?: Record<string, string>; body?: string | undefined};
const call = (path: string, options: Options = {}): Promise<Reply> => callAt(desk.port, path, options);

function callAt(port: number, path: string, options: Options = {}): Promise<Reply> {
  return new Promise((resolve, reject) => {
    const req = request({host: "127.0.0.1", port, path, method: options.method ?? "GET",
      headers: {Host: `127.0.0.1:${port}`, ...options.headers}}, (res) => {
      let body = "";
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => resolve({status: res.statusCode ?? 0, headers: res.headers, body}));
    });
    req.on("error", reject);
    req.end(options.body);
  });
}

test("the desk page and its modules are served as JavaScript", async () => {
  const page = await call("/");
  assert.equal(page.status, 200);
  assert.match(page.body, /<script type="module" src="\/src\/main.ts">/);
  assert.match(String(page.headers["content-security-policy"]), /connect-src 'self'/);
  const module = await call("/src/api.ts");
  assert.equal(module.status, 200);
  assert.match(String(module.headers["content-type"]), /text\/javascript/);
  assert.doesNotMatch(module.body, /readonly status: number|: Promise<CommanderState>/, "types are stripped");
  assert.match(module.body, /from "\/contracts\/index.ts"/, "the bare contracts import is rewritten");
  const contract = await call("/contracts/map.ts");
  assert.equal(contract.status, 200);
  assert.match(contract.body, /mapDocument/);
});

test("paths outside the desk and contract sources are not served", async () => {
  for (const path of ["/src/../../package.json", "/contracts/../package.json", "/server/desk-server.ts", "/%2e%2e/package.json"]) {
    assert.equal((await call(path)).status, 404, path);
  }
});

test("api requests reach the POC with its own host and origin", async () => {
  seen.length = 0;
  const state = await call("/api/state");
  assert.equal(state.status, 200);
  const order = await call("/api/orders", {method: "POST",
    headers: {"Content-Type": "application/json", Origin: `http://127.0.0.1:${desk.port}`}, body: "{\"orders\":[]}"});
  assert.equal(order.status, 409, "the POC's refusal status is relayed");
  assert.deepEqual(JSON.parse(order.body), {error: "Battle changed."});
  assert.equal(seen[0]!.url, "/api/state");
  assert.equal(seen[0]!.headers.host, `127.0.0.1:${upstreamPort}`);
  assert.equal(seen[1]!.headers.origin, `http://127.0.0.1:${upstreamPort}`);
  assert.equal(seen[1]!.headers["content-type"], "application/json");
  assert.equal(seen[1]!.body, "{\"orders\":[]}");
});

test("a foreign host or origin is refused before the POC sees it", async () => {
  seen.length = 0;
  assert.equal((await call("/api/state", {headers: {Host: "evil.example"}})).status, 403);
  assert.equal((await call("/api/orders", {method: "POST",
    headers: {"Content-Type": "application/json", Origin: "http://evil.example"}, body: "{}"})).status, 403);
  assert.equal(seen.length, 0);
});

test("only a loopback POC can be named", async () => {
  await assert.rejects(createDeskServer({pocUrl: "http://example.com:8874", port: 0}), /loopback/);
  await assert.rejects(createDeskServer({pocUrl: "https://127.0.0.1:8874", port: 0}), /http/);
});

test("a POC that drops the connection mid-reply gets a 502 with an unknown outcome, not a hung request", {timeout: 5000}, async () => {
  behaviour = "partial";
  try {
    const reply = await call("/api/state");
    assert.equal(reply.status, 502);
    const body = JSON.parse(reply.body);
    // A reset may surface as a request error rather than a short reply; both may have reached the POC.
    assert.match(body.error, /not reachable|stopped answering/);
    assert.equal(body.outcome, "unknown");
  } finally { behaviour = "normal"; }
});

test("an unresponsive POC times out with a 504", {timeout: 5000}, async () => {
  behaviour = "silent";
  try {
    const started = Date.now();
    const reply = await call("/api/state");
    assert.equal(reply.status, 504);
    assert.ok(Date.now() - started < 3000, "answered near the 500 ms relay timeout");
  } finally { behaviour = "normal"; }
});

test("a POST that outlives the relay timeout is a 504 whose outcome is unknown", {timeout: 5000}, async () => {
  behaviour = "late";
  seen.length = 0;
  try {
    const reply = await call("/api/orders", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{\"orders\":[]}"});
    assert.equal(reply.status, 504);
    const body = JSON.parse(reply.body);
    assert.equal(body.outcome, "unknown", "the POC may have taken the order");
    assert.match(body.error, /did not answer within 500 ms/);
    assert.equal(seen.length, 1, "the POC did receive the order");
  } finally { behaviour = "normal"; }
});

test("an unreachable POC is a 502 whose outcome is known: nothing was sent", {timeout: 5000}, async () => {
  const probe = createServer();
  await new Promise<void>((resolve) => probe.listen(0, "127.0.0.1", resolve));
  const port = (probe.address() as AddressInfo).port;
  await new Promise<void>((resolve) => probe.close(() => resolve()));
  const lonely = await createDeskServer({pocUrl: `http://127.0.0.1:${port}`, port: 0});
  try {
    const reply = await callAt(lonely.port, "/api/state");
    assert.equal(reply.status, 502);
    const body = JSON.parse(reply.body);
    assert.match(body.error, /not reachable/);
    assert.equal(body.outcome, undefined);
  } finally { await lonely.close(); }
});

test("only the routes the desk uses are relayed; others never reach the POC", async () => {
  seen.length = 0;
  const refused: [string, string, number][] = [
    ["POST", "/api/history", 405], ["POST", "/api/replay", 405], ["POST", "/api/chat", 404],
    ["POST", "/api/advance", 404], ["POST", "/api/mode", 404], ["POST", "/api/recommendations", 404],
    ["GET", "/api/unknown", 404], ["GET", "/api/orders", 405], ["POST", "/api/state", 405],
    ["GET", "/api/standing-orders", 405], ["GET", "/api/formations", 405],
    // docs/research/81 §12: an empty body is not a standing order or formation request.
    ["POST", "/api/standing-orders", 400], ["POST", "/api/formations", 400],
  ];
  for (const [method, path, status] of refused) {
    const reply = await call(path, {method, headers: {"Content-Type": "application/json"}, body: method === "POST" ? "{}" : undefined});
    assert.equal(reply.status, status, `${method} ${path}`);
    assert.ok(JSON.parse(reply.body).error, `${method} ${path} says why`);
  }
  assert.equal(seen.length, 0);
  for (const path of ["/api/state", "/api/map", "/api/scenarios"]) assert.equal((await call(path)).status, 200, path);
  for (const path of ["/api/orders", "/api/clock", "/api/new"]) {
    await call(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
  }
  assert.deepEqual(seen.map((s) => `${s.method} ${s.url}`), [
    "GET /api/state", "GET /api/map", "GET /api/scenarios", "POST /api/orders", "POST /api/clock", "POST /api/new",
  ]);
});

test("a God view or an export is refused with 403 and never relayed", async () => {
  seen.length = 0;
  for (const path of ["/api/state?view=god", "/api/state?view=commander&view=god", "/api/state?VIEW=GOD",
    "/api/map?view=god", "/api/export", "/api/export?game_id=x", "/api/replay?revision=0&view=god", "/api/state?view=%67od"]) {
    const reply = await call(path);
    assert.equal(reply.status, 403, path);
    assert.match(JSON.parse(reply.body).error, /God view|export/i, path);
  }
  const post = await call("/api/orders?view=god", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
  assert.equal(post.status, 403);
  assert.equal(seen.length, 0);
});

// Slice 2 review: the relay forwards the path only on the desk's live routes.
test("the query string is dropped on the desk's live routes", async () => {
  seen.length = 0;
  assert.equal((await call("/api/state?game_id=abc&revision=2&side=confederate&x=1")).status, 200);
  assert.equal((await call("/api/map?game_id=abc")).status, 200);
  await call("/api/orders?revision=9", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
  assert.deepEqual(seen.map((s) => s.url), ["/api/state", "/api/map", "/api/orders"]);
});

// docs/research/73: the commander replay uses the POC's own /api/history and /api/replay.
test("replay and history relay only game_id and revision, so only the player's commander view is replayed", async () => {
  seen.length = 0;
  assert.equal((await call("/api/history?game_id=f1c7f1c7f1c7f1c7")).status, 200);
  assert.equal((await call("/api/replay?revision=3&game_id=f1c7f1c7f1c7f1c7")).status, 200);
  assert.deepEqual(seen.map((s) => s.url), ["/api/history?game_id=f1c7f1c7f1c7f1c7", "/api/replay?game_id=f1c7f1c7f1c7f1c7&revision=3"]);
  seen.length = 0;
  const refused: [string, number, RegExp][] = [
    ["/api/replay?game_id=g1&revision=3&side=confederate", 403, /commander view/],
    ["/api/replay?game_id=g1&revision=3&SIDE=union", 403, /commander view/],
    ["/api/history?game_id=g1&side=union", 403, /commander view/],
    ["/api/replay?game_id=g1&revision=3&view=god", 403, /God view/],
    ["/api/replay?game_id=g1", 400, /revision/],
    ["/api/replay?revision=3", 400, /game_id/],
    ["/api/history", 400, /game_id/],
    ["/api/replay?game_id=g1&revision=-1", 400, /revision/],
    ["/api/replay?game_id=g1&revision=3&revision=4", 400, /revision/],
    ["/api/replay?game_id=..%2Fx&revision=3", 400, /game_id/],
    ["/api/replay?game_id=g1&revision=3&format=full", 400, /game_id and revision/],
  ];
  for (const [path, status, error] of refused) {
    const reply = await call(path);
    assert.equal(reply.status, status, path);
    assert.match(JSON.parse(reply.body).error, error, path);
  }
  assert.equal(seen.length, 0, "a refused replay request never reaches the POC");
});

test("the POC's feature status table is served unchanged, and no other POC file is", async () => {
  const table = await call("/poc/feature-sources.js");
  assert.equal(table.status, 200);
  assert.match(String(table.headers["content-type"]), /text\/javascript/);
  assert.equal(table.body, readFileSync(new URL("../../poc/static/feature-sources.js", import.meta.url), "utf8"));
  for (const path of ["/poc/map-features.js", "/poc/app.js", "/poc/../poc/static/app.js", "/poc/feature-sources.ts"]) {
    assert.equal((await call(path)).status, 404, path);
  }
  assert.match((await call("/")).body, /<script src="\/poc\/feature-sources.js"><\/script>\s*<script type="module"/,
    "the table loads before the desk module");
});

test("a module that exists but fails to load or strip is a 500 with the reason, not a 404", async () => {
  const root = mkdtempSync(join(tmpdir(), "battle-desk-modules."));
  writeFileSync(join(root, "broken.ts"), "enum Side { Union }\nexport const side = Side.Union;\n");
  mkdirSync(join(root, "folder.ts"));
  writeFileSync(join(root, "fine.ts"), "export const n: number = 1;\n");
  const local = await createDeskServer({pocUrl: `http://127.0.0.1:${upstreamPort}`, port: 0, sourceRoots: {"/src/": root}});
  try {
    const broken = await callAt(local.port, "/src/broken.ts");
    assert.equal(broken.status, 500);
    assert.match(JSON.parse(broken.body).error, /broken\.ts could not be served: .*enum|broken\.ts could not be served: .*TypeScript/i);
    const folder = await callAt(local.port, "/src/folder.ts");
    assert.equal(folder.status, 500);
    assert.match(JSON.parse(folder.body).error, /folder\.ts could not be served/);
    assert.equal((await callAt(local.port, "/src/missing.ts")).status, 404);
    const fine = await callAt(local.port, "/src/fine.ts");
    assert.equal(fine.status, 200);
    assert.doesNotMatch(fine.body, /: number/);
  } finally { await local.close(); }
});

const recorded = (name: string): string =>
  readFileSync(new URL(`../../../packages/contracts/fixtures/${name}.json`, import.meta.url), "utf8");

// docs/research/81 §12: the two command routes relay a body only once it passes its contract,
// and the POC receives the checked copy, so nothing outside the contract reaches it.
test("standing orders and formations are relayed only as contract-valid bodies; a malformed one is a 400 never relayed", async () => {
  seen.length = 0;
  const json = {"Content-Type": "application/json"};
  const bodies: [string, string][] = [
    ["/api/standing-orders", recorded("standing-request")],
    ["/api/formations", recorded("formation-request-split")],
    ["/api/formations", recorded("formation-request-combine")],
  ];
  for (const [path, body] of bodies) {
    const reply = await call(path, {method: "POST", headers: json, body});
    assert.equal(reply.status, 200, path);
  }
  assert.deepEqual(seen.map((s) => `${s.method} ${s.url}`),
    ["POST /api/standing-orders", "POST /api/formations", "POST /api/formations"]);
  bodies.forEach(([, body], index) => assert.deepEqual(JSON.parse(seen[index]!.body), JSON.parse(body)));
  seen.length = 0;
  const standing = JSON.parse(recorded("standing-request"));
  const split = JSON.parse(recorded("formation-request-split"));
  const refused: [string, unknown, RegExp][] = [
    ["/api/standing-orders", {...standing, instruction: {...standing.instruction, profile_id: ""}}, /\$\.instruction\.profile_id/],
    ["/api/standing-orders", {...standing, side: "confederate"}, /\$\.side/],
    ["/api/formations", {...split, instruction: {...split.instruction, kind: "merge"}}, /\$\.instruction\.kind/],
    ["/api/formations", {...split, instruction: {...split.instruction, partner_id: "U1"}}, /\$\.instruction\.partner_id/],
    ["/api/formations", "not json", /JSON/],
  ];
  for (const [path, body, error] of refused) {
    const reply = await call(path, {method: "POST", headers: json, body: typeof body === "string" ? body : JSON.stringify(body)});
    assert.equal(reply.status, 400, `${path} ${JSON.stringify(body)}`);
    assert.match(JSON.parse(reply.body).error, error);
    assert.equal(JSON.parse(reply.body).outcome, undefined, "a refused request was never sent, so its outcome is known");
  }
  assert.equal(seen.length, 0, "a malformed command never reaches the POC");
});
