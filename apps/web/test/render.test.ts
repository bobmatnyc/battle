// The desk's markup is drawn from the commander view only.
import assert from "node:assert/strict";
import {test} from "node:test";
import {contactsMarkup, mapMarkup, ordersMarkup} from "../src/render.ts";
import {statusTableFor} from "../src/feature-sources.ts";
import {hexCenter} from "../src/geometry.ts";
import {commander, map, pocFeatureSources} from "./fixtures.ts";

const count = (text: string, pattern: RegExp): number => (text.match(pattern) ?? []).length;

test("the map draws every cell and the player's own counters", () => {
  const view = commander();
  const terrain = map();
  const svg = mapMarkup(view, terrain, {unitId: null, destination: null});
  assert.equal(count(svg, /<polygon class="hex/g), terrain.cells.length);
  assert.equal(count(svg, /data-unit="/g), view.units.length);
  for (const unit of view.units) {
    assert.ok(svg.includes(`data-unit="${unit.id}"`), unit.id);
    assert.ok(svg.includes(`${unit.strength} INF`) || svg.includes(`${unit.strength} SC`), unit.id);
  }
});

test("enemy counters come from contacts and carry no exact values", () => {
  const view = commander();
  const svg = mapMarkup(view, map(), {unitId: null, destination: null});
  assert.equal(count(svg, /data-contact="/g), view.contacts.length);
  const contact = view.contacts[0]!;
  const marker = svg.slice(svg.indexOf(`data-contact="${contact.id}"`));
  const end = marker.indexOf("</g>");
  const drawn = marker.slice(0, end);
  assert.ok(drawn.includes(contact.estimate), "the estimate is shown");
  assert.match(drawn, /S\? E\? M\?/, "unknown skill, energy and morale stay unknown");
  const list = contactsMarkup(view, () => "16:34");
  assert.ok(list.includes(contact.estimate));
  assert.ok(list.includes(`${contact.confidence} confidence`));
});

test("a selected counter and its destination are marked", () => {
  const view = commander();
  const id = view.units[0]!.id;
  const svg = mapMarkup(view, map(), {unitId: id, destination: [12, 14]});
  assert.match(svg, new RegExp(`class="counter friendly selected" data-unit="${id}"[^>]*aria-pressed="true"`));
  assert.match(svg, /class="hex destination" data-c="12" data-r="14"/);
});

test("orders show battlefield times, not turns or revisions", () => {
  const view = commander();
  const html = ordersMarkup(view, (turn) => `T${turn}`);
  for (const order of view.orders) assert.ok(html.includes(`${order.unit_id} · ${order.stance}`), order.id);
  assert.ok(html.includes("sent T0"));
  assert.doesNotMatch(html, /turn|revision/i);
});

test("text from the server is escaped", () => {
  const view = commander();
  const hostile = {...view, units: [{...view.units[0]!, name: "<img src=x onerror=alert(1)>"}]};
  const svg = mapMarkup(hostile, map(), {unitId: null, destination: null});
  assert.ok(!svg.includes("<img"));
  assert.ok(svg.includes("&lt;img"));
});

test("the map draws the commander view's features above the hexes and below the counters, with status in each hex tooltip", () => {
  const view = commander();
  const sources = statusTableFor(pocFeatureSources(), view.scenario_brief?.id);
  const svg = mapMarkup(view, map(), {unitId: null, destination: null}, sources);
  const layer = svg.indexOf("<g class=\"battle-features\"");
  assert.ok(layer > svg.lastIndexOf("<polygon class=\"hex"), "features are drawn over the hexes");
  assert.ok(layer < svg.indexOf("<g class=\"units\">"), "counters stay on top");
  assert.equal(count(svg, /class="feature-mark feature-road"/g), view.map_features.filter((f) => f.kind === "road").length);
  assert.equal(count(svg, /<rect class="footprint"/g), view.map_features.filter((f) => f.kind === "building").length);
  const farm = view.map_features.find((f) => f.id === "farmstead") as {pos: [number, number]};
  assert.match(svg, new RegExp(`data-c="${farm.pos[0]}" data-r="${farm.pos[1]}"[^>]*><title>Hex ${farm.pos.join(",")} [^<]*· Farmstead \\(Illustrative: `));
});

test("water and marsh cells have their own fill", () => {
  const terrain = map();
  terrain.cells[0] = {...terrain.cells[0]!, terrain: "water"};
  terrain.cells[1] = {...terrain.cells[1]!, terrain: "marsh"};
  const svg = mapMarkup(commander(), terrain, {unitId: null, destination: null});
  assert.match(svg, /data-c="0" data-r="0"[^>]*fill="#b9d3e3"/);
  assert.match(svg, /data-c="1" data-r="0"[^>]*fill="#d7e3cf"/);
});

// bt-T11: the POC desk's dashed ring round a hold-objective objective and its neighbours.
const RING = /<circle class="objective-ring" pointer-events="none" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"\/>/g;

test("a hold-objective brief rings the objective", () => {
  const view = commander();
  const terrain = map();
  assert.equal(view.scenario_brief?.objective.ring, true, "the recorded Little Round Top brief sets the ring");
  const rings = [...mapMarkup(view, terrain, {unitId: null, destination: null}).matchAll(RING)];
  assert.equal(rings.length, 1);
  const [cx, cy, radius] = rings[0]!.slice(1).map(Number) as [number, number, number];
  const [ox, oy] = hexCenter(view.objective, terrain.radius);
  assert.deepEqual([cx, cy], [Number(ox.toFixed(1)), Number(oy.toFixed(1))], "centred on the objective hex");
  assert.ok(Math.abs(radius - terrain.radius * 53 / 25.5) < 0.1, `the POC proportion, r=${radius}`);
  assert.ok(radius > Math.sqrt(3) * terrain.radius, "the six neighbouring hex centres lie inside the ring");
});

test("no ring without the brief's ring flag or without a brief", () => {
  const view = commander();
  const brief = view.scenario_brief!;
  const unringed = {...view, scenario_brief: {...brief, objective: {...brief.objective, ring: false}}};
  const {scenario_brief: _omitted, ...bare} = view;
  for (const shown of [unringed, bare]) {
    const svg = mapMarkup(shown, map(), {unitId: null, destination: null});
    assert.doesNotMatch(svg, /objective-ring/);
    assert.match(svg, /<g class="objective" pointer-events="none"><circle/, "the objective mark stays");
  }
});
