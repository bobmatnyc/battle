// Roads, bridges, walled compounds and gates, building footprints and fieldworks, drawn from
// the commander view's map_features and the briefing cells of /api/map (docs/research/73).
// A typed port of the POC desk's renderer, apps/poc/static/map-features.js (docs/research/72);
// `test/features.test.ts` holds the two byte-identical for every catalog entry, so a change to
// either shows up there. Each mark's status comes from the POC's table (feature-sources.ts).
import type {BuildingFeature, BridgeFeature, FortificationFeature, MapCell, MapFeature, Opening, RoadFeature} from "@battle/contracts";
import type {StatusTable} from "./feature-sources.ts";
import {hexCenter} from "./geometry.ts";
import {esc} from "./markup.ts";

type Point = [number, number];
type Hex = readonly [number, number];
type Center = (pos: Hex) => Point;

/** `radius` is the map document's; `cells` are its briefing cells (bridge crossings); `sources` the status table;
 * `obstacles` (optional) the boxes the counters cover, which no label may sit under (docs/research/80);
 * `frame` (optional) the map frame no label may cross (bt-T23, docs/research/80 §7). */
export interface FeatureOptions {
  metresPerHex: number; cells: readonly MapCell[]; sources: StatusTable; radius: number; obstacles?: readonly Rect[]; frame?: Rect;
}
/** A status as drawn: the table's, or "reported" / "unlisted" when the table has none. */
interface Info { status: string; source: string; name?: string; footprint_m?: [number, number] }
export type MarkKind = "road" | "bridge" | "wall" | "gate" | "building" | "works";
/** One drawn mark: its status key, legend kind and name, and the hexes whose tooltip names it. */
export interface Mark { key: string; kind: MarkKind; name: string; hexes: Hex[]; info: Info; label?: LabelSpec; draw(place?: LabelPlace | null): string }

const MIN_SIDE = 6;  // px: the smallest legible footprint side
const ROAD = {casing: "#ae997b", fill: "#fff4d5", casingWidth: 10, fillWidth: 6};
const PASSABLE = ["open", "closing", "forced"];  // battle/gates.py PASSABLE
const LABELS: Record<string, string> = {sourced: "Sourced", reconstructed: "Reconstructed", illustrative: "Illustrative",
  reported: "Reported in battle", unlisted: "Status not recorded"};
const REPORTED: Info = {status: "reported", source: "Built during this battle; drawn as last reported to headquarters."};
const UNLISTED: Info = {status: "unlisted", source: "No status is recorded for this mark in static/feature-sources.js."};
const KINDS: Record<MarkKind, string> = {road: "Road or track", bridge: "Bridge", wall: "Wall", gate: "Gate",
  building: "Building footprint", works: "Fieldworks"};
const label = (status: string): string => LABELS[status] ?? status;

const pt = (p: readonly number[]): string => p.join(",");
const add = (a: Point, b: Point, k = 1): Point => [a[0] + b[0] * k, a[1] + b[1] * k];
const near = (a: Point, b: Point): boolean => Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-3;
const same = (a: Hex, b: Hex): boolean => String(a) === String(b);
function unit(a: Point, b: Point): Point {
  const d = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
  return [(b[0] - a[0]) / d, (b[1] - a[1]) / d];
}

/** Geometry of one map: hex centres, vertices and the spacing between neighbouring centres. */
class Grid {
  readonly r: number;
  readonly spacing: number;
  readonly center: Center;
  constructor(radius: number) {
    this.r = radius;
    this.spacing = Math.sqrt(3) * radius;  // px between neighbouring hex centres (one metres_per_hex)
    this.center = (pos) => hexCenter(pos, radius);
  }
  vertex(c: Point, degrees: number): Point {
    return [c[0] + this.r * Math.cos(degrees * Math.PI / 180), c[1] + this.r * Math.sin(degrees * Math.PI / 180)];
  }
  ring(c: Point): string {
    return "M" + [0, 1, 2, 3, 4, 5].map((i) => pt(this.vertex(c, 60 * i - 30))).join("L") + "Z";
  }
}

