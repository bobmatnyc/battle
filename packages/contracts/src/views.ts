// The presented battle view: what BattleQueries.project returns for one
// side's commander (engine.view) or for God (engine.god_view), after
// presentation.present_view. docs/research/67 lists the source of each field.
import {
  array, boolean, count, fail, hex, integer, json, jsonObject, literal, nullable, number,
  object, record, refine, string, type Check, type JsonObject, type JsonValue,
} from "./check.ts";
import {mapFeatures, type MapFeature} from "./features.ts";

type Hex = [number, number];

/** Top-level fields only engine.god_view adds; a commander view never carries
 * them (docs/research/21, 65; tests/test_replay_sides.py GOD_ONLY). */
export const GOD_ONLY_FIELDS = [
  "view_mode", "reports", "events", "decisions", "headquarters", "commands", "retired_units", "captives",
] as const;

/** A unit as reported (commander) or exact (God): engine.summary plus report
 * timing. Keys beyond these vary by rules edition and scenario and are kept. */
export interface UnitReport {
  id: string; side: string; name: string; pos: Hex;
  initial: number; strength: number; ammo: number;
  morale: number; suppression: number; fatigue: number;
  status: string; stance: string; target: Hex | null; order_version: number;
  observed_turn: number; received_turn: number;
  [extra: string]: unknown;
}
export const unitReport: Check<UnitReport> = object({
  id: string, side: string, name: string, pos: hex,
  initial: count, strength: count, ammo: number,
  morale: number, suppression: number, fatigue: number,
  status: string, stance: string, target: nullable(hex), order_version: count,
  observed_turn: integer, received_turn: integer,
}, {}, {rest: "keep"});

/** Exact enemy values a sighting never carries: a contact holds an estimate,
 * a confidence and a strength range (recon.py), never the true unit's state. */
export const CONTACT_FORBIDDEN = ["strength", "initial", "ammo", "morale", "suppression", "fatigue"] as const;

/** An enemy sighting held by headquarters (engine.view adds ``age``). */
export interface Contact {
  id: string; side: string; pos: Hex; observed_turn: number; received_turn: number; age: number;
  confidence: string; estimate: string;
  [extra: string]: unknown;
}
export const contact: Check<Contact> = object({
  id: string, side: string, pos: hex, observed_turn: integer, received_turn: integer, age: count,
  confidence: string, estimate: string,
}, {}, {rest: "keep", forbidden: CONTACT_FORBIDDEN});

// engine.issue copies the order as given, and validate_order accepts one with no
// destination for a template that selects its own, so the key may be absent.
const orderFields = {
  id: string, side: string, unit_id: string, stance: string,
  source: string, version: count, sent_turn: count, arrival_turn: nullable(integer), status: string,
};
const orderOptional = {destination: nullable(hex)};
/** An order as the issuing side knows it: status from acknowledgements only. */
export interface CommanderOrder {
  id: string; side: string; unit_id: string; stance: string; destination?: Hex | null;
  source: string; version: number; sent_turn: number; arrival_turn: number | null; status: string;
  [extra: string]: unknown;
}
export const commanderOrder: Check<CommanderOrder> = object(orderFields, orderOptional, {rest: "keep", forbidden: ["transport"]});
/** An order with its true status and its messenger packet (God only). */
export interface GodOrder extends CommanderOrder { transport: JsonObject }
export const godOrder: Check<GodOrder> = object({...orderFields, transport: jsonObject}, orderOptional, {rest: "keep"});

const dispatchFields = {turn: integer, observed_turn: integer, kind: string, text: string, display_text: string};
const dispatchOptional = {message_key: string, message_args: record(string)};
/** A delivered message in the battle's period voice (presentation.present_view). */
export interface Dispatch {
  turn: number; observed_turn: number; kind: string; text: string; display_text: string;
  message_key?: string; message_args?: Record<string, string>;
}
export const commanderDispatch: Check<Dispatch> = object(dispatchFields, dispatchOptional, {forbidden: ["side"]});
/** God sees every side's dispatches, each tagged with its side. */
export interface GodDispatch extends Dispatch { side: string }
export const godDispatch: Check<GodDispatch> = object({...dispatchFields, side: string}, dispatchOptional);

