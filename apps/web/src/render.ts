// Markup for the desk, drawn only from the commander view and the map document.
// Every server string passes through `esc`. Enemy markers come from `contacts`
// (estimates); exact enemy values are not in the view, and none is drawn.
import type {CommanderView, Contact, MapDocument, UnitReport} from "@battle/contracts";
import type {StatusTable} from "./feature-sources.ts";
import {featureLayer, featureNotes, type FeatureOptions} from "./features.ts";
import {hexCenter, hexPoints} from "./geometry.ts";
import {esc} from "./markup.ts";
import type {Selection} from "./selection.ts";

export {esc};

// Water and marsh as the POC desk fills them (docs/research/72 §1).
const TERRAIN_FILL: Record<string, string> = {open: "#e7e0c4", woods: "#b9c99a", rocky: "#c9c1b0", water: "#b9d3e3", marsh: "#d7e3cf"};
const SYMBOLS: Record<string, string> = {infantry: "INF", cavalry: "CAV", artillery: "ART"};
// bt-T11: the POC desk's ring is r=53 on its 25.5 hex radius (apps/poc/static/app.js renderMap).
const RING_PER_RADIUS = 53 / 25.5;

const percent = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(100, Math.round(value))) : null;
const shown = (value: number | null): string => (value === null ? "?" : String(value));

/** Counter lines for an own unit: strength and type, then skill, energy (100 - fatigue) and morale. */
export function unitLines(unit: UnitReport): [string, string] {
  const symbol = SYMBOLS[String(unit["unit_type"])] ?? "?";
  const scout = unit["recon_role"] === "scout" ? "/SC" : "";
  const fatigue = percent(unit.fatigue);
  const energy = fatigue === null ? null : 100 - fatigue;
  return [`${unit.strength} ${symbol}${scout}`, `S${shown(percent(unit["skill"]))} E${shown(energy)} M${shown(percent(unit.morale))}`];
}

/** Counter lines for a sighting: the reported range, never an exact value. */
export function contactLines(contact: Contact): [string, string] {
  const range = Array.isArray(contact["strength_range"]) ? (contact["strength_range"] as unknown[]).join("–") : "?";
  const composition = contact["composition"] as {type?: unknown} | undefined;
  return [`${range} ${SYMBOLS[String(composition?.type)] ?? "?"}`, "S? E? M?"];
}

function counter(kind: "friendly" | "contact", id: string, point: [number, number], lines: [string, string],
  title: string, selected: boolean): string {
  const [x, y] = point;
  const data = kind === "friendly" ? `data-unit="${esc(id)}"` : `data-contact="${esc(id)}"`;
  const pressed = kind === "friendly" ? ` role="button" tabindex="0" aria-pressed="${selected}"` : "";
  return `<g class="counter ${kind}${selected ? " selected" : ""}" ${data}${pressed} transform="translate(${(x - 37).toFixed(1)},${(y - 17).toFixed(1)})">`
    + `<title>${esc(title)}</title><rect width="74" height="34" rx="3"/>`
    + `<text x="4" y="11" class="counter-id">${esc(id)}</text>`
    + `<text x="4" y="21">${esc(lines[0])}</text><text x="4" y="31">${esc(lines[1])}</text></g>`;
}

/** The feature options for `map`: its scale, briefing cells and radius, with `sources`' statuses. */
export const featureOptions = (map: MapDocument, sources: StatusTable): FeatureOptions =>
  ({metresPerHex: map.metres_per_hex, cells: map.cells, sources, radius: map.radius});

/** Why: the map is the player's main view and must show only what the commander view holds.
 * What: SVG markup: one hex per map cell (its tooltip names each feature mark on it, with
 * status), the objective (with a dashed ring round it and its neighbours when the brief's
 * `objective.ring` is set), the view's map features, a dashed line to the chosen destination,
 * a counter per own unit (`data-unit`) and per contact (`data-contact`).
 * Test: `the map draws every cell and the player's own counters`,
 * `enemy counters come from contacts and carry no exact values`, `text from the server is escaped`,
 * `a hold-objective brief rings the objective`, `no ring without the brief's ring flag or without a brief`,
 * `the map draws the commander view's features above the hexes and below the counters, with status in each hex tooltip`. */
