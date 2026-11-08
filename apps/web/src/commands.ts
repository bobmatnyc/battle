// The desk's command flows, apart from the DOM so they can be tested with a fake DeskApi
// (docs/research/71). A command the relay could not confirm (`outcome: "unknown"`) is
// followed by a re-read; its notice stays "unknown" whatever the re-read finds or fails to do,
// so the player is never told a possibly committed command simply failed.
import type {CommanderState, FormationSubmission, MapDocument, OrderSubmission, StandingOrderSubmission} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "./api.ts";
import {formationAccepted, formationOutcome} from "./formations.ts";
import {orderOutcome, templateFor} from "./orders.ts";
import {standingAccepted, standingOutcome} from "./standing.ts";
import type {Notice} from "./selection.ts";
import {battleClock} from "./timeline.ts";

/** The view and the terrain the desk draws; `terrainGame` is the game the terrain belongs to. */
export interface Loaded { readonly view: CommanderState; readonly terrain: MapDocument; readonly terrainGame: string }
export interface Step { loaded: Loaded; notice: Notice }

const unknownOutcome = (error: unknown): boolean => error instanceof DeskRefusal && error.outcomeUnknown;
const message = (error: unknown): string => (error instanceof Error ? error.message : String(error));
const SLOW = "The local simulation did not answer in time";

/** Why: the header and map must never describe another game than the counters (fix round #4).
 * What: re-reads the commander view, and re-reads the terrain whenever the view's game is not
 * the game the held terrain belongs to. Rejects, leaving the caller's pair as it was, if either read fails.
 * Test: `after a new battle whose map read fails, the next re-read fetches the new game's terrain`,
 * `a re-read of the same game does not fetch the map again, and a new game's view never pairs with old terrain`. */
export async function reread(api: DeskApi, loaded: Loaded): Promise<Loaded> {
  const view = await api.state();
  if (view.game_id === loaded.terrainGame) return {...loaded, view};
  return {view, terrain: await api.map(), terrainGame: view.game_id};
}

/** Why: an order the POC may have committed must not read as a failure, or the player resends it.
 * What: posts `body`; on an unknown outcome re-reads and reports what the battle now holds,
 * or, if the re-read fails, that the outcome is unknown and the order list needs checking.
 * Any other refusal is rethrown for the caller to show.
 * Test: `an order whose outcome is unknown is re-read, and the re-read decides the notice`,
 * `an order whose outcome is unknown stays unknown when the re-read also fails`,
 * `a plain refusal is not turned into an unknown outcome`. */
export async function sendOrder(api: DeskApi, loaded: Loaded, body: OrderSubmission): Promise<Step> {
  const order = body.orders[0]!;
  let view: CommanderState;
  try {
    view = await api.orders(body);
  } catch (error) {
    if (!unknownOutcome(error)) throw error;
    try {
      const next = await reread(api, loaded);
      return {loaded: next, notice: orderOutcome(loaded.view, next.view, order.unit_id, order.stance)};
    } catch (failure) {
      return {loaded, notice: {kind: "unknown", text: `${SLOW}, so the outcome of ${order.unit_id} ${order.stance} is unknown, `
        + `and re-reading the battle failed (${message(failure)}). Check the order list before sending it again.`}};
    }
  }
  const label = templateFor(view, order.stance)?.label ?? order.stance;
  const where = order.destination ? ` → hex ${order.destination.join(",")}` : "";
  return {loaded: {...loaded, view},
    notice: {kind: "accepted", text: `Order accepted: ${order.unit_id} ${label}${where}. Start the clock to carry it out.`}};
}

// docs/research/81 §12: a standing order or formation goes the way of an order. `send` posts it;
// on an unknown outcome the re-read decides the notice (`outcome`), or says the re-read failed too.
async function sendCommand(api: DeskApi, loaded: Loaded, send: () => Promise<CommanderState>, what: string,
  outcome: (after: CommanderState) => Notice, accepted: (after: CommanderState) => Notice): Promise<Step> {
  let view: CommanderState;
  try {
    view = await send();
  } catch (error) {
    if (!unknownOutcome(error)) throw error;
    try {
      const next = await reread(api, loaded);
      return {loaded: next, notice: outcome(next.view)};
    } catch (failure) {
      return {loaded, notice: {kind: "unknown", text: `${SLOW}, so the outcome of ${what} is unknown, `
        + `and re-reading the battle failed (${message(failure)}). Check the battle before sending it again.`}};
    }
  }
  return {loaded: {...loaded, view}, notice: accepted(view)};
}

