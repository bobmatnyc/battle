// GET /api/map (BattleService.map -> catalog map of the current game's scenario):
// the authored terrain grid and the scenario's calendar setting. Display only;
// no rule reads it (docs/research/70).
import {array, fail, hex, nullable, number, object, parse, refine, string, count, type Check} from "./check.ts";

type Hex = [number, number];

/** Where and when the battle is set. `start_local` is wall time at the battlefield. */
export interface BattleSetting { location: string; start_local: string; time_basis: string }

// No offset or "Z": a stated offset would let a browser convert the battle's local time.
const LOCAL_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/;
const localTime: Check<string> = (input, path) => {
  const value = string(input, path);
  return LOCAL_TIME.test(value) ? value : fail(path, "expected a local date-time with no offset");
};

export const battleSetting: Check<BattleSetting> = object({location: string, start_local: localTime, time_basis: string});

/** One authored terrain cell. Keys beyond these vary by scenario (e.g. `area`) and are kept. */
export interface MapCell {
  pos: Hex; elevation: number; terrain: string; move_cost: number; cover: number;
  [extra: string]: unknown;
}
export const mapCell: Check<MapCell> = object({
  pos: hex, elevation: number, terrain: string, move_cost: number, cover: number,
}, {}, {rest: "keep"});

/** The map document; `radius` and `width`/`height` are the POC's drawing units. */
export interface MapDocument {
  setting: BattleSetting; cells: MapCell[]; cols: number; rows: number;
  radius: number; metres_per_hex: number; width: number; height: number;
  source: string; source_url: string | null;
}

const positive: Check<number> = (input, path) => {
  const value = number(input, path);
  return value > 0 ? value : fail(path, "expected a number > 0");
};

/** Why: the desk draws the grid from this document, so a cell off the grid must not pass.
 * What: the map keys; every cell inside `cols` by `rows`; a local start time with no offset.
 * Test: `map fixture validates`, `map refuses a bad field with its path`. */
export const mapDocument: Check<MapDocument> = refine(object({
  setting: battleSetting, cells: array(mapCell, {min: 1}), cols: count, rows: count,
  radius: positive, metres_per_hex: positive, width: positive, height: positive,
  source: string, source_url: nullable(string),
}), (map, path) => {
  map.cells.forEach((cell, index) => {
    if (cell.pos[0] >= map.cols || cell.pos[1] >= map.rows) {
      fail(`${path}.cells[${index}].pos`, `expected a hex inside ${map.cols} by ${map.rows}`);
    }
  });
});

export const readMapDocument = (input: unknown): MapDocument => parse(mapDocument, input);
