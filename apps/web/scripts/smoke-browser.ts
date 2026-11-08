// Browser smoke test for the TypeScript desk (docs/research/70).
// Starts an offline POC on a temporary SQLite file and a free port, the desk
// server on another free port, and a headless Chrome/Chromium in a time zone
// far from the battle's. It clicks a friendly map counter with real pointer
// input, then a hex, then "Send move order", and checks the server accepted the
// order. It then makes the desk's cursor stale and checks the refusal is shown.
//
// Exit 0: passed. Exit 1: failed. Exit 3: BLOCKED, no runnable browser (never a pass).
// Usage: node scripts/smoke-browser.ts   (BATTLE_BROWSER=/path/to/chrome to choose one)
import assert from "node:assert/strict";
import {spawn, type ChildProcess} from "node:child_process";
import {mkdtempSync, writeFileSync} from "node:fs";
import {createServer, request} from "node:http";
import type {AddressInfo} from "node:net";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";
import {createDeskServer, type DeskServer} from "../server/desk-server.ts";
import {findBrowser, launch, Page} from "./cdp.ts";

const POC_DIR = fileURLToPath(new URL("../../poc/", import.meta.url));
const BROWSER_ZONE = "Pacific/Kiritimati";  // UTC+14: a browser-zone shift would move 16:30 to another day
const BLOCKED = 3;
type Doc = Record<string, any>;

function freePort(): Promise<number> {
  return new Promise((done) => {
    const probe = createServer();
    probe.listen(0, "127.0.0.1", () => {
      const {port} = probe.address() as AddressInfo;
      probe.close(() => done(port));
    });
  });
}

// No provider credentials reach the POC; --offline uses the scripted commander.
function cleanEnv(extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {};
  for (const [key, value] of Object.entries(process.env)) if (!/OPENROUTER|API_KEY|TOKEN|SECRET/i.test(key)) env[key] = value;
  return {...env, ...extra};
}

function startPoc(port: number, db: string): Promise<ChildProcess> {
  const child = spawn("python3", ["-m", "battle", "--offline", "--port", String(port), "--db", db],
    {cwd: POC_DIR, env: cleanEnv(), stdio: ["ignore", "pipe", "pipe"]});
  return new Promise((done, failed) => {
    let log = "";
    const timer = setTimeout(() => failed(new Error(`POC not ready in 20 s:\n${log}`)), 20000);
    const read = (chunk: Buffer): void => {
      log += chunk.toString();
      if (log.includes("Battle ready")) { clearTimeout(timer); done(child); }
    };
    child.stdout!.on("data", read);
    child.stderr!.on("data", read);
    child.on("exit", (code) => { clearTimeout(timer); failed(new Error(`POC exited (${code}):\n${log}`)); });
  });
}

// Direct POC calls, as the POC's own host; used only to check and to stale the cursor.
function poc(port: number, path: string, body?: unknown): Promise<Doc> {
  return new Promise((done, failed) => {
    const data = body === undefined ? undefined : JSON.stringify(body);
    const req = request({host: "127.0.0.1", port, path, method: data ? "POST" : "GET",
      headers: {Host: `127.0.0.1:${port}`, ...(data ? {"Content-Type": "application/json"} : {})}}, (res) => {
      let text = "";
      res.on("data", (chunk) => { text += chunk; });
      res.on("end", () => (res.statusCode === 200 ? done(JSON.parse(text)) : failed(new Error(`${path}: ${res.statusCode} ${text}`))));
    });
    req.on("error", failed);
    req.end(data);
  });
}

async function until<T>(what: string, probe: () => Promise<T | null | false>, ms = 15000): Promise<T> {
  const end = Date.now() + ms;
  for (;;) {
    const value = await probe();
    if (value) return value;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await new Promise((done) => setTimeout(done, 100));
  }
}

interface Point { x: number; y: number }
const centre = (selector: string): string => `(() => { const n = document.querySelector(${JSON.stringify(selector)});
  if (!n) return null; const b = n.getBoundingClientRect(); return {x: b.x + b.width / 2, y: b.y + b.height / 2}; })()`;