export function mapMarkup(view: CommanderView, map: MapDocument, selection: Selection, sources: StatusTable = {}): string {
  const r = map.radius;
  const chosen = selection.destination ? String(selection.destination) : "";
  const options = featureOptions(map, sources);
  const hexes = map.cells.map((cell) => {
    const cls = String(cell.pos) === chosen ? "hex destination" : "hex";
    const notes = featureNotes(view.map_features, cell.pos, options).map((n) => ` · ${esc(n)}`).join("");
    return `<polygon class="${cls}" data-c="${cell.pos[0]}" data-r="${cell.pos[1]}" points="${hexPoints(cell.pos, r)}" `
      + `fill="${TERRAIN_FILL[cell.terrain] ?? "#ddd"}"><title>Hex ${cell.pos.join(",")} · ${esc(cell.terrain)} · ${cell.elevation} m${notes}</title></polygon>`;
  }).join("");
  const [ox, oy] = hexCenter(view.objective, r);
  const label = view.scenario_brief?.objective.label ?? "Objective";
  // bt-T11: the brief sets `ring` for a hold-objective victory; no brief, no ring.
  const ring = view.scenario_brief?.objective.ring === true
    ? `<circle class="objective-ring" pointer-events="none" cx="${ox.toFixed(1)}" cy="${oy.toFixed(1)}" r="${(r * RING_PER_RADIUS).toFixed(1)}"/>`
    : "";
  const objective = `<g class="objective" pointer-events="none">${ring}<circle cx="${ox.toFixed(1)}" cy="${oy.toFixed(1)}" r="${(r * 0.6).toFixed(1)}"/>`
    + `<text x="${ox.toFixed(1)}" y="${(oy + r * 0.6 + 12).toFixed(1)}" text-anchor="middle">${esc(label)}</text></g>`;
  const unit = view.units.find((u) => u.id === selection.unitId);
  let route = "";
  if (unit && selection.destination) {
    const [a, b] = hexCenter(unit.pos, r);
    const [c, d] = hexCenter(selection.destination, r);
    route = `<path class="route" pointer-events="none" d="M${a.toFixed(1)},${b.toFixed(1)}L${c.toFixed(1)},${d.toFixed(1)}"/>`;
  }
  const contacts = view.contacts.map((c) => counter("contact", c.id, hexCenter(c.pos, r), contactLines(c),
    `${c.id} · ${c.estimate} · ${c.confidence} confidence`, false)).join("");
  const own = view.units.map((u) => counter("friendly", u.id, hexCenter(u.pos, r), unitLines(u),
    `${u.id} · ${u.name} · ${u.status}`, u.id === selection.unitId)).join("");
  return `<g class="hexes">${hexes}</g>${objective}${featureLayer(view.map_features, options)}${route}`
    + `<g class="contacts">${contacts}</g><g class="units">${own}</g>`;
}

/** The enemy-intelligence list: each delivered sighting with its estimate and age. */
export function contactsMarkup(view: CommanderView, clock: (turn: number) => string): string {
  if (!view.contacts.length) return "<li>No delivered enemy sightings.</li>";
  return view.contacts.map((c) => `<li data-contact-row="${esc(c.id)}"><b>${esc(c.id)}</b> · ${esc(c.estimate)} · `
    + `${esc(c.confidence)} confidence · hex ${c.pos.join(",")} · seen ${esc(clock(c.observed_turn))}</li>`).join("");
}

/** Own orders, newest first: the template, the status headquarters knows, and battlefield
 * send and expected delivery times (the delivery estimate only while en route). */
export function ordersMarkup(view: CommanderView, clock: (turn: number) => string): string {
  if (!view.orders.length) return "<li>No orders sent.</li>";
  return [...view.orders].reverse().map((o) => {
    const where = o.destination ? ` → hex ${o.destination.join(",")}` : "";
    const label = view.order_templates.find((t) => t.id === o.stance)?.label;
    const due = o.status === "en_route" && o.arrival_turn !== null ? ` · due ${esc(clock(o.arrival_turn))}` : "";
    return `<li data-order="${esc(o.id)}" data-order-unit="${esc(o.unit_id)}">${esc(o.unit_id)} · ${esc(o.stance)}${where}`
      + `${label ? ` · ${esc(label)}` : ""} · ${esc(o.status.replaceAll("_", " "))} · sent ${esc(clock(o.sent_turn))}${due}</li>`;
  }).join("");
}
