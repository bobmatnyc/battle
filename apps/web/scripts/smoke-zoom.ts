// Browser checks for the desk's zoom (bt-T26, docs/research/81 §13): the 2x view's camera and labels,
// real clicks at 2x through the screen transform, fit restoring the fit markup, replay at 2x, and pan.
import assert from "node:assert/strict";
import type {CommanderView, MapDocument} from "@battle/contracts";
import {hexCenter, hexDistance} from "../src/geometry.ts";
import {FIT, hexAt, mapFocus, pan, toScene, toScreen, viewBox, zoomIn, zoomWindow, type Zoom} from "../src/zoom.ts";
import type {Page} from "./cdp.ts";
import {checkLabels} from "./smoke-features.ts";
import {choose, clickOn, poc, screenshot, until, type Doc} from "./smoke-page.ts";

type Point = [number, number];
interface Box { left: number; top: number; width: number; height: number; vw: number; vh: number }

const shown = (page: Page): Promise<string> => page.evaluate<string>(`document.getElementById("map").getAttribute("viewBox")`);
const markup = (page: Page): Promise<string> => page.evaluate<string>(`document.getElementById("map").innerHTML`);
// The SVG's content box in viewport px (inside its border), after scrolling it into view.
const BOX = `(() => { const svg = document.getElementById("map"); svg.scrollIntoView({block: "center"});
  const b = svg.getBoundingClientRect(), s = getComputedStyle(svg), l = parseFloat(s.borderLeftWidth), t = parseFloat(s.borderTopWidth);
  return {left: b.left + l, top: b.top + t, width: b.width - l - parseFloat(s.borderRightWidth),
    height: b.height - t - parseFloat(s.borderBottomWidth), vw: innerWidth, vh: innerHeight}; })()`;
const usable = (box: Box, [x, y]: Point): boolean =>
  x > box.left + 2 && x < box.left + box.width - 2 && y > box.top + 2 && y < box.top + box.height - 2 && x < box.vw && y < box.vh && y > 0;
// What the browser hit-tests at a viewport point: a counter's unit, or a hex polygon's position.
const hitAt = (page: Page, [x, y]: Point): Promise<Doc> => page.evaluate<Doc>(`(() => { const n = document.elementFromPoint(${x}, ${y});
  const unit = n?.closest("[data-unit]"); const hex = n?.closest("polygon.hex");
  return {unit: unit?.dataset.unit ?? null, hex: hex ? [+hex.dataset.c, +hex.dataset.r] : null}; })()`);

async function read(pocPort: number): Promise<{state: CommanderView; map: MapDocument}> {
  return {state: await poc(pocPort, "/api/state") as unknown as CommanderView, map: await poc(pocPort, "/api/map") as unknown as MapDocument};
}

/** A battle opens at the fit view (zoom resets on a scenario switch): the whole map, as before zoom. */
export async function checkFitAtStart(page: Page, pocPort: number): Promise<string> {
  const {map} = await read(pocPort);
  await until("the fit view", async () => (await shown(page)) === `0 0 ${map.width} ${map.height}`);
  assert.equal(await page.evaluate<string>(`document.getElementById("map-zoom-level").textContent`), "1× view");
  return `opens at the fit view (viewBox 0 0 ${map.width} ${map.height})`;
}

async function zoomTo(page: Page, expected: string): Promise<void> {
  await clickOn(page, "#map-zoom-in");
  await until(`the 2x view ${expected}`, async () => (await shown(page)) === expected);
}

/** Why: at 2x the player must see the objective and its marks, read every label whole, and click the hex
 * or counter under the pointer (docs/research/80 §7, 81 §11). What: zooms in; the window is the POC desk's
 * focus rule's, the objective's circle is inside the frame and every label lies inside it (checkLabels);
 * Fit restores the fit markup byte for byte; at 2x again (panned with the buttons until an own counter is in
 * frame) a real click at the transform's point of that counter selects it, and every in-frame hex centre hit-tests to that hex (or a counter on it), and a click
 * on one sets it as the destination. Leaves the fit view. Returns a one-line summary. */