/** Staff advice; ``display_text`` in a voice with its own address. */
export interface Recommendation {
  id: string; side: string; unit_id: string; status: string; text: string; display_text?: string;
  received_turn?: number;
  [extra: string]: unknown;
}
const recommendationFields = {id: string, side: string, unit_id: string, status: string, text: string};
/** recommendations.visible returns only advice that reached headquarters. */
export const commanderRecommendation: Check<Recommendation & {received_turn: number}> = object(
  {...recommendationFields, received_turn: count}, {display_text: string}, {rest: "keep"});
/** God sees every piece of advice, delivered or not. */
export const godRecommendation: Check<Recommendation> = object(
  recommendationFields, {display_text: string, received_turn: count}, {rest: "keep"});

/** A split or combine as the issuing side knows it (formations.observed):
 * the status is the last notice received; the true ready and completed turns are God-only. */
export interface FormationOp { id: string; side: string; kind: string; status: string; [extra: string]: unknown }
export const commanderFormationOp: Check<FormationOp> = object(
  {id: string, side: string, kind: string, status: string}, {},
  {rest: "keep", forbidden: ["ready_turn", "completed_turn"]});

/** A delivered codeword (signals.receive): the report data plus its arrival turn.
 * Confirmed by fixture `replay-commander-pegasus.json` (Pegasus Bridge, docs/research/81 §4). */
export interface ReceivedSignal {
  codeword: string; meaning: string; bridge: string; sender_id: string; receiver_id: string;
  sent_turn: number; delivered_turn: number;
}
export const receivedSignal: Check<ReceivedSignal> = object({
  codeword: string, meaning: string, bridge: string, sender_id: string, receiver_id: string,
  sent_turn: integer, delivered_turn: integer,
});

/** A side's own broadcast signal (broadcast.visible): exactly these keys, never who heard.
 * UNCONFIRMED by fixture (Gergovia only); keys from broadcast.py. */
export interface CommanderBroadcast {
  id: string; kind: string; meaning: string; stance: string; destination: Hex | null;
  turn: number | null; ordered_turn: number | null; sounded_turn: number | null;
}
export const commanderBroadcast: Check<CommanderBroadcast> = object({
  id: string, kind: string, meaning: string, stance: string, destination: nullable(hex),
  turn: nullable(integer), ordered_turn: nullable(integer), sounded_turn: nullable(integer),
});

/** A standing-order instruction (standing.visible). UNCONFIRMED: no fixture holds one. */
export interface StandingOrder { id: string; side: string; status: string; [extra: string]: unknown }
const standingFields = {id: string, side: string, status: string};
export const commanderStandingOrder: Check<StandingOrder> =
  object(standingFields, {}, {rest: "keep", forbidden: ["transport"]});
export const godStandingOrder: Check<StandingOrder> = object(standingFields, {}, {rest: "keep"});

/** A briefed ammunition point (orders.known_sites); its stock is God-only. */
export interface SupplySite { id: string; side: string; name: string; pos: Hex; weapon_class: string }
const siteFields = {id: string, side: string, name: string, pos: hex, weapon_class: string};
export const commanderSupplySite: Check<SupplySite> = object(siteFields, {}, {forbidden: ["ammo"]});
export interface GodSupplySite extends SupplySite { ammo?: number; [extra: string]: unknown }
export const godSupplySite: Check<GodSupplySite> = object(siteFields, {ammo: number}, {rest: "keep"});

