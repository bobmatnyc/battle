// Local server for the TypeScript command desk (docs/research/70, 71).
// Serves apps/web and packages/contracts sources as JavaScript (Node's type
// stripping; no build step, no dependency) and relays /api/* to a loopback POC,
// so the page and the API share one origin. The POC is not changed: the relay
// applies the POC's own Host/Origin rule, then presents the POC's host and origin.
// Only the routes the desk uses are relayed (ROUTES); a God view or an export is refused.
//
// Usage: node server/desk-server.ts [--port 8875] [--poc http://127.0.0.1:8874]
// Needs Node >= 24.2 (`import.meta.main`); `make web` checks it first.
import {readFile} from "node:fs/promises";
import {createServer, request, type IncomingMessage, type ServerResponse} from "node:http";
import {stripTypeScriptTypes} from "node:module";
import type {AddressInfo} from "node:net";
import {resolve, sep} from "node:path";
import {fileURLToPath} from "node:url";

const WEB_ROOT = fileURLToPath(new URL("../", import.meta.url));
const ROOTS: Record<string, string> = {
  "/src/": resolve(WEB_ROOT, "src"),
  "/contracts/": resolve(WEB_ROOT, "../../packages/contracts/src"),
};
const PAGES: Record<string, [string, string]> = {
  "/": [resolve(WEB_ROOT, "index.html"), "text/html; charset=utf-8"],
  "/style.css": [resolve(WEB_ROOT, "style.css"), "text/css; charset=utf-8"],
  // docs/research/73: the POC's presentation-only status table, served unchanged as a classic
  // script; the desk keeps no copy of it. No other POC file is served.
  "/poc/feature-sources.js": [resolve(WEB_ROOT, "../poc/static/feature-sources.js"), "text/javascript; charset=utf-8"],
};
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
  + "connect-src 'self'; frame-ancestors 'none'";
// docs/research/71: a POST can queue behind a commander turn that holds the POC's lock;
// with a reasoning effort the provider may take 90 s (apps/poc config.EFFORT_TIMEOUT).
export const RELAY_TIMEOUT_MS = 120000;
const MAX_BODY = 16000;  // the POC's own request limit
const MODULE_NAME = /^[a-z0-9-]+\.ts$/;

/** The POC routes the desk uses, each with its one method; nothing else is relayed. */
export const ROUTES: Readonly<Record<string, "GET" | "POST">> = Object.freeze({
  "/api/state": "GET", "/api/map": "GET", "/api/scenarios": "GET",
  "/api/orders": "POST", "/api/clock": "POST", "/api/new": "POST",
  "/api/history": "GET", "/api/replay": "GET",
});

/** The query keys relayed per route, each required once; every other route's query is dropped.
 * Replay takes no `side` or `view`, so the POC replays the player's own commander view only. */
export const QUERY_KEYS: Readonly<Record<string, readonly string[]>> = Object.freeze({
  "/api/history": ["game_id"], "/api/replay": ["game_id", "revision"],
});
const QUERY_VALUE: Readonly<Record<string, RegExp>> = {game_id: /^[A-Za-z0-9_-]{1,64}$/, revision: /^\d{1,9}$/};

/** `relayTimeoutMs`: how long a silent POC is waited for before a 504 (default 120 s).
 * `sourceRoots`: URL prefix to source directory; tests point it at a temporary directory. */
export interface DeskServerOptions {
  pocUrl: string; port: number; host?: string; relayTimeoutMs?: number;
  sourceRoots?: Readonly<Record<string, string>>;
}
export interface DeskServer { readonly port: number; readonly url: string; close(): Promise<void> }

function loopback(pocUrl: string): URL {
  const url = new URL(pocUrl);
  if (url.protocol !== "http:") throw new Error(`The POC is served over http, not ${url.protocol}`);
  if (!["127.0.0.1", "localhost"].includes(url.hostname)) throw new Error("The POC must be a loopback address");
  return url;
}

function send(res: ServerResponse, status: number, type: string, data: string | Buffer): void {
  res.writeHead(status, {
    "Content-Type": type, "Content-Length": Buffer.byteLength(data), "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff", "Content-Security-Policy": CSP,
  });
  res.end(data);
}
const sendError = (res: ServerResponse, status: number, error: string, extra: Record<string, string> = {}): void =>
  send(res, status, "application/json", JSON.stringify({error, ...extra}));

/** TypeScript source as a browser module: types stripped, the contracts package mapped to /contracts/. */
async function module(file: string): Promise<string> {
  const source = await readFile(file, "utf8");
  return stripTypeScriptTypes(source).replaceAll("from \"@battle/contracts\"", "from \"/contracts/index.ts\"");
}

