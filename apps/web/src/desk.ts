// DOM wiring for the command desk (docs/research/70, 71, 73): reads the commander view,
// draws it with its map features, turns clicks into a selection, sends any order kind the
// battle offers, starts a scenario from the POC's catalog, and replays the current battle in
// the commander view. Rules stay in Python; every refusal is shown in #notice with the server's own text.
import type {CommanderState, CommanderView, MapDocument, ScenarioList} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "./api.ts";
import {reread, sendOrder, startBattle, type Loaded} from "./commands.ts";
import {statusTableFor} from "./feature-sources.ts";
import {featureLegend} from "./features.ts";
import {orderBody, templateFor} from "./orders.ts";
import {dispatchesMarkup, missionMarkup, outcomeText, scenarioOptions, templateHelp, templateOptions, unitCardMarkup} from "./panels.ts";
import {contactsMarkup, featureOptions, mapMarkup, ordersMarkup} from "./render.ts";
import {openReplay, ordersOpen, replayAt, replayLabel, type Replay} from "./replay.ts";
import {clickMap, emptySelection, ownUnit, type MapTarget, type Notice, type Selection} from "./selection.ts";
import {battleClock, timeAt} from "./timeline.ts";

const POLL_MS = 1000;
// A paused clock may still be finishing a commander turn (up to the relay timeout).
const SETTLE_MS = 250;
const SETTLE_LIMIT_MS = 120000;
const REPLAYING = "Replaying the recorded commander view. Orders are disabled; return to live to command.";

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
 * What: loads the commander view, map and scenario catalog, renders them with the map features
 * (status from `featureSources`, the POC's BattleFeatureSources), and handles map clicks, orders
 * of every offered kind, the clock, the grid toggle, starting a scenario and the commander replay;
 * polls while the clock runs or a new battle's map still needs reading. A command whose outcome
 * the relay could not confirm is followed by a re-read. While replaying, the map, header and
 * panels show the recorded view, and orders, the clock and new battles are disabled.
 * Test: `apps/web/scripts/smoke-browser.ts` (real clicks in a browser against the POC). */
export async function startDesk(doc: Document, api: DeskApi, featureSources: unknown = null): Promise<void> {
  const svg = element<SVGSVGElement>(doc, "map");
  const notice = element<HTMLElement>(doc, "notice");
  const sendButton = element<HTMLButtonElement>(doc, "send-order");
  const kindSelect = element<HTMLSelectElement>(doc, "order-kind");
  const clockButton = element<HTMLButtonElement>(doc, "clock-toggle");
  const scenarioSelect = element<HTMLSelectElement>(doc, "scenario-select");
  const newButton = element<HTMLButtonElement>(doc, "new-battle");
  const gridButton = element<HTMLButtonElement>(doc, "grid-toggle");
  const replayButton = element<HTMLButtonElement>(doc, "replay-toggle");
  const replayBar = element<HTMLElement>(doc, "replay-bar");
  const slider = element<HTMLInputElement>(doc, "replay-slider");
  const backButton = element<HTMLButtonElement>(doc, "replay-back");
  const forwardButton = element<HTMLButtonElement>(doc, "replay-forward");
  const liveButton = element<HTMLButtonElement>(doc, "replay-live");
  let view: CommanderState;
  let terrain: MapDocument;
  let terrainGame = "";  // the game `terrain` belongs to
  let catalog: ScenarioList | null = null;
  let replay: Replay | null = null;
  let selection: Selection = emptySelection;
  let kind = "move";
  let current: Notice | null = null;
  let busy = false;
  let polling = false;

  // While replaying, everything drawn is the recorded view; orders go to `view` (live) only.
  const shown = (): CommanderView => replay?.view ?? view;
  // Slice 2 review: a new battle whose map read failed keeps the old terrain tagged with the old
  // game; nothing is drawn against it until the map is read again.
  const fresh = (): boolean => terrainGame === view.game_id;
  const clock = (turn: number): string => fresh() ? timeAt(terrain.setting, turn * shown().seconds_per_turn, shown().display_locale) : "--:--";

  function renderOrderForm(): void {
    const seen = shown();
    if (!templateFor(seen, kind)) kind = seen.order_templates[0]?.id ?? "";
    const options = templateOptions(seen, kind);
    if (kindSelect.dataset["options"] !== options) { kindSelect.innerHTML = options; kindSelect.dataset["options"] = options; }
    kindSelect.value = kind;
    const template = templateFor(seen, kind);
    element(doc, "order-help").innerHTML = template ? templateHelp(seen, template) : "This battle offers no orders.";
    const unit = ownUnit(seen, selection.unitId);
    element(doc, "unit-card").innerHTML = unit ? unitCardMarkup(seen, unit, clock) : "";
    element(doc, "selection").textContent = !unit ? "Select one of your counters on the map."
      : `${unit.id} · ${unit.name} · ${unit.status} · hex ${unit.pos.join(",")}`
        + (replay || template?.destination !== "hex" ? "" : selection.destination ? ` → hex ${selection.destination.join(",")}` : " · click a destination hex");
    const open = ordersOpen(view, replay, busy) && fresh();
    kindSelect.disabled = !open || !unit;
    sendButton.disabled = !open || orderBody(view, selection, kind) === null;
  }

  function renderReplay(): void {
    replayBar.hidden = replay === null;
    replayButton.disabled = busy || replay !== null || !fresh();
    if (!replay) return;
    const label = fresh() ? replayLabel(replay, terrain.setting) : "";
    element(doc, "replay-label").textContent = label;
    slider.max = String(replay.entries.length - 1);
    slider.value = String(replay.index);
    slider.setAttribute("aria-valuetext", label);
    slider.disabled = busy;
    backButton.disabled = busy || replay.index === 0;
    forwardButton.disabled = busy || replay.index === replay.entries.length - 1;
    liveButton.disabled = busy;
  }

  function render(): void {
    const seen = shown();
    const header = fresh() ? battleClock(terrain.setting, seen.turn, seen.seconds_per_turn, seen.display_locale) : null;
    element(doc, "battle-time").textContent = header?.time ?? "--:--";
    element(doc, "battle-date").textContent = header?.date ?? "";
    element(doc, "battle-location").textContent = header?.location ?? "";
    element(doc, "campaign").textContent = seen.scenario_brief?.campaign ?? "";
    element(doc, "title").textContent = seen.scenario_brief?.title ?? "Command desk";
    doc.title = `battle · ${seen.scenario_brief?.title ?? "command desk"}`;
    element(doc, "mission").innerHTML = missionMarkup(seen);
    const sources = statusTableFor(featureSources, seen.scenario_brief?.id);
    if (fresh()) {
      svg.setAttribute("viewBox", `0 0 ${terrain.width} ${terrain.height}`);
      svg.innerHTML = mapMarkup(seen, terrain, replay ? {unitId: selection.unitId, destination: null} : selection, sources);
      element(doc, "feature-legend").innerHTML = featureLegend(seen.map_features, featureOptions(terrain, sources));
    } else {
      svg.innerHTML = "";
      element(doc, "feature-legend").innerHTML = "";
    }
    element(doc, "orders").innerHTML = ordersMarkup(seen, clock);
    element(doc, "dispatches").innerHTML = dispatchesMarkup(seen, clock);
    element(doc, "contacts").innerHTML = contactsMarkup(seen, clock);
    renderOrderForm();
    renderReplay();
    if (catalog) {
      const options = scenarioOptions(catalog, view.scenario_brief?.id ?? null);
      if (scenarioSelect.dataset["options"] !== options && doc.activeElement !== scenarioSelect) {
        scenarioSelect.innerHTML = options;
        scenarioSelect.dataset["options"] = options;
      }
    }
    scenarioSelect.disabled = busy || !catalog || replay !== null;
    newButton.disabled = busy || !catalog || replay !== null;
    clockButton.disabled = busy || view.status !== "active" || replay !== null;
    clockButton.textContent = view.clock.running ? "Pause clock" : "Start clock";
    notice.textContent = current?.text ?? (view.status === "active" ? "" : "Battle complete.");
    // docs/research/74: the live battle's outcome headline, in the brief's words.
    const outcome = outcomeText(view);
    element<HTMLElement>(doc, "outcome").hidden = outcome === null;
    element(doc, "outcome-headline").textContent = outcome?.headline ?? "";
    element(doc, "outcome-reason").textContent = outcome?.reason ?? "";
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
    if (replay && hit.kind === "hex") {
      current = {kind: "info", text: REPLAYING};
    } else {
      const step = clickMap(shown(), selection, hit);
      selection = step.selection;
      current = step.notice;
    }
    render();
  });

  kindSelect.addEventListener("change", () => { kind = kindSelect.value; current = null; render(); });

  gridButton.addEventListener("click", () => {
    // Hex outlines only (style.css `#map.no-grid .hex`); terrain fills and map features stay.
    const on = svg.classList.toggle("no-grid");
    gridButton.setAttribute("aria-pressed", String(!on));
  });

  sendButton.addEventListener("click", () => act(async () => {
    if (replay) return {kind: "info", text: REPLAYING};
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

  // docs/research/73: the replay reads recorded revisions of this game; the live clock is paused first,
  // as the POC desk does, so the live battle does not run on unseen.
  replayButton.addEventListener("click", () => act(async () => {
    await paused();
    replay = await openReplay(api, view);
    selection = {unitId: selection.unitId, destination: null};
    return {kind: "info", text: REPLAYING};
  }));
  const step = (index: number): void => {
    if (!replay || busy) return;
    void act(async () => { replay = replay ? await replayAt(api, replay, index) : null; return {kind: "info", text: REPLAYING}; });
  };
  backButton.addEventListener("click", () => step((replay?.index ?? 0) - 1));
  forwardButton.addEventListener("click", () => step((replay?.index ?? 0) + 1));
  slider.addEventListener("input", () => step(Number(slider.value)));
  slider.addEventListener("change", () => step(Number(slider.value)));
  liveButton.addEventListener("click", () => act(async () => {
    replay = null;
    selection = {unitId: selection.unitId, destination: null};
    await refresh();
    return null;
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
  if (featureSources === null) current = {kind: "refusal", text: "The map-feature status table did not load; marks show no status."};
  render();
  doc.documentElement.dataset["deskReady"] = "true";
  setInterval(() => {
    if (busy || polling || replay || (fresh() && !view.clock.running && !view.clock.inflight)) return;
    polling = true;
    refresh().then(render, (error: unknown) => { current = {kind: "refusal", text: message(error)}; render(); })
      .finally(() => { polling = false; });
  }, POLL_MS);
}