/** An order template the desk offers (orders.catalog). */
export interface OrderTemplate {
  id: string; label: string; destination: "none" | "hex" | "supply";
  intent: string; effect: string; message_key: string; version: string;
  [extra: string]: unknown;
}
export const orderTemplate: Check<OrderTemplate> = object({
  id: string, label: string, destination: literal("none", "hex", "supply"),
  intent: string, effect: string, message_key: string, version: string,
}, {}, {rest: "keep"});

/** Where a side's headquarters is and whether it can command (comms.location). */
export interface CommandLocation {
  unit_id: string | null; pos: Hex | null; status: string; operational: boolean; profile: JsonObject;
  [extra: string]: unknown;
}
export const commandLocation: Check<CommandLocation> = object({
  unit_id: nullable(string), pos: nullable(hex), status: string, operational: boolean, profile: jsonObject,
}, {}, {rest: "keep"});

/** The viewing side's brief (presentation.scenario_brief); never the opponent's mission. */
export interface ScenarioBrief {
  id: string; title: string; voice_profile: string; campaign: string; conditions: string;
  side: {id: string; name: string}; opponent: {id: string; name: string};
  kicker: string; tagline: string; subhead: string;
  mission: {title: string; text: string};
  objective: {place: string; label: string; key: string; ring: boolean};
  outcomes: {win: string; loss: string; draw: string};
}
const named = object({id: string, name: string});
export const scenarioBrief: Check<ScenarioBrief> = object({
  id: string, title: string, voice_profile: string, campaign: string, conditions: string,
  side: named, opponent: named, kicker: string, tagline: string, subhead: string,
  mission: object({title: string, text: string}),
  objective: object({place: string, label: string, key: string, ring: boolean}),
  outcomes: object({win: string, loss: string, draw: string}),
});

/** The staff assessment of the viewing side's own reports (analysis.assess). */
export interface Analysis {
  version: string; side: string; revision: number; turn: number; basis: string; limitations: string;
  command_operational: boolean; summary: JsonObject;
  contacts: JsonValue[]; units: JsonValue[]; standing_templates: JsonValue[];
  [extra: string]: unknown;
}
export const analysis: Check<Analysis> = object({
  version: string, side: string, revision: count, turn: count, basis: string, limitations: string,
  command_operational: boolean, summary: jsonObject,
  contacts: array(json), units: array(json), standing_templates: array(json),
}, {}, {rest: "keep"});

const jsonList = array(jsonObject);
const sharedFields = {
  rules: string, turn: count, revision: count, status: literal("active", "complete"),
  winner: nullable(string), reason: nullable(string), objective: hex,
  max_turns: count, seconds_per_turn: count, side: string, weather: jsonObject, hq: hex,
  command: commandLocation, units: array(unitReport), order_templates: array(orderTemplate),
  standing_templates: jsonList,
  display_locale: literal("en"), voice_profile: string, analysis,
};
const sharedOptional = {scenario_brief: scenarioBrief};

interface SharedView {
  rules: string; turn: number; revision: number; status: "active" | "complete";
  winner: string | null; reason: string | null; objective: Hex;
  max_turns: number; seconds_per_turn: number; side: string; weather: JsonObject; hq: Hex;
  command: CommandLocation; units: UnitReport[]; order_templates: OrderTemplate[];
  standing_templates: JsonObject[]; recommendations: Recommendation[];
  display_locale: "en"; voice_profile: string; analysis: Analysis;
  scenario_brief?: ScenarioBrief;
}

/** One side's commander view: its own delivered reports only. */
export interface CommanderView extends SharedView {
  map_features: MapFeature[];
  contacts: Contact[]; orders: CommanderOrder[]; dispatches: Dispatch[];
  standing_orders: StandingOrder[]; supply_sites: SupplySite[];
  recommendations: (Recommendation & {received_turn: number})[]; formation_ops: FormationOp[];
  signals?: ReceivedSignal[]; broadcasts?: CommanderBroadcast[];
}