// Slice 1 review #4: a missing module is a 404; one that exists but cannot be read
// or stripped is a 500 that names the reason, so the cause is not hidden.
async function serveStatic(path: string, res: ServerResponse, roots: Readonly<Record<string, string>>): Promise<void> {
  const page = PAGES[path];
  if (page) return send(res, 200, page[1], await readFile(page[0]));
  for (const [prefix, root] of Object.entries(roots)) {
    if (!path.startsWith(prefix)) continue;
    const name = path.slice(prefix.length);
    const file = resolve(root, name);
    if (!MODULE_NAME.test(name) || !file.startsWith(resolve(root) + sep)) break;
    try {
      return send(res, 200, "text/javascript; charset=utf-8", await module(file));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") break;
      const reason = error instanceof Error ? error.message : String(error);
      return sendError(res, 500, `${name} could not be served: ${reason}`);
    }
  }
  sendError(res, 404, "Not found.");
}

/** Why: the desk must not become a path to God Mode, an export or a POC route it does not use.
 * What: null when `method` `path` is a desk route and `query` asks for no God view; else the
 * refusal status and text. Query keys and values are compared case-insensitively. On the
 * replay routes a `side` or `view` key is a 403, and the query must be exactly QUERY_KEYS.
 * Test: `only the routes the desk uses are relayed; others never reach the POC`,
 * `a God view or an export is refused with 403 and never relayed`,
 * `replay and history relay only game_id and revision, so only the player's commander view is replayed`. */
export function relayRefusal(method: string, path: string, query: URLSearchParams): [number, string] | null {
  const god = [...query].some(([key, value]) =>
    value.toLowerCase() === "god" || (key.toLowerCase() === "view" && value.toLowerCase() !== "commander"));
  if (god) return [403, "The desk shows the commander view only; a God view is refused."];
  if (/export/i.test(path)) return [403, "The desk does not export battles."];
  const allowed = ROUTES[path];
  if (!allowed) return [404, "The desk does not use this route."];
  if (allowed !== method) return [405, "Method not allowed."];
  const keys = QUERY_KEYS[path];
  if (!keys) return null;
  for (const key of new Set(query.keys())) {
    if (["side", "view"].includes(key.toLowerCase())) {
      return [403, "The desk replays the player's commander view only; another side's view is refused."];
    }
    if (!keys.includes(key)) return [400, `The desk relays only ${keys.join(" and ")} on ${path}.`];
  }
  for (const key of keys) {
    const values = query.getAll(key);
    if (values.length !== 1 || !QUERY_VALUE[key]!.test(values[0]!)) return [400, `${path} needs one valid ${key}.`];
  }
  return null;
}

/** The request the POC receives: the path, plus only the route's own query keys (QUERY_KEYS). */
export function relayTarget(path: string, query: URLSearchParams): string {
  const keys = QUERY_KEYS[path];
  return keys ? `${path}?${new URLSearchParams(keys.map((key) => [key, query.get(key) ?? ""]))}` : path;
}

function readBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((done, failed) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > MAX_BODY) { failed(new Error("Request too large.")); req.destroy(); return; }
      chunks.push(chunk);
    });
    req.on("end", () => done(Buffer.concat(chunks)));
    req.on("error", failed);
  });
}

// Every relay ends in one answer: the POC's reply, a 502 when the POC is unreachable or
// drops the connection mid-reply, or a 504 when it is silent for `timeoutMs`. When the
// request may have reached the POC the body says `outcome: "unknown"`, so the desk
// re-reads state rather than report a plain failure (docs/research/71, review #6).
// `path` is relayTarget's: the path, plus game_id and revision on the replay routes only.
async function relay(poc: URL, path: string, req: IncomingMessage, res: ServerResponse, timeoutMs: number): Promise<void> {
  const payload = req.method === "POST" ? await readBody(req) : Buffer.alloc(0);
  const headers: Record<string, string> = {Host: poc.host};
  if (req.headers.origin) headers["Origin"] = poc.origin;
  if (req.headers["content-type"]) headers["Content-Type"] = req.headers["content-type"];
  if (req.method === "POST") headers["Content-Length"] = String(payload.length);
  await new Promise<void>((done) => {
    let settled = false;
    const finish = (answer: () => void): void => {
      if (settled) return;
      settled = true;
      answer();
      done();
    };
    const fail = (error: string, status = 502, unknown = true): void => finish(() => {
      if (res.headersSent) res.destroy(); else sendError(res, status, error, unknown ? {outcome: "unknown"} : {});
    });
    const dropped = `The local simulation at ${poc.origin} stopped answering mid-reply.`;
    const upstream = request({hostname: poc.hostname, port: poc.port, path, method: req.method, headers}, (reply) => {
      const chunks: Buffer[] = [];
      reply.on("data", (chunk: Buffer) => chunks.push(chunk));
      reply.on("end", () => finish(() => send(res, reply.statusCode ?? 502,
        String(reply.headers["content-type"] ?? "application/json"), Buffer.concat(chunks))));
      reply.on("error", () => fail(dropped));
      reply.on("close", () => { if (!reply.complete) fail(dropped); });
    });
    upstream.setTimeout(timeoutMs, () => {
      fail(`The local simulation at ${poc.origin} did not answer within ${timeoutMs} ms.`, 504);
      upstream.destroy();
    });
    upstream.on("error", (error: NodeJS.ErrnoException) => {
      // A refused connection carried nothing to the POC; any other error may have.
      fail(`The local simulation is not reachable at ${poc.origin}.`, 502, error.code !== "ECONNREFUSED");
    });
    upstream.end(payload);
  });
}

