// What a map click does to the desk's selection; orders.ts builds the order body.
// Pure: no DOM, no network. The server still checks every rule.
import type {CommanderView, UnitReport} from "@battle/contracts";

type Hex = [number, number];

export interface Selection { readonly unitId: string | null; readonly destination: Hex | null }
export const emptySelection: Selection = {unitId: null, destination: null};

export type MapTarget =
  | {kind: "unit"; id: string}
  | {kind: "contact"; id: string}
  | {kind: "hex"; pos: Hex};

// "unknown": the POC may or may not have taken a command (docs/research/71).
export type NoticeKind = "info" | "accepted" | "refusal" | "unknown";
export interface Notice { readonly kind: NoticeKind; readonly text: string }

export interface ClickResult { selection: Selection; notice: Notice | null }

/** The player's own unit `id`; undefined for anything else, a contact id included. */
export function ownUnit(view: CommanderView, id: string | null): UnitReport | undefined {
  return id === null ? undefined : view.units.find((unit) => unit.id === id && unit.side === view.side);
}

/** Why: a click must never turn an enemy sighting into something the player commands.
 * What: an own counter selects it; a hex sets the destination of the selection;
 * a contact leaves the selection as it was and says it is an estimate.
 * Test: `a friendly counter selects, a hex sets the destination, and the order body passes the contract`,
 * `a contact is shown, never selected for orders`. */
export function clickMap(view: CommanderView, selection: Selection, target: MapTarget): ClickResult {
  if (target.kind === "unit") {
    const unit = ownUnit(view, target.id);
    return unit
      ? {selection: {unitId: unit.id, destination: null}, notice: null}
      : {selection, notice: {kind: "info", text: "That counter is not under your command."}};
  }
  if (target.kind === "contact") {
    const contact = view.contacts.find((item) => item.id === target.id);
    const text = contact ? `${contact.id}: enemy estimate (${contact.estimate}); it takes no orders.` : "Unknown contact.";
    return {selection, notice: {kind: "info", text}};
  }
  if (!ownUnit(view, selection.unitId)) {
    return {selection: emptySelection, notice: {kind: "info", text: "Select one of your counters first."}};
  }
  return {selection: {...selection, destination: [target.pos[0], target.pos[1]]}, notice: null};
}
