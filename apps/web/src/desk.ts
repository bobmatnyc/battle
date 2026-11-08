// DOM wiring for the command desk (docs/research/70, 71): reads the commander view,
// draws it, turns clicks into a selection, sends any order kind the battle offers,
// and starts a scenario from the POC's catalog. Rules stay in Python; every refusal
// is shown in #notice with the server's own text.
import type {CommanderState, MapDocument, ScenarioList} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "./api.ts";
import {reread, sendOrder, startBattle, type Loaded} from "./commands.ts";
import {orderBody, templateFor} from "./orders.ts";
import {dispatchesMarkup, missionMarkup, scenarioOptions, templateHelp, templateOptions, unitCardMarkup} from "./panels.ts";
import {contactsMarkup, mapMarkup, ordersMarkup} from "./render.ts";
import {clickMap, emptySelection, ownUnit, type MapTarget, type Notice, type Selection} from "./selection.ts";
import {battleClock, timeAt} from "./timeline.ts";

const POLL_MS = 1000;
// A paused clock may still be finishing a commander turn (up to the relay timeout).
const SETTLE_MS = 250;
const SETTLE_LIMIT_MS = 120000;

const wait = (ms: number): Promise<void> => new Promise((done) => setTimeout(done, ms));
const message = (error: unknown): string => (error instanceof Error ? error.message : String(error));
const unknownOutcome = (error: unknown): boolean => error instanceof DeskRefusal && error.outcomeUnknown;

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
 * What: loads the commander view, map and scenario catalog, renders them, and handles map
 * clicks, orders of every offered kind, the clock and starting a scenario; polls while the
 * clock runs. A command whose outcome the relay could not confirm is followed by a re-read.
 * Test: `apps/web/scripts/smoke-browser.ts` (real clicks in a browser against the POC). */
