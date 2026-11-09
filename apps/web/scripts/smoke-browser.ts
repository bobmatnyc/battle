// Browser smoke test for the TypeScript desk (docs/research/70, 71, 73).
// Starts an offline POC on a temporary SQLite file and a free port, the desk
// server on another free port, and a headless Chrome/Chromium in a time zone
// far from the battle's. It checks the map features, their legend status and the
// grid toggle; with real pointer input it selects a counter and reads its unit
// card, sends a move and a non-move order, a standing order and its cancel and a split of headquarters
// (docs/research/81 §12), sees refusals carry the server's text (at Hougoumont, a split across the wall),
// runs the clock, replays the battle in the commander view and returns to live,
// then switches to Hougoumont and checks the header, features (compound and gate),
// counters, unit card and a Hougoumont-only order, then to Concord (docs/research/74): header,
// water, roads and bridge, an order, and the clock run to the outcome headline, then to Pegasus
// Bridge and Hill 223 (docs/research/75) the same way, each also zoomed to 2x (bt-T26). On every scenario it checks the objective
// ring is drawn exactly when the brief sets it, takes no clicks, and spans the neighbours (bt-T11).
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
import {mkdtempSync, readdirSync} from "node:fs";
import {createServer} from "node:http";
import type {AddressInfo} from "node:net";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";
import {createDeskServer, type DeskServer} from "../server/desk-server.ts";
import {findBrowser, launch, Page} from "./cdp.ts";
import {checkFeatures, checkGridToggle, checkLabels, checkReplay, checkRing} from "./smoke-features.ts";
import {checkEngineRefusal, checkSplit, checkStanding} from "./smoke-commands.ts";
import {checkCard, choose, clickOn, header, nextNotice, noticeText, openHex, poc, screenshot, selectUnit, until, type Doc} from "./smoke-page.ts";
import {removeDir, stop, waitForOutput, withDeadline} from "./smoke-support.ts";
import {checkFitAtStart, checkZoom, checkZoomedReplay} from "./smoke-zoom.ts";

const POC_DIR = fileURLToPath(new URL("../../poc/", import.meta.url));
const BROWSER_ZONE = "Pacific/Kiritimati";  // UTC+14: a browser-zone shift would move 16:30 to another day
const BLOCKED = 3;
const HOUGOUMONT = "hougoumont-north-gate";
const CONCORD = "concord-north-bridge";

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

  // Slice 3: roads, footprints and the legend with each mark's status; the grid toggle keeps them.
  console.log(`features: ${await checkFeatures(page, pocPort)}`);
  await screenshot(page, artifacts, "desk-lrt-features.png");
  // bt-T11: the hold-objective ring, as the POC desk draws it; the clicks below pass through it.
  console.log(`ring: ${await checkRing(page, pocPort)}`);
  console.log(`labels: ${await checkLabels(page)}`);
  await screenshot(page, artifacts, "desk-lrt-ring.png");
  console.log(`grid: ${await checkGridToggle(page, artifacts, "desk-lrt-grid-off.png")}`);

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

  // 3b. docs/research/81 §12: a standing order and its cancel, then a split of headquarters.
  console.log(`standing: ${await checkStanding(page, pocPort, unit.id, "cautious")}`);
  console.log(`split: ${await checkSplit(page, pocPort, state["command"].unit_id)}`);
  await screenshot(page, artifacts, "desk-lrt-commands.png");
  await selectUnit(page, unit.id);

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

  // 7. Slice 3: replay this battle in the commander view, back to an earlier interval, then live again.
  console.log(await checkReplay(page, pocPort, artifacts));
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
  // Slice 3: the lanes, the chateau footprint, the compound wall and the open north gate.
  console.log(`features: ${await checkFeatures(page, pocPort)}`);
  console.log(`grid: ${await checkGridToggle(page, artifacts, "desk-hougoumont-grid-off.png")}`);
  await screenshot(page, artifacts, "desk-hougoumont-features.png");
  console.log(`ring: ${await checkRing(page, pocPort)}`);
  console.log(`labels: ${await checkLabels(page)}`);

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
  // docs/research/81 §12: the desk draws no wall rule, so the engine refuses a split of A2 (10,9)
  // west across the compound wall to 9,9, and the desk shows the engine's text.
  console.log(`refused split: ${await checkEngineRefusal(page, pocPort, "A2", 30, [9, 9])}`);
}

