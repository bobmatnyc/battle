// A minimal Chrome DevTools Protocol client over Node's built-in WebSocket.
// Enough for the desk smoke test: one page session, evaluate, mouse input.
import {spawn, type ChildProcess} from "node:child_process";
import {existsSync, readdirSync} from "node:fs";
import {homedir} from "node:os";
import {join} from "node:path";

type Params = Record<string, unknown>;
interface Reply { id?: number; result?: Params; error?: {message: string}; method?: string; sessionId?: string }

/** A browser binary: $BATTLE_BROWSER, an installed Chrome/Chromium, or a Playwright Chromium. */
export function findBrowser(): string | null {
  const named = process.env["BATTLE_BROWSER"];
  if (named) return existsSync(named) ? named : null;
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
  ];
  const playwright = join(homedir(), "Library/Caches/ms-playwright");
  if (existsSync(playwright)) {
    for (const dir of readdirSync(playwright).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse()) {
      for (const sub of ["chrome-mac-arm64", "chrome-mac"]) {
        candidates.push(join(playwright, dir, sub, "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"));
        candidates.push(join(playwright, dir, sub, "Chromium.app/Contents/MacOS/Chromium"));
      }
    }
  }
  return candidates.find((path) => existsSync(path)) ?? null;
}

export interface Browser { process: ChildProcess; endpoint: string }

/** Starts a headless browser with its own profile; resolves with its DevTools endpoint. */
export function launch(binary: string, profile: string, env: NodeJS.ProcessEnv, timeoutMs = 20000): Promise<Browser> {
  const child = spawn(binary, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
    "--window-size=1400,1000", "about:blank",
  ], {env, stdio: ["ignore", "ignore", "pipe"]});
  return new Promise((done, failed) => {
    let log = "";
    const timer = setTimeout(() => failed(new Error(`browser gave no DevTools endpoint in ${timeoutMs} ms`)), timeoutMs);
    child.stderr!.on("data", (chunk: Buffer) => {
      log += chunk.toString();
      const found = /DevTools listening on (ws:\/\/\S+)/.exec(log);
      if (found) { clearTimeout(timer); done({process: child, endpoint: found[1]!}); }
    });
    child.on("exit", (code) => { clearTimeout(timer); failed(new Error(`browser exited (${code}) before DevTools started`)); });
  });
}

/** One attached page: `send` a CDP method in the page session. */
export class Page {
  private next = 1;
  private readonly waiting = new Map<number, {done: (r: Params) => void; failed: (e: Error) => void}>();
  private readonly socket: WebSocket;
  private sessionId: string | undefined;
  // No parameter properties: Node's type stripping cannot erase them.
  private constructor(socket: WebSocket) {
    this.socket = socket;
    socket.addEventListener("message", (event) => {
      const reply = JSON.parse(String(event.data)) as Reply;
      const entry = reply.id === undefined ? undefined : this.waiting.get(reply.id);
      if (!entry || reply.id === undefined) return;
      this.waiting.delete(reply.id);
      if (reply.error) entry.failed(new Error(reply.error.message)); else entry.done(reply.result ?? {});
    });
  }

  static async open(endpoint: string): Promise<Page> {
    const socket = new WebSocket(endpoint);
    await new Promise<void>((done, failed) => {
      socket.addEventListener("open", () => done(), {once: true});
      socket.addEventListener("error", () => failed(new Error("could not open the DevTools socket")), {once: true});
    });
    const page = new Page(socket);
    const {targetId} = await page.send("Target.createTarget", {url: "about:blank"});
    const {sessionId} = await page.send("Target.attachToTarget", {targetId, flatten: true});
    page.sessionId = String(sessionId);
    return page;
  }

  send(method: string, params: Params = {}): Promise<Params> {
    const id = this.next++;
    return new Promise((done, failed) => {
      this.waiting.set(id, {done, failed});
      this.socket.send(JSON.stringify({id, method, params, ...(this.sessionId ? {sessionId: this.sessionId} : {})}));
    });
  }

  /** Evaluates `expression` in the page and returns its JSON value. */
  async evaluate<T>(expression: string): Promise<T> {
    const reply = await this.send("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    const details = reply["exceptionDetails"] as {text?: string; exception?: {description?: string}} | undefined;
    if (details) throw new Error(`page error: ${details.exception?.description ?? details.text}`);
    return (reply["result"] as {value: T}).value;
  }

  /** A real pointer click at viewport point (x, y): the browser hit-tests it like a user's. */
  async click(x: number, y: number): Promise<void> {
    await this.send("Input.dispatchMouseEvent", {type: "mouseMoved", x, y});
    await this.send("Input.dispatchMouseEvent", {type: "mousePressed", x, y, button: "left", clickCount: 1});
    await this.send("Input.dispatchMouseEvent", {type: "mouseReleased", x, y, button: "left", clickCount: 1});
  }

  close(): void { this.socket.close(); }
}