// bt-T16 (docs/research/80): a label keeps its text clear of every other label and of the counters.
export interface Rect { x0: number; y0: number; x1: number; y1: number }
export interface LabelPlace { x: number; y: number; anchor: "start" | "middle" | "end" }
/** A label to place: `candidates` in preference order (the first is where it has always sat). */
export interface LabelSpec { key: string; priority: number; text: string; candidates: LabelPlace[] }
const GLYPH = 6.4, CAPITAL = 8.2, PAD = 2;  // px a character at 11 px, deliberately wide; padding for the 3 px halo
const PRIORITY: Record<MarkKind, number> = {bridge: 0, gate: 1, building: 2, works: 3, road: 4, wall: 5};

/** The box a label's text occupies at `place`, with a safety margin; `size` is the font size in px and
 * `spacing` the letter spacing (bt-T23: the objective's title is larger than a feature label). */
export function labelBox(text: string, place: LabelPlace, size = 11, spacing = 0): Rect {
  const k = size / 11;
  const width = [...text].reduce((n, ch) => n + ((ch >= "A" && ch <= "Z") || ch === "%" ? CAPITAL : GLYPH) * k + spacing, 0);
  const x0 = place.anchor === "middle" ? place.x - width / 2 : place.anchor === "end" ? place.x - width : place.x;
  return {x0: x0 - PAD, y0: place.y - 12 * k, x1: x0 + width + PAD, y1: place.y + 4 * k};
}
const meets = (a: Rect, b: Rect): boolean => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
// bt-T23 (docs/research/80 §7): a label box wholly inside the map frame, so no edge cuts it.
const inside = (box: Rect, frame: Rect): boolean => box.x0 >= frame.x0 && box.y0 >= frame.y0 && box.x1 <= frame.x1 && box.y1 <= frame.y1;

/** Places around a symbol of half-extents (`hw`, `hh`) at (`cx`, `cy`): below, above, right, left,
 * then the same shifted up and down in 14 px steps. */
export function around(cx: number, cy: number, hw: number, hh: number): LabelPlace[] {
  const out: LabelPlace[] = [{x: cx, y: cy + hh + 13, anchor: "middle"}, {x: cx, y: cy - hh - 6, anchor: "middle"},
    {x: cx + hw + 8, y: cy + 4, anchor: "start"}, {x: cx - hw - 8, y: cy + 4, anchor: "end"}];
  for (const k of [1, 2, 3]) {
    const d = 14 * k;
    out.push({x: cx, y: cy + hh + 13 + d, anchor: "middle"}, {x: cx, y: cy - hh - 6 - d, anchor: "middle"},
      {x: cx + hw + 8, y: cy + 4 + d, anchor: "start"}, {x: cx + hw + 8, y: cy + 4 - d, anchor: "start"},
      {x: cx - hw - 8, y: cy + 4 + d, anchor: "end"}, {x: cx - hw - 8, y: cy + 4 - d, anchor: "end"});
  }
  return out;
}

/** Why: labels sat wherever each mark's drawing put them, so they overlapped each other and the counters
 * (docs/research/75 §8). What: the place of each label, or null where none fits. Labels go in order of
 * `priority` (lower first), then `key`; each takes its first candidate whose box meets no obstacle and no
 * label placed before it and, given a `frame`, lies inside it (bt-T23). A label with no such candidate is
 * hidden; its mark keeps its tooltip and legend line.
 * Test: `label placement is deterministic, takes the first free place and hides a label with none`,
 * `a place outside the map frame is not taken, and a label with no place inside it is hidden`. */