export async function checkZoom(page: Page, pocPort: number, artifacts: string, shot: string): Promise<string> {
  const {state, map} = await read(pocPort);
  const fitBox = `0 0 ${map.width} ${map.height}`, fitMarkup = await markup(page);
  assert.equal(await shown(page), fitBox);
  const window = zoomWindow(zoomIn(FIT, map, mapFocus(state, map)), map), expected = viewBox(window);
  await zoomTo(page, expected);
  assert.equal(await page.evaluate<string>(`document.getElementById("map-zoom-level").textContent`), "2× view");
  const box = await page.evaluate<Box>(BOX);
  const ring = await page.evaluate<Doc>(`(() => { const b = document.querySelector("#map .objective circle:not(.objective-ring)").getBoundingClientRect();
    return {x0: b.left, y0: b.top, x1: b.right, y1: b.bottom}; })()`);
  assert.ok(ring["x0"] >= box.left && ring["y0"] >= box.top && ring["x1"] <= box.left + box.width && ring["y1"] <= box.top + box.height,
    `the objective is inside the 2x frame: ${JSON.stringify(ring)}`);
  const labels = await checkLabels(page);
  await screenshot(page, artifacts, `desk-${shot}-zoom2x.png`);
  await clickOn(page, "#map-fit");
  await until("the fit view again", async () => (await shown(page)) === fitBox);
  assert.equal(await markup(page), fitMarkup, "Fit draws the fit markup byte for byte");

  // Clicks at 2x through the transform: a counter, then every hex in frame, then a destination. Where no own
  // counter is in the 2x frame (Hill 223's patrol starts away from the shack), the pan buttons bring one in.
  await zoomTo(page, expected);
  const crowded = (pos: readonly number[]): boolean => [...state.units, ...state.contacts].filter((u) => String(u.pos) === String(pos)).length > 1;
  const unit = state.units.find((u) => !crowded(u.pos));
  assert.ok(unit, "an own counter alone in its hex");
  let zoom: Zoom = zoomIn(FIT, map, mapFocus(state, map)), panned = 0;
  for (;;) {
    const w = zoomWindow(zoom, map), [x, y] = hexCenter(unit.pos, map.radius), r = map.radius;
    const step: [number, number] = [x < w.x0 + r ? -1 : x > w.x1 - r ? 1 : 0, y < w.y0 + r ? -1 : y > w.y1 - r ? 1 : 0];
    if (!step[0] && !step[1]) break;
    assert.ok(panned < 6, `${unit.id} brought into the 2x frame`);
    const moves: [number, number, string][] = [[step[0], 0, step[0] < 0 ? "#map-pan-w" : "#map-pan-e"], [0, step[1], step[1] < 0 ? "#map-pan-n" : "#map-pan-s"]];
    for (const [dx, dy, button] of moves) {
      if (!dx && !dy) continue;
      zoom = pan(zoom, map, dx, dy);
      const next = viewBox(zoomWindow(zoom, map));
      await clickOn(page, button);
      await until(`the pan to ${next}`, async () => (await shown(page)) === next);
      panned += 1;
    }
  }
  const frame = zoomWindow(zoom, map);
  const at = await page.evaluate<Box>(BOX);
  const point = (pos: readonly [number, number]): Point => toScreen(frame, at, hexCenter(pos, map.radius));
  assert.equal((await hitAt(page, point(unit.pos)))["unit"], unit.id, `the transform's point for ${unit.id} is on its counter`);
  await page.click(...point(unit.pos));
  await until(`${unit.id} selected at 2x`, () => page.evaluate<boolean>(
    `document.querySelector('[data-unit="${unit.id}"]')?.getAttribute("aria-pressed") === "true"`));
  let hexes = 0, target: readonly [number, number] | null = null;
  for (const cell of map.cells) {
    const p = point(cell.pos);
    if (!usable(at, p)) continue;
    const hit = await hitAt(page, p);
    assert.ok(hit["hex"] === null || String(hit["hex"]) === String(cell.pos), `hex ${cell.pos} at 2x hit-tests to hex ${hit["hex"]}`);
    assert.deepEqual(hexAt(map.cells, map.radius, toScene(frame, at, p)), cell.pos);
    hexes += 1;
    const d = hexDistance(unit.pos, cell.pos);
    if (!target && hit["hex"] && d >= 2 && d <= 6) target = cell.pos;
  }
  assert.ok(target && hexes > 100, `${hexes} hexes in the 2x frame, a destination among them`);
  await page.click(...point(target));
  await until(`destination ${target} at 2x`, () => page.evaluate<boolean>(
    `!!document.querySelector('.hex.destination[data-c="${target[0]}"][data-r="${target[1]}"]')`));
  await clickOn(page, "#map-fit");
  await until("the fit view after the clicks", async () => (await shown(page)) === fitBox);
  return `2x window ${expected} (objective in frame); ${labels}; Fit restored the fit markup byte for byte; `
    + `at 2x (${panned} pan click(s), window ${viewBox(frame)}) ${unit.id} selected by a click at the transform's point, ${hexes} hexes hit-test to themselves, destination ${target} set`;
}