// A hex whose centre hit-tests to the hex itself (no counter on top), 3 to 6 hexes from `from`.
const openHex = (from: [number, number]): string => `(() => {
  for (const hex of document.querySelectorAll(".hex")) {
    const c = +hex.dataset.c, r = +hex.dataset.r;
    const d = Math.max(Math.abs(c - ${from[0]}), Math.abs(r - ${from[1]}));
    if (d < 3 || d > 6) continue;
    const b = hex.getBoundingClientRect(), x = b.x + b.width / 2, y = b.y + b.height / 2;
    if (document.elementFromPoint(x, y) === hex) return {c, r, x, y};
  }
  return null; })()`;

async function run(page: Page, deskUrl: string, pocPort: number, artifacts: string): Promise<void> {
  await page.send("Page.navigate", {url: deskUrl});
  await until("the desk to load", () => page.evaluate<boolean>("document.documentElement.dataset.deskReady === 'true'"));

  const header = await page.evaluate<Doc>(`({time: document.getElementById("battle-time").textContent,
    date: document.getElementById("battle-date").textContent, location: document.getElementById("battle-location").textContent,
    zone: Intl.DateTimeFormat().resolvedOptions().timeZone, text: document.body.innerText})`);
  assert.equal(header["zone"], BROWSER_ZONE);
  assert.deepEqual([header["time"], header["date"], header["location"]],
    // display_locale "en", as the POC desk formats it.
    ["16:30", "Thursday, July 2, 1863", "Little Round Top · Gettysburg, Pennsylvania"]);
  assert.doesNotMatch(header["text"], /\bturn\b|revision/i, "no turn counter or revision label");

  const before = await poc(pocPort, "/api/state");
  const unit = before["units"].find((u: Doc) => u.status === "ready");
  const drawn = await page.evaluate<Doc>(`({units: [...document.querySelectorAll("[data-unit]")].map(n => n.dataset.unit),
    contacts: [...document.querySelectorAll("[data-contact]")].map(n => n.dataset.contact)})`);
  assert.deepEqual(drawn["units"], before["units"].map((u: Doc) => u.id), "one counter per own unit");
  assert.deepEqual(drawn["contacts"], before["contacts"].map((c: Doc) => c.id), "enemy markers only from contacts");

  // 1. A real click on the friendly counter selects it.
  const counter = await page.evaluate<Point>(centre(`[data-unit="${unit.id}"] rect`));
  const hit = await page.evaluate<string | null>(`document.elementFromPoint(${counter.x}, ${counter.y})?.closest("[data-unit]")?.dataset.unit ?? null`);
  assert.equal(hit, unit.id, "the counter is the element under the pointer");
  await page.click(counter.x, counter.y);
  const selected = await page.evaluate<Doc>(`({cls: document.querySelector('[data-unit="${unit.id}"]').getAttribute("class"),
    pressed: document.querySelector('[data-unit="${unit.id}"]').getAttribute("aria-pressed"),
    text: document.getElementById("selection").textContent})`);
  assert.match(selected["cls"], /\bselected\b/);
  assert.equal(selected["pressed"], "true");
  assert.ok(selected["text"].startsWith(unit.id), selected["text"]);

  // 2. A click on an open hex sets the destination; "Send move order" sends it.
  const target = await until("an open hex", () => page.evaluate<Doc | null>(openHex(unit.pos)));
  await page.click(target["x"], target["y"]);
  await until("the destination mark", () => page.evaluate<boolean>(
    `!!document.querySelector('.hex.destination[data-c="${target["c"]}"][data-r="${target["r"]}"]')`));
  const send = await page.evaluate<Point>(centre("#send-order"));
  await page.click(send.x, send.y);
  const accepted = await until("the order reply", () => page.evaluate<Doc | null>(`(() => { const n = document.getElementById("notice");
    return n.dataset.kind === "info" ? null : {kind: n.dataset.kind, text: n.textContent}; })()`));
  assert.equal(accepted["kind"], "accepted", accepted["text"]);
  const after = await poc(pocPort, "/api/state");
  const order = after["orders"].find((o: Doc) => o.unit_id === unit.id && o.stance === "move");
  assert.ok(order, "the POC holds the move order");
  assert.deepEqual(order.destination, [target["c"], target["r"]]);
  const listed = await page.evaluate<string>(`document.querySelector('[data-order="${order.id}"]')?.textContent ?? ""`);
  assert.match(listed, new RegExp(`^${unit.id} · move → hex ${target["c"]},${target["r"]}`), "the refreshed state shows it");
  const shot = await page.send("Page.captureScreenshot", {format: "png"});
  writeFileSync(join(artifacts, "desk-accepted.png"), Buffer.from(String(shot["data"]), "base64"));
  console.log(`accepted: ${unit.id} move → ${target["c"]},${target["r"]} (${order.id}, ${order.status}); notice: ${accepted["text"]}`);

  // 3. Start the clock from the desk: battlefield time advances on the header; then pause.
  const clockButton = await page.evaluate<Point>(centre("#clock-toggle"));
  await page.click(clockButton.x, clockButton.y);
  const moved = await until("battlefield time to advance", () => page.evaluate<string | null>(
    `(() => { const t = document.getElementById("battle-time").textContent; return t !== "16:30" ? t : null; })()`), 30000);
  await page.click(clockButton.x, clockButton.y);
  await until("the clock to pause", () => page.evaluate<boolean>(`document.getElementById("clock-toggle").textContent === "Start clock"`));
  const settled = await until("the POC to settle", async () => {
    const state = await poc(pocPort, "/api/state");
    return !state["clock"].running && !state["clock"].inflight ? state : null;
  });
  console.log(`clock: header advanced to ${moved}; paused`);

  // 4. The POC moves on without the desk; the desk's next order is refused and the refusal is shown.
  await poc(pocPort, "/api/advance", {game_id: settled["game_id"], revision: settled["revision"]});
  const again = await page.evaluate<Point>(centre(`[data-unit="${unit.id}"] rect`));
  await page.click(again.x, again.y);
  const second = await until("another open hex", () => page.evaluate<Doc | null>(openHex(unit.pos)));
  await page.click(second["x"], second["y"]);
  await page.click(send.x, send.y);
  const refused = await until("the refusal", () => page.evaluate<Doc | null>(`(() => { const n = document.getElementById("notice");
    return n.dataset.kind === "refusal" ? {text: n.textContent} : null; })()`));
  assert.match(refused["text"], /Battle changed/);
  const final = await poc(pocPort, "/api/state");
  assert.equal(final["orders"].length, settled["orders"].length, "the refused order changed nothing");
  console.log(`refused: ${refused["text"]}`);
}

