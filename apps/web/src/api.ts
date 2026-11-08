// Transport to the POC's HTTP API. Same origin only; the fetch is injected.
// Every response is read through the commander-view contract, so a God view
// (or any omniscient field) is refused rather than drawn.
import {
  orderSubmission, parse, readCommanderReplay, readCommanderState, readHistory, readMapDocument, readScenarioList,
  type BattleCursor, type CommanderState, type CommanderView, type HistoryEntry, type MapDocument,
  type OrderSubmission, type ScenarioList,
} from "@battle/contracts";

/** A request the server refused: its HTTP status and the server's own text.
 * `outcomeUnknown`: the desk server gave up on a request the POC may have committed
 * (a 504 or a dropped reply marked `outcome: "unknown"`, docs/research/71). */
export class DeskRefusal extends Error {
  readonly status: number;
  readonly outcomeUnknown: boolean;
  constructor(status: number, message: string, outcomeUnknown = false) {
    super(message);
    this.name = "DeskRefusal";
    this.status = status;
    this.outcomeUnknown = outcomeUnknown;
  }
}

export type ClockCommand = "start" | "pause";

export interface DeskApi {
  state(): Promise<CommanderState>;
  map(): Promise<MapDocument>;
  scenarios(): Promise<ScenarioList>;
  orders(body: OrderSubmission): Promise<CommanderState>;
  clock(command: ClockCommand, gameId: string): Promise<CommanderState>;
  newBattle(scenario: string, cursor: BattleCursor): Promise<CommanderState>;
  /** The game's stored revisions (docs/research/73). */
  history(gameId: string): Promise<HistoryEntry[]>;
  /** The player's commander view at `revision`, read only; never God's or another side's. */
  replay(gameId: string, revision: number): Promise<CommanderView>;
}

async function body(response: Response): Promise<unknown> {
  const text = await response.text();
  let data: unknown = null;
  try { data = JSON.parse(text); } catch { data = null; }
  if (response.ok) {
    if (data === null) throw new DeskRefusal(response.status, "The server sent no readable battle data.");
    return data;
  }
  const fields = typeof data === "object" && data !== null ? data as Record<string, unknown> : {};
  const error = fields["error"];
  throw new DeskRefusal(response.status,
    typeof error === "string" && error ? error : `The server refused the request (HTTP ${response.status}).`,
    fields["outcome"] === "unknown");
}

/** Why: refusals must reach the player, and the desk must never hold a God view.
 * What: GET /api/state, /api/map, /api/scenarios, /api/history and /api/replay (game and
 * revision only, so the commander view); POST /api/orders, /api/clock and /api/new.
 * A non-2xx reply throws DeskRefusal with the server's `error` text; replies pass the contracts.
 * Test: `a server refusal keeps its status and text`, `a God view is refused, so the desk cannot draw omniscient state`,
 * `a relay reply marked outcome unknown is a refusal the desk can tell apart`,
 * `the scenario catalog is read through its contract, and a new battle posts the chosen id at the cursor`,
 * `history and replay requests name the game and revision only`. */
export function createDeskApi(request: typeof fetch, base = ""): DeskApi {
  const get = async (path: string): Promise<unknown> => body(await request(base + path));
  const post = async (path: string, payload: unknown): Promise<unknown> => body(await request(base + path, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
  }));
  return Object.freeze({
    state: async () => readCommanderState(await get("/api/state")),
    map: async () => readMapDocument(await get("/api/map")),
    scenarios: async () => readScenarioList(await get("/api/scenarios")),
    orders: async (submission: OrderSubmission) => {
      const checked = parse(orderSubmission, submission);
      return readCommanderState(await post("/api/orders", checked));
    },
    clock: async (command: ClockCommand, gameId: string) =>
      readCommanderState(await post("/api/clock", {command, game_id: gameId})),
    newBattle: async (scenario: string, cursor: BattleCursor) =>
      readCommanderState(await post("/api/new", {scenario, game_id: cursor.game_id, revision: cursor.revision})),
    history: async (gameId: string) => readHistory(await get(`/api/history?${new URLSearchParams({game_id: gameId})}`)),
    replay: async (gameId: string, revision: number) =>
      readCommanderReplay(await get(`/api/replay?${new URLSearchParams({game_id: gameId, revision: String(revision)})}`)),
  });
}
