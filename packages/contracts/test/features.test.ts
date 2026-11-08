// Contract test for the commander view's map_features (docs/research/73) against the
// recorded opening features of every catalog entry and the 12-interval fixtures.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {test} from "node:test";
import {ContractError, mapFeatures, parse, readCommanderState, readMapFeatures} from "../src/index.ts";

type Doc = Record<string, any>;
const load = (name: string): Doc => JSON.parse(readFileSync(new URL(`../fixtures/${name}`, import.meta.url), "utf8"));
const catalog: Record<string, Doc> = load("map-features.json");
const hougoumont = (): Doc[] => structuredClone(catalog["hougoumont-north-gate"]!["map_features"]);
const byId = (features: Doc[], id: string): Doc => features.find((f) => f["id"] === id)!;

function rejects(features: Doc[], edit: (features: Doc[]) => void, path: string): void {
  edit(features);
  assert.throws(() => parse(mapFeatures, features), (error: unknown) => {
    assert.ok(error instanceof ContractError, String(error));
    assert.equal(error.path, path, error.message);
    return true;
  });
}

test("every catalog entry's map features validate, and every kind is covered", () => {
  const kinds = new Set<string>();
  for (const [id, entry] of Object.entries(catalog)) {
    assert.deepEqual(readMapFeatures(entry["map_features"]), entry["map_features"], id);
    for (const f of entry["map_features"]) kinds.add(f["kind"]);
  }
  assert.deepEqual([...kinds].sort(), ["bridge", "building", "fortification", "road"]);
  const gate = byId(hougoumont(), "hougoumont");
  assert.equal(gate["openings"][0]["state"], "open", "Hougoumont's north gate is briefed open");
});

test("the commander fixtures' map features pass through the typed reader", () => {
  for (const name of ["state-commander.json"]) {
    const view = readCommanderState(load(name));
    assert.ok(view.map_features.some((f) => f.kind === "road" && f.points.length >= 2), name);
  }
});

test("map features refuse an unknown kind, an unknown key and a bad state with the path", () => {
  rejects(hougoumont(), (f) => { f[0]["kind"] = "tower"; }, "$[0].kind");
  rejects(hougoumont(), (f) => { byId(f, "north-lane")["width_m"] = 6; }, "$[0].width_m");
  rejects(hougoumont(), (f) => { delete byId(f, "north-lane")["points"]; }, "$[0].points");
  rejects(hougoumont(), (f) => { byId(f, "north-lane")["points"] = [[3, 2]]; }, "$[0].points");
  const building = hougoumont().findIndex((f) => f["id"] === "hougoumont");
  rejects(hougoumont(), (f) => { f[building]["openings"][0]["state"] = "ajar"; }, `$[${building}].openings[0].state`);
  rejects(hougoumont(), (f) => { f[building]["openings"][0]["guard"] = "C1"; }, `$[${building}].openings[0].guard`);
  // A gate needs the compound it opens.
  rejects(hougoumont(), (f) => { delete f[building]["compound"]; }, `$[${building}].compound`);
  rejects(hougoumont(), (f) => { f[building]["pos"] = [11]; }, `$[${building}].pos`);
  const pegasus = (): Doc[] => structuredClone(catalog["pegasus-bridge"]!["map_features"]);
  const bridge = pegasus().findIndex((f) => f["kind"] === "bridge");
  rejects(pegasus(), (f) => { f[bridge]["state"] = "wobbly"; }, `$[${bridge}].state`);
  const works = (): Doc[] => structuredClone(catalog["little-round-top"]!["map_features"]);
  const dug = works().findIndex((f) => f["kind"] === "fortification");
  rejects(works(), (f) => { f[dug]["progress"] = 101; }, `$[${dug}].progress`);
  rejects(works(), (f) => { f[dug]["truth"] = {cover: 70}; }, `$[${dug}].truth`);
});

test("map features accept works dug in battle and a gate in each known state", () => {
  const features = hougoumont();
  features.push({id: "works-5,5", kind: "fortification", name: "Hasty fieldworks", pos: [5, 5], base_cover: 10,
    cover: 25, progress: 50, effort: 200, required: 400, updated_turn: 3, briefed: false,
    provenance: "simulation-built", observed_turn: 3, received_turn: 4});
  for (const state of ["open", "closing", "closed", "barred", "forced"]) {
    byId(features, "hougoumont")["openings"][0] = {...byId(features, "hougoumont")["openings"][0], state, updated_turn: 2};
    assert.deepEqual(readMapFeatures(features), features, state);
  }
});