/** The God view: true state of every side, for the local observer only. */
export interface GodView extends SharedView {
  map_features: JsonObject[];
  view_mode: "god"; contacts: []; orders: GodOrder[]; dispatches: GodDispatch[];
  standing_orders: StandingOrder[]; supply_sites: GodSupplySite[];
  reports: JsonObject[]; events: JsonObject[]; decisions: JsonObject[];
  headquarters: Record<string, Hex>; commands: Record<string, CommandLocation>;
  retired_units: JsonObject[]; formation_ops: JsonObject[];
  signals?: JsonObject[]; broadcasts?: JsonObject[]; captives?: JsonValue;
}

function sameSide(items: readonly {side: string}[], side: string, path: string, field: string): void {
  items.forEach((item, index) => {
    if (item.side !== side) fail(`${path}.${field}[${index}].side`, `expected the viewing side ${JSON.stringify(side)}, got ${JSON.stringify(item.side)}`);
  });
}

// Both views carry only the viewing (God: the player's) side's brief and assessment.
function ownBrief(view: SharedView, path: string): void {
  if (view.analysis.side !== view.side) fail(`${path}.analysis.side`, `expected the viewing side ${JSON.stringify(view.side)}`);
  if (view.scenario_brief && view.scenario_brief.side.id !== view.side) {
    fail(`${path}.scenario_brief.side.id`, `expected the viewing side ${JSON.stringify(view.side)}`);
  }
}

/** Why: the commander view is the information boundary of docs/research/21 and 65.
 * What: the projection fields; no God-only field; every unit, order, standing
 * order, recommendation, formation operation and supply site of the viewing
 * side; every contact of another side with no exact enemy values; dispatches
 * untagged by side; no order transport; no stocks; delivered codewords and
 * own broadcasts with no sender condition, reach or receipts.
 * Test: `commander fixtures validate`, `commander view refuses each God-only field`. */
export const commanderView: Check<CommanderView> = refine(object({
  ...sharedFields, map_features: mapFeatures,
  contacts: array(contact), orders: array(commanderOrder), dispatches: array(commanderDispatch),
  standing_orders: array(commanderStandingOrder), supply_sites: array(commanderSupplySite),
  recommendations: array(commanderRecommendation), formation_ops: array(commanderFormationOp),
}, {...sharedOptional, signals: array(receivedSignal), broadcasts: array(commanderBroadcast)},
{forbidden: GOD_ONLY_FIELDS}), (view, path) => {
  sameSide(view.units, view.side, path, "units");
  sameSide(view.orders, view.side, path, "orders");
  sameSide(view.standing_orders, view.side, path, "standing_orders");
  sameSide(view.recommendations, view.side, path, "recommendations");
  sameSide(view.supply_sites, view.side, path, "supply_sites");
  sameSide(view.formation_ops, view.side, path, "formation_ops");
  view.contacts.forEach((item, index) => {
    if (item.side === view.side) fail(`${path}.contacts[${index}].side`, "a contact is an enemy sighting, not the viewing side");
  });
  ownBrief(view, path);
});

const emptyContacts: Check<[]> = (input, path) => array(json, {max: 0})(input, path) as [];

/** Why: God Mode must be told apart from a commander view by shape, not by trust.
 * What: the projection fields plus every God-only field, `view_mode: "god"`,
 * no contacts (God sees units), side-tagged dispatches, transports on orders.
 * Test: `god fixtures validate`, `god view requires view_mode god`. */
export const godView: Check<GodView> = refine(object({
  ...sharedFields, map_features: jsonList,
  view_mode: literal("god"), contacts: emptyContacts,
  orders: array(godOrder), dispatches: array(godDispatch),
  standing_orders: array(godStandingOrder), supply_sites: array(godSupplySite),
  reports: jsonList, events: jsonList, decisions: jsonList,
  headquarters: record(hex), commands: record(commandLocation), retired_units: jsonList,
  recommendations: array(godRecommendation), formation_ops: jsonList,
}, {...sharedOptional, signals: jsonList, broadcasts: jsonList, captives: json}), ownBrief);
