// Zoom and pan for the desk's SVG map (bt-T26, docs/research/81 §13): the fit view and a 2x view,
// centred by the POC desk's focus rule (apps/poc/static/map-view.js focusCentre, app.js mapFocus).
// The desk shows a window of the map through the SVG viewBox; labels are placed inside that window
// (docs/research/80 §7). Pure: no DOM. Clicks are hit-tested by the browser; `toScreen`, `toScene`
// and `hexAt` state the same transform so tests and the smoke run can check where a click lands.
import type {CommanderView, MapCell, MapDocument} from "@battle/contracts";
import {labelBox, type Rect} from "./features.ts";
import {hexCenter} from "./geometry.ts";
import {objectiveLabel} from "./render.ts";

type Point = [number, number];
type Hex = readonly [number, number];
type Size = Pick<MapDocument, "width" | "height">;
type Edges = [number, number, number, number];  // x0, y0, x1, y1

/** The desk's camera: the fit view (the whole map), or 2x about `centre` (scene px). */
export type Zoom = {readonly scale: 1} | {readonly scale: 2; readonly centre: Point};
export const FIT: Zoom = {scale: 1};
/** What a zoom-in keeps in frame: `core`, the objective hex and its label; `all`, that and every mark with a hex. */
export interface Focus { core: Edges; all: Edges }
/** The SVG's content box in CSS px (inside its border). */
export interface ScreenBox { left: number; top: number; width: number; height: number }

const clamp = (v: number, lo: number, hi: number): number => Math.min(Math.max(v, lo), hi);
const tidy = (v: number): number => Math.round(v * 100) / 100;
const grow = (box: Edges, b: Rect): Edges =>
  [Math.min(box[0], b.x0), Math.min(box[1], b.y0), Math.max(box[2], b.x1), Math.max(box[3], b.y1)];

/** The part of the map the frame shows, in scene px: the whole map at fit; at 2x a window of half its width
 * and height about the centre, kept on the map. Test: `the fit view is the whole map, …`. */
export function zoomWindow(zoom: Zoom, map: Size): Rect {
  if (zoom.scale === 1) return {x0: 0, y0: 0, x1: map.width, y1: map.height};
  const hw = map.width / 4, hh = map.height / 4;
  const x0 = tidy(clamp(zoom.centre[0], hw, map.width - hw) - hw), y0 = tidy(clamp(zoom.centre[1], hh, map.height - hh) - hh);
  return {x0, y0, x1: x0 + 2 * hw, y1: y0 + 2 * hh};
}

/** The SVG viewBox for a window; at fit `0 0 width height`, as the desk set it before zoom. */
export const viewBox = (w: Rect): string => [w.x0, w.y0, w.x1 - w.x0, w.y1 - w.y0].map(tidy).join(" ");

/** The POC desk's mapFocus for this desk's drawing: the objective hex with its label as drawn at fit, and
 * every map feature with a hex (`pos`). */
export function mapFocus(view: CommanderView, map: MapDocument): Focus {
  const r = map.radius, [ox, oy] = hexCenter(view.objective, r);
  const title = objectiveLabel(view, map, zoomWindow(FIT, map));
  const core = grow([ox - r, oy - r, ox + r, oy + r], labelBox(title.text, title));
  let all = core;
  for (const f of view.map_features) {
    if (!("pos" in f)) continue;
    const [x, y] = hexCenter(f.pos, r);
    all = grow(all, {x0: x - r, y0: y - r, x1: x + r, y1: y + r});
  }
  return {core, all};
}

/** Why: a zoom about the map's middle left Hill 223's objective off screen (docs/research/81 §11).
 * What: the POC desk's rule, per axis: the least move of `centre` that keeps `all` in a frame of
 * half-size `half`; if `all` is larger, the least move that keeps `core` in; if that is larger too, the
 * middle of `core`. Then the frame is kept on the map (`size`). No focus: `centre` unchanged.
 * Test: `zoom in shows half the map each way, keeping the objective and every mark in frame, else the objective only`. */
export function focusCentre(centre: Point, half: Point, focus: Focus | null, size: Point): Point {
  if (!focus) return centre;
  const fit = (c: number, h: number, lo: number, hi: number): number | null => (hi - lo <= 2 * h ? Math.min(Math.max(c, hi - h), lo + h) : null);
  const axis = (i: 0 | 1): number => {
    const c = centre[i], h = half[i], {core, all} = focus;
    const v = fit(c, h, all[i], all[i + 2]!) ?? fit(c, h, core[i], core[i + 2]!) ?? (core[i] + core[i + 2]!) / 2;
    return 2 * h >= size[i] ? size[i] / 2 : clamp(v, h, size[i] - h);
  };
  return [axis(0), axis(1)];
}

/** Zoom in from fit to 2x about the focus; at 2x already, unchanged. */
export function zoomIn(zoom: Zoom, map: Size, focus: Focus | null): Zoom {
  if (zoom.scale === 2) return zoom;
  const centre = focusCentre([map.width / 2, map.height / 2], [map.width / 4, map.height / 4], focus, [map.width, map.height]);
  return {scale: 2, centre};
}

/** Why: at 2x the player must reach the rest of the map. What: moves the 2x window `dx`, `dy` steps of half
 * its size, kept on the map; the fit view does not pan. Test: `pan moves the 2x window by half its size …`. */
export function pan(zoom: Zoom, map: Size, dx: number, dy: number): Zoom {
  if (zoom.scale === 1) return zoom;
  const w = zoomWindow(zoom, map);
  const moved = zoomWindow({scale: 2, centre: [(w.x0 + w.x1) / 2 + dx * map.width / 4, (w.y0 + w.y1) / 2 + dy * map.height / 4]}, map);
  return moved.x0 === w.x0 && moved.y0 === w.y0 ? zoom : {scale: 2, centre: [(moved.x0 + moved.x1) / 2, (moved.y0 + moved.y1) / 2]};
}

/** A scene point's place on screen when the frame `box` shows window `w`. */
export const toScreen = (w: Rect, box: ScreenBox, [x, y]: readonly [number, number]): Point =>
  [box.left + (x - w.x0) * box.width / (w.x1 - w.x0), box.top + (y - w.y0) * box.height / (w.y1 - w.y0)];
/** The scene point under screen point (`sx`, `sy`); the inverse of `toScreen`. */
export const toScene = (w: Rect, box: ScreenBox, [sx, sy]: readonly [number, number]): Point =>
  [w.x0 + (sx - box.left) * (w.x1 - w.x0) / box.width, w.y0 + (sy - box.top) * (w.y1 - w.y0) / box.height];

/** The map cell whose hex holds scene point `p` (the nearest centre, within a radius); null off the map.
 * Test: `a click at 2x maps to the hex under the pointer`. */
export function hexAt(cells: readonly MapCell[], radius: number, p: readonly [number, number]): Hex | null {
  let best: Hex | null = null, near = radius;
  for (const cell of cells) {
    const [x, y] = hexCenter(cell.pos, radius), d = Math.hypot(x - p[0], y - p[1]);
    if (d <= near) { near = d; best = cell.pos; }
  }
  return best;
}
