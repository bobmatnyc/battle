// Slice 2 (docs/research/71): the full order catalog, the unknown-outcome re-read,
// the unit card, dispatches and the scenario choice, all from the commander view.
import assert from "node:assert/strict";
import {test} from "node:test";
import {orderSubmission, parse, readScenarioList, type CommanderOrder, type CommanderState} from "@battle/contracts";
import {orderBody, orderOutcome, templateFor} from "../src/orders.ts";
import {dispatchesMarkup, missionMarkup, outcomeText, scenarioOptions, templateHelp, templateOptions, unitCardMarkup} from "../src/panels.ts";
import {ordersMarkup} from "../src/render.ts";
import {commander, raw} from "./fixtures.ts";

const clock = (turn: number): string => `T${turn}`;

test("every template in the view's catalog builds a body with the inputs it needs", () => {
  const view = commander();
  const unit = view.units[0]!;
  const ids = view.order_templates.map((t) => t.id);
  assert.deepEqual(ids, ["hold", "move", "rest", "retreat", "resupply", "recon", "dig_in", "hold_fire", "open_fire"]);
  for (const template of view.order_templates) {
    const noHex = orderBody(view, {unitId: unit.id, destination: null}, template.id);
    const withHex = orderBody(view, {unitId: unit.id, destination: [12, 14]}, template.id);
    if (template.destination === "hex") {
      assert.equal(noHex, null, `${template.id} waits for a destination hex`);
      assert.deepEqual(withHex?.orders, [{unit_id: unit.id, stance: template.id, destination: [12, 14]}]);
    } else {
      // "none" and "supply": the template selects its own position, so no destination is sent.
      assert.deepEqual(noHex?.orders, [{unit_id: unit.id, stance: template.id, destination: null}], template.id);
      assert.deepEqual(withHex, noHex, `${template.id} ignores a chosen hex`);
    }
    if (withHex) assert.deepEqual(parse(orderSubmission, withHex), withHex);
  }
});

test("an order names the view's cursor, and none is built for a template the view lacks or a routed unit", () => {
  const view = commander();
  const unit = view.units[0]!;
  const body = orderBody(view, {unitId: unit.id, destination: null}, "hold_fire");
  assert.equal(body?.game_id, view.game_id);
  assert.equal(body?.revision, view.revision);
  assert.equal(orderBody(view, {unitId: unit.id, destination: null}, "close_gate"), null, "Little Round Top has no gate");
  assert.equal(templateFor(view, "close_gate"), undefined);
  const routed = {...view, units: [{...unit, status: "routed"}, ...view.units.slice(1)]};
  assert.equal(orderBody(routed, {unitId: unit.id, destination: null}, "hold"), null);
  const contact = view.contacts[0]!;
  assert.equal(orderBody(view, {unitId: contact.id, destination: null}, "hold"), null, "a contact takes no orders");
});

function withOrder(view: CommanderState, order: Partial<CommanderOrder>): CommanderState {
  const base = view.orders[0]!;
  return {...view, revision: view.revision + 1, orders: [...view.orders, {...base, ...order} as CommanderOrder]};
}

test("after an unknown outcome the re-read state decides what the player is told", () => {
  const before = commander();
  const unit = before.units[1]!;
  const taken = withOrder(before, {id: "O9", unit_id: unit.id, stance: "hold_fire", status: "en_route"});
  const found = orderOutcome(before, taken, unit.id, "hold_fire");
  assert.equal(found.kind, "unknown");
  assert.match(found.text, /did not answer in time/);
  assert.match(found.text, /O9/);
  assert.match(found.text, /did take/);

  const missing = orderOutcome(before, before, unit.id, "hold_fire");
  assert.equal(missing.kind, "unknown");
  assert.match(missing.text, /outcome is unknown/);
  assert.match(missing.text, /no new order/);
  // An order for another unit is not mistaken for this one.
  const other = withOrder(before, {id: "O9", unit_id: "U3", stance: "hold_fire"});
  assert.match(orderOutcome(before, other, unit.id, "hold_fire").text, /no new order/);
});

