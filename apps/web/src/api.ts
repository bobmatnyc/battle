// Transport to the POC's HTTP API. Same origin only; the fetch is injected.
// Every response is read through the commander-view contract, so a God view
// (or any omniscient field) is refused rather than drawn.
import {
  orderSubmission, parse, readCommanderState, readMapDocument,
  type CommanderState, type MapDocument, type OrderSubmission,
} from "@battle/contracts";

/** A request the server refused: its HTTP status and the server's own text. */
export class DeskRefusal extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "DeskRefusal";
    this.status = status;
  }
}

export type ClockCommand = "start" | "pause";

export interface DeskApi {
  state(): Promise<CommanderState>;
  map(): Promise<MapDocument>;
  orders(body: OrderSubmission): Promise<CommanderState>;
  clock(command: ClockCommand, gameId: string): Promise<CommanderState>;
}

async function body(response: Response): Promise<unknown> {
  const text = await response.text();
  let data: unknown = null;
  try { data = JSON.parse(text); } catch { data = null; }
  if (response.ok) {
    if (data === null) throw new DeskRefusal(response.status, "The server sent no readable battle data.");
    return data;
  }
  const error = typeof data === "object" && data !== null ? (data as Record<string, unknown>)["error"] : undefined;
  throw new DeskRefusal(response.status,
    typeof error === "string" && error ? error : `The server refused the request (HTTP ${response.status}).`);
}

/** Why: refusals must reach the player, and the desk must never hold a God view.
 * What: GET /api/state and /api/map, POST /api/orders and /api/clock; a non-2xx reply
 * throws DeskRefusal with the server's `error` text; replies pass the contracts.
 * Test: `a server refusal keeps its status and text`, `a God view is refused, so the desk cannot draw omniscient state`. */
export function createDeskApi(request: typeof fetch, base = ""): DeskApi {
  const get = async (path: string): Promise<unknown> => body(await request(base + path));
  const post = async (path: string, payload: unknown): Promise<unknown> => body(await request(base + path, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
  }));
  return Object.freeze({
    state: async () => readCommanderState(await get("/api/state")),
    map: async () => readMapDocument(await get("/api/map")),
    orders: async (submission: OrderSubmission) => {
      const checked = parse(orderSubmission, submission);
      return readCommanderState(await post("/api/orders", checked));
    },
    clock: async (command: ClockCommand, gameId: string) =>
      readCommanderState(await post("/api/clock", {command, game_id: gameId})),
  });
}
