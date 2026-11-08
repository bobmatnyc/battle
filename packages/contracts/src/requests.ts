// Request bodies of the desk's standing-order and formation commands (docs/research/81 §5, §6, §12):
// POST /api/standing-orders (standing.issue) and POST /api/formations (formations.validate).
// Each takes exactly the key set the Python code accepts; Python still checks every rule.
import {count, fail, hex, literal, nonEmpty, object, parse, refine, type Check} from "./check.ts";

type Hex = [number, number];

/** standing.issue: exactly `unit_id` and `profile_id`, a template id from the view's `standing_templates`. */
export interface StandingInstruction { unit_id: string; profile_id: string }
/** POST /api/standing-orders body: one instruction at the cursor the desk last read. */
export interface StandingOrderSubmission { instruction: StandingInstruction; game_id: string; revision: number }

/** Why: the relay must forward only what standing.issue accepts.
 * What: `{instruction: {unit_id, profile_id}, game_id, revision}`, no other key.
 * Test: `the recorded standing-order, split and combine bodies validate unchanged`,
 * `a malformed standing-order or formation request is rejected with the path of the bad field`. */
export const standingOrderSubmission: Check<StandingOrderSubmission> = object({
  instruction: object({unit_id: nonEmpty, profile_id: nonEmpty}), game_id: nonEmpty, revision: count,
});

/** formations.validate, split: troops `count` detach to the adjacent hex `destination`. */
export interface SplitInstruction { kind: "split"; unit_id: string; count: number; destination: Hex }
/** formations.validate, combine: `partner_id` joins `unit_id`, which survives. */
export interface CombineInstruction { kind: "combine"; unit_id: string; partner_id: string }
export type FormationInstruction = SplitInstruction | CombineInstruction;
/** POST /api/formations body: one split or combine at the cursor the desk last read. */
export interface FormationSubmission { instruction: FormationInstruction; game_id: string; revision: number }

const splitInstruction: Check<SplitInstruction> = object({kind: literal("split"), unit_id: nonEmpty, count, destination: hex});
const combineInstruction: Check<CombineInstruction> = refine(
  object({kind: literal("combine"), unit_id: nonEmpty, partner_id: nonEmpty}),
  (instruction, path) => {
    if (instruction.partner_id === instruction.unit_id) fail(`${path}.partner_id`, "expected a partner other than unit_id");
  });

// The `kind` picks the key set, as formations.validate does.
const formationInstruction: Check<FormationInstruction> = (input, path) => {
  if (typeof input !== "object" || input === null || Array.isArray(input)) return fail(path, "expected object");
  const kind = (input as Record<string, unknown>)["kind"];
  if (kind === "split") return splitInstruction(input, path);
  if (kind === "combine") return combineInstruction(input, path);
  return fail(`${path}.kind`, `expected one of ["split","combine"], got ${JSON.stringify(kind)}`);
};

/** Why: the relay must forward only what formations.validate accepts.
 * What: `{instruction, game_id, revision}`; a split instruction is exactly
 * `{kind, unit_id, count, destination}`, a combine exactly `{kind, unit_id, partner_id}` with a
 * partner other than the unit.
 * Test: `the recorded standing-order, split and combine bodies validate unchanged`,
 * `a malformed standing-order or formation request is rejected with the path of the bad field`. */
export const formationSubmission: Check<FormationSubmission> = object({
  instruction: formationInstruction, game_id: nonEmpty, revision: count,
});

export const readStandingOrderSubmission = (input: unknown): StandingOrderSubmission => parse(standingOrderSubmission, input);
export const readFormationSubmission = (input: unknown): FormationSubmission => parse(formationSubmission, input);
