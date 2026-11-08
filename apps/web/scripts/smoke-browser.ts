// Browser smoke test for the TypeScript desk (docs/research/70, 71).
// Starts an offline POC on a temporary SQLite file and a free port, the desk
// server on another free port, and a headless Chrome/Chromium in a time zone
// far from the battle's. With real pointer input it selects a counter and reads
// its unit card, sends a move and a non-move order, sees refusals carry the
// server's text, runs the clock, then switches to Hougoumont and checks the
// header, counters, unit card and a Hougoumont-only order.
//
// Exit 0: passed. Exit 1: failed (also when the overall deadline passes). Exit 3:
// BLOCKED, no runnable browser (never a pass).
// Usage: node scripts/smoke-browser.ts   (BATTLE_BROWSER=/path/to/chrome to choose one)
// Forcing a failure: SMOKE_POC_READY=<text the POC never prints>, SMOKE_READY_MS, SMOKE_BROWSER_MS,
// SMOKE_DEADLINE_MS (the whole run), SMOKE_FREEZE_BROWSER=1 (SIGSTOP the browser once its
// page is open: it stops answering with its socket open).
// Every exit path stops the POC and the browser group, and removes the browser profile;
// the artifacts directory keeps only the screenshots and the SQLite file.
import assert from "node:assert/strict";
import {spawn, type ChildProcess} from "node:child_process";
import {mkdtempSync, readdirSync, writeFileSync} from "node:fs";
import {createServer} from "node:http";
import type {AddressInfo} from "node:net";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";
import {createDeskServer, type DeskServer} from "../server/desk-server.ts";
import {findBrowser, launch, Page} from "./cdp.ts";
import {pocRequest, removeDir, stop, waitForOutput, withDeadline} from "./smoke-support.ts";

const POC_DIR = fileURLToPath(new URL("../../poc/", import.meta.url));
const BROWSER_ZONE = "Pacific/Kiritimati";  // UTC+14: a browser-zone shift would move 16:30 to another day
const BLOCKED = 3;
const HOUGOUMONT = "hougoumont-north-gate";
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

// Overrides exist to force the failure paths (docs/research/70, 71).
const POC_READY = new RegExp(process.env["SMOKE_POC_READY"] ?? "Battle ready");
const READY_MS = Number(process.env["SMOKE_READY_MS"] ?? 20000);
const DEADLINE_MS = Number(process.env["SMOKE_DEADLINE_MS"] ?? 240000);
const FREEZE = process.env["SMOKE_FREEZE_BROWSER"] === "1";

function spawnPoc(port: number, db: string): ChildProcess {
  return spawn("python3", ["-m", "battle", "--offline", "--port", String(port), "--db", db],
    {cwd: POC_DIR, env: cleanEnv(), stdio: ["ignore", "pipe", "pipe"]});
}

// Direct POC calls, as the POC's own host; used only to check, to stale the cursor and to run the clock elsewhere.
const poc = (port: number, path: string, body?: unknown): Promise<Doc> => pocRequest(port, path, body);

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

async function clickOn(page: Page, selector: string): Promise<void> {
  const point = await until(selector, () => page.evaluate<Point | null>(centre(selector)));
  await page.click(point.x, point.y);
}

// A real click on the counter: the counter must be the element under the pointer.
async function selectUnit(page: Page, id: string): Promise<void> {
  const point = await until(`counter ${id}`, () => page.evaluate<Point | null>(centre(`[data-unit="${id}"] rect`)));
  const hit = await page.evaluate<string | null>(`document.elementFromPoint(${point.x}, ${point.y})?.closest("[data-unit]")?.dataset.unit ?? null`);
  assert.equal(hit, id, "the counter is the element under the pointer");
  await page.click(point.x, point.y);
  await until(`${id} selected`, () => page.evaluate<boolean>(
    `document.querySelector('[data-unit="${id}"]')?.getAttribute("aria-pressed") === "true"`));
}

// A <select> choice, as the browser's own change event (headless Chrome draws no native list to click).
async function choose(page: Page, id: string, value: string): Promise<void> {
  const ok = await page.evaluate<boolean>(`(() => { const s = document.getElementById(${JSON.stringify(id)});
    if (![...s.options].some(o => o.value === ${JSON.stringify(value)})) return false;
    s.value = ${JSON.stringify(value)}; s.dispatchEvent(new Event("change", {bubbles: true})); return true; })()`);
  assert.ok(ok, `#${id} offers ${value}`);
}