export function placeLabels(specs: readonly LabelSpec[], obstacles: readonly Rect[] = [], frame?: Rect | null): Map<string, LabelPlace | null> {
  const taken: Rect[] = [...obstacles], out = new Map<string, LabelPlace | null>();
  const order = [...specs].sort((a, b) => a.priority - b.priority || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
  for (const spec of order) {
    const place = spec.candidates.find((c) => {
      const box = labelBox(spec.text, c);
      return (!frame || inside(box, frame)) && !taken.some((t) => meets(t, box));
    });
    if (place) taken.push(labelBox(spec.text, place));
    out.set(spec.key, place ?? null);
  }
  return out;
}

/** One line of the objective's title: its text, baseline `y`, font `size` and letter `spacing` in px. */
export interface TitleLine { text: string; y: number; size: number; spacing?: number }
/** Why: the objective's title is centred over its mark, so an objective at the map's edge had its title cut
 * (docs/research/81 §11: Hill 223's shack is in column 0). What: the x and anchor shared by the title's
 * lines: centred on `x` (where it has always sat), else starting at `x - hw`, else ending at `x + hw`; the
 * first place where every line's box lies inside `frame`. Centred when none does: the title is never hidden.
 * Test: `the objective's title stays centred where it fits and moves inside the frame at an edge`. */
export function titlePlace(lines: readonly TitleLine[], x: number, hw: number, frame: Rect): {x: number; anchor: LabelPlace["anchor"]} {
  const places: {x: number; anchor: LabelPlace["anchor"]}[] = [{x, anchor: "middle"}, {x: x - hw, anchor: "start"}, {x: x + hw, anchor: "end"}];
  return places.find((p) => lines.every((l) => inside(labelBox(l.text, {...p, y: l.y}, l.size, l.spacing), frame))) ?? places[0]!;
}
const tidy = (v: number): number => Math.round(v * 100) / 100;
// The label's <text>; `dx`, `dy` shift absolute coordinates into a translated group. Nothing when hidden.
function labelText(place: LabelPlace | null, text: string, dx = 0, dy = 0): string {
  if (!place) return "";
  const anchor = place.anchor === "start" ? "" : ` text-anchor="${place.anchor}"`;
  return `<text x="${tidy(place.x - dx)}" y="${tidy(place.y - dy)}"${anchor} class="feature-label">${esc(text)}</text>`;
}
const hiddenIf = (place: LabelPlace | null): string => (place ? "" : " data-label=\"hidden\"");

function title(name: string, info: Info, extra = ""): string {
  return `<title>${esc(name)}${extra ? " · " + esc(extra) : ""} — ${label(info.status)}: ${esc(info.source)}</title>`;
}
function open(kind: string, key: string, info: Info, extra = ""): string {
  return `<g class="feature-mark feature-${kind}" data-feature="${esc(key)}" data-status="${esc(info.status)}"${extra}>`;
}

// The places a road's label may take: along its segments, longest first, the spots whose text box keeps
// 30 px from every other mark's centre (`avoid`) before the others.
function roadPlaces(f: RoadFeature, g: Grid, avoid: Point[]): LabelPlace[] {
  const legs = f.points.slice(1).map((p, i): [Point, Point] => [g.center(f.points[i]!), g.center(p)]);
  const length = ([a, b]: [Point, Point]): number => Math.hypot(b[0] - a[0], b[1] - a[1]);
  const along = (ts: number[]): Point[] => [...legs].sort((l, m) => length(m) - length(l))
    .flatMap(([a, b]) => ts.map((t): Point => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]));
  const spots = along([.5, .35, .65, .25, .75]);
  const clear = ([sx, sy]: Point): boolean => avoid.every(([qx, qy]) => {
    const dx = Math.max(sx + 12 - qx, 0, qx - (sx + 12 + 6 * f.name.length)), dy = Math.max(sy - 25 - qy, 0, qy - (sy - 10));
    return Math.hypot(dx, dy) > 30;
  });
  // Above the line (the first spot that is clear of the other marks), then below it, then on it; then the same at more spots.
  const above = ([x, y]: Point): LabelPlace => ({x: x + 12, y: y - 14, anchor: "start"});
  const below = ([x, y]: Point): LabelPlace => ({x: x + 12, y: y + 22, anchor: "start"});
  const on = ([x, y]: Point): LabelPlace => ({x, y: y + 4, anchor: "middle"});
  const more = along([.1, .15, .2, .3, .4, .45, .55, .6, .7, .8, .85, .9]);
  // bt-T23: last, the text ending left of each spot, above then below, for a road that runs to the right edge.
  const aboveLeft = ([x, y]: Point): LabelPlace => ({x: x - 12, y: y - 14, anchor: "end"});
  const belowLeft = ([x, y]: Point): LabelPlace => ({x: x - 12, y: y + 22, anchor: "end"});
  return [...spots.filter(clear).map(above), ...spots.filter((s) => !clear(s)).map(above), ...spots.map(below), ...spots.map(on),
    ...more.flatMap((s) => [above(s), below(s), on(s)]), ...[...spots, ...more].flatMap((s) => [aboveLeft(s), belowLeft(s)])];
}