/** Why: the POC accepts only its own Host and Origin and sends no CORS headers, so the
 * desk must be same-origin with the API without the POC changing.
 * What: an http server on 127.0.0.1 serving the desk and relaying the desk's ROUTES to `pocUrl`;
 * a request whose Host or Origin is not this server's is refused with 403 and not relayed, and
 * so is a God view or export; another /api route is a 404. A POC that drops a reply gets a 502,
 * one silent past `relayTimeoutMs` a 504 (a closed connection once headers are sent).
 * Test: `api requests reach the POC with its own host and origin`, `a foreign host or origin is refused before the POC sees it`,
 * `a POC that drops the connection mid-reply gets a 502 with an unknown outcome, not a hung request`,
 * `a POST that outlives the relay timeout is a 504 whose outcome is unknown`,
 * `a module that exists but fails to load or strip is a 500 with the reason, not a 404`. */
export async function createDeskServer(options: DeskServerOptions): Promise<DeskServer> {
  const poc = loopback(options.pocUrl);
  let port = options.port;
  const allowed = (): Set<string> => new Set([`127.0.0.1:${port}`, `localhost:${port}`]);
  const server = createServer((req, res) => {
    const hosts = allowed();
    const origin = req.headers.origin;
    if (!hosts.has(req.headers.host ?? "") || (origin && ![...hosts].some((h) => origin === `http://${h}`))) {
      return sendError(res, 403, "Local access only.");
    }
    const url = new URL(req.url ?? "/", "http://desk.invalid");
    const path = url.pathname;
    const api = path.startsWith("/api/");
    const refusal = api ? relayRefusal(req.method ?? "", path, url.searchParams) : null;
    if (refusal) return sendError(res, refusal[0], refusal[1]);
    const work = api ? relay(poc, relayTarget(path, url.searchParams), req, res, options.relayTimeoutMs ?? RELAY_TIMEOUT_MS)
      : req.method === "GET" ? serveStatic(path, res, options.sourceRoots ?? ROOTS)
        : Promise.resolve(sendError(res, 405, "Method not allowed."));
    work.catch((error: unknown) => {
      if (!res.headersSent) sendError(res, 400, error instanceof Error ? error.message : "Invalid request.");
    });
  });
  await new Promise<void>((done, failed) => {
    server.once("error", failed);
    server.listen(options.port, options.host ?? "127.0.0.1", () => done());
  });
  port = (server.address() as AddressInfo).port;
  return {
    port, url: `http://127.0.0.1:${port}/`,
    close: () => new Promise<void>((done) => { server.closeAllConnections(); server.close(() => done()); }),
  };
}

function option(name: string, fallback: string): string {
  const index = process.argv.indexOf(name);
  return index > 0 && process.argv[index + 1] ? process.argv[index + 1]! : fallback;
}

// Review #5: before Node 24.2 `import.meta.main` is undefined, and the server would exit 0
// without serving. Say so and fail instead.
if (import.meta.main === undefined) {
  console.error(`The desk server needs Node >= 24.2 (import.meta.main); this is Node ${process.versions.node}.`);
  process.exit(1);
}
if (import.meta.main) {
  const desk = await createDeskServer({pocUrl: option("--poc", "http://127.0.0.1:8874"), port: Number(option("--port", "8875"))});
  console.log(`TypeScript desk: ${desk.url} (POC ${option("--poc", "http://127.0.0.1:8874")})`);
}
