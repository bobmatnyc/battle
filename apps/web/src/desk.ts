// DOM wiring for the command desk (docs/research/70, 71, 73): reads the commander view,
// draws it with its map features, turns clicks into a selection, sends any order kind the
// battle offers, starts a scenario from the POC's catalog, and replays the current battle in
// the commander view. Rules stay in Python; every refusal is shown in #notice with the server's own text.
import type {CommanderState, CommanderView, MapDocument, ScenarioList} from "@battle/contracts";
import {DeskRefusal, type DeskApi} from "./api.ts";
import {reread, sendFormation, sendOrder, sendStanding, startBattle, type Loaded} from "./commands.ts";
import {statusTableFor} from "./feature-sources.ts";
import {featureLegend} from "./features.ts";
import {
  combineBody, combinePartners, defaultSplit, formationHelp, operationsMarkup, partnerOptions, splitBody,
} from "./formations.ts";
import {orderBody, templateFor} from "./orders.ts";
import {
  dispatchesMarkup, missionMarkup, outcomeText, scenarioOptions, signalsMarkup, templateHelp, templateOptions, unitCardMarkup,
} from "./panels.ts";
import {contactsMarkup, esc, featureOptions, mapMarkup, ordersMarkup} from "./render.ts";
import {
  browserTimers, openReplay, ordersClosedReason, ordersOpen, Playback, replayAt, replayHelp, replayLabel, speedOptions,
  type Replay,
} from "./replay.ts";
import {clickMap, emptySelection, ownUnit, type MapTarget, type Notice, type Selection} from "./selection.ts";
import {cancelBody, standingBody, standingCurrent, standingHelp, standingListMarkup, standingOptions} from "./standing.ts";
import {battleClock, timeAt} from "./timeline.ts";
import {FIT, mapFocus, pan, viewBox, zoomIn, zoomWindow, type Zoom} from "./zoom.ts";

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
 * of every offered kind, standing orders (send and cancel) and split/combine (docs/research/81 §12),
 * the clock, the grid toggle, zoom (fit or 2x about the objective, with pan; reset for a new game; bt-T26),
 * starting a scenario and the commander replay;
 * polls while the clock runs or a new battle's map still needs reading. A command whose outcome
 * the relay could not confirm is followed by a re-read. While replaying, the map, header and
 * panels show the recorded view, and orders, the clock and new battles are disabled. Playback
 * (docs/research/81) runs at a speed from the live clock's `speeds`; any step, scrub, Return to
 * live or reopening stops it first, so no timer outlives the replay it was started for.
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
  const playButton = element<HTMLButtonElement>(doc, "replay-play");
  const speedSelect = element<HTMLSelectElement>(doc, "replay-speed");
  const standingSelect = element<HTMLSelectElement>(doc, "standing-profile");
  const standingButton = element<HTMLButtonElement>(doc, "send-standing");
  const cancelButton = element<HTMLButtonElement>(doc, "cancel-standing");
  const splitInput = element<HTMLInputElement>(doc, "split-count");
  const splitButton = element<HTMLButtonElement>(doc, "send-split");
  const partnerSelect = element<HTMLSelectElement>(doc, "combine-partner");
  const combineButton = element<HTMLButtonElement>(doc, "send-combine");
  const zoomInButton = element<HTMLButtonElement>(doc, "map-zoom-in");
  const zoomOutButton = element<HTMLButtonElement>(doc, "map-zoom-out");
  const fitButton = element<HTMLButtonElement>(doc, "map-fit");
  const panButtons = ([["w", -1, 0], ["e", 1, 0], ["n", 0, -1], ["s", 0, 1]] as const)
    .map(([to, dx, dy]) => ({button: element<HTMLButtonElement>(doc, `map-pan-${to}`), dx, dy}));
  let view: CommanderState;
  let terrain: MapDocument;
  let terrainGame = "";  // the game `terrain` belongs to
  let catalog: ScenarioList | null = null;
  let replay: Replay | null = null;
  let selection: Selection = emptySelection;
  let kind = "move";
  let profile = "";       // the standing template chosen in the form
  let splitCount = 0;
  let splitFor = "";      // the unit `splitCount` was defaulted for
  let current: Notice | null = null;
  let busy = false;
  let polling = false;
  let zoom: Zoom = FIT;   // bt-T26: presentation only; back to fit when a new game is adopted
  const playback = new Playback({
    current: () => replay,
    load: (from, index) => replayAt(api, from, index),
    show: (next) => { replay = next; render(); },
    stopped: (error) => { if (error !== null) current = {kind: "refusal", text: message(error)}; render(); },
  }, browserTimers, 1);

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
    // docs/research/81 §2: the help says when and why orders are closed; while replaying, only that.
    const closed = fresh() ? ordersClosedReason(view, replay) : null;
    element(doc, "order-help").innerHTML = (closed ? `<p class="order-closed">${esc(closed)}</p>` : "")
      + (replay ? "" : template ? templateHelp(seen, template) : "This battle offers no orders.");
    const unit = ownUnit(seen, selection.unitId);
    element(doc, "unit-card").innerHTML = unit ? unitCardMarkup(seen, unit, clock) : "";
    element(doc, "selection").textContent = !unit ? "Select one of your counters on the map."
      : `${unit.id} · ${unit.name} · ${unit.status} · hex ${unit.pos.join(",")}`
        + (replay || template?.destination !== "hex" ? "" : selection.destination ? ` → hex ${selection.destination.join(",")}` : " · click a destination hex");
    const open = ordersOpen(view, replay, busy) && fresh();
    kindSelect.disabled = !open || !unit;
    sendButton.disabled = !open || orderBody(view, selection, kind) === null;
  }

  // docs/research/81 §12: standing orders, split and combine for the selected unit. The lists show
  // the drawn view (live or replayed); the bodies are built from the live view, as orders are.
  function renderCommandForms(): void {
    const seen = shown();
    const unit = ownUnit(seen, selection.unitId);
    const open = ordersOpen(view, replay, busy) && fresh() && unit !== undefined;
    if (!seen.standing_templates.some((t) => t.id === profile)) profile = seen.standing_templates[0]?.id ?? "";
    const options = standingOptions(seen, profile);
    if (standingSelect.dataset["options"] !== options) { standingSelect.innerHTML = options; standingSelect.dataset["options"] = options; }
    standingSelect.value = profile;
    standingSelect.disabled = !open;
    element(doc, "standing-current").textContent = unit ? `${unit.id}: ${standingCurrent(seen, unit)}`
      : "Select one of your counters to give it standing instructions.";
    const first = seen.standing_templates[0]?.label ?? "";
    element(doc, "standing-help").innerHTML = standingHelp(seen, profile)
      + (first ? `<br><small>An instruction already sent cannot be recalled; Cancel sends ${esc(first)}, which supersedes it on arrival.</small>` : "");
    standingButton.disabled = !open || standingBody(view, selection.unitId, profile) === null;
    cancelButton.disabled = !open || cancelBody(view, selection.unitId) === null;
    element(doc, "standing-orders").innerHTML = standingListMarkup(seen, clock);

    if (unit && unit.id !== splitFor) { splitCount = defaultSplit(unit); splitFor = unit.id; splitInput.value = String(splitCount); }
    const partners = unit ? combinePartners(seen, unit) : [];
    const chosen = partners.some((u) => u.id === partnerSelect.value) ? partnerSelect.value : partners[0]?.id ?? "";
    const choices = partnerOptions(partners, chosen);
    if (partnerSelect.dataset["options"] !== choices) { partnerSelect.innerHTML = choices; partnerSelect.dataset["options"] = choices; }
    partnerSelect.value = chosen;
    splitInput.disabled = !open;
    partnerSelect.disabled = !open || !partners.length;
    splitButton.disabled = !open || splitBody(view, selection.unitId, splitCount, selection.destination) === null;
    combineButton.disabled = !open || combineBody(view, selection.unitId, chosen) === null;
    element(doc, "formation-help").textContent = unit && !replay ? formationHelp(seen, unit, splitCount, selection.destination) : "";
    element(doc, "formation-ops").innerHTML = operationsMarkup(seen, clock);
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
    playButton.textContent = playback.playing ? "Pause" : "Play";
    playButton.disabled = busy;
    const speeds = speedOptions(view.clock.speeds, playback.speed);
    if (speedSelect.dataset["options"] !== speeds) { speedSelect.innerHTML = speeds; speedSelect.dataset["options"] = speeds; }
    speedSelect.value = String(playback.speed);
    element(doc, "replay-help").textContent = replayHelp();
  }

  // bt-T26: zoom in to 2x (the POC desk's focus), back out to fit, and pan the 2x window.
  function renderZoom(): void {
    const drawn = fresh();
    zoomInButton.disabled = !drawn || zoom.scale === 2;
    zoomOutButton.disabled = fitButton.disabled = !drawn || zoom.scale === 1;
    for (const p of panButtons) p.button.disabled = !drawn || pan(zoom, terrain, p.dx, p.dy) === zoom;
    element(doc, "map-zoom-level").textContent = `${zoom.scale}× view`;
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
    renderZoom();
    if (fresh()) {
      // bt-T26: the SVG shows the zoom's window, and labels are placed inside it (docs/research/80 §7).
      const frame = zoomWindow(zoom, terrain);
      svg.setAttribute("viewBox", viewBox(frame));
      svg.innerHTML = mapMarkup(seen, terrain, replay ? {unitId: selection.unitId, destination: null} : selection, sources, frame);
      element(doc, "feature-legend").innerHTML = featureLegend(seen.map_features, featureOptions(terrain, sources));
    } else {
      svg.innerHTML = "";
      element(doc, "feature-legend").innerHTML = "";
    }
    element(doc, "orders").innerHTML = ordersMarkup(seen, clock);
    element(doc, "dispatches").innerHTML = dispatchesMarkup(seen, clock);
    const signals = signalsMarkup(seen, clock);  // docs/research/81 §4: delivered codewords only
    element<HTMLElement>(doc, "signals-panel").hidden = signals === null;
    element(doc, "signals").innerHTML = signals ?? "";
    element(doc, "contacts").innerHTML = contactsMarkup(seen, clock);
    renderOrderForm();
    renderCommandForms();
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
    if (next.view.game_id !== view.game_id) { selection = emptySelection; zoom = FIT; }
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

  zoomInButton.addEventListener("click", () => { zoom = zoomIn(zoom, terrain, mapFocus(shown(), terrain)); render(); });
  for (const b of [zoomOutButton, fitButton]) b.addEventListener("click", () => { zoom = FIT; render(); });
  for (const p of panButtons) p.button.addEventListener("click", () => { zoom = pan(zoom, terrain, p.dx, p.dy); render(); });

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

  // docs/research/81 §12: as an order: pause first, build the body from the live view, and on an
  // unknown outcome re-read (commands.ts). A refusal shows the engine's own text (act).
  const command = (build: () => Promise<Notice>): void => void act(async () => {
    if (replay) return {kind: "info", text: REPLAYING};
    await paused();
    return build();
  });
  const standing = (body: ReturnType<typeof standingBody>): Promise<Notice> => {
    if (!body) return Promise.resolve({kind: "info", text: "Select one of your counters and a standing instruction it can take."});
    return sendStanding(api, held(), body).then((step) => { adopt(step.loaded); return step.notice; });
  };
  const formation = (body: ReturnType<typeof splitBody>): Promise<Notice> => {
    if (!body) return Promise.resolve({kind: "info", text: "Select a counter, then an adjacent hex for a split or a partner to combine with."});
    return sendFormation(api, held(), body).then((step) => {
      adopt(step.loaded);
      if (step.notice.kind === "accepted") selection = {unitId: selection.unitId, destination: null};
      return step.notice;
    });
  };
  standingSelect.addEventListener("change", () => { profile = standingSelect.value; render(); });
  standingButton.addEventListener("click", () => command(() => standing(standingBody(view, selection.unitId, profile))));
  cancelButton.addEventListener("click", () => command(() => standing(cancelBody(view, selection.unitId))));
  splitInput.addEventListener("input", () => { splitCount = Number(splitInput.value); render(); });
  partnerSelect.addEventListener("change", () => render());
  splitButton.addEventListener("click", () => command(() => formation(splitBody(view, selection.unitId, splitCount, selection.destination))));
  combineButton.addEventListener("click", () => command(() => formation(combineBody(view, selection.unitId, partnerSelect.value))));

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
    playback.stop();
    await paused();
    playback.setSpeed(view.clock.speed);  // as the POC desk: the live clock's speed
    replay = await openReplay(api, view);
    selection = {unitId: selection.unitId, destination: null};
    return {kind: "info", text: REPLAYING};
  }));
  const step = (index: number): void => {
    if (!replay || busy) return;
    playback.stop();
    void act(async () => { replay = replay ? await replayAt(api, replay, index) : null; return {kind: "info", text: REPLAYING}; });
  };
  backButton.addEventListener("click", () => step((replay?.index ?? 0) - 1));
  forwardButton.addEventListener("click", () => step((replay?.index ?? 0) + 1));
  slider.addEventListener("input", () => step(Number(slider.value)));
  slider.addEventListener("change", () => step(Number(slider.value)));
  playButton.addEventListener("click", () => {
    if (!replay || busy) return;
    if (playback.playing) playback.stop();
    else { current = {kind: "info", text: REPLAYING}; playback.play(); }
    render();
  });
  speedSelect.addEventListener("change", () => { playback.setSpeed(Number(speedSelect.value)); render(); });
  liveButton.addEventListener("click", () => act(async () => {
    playback.stop();
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