// docs/research/74: Concord from the picker, offline and scripted, played to its outcome headline.
async function concord(page: Page, pocPort: number, artifacts: string): Promise<void> {
  const before = await noticeText(page);
  await choose(page, "scenario-select", CONCORD);
  await clickOn(page, "#new-battle");
  const started = await nextNotice(page, before);
  assert.equal(started["kind"], "accepted", started["text"]);
  const state = await poc(pocPort, "/api/state");
  assert.equal(state["scenario_brief"].id, CONCORD, "the POC started Concord");
  const head = await header(page);
  assert.deepEqual([head["title"], head["time"], head["date"], head["location"]],
    ["Concord North Bridge", "09:25", "Wednesday, April 19, 1775", "North Bridge · Concord, Massachusetts"]);
  assert.doesNotMatch(head["text"], /\bturn\b|revision/i, "no turn counter or revision label");
  console.log(`scenario: ${started["text"]}`);
  console.log(`features: ${await checkFeatures(page, pocPort)}`);
  await screenshot(page, artifacts, "desk-concord-features.png");
  console.log(`ring: ${await checkRing(page, pocPort)}`);
  console.log(`labels: ${await checkLabels(page)}`);

  // The Acton company, the command's own detachment, gets a move to an open hex 3 to 6 hexes away.
  const acton = state["units"].find((u: Doc) => u.id === "P1");
  await selectUnit(page, acton.id);
  console.log(`unit card: ${await checkCard(page, acton)}`);
  await choose(page, "order-kind", "move");
  const target = await until("an open hex", () => page.evaluate<Doc | null>(openHex(acton.pos)));
  await page.click(target["x"], target["y"]);
  await clickOn(page, "#send-order");
  const accepted = await nextNotice(page, started["text"]);
  assert.equal(accepted["kind"], "accepted", accepted["text"]);
  const order = (await poc(pocPort, "/api/state"))["orders"].find((o: Doc) => o.unit_id === "P1" && o.stance === "move");
  assert.deepEqual(order?.destination, [target["c"], target["r"]], "the POC holds the move order");
  console.log(`accepted: P1 move → ${target["c"]},${target["r"]} (${order.id}, ${order.status}); notice: ${accepted["text"]}`);

  // The clock at 60x from the desk's own button, until the battle ends; the headline is the brief's.
  await poc(pocPort, "/api/clock", {command: "speed", speed: 60, game_id: state["game_id"]});
  await clickOn(page, "#clock-toggle");
  const outcome = await until("the Concord outcome", () => page.evaluate<Doc | null>(`(() => {
    const box = document.getElementById("outcome");
    return box.hidden ? null : {headline: document.getElementById("outcome-headline").textContent,
      reason: document.getElementById("outcome-reason").textContent}; })()`), 90000);
  const done = await poc(pocPort, "/api/state?view=god");
  const outcomes = done["scenario_brief"].outcomes;
  const expected = done["winner"] === done["side"] ? outcomes.win : done["winner"] === "draw" ? outcomes.draw : outcomes.loss;
  assert.equal(outcome["headline"], expected);
  assert.equal(outcome["reason"], done["reason"]);
  const british = done["decisions"].filter((d: Doc) => d.side === "british" && d.role !== "staff");
  assert.ok(british.length > 0 && british.every((d: Doc) => d.source === "scripted" && d.policy === "scripted-concord-regulars-v1"),
    "the desk opponent played the regulars' scripted policy");
  await screenshot(page, artifacts, "desk-concord-outcome.png");
  console.log(`outcome: ${done["winner"]} after ${done["turn"]} intervals · "${outcome["headline"]}" ${outcome["reason"]}; `
    + `${british.length} British decisions, all scripted-concord-regulars-v1; mode ${done["mode"]}`);
}

// docs/research/75: Pegasus Bridge and Hill 223 from the picker, offline and scripted, each played to
// its outcome headline with the server's reason; the computer side plays the entry's scripted control.
interface Era { id: string; title: string; time: string; date: string; location: string; unit: string;
  opponent: string; policy: string; shot: string; note?: string }
const ERAS: Era[] = [
  {id: "pegasus-bridge", title: "Pegasus Bridge", time: "00:25", date: "Tuesday, June 6, 1944",
    location: "Caen Canal bridge · Bénouville, Normandy", unit: "D24", opponent: "german",
    policy: "scripted-pegasus-guard-v1", shot: "pegasus",
    note: "Note: on this entry the bridge is blown at 00:27:30 whatever you order, because the charge timings are authored, not sourced."},
  {id: "hill-223-patrol", title: "Hill 223", time: "06:45", date: "Tuesday, October 8, 1918",
    location: "Hill southwest of Hill 223 · Châtel-Chéhéry, Argonne", unit: "A3", opponent: "german",
    policy: "scripted-hill-223-german-v1", shot: "hill-223"},
];

