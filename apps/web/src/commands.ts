// The desk's command flows, apart from the DOM so they can be tested with a fake DeskApi.
import type {CommanderState, MapDocument, OrderSubmission} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "./api.ts";
import {orderOutcome, templateFor} from "./orders.ts";
import type {Notice} from "./selection.ts";
import {battleClock} from "./timeline.ts";

/** The view and the terrain the desk draws; `terrainGame` is the game the terrain belongs to. */
export interface Loaded { readonly view: CommanderState; readonly terrain: MapDocument; readonly terrainGame: string }
export interface Step { loaded: Loaded; notice: Notice }

const unknownOutcome = (error: unknown): boolean => error instanceof DeskRefusal && error.outcomeUnknown;

/** Re-reads the commander view; a new game also re-reads its terrain. */
export async function reread(api: DeskApi, loaded: Loaded): Promise<Loaded> {
  const view = await api.state();
  if (view.game_id === loaded.view.game_id) return {...loaded, view};
  return {view, terrain: await api.map(), terrainGame: view.game_id};
}

/** Sends one order; an unconfirmed outcome is followed by a re-read. */
export async function sendOrder(api: DeskApi, loaded: Loaded, body: OrderSubmission): Promise<Step> {
  const order = body.orders[0]!;
  let view: CommanderState;
  try {
    view = await api.orders(body);
  } catch (error) {
    if (!unknownOutcome(error)) throw error;
    const next = await reread(api, loaded);
    return {loaded: next, notice: orderOutcome(loaded.view, next.view, order.unit_id, order.stance)};
  }
  const label = templateFor(view, order.stance)?.label ?? order.stance;
  const where = order.destination ? ` → hex ${order.destination.join(",")}` : "";
  return {loaded: {...loaded, view},
    notice: {kind: "accepted", text: `Order accepted: ${order.unit_id} ${label}${where}. Start the clock to carry it out.`}};
}

/** Starts scenario `chosen`; an unconfirmed outcome is followed by a re-read. */
export async function startBattle(api: DeskApi, loaded: Loaded, chosen: {id: string; title: string}): Promise<Step> {
  let view: CommanderState;
  try {
    view = await api.newBattle(chosen.id, loaded.view);
  } catch (error) {
    if (!unknownOutcome(error)) throw error;
    const next = await reread(api, loaded);
    const started = next.view.game_id !== loaded.view.game_id;
    return {loaded: next, notice: {kind: "unknown", text: "The local simulation did not answer in time. Re-reading the battle shows "
      + (started ? `a new battle: ${next.view.scenario_brief?.title ?? chosen.title}.` : "the same battle; no new one was started.")}};
  }
  const terrain = await api.map();
  const header = battleClock(terrain.setting, view.turn, view.seconds_per_turn, view.display_locale);
  return {loaded: {view, terrain, terrainGame: view.game_id},
    notice: {kind: "accepted", text: `New battle: ${view.scenario_brief?.title ?? chosen.title}, ${header.date}, ${header.time}. The clock is paused.`}};
}
