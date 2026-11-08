// Local server for the TypeScript command desk (docs/research/70).
// Serves apps/web and packages/contracts sources as JavaScript (Node's type
// stripping; no build step, no dependency) and relays /api/* to a loopback POC,
// so the page and the API share one origin. The POC is not changed: the relay
// applies the POC's own Host/Origin rule, then presents the POC's host and origin.
//
// Usage: node server/desk-server.ts [--port 8875] [--poc http://127.0.0.1:8874]
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
};
const CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
  + "connect-src 'self'; frame-ancestors 'none'";
const MAX_BODY = 16000;  // the POC's own request limit
const MODULE_NAME = /^[a-z0-9-]+\.ts$/;

export interface DeskServerOptions { pocUrl: string; port: number; host?: string }
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
const sendError = (res: ServerResponse, status: number, error: string): void =>
  send(res, status, "application/json", JSON.stringify({error}));

/** TypeScript source as a browser module: types stripped, the contracts package mapped to /contracts/. */
async function module(file: string): Promise<string> {
  const source = await readFile(file, "utf8");
  return stripTypeScriptTypes(source).replaceAll("from \"@battle/contracts\"", "from \"/contracts/index.ts\"");
}

async function serveStatic(path: string, res: ServerResponse): Promise<void> {
  const page = PAGES[path];
  if (page) return send(res, 200, page[1], await readFile(page[0]));
  for (const [prefix, root] of Object.entries(ROOTS)) {
    if (!path.startsWith(prefix)) continue;
    const name = path.slice(prefix.length);
    const file = resolve(root, name);
    if (!MODULE_NAME.test(name) || !file.startsWith(root + sep)) break;
    try {
      return send(res, 200, "text/javascript; charset=utf-8", await module(file));
    } catch {
      break;
    }
  }
  sendError(res, 404, "Not found.");
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

async function relay(poc: URL, req: IncomingMessage, res: ServerResponse): Promise<void> {
  const payload = req.method === "POST" ? await readBody(req) : Buffer.alloc(0);
  const headers: Record<string, string> = {Host: poc.host};
  if (req.headers.origin) headers["Origin"] = poc.origin;
  if (req.headers["content-type"]) headers["Content-Type"] = req.headers["content-type"];
  if (req.method === "POST") headers["Content-Length"] = String(payload.length);
  await new Promise<void>((done) => {
    const upstream = request({hostname: poc.hostname, port: poc.port, path: req.url, method: req.method, headers}, (reply) => {
      const chunks: Buffer[] = [];
      reply.on("data", (chunk: Buffer) => chunks.push(chunk));
      reply.on("end", () => {
        send(res, reply.statusCode ?? 502, String(reply.headers["content-type"] ?? "application/json"), Buffer.concat(chunks));
        done();
      });
    });
    upstream.on("error", () => {
      sendError(res, 502, `The local simulation is not reachable at ${poc.origin}.`);
      done();
    });
    upstream.end(payload);
  });
}

/** Why: the POC accepts only its own Host and Origin and sends no CORS headers, so the
 * desk must be same-origin with the API without the POC changing.
 * What: an http server on 127.0.0.1 serving the desk and relaying /api/* to `pocUrl`;
 * a request whose Host or Origin is not this server's is refused with 403 and not relayed.
 * Test: `api requests reach the POC with its own host and origin`, `a foreign host or origin is refused before the POC sees it`. */
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
    const path = new URL(req.url ?? "/", "http://desk.invalid").pathname;
    const work = path.startsWith("/api/") ? relay(poc, req, res)
      : req.method === "GET" ? serveStatic(path, res) : Promise.resolve(sendError(res, 405, "Method not allowed."));
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

if (import.meta.main) {
  const desk = await createDeskServer({pocUrl: option("--poc", "http://127.0.0.1:8874"), port: Number(option("--port", "8875"))});
  console.log(`TypeScript desk: ${desk.url} (POC ${option("--poc", "http://127.0.0.1:8874")})`);
}