async function era(page: Page, pocPort: number, artifacts: string, spec: Era): Promise<void> {
  const before = await noticeText(page);
  await choose(page, "scenario-select", spec.id);
  await clickOn(page, "#new-battle");
  const started = await nextNotice(page, before);
  assert.equal(started["kind"], "accepted", started["text"]);
  const state = await poc(pocPort, "/api/state");
  assert.equal(state["scenario_brief"].id, spec.id, `the POC started ${spec.title}`);
  const head = await header(page);
  assert.deepEqual([head["title"], head["time"], head["date"], head["location"]], [spec.title, spec.time, spec.date, spec.location]);
  assert.doesNotMatch(head["text"], /\bturn\b|revision/i, "no turn counter or revision label");
  if (spec.note) {  // bt-D09 default: the brief's note is on the desk, and visible, before play.
    const seen = await page.evaluate<Doc>(`(n => ({text: n.innerText, visible: n.checkVisibility()}))(document.getElementById("mission"))`);
    assert.ok(seen["visible"] && String(seen["text"]).includes(spec.note), `the ${spec.title} brief shows its note: ${seen["text"]}`);
    console.log(`brief note visible before play: "${spec.note}"`);
  }
  console.log(`scenario: ${started["text"]}`);
  console.log(`features: ${await checkFeatures(page, pocPort)}`);
  await screenshot(page, artifacts, `desk-${spec.shot}-features.png`);
  console.log(`ring: ${await checkRing(page, pocPort)}`);
  console.log(`labels: ${await checkLabels(page)}`);
  // bt-T26 (docs/research/81 §13): zoom resets on the switch; the 2x view's camera, labels and clicks.
  console.log(`zoom: ${await checkFitAtStart(page, pocPort)}; ${await checkZoom(page, pocPort, artifacts, spec.shot)}`);

  const unit = state["units"].find((u: Doc) => u.id === spec.unit);
  await selectUnit(page, unit.id);
  console.log(`unit card: ${await checkCard(page, unit)}`);
  await choose(page, "order-kind", "move");
  const target = await until("an open hex", () => page.evaluate<Doc | null>(openHex(unit.pos)));
  await page.click(target["x"], target["y"]);
  await clickOn(page, "#send-order");
  const accepted = await nextNotice(page, started["text"]);
  assert.equal(accepted["kind"], "accepted", accepted["text"]);
  const order = (await poc(pocPort, "/api/state"))["orders"].find((o: Doc) => o.unit_id === spec.unit && o.stance === "move");
  assert.deepEqual(order?.destination, [target["c"], target["r"]], "the POC holds the move order");
  console.log(`accepted: ${spec.unit} move → ${target["c"]},${target["r"]} (${order.id}, ${order.status}); notice: ${accepted["text"]}`);

  await poc(pocPort, "/api/clock", {command: "speed", speed: 60, game_id: state["game_id"]});
  await clickOn(page, "#clock-toggle");
  const outcome = await until(`the ${spec.title} outcome`, () => page.evaluate<Doc | null>(`(() => {
    const box = document.getElementById("outcome");
    return box.hidden ? null : {headline: document.getElementById("outcome-headline").textContent,
      reason: document.getElementById("outcome-reason").textContent}; })()`), 120000);
  const done = await poc(pocPort, "/api/state?view=god");
  const outcomes = done["scenario_brief"].outcomes;
  const expected = done["winner"] === done["side"] ? outcomes.win : done["winner"] === "draw" ? outcomes.draw : outcomes.loss;
  assert.equal(outcome["headline"], expected);
  assert.equal(outcome["reason"], done["reason"]);
  const theirs = done["decisions"].filter((d: Doc) => d.side === spec.opponent && d.role !== "staff");
  assert.ok(theirs.length > 0 && theirs.every((d: Doc) => d.source === "scripted" && d.policy === spec.policy),
    `the desk opponent played ${spec.policy}`);
  await screenshot(page, artifacts, `desk-${spec.shot}-outcome.png`);
  console.log(`outcome: ${done["winner"]} after ${done["turn"]} intervals · "${outcome["headline"]}" ${outcome["reason"]}; `
    + `${theirs.length} ${spec.opponent} decisions, all ${spec.policy}; mode ${done["mode"]}`);
  console.log(`zoom replay: ${await checkZoomedReplay(page, pocPort, artifacts, spec.shot)}`);
}