// The next notice that is not plain info and differs from `before`.
async function nextNotice(page: Page, before: string, ms = 15000): Promise<Doc> {
  return until("a desk notice", () => page.evaluate<Doc | null>(`(() => { const n = document.getElementById("notice");
    return n.dataset.kind !== "info" && n.textContent !== ${JSON.stringify(before)} ? {kind: n.dataset.kind, text: n.textContent} : null; })()`), ms);
}
const noticeText = (page: Page): Promise<string> => page.evaluate<string>(`document.getElementById("notice").textContent`);

async function header(page: Page): Promise<Doc> {
  return page.evaluate<Doc>(`({time: document.getElementById("battle-time").textContent,
    date: document.getElementById("battle-date").textContent, location: document.getElementById("battle-location").textContent,
    title: document.getElementById("title").textContent, zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    text: document.body.innerText})`);
}

// The unit card's fields against the POC's own commander view of that unit.
async function checkCard(page: Page, unit: Doc): Promise<string> {
  const card = await until("the unit card", () => page.evaluate<Doc | null>(`(() => {
    const out = {}; for (const n of document.querySelectorAll("#unit-card [data-field]")) out[n.dataset.field] = n.querySelector("dd").textContent;
    return Object.keys(out).length ? {...out, title: document.getElementById("unit-title")?.textContent} : null; })()`));
  assert.equal(card["title"], `${unit["id"]} · ${unit["name"]}`);
  assert.equal(card["strength"], `${unit["strength"]} / ${unit["initial"]}`);
  assert.equal(card["morale"], `${unit["morale"]}%`);
  assert.equal(card["ammo"], String(unit["ammo"]));
  assert.equal(card["energy"], `${100 - unit["fatigue"]}%`);
  assert.equal(card["status"], unit["status"]);
  return `${card["title"]}: strength ${card["strength"]}, morale ${card["morale"]}, ammunition ${card["ammo"]}, energy ${card["energy"]}, posture ${card["posture"]}, mission ${card["mission"]}`;
}

async function screenshot(page: Page, artifacts: string, name: string): Promise<void> {
  const shot = await page.send("Page.captureScreenshot", {format: "png"});
  writeFileSync(join(artifacts, name), Buffer.from(String(shot["data"]), "base64"));
}

