// bt-T26 (docs/research/81 §13): the desk's zoom, pan and screen transforms, and the map drawn at 2x.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {readMapFeatures, type CommanderView, type MapDocument} from "@battle/contracts";
import {statusTableFor} from "../src/feature-sources.ts";
import {labelBox, type LabelPlace, type Rect} from "../src/features.ts";
import {hexCenter} from "../src/geometry.ts";
import {mapMarkup} from "../src/render.ts";
import {FIT, focusCentre, hexAt, mapFocus, pan, toScene, toScreen, viewBox, zoomIn, zoomWindow, type Focus} from "../src/zoom.ts";
import {commander, map, pocFeatureSources, type Doc} from "./fixtures.ts";

const catalog: Record<string, Doc> = JSON.parse(readFileSync(
  new URL("../../../packages/contracts/fixtures/map-features.json", import.meta.url), "utf8"));
const none = {unitId: null, destination: null};
const inside = (b: Rect, f: Rect): boolean => b.x0 >= f.x0 && b.y0 >= f.y0 && b.x1 <= f.x1 && b.y1 <= f.y1;
const asRect = ([x0, y0, x1, y1]: readonly number[]): Rect => ({x0: x0!, y0: y0!, x1: x1!, y1: y1!});
const hexBox = (pos: readonly [number, number], r: number): Rect => {
  const [x, y] = hexCenter(pos, r);
  return {x0: x - r, y0: y - r, x1: x + r, y1: y + r};
};

// The commander view of Hill 223 or Pegasus Bridge as the desk draws it: the catalog's features and the
// scenario's objective and label (apps/poc/battle/scenario_hill223.py SHACK, scenario_pegasus.py CANAL).
const SCENARIOS = {
  "hill-223-patrol": {objective: [0, 11] as [number, number], label: "PATROL OBJECTIVE"},
  "pegasus-bridge": {objective: [9, 10] as [number, number], label: "BRIDGE OBJECTIVE"},
};
type Id = keyof typeof SCENARIOS;
function scenario(id: Id): CommanderView {
  const view = commander(), brief = view.scenario_brief!;
  return {...view, objective: SCENARIOS[id].objective, map_features: readMapFeatures(catalog[id]!["map_features"]),
    scenario_brief: {...brief, id, objective: {...brief.objective, label: SCENARIOS[id].label}}};
}
const sources = (id: string): ReturnType<typeof statusTableFor> => statusTableFor(pocFeatureSources(), id);
const zoomed = (view: CommanderView, terrain: MapDocument): Rect => zoomWindow(zoomIn(FIT, terrain, mapFocus(view, terrain)), terrain);

