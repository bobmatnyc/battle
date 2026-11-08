// Page helpers for the desk smoke test (docs/research/70, 71, 73): real pointer clicks, waits
// on the page's own state, and direct POC reads used only to check what the desk shows.
import assert from "node:assert/strict";
import {writeFileSync} from "node:fs";
import {join} from "node:path";
import type {Page} from "./cdp.ts";
import {pocRequest} from "./smoke-support.ts";

export type Doc = Record<string, any>;

// Direct POC calls, as the POC's own host; used only to check, to stale the cursor and to run the clock elsewhere.
export const poc = (port: number, path: string, body?: unknown): Promise<Doc> => pocRequest(port, path, body);

export async function until<T>(what: string, probe: () => Promise<T | null | false>, ms = 15000): Promise<T> {
  const end = Date.now() + ms;
  for (;;) {
    const value = await probe();
    if (value) return value;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}`);
    await new Promise((done) => setTimeout(done, 100));
  }
}

interface Point { x: number; y: number }
// The element's centre in the viewport, after scrolling it into view (the toolbar and replay
// bar move the map down, and a point off the viewport cannot be clicked).
const centre = (selector: string): string => `(() => { const n = document.querySelector(${JSON.stringify(selector)});
  if (!n) return null; n.scrollIntoView({block: "center", inline: "center"});
  const b = n.getBoundingClientRect(); return {x: b.x + b.width / 2, y: b.y + b.height / 2}; })()`;

// A hex whose centre hit-tests to the hex itself (no counter or label on top), 3 to 6 hexes from `from`.
export const openHex = (from: [number, number]): string => `(() => {
  for (const hex of document.querySelectorAll(".hex")) {
    const c = +hex.dataset.c, r = +hex.dataset.r;
    const d = Math.max(Math.abs(c - ${from[0]}), Math.abs(r - ${from[1]}));
    if (d < 3 || d > 6) continue;
    const b = hex.getBoundingClientRect(), x = b.x + b.width / 2, y = b.y + b.height / 2;
    if (document.elementFromPoint(x, y) === hex) return {c, r, x, y};
  }
  return null; })()`;

export async function clickOn(page: Page, selector: string): Promise<void> {
  const point = await until(selector, () => page.evaluate<Point | null>(centre(selector)));
  await page.click(point.x, point.y);
}

// A real click on the counter: the counter must be the element under the pointer.
export async function selectUnit(page: Page, id: string): Promise<void> {
  const point = await until(`counter ${id}`, () => page.evaluate<Point | null>(centre(`[data-unit="${id}"] rect`)));
  const hit = await page.evaluate<string | null>(`document.elementFromPoint(${point.x}, ${point.y})?.closest("[data-unit]")?.dataset.unit ?? null`);
  assert.equal(hit, id, "the counter is the element under the pointer");
  await page.click(point.x, point.y);
  await until(`${id} selected`, () => page.evaluate<boolean>(
    `document.querySelector('[data-unit="${id}"]')?.getAttribute("aria-pressed") === "true"`));
}

// A <select> or range choice, as the browser's own events (headless Chrome draws no native list to click).
export async function choose(page: Page, id: string, value: string, events = ["change"]): Promise<void> {
  const ok = await page.evaluate<boolean>(`(() => { const s = document.getElementById(${JSON.stringify(id)});
    if (s.options && ![...s.options].some(o => o.value === ${JSON.stringify(value)})) return false;
    s.value = ${JSON.stringify(value)};
    for (const e of ${JSON.stringify(events)}) s.dispatchEvent(new Event(e, {bubbles: true})); return true; })()`);
  assert.ok(ok, `#${id} offers ${value}`);
}

// The next notice that is not plain info and differs from `before`.
export async function nextNotice(page: Page, before: string, ms = 15000): Promise<Doc> {
  return until("a desk notice", () => page.evaluate<Doc | null>(`(() => { const n = document.getElementById("notice");
    return n.dataset.kind !== "info" && n.textContent !== ${JSON.stringify(before)} ? {kind: n.dataset.kind, text: n.textContent} : null; })()`), ms);
}
export const noticeText = (page: Page): Promise<string> => page.evaluate<string>(`document.getElementById("notice").textContent`);

export async function header(page: Page): Promise<Doc> {
  return page.evaluate<Doc>(`({time: document.getElementById("battle-time").textContent,
    date: document.getElementById("battle-date").textContent, location: document.getElementById("battle-location").textContent,
    title: document.getElementById("title").textContent, zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    text: document.body.innerText})`);
}

// The unit card's fields against the POC's own commander view of that unit.
export async function checkCard(page: Page, unit: Doc): Promise<string> {
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

// The whole page, so the legend under the map is in the picture.
export async function screenshot(page: Page, artifacts: string, name: string): Promise<void> {
  await page.evaluate("window.scrollTo(0, 0)");
  const metrics = await page.send("Page.getLayoutMetrics");
  const size = metrics["cssContentSize"] as {width: number; height: number};
  const clip = {x: 0, y: 0, width: Math.ceil(size.width), height: Math.ceil(size.height), scale: 1};
  const shot = await page.send("Page.captureScreenshot", {format: "png", captureBeyondViewport: true, clip});
  writeFileSync(join(artifacts, name), Buffer.from(String(shot["data"]), "base64"));
}
