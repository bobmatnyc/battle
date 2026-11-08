/* Roads, bridges, walled compounds and gates, buildings and fieldworks drawn from the
 * commander's map_features (the observer-visible features the engine routes, covers and
 * sights with) and the briefing cells of /api/map. A separate module so
 * scripts/check_map_features.mjs and the screenshot harness render the same SVG.
 * Design: docs/research/24, 64, 72. */
const BattleFeatures = (() => {
  const R = 25.5;
  const SPACING = Math.sqrt(3) * R;  // px between neighbouring hex centres (one metres_per_hex)
  const MIN_SIDE = 6;  // px: the smallest legible footprint side
  const ROAD = {casing: '#ae997b', fill: '#fff4d5', casingWidth: 10, fillWidth: 6};
  const PASSABLE = ['open', 'closing', 'forced'];  // battle/gates.py PASSABLE
  const LABELS = {sourced: 'Sourced', reconstructed: 'Reconstructed', illustrative: 'Illustrative',
                  reported: 'Reported in battle', unlisted: 'Status not recorded'};
  const REPORTED = {status: 'reported', source: 'Built during this battle; drawn as last reported to headquarters.'};
  const UNLISTED = {status: 'unlisted', source: 'No status is recorded for this mark in static/feature-sources.js.'};

  const pt = p => p.join(',');
  const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k];
  const near = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-3;
  const unit = (a, b) => {
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    return [(b[0] - a[0]) / d, (b[1] - a[1]) / d];
  };
  const vertex = (c, degrees) => [c[0] + R * Math.cos(degrees * Math.PI / 180), c[1] + R * Math.sin(degrees * Math.PI / 180)];
  const ring = c => 'M' + [0, 1, 2, 3, 4, 5].map(i => pt(vertex(c, 60 * i - 30))).join('L') + 'Z';

  // bt-T16 (docs/research/80): a label keeps its text clear of every other label and of the counters.
  // A place is {x, y, anchor}; a box {x0, y0, x1, y1}. Mirrors apps/web/src/features.ts, which test/features.test.ts holds byte-identical.
  const GLYPH = 6.4, CAPITAL = 8.2, PAD = 2;  // px a character at 11 px, deliberately wide; padding for the 3 px halo
  const PRIORITY = {bridge: 0, gate: 1, building: 2, works: 3, road: 4, wall: 5};

  /** The box a label's text occupies at `place`, with a safety margin; `size` is the font size in px and
   * `spacing` the letter spacing (bt-T23: the objective's title is larger than a feature label). */
  function labelBox(text, place, size = 11, spacing = 0) {
    const k = size / 11;
    const width = [...text].reduce((n, ch) => n + ((ch >= 'A' && ch <= 'Z') || ch === '%' ? CAPITAL : GLYPH) * k + spacing, 0);
    const x0 = place.anchor === 'middle' ? place.x - width / 2 : place.anchor === 'end' ? place.x - width : place.x;
    return {x0: x0 - PAD, y0: place.y - 12 * k, x1: x0 + width + PAD, y1: place.y + 4 * k};
  }
  const meets = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
  // bt-T23 (docs/research/80 §7): a label box wholly inside the map frame, so no edge cuts it.
  const inside = (box, frame) => box.x0 >= frame.x0 && box.y0 >= frame.y0 && box.x1 <= frame.x1 && box.y1 <= frame.y1;

  /** Places around a symbol of half-extents (`hw`, `hh`) at (`cx`, `cy`): below, above, right, left,
   * then the same shifted up and down in 14 px steps. */
  function around(cx, cy, hw, hh) {
    const out = [{x: cx, y: cy + hh + 13, anchor: 'middle'}, {x: cx, y: cy - hh - 6, anchor: 'middle'},
      {x: cx + hw + 8, y: cy + 4, anchor: 'start'}, {x: cx - hw - 8, y: cy + 4, anchor: 'end'}];
    for (const k of [1, 2, 3]) {
      const d = 14 * k;
      out.push({x: cx, y: cy + hh + 13 + d, anchor: 'middle'}, {x: cx, y: cy - hh - 6 - d, anchor: 'middle'},
        {x: cx + hw + 8, y: cy + 4 + d, anchor: 'start'}, {x: cx + hw + 8, y: cy + 4 - d, anchor: 'start'},
        {x: cx - hw - 8, y: cy + 4 + d, anchor: 'end'}, {x: cx - hw - 8, y: cy + 4 - d, anchor: 'end'});
    }
    return out;
  }

  /** Why: labels sat wherever each mark's drawing put them, so they overlapped each other and the counters
   * (docs/research/75 §8). What: a Map from label key to its place, or null where none fits. `specs` are
   * {key, priority, text, candidates}; they go in order of priority (lower first), then key; each takes its
   * first candidate whose box meets no obstacle and no label placed before it and, given a `frame`
   * {x0, y0, x1, y1}, lies inside it (bt-T23). A label with no such candidate is hidden; its mark keeps its
   * tooltip and legend line.
   * Test: scripts/check_map_features.mjs (label placement). */
  function placeLabels(specs, obstacles = [], frame = null) {
    const taken = [...obstacles], out = new Map();
    const order = [...specs].sort((a, b) => a.priority - b.priority || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
    for (const spec of order) {
      const place = spec.candidates.find(c => {
        const box = labelBox(spec.text, c);
        return (!frame || inside(box, frame)) && !taken.some(t => meets(t, box));
      });
      if (place) taken.push(labelBox(spec.text, place));
      out.set(spec.key, place || null);
    }
    return out;
  }

  /** Why: the objective's title is centred over its mark, so an objective at the map's edge had its title cut
   * (docs/research/81 §11: Hill 223's shack is in column 0). What: {x, anchor} shared by the title's `lines`
   * ({text, y, size, spacing}): centred on `x` (where it has always sat), else starting at `x - hw`, else
   * ending at `x + hw`; the first place where every line's box lies inside `frame`. Centred when none does:
   * the title is never hidden. Test: scripts/check_map_features.mjs (the objective's title). */
  function titlePlace(lines, x, hw, frame) {
    const places = [{x, anchor: 'middle'}, {x: x - hw, anchor: 'start'}, {x: x + hw, anchor: 'end'}];
    return places.find(p => lines.every(l => inside(labelBox(l.text, {...p, y: l.y}, l.size, l.spacing), frame))) || places[0];
  }
  const tidy = v => Math.round(v * 100) / 100;
  // The label's <text>; dx, dy shift absolute coordinates into a translated group. Nothing when hidden.
  function labelText(place, text, esc, dx = 0, dy = 0) {
    if (!place) return '';
    const anchor = place.anchor === 'start' ? '' : ` text-anchor="${place.anchor}"`;
    return `<text x="${tidy(place.x - dx)}" y="${tidy(place.y - dy)}"${anchor} class="feature-label">${esc(text)}</text>`;
  }
  const hiddenIf = place => place ? '' : ' data-label="hidden"';

  // The status of mark `key`: the scenario's sources entry, or "reported" for works dug in battle.
  function statusOf(key, feature, sources) {
    if (sources && sources[key]) return sources[key];
    return feature && feature.briefed === false ? REPORTED : UNLISTED;
  }
  function title(name, info, esc, extra = '') {
    return `<title>${esc(name)}${extra ? ' · ' + esc(extra) : ''} — ${LABELS[info.status] || info.status}: ${esc(info.source)}</title>`;
  }
  function open(kind, key, info, esc, extra = '') {
    return `<g class="feature-mark feature-${kind}" data-feature="${esc(key)}" data-status="${esc(info.status)}"${extra}>`;
  }

  // Why: a road must read as one continuous line. What: casing and fill through its authored
  // points; the engine's routed hexes are the rasterised line (features.setup).
  // The places a road's label may take: along its segments, longest first; the spots whose text box keeps
  // 30 px from every other mark's centre (`avoid`: bridges, buildings and works) come before the others.
  function roadPlaces(f, center, avoid = []) {
    const legs = f.points.slice(1).map((p, i) => [center(f.points[i]), center(p)]);
    const length = ([a, b]) => Math.hypot(b[0] - a[0], b[1] - a[1]);
    const along = ts => [...legs].sort((l, m) => length(m) - length(l))
      .flatMap(([a, b]) => ts.map(t => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]));
    const spots = along([.5, .35, .65, .25, .75]);
    // The text box (about 6 px a character at 11 px) must keep 30 px from each mark's centre.
    const clear = ([sx, sy]) => avoid.every(([qx, qy]) => {
      const dx = Math.max(sx + 12 - qx, 0, qx - (sx + 12 + 6 * f.name.length)), dy = Math.max(sy - 25 - qy, 0, qy - (sy - 10));
      return Math.hypot(dx, dy) > 30;
    });
    // Above the line (the first spot that is clear of the other marks), then below it, then on it; then the same at more spots.
    const above = ([x, y]) => ({x: x + 12, y: y - 14, anchor: 'start'});
    const below = ([x, y]) => ({x: x + 12, y: y + 22, anchor: 'start'});
    const on = ([x, y]) => ({x, y: y + 4, anchor: 'middle'});
    const more = along([.1, .15, .2, .3, .4, .45, .55, .6, .7, .8, .85, .9]);
    // bt-T23: last, the text ending left of each spot, above then below, for a road that runs to the right edge.
    const aboveLeft = ([x, y]) => ({x: x - 12, y: y - 14, anchor: 'end'});
    const belowLeft = ([x, y]) => ({x: x - 12, y: y + 22, anchor: 'end'});
    return [...spots.filter(clear).map(above), ...spots.filter(s => !clear(s)).map(above), ...spots.map(below), ...spots.map(on),
      ...more.flatMap(s => [above(s), below(s), on(s)]), ...[...spots, ...more].flatMap(s => [aboveLeft(s), belowLeft(s)])];
  }
  function road(f, info, center, esc, place) {
    const d = f.points.map((p, i) => (i ? 'L' : 'M') + pt(center(p))).join(' ');
    return open('road', f.id, info, esc, hiddenIf(place)) + title(f.name, info, esc)
      + `<path class="road-casing" d="${d}" fill="none" stroke="${ROAD.casing}" stroke-width="${ROAD.casingWidth}" stroke-linejoin="round"/>`
      + `<path class="road-fill" d="${d}" fill="none" stroke="${ROAD.fill}" stroke-width="${ROAD.fillWidth}" stroke-linejoin="round"/>`
      + labelText(place, f.name, esc) + '</g>';
  }

  // Why: roads stop at each bank (the bridge hex keeps its own cost), but the player must see the
  // road carried across. What: a span from each road end beside the bridge through its centre,
  // drawn like the road, under a deck with parapets; a destroyed bridge is drawn broken, no span.
  const bridgeText = (feature, info) => {
    const name = feature ? feature.name : info.name || 'Bridge', state = feature ? feature.state : 'intact';
    return state === 'intact' ? name : `${name} · ${state === 'charges' ? 'charges' : state}`;
  };
  // Below the bridge, where it has always sat; then round it.
  function bridgePlaces(pos, center) {
    const [x, y] = center(pos);
    return [{x, y: y + R + 14, anchor: 'middle'}, ...around(x, y, R + 4, R)];
  }
  function bridge(pos, feature, info, roads, center, esc, place) {
    const c = center(pos);
    const ends = roads.flatMap(r => [r.hexes[0], r.hexes.at(-1)])
      .filter(h => Math.abs(Math.hypot(center(h)[0] - c[0], center(h)[1] - c[1]) - SPACING) < 1e-6)
      .map(center);
    const a = ends[0] || add(c, [-SPACING, 0]);
    const b = ends.slice(1).sort((p, q) => Math.hypot(q[0] - a[0], q[1] - a[1]) - Math.hypot(p[0] - a[0], p[1] - a[1]))[0]
      || add(c, unit(a, c), SPACING);
    const state = feature ? feature.state : 'intact';
    const name = feature ? feature.name : info.name || 'Bridge';
    const u = unit(a, b), n = [-u[1], u[0]], half = R * .9, side = 7;
    const deck = [-1, 1].map(s => {
      const from = add(add(c, u, -half), n, s * side), to = add(add(c, u, half), n, s * side);
      // Parapet with splayed wing walls at both abutments.
      return `M${pt(add(add(from, u, -5), n, s * 5))}L${pt(from)}L${pt(to)}L${pt(add(add(to, u, 5), n, s * 5))}`;
    }).join('');
    let svg = open('bridge', feature ? feature.id : `crossing:${pos}`, info, esc, ` data-state="${esc(state)}"${hiddenIf(place)}`)
      + title(name, info, esc, state === 'charges' ? 'wired with charges, as known' : state);
    if (state === 'destroyed') {
      const gap = [add(c, u, -6), add(c, u, 6)];
      svg += `<path class="bridge-deck" d="${deck}" fill="none" stroke="#3d3a33" stroke-width="2.5" stroke-dasharray="${half - 6} 12" stroke-linecap="round"/>`
        + `<path class="bridge-broken" d="M${pt(add(gap[0], n, -9))}L${pt(add(gap[0], n, 9))}M${pt(add(gap[1], n, -9))}L${pt(add(gap[1], n, 9))}" stroke="#9b2d20" stroke-width="3"/>`;
    } else {
      const span = `M${pt(a)}L${pt(c)}L${pt(b)}`;
      svg += `<path class="road-span-casing" d="${span}" fill="none" stroke="${ROAD.casing}" stroke-width="${ROAD.casingWidth}" stroke-linejoin="round"/>`
        + `<path class="road-span-fill" d="${span}" fill="none" stroke="${ROAD.fill}" stroke-width="${ROAD.fillWidth}" stroke-linejoin="round"/>`
        + `<path class="bridge-deck" d="${deck}" fill="none" stroke="#3d3a33" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;
      if (state === 'charges') svg += `<circle class="bridge-charges" cx="${c[0]}" cy="${c[1]}" r="3.5" fill="#9b2d20"/>`;
    }
    return svg + labelText(place, bridgeText(feature, info), esc) + '</g>';
  }

  // The outward edges of a compound: for each compound hex, each neighbour direction whose
  // neighbour centre is not a compound hex. Geometry only, so it matches any grid offset.
  function perimeter(compound, center) {
    const centres = compound.map(center), edges = [];
    compound.forEach((p, i) => {
      for (let k = 0; k < 6; k++) {
        const angle = 60 * k, out = add(centres[i], [Math.cos(angle * Math.PI / 180), Math.sin(angle * Math.PI / 180)], SPACING);
        if (!centres.some(q => near(q, out))) edges.push({inside: p, out, a: vertex(centres[i], angle - 30), b: vertex(centres[i], angle + 30)});
      }
    });
    return edges;
  }
  const isGate = (e, o, center) => String(e.inside) === String(o.inside) && near(e.out, center(o.outside));

  // Why: Hougoumont turns on its walls and gate (docs/research/41, 42). What: the yard as the
  // compound hexes, and a wall on every outward edge except the gates, which `gate` draws.
  function compound(f, info, center, esc) {
    const edges = perimeter(f.compound, center).filter(e => !f.openings.some(o => isGate(e, o, center)));
    return open('compound', `${f.id}#walls`, info, esc) + title(`${f.name}: walls`, info, esc)
      + `<path class="compound-yard" d="${f.compound.map(p => ring(center(p))).join('')}" fill="#e3d2b0" fill-opacity=".55"/>`
      + `<path class="compound-wall" d="${edges.map(e => `M${pt(e.a)}L${pt(e.b)}`).join('')}" fill="none" stroke="#5a4632" stroke-width="4" stroke-linecap="round"/></g>`;
  }

  // The gate in the state the side knows: open (leaves swung out) or shut (a bar on the edge).
  // The gate label sits just outside its edge, as it always has; then round that point.
  function gatePlaces(f, o, center) {
    const e = perimeter(f.compound, center).find(x => isGate(x, o, center));
    if (!e) return [];
    const at = add([(e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2], unit(center(o.inside), center(o.outside)), 18);
    return [{x: at[0] + 8, y: at[1], anchor: 'start'}, ...around(at[0], at[1] - 4, 4, 6)];
  }
  function gate(f, o, info, center, esc, place) {
    const e = perimeter(f.compound, center).find(x => isGate(x, o, center));
    const outward = unit(center(o.inside), center(o.outside)), along = unit(e.a, e.b);
    const passable = PASSABLE.includes(o.state);
    let svg = open('gate', `${f.id}#${o.id}`, info, esc, ` data-state="${esc(o.state)}"${hiddenIf(place)}`) + title(o.name, info, esc, o.state);
    const edge = ` data-edge="${pt(e.a)} ${pt(e.b)}"`;
    if (passable) {
      const leaf = (post, dir) => `M${pt(post)}L${pt(add(add(post, outward, 9), along, dir * 4))}`;
      svg += `<path class="gate-open" d="${leaf(e.a, 1)}${leaf(e.b, -1)}"${edge} fill="none" stroke="#7a2e1f" stroke-width="3" stroke-linecap="round"/>`;
    } else {
      svg += `<path class="gate-shut" d="M${pt(e.a)}L${pt(e.b)}"${edge} stroke="#7a2e1f" stroke-width="7"/>`;
      if (o.state === 'barred') svg += `<path class="gate-bar" d="M${pt(add(add(e.a, along, 5), outward, 4))}L${pt(add(add(e.b, along, -5), outward, 4))}" stroke="#f1e6c8" stroke-width="2"/>`;
    }
    for (const post of [e.a, e.b]) svg += `<rect class="gate-post" x="${post[0] - 3}" y="${post[1] - 3}" width="6" height="6" fill="#3b2a1e"/>`;
    return svg + labelText(place, `${o.name} · ${o.state}`, esc) + '</g>';
  }

  /** Why: a building must read at its true size, not as a fixed symbol (docs/research/72 §2).
   * What: the footprint in px for `metres` [width, depth] at `metresPerHex`: metres x
   * (hex-centre spacing / metres per hex), each side at least MIN_SIDE; if it would leave the
   * hex (the one hex the engine gives the building's cover and sight), it is scaled down to fit.
   * Test: scripts/check_map_features.mjs (scaled, centred, inside its hex). */
  function footprint(metres, metresPerHex) {
    const scale = SPACING / metresPerHex;
    let [w, h] = metres.map(m => Math.max(MIN_SIDE, m * scale));
    const fit = Math.min(1, SPACING / w, R / (h / 2 + w / (2 * Math.sqrt(3))));  // inside a pointy-top hex
    const capped = fit < 1;
    if (capped) [w, h] = [w * fit * .98, h * fit * .98];
    return {w, h, capped, enlarged: metres.some(m => m * scale < MIN_SIDE)};
  }

  // Above the footprint, where the label has always sat; then round it.
  function buildingPlaces(f, info, center, metresPerHex) {
    const [x, y] = center(f.pos), {w, h} = footprint(info.footprint_m || [30, 20], metresPerHex);
    return [{x, y: y - h / 2 - 6, anchor: 'middle'}, ...around(x, y, w / 2, h / 2)];
  }
  function building(f, info, center, esc, metresPerHex, place) {
    const [x, y] = center(f.pos), metres = info.footprint_m || [30, 20];
    const {w, h, capped, enlarged} = footprint(metres, metresPerHex);
    const note = `footprint ${metres[0]} x ${metres[1]} m at ${metresPerHex} m a hex${capped ? ', reduced to fit its hex' : ''}${enlarged ? ', enlarged to stay legible' : ''}`;
    const ridge = w >= h ? `M${x - w / 2 + 3},${y}H${x + w / 2 - 3}` : `M${x},${y - h / 2 + 3}V${y + h / 2 - 3}`;
    return open('building', f.id, info, esc, hiddenIf(place)) + title(f.name, info, esc, note)
      + `<rect class="footprint-shadow" x="${x - w / 2 + 2}" y="${y - h / 2 + 2}" width="${w}" height="${h}" fill="#3f2f22" fill-opacity=".3"/>`
      + `<rect class="footprint" x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" fill="#a8876a" stroke="#3f2f22" stroke-width="1.5"/>`
      + `<path class="footprint-ridge" d="${ridge}" stroke="#6e5541" stroke-width="1.2"/>`
      + labelText(place, f.name, esc) + '</g>';
  }

  const worksText = f => f.progress === 100 ? 'FIELDWORKS' : String(f.progress) + '% WORKS';
  // Right of the works symbol (drawn 24 px below its hex centre), where the label has always sat; then round it.
  function worksPlaces(f, center) {
    const [x, y] = center(f.pos);
    return [{x: x + 30, y: y + 29, anchor: 'start'}, ...around(x, y + 24, 25, 8)];
  }
  function works(f, info, center, esc, place) {
    const [x, y] = center(f.pos), shape = 'M-22,8V0L-11,-6L0,0L11,-6L22,0V8';
    const done = f.progress === 100;
    return open('works', f.id, info, esc, ` transform="translate(${x},${y + 24})" opacity="${done ? 1 : .65}"${hiddenIf(place)}`)
      + title(f.name, info, esc, done ? 'complete' : `${f.progress}% · cover ${f.cover}`)
      + `<path d="${shape}" fill="none" stroke="#70563a" stroke-width="6"/><path d="${shape}" fill="none" stroke="#cab18b" stroke-width="2"/>`
      + labelText(place, worksText(f), esc, x, y + 24) + '</g>';
  }

  /** Why: the layer, the legend and the hex tooltips must list the same marks.
   * What: every mark of `features` (the commander view) and the briefing `cells`, in draw
   * order: roads, bridges, compound walls, gates, buildings, works. Each has its `key`, `name`,
   * `hexes` (for tooltips), status `info` and `draw(center, esc)`.
   * Test: scripts/check_map_features.mjs. */
  function marks(features, options = {}) {
    const all = features || [], sources = options.sources || {}, metresPerHex = options.metresPerHex || 50;
    const roads = all.filter(f => f.kind === 'road');
    const bridges = new Map(all.filter(f => f.kind === 'bridge').map(f => [String(f.pos), f]));
    const crossings = (options.cells || []).filter(c => c.crossing === 'bridge').map(c => c.pos);
    for (const f of bridges.values()) if (!crossings.some(p => String(p) === String(f.pos))) crossings.push(f.pos);
    const list = [];
    const push = (key, kind, name, hexes, feature, draw, label) => {
      const info = statusOf(key, feature, sources);
      list.push({key, kind, name, hexes, info, draw: (center, esc, place = null) => draw(info, center, esc, place),
        ...(label ? {label: center => { const l = label(center, info); return {key, priority: PRIORITY[kind], text: l.text, candidates: l.places}; }} : {})});
    };
    const placed = [...crossings, ...all.filter(f => f.kind === 'building' || f.kind === 'fortification').map(f => f.pos)];
    for (const f of roads) push(f.id, 'road', f.name, f.hexes || f.points, f, (i, c, e, p) => road(f, i, c, e, p), c => ({text: f.name, places: roadPlaces(f, c, placed.map(c))}));
    for (const pos of crossings) {
      const f = bridges.get(String(pos)), key = f ? f.id : `crossing:${pos}`;
      push(key, 'bridge', f ? f.name : (sources[key] || {}).name || 'Bridge', [pos], f, (i, c, e, p) => bridge(pos, f, i, roads, c, e, p),
        (c, i) => ({text: bridgeText(f, i), places: bridgePlaces(pos, c)}));
    }
    const compounds = all.filter(f => f.kind === 'building' && f.openings && f.openings.length && f.compound);
    for (const f of compounds) push(`${f.id}#walls`, 'wall', `${f.name}: walls`, f.compound, f, (i, c, e) => compound(f, i, c, e));
    for (const f of compounds) for (const o of f.openings) {
      push(`${f.id}#${o.id}`, 'gate', `${o.name} · ${o.state}`, [o.inside, o.outside], f, (i, c, e, p) => gate(f, o, i, c, e, p),
        (c) => ({text: `${o.name} · ${o.state}`, places: gatePlaces(f, o, c)}));
    }
    for (const f of all.filter(f => f.kind === 'building')) {
      push(f.id, 'building', f.name, [f.pos], f, (i, c, e, p) => building(f, i, c, e, metresPerHex, p),
        (c, i) => ({text: f.name, places: buildingPlaces(f, i, c, metresPerHex)}));
    }
    for (const f of all.filter(f => f.kind === 'fortification')) {
      push(f.id, 'works', f.name + (f.progress === 100 ? '' : ` ${f.progress}% · cover ${f.cover}`), [f.pos], f, (i, c, e, p) => works(f, i, c, e, p),
        (c) => ({text: worksText(f), places: worksPlaces(f, c)}));
    }
    return list;
  }

  /** Why: the command map must show the features the engine moves and sees by.
   * What: one SVG group of every mark, each with a status tooltip. Options: `metresPerHex`
   * (footprint scale), `cells` (briefing cells: bridge crossings), `sources` (status table), `obstacles`
   * (counter boxes no label may sit under), `frame` (the map frame no label may cross, bt-T23).
   * Independent of the hex-grid toggle. Test: scripts/check_map_features.mjs. */
  function render(features, center, esc, options = {}) {
    const list = marks(features, options);
    const placed = placeLabels(list.flatMap(m => m.label ? [m.label(center)] : []), options.obstacles, options.frame);
    return '<g class="battle-features" pointer-events="none">' + list.map(m => m.draw(center, esc, placed.get(m.key) || null)).join('') + '</g>';
  }

  /** Tooltip lines for hex `pos`: each mark over it, with its status and basis. */
  function notes(features, pos, options = {}) {
    return marks(features, options).filter(m => m.hexes.some(p => String(p) === String(pos)))
      .map(m => `${m.name} (${LABELS[m.info.status] || m.info.status}: ${m.info.source})`);
  }

  /** Why: the status of every mark must be readable without hovering (docs/research/72 §3).
   * What: legend HTML: a symbol key for the kinds drawn, a key for the statuses used, and
   * one line per mark with its status and basis. Empty when nothing is drawn. */
  function legend(features, esc, options = {}) {
    const list = marks(features, options);
    if (!list.length) return '';
    const kinds = {road: 'Road or track', bridge: 'Bridge', wall: 'Wall', gate: 'Gate', building: 'Building footprint', works: 'Fieldworks'};
    const used = [...new Set(list.map(m => m.kind))], statuses = [...new Set(list.map(m => m.info.status))];
    return `<div class="legend-key">${used.map(k => `<span><i class="legend-symbol legend-${k}"></i>${kinds[k]}</span>`).join('')}</div>`
      + `<div class="legend-statuses">${statuses.map(s => `<span class="legend-status legend-status-${esc(s)}">${LABELS[s] || esc(s)}</span>`).join('')}</div>`
      + `<ul class="legend-items">${list.map(m => `<li data-feature="${esc(m.key)}"><i class="legend-symbol legend-${m.kind}"></i><b>${esc(m.name)}</b>`
        + ` <span class="legend-status legend-status-${esc(m.info.status)}">${LABELS[m.info.status] || esc(m.info.status)}</span> ${esc(m.info.source)}</li>`).join('')}</ul>`;
  }

  return {render, legend, notes, marks, footprint, perimeter, placeLabels, titlePlace, labelBox, around, SPACING};
})();
