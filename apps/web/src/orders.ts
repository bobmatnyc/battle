// The order catalog as the desk uses it (docs/research/71). Pure: no DOM, no network.
// The catalog is the view's `order_templates` (apps/poc orders.catalog), so the desk
// offers exactly the kinds the POC takes for this battle; Python still checks every rule.
import {
  orderSubmission, parse, type CommanderView, type OrderSubmission, type OrderTemplate, type UnitReport,
} from "@battle/contracts";
import {ownUnit, type Notice, type Selection} from "./selection.ts";

const UNORDERABLE = new Set(["routed", "lost", "merged"]);

/** True when headquarters' report bars orders to `unit` (engine.report_refusal: routed, lost,
 * merged or leaderless); standing orders and formations use it (docs/research/81 §12). */
export const reportedUnable = (unit: UnitReport): boolean => UNORDERABLE.has(unit.status) || unit["leaderless"] === true;

/** The view's template `id`, or undefined when this battle does not offer it. */
export function templateFor(view: CommanderView, id: string): OrderTemplate | undefined {
  return view.order_templates.find((template) => template.id === id);
}

/** Why: each order kind needs different inputs; a hex template needs a destination, the rest none.
 * What: one order for the selected own unit at the view's cursor. A "hex" template sends the
 * chosen destination; "none" and "supply" send `destination: null`, as the POC desk does
 * (orders.validate refuses a destination for them; resupply picks its own point).
 * Null when the template is not offered, the unit is not the player's or is reported
 * routed, lost or merged, or a hex template has no destination yet.
 * Test: `every template in the view's catalog builds a body with the inputs it needs`,
 * `an order names the view's cursor, and none is built for a template the view lacks or a routed unit`. */
export function orderBody(view: CommanderView & {game_id: string}, selection: Selection, templateId: string): OrderSubmission | null {
  const unit = ownUnit(view, selection.unitId);
  const template = templateFor(view, templateId);
  if (!unit || !template || UNORDERABLE.has(unit.status)) return null;
  const hex = template.destination === "hex";
  if (hex && !selection.destination) return null;
  return parse(orderSubmission, {
    orders: [{unit_id: unit.id, stance: template.id, destination: hex ? selection.destination : null}],
    game_id: view.game_id, revision: view.revision,
  });
}

/** Why: a POST the relay gave up on may still have been committed by the POC (review #6).
 * What: after the desk re-reads state, says whether an order for `unitId` with `stance` that
 * was not in `before` is now on record, and that the outcome was not confirmed at the time.
 * Test: `after an unknown outcome the re-read state decides what the player is told`. */
export function orderOutcome(before: CommanderView, after: CommanderView, unitId: string, stance: string): Notice {
  const known = new Set(before.orders.map((order) => order.id));
  const found = after.orders.find((order) => !known.has(order.id) && order.unit_id === unitId && order.stance === stance);
  const slow = "The local simulation did not answer in time.";
  if (found) {
    return {kind: "unknown", text: `${slow} Re-reading the battle shows it did take the order: ${found.id}, ${unitId} ${stance}, ${found.status.replaceAll("_", " ")}.`};
  }
  return {kind: "unknown", text: `${slow} The outcome is unknown: re-reading the battle shows no new order for ${unitId}. Check the order list before sending it again.`};
}
