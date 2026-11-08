// Split and combine on the desk (docs/research/81 §6, §12). Pure: no DOM, no network.
// The desk refuses, in the engine's own words, every request formations.validate would refuse on
// what the commander view shows; the rest (walls, water, rules edition, an unreported unit) the
// engine refuses and the desk shows its text. `the desk's formation limits and refusal texts are
// the engine's own` pins every constant and text below to apps/poc/battle.
import {
  formationSubmission, parse, type CommanderState, type CommanderView, type FormationInstruction,
  type FormationSubmission, type UnitReport,
} from "@battle/contracts";
import {hexDistance} from "./geometry.ts";
import {esc} from "./markup.ts";
import {reportedUnable} from "./orders.ts";
import {ownUnit, type Notice} from "./selection.ts";

type Hex = [number, number];

/** formations.MIN_STRENGTH / MAX_STRENGTH / PROFILE. */
export const MIN_STRENGTH = 12;
export const MAX_STRENGTH = 80;
export const PROFILE = ["unit_type", "weapon_class", "skill", "recon_role", "recon_skill"] as const;

/** The engine's refusal texts (formations.validate, engine.validate_order). */
export const REFUSALS = {
  outside: "That unit is outside your command.",
  unable: "That unit is reported unable to accept orders.",
  same: "Choose two different formations.",
  fixed: "A formation with a declared rout_strength, gun facing, surrender or exploit rule, or holding captives, "
    + "cannot split or combine.",
  count: "Each resulting formation needs at least 12 reported troops.",
  adjacent: "Select an adjacent hex for the detached formation.",
  occupied: "That hex is reported occupied by a friendly formation.",
  mismatch: "Combine requires matching troops, weapons, proficiency and reconnaissance roles.",
  apart: "Move the formations into adjacent hexes before combining.",
  tooStrong: "Combined strength may not exceed 80 troops.",
  headquarters: "Select the headquarters unit as the surviving formation.",
} as const;

const GONE = new Set(["lost", "merged"]);
// Of formations.FIXED_KEYS only captives reach the commander view (engine.summary).
const fixed = (unit: UnitReport): boolean => Boolean(unit["captives"]);

/** The POC desk's default split: half the reported strength, rounded down. */
export const defaultSplit = (unit: UnitReport): number => Math.floor(unit.strength / 2);

/** Why: the desk must not send a split the engine would refuse on what headquarters knows.
 * What: the engine's refusal text for splitting `count` troops of `unit` to `destination`, in
 * formations.validate's order, or null: the unit must take orders and hold no captives, each part
 * keeps at least MIN_STRENGTH, the hex is adjacent and no reported friendly formation stands on it.
 * Test: `split refusals use the engine's words: count bounds, an adjacent hex, a free hex`. */
export function splitRefusal(view: CommanderView, unit: UnitReport, count: number, destination: Hex | null): string | null {
  if (reportedUnable(unit)) return REFUSALS.unable;
  if (fixed(unit)) return REFUSALS.fixed;
  if (!Number.isInteger(count) || count < MIN_STRENGTH || unit.strength - count < MIN_STRENGTH) return REFUSALS.count;
  if (!destination || hexDistance(unit.pos, destination) !== 1) return REFUSALS.adjacent;
  const [c, r] = destination;
  if (view.units.some((u) => u.pos[0] === c && u.pos[1] === r && !GONE.has(u.status))) return REFUSALS.occupied;
  return null;
}

/** Why: the desk must not offer a combine the engine would refuse; a merged unit is never a partner.
 * What: the engine's refusal text for `partnerId` joining `unit` (which survives), in
 * formations.validate's order, or null: two different own units that take orders and hold no
 * captives, matching PROFILE, adjacent, together at most MAX_STRENGTH, and the partner is not headquarters.
 * Test: `combine partners are the adjacent own formations the engine would accept`. */
export function combineRefusal(view: CommanderView, unit: UnitReport, partnerId: string): string | null {
  if (partnerId === unit.id) return REFUSALS.same;
  const partner = ownUnit(view, partnerId);
  if (!partner) return REFUSALS.outside;
  if (reportedUnable(unit) || reportedUnable(partner)) return REFUSALS.unable;
  if (fixed(unit) || fixed(partner)) return REFUSALS.fixed;
  if (!PROFILE.every((key) => unit[key] === partner[key])) return REFUSALS.mismatch;
  if (hexDistance(unit.pos, partner.pos) !== 1) return REFUSALS.apart;
  if (unit.strength + partner.strength > MAX_STRENGTH) return REFUSALS.tooStrong;
  if (partner.id === view.command.unit_id) return REFUSALS.headquarters;
  return null;
}

/** The own units `unit` could absorb now: those `combineRefusal` accepts. */
export function combinePartners(view: CommanderView, unit: UnitReport): UnitReport[] {
  return view.units.filter((u) => u.side === view.side && u.id !== unit.id && combineRefusal(view, unit, u.id) === null);
}

const submission = (view: CommanderState, instruction: FormationInstruction): FormationSubmission =>
  parse(formationSubmission, {instruction, game_id: view.game_id, revision: view.revision});

