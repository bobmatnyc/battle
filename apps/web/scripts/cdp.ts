// A minimal Chrome DevTools Protocol client over Node's built-in WebSocket.
// Enough for the desk smoke test: one page session, evaluate, mouse input.
import {spawn, type ChildProcess} from "node:child_process";
import {existsSync, readdirSync} from "node:fs";
import {homedir} from "node:os";
import {join} from "node:path";
import {ChildFailure, stop, waitForOutput} from "./smoke-support.ts";

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

/** Why: a browser that never opens DevTools, or a run interrupted while it starts, must not
 * leave the browser running (slice 1 #2; bt-T07 fix round #3).
 * What: starts a headless browser with its own profile in its own process group and hands it to
 * `register` before waiting, so the caller's cleanup can stop it at any time. When `register`
 * returns false (cleanup has begun), the group is stopped and launch rejects. Resolves with the
 * DevTools endpoint, else stops the group and rejects with ChildFailure (its `pid`).
 * Test: `a browser that gives no DevTools endpoint is killed and launch rejects`,
 * `launch registers the browser before it waits, so cleanup can stop its group mid-launch`,
 * `launch refuses to start a browser once cleanup has begun`. */
export async function launch(binary: string, profile: string, env: NodeJS.ProcessEnv, timeoutMs = 20000,
  register: (child: ChildProcess) => boolean = () => true): Promise<Browser> {
  const child = spawn(binary, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
    "--window-size=1400,1000", "about:blank",
    // Its own process group, so `stop(child, {group: true})` also ends its helper processes.
  ], {env, stdio: ["ignore", "ignore", "pipe"], detached: true});
  if (!register(child)) {
    await stop(child, {group: true});
    throw new ChildFailure("browser launch refused: cleanup has begun", child.pid);
  }
  try {
    const found = await waitForOutput(child, /DevTools listening on (ws:\/\/\S+)/, timeoutMs, "browser");
    return {process: child, endpoint: found[1]!};
  } catch (error) {
    await stop(child, {group: true});  // waitForOutput stopped the main process; end its helpers too
    if (error instanceof ChildFailure && /not ready/.test(error.message)) {
      throw new ChildFailure(`browser gave no DevTools endpoint in ${timeoutMs} ms`, error.pid);
    }
    throw error;
  }
}

/** The part of a WebSocket the page client uses; a test passes a fake. */
export interface SocketLike {
  addEventListener(type: string, listener: (event: Event) => void): void;
  send(data: string): void;
  close(): void;
}

/** One attached page: `send` a CDP method in the page session. */
export class Page {
  private next = 1;
  private readonly waiting = new Map<number, {done: (r: Params) => void; failed: (e: Error) => void}>();
  private readonly socket: SocketLike;
  private sessionId: string | undefined;
  private closed = false;
  // No parameter properties: Node's type stripping cannot erase them.
  private constructor(socket: SocketLike) {
    this.socket = socket;
    socket.addEventListener("message", (event) => {
      const reply = JSON.parse(String((event as MessageEvent).data)) as Reply;
      const entry = reply.id === undefined ? undefined : this.waiting.get(reply.id);
      if (!entry || reply.id === undefined) return;
      this.waiting.delete(reply.id);
      if (reply.error) entry.failed(new Error(reply.error.message)); else entry.done(reply.result ?? {});
    });
    // #3: a browser that dies mid-run closes the socket; every pending call fails instead of waiting for ever.
    const lost = (): void => {
      this.closed = true;
      for (const entry of this.waiting.values()) entry.failed(new Error("DevTools connection closed"));
      this.waiting.clear();
    };
    socket.addEventListener("close", lost);
    socket.addEventListener("error", lost);
  }

  /** A page client on an open socket and session; `open` uses it, and so do tests with a fake socket.
   * Test: `pending DevTools calls reject when the socket closes, and later calls reject at once`. */
  static attach(socket: SocketLike, sessionId?: string): Page {
    const page = new Page(socket);
    page.sessionId = sessionId;
    return page;
  }

  static async open(endpoint: string): Promise<Page> {
    const socket = new WebSocket(endpoint);
    await new Promise<void>((done, failed) => {
      socket.addEventListener("open", () => done(), {once: true});
      socket.addEventListener("error", () => failed(new Error("could not open the DevTools socket")), {once: true});
    });
    const page = Page.attach(socket);
    const {targetId} = await page.send("Target.createTarget", {url: "about:blank"});
    const {sessionId} = await page.send("Target.attachToTarget", {targetId, flatten: true});
    page.sessionId = String(sessionId);
    return page;
  }

  send(method: string, params: Params = {}): Promise<Params> {
    const id = this.next++;
    if (this.closed) return Promise.reject(new Error("DevTools connection closed"));
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
