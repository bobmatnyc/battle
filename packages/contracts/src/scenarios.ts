// GET /api/scenarios (BattleService.scenario_list): the player-facing catalog
// a new battle may start from. The POC lists only PLAYER_SCENARIOS here;
// headless-only entries never appear (docs/research/71).
import {array, fail, object, parse, refine, string, type Check} from "./check.ts";

/** One catalog entry: `date` is the scenario's calendar date, `YYYY-MM-DD`. */
export interface ScenarioEntry { id: string; title: string; location: string; date: string }
/** The catalog and the id a new battle uses when none is named. */
export interface ScenarioList { default: string; scenarios: ScenarioEntry[] }

const id: Check<string> = (input, path) => {
  const value = string(input, path);
  return value ? value : fail(path, "expected a non-empty id");
};
const calendarDate: Check<string> = (input, path) => {
  const value = string(input, path);
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : fail(path, "expected a YYYY-MM-DD date");
};

export const scenarioEntry: Check<ScenarioEntry> = object({id, title: string, location: string, date: calendarDate});

/** Why: the desk offers exactly the catalog the POC will accept in `/api/new`.
 * What: at least one entry, unique ids, and a default that is one of them.
 * Test: `scenario list fixture validates and names the player-facing scenarios`,
 * `scenario list refuses a bad field with its path`. */
export const scenarioList: Check<ScenarioList> = refine(object({
  default: id, scenarios: array(scenarioEntry, {min: 1}),
}), (list, path) => {
  const seen = new Set<string>();
  list.scenarios.forEach((entry, index) => {
    if (seen.has(entry.id)) fail(`${path}.scenarios[${index}].id`, "expected a unique id");
    seen.add(entry.id);
  });
  if (!seen.has(list.default)) fail(`${path}.default`, "expected one of the listed ids");
});

export const readScenarioList = (input: unknown): ScenarioList => parse(scenarioList, input);
