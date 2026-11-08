// DOM wiring for the command desk: reads the commander view, draws it, turns
// clicks into a selection and sends one move order. Rules stay in Python;
// every refusal is shown in #notice with the server's own text.
import type {CommanderState, MapDocument} from "@battle/contracts";
import type {DeskApi} from "./api.ts";
import {contactsMarkup, mapMarkup, ordersMarkup} from "./render.ts";
import {clickMap, emptySelection, moveOrder, ownUnit, type MapTarget, type Notice, type Selection} from "./selection.ts";
import {battleClock, timeAt} from "./timeline.ts";

const POLL_MS = 1000;
const SETTLE_TRIES = 40;
const SETTLE_MS = 150;

const wait = (ms: number): Promise<void> => new Promise((done) => setTimeout(done, ms));
const message = (error: unknown): string => (error instanceof Error ? error.message : String(error));

function element<T extends Element>(doc: Document, id: string): T {
  const found = doc.getElementById(id);
  if (!found) throw new Error(`The desk page has no #${id}`);
  return found as unknown as T;
}

function target(node: EventTarget | null): MapTarget | null {
  if (!(node instanceof Element)) return null;
  const unit = node.closest("[data-unit]");
  if (unit) return {kind: "unit", id: unit.getAttribute("data-unit") ?? ""};
  const contact = node.closest("[data-contact]");
  if (contact) return {kind: "contact", id: contact.getAttribute("data-contact") ?? ""};
  const hex = node.closest("[data-c]");
  if (hex) return {kind: "hex", pos: [Number(hex.getAttribute("data-c")), Number(hex.getAttribute("data-r"))]};
  return null;
}

/** Why: the TypeScript desk must play the POC battle with the same information limits.
 * What: loads the commander view and map, renders them, and handles map clicks, the
 * move order and the clock; polls while the clock runs.
 * Test: `apps/web/scripts/smoke-browser.ts` (a real click in a browser against the POC). */
export async function startDesk(doc: Document, api: DeskApi): Promise<void> {
  const svg = element<SVGSVGElement>(doc, "map");
  const notice = element<HTMLElement>(doc, "notice");
  const sendButton = element<HTMLButtonElement>(doc, "send-order");
  const clockButton = element<HTMLButtonElement>(doc, "clock-toggle");
  let view: CommanderState;
  let terrain: MapDocument;
  let selection: Selection = emptySelection;
  let current: Notice | null = null;
  let busy = false;

  const clock = (turn: number): string => timeAt(terrain.setting, turn * view.seconds_per_turn, view.display_locale);

  function render(): void {
    const header = battleClock(terrain.setting, view.turn, view.seconds_per_turn, view.display_locale);
    element(doc, "battle-time").textContent = header.time;
    element(doc, "battle-date").textContent = header.date;
    element(doc, "battle-location").textContent = header.location;
    element(doc, "campaign").textContent = view.scenario_brief?.campaign ?? "";
    element(doc, "title").textContent = view.scenario_brief?.title ?? "Command desk";
    svg.setAttribute("viewBox", `0 0 ${terrain.width} ${terrain.height}`);
    svg.innerHTML = mapMarkup(view, terrain, selection);
    element(doc, "orders").innerHTML = ordersMarkup(view, clock);
    element(doc, "contacts").innerHTML = contactsMarkup(view, clock);
    const unit = ownUnit(view, selection.unitId);
    element(doc, "selection").textContent = !unit ? "Select one of your counters on the map."
      : `${unit.id} · ${unit.name} · ${unit.status} · hex ${unit.pos.join(",")}`
        + (selection.destination ? ` → hex ${selection.destination.join(",")}` : " · click a destination hex");
    sendButton.disabled = busy || view.status !== "active" || moveOrder(view, selection) === null;
    clockButton.disabled = busy || view.status !== "active";
    clockButton.textContent = view.clock.running ? "Pause clock" : "Start clock";
    notice.textContent = current?.text ?? (view.status === "active" ? "" : "Battle complete.");
    notice.dataset["kind"] = current?.kind ?? "info";
  }

  async function refresh(): Promise<void> {
    const gameId = view.game_id;
    view = await api.state();
    if (view.game_id !== gameId) { terrain = await api.map(); selection = emptySelection; }
  }

  // Orders are taken only while paused (BattleService._ensure_paused): pause and let an interval finish.
  async function paused(): Promise<void> {
    if (!view.clock.running && !view.clock.inflight) return;
    view = await api.clock("pause", view.game_id);
    for (let i = 0; view.clock.inflight && i < SETTLE_TRIES; i++) { await wait(SETTLE_MS); view = await api.state(); }
  }

  async function act(work: () => Promise<Notice | null>): Promise<void> {
    if (busy) return;
    busy = true;
    render();
    try {
      current = await work();
    } catch (error) {
      current = {kind: "refusal", text: message(error)};
      try { await refresh(); } catch { /* the refusal above is what the player needs */ }
    } finally {
      busy = false;
      render();
    }
  }

  svg.addEventListener("click", (event) => {
    const hit = target(event.target);
    if (!hit || busy) return;
    const step = clickMap(view, selection, hit);
    selection = step.selection;
    current = step.notice;
    render();
  });

  sendButton.addEventListener("click", () => act(async () => {
    await paused();
    const body = moveOrder(view, selection);
    if (!body) return {kind: "info", text: "Select a counter and a destination hex."};
    const order = body.orders[0]!;
    view = await api.orders(body);
    selection = {unitId: selection.unitId, destination: null};
    return {kind: "accepted", text: `Order accepted: ${order.unit_id} move → hex ${String(order.destination)}. Start the clock to carry it out.`};
  }));

  clockButton.addEventListener("click", () => act(async () => {
    view = await api.clock(view.clock.running ? "pause" : "start", view.game_id);
    return null;
  }));

  try {
    [view, terrain] = await Promise.all([api.state(), api.map()]);
  } catch (error) {
    notice.textContent = `Could not read the local simulation: ${message(error)}`;
    notice.dataset["kind"] = "refusal";
    return;
  }
  current = null;
  render();
  doc.documentElement.dataset["deskReady"] = "true";
  setInterval(() => {
    if (busy || (!view.clock.running && !view.clock.inflight)) return;
    refresh().then(render, (error: unknown) => { current = {kind: "refusal", text: message(error)}; render(); });
  }, POLL_MS);
}
