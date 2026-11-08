// Route and sight check per player scenario (docs/research/72 §5): a scripted move order run
// through the engine (RulesSimulation) follows a named road hex by hex over road edges, and a
// sight line the engine blocks with a building is blocked by the drawn footprint; the drawn road
// line and footprint lie over the same hexes the engine moved through and sighted across.
// Usage: node scripts/check_route_sight.mjs [output dir for annotated SVGs]
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
const root=new URL('../',import.meta.url);
// Each case: the unit, an optional start hex (a test arrangement, not a scenario change), the road
// it should keep to and the goal hex on it; a sight line through a building hex.
const fixtureScript=`
import copy, json
from battle import engine, grid, recon
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import build_scenarios
from battle.presentation import present_view
from battle.scenario_entry import build_state, map_document
catalog = build_scenarios()
sim = RulesSimulation()
CASES = {
    # U1 is set at the east end of the north farm lane, far from the enemy, and ordered 11 hexes west.
    'little-round-top': {'unit': 'U1', 'road': 'north-lane', 'start': -1, 'goal': -12,
                         'sight': ('farmstead', [6, 3], [8, 3])},
    # The gate party leaves the north gate and marches up the lane to the ridge, from its own start.
    'hougoumont-north-gate': {'unit': 'A1', 'road': 'north-lane', 'start': None, 'goal': -1,
                              'sight': ('hougoumont', [11, 8], [11, 13])},
    # docs/research/74: Laurie's company marches from its own start down the town road, away from
    # the column. Concord has no building, so it has no sight case.
    'concord-north-bridge': {'unit': 'B2', 'road': 'town-road', 'start': None, 'goal': -1, 'sight': None},
    # docs/research/75: the west counter-attack group marches the Benouville road from its own start
    # to the hex before the guard's post. Test arrangement, not a scenario change: the default charges
    # end the battle at turn 5 (docs/research/54 §5), before any 7-step march, so the test state has
    # no demolition rule. Pegasus has no building, so it has no sight case.
    'pegasus-bridge': {'unit': 'R1', 'road': 'benouville-road', 'start': None, 'goal': -2, 'sight': None,
                       'no_demolition': True},
    # Hill 223 has no road and no building: no route or sight case.
    'hill-223-patrol': None,
}
out = {}
for sid in catalog.ids():
    case = CASES[sid]
    if case is None:
        out[sid] = None
        continue
    entry = catalog.resolve(sid)
    s = build_state(entry)
    if case.get('no_demolition'):
        s['bridge_demolition'] = []
    road = next(f for f in s['map_features'] if f['id'] == case['road'])
    u = next(u for u in s['units'] if u['id'] == case['unit'])
    if case['start'] is not None:
        u['pos'] = list(road['hexes'][case['start']])
        s['friendly_reports'][u['side']][u['id']]['pos'] = list(u['pos'])
    start, goal = list(u['pos']), road['hexes'][case['goal']]
    shown = present_view(sim.view(s), entry)
    order = {'unit_id': u['id'], 'stance': 'move', 'destination': goal}
    moves, seen = [], len(s['events'])
    if u['side'] == engine.player_side(s):
        s = sim.apply(s, {'type': 'orders', 'orders': [order]})
    else:  # The computer side's order goes out as its scripted decision does, in an interval.
        s = sim.apply(s, {'type': 'advance', 'decision': {'side': u['side'], 'source': 'scripted', 'orders': [order]}})
    moves += [[e['origin'], e['destination']] for e in s['events'][seen:] if e['kind'] == 'unit_moved' and e['unit_id'] == u['id']]
    seen = len(s['events'])
    while next(x for x in s['units'] if x['id'] == u['id'])['pos'] != goal and s['turn'] < 60:
        s = sim.apply(s, {'type': 'advance', 'decision': None})
        moves += [[e['origin'], e['destination']] for e in s['events'][seen:] if e['kind'] == 'unit_moved' and e['unit_id'] == u['id']]
        seen = len(s['events'])
    cells = s['cells']
    sight = None
    if case['sight']:
        bid, a, b = case['sight']
        bare = copy.deepcopy(s)
        hexes = grid.line(a, b)
        blocking = [p for p in hexes[1:-1] if cells[grid.key(p)].get('obstacle_height')]
        for p in blocking:
            bare['cells'][grid.key(p)]['obstacle_height'] = 0
        sight = {'building': bid, 'from': a, 'to': b, 'line': hexes, 'blocking': blocking,
                 'blocked': not recon.sees(s, {'pos': a}, b), 'clear_without': recon.sees(bare, {'pos': a}, b),
                 'building_hex': next(f['pos'] for f in s['map_features'] if f['id'] == bid)}
    out[sid] = {
        'unit': u['id'], 'start': start, 'goal': goal, 'turn': s['turn'], 'road': road['id'], 'road_hexes': road['hexes'],
        'moves': moves, 'road_edges': [list(b) in cells[grid.key(a)].get('road_neighbors', []) for a, b in moves],
        'path': grid.path(build_state(entry)['cells'], start, goal) if case['start'] is None else None,
        'sight': sight,
        'features': shown['map_features'], 'metres_per_hex': map_document(entry)['metres_per_hex'],
        'cells': list(map_document(entry)['cells']),
    }
print(json.dumps(out))`;
const generated=spawnSync('python3',['-c',fixtureScript],{cwd:root,encoding:'utf8',maxBuffer:64<<20});
assert.equal(generated.status,0,generated.stderr);
const cases=JSON.parse(generated.stdout);
const context=vm.createContext({});
for(const file of ['cartography.js','feature-sources.js','map-features.js'])vm.runInContext(readFileSync(new URL('../static/'+file,import.meta.url),'utf8'),context);
const R=25.5,SPACING=Math.sqrt(3)*R,inner=SPACING/2;
const center=p=>[(p[0]+.5*(p[1]&1))*SPACING+24,p[1]*38.25+26];  // static/app.js center
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
context.center=center;context.esc=esc;
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
function toSegment(p,a,b){
  const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));
  return dist(p,[a[0]+t*dx,a[1]+t*dy]);
}
// Liang-Barsky: does segment a-b cross the axis-aligned rect [x, y, w, h]?
function crossesRect(a,b,[x,y,w,h]){
  let t0=0,t1=1;const dx=b[0]-a[0],dy=b[1]-a[1];
  for(const [p,q] of [[-dx,a[0]-x],[dx,x+w-a[0]],[-dy,a[1]-y],[dy,y+h-a[1]]]){
    if(p===0){if(q<0)return false;continue;}
    const t=q/p;if(p<0)t0=Math.max(t0,t);else t1=Math.min(t1,t);
    if(t0>t1)return false;
  }
  return true;
}
const outDir=process.argv[2];
const lines=[];
for(const [sid,c] of Object.entries(cases)){
  if(!c){lines.push(`${sid}: no road and no building, so no route or sight case`);continue;}
  context.args=[c.features,{metresPerHex:c.metres_per_hex,cells:c.cells,sources:vm.runInContext(`BattleFeatureSources.forScenario(${JSON.stringify(sid)})`,context)}];
  const layer=vm.runInContext('BattleFeatures.render(args[0],center,esc,args[1])',context);
  // Route: the engine moved the unit to its goal, every step one road hex to the next over a road edge.
  assert.deepEqual(c.moves.at(-1)?.[1],c.goal,`${sid}: ${c.unit} reached ${c.goal} by turn ${c.turn}`);
  const along=c.road_hexes.map(String),steps=c.moves.map(([,d])=>d);
  // A step from off the road onto it (the gateway to the lane) is ordinary ground (docs/research/24).
  c.moves.forEach(([a,b],i)=>{
    assert.ok(along.includes(String(b)),`${sid}: ${c.unit} stepped off ${c.road} to ${b}`);
    if(!along.includes(String(a))){assert.equal(i,0,`${sid}: only the first step joins the road`);return;}
    assert.equal(Math.abs(along.indexOf(String(a))-along.indexOf(String(b))),1,`${sid}: ${a}->${b} is the next road hex`);
    assert.ok(c.road_edges[i],`${sid}: ${a}->${b} used a road edge (road_neighbors)`);
  });
  const roadSteps=c.moves.filter(([a])=>along.includes(String(a))).length;
  assert.ok(roadSteps>=7,`${sid}: ${roadSteps} steps along the road`);
  if(c.path)assert.deepEqual(c.path,steps,`${sid}: grid.path on the briefing cells is the route moved`);
  // The drawn road line crosses every hex the unit moved through.
  const d=layer.match(new RegExp(`data-feature="${c.road}"[^>]*>.*?<path class="road-casing" d="([^"]+)"`))[1];
  const line=d.split(/ ?[ML]/).filter(Boolean).map(s=>s.split(',').map(Number));
  for(const h of steps){
    const gap=Math.min(...line.slice(1).map((b,i)=>toSegment(center(h),line[i],b)));
    assert.ok(gap<=inner,`${sid}: drawn ${c.road} misses moved-through hex ${h} by ${gap.toFixed(1)} px`);
  }
  // Sight: the engine blocks the line only because of the building hex's obstacle height.
  const sight=c.sight;
  let seen='no building, no sight case',mark='';
  if(sight){
  assert.ok(sight.blocked,`${sid}: ${sight.from}->${sight.to} blocked`);
  assert.ok(sight.clear_without,`${sid}: clear without the building's obstacle height`);
  assert.deepEqual(sight.blocking,[sight.building_hex],`${sid}: the building hex is the only obstacle`);
  const rect=layer.match(new RegExp(`data-feature="${sight.building}"[^>]*>.*?<rect class="footprint" x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"`)).slice(1).map(Number);
  const [a,b]=[center(sight.from),center(sight.to)];
  assert.ok(crossesRect(a,b,rect),`${sid}: the drawn sight line crosses the drawn footprint`);
  // The footprint lies in the blocking hex, and the line crosses no other drawn footprint.
  assert.ok(dist([rect[0]+rect[2]/2,rect[1]+rect[3]/2],center(sight.building_hex))<1e-6);
  for(const m of layer.matchAll(/data-feature="([^"#]+)"[^>]*>(?:(?!<\/g>).)*?<rect class="footprint" x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/g)){
    if(m[1]!==sight.building)assert.ok(!crossesRect(a,b,m.slice(2).map(Number)),`${sid}: the line also crosses ${m[1]}`);
  }
  seen=`sight ${sight.from}->${sight.to} blocked by ${sight.building} at ${sight.building_hex}, clear without it`;
  mark=`<path d="M${a}L${b}" stroke="#a0281c" stroke-width="2.5" stroke-dasharray="6 4"/><circle cx="${a[0]}" cy="${a[1]}" r="5" fill="#a0281c"/><circle cx="${b[0]}" cy="${b[1]}" r="5" fill="none" stroke="#a0281c" stroke-width="2"/>`;
  }
  lines.push(`${sid}: ${c.unit} ${c.start}->${c.goal} along ${c.road} in ${steps.length} steps (${c.moves.filter(([a])=>along.includes(String(a))).length} over road edges) by turn ${c.turn}; ${seen}`);
  if(outDir){
    // An annotated read-only render: the route's hexes outlined, the sight line dashed.
    context.cells=c.cells;
    const terrain=vm.runInContext('BattleMap.render(cells,false,false)',context);
    const ring=p=>{const[x,y]=center(p);return Array.from({length:6},(_,i)=>{const t=(60*i-30)*Math.PI/180;return `${x+R*Math.cos(t)},${y+R*Math.sin(t)}`;}).join(' ');};
    const route=[c.start,...steps].map(p=>`<polygon points="${ring(p)}" fill="#2f6fa8" fill-opacity=".18" stroke="#2f6fa8" stroke-width="2"/>`).join('');
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 840" width="1080" height="840"><style>.feature-label{font:11px Arial,sans-serif;fill:#654e36;paint-order:stroke;stroke:#f7f3e9;stroke-width:3px}.terrain-label,.contour-label,.vector-scale text{font:10px Arial,sans-serif;fill:#6b7d6b}.vector-scale path{fill:none;stroke:#46553f}</style>${terrain}${layer}<g>${route}${mark}</g></svg>`;
    writeFileSync(join(outDir,`${sid}-route-sight.svg`),svg);
  }
}
assert.deepEqual(Object.keys(cases).sort(),['concord-north-bridge','hill-223-patrol','hougoumont-north-gate','little-round-top','pegasus-bridge']);
console.log('Route and sight passed:\n  '+lines.join('\n  '));