/** The split body at the view's cursor; null when `splitRefusal` refuses it or `unitId` is not an own unit. */
export function splitBody(view: CommanderState, unitId: string | null, count: number, destination: Hex | null): FormationSubmission | null {
  const unit = ownUnit(view, unitId);
  if (!unit || !destination || splitRefusal(view, unit, count, destination)) return null;
  return submission(view, {kind: "split", unit_id: unit.id, count, destination: [destination[0], destination[1]]});
}

/** The combine body at the view's cursor; null when `combineRefusal` refuses it or `unitId` is not an own unit. */
export function combineBody(view: CommanderState, unitId: string | null, partnerId: string): FormationSubmission | null {
  const unit = ownUnit(view, unitId);
  if (!unit || combineRefusal(view, unit, partnerId)) return null;
  return submission(view, {kind: "combine", unit_id: unit.id, partner_id: partnerId});
}

/** The partners `combinePartners` accepts, as `<option>`s with their reported strength. */
export function partnerOptions(partners: readonly UnitReport[], chosen: string): string {
  return partners.map((u) =>
    `<option value="${esc(u.id)}"${u.id === chosen ? " selected" : ""}>${esc(u.id)} · ${u.strength} troops</option>`).join("");
}

/** Why: the player should know what a split or combine needs before sending it, in the engine's words.
 * What: the split line (click an adjacent hex, the engine's refusal, or what will be sent), the
 * combine line (who survives, or why no partner qualifies) and the regrouping delay.
 * Test: `the formation help says what a split and a combine need, in the engine's words`. */
export function formationHelp(view: CommanderView, unit: UnitReport, count: number, destination: Hex | null): string {
  const why = splitRefusal(view, unit, count, destination);
  const split = !destination && why === REFUSALS.adjacent ? "Split: click an adjacent hex for the detached troops."
    : why ? `Split: ${why}` : `Split: ${count} troops to hex ${destination!.join(",")}.`;
  const combine = combinePartners(view, unit).length ? `Combine: the partner joins ${unit.id}, which survives.`
    : "Combine: no adjacent formation can join this one (matching troops, weapons, proficiency and role; "
      + `at most ${MAX_STRENGTH} troops together; headquarters only as the survivor).`;
  return `${split} ${combine} Regrouping takes sixty seconds after the instructions arrive.`;
}

const words = (status: string): string => status.replaceAll("_", " ");
const what = (o: {kind: string; unit_id: string; partner_id?: string | undefined; count?: number | undefined; destination?: Hex | undefined}): string =>
  o.kind === "combine" ? `combine ${o.unit_id} + ${o.partner_id ?? "?"}`
    : `split ${o.unit_id}${o.count !== undefined ? ` (${o.count} to hex ${o.destination?.join(",") ?? "?"})` : ""}`;

/** Why: a split or combine takes effect only after its instructions arrive and the units regroup;
 * the player learns the result from the last notice (formations.observed).
 * What: the side's operations, newest first: id, kind, units, status, battlefield send time, and the notice's reason.
 * Test: `the operations list shows each split or combine with its units, status and last notice`. */
export function operationsMarkup(view: CommanderView, clock: (turn: number) => string): string {
  if (!view.formation_ops.length) return "<li>No split or combine sent.</li>";
  return [...view.formation_ops].reverse().map((o) =>
    `<li data-operation="${esc(o.id)}">${esc(o.id)} · ${esc(what(o))} · ${esc(words(o.status))} · sent ${esc(clock(o.sent_turn))}`
    + (o.reason ? `<br><small>${esc(o.reason)}</small>` : "") + "</li>").join("");
}

const isNew = (before: CommanderView, instruction: FormationInstruction) => {
  const known = new Set(before.formation_ops.map((o) => o.id));
  return (o: CommanderView["formation_ops"][number]): boolean =>
    !known.has(o.id) && o.kind === instruction.kind && o.unit_id === instruction.unit_id;
};

/** Why: a split or combine the POC may have committed must not read as a failure (docs/research/71).
 * What: after a re-read, whether a new operation of the same kind for the same unit is now on record.
 * Test: `after an unknown outcome the re-read decides what the player is told about a split or combine`. */
export function formationOutcome(before: CommanderView, after: CommanderView, instruction: FormationInstruction): Notice {
  const found = after.formation_ops.find(isNew(before, instruction));
  const slow = "The local simulation did not answer in time.";
  return found
    ? {kind: "unknown", text: `${slow} Re-reading the battle shows it did take the ${instruction.kind}: ${found.id}, ${instruction.unit_id}, ${words(found.status)}.`}
    : {kind: "unknown", text: `${slow} The outcome is unknown: re-reading the battle shows no new ${instruction.kind} for ${instruction.unit_id}. `
      + "Check the operations list before sending it again."};
}

/** The accepted notice, naming the operation the returned view holds. */
export function formationAccepted(before: CommanderView, after: CommanderView, instruction: FormationInstruction): Notice {
  const id = after.formation_ops.find(isNew(before, instruction))?.id;
  const tag = id ? ` (${id})` : "";
  const text = instruction.kind === "split"
    ? `Split sent: ${instruction.unit_id} detaches ${instruction.count} troops to hex ${instruction.destination.join(",")}${tag}.`
    : `Combine sent: ${instruction.partner_id} joins ${instruction.unit_id}${tag}.`;
  return {kind: "accepted", text: `${text} Regrouping takes sixty seconds after the instructions arrive; start the clock.`};
}
