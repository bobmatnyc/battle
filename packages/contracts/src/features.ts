// The commander view's map_features (engine.view -> features.known, docs/research/24, 41, 53, 73):
// roads, buildings (a walled compound with its gates when it has openings), fieldworks and
// bridges, each as the viewing side last knew it. Keys are pinned per kind: a new key or kind
// is refused, so a change in the Python app is noticed here, not drawn by guesswork.
import {array, boolean, count, fail, hex, integer, literal, object, refine, string, parse, type Check} from "./check.ts";

type Hex = [number, number];

/** Report timing every known feature carries (features.setup, features.receive). */
interface Known { id: string; name: string; provenance: string; briefed: boolean; observed_turn: number; received_turn: number }
const known = {id: string, name: string, provenance: string, briefed: boolean, observed_turn: integer, received_turn: integer};

/** An authored road: its waypoints and the hexes the engine routed between them. */
export interface RoadFeature extends Known { kind: "road"; points: Hex[]; hexes: Hex[] }

/** gates.STATES; open, closing and forced are passable (gates.PASSABLE). */
export const GATE_STATES = ["open", "closing", "closed", "barred", "forced"] as const;
export type GateState = typeof GATE_STATES[number];
/** A gate between a compound hex (`inside`) and its neighbour (`outside`), in its known state. */
export interface Opening {
  id: string; name: string; inside: Hex; outside: Hex; state: GateState;
  effort: number; bar_effort: number; force_effort: number; updated_turn?: number;
}
const opening: Check<Opening> = object({
  id: string, name: string, inside: hex, outside: hex, state: literal(...GATE_STATES),
  effort: count, bar_effort: count, force_effort: count,
}, {updated_turn: integer});

/** A building on one hex; with `openings`, the walled `compound` around it (poc-10). */
export interface BuildingFeature extends Known {
  kind: "building"; pos: Hex; cover: number; height: number;
  compound?: Hex[]; openings?: Opening[]; updated_turn?: number;
}

/** Fieldworks: briefed works, or works dug in battle (`briefed: false`, as last reported). */
export interface FortificationFeature extends Known {
  kind: "fortification"; pos: Hex; cover: number; progress: number;
  effort?: number; required?: number; updated_turn?: number; base_cover?: number;
}

/** bridges.STATES. */
export const BRIDGE_STATES = ["intact", "charges", "destroyed"] as const;
/** A bridge feature (poc-13) in its known state. */
export interface BridgeFeature extends Known { kind: "bridge"; pos: Hex; state: typeof BRIDGE_STATES[number]; updated_turn: number }

export type MapFeature = RoadFeature | BuildingFeature | FortificationFeature | BridgeFeature;

const percent: Check<number> = (input, path) => {
  const value = count(input, path);
  return value <= 100 ? value : fail(path, `expected 0 to 100, got ${value}`);
};

const road = object({...known, kind: literal("road"), points: array(hex, {min: 2}), hexes: array(hex, {min: 2})});
const building = refine(object({...known, kind: literal("building"), pos: hex, cover: count, height: count},
  {compound: array(hex, {min: 1}), openings: array(opening), updated_turn: integer}), (f, path) => {
  if (f.openings?.length && !f.compound) fail(`${path}.compound`, "a building with openings needs its compound");
});
const fortification = object({...known, kind: literal("fortification"), pos: hex, cover: count, progress: percent},
  {effort: count, required: count, updated_turn: integer, base_cover: count});
const bridge = object({...known, kind: literal("bridge"), pos: hex, state: literal(...BRIDGE_STATES), updated_turn: integer});

const KINDS: Record<string, Check<MapFeature>> = {road, building, fortification, bridge} as Record<string, Check<MapFeature>>;

/** Why: the desk draws walls, gates and bridges from these fields, so a shape it does not know must not pass.
 * What: one known feature, checked by its `kind` with that kind's exact keys; an unknown kind is refused.
 * Test: `map features refuse an unknown kind, an unknown key and a bad state with the path`. */
export const mapFeature: Check<MapFeature> = (input, path) => {
  const kind = typeof input === "object" && input !== null && !Array.isArray(input) ? (input as Record<string, unknown>)["kind"] : undefined;
  const check = typeof kind === "string" && Object.hasOwn(KINDS, kind) ? KINDS[kind] : undefined;
  return check ? check(input, path) : fail(`${path}.kind`, `expected one of ${JSON.stringify(Object.keys(KINDS))}, got ${JSON.stringify(kind)}`);
};

/** Test: `every catalog entry's map features validate, and every kind is covered`. */
export const mapFeatures: Check<MapFeature[]> = array(mapFeature);
export const readMapFeatures = (input: unknown): MapFeature[] => parse(mapFeatures, input);