export async function startDesk(doc: Document, api: DeskApi): Promise<void> {
  const svg = element<SVGSVGElement>(doc, "map");
  const notice = element<HTMLElement>(doc, "notice");
  const sendButton = element<HTMLButtonElement>(doc, "send-order");
  const kindSelect = element<HTMLSelectElement>(doc, "order-kind");
  const clockButton = element<HTMLButtonElement>(doc, "clock-toggle");
  const scenarioSelect = element<HTMLSelectElement>(doc, "scenario-select");
  const newButton = element<HTMLButtonElement>(doc, "new-battle");
  let view: CommanderState;
  let terrain: MapDocument;
  let terrainGame = "";  // the game `terrain` belongs to
  let catalog: ScenarioList | null = null;
  let selection: Selection = emptySelection;
  let kind = "move";
  let current: Notice | null = null;
  let busy = false;
  let polling = false;

  const clock = (turn: number): string => timeAt(terrain.setting, turn * view.seconds_per_turn, view.display_locale);

  function renderOrderForm(): void {
    if (!templateFor(view, kind)) kind = view.order_templates[0]?.id ?? "";
    const options = templateOptions(view, kind);
    if (kindSelect.dataset["options"] !== options) { kindSelect.innerHTML = options; kindSelect.dataset["options"] = options; }
    kindSelect.value = kind;
    const template = templateFor(view, kind);
    element(doc, "order-help").innerHTML = template ? templateHelp(view, template) : "This battle offers no orders.";
    const unit = ownUnit(view, selection.unitId);
    element(doc, "unit-card").innerHTML = unit ? unitCardMarkup(view, unit, clock) : "";
    element(doc, "selection").textContent = !unit ? "Select one of your counters on the map."
      : `${unit.id} · ${unit.name} · ${unit.status} · hex ${unit.pos.join(",")}`
        + (template?.destination !== "hex" ? "" : selection.destination ? ` → hex ${selection.destination.join(",")}` : " · click a destination hex");
    const inactive = busy || view.status !== "active" || !view.command.operational;
    kindSelect.disabled = inactive || !unit;
    sendButton.disabled = inactive || orderBody(view, selection, kind) === null;
  }

  function render(): void {
    const header = battleClock(terrain.setting, view.turn, view.seconds_per_turn, view.display_locale);
    element(doc, "battle-time").textContent = header.time;
    element(doc, "battle-date").textContent = header.date;
    element(doc, "battle-location").textContent = header.location;
    element(doc, "campaign").textContent = view.scenario_brief?.campaign ?? "";
    element(doc, "title").textContent = view.scenario_brief?.title ?? "Command desk";
    doc.title = `battle · ${view.scenario_brief?.title ?? "command desk"}`;
    element(doc, "mission").innerHTML = missionMarkup(view);
    svg.setAttribute("viewBox", `0 0 ${terrain.width} ${terrain.height}`);
    svg.innerHTML = mapMarkup(view, terrain, selection);
    element(doc, "orders").innerHTML = ordersMarkup(view, clock);
    element(doc, "dispatches").innerHTML = dispatchesMarkup(view, clock);
    element(doc, "contacts").innerHTML = contactsMarkup(view, clock);
    renderOrderForm();
    if (catalog) {
      const options = scenarioOptions(catalog, view.scenario_brief?.id ?? null);
      if (scenarioSelect.dataset["options"] !== options && doc.activeElement !== scenarioSelect) {
        scenarioSelect.innerHTML = options;
        scenarioSelect.dataset["options"] = options;
      }
    }
    scenarioSelect.disabled = busy || !catalog;
    newButton.disabled = busy || !catalog;
    clockButton.disabled = busy || view.status !== "active";
    clockButton.textContent = view.clock.running ? "Pause clock" : "Start clock";
    notice.textContent = current?.text ?? (view.status === "active" ? "" : "Battle complete.");
    notice.dataset["kind"] = current?.kind ?? "info";
  }

  const held = (): Loaded => ({view, terrain, terrainGame});
  function adopt(next: Loaded): void {
    if (next.view.game_id !== view.game_id) selection = emptySelection;
    ({view, terrain, terrainGame} = next);
  }

  async function refresh(): Promise<void> {
    adopt(await reread(api, held()));
  }

  // Commands are taken only while paused (BattleService._ensure_paused): pause and let an interval finish.
  async function paused(): Promise<void> {
    if (!view.clock.running && !view.clock.inflight) return;
    view = await api.clock("pause", view.game_id);
    const end = Date.now() + SETTLE_LIMIT_MS;
    while (view.clock.inflight && Date.now() < end) { await wait(SETTLE_MS); view = await api.state(); }
  }

  async function act(work: () => Promise<Notice | null>): Promise<void> {
    if (busy) return;
    busy = true;
    render();
    try {
      current = await work();
    } catch (error) {
      current = {kind: unknownOutcome(error) ? "unknown" : "refusal", text: message(error)};
      try { await refresh(); } catch { /* the notice above is what the player needs */ }
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

  kindSelect.addEventListener("change", () => { kind = kindSelect.value; current = null; render(); });

  sendButton.addEventListener("click", () => act(async () => {
    await paused();
    const body = orderBody(view, selection, kind);
    if (!body) return {kind: "info", text: "Select a counter, an order and any destination it needs."};
    // Review #6: an unconfirmed order is followed by a re-read (commands.ts).
    const step = await sendOrder(api, held(), body);
    adopt(step.loaded);
    if (step.notice.kind === "accepted") selection = {unitId: selection.unitId, destination: null};
    return step.notice;
  }));

  clockButton.addEventListener("click", () => act(async () => {
    view = await api.clock(view.clock.running ? "pause" : "start", view.game_id);
    return null;
  }));

  newButton.addEventListener("click", () => act(async () => {
    const chosen = catalog?.scenarios.find((s) => s.id === scenarioSelect.value);
    if (!chosen) return {kind: "info", text: "Choose a scenario."};
    await paused();
    const step = await startBattle(api, held(), chosen);
    adopt(step.loaded);
    return step.notice;
  }));

  try {
    [view, terrain] = await Promise.all([api.state(), api.map()]);
    terrainGame = view.game_id;
  } catch (error) {
    notice.textContent = `Could not read the local simulation: ${message(error)}`;
    notice.dataset["kind"] = "refusal";
    return;
  }
  try {
    catalog = await api.scenarios();
  } catch (error) {
    current = {kind: "refusal", text: `Scenario list unavailable: ${message(error)}`};
  }
  render();
  doc.documentElement.dataset["deskReady"] = "true";
  setInterval(() => {
    if (busy || polling || (!view.clock.running && !view.clock.inflight)) return;
    polling = true;
    refresh().then(render, (error: unknown) => { current = {kind: "refusal", text: message(error)}; render(); })
      .finally(() => { polling = false; });
  }, POLL_MS);
}