// `closing` is set when cleanup begins; nothing is started after that, and every child is
// recorded here before the run waits on it, so cleanup can stop it on every exit path.
interface Started { closing: boolean; poc?: ChildProcess; desk?: DeskServer; browser?: ChildProcess; page?: Page }

function halt(held: Started): void {
  if (held.closing) throw new Error("the smoke run is stopping; nothing more is started");
}

async function body(binary: string, artifacts: string, profile: string, held: Started): Promise<number> {
  const [pocPort, deskPort] = [await freePort(), await freePort()];
  halt(held);
  // Slice 1 review #1: assigned before the wait, so cleanup stops it on every path.
  held.poc = spawnPoc(pocPort, join(artifacts, "battle.sqlite"));
  await waitForOutput(held.poc, POC_READY, READY_MS, "POC");
  halt(held);
  const desk = await createDeskServer({pocUrl: `http://127.0.0.1:${pocPort}`, port: deskPort});
  if (held.closing) await desk.close();
  halt(held);
  held.desk = desk;
  console.log("launching browser");
  let started;
  try {
    // Fix round #3: the browser is registered before launch waits for DevTools, so an interrupt or
    // the deadline during launch stops its group; once cleanup has begun, launch refuses.
    started = await launch(binary, profile, cleanEnv({TZ: BROWSER_ZONE}), Number(process.env["SMOKE_BROWSER_MS"] ?? 20000),
      (child) => { held.browser = child; return !held.closing; });
  } catch (error) {
    halt(held);
    console.error(`SMOKE BLOCKED: the browser did not start (${(error as Error).message}). This is not a pass.`);
    return BLOCKED;
  }
  halt(held);
  held.page = await Page.open(started.endpoint);
  if (FREEZE) {
    console.log("SMOKE_FREEZE_BROWSER: stopping the browser group; its DevTools socket stays open");
    process.kill(-started.process.pid!, "SIGSTOP");
  }
  await held.page.send("Emulation.setDeviceMetricsOverride", {width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false});
  await held.page.send("Page.navigate", {url: held.desk.url});
  await until("the desk to load", () => held.page!.evaluate<boolean>("document.documentElement.dataset.deskReady === 'true'"));
  await littleRoundTop(held.page, pocPort, artifacts);
  await hougoumont(held.page, pocPort, artifacts);
  await concord(held.page, pocPort, artifacts);
  for (const spec of ERAS) await era(held.page, pocPort, artifacts, spec);
  console.log("SMOKE PASSED: map features with legend status and the grid toggle at Little Round Top and Hougoumont, "
    + "the objective ring exactly where the brief sets it (Little Round Top, Concord), "
    + "unit card, move and hold-fire orders accepted, a standing order sent and cancelled, a split of headquarters, "
    + "refusals shown with the server's text (a split across the Hougoumont wall with the engine's), clock, "
    + "commander replay back to an earlier interval and return to live, a switch to Hougoumont with its header, "
    + "unit card and Close the gate order, and a switch to Concord with its header, water, roads and bridge, "
    + "a move order and the clock run to the outcome headline, then Pegasus Bridge (canal, marsh, both bridges, the charges "
    + "as known) and Hill 223 (woods, old trench), each with an order and the clock run to its headline and reason, "
    + "and each at 2x (bt-T26): focus in frame, labels inside the frame, clicks at 2x, Fit byte for byte, replay and pan.");
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
  const held: Started = {closing: false};
  let cleaned: Promise<void> | undefined;
  const cleanup = (): Promise<void> => cleaned ??= (async () => {
    held.closing = true;
    held.page?.close();
    if (held.browser) await stop(held.browser, {group: true});
    await held.desk?.close();
    if (held.poc) await stop(held.poc);
    removeDir(profile);
  })();
  // As the POC harness after docs/research/72 §6.1: `on`, not `once`, for the whole run, so a second
  // signal during cleanup (or a closed terminal's SIGHUP) cannot end the run before cleanup finishes.
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"] as const) {
    process.on(signal, () => { void cleanup().finally(() => process.exit(1)); });
  }
  for (const stream of [process.stdout, process.stderr]) stream.on("error", () => { /* a closed terminal */ });
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
