// HTTP responses and request bodies of the Python POC (adapters/http_api.py):
// /api/state, /api/replay, /api/history and the /api/orders body.
import {
  array, boolean, count, fail, hex, jsonObject, literal, nonEmpty, nullable, number, object, parse,
  refine, string, type Check, type JsonObject,
} from "./check.ts";
import {commanderView, godView, type CommanderView, type GodView} from "./views.ts";

type Hex = [number, number];

/** Wall-time pacing state (clock.SimulationClock.status); never battle physics. */
export interface ClockStatus {
  running: boolean; inflight: boolean; speed: number; remaining_seconds: number;
  speeds: number[]; error: string | null;
}
export const clockStatus: Check<ClockStatus> = refine(object({
  running: boolean, inflight: boolean, speed: number, remaining_seconds: number,
  speeds: array(number, {min: 1}), error: nullable(string),
}), (clock, path) => {
  if (!clock.speeds.includes(clock.speed)) fail(`${path}.speed`, "expected one of the offered speeds");
});

/** A staff chat line (storage.Store.messages). ``proposals`` items are
 * UNCONFIRMED: the recorded game has none. */
export interface ChatMessage {
  id: number; game_id: string; turn: number; role: "user" | "assistant";
  content: string; proposals: JsonObject[]; source: string;
}
export const chatMessage: Check<ChatMessage> = object({
  id: count, game_id: string, turn: count, role: literal("user", "assistant"),
  content: string, proposals: array(jsonObject), source: string,
});

/** Fields BattleService.state adds to the projection; a replay has none. */
export const LIVE_FIELDS = [
  "clock", "game_id", "mode", "model", "inference_available", "messages",
  "last_commander_source", "last_fallback_reason",
] as const;
export interface LiveFields {
  clock: ClockStatus; game_id: string; mode: "scripted" | "openrouter"; model: string;
  inference_available: boolean; messages: ChatMessage[];
  last_commander_source: string | null; last_fallback_reason: string | null;
}
const liveCheck = object({
  clock: clockStatus, game_id: nonEmpty, mode: literal("scripted", "openrouter"), model: string,
  inference_available: boolean, messages: array(chatMessage),
  last_commander_source: nullable(string), last_fallback_reason: nullable(string),
});

// Split the live fields off, check each part with its own strict check, and join them.
function live<V>(view: Check<V>): Check<V & LiveFields> {
  return (input, path) => {
    if (typeof input !== "object" || input === null || Array.isArray(input)) {
      return fail(path, "expected object");
    }
    const source = input as Record<string, unknown>;
    const liveInput: Record<string, unknown> = {};
    const viewInput: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(source)) {
      Object.defineProperty((LIVE_FIELDS as readonly string[]).includes(key) ? liveInput : viewInput, key,
        {value, enumerable: true, writable: true, configurable: true});
    }
    return {...view(viewInput, path), ...liveCheck(liveInput, path)};
  };
}

/** GET /api/state: the player's commander view with the live fields. */
export type CommanderState = CommanderView & LiveFields;
/** GET /api/state?view=god: the God view with the live fields. */
export type GodState = GodView & LiveFields;
export type StateResponse = CommanderState | GodState;
export const commanderState: Check<CommanderState> = live(commanderView);
export const godState: Check<GodState> = live(godView);

/** A God view is told apart by `view_mode`; anything else must be a commander view. */
function byViewMode<C, G>(commander: Check<C>, god: Check<G>): Check<C | G> {
  return (input, path) => typeof input === "object" && input !== null && !Array.isArray(input)
      && (input as Record<string, unknown>)["view_mode"] === "god"
    ? god(input, path) : commander(input, path);
}
export const stateResponse: Check<StateResponse> = byViewMode(commanderState, godState);

/** GET /api/replay?revision=N[&side=<id>]: that side's (default: the player's)
 * commander view at revision N, read only. No live fields. */
export type CommanderReplay = CommanderView;
/** GET /api/replay?revision=N&view=god. */
export type GodReplay = GodView;
export type ReplayResponse = CommanderReplay | GodReplay;
export const commanderReplay: Check<CommanderReplay> = commanderView;
export const godReplay: Check<GodReplay> = godView;
export const replayResponse: Check<ReplayResponse> = byViewMode(commanderReplay, godReplay);

/** One stored revision (storage.Store.history): the digest a replay checks. */
export interface HistoryEntry { revision: number; turn: number; sha256: string }
const sha256: Check<string> = (input, path) => {
  const value = string(input, path);
  return /^[0-9a-f]{64}$/.test(value) ? value : fail(path, "expected 64 lowercase hex digits");
};
export const historyEntry: Check<HistoryEntry> = object({revision: count, turn: count, sha256});

/** GET /api/history: revisions from 0 in ascending order; turns never decrease. */
export const history: Check<HistoryEntry[]> = refine(array(historyEntry, {min: 1}), (entries, path) => {
  if (entries[0]?.revision !== 0) fail(`${path}[0].revision`, "expected the first revision to be 0");
  entries.forEach((entry, index) => {
    const previous = entries[index - 1];
    if (!previous) return;
    if (entry.revision <= previous.revision) fail(`${path}[${index}].revision`, "expected ascending revisions");
    if (entry.turn < previous.turn) fail(`${path}[${index}].turn`, "expected turns that never decrease");
  });
});

/** One order (engine.validate_order): only these keys; Python checks the rules. */
export interface OrderEntry { unit_id: string; stance: string; destination?: Hex | null }
export const orderEntry: Check<OrderEntry> = object({unit_id: nonEmpty, stance: nonEmpty}, {destination: nullable(hex)});

/** POST /api/orders body: one to three orders at the cursor the desk last read. */
export interface OrderSubmission { orders: OrderEntry[]; game_id: string; revision: number }
export const orderSubmission: Check<OrderSubmission> = object({
  orders: array(orderEntry, {min: 1, max: 3}), game_id: nonEmpty, revision: count,
});

export const readStateResponse = (input: unknown): StateResponse => parse(stateResponse, input);
export const readCommanderState = (input: unknown): CommanderState => parse(commanderState, input);
export const readGodState = (input: unknown): GodState => parse(godState, input);
export const readReplayResponse = (input: unknown): ReplayResponse => parse(replayResponse, input);
export const readCommanderReplay = (input: unknown): CommanderReplay => parse(commanderReplay, input);
export const readGodReplay = (input: unknown): GodReplay => parse(godReplay, input);
export const readHistory = (input: unknown): HistoryEntry[] => parse(history, input);
export const readClockStatus = (input: unknown): ClockStatus => parse(clockStatus, input);
export const readOrderSubmission = (input: unknown): OrderSubmission => parse(orderSubmission, input);