async function littleRoundTop(page: Page, pocPort: number, artifacts: string): Promise<void> {
  const head = await header(page);
  assert.equal(head["zone"], BROWSER_ZONE);
  // display_locale "en", as the POC desk formats it.
  assert.deepEqual([head["time"], head["date"], head["location"]],
    ["16:30", "Thursday, July 2, 1863", "Little Round Top · Gettysburg, Pennsylvania"]);
  assert.doesNotMatch(head["text"], /\bturn\b|revision/i, "no turn counter or revision label");

  const before = await poc(pocPort, "/api/state");
  const unit = before["units"].find((u: Doc) => u.status === "ready");
  const drawn = await page.evaluate<Doc>(`({units: [...document.querySelectorAll("[data-unit]")].map(n => n.dataset.unit),
    contacts: [...document.querySelectorAll("[data-contact]")].map(n => n.dataset.contact),
    kinds: [...document.getElementById("order-kind").options].map(o => o.value)})`);
  assert.deepEqual(drawn["units"], before["units"].map((u: Doc) => u.id), "one counter per own unit");
  assert.deepEqual(drawn["contacts"], before["contacts"].map((c: Doc) => c.id), "enemy markers only from contacts");
  assert.deepEqual(drawn["kinds"], before["order_templates"].map((t: Doc) => t.id), "the POC's whole order catalog");

  // 1. A real click on the friendly counter selects it and shows its unit card.
  await selectUnit(page, unit.id);
  console.log(`unit card: ${await checkCard(page, unit)}`);

  // 2. Move: a click on an open hex sets the destination; "Send order" sends it.
  await choose(page, "order-kind", "move");
  const target = await until("an open hex", () => page.evaluate<Doc | null>(openHex(unit.pos)));
  await page.click(target["x"], target["y"]);
  await until("the destination mark", () => page.evaluate<boolean>(
    `!!document.querySelector('.hex.destination[data-c="${target["c"]}"][data-r="${target["r"]}"]')`));
  await clickOn(page, "#send-order");
  const accepted = await nextNotice(page, "");
  assert.equal(accepted["kind"], "accepted", accepted["text"]);
  let state = await poc(pocPort, "/api/state");
  const order = state["orders"].find((o: Doc) => o.unit_id === unit.id && o.stance === "move");
  assert.ok(order, "the POC holds the move order");
  assert.deepEqual(order.destination, [target["c"], target["r"]]);
  const listed = await page.evaluate<string>(`document.querySelector('[data-order="${order.id}"]')?.textContent ?? ""`);
  assert.match(listed, new RegExp(`^${unit.id} · move → hex ${target["c"]},${target["r"]}`), "the refreshed state shows it");
  console.log(`accepted: ${unit.id} move → ${target["c"]},${target["r"]} (${order.id}, ${order.status}); notice: ${accepted["text"]}`);

  // 3. A non-move order: Hold fire, a posture with no destination.
  await choose(page, "order-kind", "hold_fire");
  await clickOn(page, "#send-order");
  const posture = await nextNotice(page, accepted["text"]);
  assert.equal(posture["kind"], "accepted", posture["text"]);
  state = await poc(pocPort, "/api/state");
  const held = state["orders"].find((o: Doc) => o.unit_id === unit.id && o.stance === "hold_fire");
  assert.ok(held, "the POC holds the hold_fire order");
  assert.equal(held.destination, null);
  assert.match(await page.evaluate<string>(`document.getElementById("dispatches").textContent`), new RegExp(`${unit.id}`),
    "the commander's dispatches list the order");
  await screenshot(page, artifacts, "desk-accepted.png");
  console.log(`accepted: ${unit.id} hold_fire (${held.id}, ${held.status}); notice: ${posture["text"]}`);

  // 4. Refused with the server's text: the clock was started elsewhere (e.g. the POC desk),
  // so the POC refuses a Rest order the desk sends from its paused view.
  await poc(pocPort, "/api/clock", {command: "start", game_id: state["game_id"]});
  const counted = (await poc(pocPort, "/api/state"))["orders"].length;
  await choose(page, "order-kind", "rest");
  await clickOn(page, "#send-order");
  const busyClock = await nextNotice(page, posture["text"]);
  assert.equal(busyClock["kind"], "refusal", busyClock["text"]);
  assert.equal(busyClock["text"], "Pause the clock and let the current interval finish before issuing commands.");
  console.log(`refused: rest · ${busyClock["text"]}`);
  await until("the desk to see the running clock", () => page.evaluate<boolean>(
    `document.getElementById("clock-toggle").textContent === "Pause clock"`));

  // 5. Battlefield time advances on the header; Pause stops the clock.
  const moved = await until("battlefield time to advance", () => page.evaluate<string | null>(
    `(() => { const t = document.getElementById("battle-time").textContent; return t !== "16:30" ? t : null; })()`), 30000);
  await clickOn(page, "#clock-toggle");
  await until("the clock to pause", () => page.evaluate<boolean>(`document.getElementById("clock-toggle").textContent === "Start clock"`));
  const settled = await until("the POC to settle", async () => {
    const now = await poc(pocPort, "/api/state");
    return !now["clock"].running && !now["clock"].inflight ? now : null;
  });
  assert.equal(settled["orders"].length, counted, "the refused order changed nothing");
  console.log(`clock: header advanced to ${moved}; paused`);

  // 6. The POC moves on without the desk; the desk's next order is refused and the refusal is shown.
  await poc(pocPort, "/api/advance", {game_id: settled["game_id"], revision: settled["revision"]});
  await selectUnit(page, unit.id);
  await choose(page, "order-kind", "move");
  const second = await until("another open hex", () => page.evaluate<Doc | null>(openHex(unit.pos)));
  await page.click(second["x"], second["y"]);
  await clickOn(page, "#send-order");
  const refused = await nextNotice(page, "");
  assert.equal(refused["kind"], "refusal");
  assert.match(refused["text"], /Battle changed/);
  assert.equal((await poc(pocPort, "/api/state"))["orders"].length, settled["orders"].length, "the stale order changed nothing");
  console.log(`refused: move · ${refused["text"]}`);
}

async function hougoumont(page: Page, pocPort: number, artifacts: string): Promise<void> {
  const before = await noticeText(page);
  await choose(page, "scenario-select", HOUGOUMONT);
  await clickOn(page, "#new-battle");
  const started = await nextNotice(page, before);
  assert.equal(started["kind"], "accepted", started["text"]);
  const state = await poc(pocPort, "/api/state");
  assert.equal(state["scenario_brief"].id, HOUGOUMONT, "the POC started Hougoumont");
  const head = await header(page);
  assert.deepEqual([head["title"], head["time"], head["date"], head["location"]],
    ["Hougoumont: the north gate", "11:20", "Sunday, June 18, 1815", "Hougoumont · Waterloo, Belgium"]);
  assert.doesNotMatch(head["text"], /\bturn\b|revision/i);
  const drawn = await page.evaluate<Doc>(`({units: [...document.querySelectorAll("[data-unit]")].map(n => n.dataset.unit),
    kinds: [...document.getElementById("order-kind").options].map(o => o.value),
    hexes: document.querySelectorAll(".hex").length, chosen: document.getElementById("scenario-select").value})`);
  const map = await poc(pocPort, "/api/map");
  assert.deepEqual(drawn["units"], state["units"].map((u: Doc) => u.id), "Hougoumont's own counters");
  assert.equal(drawn["hexes"], map["cells"].length);
  assert.equal(drawn["chosen"], HOUGOUMONT);
  assert.ok(drawn["kinds"].includes("close_gate"), "Hougoumont's catalog adds Close the gate");
  console.log(`scenario: ${started["text"]}`);

  const gateParty = state["units"][0];
  await selectUnit(page, gateParty.id);
  console.log(`unit card: ${await checkCard(page, gateParty)}`);
  await choose(page, "order-kind", "close_gate");
  await clickOn(page, "#send-order");
  const gate = await nextNotice(page, "");
  assert.equal(gate["kind"], "accepted", gate["text"]);
  const after = await poc(pocPort, "/api/state");
  assert.ok(after["orders"].some((o: Doc) => o.unit_id === gateParty.id && o.stance === "close_gate"), "the POC holds close_gate");
  await screenshot(page, artifacts, "desk-hougoumont.png");
  console.log(`accepted: ${gateParty.id} close_gate; notice: ${gate["text"]}`);
}

