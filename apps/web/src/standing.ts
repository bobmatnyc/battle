// Standing orders on the desk (docs/research/81 §5, §12). Pure: no DOM, no network.
// The templates are the view's typed `standing_templates` (standing.catalog), so the desk offers
// exactly what the POC takes for this battle; Python still checks every rule (standing.issue).
import {
  parse, standingOrderSubmission, type CommanderState, type CommanderView, type StandingOrder,
  type StandingOrderSubmission, type UnitReport,
} from "@battle/contracts";
import {esc} from "./markup.ts";
import {reportedUnable} from "./orders.ts";
import {ownUnit, type Notice} from "./selection.ts";

// standing.deliver: an instruction with one of these statuses never took effect.
const VOID = new Set(["refused", "superseded", "expired"]);

const label = (view: CommanderView, id: unknown): string =>
  view.standing_templates.find((t) => t.id === id)?.label ?? String(id ?? "?");
const words = (status: string): string => status.replaceAll("_", " ");
const ofUnit = (view: CommanderView, unitId: string): StandingOrder[] =>
  view.standing_orders.filter((o) => o.unit_id === unitId).sort((a, b) => a.version - b.version);

/** The view's standing templates as `<option>`s, with `chosen` selected. */
export function standingOptions(view: CommanderView, chosen: string): string {
  return view.standing_templates.map((t) =>
    `<option value="${esc(t.id)}"${t.id === chosen ? " selected" : ""}>${esc(t.label)}</option>`).join("");
}

/** The template's intent, escaped; empty when the view does not offer `profileId`. */
export function standingHelp(view: CommanderView, profileId: string): string {
  return esc(view.standing_templates.find((t) => t.id === profileId)?.intent ?? "");
}

/** Why: a standing order goes to one of the player's own units, with a template the battle offers.
 * What: the request body at the view's cursor; null when `unitId` is not an own unit, the unit is
 * reported unable to take orders, or the view does not offer `profileId`.
 * Test: `a standing order body names the unit, template and cursor; none for an unknown template or a unit that cannot take orders`. */
export function standingBody(view: CommanderState, unitId: string | null, profileId: string): StandingOrderSubmission | null {
  const unit = ownUnit(view, unitId);
  if (!unit || reportedUnable(unit) || !view.standing_templates.some((t) => t.id === profileId)) return null;
  return parse(standingOrderSubmission, {instruction: {unit_id: unit.id, profile_id: profileId}, game_id: view.game_id, revision: view.revision});
}

/** Why: the engine cannot recall an instruction (standing.py has no cancel), but a newer one
 * supersedes it on arrival (standing.deliver). Cancelling is therefore sending the battle's first
 * template, the one every unit starts with (scenario_entry) and the engine's fallback (standing.profile).
 * What: that body when the unit's last instruction still in force or on its way (else its reported
 * template) is another template; null when it already is the first, or no body can be built.
 * Test: `cancel sends the battle's first template, and only while the unit's last instruction differs from it`. */
export function cancelBody(view: CommanderState, unitId: string | null): StandingOrderSubmission | null {
  const unit = ownUnit(view, unitId);
  const first = view.standing_templates[0];
  if (!unit || !first) return null;
  const last = ofUnit(view, unit.id).filter((o) => !VOID.has(o.status)).at(-1);
  const current = last?.profile_id ?? unit["standing_profile"];
  return current === undefined || current === first.id ? null : standingBody(view, unit.id, first.id);
}

/** Why: the player commands from reports; an instruction on its way has not taken effect.
 * What: the unit's reported template and version, then every instruction still awaiting its acknowledgement.
 * Test: `the unit's doctrine line names the reported template and any instruction still on its way`. */
export function standingCurrent(view: CommanderView, unit: UnitReport): string {
  const profile = unit["standing_profile"];
  const reported = profile === undefined ? "Reported: no standing instructions."
    : `Reported: ${label(view, profile)} (version ${String(unit["standing_version"] ?? "?")}).`;
  const waiting = ofUnit(view, unit.id).filter((o) => o.status === "awaiting_ack")
    .map((o) => `${o.id} ${label(view, o.profile_id)}, ${words(o.status)}`);
  return waiting.length ? `${reported} On its way: ${waiting.join("; ")}.` : reported;
}

/** Why: the player must see every standing instruction and whether it arrived.
 * What: the side's standing orders, newest first: unit, template, battlefield send time, status.
 * Test: `the standing orders list shows each instruction's unit, template, battlefield time and status, newest first`. */
export function standingListMarkup(view: CommanderView, clock: (turn: number) => string): string {
  if (!view.standing_orders.length) return "<li>No standing orders sent.</li>";
  return [...view.standing_orders].reverse().map((o) =>
    `<li data-standing="${esc(o.id)}">${esc(o.unit_id)} · ${esc(label(view, o.profile_id))} · sent ${esc(clock(o.sent_turn))} · ${esc(words(o.status))}`
    + ` <small>${esc(o.id)}</small></li>`).join("");
}

/** Why: a standing order the POC may have committed must not read as a failure (docs/research/71).
 * What: after a re-read, whether a standing order for `unitId` with `profileId` not in `before` is now on record.
 * Test: `after an unknown outcome the re-read decides what the player is told about a standing order`. */
export function standingOutcome(before: CommanderView, after: CommanderView, unitId: string, profileId: string): Notice {
  const known = new Set(before.standing_orders.map((o) => o.id));
  const found = after.standing_orders.find((o) => !known.has(o.id) && o.unit_id === unitId && o.profile_id === profileId);
  const slow = "The local simulation did not answer in time.";
  return found
    ? {kind: "unknown", text: `${slow} Re-reading the battle shows it did take the standing order: ${found.id}, ${unitId} ${label(after, profileId)}, ${words(found.status)}.`}
    : {kind: "unknown", text: `${slow} The outcome is unknown: re-reading the battle shows no new standing order for ${unitId}. Check the standing orders before sending it again.`};
}

/** The accepted notice: the new instruction the returned view holds for `unitId`. */
export function standingAccepted(before: CommanderView, after: CommanderView, unitId: string, profileId: string): Notice {
  const known = new Set(before.standing_orders.map((o) => o.id));
  const found = after.standing_orders.find((o) => !known.has(o.id) && o.unit_id === unitId);
  return {kind: "accepted", text: `Standing order sent: ${unitId} ${label(after, profileId)}${found ? ` (${found.id})` : ""}. `
    + "It takes effect when it arrives; the present mission continues. Start the clock to carry it."};
}