/** Why: a standing order the POC may have committed must not read as a failure.
 * What: posts `body`; on an unknown outcome re-reads and reports what the battle now holds, or that
 * the outcome is unknown when the re-read fails. Any other refusal (the engine's text) is rethrown.
 * Test: `an accepted standing order, split or combine names what the POC now holds`,
 * `a standing order or formation whose outcome is unknown is re-read, and the re-read decides the notice`,
 * `a plain refusal of a standing order or formation keeps the engine's text and is not re-read`. */
export function sendStanding(api: DeskApi, loaded: Loaded, body: StandingOrderSubmission): Promise<Step> {
  const {unit_id: unit, profile_id: profile} = body.instruction;
  return sendCommand(api, loaded, () => api.standingOrder(body), `the ${unit} standing order`,
    (after) => standingOutcome(loaded.view, after, unit, profile), (after) => standingAccepted(loaded.view, after, unit, profile));
}

/** Why: a split or combine the POC may have committed must not read as a failure.
 * What: as `sendStanding`, for POST /api/formations.
 * Test: `an accepted standing order, split or combine names what the POC now holds`,
 * `a standing order or formation whose outcome is unknown is re-read, and the re-read decides the notice`,
 * `a plain refusal of a standing order or formation keeps the engine's text and is not re-read`. */
export function sendFormation(api: DeskApi, loaded: Loaded, body: FormationSubmission): Promise<Step> {
  const instruction = body.instruction;
  return sendCommand(api, loaded, () => api.formation(body), `the ${instruction.unit_id} ${instruction.kind}`,
    (after) => formationOutcome(loaded.view, after, instruction), (after) => formationAccepted(loaded.view, after, instruction));
}

/** Why: after a 504 the POC may still start the new battle, so "no new battle" cannot be claimed.
 * What: posts `/api/new` for `chosen`, then reads the new game's map. If that map read fails, the
 * new view is returned with the old terrain still tagged with the old game, and the notice says
 * the battle started and its map will be read again. On an unknown outcome it re-reads: a new game is reported as started;
 * the same game is reported as "so far", since a new battle may still start; a failed re-read
 * says so. Any other refusal is rethrown.
 * Test: `an unknown new battle that re-reads as the same game is still unknown: it may yet start`,
 * `an unknown new battle whose re-read fails stays unknown and says so`,
 * `an unknown new battle that re-reads as a new game loads that game's terrain`,
 * `after a new battle whose map read fails, the next re-read fetches the new game's terrain`. */
export async function startBattle(api: DeskApi, loaded: Loaded, chosen: {id: string; title: string}): Promise<Step> {
  let view: CommanderState;
  try {
    view = await api.newBattle(chosen.id, loaded.view);
  } catch (error) {
    if (!unknownOutcome(error)) throw error;
    let next: Loaded;
    try {
      next = await reread(api, loaded);
    } catch (failure) {
      return {loaded, notice: {kind: "unknown", text: `${SLOW}, so the outcome is unknown: ${chosen.title} may or may not have started, and re-reading `
        + `the battle failed (${message(failure)}). Re-read the battle before starting another.`}};
    }
    const started = next.view.game_id !== loaded.view.game_id;
    return {loaded: next, notice: {kind: "unknown", text: started
      ? `${SLOW}, but re-reading the battle shows it did start a new battle: ${next.view.scenario_brief?.title ?? chosen.title}.`
      : `${SLOW}; the outcome is unknown. Re-reading shows the same battle so far; a new battle may still start. `
        + "Re-read before starting another."}};
  }
  const title = view.scenario_brief?.title ?? chosen.title;
  let terrain: MapDocument;
  try {
    terrain = await api.map();
  } catch (failure) {
    // Slice 2 review: the battle did start. Keep the old terrain tagged with the old game, so no
    // header or map pairs it with the new view, and the next re-read fetches the new map.
    return {loaded: {...loaded, view}, notice: {kind: "accepted", text: `New battle started: ${title}. `
      + `Its map could not be read (${message(failure)}); the desk will read it again.`}};
  }
  const header = battleClock(terrain.setting, view.turn, view.seconds_per_turn, view.display_locale);
  return {loaded: {view, terrain, terrainGame: view.game_id},
    notice: {kind: "accepted", text: `New battle: ${title}, ${header.date}, ${header.time}. The clock is paused.`}};
}
