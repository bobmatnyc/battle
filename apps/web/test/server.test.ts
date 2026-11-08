// The local desk server: serves the TypeScript desk as JavaScript and relays /api to a loopback POC.
import assert from "node:assert/strict";
import {createServer, request, type IncomingHttpHeaders, type Server} from "node:http";
import type {AddressInfo} from "node:net";
import {after, before, test} from "node:test";
import {createDeskServer, type DeskServer} from "../server/desk-server.ts";

interface Seen { method: string; url: string; headers: IncomingHttpHeaders; body: string }
const seen: Seen[] = [];
let upstream: Server;
let upstreamPort = 0;
let desk: DeskServer;

before(async () => {
  upstream = createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      seen.push({method: req.method ?? "", url: req.url ?? "", headers: req.headers, body});
      res.writeHead(req.url === "/api/orders" ? 409 : 200, {"Content-Type": "application/json"});
      res.end(JSON.stringify(req.url === "/api/orders" ? {error: "Battle changed."} : {ok: true}));
    });
  });
  await new Promise<void>((resolve) => upstream.listen(0, "127.0.0.1", resolve));
  upstreamPort = (upstream.address() as AddressInfo).port;
  desk = await createDeskServer({pocUrl: `http://127.0.0.1:${upstreamPort}`, port: 0});
});

after(async () => {
  await desk.close();
  await new Promise<void>((resolve) => upstream.close(() => resolve()));
});

interface Reply { status: number; headers: IncomingHttpHeaders; body: string }

function call(path: string, options: {method?: string; headers?: Record<string, string>; body?: string} = {}): Promise<Reply> {
  return new Promise((resolve, reject) => {
    const req = request({host: "127.0.0.1", port: desk.port, path, method: options.method ?? "GET",
      headers: {Host: `127.0.0.1:${desk.port}`, ...options.headers}}, (res) => {
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
  const module = await call("/src/timeline.ts");
  assert.equal(module.status, 200);
  assert.match(String(module.headers["content-type"]), /text\/javascript/);
  assert.doesNotMatch(module.body, /: BattleSetting/);
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
  const state = await call("/api/state?view=commander");
  assert.equal(state.status, 200);
  const order = await call("/api/orders", {method: "POST",
    headers: {"Content-Type": "application/json", Origin: `http://127.0.0.1:${desk.port}`}, body: "{\"orders\":[]}"});
  assert.equal(order.status, 409, "the POC's refusal status is relayed");
  assert.deepEqual(JSON.parse(order.body), {error: "Battle changed."});
  assert.equal(seen[0]!.url, "/api/state?view=commander");
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
