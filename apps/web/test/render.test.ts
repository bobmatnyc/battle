// The desk's markup is drawn from the commander view only.
import assert from "node:assert/strict";
import {test} from "node:test";
import {contactsMarkup, mapMarkup, ordersMarkup} from "../src/render.ts";
import {commander, map} from "./fixtures.ts";

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
