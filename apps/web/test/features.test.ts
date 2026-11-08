// Map features in the TypeScript desk (docs/research/73): drawn as the POC desk draws them
// (apps/poc/static/map-features.js, docs/research/72), with each mark's status read from the
// POC's own presentation table, apps/poc/static/feature-sources.js, never a copy of it.
import assert from "node:assert/strict";
import {readdirSync, readFileSync} from "node:fs";
import {test} from "node:test";
import vm from "node:vm";
import {readMapFeatures, type MapFeature} from "@battle/contracts";
import {featureLayer, featureLegend, featureNotes, footprint, placeLabels, type FeatureOptions, type LabelPlace, type LabelSpec, type Rect} from "../src/features.ts";
import {readStatusTable, statusTableFor} from "../src/feature-sources.ts";
import {hexCenter} from "../src/geometry.ts";
import {esc} from "../src/render.ts";

type Doc = Record<string, any>;
const POC_STATIC = new URL("../../poc/static/", import.meta.url);
const catalog: Record<string, Doc> = JSON.parse(readFileSync(
  new URL("../../../packages/contracts/fixtures/map-features.json", import.meta.url), "utf8"));
const RADIUS = 25.5;  // every catalog map's radius (map.json); the POC renderer's R

// The POC's own renderer and table, loaded as the POC desk loads them (classic scripts).
const poc = vm.createContext({});
for (const file of ["feature-sources.js", "map-features.js"]) vm.runInContext(readFileSync(new URL(file, POC_STATIC), "utf8"), poc);
poc["center"] = (p: [number, number]) => hexCenter(p, RADIUS);
poc["esc"] = esc;
const sourcesModule = vm.runInContext("BattleFeatureSources", poc);
const pocCall = (expression: string, args: unknown[]): string => { poc["args"] = args; return vm.runInContext(expression, poc); };

function options(id: string): FeatureOptions {
  const entry = catalog[id]!;
  return {metresPerHex: entry["metres_per_hex"], cells: entry["bridge_cells"], sources: statusTableFor(sourcesModule, id), radius: RADIUS};
}
const pocOptions = (id: string): Doc => ({metresPerHex: catalog[id]!["metres_per_hex"], cells: catalog[id]!["bridge_cells"],
  sources: vm.runInContext(`BattleFeatureSources.forScenario(${JSON.stringify(id)})`, poc)});
const features = (id: string): MapFeature[] => readMapFeatures(catalog[id]!["map_features"]);

test("every catalog entry's feature layer, legend and hex notes match the POC desk's", () => {
  for (const id of Object.keys(catalog)) {
    const list = features(id);
    assert.equal(featureLayer(list, options(id)), pocCall("BattleFeatures.render(args[0], center, esc, args[1])", [list, pocOptions(id)]), id);
    assert.equal(featureLegend(list, options(id)), pocCall("BattleFeatures.legend(args[0], esc, args[1])", [list, pocOptions(id)]), id);
    for (const f of list) {
      const pos = "pos" in f ? f.pos : f.points[0]!;
      // JSON: the POC's array belongs to the vm's realm.
      assert.equal(JSON.stringify(featureNotes(list, pos, options(id))),
        pocCall("JSON.stringify(BattleFeatures.notes(args[0], args[1], args[2]))", [list, pos, pocOptions(id)]), `${id} ${f.id}`);
    }
  }
});