interface Started { poc?: ChildProcess; desk?: DeskServer; browser?: ChildProcess; page?: Page }

async function body(binary: string, artifacts: string, profile: string, held: Started): Promise<number> {
  const [pocPort, deskPort] = [await freePort(), await freePort()];
  // Slice 1 review #1: assigned before the wait, so cleanup stops it on every path.
  held.poc = spawnPoc(pocPort, join(artifacts, "battle.sqlite"));
  await waitForOutput(held.poc, POC_READY, READY_MS, "POC");
  held.desk = await createDeskServer({pocUrl: `http://127.0.0.1:${pocPort}`, port: deskPort});
  let started;
  try {
    started = await launch(binary, profile, cleanEnv({TZ: BROWSER_ZONE}), Number(process.env["SMOKE_BROWSER_MS"] ?? 20000));
  } catch (error) {
    console.error(`SMOKE BLOCKED: the browser did not start (${(error as Error).message}). This is not a pass.`);
    return BLOCKED;
  }
  held.browser = started.process;
  held.page = await Page.open(started.endpoint);
  if (FREEZE) {
    console.log("SMOKE_FREEZE_BROWSER: stopping the browser group; its DevTools socket stays open");
    process.kill(-held.browser.pid!, "SIGSTOP");
  }
  await held.page.send("Page.navigate", {url: held.desk.url});
  await until("the desk to load", () => held.page!.evaluate<boolean>("document.documentElement.dataset.deskReady === 'true'"));
  await littleRoundTop(held.page, pocPort, artifacts);
  await hougoumont(held.page, pocPort, artifacts);
  console.log("SMOKE PASSED: unit card, move and hold-fire orders accepted, refusals shown with the server's text, "
    + "clock, and a switch to Hougoumont with its header, unit card and Close the gate order.");
  return 0;
}

async function main(): Promise<number> {
  const binary = findBrowser();
  if (!binary) {
    console.error("SMOKE BLOCKED: no Chrome/Chromium found (set BATTLE_BROWSER). This is not a pass.");
    return BLOCKED;
  }
  const artifacts = mkdtempSync(join(tmpdir(), "battle-desk-smoke."));
  // Review #3: the profile lives outside the artifacts and is removed on every exit path.
  const profile = mkdtempSync(join(tmpdir(), "battle-desk-profile."));
  console.log(`artifacts: ${artifacts}\nbrowser: ${binary}\ndeadline: ${DEADLINE_MS} ms`);
  const held: Started = {};
  let cleaned: Promise<void> | undefined;
  const cleanup = (): Promise<void> => cleaned ??= (async () => {
    held.page?.close();
    if (held.browser) await stop(held.browser, {group: true});
    await held.desk?.close();
    if (held.poc) await stop(held.poc);
    removeDir(profile);
  })();
  for (const signal of ["SIGINT", "SIGTERM"] as const) {
    process.once(signal, () => { void cleanup().finally(() => process.exit(1)); });
  }
  try {
    // Review #2: one deadline over the whole run, so a browser that stops answering cannot hang it.
    return await withDeadline(body(binary, artifacts, profile, held), DEADLINE_MS, "smoke run");
  } catch (error) {
    console.error(`SMOKE FAILED: ${(error as Error).stack ?? error}`);
    return 1;
  } finally {
    await cleanup();
    console.log(`kept: ${readdirSync(artifacts).sort().join(", ") || "nothing"}; profile removed`);
  }
}

const code = await main();
process.exitCode = code;
// Work abandoned at the deadline (a poll, a pending call) must not hold the process open.
setTimeout(() => process.exit(code), 3000).unref();