/** Why: zoom is presentation only, so replay must play at 2x and its controls must not stack listeners.
 * What: zooms in; opens the replay, plays it from the first record to the latest at the fastest speed with
 * the 2x window kept and labels inside the frame; returns to live; opens and closes the replay again; then
 * one pan click moves the window exactly one step and the opposite one brings it back. Leaves the 2x view,
 * so the next scenario's checkFitAtStart sees zoom reset. Returns a one-line summary. */
export async function checkZoomedReplay(page: Page, pocPort: number, artifacts: string, shot: string): Promise<string> {
  const {state, map} = await read(pocPort);
  const zoom: Zoom = zoomIn(FIT, map, mapFocus(state, map)), expected = viewBox(zoomWindow(zoom, map));
  await zoomTo(page, expected);
  const index = async (): Promise<number> => Number(await page.evaluate<string>(`document.getElementById("replay-slider").value`));
  const play = (): Promise<string> => page.evaluate<string>(`document.getElementById("replay-play").textContent`);
  await clickOn(page, "#replay-toggle");
  await until("the replay bar", () => page.evaluate<boolean>(`!document.getElementById("replay-bar").hidden`));
  const records = Number(await page.evaluate<string>(`document.getElementById("replay-slider").max`)) + 1;
  assert.equal(await shown(page), expected, "the replay opens at 2x");
  await choose(page, "replay-slider", "0", ["input", "change"]);
  await until("the scrub to the start", async () => (await index()) === 0);
  const fastest = await page.evaluate<string>(`[...document.getElementById("replay-speed").options].at(-1).value`);
  await choose(page, "replay-speed", fastest);
  await clickOn(page, "#replay-play");
  await until("playback at 2x", async () => (await play()) === "Pause");
  await until("playback to the latest record at 2x", async () => (await index()) === records - 1 && (await play()) === "Play", 90000);
  assert.equal(await shown(page), expected, "playback keeps the 2x window");
  const labels = await checkLabels(page);
  await screenshot(page, artifacts, `desk-${shot}-replay-zoom2x.png`);
  for (let i = 0; i < 2; i++) {  // return to live, then reopen and close once more
    await clickOn(page, "#replay-live");
    await until("the live battle", () => page.evaluate<boolean>(`document.getElementById("replay-bar").hidden`));
    if (i === 0) {
      await clickOn(page, "#replay-toggle");
      await until("the replay bar again", () => page.evaluate<boolean>(`!document.getElementById("replay-bar").hidden`));
    }
  }
  assert.equal(await shown(page), expected, "live again at 2x");
  const [dx, button, back] = viewBox(zoomWindow(pan(zoom, map, 1, 0), map)) !== expected ? [1, "#map-pan-e", "#map-pan-w"] : [-1, "#map-pan-w", "#map-pan-e"];
  const moved = viewBox(zoomWindow(pan(zoom, map, dx as number, 0), map));
  await clickOn(page, button as string);
  await until(`one pan step to ${moved}`, async () => (await shown(page)) === moved);
  await new Promise((done) => setTimeout(done, 300));
  assert.equal(await shown(page), moved, "one click is one step: no listener added by reopening");
  await clickOn(page, back as string);
  await until("the pan back", async () => (await shown(page)) === expected);
  return `replay played ${records} records at ${fastest}× at 2x (${labels}); reopened; one pan click moved ${expected} to ${moved} and back`;
}