test("a gate is drawn in its known state, works dug in battle are 'reported', and a blown bridge has no span", () => {
  const gate = (state: string): MapFeature[] => {
    const list = structuredClone(catalog["hougoumont-north-gate"]!["map_features"]);
    list.find((f: Doc) => f["id"] === "hougoumont")["openings"][0]["state"] = state;
    list.push({id: "works-5,5", kind: "fortification", name: "Hasty fieldworks", pos: [5, 5], base_cover: 10, cover: 25,
      progress: 50, effort: 200, required: 400, updated_turn: 3, briefed: false, provenance: "simulation-built",
      observed_turn: 3, received_turn: 4});
    return readMapFeatures(list);
  };
  for (const state of ["open", "closed", "barred"]) {
    const layer = featureLayer(gate(state), options("hougoumont-north-gate"));
    assert.equal(layer, pocCall("BattleFeatures.render(args[0], center, esc, args[1])", [gate(state), pocOptions("hougoumont-north-gate")]), state);
    assert.match(layer, new RegExp(`data-feature="hougoumont#north-gate" data-status="sourced" data-state="${state}"`));
    assert.match(layer, new RegExp(`North gate · ${state}</text>`));
  }
  assert.match(featureLayer(gate("closed"), options("hougoumont-north-gate")), /class="gate-shut"/);
  assert.match(featureLegend(gate("open"), options("hougoumont-north-gate")), /data-feature="works-5,5".*Reported in battle/);
  const blown = readMapFeatures(catalog["pegasus-bridge"]!["map_features"].map((f: Doc) => f["kind"] === "bridge" ? {...f, state: "destroyed"} : f));
  const layer = featureLayer(blown, options("pegasus-bridge"));
  assert.equal(layer, pocCall("BattleFeatures.render(args[0], center, esc, args[1])", [blown, pocOptions("pegasus-bridge")]));
  assert.match(layer, /data-feature="canal-bridge"[^>]*data-state="destroyed"><title>[^<]*<\/title><path class="bridge-deck"/, "no road span over a destroyed bridge");
});

test("footprints scale with metres_per_hex, and every mark's tooltip names its status and basis", () => {
  const spacing = Math.sqrt(3) * RADIUS;
  const lrt = footprint([30, 18], 50, RADIUS);
  assert.ok(Math.abs(lrt.w - 30 * spacing / 50) < 1e-9 && Math.abs(lrt.h - 18 * spacing / 50) < 1e-9);
  assert.ok(Math.abs(footprint([30, 18], 100, RADIUS).w - lrt.w / 2) < 1e-9, "halves when metres_per_hex doubles");
  assert.equal(footprint([2, 2], 50, RADIUS).enlarged, true);
  assert.equal(footprint([400, 400], 50, RADIUS).capped, true);
  const layer = featureLayer(features("hougoumont-north-gate"), options("hougoumont-north-gate"));
  for (const key of ["north-lane", "hougoumont", "hougoumont#walls", "hougoumont#north-gate"]) {
    const info = statusTableFor(sourcesModule, "hougoumont-north-gate")[key]!;
    assert.match(layer, new RegExp(`data-feature="${key}" data-status="${info.status}"[^>]*><title>[^<]*${info.status === "sourced" ? "Sourced" : "Illustrative"}: `), key);
  }
});

test("the status table is the POC's file, read through a checked reader; the desk holds no copy", () => {
  const table = statusTableFor(sourcesModule, "hougoumont-north-gate");
  assert.equal(table["hougoumont#north-gate"]!.status, "sourced");
  assert.deepEqual(statusTableFor(sourcesModule, "gergovia-recall"), {});
  assert.deepEqual(statusTableFor(null, "little-round-top"), {}, "a table that did not load gives no status, not a guess");
  assert.throws(() => readStatusTable({x: {status: "rumoured", source: "?"}}), /\$\.x\.status/);
  assert.throws(() => readStatusTable({x: {status: "sourced", source: "S1", colour: "red"}}), /\$\.x\.colour/);
  assert.throws(() => readStatusTable({x: {status: "sourced", source: "S1", footprint_m: [0, 4]}}), /\$\.x\.footprint_m/);
  // No basis text from the POC table appears in the desk's own sources.
  const texts = Object.keys(catalog).flatMap((id) => Object.values(statusTableFor(sourcesModule, id)).map((s) => s.source.slice(0, 40)));
  const src = new URL("../src/", import.meta.url);
  for (const name of readdirSync(src)) {
    const body = readFileSync(new URL(name, src), "utf8");
    for (const text of texts) assert.ok(!body.includes(text), `${name} copies "${text}"`);
  }
});