// One continuous cased line through the authored points, its label at `place`.
function road(f: RoadFeature, info: Info, g: Grid, place: LabelPlace | null): string {
  const d = f.points.map((p, i) => (i ? "L" : "M") + pt(g.center(p))).join(" ");
  return open("road", f.id, info, hiddenIf(place)) + title(f.name, info)
    + `<path class="road-casing" d="${d}" fill="none" stroke="${ROAD.casing}" stroke-width="${ROAD.casingWidth}" stroke-linejoin="round"/>`
    + `<path class="road-fill" d="${d}" fill="none" stroke="${ROAD.fill}" stroke-width="${ROAD.fillWidth}" stroke-linejoin="round"/>`
    + labelText(place, f.name) + "</g>";
}

// Roads stop at each bank; a span drawn like the road runs from each road end beside the bridge
// through its centre, under a deck with parapets. A destroyed bridge is drawn broken, with no span.
function bridge(pos: Hex, feature: BridgeFeature | undefined, info: Info, roads: RoadFeature[], g: Grid, place: LabelPlace | null): string {
  const c = g.center(pos);
  const ends = roads.flatMap((r) => [r.hexes[0]!, r.hexes.at(-1)!])
    .filter((h) => Math.abs(Math.hypot(g.center(h)[0] - c[0], g.center(h)[1] - c[1]) - g.spacing) < 1e-6)
    .map(g.center);
  const a = ends[0] ?? add(c, [-g.spacing, 0]);
  const b = ends.slice(1).sort((p, q) => Math.hypot(q[0] - a[0], q[1] - a[1]) - Math.hypot(p[0] - a[0], p[1] - a[1]))[0]
    ?? add(c, unit(a, c), g.spacing);
  const state = feature ? feature.state : "intact";
  const name = feature ? feature.name : info.name || "Bridge";
  const u = unit(a, b), n: Point = [-u[1], u[0]], half = g.r * .9, side = 7;
  const deck = [-1, 1].map((s) => {
    const from = add(add(c, u, -half), n, s * side), to = add(add(c, u, half), n, s * side);
    return `M${pt(add(add(from, u, -5), n, s * 5))}L${pt(from)}L${pt(to)}L${pt(add(add(to, u, 5), n, s * 5))}`;
  }).join("");
  let svg = open("bridge", feature ? feature.id : `crossing:${pos}`, info, ` data-state="${esc(state)}"${hiddenIf(place)}`)
    + title(name, info, state === "charges" ? "wired with charges, as known" : state);
  if (state === "destroyed") {
    const gap = [add(c, u, -6), add(c, u, 6)] as const;
    svg += `<path class="bridge-deck" d="${deck}" fill="none" stroke="#3d3a33" stroke-width="2.5" stroke-dasharray="${half - 6} 12" stroke-linecap="round"/>`
      + `<path class="bridge-broken" d="M${pt(add(gap[0], n, -9))}L${pt(add(gap[0], n, 9))}M${pt(add(gap[1], n, -9))}L${pt(add(gap[1], n, 9))}" stroke="#9b2d20" stroke-width="3"/>`;
  } else {
    const span = `M${pt(a)}L${pt(c)}L${pt(b)}`;
    svg += `<path class="road-span-casing" d="${span}" fill="none" stroke="${ROAD.casing}" stroke-width="${ROAD.casingWidth}" stroke-linejoin="round"/>`
      + `<path class="road-span-fill" d="${span}" fill="none" stroke="${ROAD.fill}" stroke-width="${ROAD.fillWidth}" stroke-linejoin="round"/>`
      + `<path class="bridge-deck" d="${deck}" fill="none" stroke="#3d3a33" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;
    if (state === "charges") svg += `<circle class="bridge-charges" cx="${c[0]}" cy="${c[1]}" r="3.5" fill="#9b2d20"/>`;
  }
  return svg + labelText(place, bridgeText(feature, info)) + "</g>";
}
const bridgeText = (feature: BridgeFeature | undefined, info: Info): string => {
  const name = feature ? feature.name : info.name || "Bridge", state = feature ? feature.state : "intact";
  return state === "intact" ? name : `${name} · ${state === "charges" ? "charges" : state}`;
};
// Below the bridge, where it has always sat; then round it.
const bridgePlaces = (pos: Hex, g: Grid): LabelPlace[] => {
  const [x, y] = g.center(pos);
  return [{x, y: y + g.r + 14, anchor: "middle"}, ...around(x, y, g.r + 4, g.r)];
};

interface Edge { inside: Hex; out: Point; a: Point; b: Point }
// The outward edges of a compound: each neighbour direction whose centre is not a compound hex.
function perimeter(compound: Hex[], g: Grid): Edge[] {
  const centres = compound.map(g.center), edges: Edge[] = [];
  compound.forEach((p, i) => {
    for (let k = 0; k < 6; k++) {
      const angle = 60 * k, out = add(centres[i]!, [Math.cos(angle * Math.PI / 180), Math.sin(angle * Math.PI / 180)], g.spacing);
      if (!centres.some((q) => near(q, out))) edges.push({inside: p, out, a: g.vertex(centres[i]!, angle - 30), b: g.vertex(centres[i]!, angle + 30)});
    }
  });
  return edges;
}
const isGate = (e: Edge, o: Opening, g: Grid): boolean => same(e.inside, o.inside) && near(e.out, g.center(o.outside));

type Compound = BuildingFeature & {compound: Hex[]; openings: Opening[]};

// The yard over the compound hexes, and a wall on every outward edge except the gates.
function walls(f: Compound, info: Info, g: Grid): string {
  const edges = perimeter(f.compound, g).filter((e) => !f.openings.some((o) => isGate(e, o, g)));
  return open("compound", `${f.id}#walls`, info) + title(`${f.name}: walls`, info)
    + `<path class="compound-yard" d="${f.compound.map((p) => g.ring(g.center(p))).join("")}" fill="#e3d2b0" fill-opacity=".55"/>`
    + `<path class="compound-wall" d="${edges.map((e) => `M${pt(e.a)}L${pt(e.b)}`).join("")}" fill="none" stroke="#5a4632" stroke-width="4" stroke-linecap="round"/></g>`;
}

// The gate in the state the side knows: open (leaves swung out) or shut (a bar on the edge).
// The gate label sits just outside its edge, as it always has; then round that point.
function gatePlaces(f: Compound, o: Opening, g: Grid): LabelPlace[] {
  const e = perimeter(f.compound, g).find((x) => isGate(x, o, g));
  if (!e) return [];
  const at = add([(e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2], unit(g.center(o.inside), g.center(o.outside)), 18);
  return [{x: at[0] + 8, y: at[1], anchor: "start"}, ...around(at[0], at[1] - 4, 4, 6)];
}
function gate(f: Compound, o: Opening, info: Info, g: Grid, place: LabelPlace | null): string {
  const e = perimeter(f.compound, g).find((x) => isGate(x, o, g));
  if (!e) return "";  // an opening off the compound's outward edges has no edge to draw on
  const outward = unit(g.center(o.inside), g.center(o.outside)), along = unit(e.a, e.b);
  let svg = open("gate", `${f.id}#${o.id}`, info, ` data-state="${esc(o.state)}"${hiddenIf(place)}`) + title(o.name, info, o.state);
  const edge = ` data-edge="${pt(e.a)} ${pt(e.b)}"`;
  if (PASSABLE.includes(o.state)) {
    const leaf = (post: Point, dir: number): string => `M${pt(post)}L${pt(add(add(post, outward, 9), along, dir * 4))}`;
    svg += `<path class="gate-open" d="${leaf(e.a, 1)}${leaf(e.b, -1)}"${edge} fill="none" stroke="#7a2e1f" stroke-width="3" stroke-linecap="round"/>`;
  } else {
    svg += `<path class="gate-shut" d="M${pt(e.a)}L${pt(e.b)}"${edge} stroke="#7a2e1f" stroke-width="7"/>`;
    if (o.state === "barred") svg += `<path class="gate-bar" d="M${pt(add(add(e.a, along, 5), outward, 4))}L${pt(add(add(e.b, along, -5), outward, 4))}" stroke="#f1e6c8" stroke-width="2"/>`;
  }
  for (const post of [e.a, e.b]) svg += `<rect class="gate-post" x="${post[0] - 3}" y="${post[1] - 3}" width="6" height="6" fill="#3b2a1e"/>`;
  return svg + labelText(place, `${o.name} · ${o.state}`) + "</g>";
}

/** Why: a building must read at its true size, not as a fixed symbol (docs/research/72 §2).
 * What: the footprint in px for `metres` [width, depth]: metres x (hex-centre spacing /
 * `metresPerHex`), each side at least 6 px (`enlarged`); scaled down to stay inside its hex (`capped`).
 * Test: `footprints scale with metres_per_hex, and every mark's tooltip names its status and basis`. */
export function footprint(metres: readonly number[], metresPerHex: number, radius: number): {w: number; h: number; capped: boolean; enlarged: boolean} {
  const spacing = Math.sqrt(3) * radius, scale = spacing / metresPerHex;
  let [w, h] = metres.map((m) => Math.max(MIN_SIDE, m * scale)) as [number, number];
  const fit = Math.min(1, spacing / w, radius / (h / 2 + w / (2 * Math.sqrt(3))));  // inside a pointy-top hex
  const capped = fit < 1;
  if (capped) [w, h] = [w * fit * .98, h * fit * .98];
  return {w, h, capped, enlarged: metres.some((m) => m * scale < MIN_SIDE)};
}

// Above the footprint, where the label has always sat; then round it.
function buildingPlaces(f: BuildingFeature, info: Info, g: Grid, metresPerHex: number): LabelPlace[] {
  const [x, y] = g.center(f.pos), {w, h} = footprint(info.footprint_m || [30, 20], metresPerHex, g.r);
  return [{x, y: y - h / 2 - 6, anchor: "middle"}, ...around(x, y, w / 2, h / 2)];
}
function building(f: BuildingFeature, info: Info, g: Grid, metresPerHex: number, place: LabelPlace | null): string {
  const [x, y] = g.center(f.pos), metres = info.footprint_m || [30, 20];
  const {w, h, capped, enlarged} = footprint(metres, metresPerHex, g.r);
  const note = `footprint ${metres[0]} x ${metres[1]} m at ${metresPerHex} m a hex${capped ? ", reduced to fit its hex" : ""}${enlarged ? ", enlarged to stay legible" : ""}`;
  const ridge = w >= h ? `M${x - w / 2 + 3},${y}H${x + w / 2 - 3}` : `M${x},${y - h / 2 + 3}V${y + h / 2 - 3}`;
  return open("building", f.id, info, hiddenIf(place)) + title(f.name, info, note)
    + `<rect class="footprint-shadow" x="${x - w / 2 + 2}" y="${y - h / 2 + 2}" width="${w}" height="${h}" fill="#3f2f22" fill-opacity=".3"/>`
    + `<rect class="footprint" x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" fill="#a8876a" stroke="#3f2f22" stroke-width="1.5"/>`
    + `<path class="footprint-ridge" d="${ridge}" stroke="#6e5541" stroke-width="1.2"/>`
    + labelText(place, f.name) + "</g>";
}

const worksText = (f: FortificationFeature): string => (f.progress === 100 ? "FIELDWORKS" : String(f.progress) + "% WORKS");
// Right of the works symbol (drawn 24 px below its hex centre), where the label has always sat; then round it.
function worksPlaces(f: FortificationFeature, g: Grid): LabelPlace[] {
  const [x, y] = g.center(f.pos);
  return [{x: x + 30, y: y + 29, anchor: "start"}, ...around(x, y + 24, 25, 8)];
}
function works(f: FortificationFeature, info: Info, g: Grid, place: LabelPlace | null): string {
  const [x, y] = g.center(f.pos), shape = "M-22,8V0L-11,-6L0,0L11,-6L22,0V8";
  const done = f.progress === 100;
  return open("works", f.id, info, ` transform="translate(${x},${y + 24})" opacity="${done ? 1 : .65}"${hiddenIf(place)}`)
    + title(f.name, info, done ? "complete" : `${f.progress}% · cover ${f.cover}`)
    + `<path d="${shape}" fill="none" stroke="#70563a" stroke-width="6"/><path d="${shape}" fill="none" stroke="#cab18b" stroke-width="2"/>`
    + labelText(place, worksText(f), x, y + 24) + "</g>";
}

const statusOf = (key: string, feature: MapFeature | undefined, sources: StatusTable): Info =>
  sources[key] ?? (feature && feature.briefed === false ? REPORTED : UNLISTED);
const isCompound = (f: MapFeature): f is Compound => f.kind === "building" && Boolean(f.openings?.length && f.compound);

/** Why: the layer, the legend and the hex tooltips must list the same marks.
 * What: every mark of `features` (the commander view) and the briefing bridge cells, in draw
 * order: roads, bridges, compound walls, gates, buildings, works; each with its status.
 * Test: `every catalog entry's feature layer, legend and hex notes match the POC desk's`. */
export function featureMarks(features: readonly MapFeature[], options: FeatureOptions): Mark[] {
  const g = new Grid(options.radius), sources = options.sources;
  const roads = features.filter((f): f is RoadFeature => f.kind === "road");
  const bridges = new Map(features.filter((f): f is BridgeFeature => f.kind === "bridge").map((f) => [String(f.pos), f]));
  const crossings: Hex[] = options.cells.filter((c) => c["crossing"] === "bridge").map((c) => c.pos);
  for (const f of bridges.values()) if (!crossings.some((p) => same(p, f.pos))) crossings.push(f.pos);
  const list: Mark[] = [];
  const push = (key: string, kind: MarkKind, name: string, hexes: Hex[], feature: MapFeature | undefined,
    draw: (info: Info, place: LabelPlace | null) => string, label?: {text: string; places: LabelPlace[]}): void => {
    const info = statusOf(key, feature, sources);
    list.push({key, kind, name, hexes, info, draw: (place = null) => draw(info, place),
      ...(label ? {label: {key, priority: PRIORITY[kind], text: label.text, candidates: label.places}} : {})});
  };
  const placed = [...crossings, ...features.filter((f) => f.kind === "building" || f.kind === "fortification")
    .map((f) => (f as BuildingFeature | FortificationFeature).pos)].map(g.center);
  for (const f of roads) push(f.id, "road", f.name, f.hexes, f, (i, p) => road(f, i, g, p), {text: f.name, places: roadPlaces(f, g, placed)});
  for (const pos of crossings) {
    const f = bridges.get(String(pos)), key = f ? f.id : `crossing:${pos}`;
    push(key, "bridge", f ? f.name : sources[key]?.name || "Bridge", [pos], f, (i, p) => bridge(pos, f, i, roads, g, p),
      {text: bridgeText(f, statusOf(key, f, sources)), places: bridgePlaces(pos, g)});
  }
  const compounds = features.filter(isCompound);
  for (const f of compounds) push(`${f.id}#walls`, "wall", `${f.name}: walls`, f.compound, f, (i) => walls(f, i, g));
  for (const f of compounds) for (const o of f.openings) {
    push(`${f.id}#${o.id}`, "gate", `${o.name} · ${o.state}`, [o.inside, o.outside], f, (i, p) => gate(f, o, i, g, p),
      {text: `${o.name} · ${o.state}`, places: gatePlaces(f, o, g)});
  }
  for (const f of features) if (f.kind === "building") {
    push(f.id, "building", f.name, [f.pos], f, (i, p) => building(f, i, g, options.metresPerHex, p),
      {text: f.name, places: buildingPlaces(f, statusOf(f.id, f, sources), g, options.metresPerHex)});
  }
  for (const f of features) if (f.kind === "fortification") {
    push(f.id, "works", f.name + (f.progress === 100 ? "" : ` ${f.progress}% · cover ${f.cover}`), [f.pos], f, (i, p) => works(f, i, g, p),
      {text: worksText(f), places: worksPlaces(f, g)});
  }
  return list;
}

/** What: one SVG group of every mark, each with a status tooltip; independent of the grid toggle.
 * Test: `every catalog entry's feature layer, legend and hex notes match the POC desk's`. */
export function featureLayer(features: readonly MapFeature[], options: FeatureOptions): string {
  const marks = featureMarks(features, options);
  const placed = placeLabels(marks.flatMap((m) => (m.label ? [m.label] : [])), options.obstacles, options.frame);
  return "<g class=\"battle-features\" pointer-events=\"none\">" + marks.map((m) => m.draw(placed.get(m.key) ?? null)).join("") + "</g>";
}

/** Tooltip lines for hex `pos`: each mark over it, with its status and basis. */
export function featureNotes(features: readonly MapFeature[], pos: Hex, options: FeatureOptions): string[] {
  return featureMarks(features, options).filter((m) => m.hexes.some((p) => same(p, pos)))
    .map((m) => `${m.name} (${label(m.info.status)}: ${m.info.source})`);
}

/** Why: each mark's status must be readable without hovering (docs/research/72 §3).
 * What: legend HTML: a key for the kinds drawn and the statuses used, then one line per mark
 * with its status and basis; empty when nothing is drawn.
 * Test: `every catalog entry's feature layer, legend and hex notes match the POC desk's`. */
export function featureLegend(features: readonly MapFeature[], options: FeatureOptions): string {
  const list = featureMarks(features, options);
  if (!list.length) return "";
  const used = [...new Set(list.map((m) => m.kind))], statuses = [...new Set(list.map((m) => m.info.status))];
  return `<div class="legend-key">${used.map((k) => `<span><i class="legend-symbol legend-${k}"></i>${KINDS[k]}</span>`).join("")}</div>`
    + `<div class="legend-statuses">${statuses.map((s) => `<span class="legend-status legend-status-${esc(s)}">${LABELS[s] || esc(s)}</span>`).join("")}</div>`
    + `<ul class="legend-items">${list.map((m) => `<li data-feature="${esc(m.key)}"><i class="legend-symbol legend-${m.kind}"></i><b>${esc(m.name)}</b>`
      + ` <span class="legend-status legend-status-${esc(m.info.status)}">${LABELS[m.info.status] || esc(m.info.status)}</span> ${esc(m.info.source)}</li>`).join("")}</ul>`;
}