test("the unit card shows the commander view's report, with energy as 100 - fatigue", () => {
  const view = commander();
  const unit = view.units[0]!;
  const html = unitCardMarkup(view, unit, clock);
  const field = (name: string): string => html.match(new RegExp(`data-field="${name}"><dt>[^<]*</dt><dd>([^<]*)</dd>`))?.[1] ?? "";
  assert.equal(field("strength"), `${unit.strength} / ${unit.initial}`);
  assert.equal(field("morale"), `${unit.morale}%`);
  assert.equal(field("ammo"), String(unit.ammo));
  assert.equal(field("energy"), `${100 - unit.fatigue}%`);
  assert.equal(field("skill"), `${String(unit["skill"])}%`);
  assert.equal(field("posture"), "Open fire");
  assert.equal(field("mission"), "Hold and defend");
  assert.match(html, /ACTIVE · Instructions received\./);
  assert.match(html, /Reported T9/);
  assert.doesNotMatch(html, /\bturn\b|revision/i);
});

test("dispatches are listed newest first with battlefield times, and the order list shows delivery", () => {
  const view = commander();
  const html = dispatchesMarkup(view, clock);
  const items = html.match(/<li/g) ?? [];
  assert.equal(items.length, view.dispatches.length);
  const newest = view.dispatches.at(-1)!;
  assert.ok(html.indexOf(newest.display_text.slice(0, 30).replace(/'/g, "&#39;")) < html.indexOf("Instructions to hold position"));
  assert.match(html, /received T0/);
  assert.equal(dispatchesMarkup({...view, dispatches: []}, clock), "<li>No dispatches received.</li>");
  const order = view.orders[0]!;
  const enRoute = {...view, orders: [{...order, status: "en_route", arrival_turn: 3}]};
  assert.match(ordersMarkup(enRoute, clock), /Hold and defend · en route · sent T0 · due T3/);
  assert.match(ordersMarkup(view, clock), /delivered · sent T0$|delivered · sent T0<\/li>/);
});

test("the order form offers the catalog with its intent and effect, and resupply names the briefed point", () => {
  const view = commander();
  const options = templateOptions(view, "hold_fire");
  assert.equal((options.match(/<option/g) ?? []).length, view.order_templates.length);
  assert.match(options, /<option value="hold_fire" selected>Hold fire<\/option>/);
  const resupply = templateHelp(view, templateFor(view, "resupply")!);
  assert.match(resupply, /ammunition point/i);
  assert.match(resupply, new RegExp(`${view.supply_sites[0]!.name} · hex ${view.supply_sites[0]!.pos.join(",")}`));
  assert.match(templateHelp(view, templateFor(view, "move")!), /click a destination hex/i);
});

test("the scenario choice lists the catalog and marks the battle being played", () => {
  const list = readScenarioList(raw("scenarios"));
  const html = scenarioOptions(list, "hougoumont-north-gate");
  assert.equal((html.match(/<option/g) ?? []).length, 3);
  assert.match(html, /<option value="concord-north-bridge">Concord North Bridge · 1775-04-19<\/option>/);
  assert.match(html, /<option value="hougoumont-north-gate" selected>Hougoumont: the north gate · 1815-06-18<\/option>/);
  assert.match(missionMarkup(commander()), /<b>17:00<\/b>/, "the brief's bold marks become <b>, the rest is escaped");
});

test("a finished battle shows the brief's headline for the player's side, with the reason", () => {
  const view = commander();
  assert.equal(outcomeText(view), null, "no headline while the battle is active");
  const done = (winner: string): CommanderState => ({...view, status: "complete", winner, reason: "Held to the deadline."});
  const outcomes = view.scenario_brief!.outcomes;
  assert.deepEqual(outcomeText(done(view.side)), {headline: outcomes.win, reason: "Held to the deadline."});
  assert.equal(outcomeText(done(view.scenario_brief!.opponent.id))?.headline, outcomes.loss);
  assert.equal(outcomeText(done("draw"))?.headline, outcomes.draw);
  const {scenario_brief: _omitted, ...bare} = done(view.side);
  assert.equal(outcomeText(bare as CommanderState)?.headline, "Battle complete.");
});