// bt-T16 (docs/research/80): no feature label meets another label or a counter. The boxes are measured here
// with a narrower text estimate than the placement rule's (6 px a character, 7.8 for capitals).
type Box = {x0: number; y0: number; x1: number; y1: number};
const meet = (a: Box, b: Box): boolean => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
function drawnLabels(layer: string): (Box & {text: string})[] {
  const out: (Box & {text: string})[] = [];
  for (const m of layer.matchAll(/<g class="feature-mark[^>]*data-feature="([^"]*)"([^>]*)>(.*?)<\/g>/g)) {
    const t = /<text x="([-\d.]+)" y="([-\d.]+)"(?: text-anchor="(\w+)")? class="feature-label">([^<]*)<\/text>/.exec(m[3]!);
    if (!t) continue;
    const move = /translate\(([-\d.]+),([-\d.]+)\)/.exec(m[2]!);
    const x = Number(t[1]) + (move ? Number(move[1]) : 0), y = Number(t[2]) + (move ? Number(move[2]) : 0);
    const text = t[4]!.replaceAll("&#39;", "'").replaceAll("&amp;", "&");
    const w = [...text].reduce((n, c) => n + (/[A-Z%]/.test(c) ? 7.8 : 6), 0), x0 = t[3] === "middle" ? x - w / 2 : t[3] === "end" ? x - w : x;
    out.push({text, x0: x0 - 1, y0: y - 10, x1: x0 + w + 1, y1: y + 3});
  }
  return out;
}
const PLAYABLE = ["little-round-top", "hougoumont-north-gate", "concord-north-bridge", "pegasus-bridge", "hill-223-patrol"];

test("label placement is deterministic, takes the first free place and hides a label with none", () => {
  const spot = (x: number, y: number): LabelPlace => ({x, y, anchor: "start"});
  const a: LabelSpec = {key: "a", priority: 1, text: "Alpha", candidates: [spot(10, 20), spot(10, 60)]};
  const b: LabelSpec = {key: "b", priority: 0, text: "Bravo", candidates: [spot(10, 20), spot(10, 60)]};
  const entries = (specs: LabelSpec[], obstacles: Rect[] = []): unknown => [...placeLabels(specs, obstacles).entries()];
  assert.deepEqual(entries([a, b]), [["b", spot(10, 20)], ["a", spot(10, 60)]], "the lower priority number takes the shared first place");
  assert.deepEqual(entries([b, a]), entries([a, b]), "the input order does not matter");
  assert.deepEqual(entries([{...b, priority: 1}, a]), [["a", spot(10, 20)], ["b", spot(10, 60)]], "equal priority: the lower key goes first");
  assert.deepEqual(entries([a], [{x0: 0, y0: 0, x1: 200, y1: 30}]), [["a", spot(10, 60)]], "an obstacle sends the label to its next place");
  assert.deepEqual(entries([a], [{x0: 0, y0: 0, x1: 200, y1: 30}, {x0: 0, y0: 40, x1: 200, y1: 90}]), [["a", null]], "no free place hides the label");
  assert.deepEqual(entries([{...a, candidates: [spot(10, 20)]}, {...b, candidates: [spot(10, 20)]}]), [["b", spot(10, 20)], ["a", null]],
    "of two labels that want one place the higher-numbered priority is hidden");
});

test("no feature label meets another label or a counter on the five playable scenarios", () => {
  for (const id of PLAYABLE) {
    const list = features(id), plain = featureLayer(list, options(id));
    const labels = drawnLabels(plain);
    assert.ok(labels.length > 0, id);
    assert.doesNotMatch(plain, /data-label="hidden"/, `${id}: no label hidden without counters`);
    // Worst case: a 74 x 34 counter centred on every mark's hex.
    const counters: Rect[] = list.flatMap((f) => ("pos" in f ? [f.pos] : f.points)).map((p) => hexCenter(p, RADIUS))
      .map(([x, y]) => ({x0: x - 37, y0: y - 17, x1: x + 37, y1: y + 17}));
    const crowded = drawnLabels(featureLayer(list, {...options(id), obstacles: counters}));
    for (const set of [labels, crowded]) for (let i = 0; i < set.length; i++) {
      for (let j = i + 1; j < set.length; j++) assert.ok(!meet(set[i]!, set[j]!), `${id}: "${set[i]!.text}" meets "${set[j]!.text}"`);
    }
    for (const label of crowded) for (const c of counters) assert.ok(!meet(label, c), `${id}: a counter covers "${label.text}"`);
  }
});

test("the POC desk and this desk place labels alike with the same counters in the way", () => {
  const id = "pegasus-bridge", list = features(id);
  const obstacles: Rect[] = [{x0: 380, y0: 440, x1: 460, y1: 480}, {x0: 880, y0: 400, x1: 960, y1: 440}];
  assert.equal(featureLayer(list, {...options(id), obstacles}),
    pocCall("BattleFeatures.render(args[0], center, esc, args[1])", [list, {...pocOptions(id), obstacles}]));
});
