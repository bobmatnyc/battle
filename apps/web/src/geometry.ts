// Pointy-top hexes in offset rows, odd rows shifted right: the POC's layout
// (apps/poc/static/app.js `center`), in the map document's drawing units.
type Hex = readonly [number, number];

const MARGIN_X = 24;
const MARGIN_Y = 26;

/** Drawing-unit centre of hex `[column, row]` for hexes of `radius`. */
export function hexCenter(pos: Hex, radius: number): [number, number] {
  const [col, row] = pos;
  return [(col + 0.5 * (row & 1)) * Math.sqrt(3) * radius + MARGIN_X, row * 1.5 * radius + MARGIN_Y];
}

/** SVG `points` for the hex outline. */
export function hexPoints(pos: Hex, radius: number): string {
  const [x, y] = hexCenter(pos, radius);
  return Array.from({length: 6}, (_, i) => {
    const angle = ((60 * i - 30) * Math.PI) / 180;
    return `${(x + radius * Math.cos(angle)).toFixed(1)},${(y + radius * Math.sin(angle)).toFixed(1)}`;
  }).join(" ");
}
