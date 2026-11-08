/* Observer-only unit counters. Never fetch or infer hidden enemy attributes. */
const UnitIcons = (() => {
  const percent = value => typeof value === 'number' && Number.isFinite(value)
    ? Math.max(0, Math.min(100, Math.round(value))) : null;

  function describe(unit, contact = false) {
    const type = contact ? unit.composition?.type : unit.unit_type;
    const skill = contact ? null : percent(unit.skill);
    const fatigue = contact ? null : percent(unit.fatigue);
    const morale = contact ? null : percent(unit.morale);
    return {
      id: unit.id,
      type: type || 'Unknown type',
      symbol: ({infantry: 'INF', cavalry: 'CAV', artillery: 'ART'})[type] || '?',
      scout: !contact && unit.recon_role === 'scout',
      strength: contact ? (unit.strength_range?.join('–') || '?') : String(unit.strength ?? '?'),
      skill, energy: fatigue === null ? null : 100 - fatigue, morale,
      estimated: contact,
    };
  }

  function create({esc}) {
    const value = number => number === null ? '?' : String(number);
    function label(info) {
      return `${info.id} · ${info.type}${info.scout ? ' · scout' : ''} · ` +
        `${info.strength} ${info.estimated ? 'estimated ' : ''}troops · ` +
        `skill ${value(info.skill)} · energy ${value(info.energy)} · morale ${value(info.morale)}`;
    }

    function metrics(unit, contact = false) {
      const info = describe(unit, contact);
      return `<div class="unit-type">${esc(info.type)}${info.scout ? ' · Scout' : ''}</div>` +
        `<div class="unit-vitals" aria-label="${esc(label(info))}">` +
        [['Skill', info.skill], ['Energy', info.energy], ['Morale', info.morale]].map(([name, n]) =>
          `<span>${name}<b>${value(n)}${n === null ? '' : '%'}</b></span>`).join('') + '</div>';
    }

    const width = 112, height = 72;
    // Where each entry's card sits: the first free place round its point, in entry order.
    function layout(entries) {
      const boxes = [];
      const overlaps = box => boxes.some(other =>
        box.x < other.x + width + 7 && box.x + width + 7 > other.x &&
        box.y < other.y + height + 7 && box.y + height + 7 > other.y);
      const anchors = entries.map(entry => entry.point);
      for (const entry of entries) {
        const [x, y] = entry.point;
        const candidates = [];
        for (let ring = 0; ring < entries.length + 2; ring++) {
          for (const dx of [18 + ring * (width + 10), -width - 18 - ring * (width + 10)]) {
            for (const dy of [-height - 14, 14, -height - 14 - ring * (height + 10), 14 + ring * (height + 10)]) {
              candidates.push({x: Math.max(4, Math.min(964, x + dx)), y: Math.max(4, Math.min(764, y + dy))});
            }
          }
        }
        const box = candidates.find(candidate => !overlaps(candidate) && !anchors.some(([ax, ay]) =>
          ax > candidate.x - 10 && ax < candidate.x + width + 10 &&
          ay > candidate.y - 10 && ay < candidate.y + height + 10)) || candidates.find(candidate => !overlaps(candidate)) || candidates[0];
        boxes.push(box);
      }
      return boxes;
    }
    // bt-T16: the boxes a feature label must keep clear of: each card, and each anchor dot.
    function obstacles(entries) {
      return [...layout(entries).map(b => ({x0: b.x, y0: b.y, x1: b.x + width, y1: b.y + height})),
        ...entries.map(({point: [x, y]}) => ({x0: x - 6, y0: y - 6, x1: x + 6, y1: y + 6}))];
    }
    function render(entries) {
      const boxes = layout(entries);
      return entries.map((entry, index) => {
        const box = boxes[index];
        const info = describe(entry.unit, entry.contact);
        const [x, y] = entry.point;
        const attribute = entry.contact ? 'data-contact' : 'data-unit';
        const description = `${label(info)} · ${entry.report}`;
        const color = entry.enemy ? '#873e30' : '#284d68';
        return `<g class="unit-counter ${entry.enemy ? 'enemy-counter' : ''} ${entry.contact ? 'estimated-counter' : ''} ${entry.selected ? 'selected-counter' : ''}" ${attribute}="${esc(info.id)}" role="button" tabindex="0" aria-label="${esc(description)}">` +
          `<title>${esc(description)}. Energy is 100 minus fatigue. ${entry.contact ? "Select to inspect this report." : "Select for unit details and available orders, split or combine."}</title>` +
          `<path class="counter-leader" d="M${x},${y}L${box.x + width / 2},${box.y + height / 2}" stroke="${color}"/>` +
          `<circle class="counter-anchor" cx="${x}" cy="${y}" r="6" fill="${color}"/>` +
          `<g transform="translate(${box.x},${box.y})"><rect class="counter-body" width="${width}" height="${height}" rx="5" fill="${color}"/>` +
          `<text class="counter-id" x="7" y="15">${esc(info.id)}</text><text class="counter-type" x="105" y="15">${esc(info.symbol)}${info.scout ? ' / SC' : ''}</text>` +
          `<text class="counter-strength" x="7" y="35">${esc(info.strength)}<tspan class="counter-troops"> ${entry.contact ? 'est.' : 'troops'}</tspan></text>` +
          [['S', info.skill], ['E', info.energy], ['M', info.morale]].map(([key, n], index) => {
            const left = 7 + index * 35;
            return `<text class="counter-metric" x="${left}" y="52">${key} ${value(n)}</text>` +
              `<rect class="counter-track" x="${left}" y="59" width="28" height="4" rx="1"/>` +
              (n === null ? '' : `<rect class="counter-fill" x="${left}" y="59" width="${28 * n / 100}" height="4" rx="1"/>`);
          }).join('') + '</g></g>';
      }).join('');
    }
    return Object.freeze({render, metrics, layout, obstacles});
  }
  return Object.freeze({create, describe});
})();