async function main(): Promise<number> {
  const binary = findBrowser();
  if (!binary) {
    console.error("SMOKE BLOCKED: no Chrome/Chromium found (set BATTLE_BROWSER). This is not a pass.");
    return BLOCKED;
  }
  const artifacts = mkdtempSync(join(tmpdir(), "battle-desk-smoke."));
  console.log(`artifacts: ${artifacts}\nbrowser: ${binary}`);
  const [pocPort, deskPort] = [await freePort(), await freePort()];
  let pocProcess: ChildProcess | undefined;
  let desk: DeskServer | undefined;
  let browser: ChildProcess | undefined;
  let page: Page | undefined;
  try {
    pocProcess = await startPoc(pocPort, join(artifacts, "battle.sqlite"));
    desk = await createDeskServer({pocUrl: `http://127.0.0.1:${pocPort}`, port: deskPort});
    let started;
    try {
      started = await launch(binary, join(artifacts, "profile"), cleanEnv({TZ: BROWSER_ZONE}));
    } catch (error) {
      console.error(`SMOKE BLOCKED: the browser did not start (${(error as Error).message}). This is not a pass.`);
      return BLOCKED;
    }
    browser = started.process;
    page = await Page.open(started.endpoint);
    await run(page, desk.url, pocPort, artifacts);
    console.log("SMOKE PASSED: counter click selected the unit; the POC accepted the move order; a stale order's refusal was shown.");
    return 0;
  } catch (error) {
    console.error(`SMOKE FAILED: ${(error as Error).stack ?? error}`);
    return 1;
  } finally {
    page?.close();
    browser?.kill();
    await desk?.close();
    pocProcess?.kill();
  }
}

process.exitCode = await main();
