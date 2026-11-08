// The desk's pure parts: battlefield time, hex geometry, selection and the order body.
import assert from "node:assert/strict";
import {test} from "node:test";
import {orderSubmission, parse} from "@battle/contracts";
import {battleClock} from "../src/timeline.ts";
import {hexCenter} from "../src/geometry.ts";
import {clickMap, emptySelection} from "../src/selection.ts";
import {orderBody} from "../src/orders.ts";
import {commander, map} from "./fixtures.ts";

test("battlefield time is the scenario's local time in every browser time zone", () => {
  const view = commander();
  const setting = map().setting;
  const seen = new Set<string>();
  const before = process.env["TZ"];
  try {
    for (const zone of ["UTC", "Pacific/Kiritimati", "America/Los_Angeles", "Asia/Kolkata"]) {
      process.env["TZ"] = zone;
      seen.add(JSON.stringify(battleClock(setting, view.turn, view.seconds_per_turn)));
    }
  } finally {
    if (before === undefined) delete process.env["TZ"]; else process.env["TZ"] = before;
  }
  assert.equal(seen.size, 1);
  // Turn 12 of 30 s intervals after 16:30.
  assert.deepEqual(battleClock(setting, view.turn, view.seconds_per_turn), {
    time: "16:36", date: "Thursday, 2 July 1863", location: "Little Round Top · Gettysburg, Pennsylvania",
  });
  assert.equal(battleClock(setting, 1, 15).time, "16:30:15");
  // The desk passes the view's display_locale, as the POC desk does.
  assert.equal(battleClock(setting, 0, 30, view.display_locale).date, "Thursday, July 2, 1863");
});

test("hex centres follow the POC's offset-row layout", () => {
  assert.deepEqual(hexCenter([0, 0], 25.5).map(Math.round), [24, 26]);
  const [oddX] = hexCenter([0, 1], 25.5);
  const [evenX] = hexCenter([0, 2], 25.5);
  assert.ok(oddX > evenX, "odd rows shift right by half a hex");
});

test("a friendly counter selects, a hex sets the destination, and the order body passes the contract", () => {
  const view = commander();
  const own = view.units[0]!;
  let step = clickMap(view, emptySelection, {kind: "hex", pos: [3, 3]});
  assert.equal(step.selection.unitId, null);
  assert.equal(step.notice?.kind, "info");

  step = clickMap(view, step.selection, {kind: "unit", id: own.id});
  assert.deepEqual(step.selection, {unitId: own.id, destination: null});
  assert.equal(orderBody(view, step.selection, "move"), null, "no destination yet");

  step = clickMap(view, step.selection, {kind: "hex", pos: [12, 14]});
  assert.deepEqual(step.selection.destination, [12, 14]);
  const body = orderBody(view, step.selection, "move");
  assert.deepEqual(body, {
    orders: [{unit_id: own.id, stance: "move", destination: [12, 14]}],
    game_id: view.game_id, revision: view.revision,
  });
  assert.deepEqual(parse(orderSubmission, body), body);
});

test("a contact is shown, never selected for orders", () => {
  const view = commander();
  const own = view.units[0]!;
  const contact = view.contacts[0]!;
  const selected = clickMap(view, emptySelection, {kind: "unit", id: own.id}).selection;
  const step = clickMap(view, selected, {kind: "contact", id: contact.id});
  assert.deepEqual(step.selection, selected);
  assert.match(step.notice?.text ?? "", /estimate/);
  // An id that is not one of the player's units (e.g. a contact id) never selects.
  assert.equal(clickMap(view, emptySelection, {kind: "unit", id: contact.id}).selection.unitId, null);
});

test("a routed or lost unit takes no move order", () => {
  const view = commander();
  const own = {...view.units[0]!, status: "routed"};
  const routed = {...view, units: [own, ...view.units.slice(1)]};
  const selection = {unitId: own.id, destination: [12, 14] as [number, number]};
  assert.equal(orderBody(routed, selection, "move"), null);
});