// Every drawn label in a map's markup, with the box the placement rule gives it (labelBox): the feature
// labels (inside any translated group) and the objective's label (11 px, as render.ts draws it).
function drawnLabels(svg: string): {text: string; box: Rect}[] {
  const out: {text: string; box: Rect}[] = [];
  const read = (t: RegExpExecArray, dx: number, dy: number): void => {
    const text = t[4]!.replaceAll("&#39;", "'").replaceAll("&amp;", "&");
    const place: LabelPlace = {x: Number(t[1]) + dx, y: Number(t[2]) + dy, anchor: (t[3] ?? "start") as LabelPlace["anchor"]};
    out.push({text, box: labelBox(text, place)});
  };
  for (const m of svg.matchAll(/<g class="feature-mark([^>]*)>(.*?)<\/g>/g)) {
    const t = /<text x="([-\d.]+)" y="([-\d.]+)"(?: text-anchor="(\w+)")? class="feature-label">([^<]*)<\/text>/.exec(m[2]!);
    const move = /translate\(([-\d.]+),([-\d.]+)\)/.exec(m[1]!);
    if (t) read(t, move ? Number(move[1]) : 0, move ? Number(move[2]) : 0);
  }
  const objective = /<g class="objective"[^>]*>.*?<text x="([-\d.]+)" y="([-\d.]+)"(?: text-anchor="(\w+)")?>([^<]*)<\/text>/.exec(svg);
  assert.ok(objective, "the objective's label is drawn");
  read(objective, 0, 0);
  return out;
}

test("the fit view is the whole map, with the viewBox the desk has always set, and draws the same markup", () => {
  const view = commander(), terrain = map(), table = sources("little-round-top");
  const whole = zoomWindow(FIT, terrain);
  assert.deepEqual(whole, {x0: 0, y0: 0, x1: terrain.width, y1: terrain.height});
  assert.equal(viewBox(whole), `0 0 ${terrain.width} ${terrain.height}`);
  for (const selection of [none, {unitId: view.units[0]!.id, destination: [12, 14] as [number, number]}]) {
    assert.equal(mapMarkup(view, terrain, selection, table, whole), mapMarkup(view, terrain, selection, table),
      "the fit window draws byte for byte what the desk drew before zoom");
  }
});

test("zoom in shows half the map each way, keeping the objective and every mark in frame, else the objective only", () => {
  const terrain = map();
  // Hill 223: the shack is in column 0 and the old trench at 3,16; both fit in a 2x window.
  const hill = scenario("hill-223-patrol"), hillFocus = mapFocus(hill, terrain), hillWindow = zoomed(hill, terrain);
  assert.deepEqual([hillWindow.x1 - hillWindow.x0, hillWindow.y1 - hillWindow.y0], [terrain.width / 2, terrain.height / 2]);
  assert.ok(inside(asRect(hillFocus.all), hillWindow), `Hill 223: objective, label and fieldworks in ${JSON.stringify(hillWindow)}`);
  assert.ok(inside(hexBox([0, 11], terrain.radius), hillWindow) && inside(hexBox([3, 16], terrain.radius), hillWindow));
  assert.equal(viewBox(hillWindow), `${hillWindow.x0} ${hillWindow.y0} 540 420`);
  // Pegasus Bridge: the marks run from the canal to the Orne pillbox, wider than the window; the objective stays in.
  const pegasus = scenario("pegasus-bridge"), pegasusFocus = mapFocus(pegasus, terrain), pegasusWindow = zoomed(pegasus, terrain);
  assert.ok(!inside(asRect(pegasusFocus.all), pegasusWindow), "the marks do not fit");
  assert.ok(inside(asRect(pegasusFocus.core), pegasusWindow), `Pegasus: objective and its label in ${JSON.stringify(pegasusWindow)}`);
  assert.ok(!inside(hexBox([20, 10], terrain.radius), pegasusWindow), "the Orne pillbox is off screen at 2x");
  // The rule itself (the POC desk's focusCentre): no focus keeps the centre; a core wider than the frame is centred.
  assert.deepEqual(focusCentre([540, 420], [270, 210], null, [1080, 840]), [540, 420]);
  const wide: Focus = {core: [0, 400, 1000, 420], all: [0, 400, 1000, 420]};
  assert.deepEqual(focusCentre([540, 420], [270, 210], wide, [1080, 840]), [500, 420]);
  const twice = zoomIn(FIT, terrain, hillFocus);
  assert.deepEqual(zoomIn(twice, terrain, null), twice, "2x is the deepest zoom");
});

test("at 2x every label is placed inside the zoomed window, and a label whose mark is off screen is hidden", () => {
  const terrain = map();
  for (const id of Object.keys(SCENARIOS) as Id[]) {
    const view = scenario(id), window = zoomed(view, terrain);
    const svg = mapMarkup(view, terrain, none, sources(id), window);
    const labels = drawnLabels(svg);
    assert.ok(labels.length > 1, `${id}: labels drawn at 2x`);
    for (const l of labels) assert.ok(inside(l.box, window), `${id} 2x: "${l.text}" ${JSON.stringify(l.box)} crosses ${JSON.stringify(window)}`);
  }
  const pegasus = scenario("pegasus-bridge");
  assert.match(mapMarkup(pegasus, terrain, none, sources("pegasus-bridge"), zoomed(pegasus, terrain)), /data-label="hidden"/,
    "the Orne pillbox's label is hidden at 2x, not drawn cut");
});

test("a click at 2x maps to the hex under the pointer", () => {
  const terrain = map(), r = terrain.radius, window = zoomed(scenario("hill-223-patrol"), terrain);
  const box = {left: 13, top: 120, width: 1043.5, height: 811.6};  // the SVG's content box in CSS px
  assert.deepEqual(toScreen(window, box, [window.x0, window.y0]), [13, 120]);
  const middle = toScreen(window, box, [(window.x0 + window.x1) / 2, (window.y0 + window.y1) / 2]);
  assert.deepEqual(middle.map((v) => Math.round(v * 1000) / 1000), [13 + 1043.5 / 2, 120 + 811.6 / 2]);
  let checked = 0;
  for (const cell of terrain.cells) {
    const [x, y] = hexCenter(cell.pos, r);
    if (x < window.x0 || x > window.x1 || y < window.y0 || y > window.y1) continue;
    // A pointer a third of a radius off the centre, as a player's click is, still names the hex.
    const point = toScreen(window, box, [x + r / 3, y - r / 3]);
    assert.deepEqual(hexAt(terrain.cells, r, toScene(window, box, point)), cell.pos, `hex ${cell.pos} at 2x`);
    checked += 1;
  }
  assert.ok(checked > 100, `${checked} hexes checked in the window`);
  // The same screen point names another hex at fit: the transform depends on the window.
  const shack = toScreen(window, box, hexCenter([0, 11], r));
  assert.deepEqual(hexAt(terrain.cells, r, toScene(window, box, shack)), [0, 11]);
  assert.notDeepEqual(hexAt(terrain.cells, r, toScene(zoomWindow(FIT, terrain), box, shack)), [0, 11]);
  assert.equal(hexAt(terrain.cells, r, [-200, -200]), null, "off the map is no hex");
});

test("pan moves the 2x window by half its size and stops at the map's edge; the fit view does not pan", () => {
  const terrain = map(), start = zoomIn(FIT, terrain, mapFocus(scenario("hill-223-patrol"), terrain));
  const w0 = zoomWindow(start, terrain);
  const east = zoomWindow(pan(start, terrain, 1, 0), terrain);
  assert.deepEqual([east.x0, east.y0], [w0.x0 + 270, w0.y0], "one step east is half the window");
  assert.deepEqual(zoomWindow(pan(pan(start, terrain, 1, 0), terrain, -1, 0), terrain), w0, "and one step back returns");
  let z = start;
  for (let i = 0; i < 5; i++) z = pan(z, terrain, 1, 1);
  assert.deepEqual(zoomWindow(z, terrain), {x0: 540, y0: 420, x1: 1080, y1: 840}, "the window stops at the map's corner");
  assert.deepEqual(pan(z, terrain, 1, 0), z, "past the edge the window stays");
  assert.deepEqual(pan(FIT, terrain, 1, 0), FIT);
});
