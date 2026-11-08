// The status of each drawn map mark comes from the POC's presentation-only table,
// apps/poc/static/feature-sources.js (docs/research/72 §3), loaded unchanged as a classic
// script beside the desk (desk-server.ts serves it). The desk keeps no copy: this module
// only reads what that file's `BattleFeatureSources.forScenario` returns (docs/research/73).
import {array, fail, literal, number, object, parse, record, string, type Check} from "@battle/contracts";

export const STATUSES = ["sourced", "reconstructed", "illustrative"] as const;
/** One mark's status and basis; `footprint_m` is a building's drawn size, `name` a crossing's label. */
export interface FeatureStatus {
  status: typeof STATUSES[number]; source: string; name?: string; footprint_m?: [number, number];
}
export type StatusTable = Readonly<Record<string, FeatureStatus>>;

const positive: Check<number> = (input, path) => {
  const value = number(input, path);
  return value > 0 ? value : fail(path, "expected a size > 0");
};
const metres: Check<[number, number]> = (input, path) => {
  const pair = array(positive, {min: 2, max: 2})(input, path);
  return [pair[0]!, pair[1]!];
};
const nonEmpty: Check<string> = (input, path) => {
  const value = string(input, path);
  return value ? value : fail(path, "expected a basis");
};
const entry: Check<FeatureStatus> = object({status: literal(...STATUSES), source: nonEmpty}, {name: string, footprint_m: metres});

/** Why: a status the legend cannot name, or a malformed size, must not be drawn as if valid.
 * What: one scenario's table, every entry checked; an unknown status or key is refused.
 * Test: `the status table is the POC's file, read through a checked reader; the desk holds no copy`. */
export const readStatusTable = (input: unknown): StatusTable => parse(record(entry), input);

/** What: the table for `scenarioId` from the loaded `BattleFeatureSources` module, or `{}`
 * when the module did not load (every mark then reads "Status not recorded").
 * Test: `the status table is the POC's file, read through a checked reader; the desk holds no copy`. */
export function statusTableFor(module: unknown, scenarioId: string | undefined): StatusTable {
  const read = (module as {forScenario?: unknown} | null)?.forScenario;
  if (typeof read !== "function" || scenarioId === undefined) return {};
  return readStatusTable(read(scenarioId));
}
