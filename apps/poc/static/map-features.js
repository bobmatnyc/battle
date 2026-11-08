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
  function road(f, info, center, esc) {
    const d = f.points.map((p, i) => (i ? 'L' : 'M') + pt(center(p))).join(' ');
    const [x, y] = center(f.points[1]);
    return open('road', f.id, info, esc) + title(f.name, info, esc)
      + `<path class="road-casing" d="${d}" fill="none" stroke="${ROAD.casing}" stroke-width="${ROAD.casingWidth}" stroke-linejoin="round"/>`
      + `<path class="road-fill" d="${d}" fill="none" stroke="${ROAD.fill}" stroke-width="${ROAD.fillWidth}" stroke-linejoin="round"/>`
      + `<text x="${x + 12}" y="${y - 14}" class="feature-label">${esc(f.name)}</text></g>`;
  }

  // Why: roads stop at each bank (the bridge hex keeps its own cost), but the player must see the
  // road carried across. What: a span from each road end beside the bridge through its centre,
  // drawn like the road, under a deck with parapets; a destroyed bridge is drawn broken, no span.
  function bridge(pos, feature, info, roads, center, esc) {
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
    let svg = open('bridge', feature ? feature.id : `crossing:${pos}`, info, esc, ` data-state="${esc(state)}"`)
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
    const label = state === 'intact' ? name : `${name} · ${state === 'charges' ? 'charges' : state}`;
    return svg + `<text x="${c[0]}" y="${c[1] + R + 14}" text-anchor="middle" class="feature-label">${esc(label)}</text></g>`;
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
  function gate(f, o, info, center, esc) {
    const e = perimeter(f.compound, center).find(x => isGate(x, o, center));
    const outward = unit(center(o.inside), center(o.outside)), along = unit(e.a, e.b);
    const passable = PASSABLE.includes(o.state);
    let svg = open('gate', `${f.id}#${o.id}`, info, esc, ` data-state="${esc(o.state)}"`) + title(o.name, info, esc, o.state);
    const edge = ` data-edge="${pt(e.a)} ${pt(e.b)}"`;
    if (passable) {
      const leaf = (post, dir) => `M${pt(post)}L${pt(add(add(post, outward, 9), along, dir * 4))}`;
      svg += `<path class="gate-open" d="${leaf(e.a, 1)}${leaf(e.b, -1)}"${edge} fill="none" stroke="#7a2e1f" stroke-width="3" stroke-linecap="round"/>`;
    } else {
      svg += `<path class="gate-shut" d="M${pt(e.a)}L${pt(e.b)}"${edge} stroke="#7a2e1f" stroke-width="7"/>`;
      if (o.state === 'barred') svg += `<path class="gate-bar" d="M${pt(add(add(e.a, along, 5), outward, 4))}L${pt(add(add(e.b, along, -5), outward, 4))}" stroke="#f1e6c8" stroke-width="2"/>`;
    }
    for (const post of [e.a, e.b]) svg += `<rect class="gate-post" x="${post[0] - 3}" y="${post[1] - 3}" width="6" height="6" fill="#3b2a1e"/>`;
    const at = add([(e.a[0] + e.b[0]) / 2, (e.a[1] + e.b[1]) / 2], outward, 18);
    return svg + `<text x="${at[0] + 8}" y="${at[1]}" class="feature-label">${esc(o.name)} · ${esc(o.state)}</text></g>`;
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

  function building(f, info, center, esc, metresPerHex) {
    const [x, y] = center(f.pos), metres = info.footprint_m || [30, 20];
    const {w, h, capped, enlarged} = footprint(metres, metresPerHex);
    const note = `footprint ${metres[0]} x ${metres[1]} m at ${metresPerHex} m a hex${capped ? ', reduced to fit its hex' : ''}${enlarged ? ', enlarged to stay legible' : ''}`;
    const ridge = w >= h ? `M${x - w / 2 + 3},${y}H${x + w / 2 - 3}` : `M${x},${y - h / 2 + 3}V${y + h / 2 - 3}`;
    return open('building', f.id, info, esc) + title(f.name, info, esc, note)
      + `<rect class="footprint-shadow" x="${x - w / 2 + 2}" y="${y - h / 2 + 2}" width="${w}" height="${h}" fill="#3f2f22" fill-opacity=".3"/>`
      + `<rect class="footprint" x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" fill="#a8876a" stroke="#3f2f22" stroke-width="1.5"/>`
      + `<path class="footprint-ridge" d="${ridge}" stroke="#6e5541" stroke-width="1.2"/>`
      + `<text x="${x}" y="${y - h / 2 - 6}" text-anchor="middle" class="feature-label">${esc(f.name)}</text></g>`;
  }

  function works(f, info, center, esc) {
    const [x, y] = center(f.pos), shape = 'M-22,8V0L-11,-6L0,0L11,-6L22,0V8';
    const done = f.progress === 100;
    return open('works', f.id, info, esc, ` transform="translate(${x},${y + 24})" opacity="${done ? 1 : .65}"`)
      + title(f.name, info, esc, done ? 'complete' : `${f.progress}% · cover ${f.cover}`)
      + `<path d="${shape}" fill="none" stroke="#70563a" stroke-width="6"/><path d="${shape}" fill="none" stroke="#cab18b" stroke-width="2"/>`
      + `<text x="30" y="5" text-anchor="start" class="feature-label">${done ? 'FIELDWORKS' : esc(f.progress) + '% WORKS'}</text></g>`;
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
    const push = (key, kind, name, hexes, feature, draw) => {
      const info = statusOf(key, feature, sources);
      list.push({key, kind, name, hexes, info, draw: (center, esc) => draw(info, center, esc)});
    };
    for (const f of roads) push(f.id, 'road', f.name, f.hexes || f.points, f, (i, c, e) => road(f, i, c, e));
    for (const pos of crossings) {
      const f = bridges.get(String(pos)), key = f ? f.id : `crossing:${pos}`;
      push(key, 'bridge', f ? f.name : (sources[key] || {}).name || 'Bridge', [pos], f, (i, c, e) => bridge(pos, f, i, roads, c, e));
    }
    const compounds = all.filter(f => f.kind === 'building' && f.openings && f.openings.length && f.compound);
    for (const f of compounds) push(`${f.id}#walls`, 'wall', `${f.name}: walls`, f.compound, f, (i, c, e) => compound(f, i, c, e));
    for (const f of compounds) for (const o of f.openings) {
      push(`${f.id}#${o.id}`, 'gate', `${o.name} · ${o.state}`, [o.inside, o.outside], f, (i, c, e) => gate(f, o, i, c, e));
    }
    for (const f of all.filter(f => f.kind === 'building')) push(f.id, 'building', f.name, [f.pos], f, (i, c, e) => building(f, i, c, e, metresPerHex));
    for (const f of all.filter(f => f.kind === 'fortification')) {
      push(f.id, 'works', f.name + (f.progress === 100 ? '' : ` ${f.progress}% · cover ${f.cover}`), [f.pos], f, (i, c, e) => works(f, i, c, e));
    }
    return list;
  }

  /** Why: the command map must show the features the engine moves and sees by.
   * What: one SVG group of every mark, each with a status tooltip. Options: `metresPerHex`
   * (footprint scale), `cells` (briefing cells: bridge crossings), `sources` (status table).
   * Independent of the hex-grid toggle. Test: scripts/check_map_features.mjs. */
  function render(features, center, esc, options = {}) {
    return '<g class="battle-features" pointer-events="none">' + marks(features, options).map(m => m.draw(center, esc)).join('') + '</g>';
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

  return {render, legend, notes, marks, footprint, perimeter, SPACING};
})();
