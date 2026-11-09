// Check that every catalog scenario's roads, buildings, compounds, bridges and works render
// from the commander view the browser receives: one continuous line over the routed road
// hexes, a scaled footprint per building, the compound's walls and gates on the engine's own
// wall edges, a bridge mark that carries the road across, a status from the presentation
// sources table on every mark, and a feature layer the hex-grid toggle cannot hide.
// docs/research/64 (first checks), docs/research/72 (slice 1).
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
const root=new URL('../',import.meta.url);
// The data path of GET /api/state and /api/map: the commander view (RulesSimulation.view)
// through present_view, and the briefing cells of map_document. For each gated building the
// engine's own wall edges for the gate state the side knows (gates.known_cells), with the gate
// open as briefed and with the report changed to closed. `unseen` is the view after the truth
// changes behind the side's back: every gate shut, every bridge blown, new works dug.
const fixtureScript=`
import json
from copy import deepcopy
from battle import engine, gates, grid
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import build_headless_scenarios
from battle.presentation import present_view
from battle.scenario_entry import build_state, map_document
catalog = build_headless_scenarios()
sim = RulesSimulation()
def walls(s, side):
    known = gates.known_cells(s, side)
    out = {}
    for f in s['feature_reports'][side].values():
        if not f.get('openings'):
            continue
        out[f['id']] = sorted([p, n] for p in f['compound'] for n in known[grid.key(p)].get('walls', ()))
    return out
out = {}
for sid in catalog.ids():
    entry = catalog.resolve(sid)
    s = build_state(entry)
    side = engine.player_side(s)
    shown = present_view(sim.view(s), entry)
    closed = deepcopy(s)
    for f in closed['feature_reports'][side].values():
        for o in f.get('openings', ()):
            o['state'] = 'closed'
    secret = deepcopy(s)
    for f in secret['map_features']:
        for o in f.get('openings', ()):
            o['state'] = 'barred'
        if f['kind'] == 'bridge':
            f['state'] = 'destroyed'
    secret['map_features'].append({'id': 'works-secret', 'kind': 'fortification', 'name': 'Hasty fieldworks',
                                   'pos': [5, 5], 'cover': 40, 'progress': 50, 'briefed': False,
                                   'provenance': 'simulation-built', 'updated_turn': 1})
    doc = map_document(entry)
    out[sid] = {
        'features': shown['map_features'],
        'metres_per_hex': doc['metres_per_hex'],
        'cells': [{k: c[k] for k in ('pos', 'terrain', 'crossing') if k in c} for c in doc['cells']],
        'walls': walls(s, side),
        'closed': {'features': present_view(sim.view(closed), entry)['map_features'], 'walls': walls(closed, side)},
        'unseen': present_view(sim.view(secret), entry)['map_features'],
        'units': [{'id': u['id'], 'pos': u['pos']} for u in shown['units']],
        'contacts': [{'id': c['id'], 'pos': c['pos']} for c in shown['contacts']],
    }
print(json.dumps(out))`;
const generated=spawnSync('python3',['-c',fixtureScript],{cwd:root,encoding:'utf8',maxBuffer:64<<20});
assert.equal(generated.status,0,generated.stderr);
const scenarios=JSON.parse(generated.stdout);
const context=vm.createContext({});
for(const file of ['feature-sources.js','map-features.js','unit-icons.js'])vm.runInContext(readFileSync(new URL('../static/'+file,import.meta.url),'utf8'),context);
const R=25.5,SPACING=Math.sqrt(3)*R,inner=SPACING/2,eps=1e-6;
const center=p=>[(p[0]+.5*(p[1]&1))*SPACING+24,p[1]*38.25+26];  // static/app.js center
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
context.center=center;context.esc=esc;
const sourcesFor=sid=>vm.runInContext(`BattleFeatureSources.forScenario(${JSON.stringify(sid)})`,context);
// The call static/app.js makes, with the scenario's metres per hex, briefing cells and sources.
const render=(features,sid,data,extra={})=>{
  context.args=[features,{metresPerHex:data.metres_per_hex,cells:data.cells,sources:sourcesFor(sid),...extra}];
  return vm.runInContext('BattleFeatures.render(args[0],center,esc,args[1])',context);
};
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
const near=(a,b)=>dist(a,b)<1e-3;
function toSegment(p,a,b){
  const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));
  return dist(p,[a[0]+t*dx,a[1]+t*dy]);
}
// Pixels from p to hex h: 0 inside, else the distance to its nearest edge.
function outside(p,h){
  const [x,y]=center(h),v=Array.from({length:6},(_,i)=>{const a=(60*i-30)*Math.PI/180;return [x+R*Math.cos(a),y+R*Math.sin(a)];});
  let inside=false;
  for(let i=0,j=5;i<6;j=i++)if((v[i][1]>p[1])!==(v[j][1]>p[1])&&p[0]<(v[j][0]-v[i][0])*(p[1]-v[i][1])/(v[j][1]-v[i][1])+v[i][0])inside=!inside;
  return inside?0:Math.min(...v.map((a,i)=>toSegment(p,a,v[(i+1)%6])));
}
const points=d=>d.split(/ ?[ML]/).filter(Boolean).map(s=>s.split(',').map(Number));
const segments=d=>[...d.matchAll(/M([^ML]+)L([^ML]+)/g)].map(m=>[m[1],m[2]].map(s=>s.trim().split(',').map(Number)));
// One drawn group per mark: <g ... data-feature="key" ...>...</g> (marks never nest groups).
function group(svg,key){
  const m=svg.match(new RegExp(`<g [^>]*data-feature="${key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}"[^>]*>(.*?)</g>`));
  return m&&{open:m[0].slice(0,m[0].indexOf('>')+1),body:m[1]};
}
const attr=(open,name)=>open.match(new RegExp(` ${name}="([^"]*)"`))?.[1];
// A mark drawn alone is the mark drawn in the full layer, except where its label sits: bt-T16 moves a label off a collision.
const bare=s=>s.replace(/<text [^>]*class="feature-label">[^<]*<\/text>/g,'');
const inLayer=(layer,body)=>bare(layer).includes(bare(body));
// Grid off adds only the no-grid class to #map; every rule it selects must style hex outlines alone.
const css=readFileSync(new URL('../static/style.css',import.meta.url),'utf8');
const gridRules=[...css.matchAll(/([^{}]*no-grid[^{}]*)\{([^}]*)\}/g)];
assert.ok(gridRules.length>0);
for(const [,selector,body] of gridRules){
  for(const one of selector.split(','))assert.match(one.trim(),/^#map\.no-grid \.hex$/,`grid toggle reaches ${one}`);
  assert.match(body.trim(),/^stroke-opacity:0;?$/);
}
assert.doesNotMatch(css,/battle-features|\.feature-mark|\.feature-label[^{]*\{[^}]*(display|opacity|visibility)/);  // No rule can hide the feature layer.
const palette=['#e8f0df','#b9ddbc','#dce2dc','#b9d3e3','#d7e3cf'];  // static/cartography.js terrain fills
const STATUSES=['sourced','reconstructed','illustrative','reported'];
// Every drawn mark carries a status from static/feature-sources.js, in its tooltip and its data.
function checkStatus(sid,key,g){
  const source=sourcesFor(sid)[key];
  assert.ok(source,`${sid} ${key}: listed in static/feature-sources.js`);
  assert.ok(STATUSES.slice(0,3).includes(source.status),`${sid} ${key}: status ${source.status}`);
  assert.ok(source.source.length>20,`${sid} ${key}: basis given`);
  if(source.status!=='illustrative')assert.match(source.source,/\bS\d+\b|Age of Revolution|NAM/,`${sid} ${key}: a ${source.status} mark cites its source`);
  assert.equal(attr(g.open,'data-status'),source.status,`${sid} ${key}: data-status`);
  const title=g.body.match(/<title>([^<]*)<\/title>/)?.[1]||'';
  assert.ok(title.includes(esc(source.source)),`${sid} ${key}: tooltip cites the basis`);
  assert.match(title,new RegExp(source.status,'i'),`${sid} ${key}: tooltip names the status`);
}
const summary=[];
let compounds=0,bridgesDrawn=0,footprints=0,spans=0;
for(const [sid,data] of Object.entries(scenarios)){
  const features=data.features,layer=render(features,sid,data),keys=new Set();
  let roads=0,buildings=0,stray=0;
  const roadEnds=[];
  for(const f of features){
    const svg=render([f],sid,data);
    if(f.kind==='road'){
      roads++;keys.add(f.id);
      // Read from the full layer: the label placement avoids the other marks drawn with it.
      const g=group(layer,f.id);
      assert.ok(g,`${sid} ${f.id}: a road group in the full layer`);
      assert.deepEqual(group(svg,f.id).body.match(/<path[^>]+>/g),g.body.match(/<path[^>]+>/g),`${sid} ${f.id}: same line alone and in the layer`);
      checkStatus(sid,f.id,g);
      const ds=[...g.body.matchAll(/<path class="road-(?:casing|fill)" d="([^"]+)"/g)].map(m=>m[1]);
      assert.equal(ds.length,2,`${sid} ${f.id}: casing and fill`);
      assert.equal(ds[0],ds[1]);
      assert.equal((ds[0].match(/M/g)||[]).length,1,`${sid} ${f.id}: one subpath, no gap`);
      const line=points(ds[0]);
      assert.deepEqual(line,f.points.map(center));
      assert.ok(f.hexes.length>=2,`${sid} ${f.id}: routed hexes`);
      assert.deepEqual(line[0],center(f.hexes[0]));assert.deepEqual(line.at(-1),center(f.hexes.at(-1)));
      roadEnds.push(f.hexes[0],f.hexes.at(-1));
      // Consecutive routed hexes touch (centres one hex apart), so the engine's road has no gap.
      for(let i=1;i<f.hexes.length;i++)assert.ok(Math.abs(dist(center(f.hexes[i-1]),center(f.hexes[i]))-SPACING)<eps,`${sid} ${f.id}: gap after ${f.hexes[i-1]}`);
      // The drawn line crosses every routed hex and never leaves them.
      for(const h of f.hexes){
        const gap=Math.min(...line.slice(1).map((b,i)=>toSegment(center(h),line[i],b)));
        assert.ok(gap<=inner+eps,`${sid} ${f.id}: line misses routed hex ${h} by ${gap}`);
      }
      // A straight segment may clip the corner of a hex beside the routed chain; the
      // centreline stays within half the casing width, so the drawn road covers the chain.
      const casing=Number(g.body.match(/stroke-width="([^"]+)"/)[1])/2;
      for(let i=1;i<line.length;i++){
        const n=Math.ceil(dist(line[i-1],line[i]));
        for(let k=0;k<=n;k++){
          const p=[line[i-1][0]+(line[i][0]-line[i-1][0])*k/n,line[i-1][1]+(line[i][1]-line[i-1][1])*k/n];
          const off=Math.min(...f.hexes.map(h=>outside(p,h)));
          stray=Math.max(stray,off);
          assert.ok(off<casing,`${sid} ${f.id}: line leaves the road hexes by ${off} px at ${p}`);
        }
      }
      assert.ok(g.body.includes(`class="feature-label">${esc(f.name)}</text>`),`${sid} ${f.id}: label`);
    }else if(f.kind==='building'){
      buildings++;footprints++;keys.add(f.id);
      const g=group(svg,f.id);
      assert.ok(g,`${sid} ${f.id}: a building group`);
      assert.ok(inLayer(layer,g.body));
      checkStatus(sid,f.id,g);
      const [x,y]=center(f.pos);
      const rect=g.body.match(/<rect class="footprint" x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)" fill="([^"]+)" stroke="([^"]+)" stroke-width="([^"]+)"/);
      assert.ok(rect,`${sid} ${f.id}: closed footprint rect`);
      const [rx,ry,w,h]=rect.slice(1,5).map(Number);
      // Scale rule: metres x (hex-centre spacing in px / metres_per_hex), at least 6 px a side.
      const metres=sourcesFor(sid)[f.id].footprint_m;
      assert.ok(Array.isArray(metres)&&metres.length===2,`${sid} ${f.id}: footprint in metres`);
      const scale=SPACING/data.metres_per_hex;
      assert.ok(Math.abs(w-Math.max(6,metres[0]*scale))<1e-3&&Math.abs(h-Math.max(6,metres[1]*scale))<1e-3,`${sid} ${f.id}: footprint ${w}x${h} px is ${metres} m at ${data.metres_per_hex} m a hex`);
      assert.ok(Math.abs(rx+w/2-x)<1e-3&&Math.abs(ry+h/2-y)<1e-3,`${sid} ${f.id}: centred on its hex`);
      // The footprint lies inside its own hex, the hex whose cover and sight the engine changes.
      for(const c of [[rx,ry],[rx+w,ry],[rx,ry+h],[rx+w,ry+h]])assert.equal(outside(c,f.pos),0,`${sid} ${f.id}: footprint leaves its hex`);
      // Distinct from the hex fills: not a terrain colour, with a dark outline.
      assert.ok(!palette.includes(rect[5].toLowerCase()),`${sid} ${f.id}: footprint fill is not a terrain fill`);
      assert.ok(Number(rect[7])>=1.5);
      assert.ok(g.body.includes(`class="feature-label">${esc(f.name)}</text>`),`${sid} ${f.id}: label`);
      // A footprint scales with the map: twice the metres per hex, half the size (or the 6 px floor).
      const half=render([f],sid,{...data,metres_per_hex:data.metres_per_hex*2});
      const w2=Number(group(half,f.id).body.match(/<rect class="footprint" x="[^"]+" y="[^"]+" width="([^"]+)"/)[1]);
      assert.ok(Math.abs(w2-Math.max(6,metres[0]*scale/2))<1e-3,`${sid} ${f.id}: footprint scales with metres_per_hex`);
      if(f.openings?.length){
        compounds++;
        checkCompound(sid,data,f,svg,layer,keys);
      }
    }else if(f.kind==='fortification'){
      keys.add(f.id);
      const g=group(svg,f.id);
      assert.ok(g&&inLayer(layer,g.body),`${sid} ${f.id}: works drawn`);
      checkStatus(sid,f.id,g);
      assert.match(g.body,/class="feature-label">(FIELDWORKS|\d+% WORKS)/);
    }
  }
  // Bridges: every briefed crossing cell and every bridge feature the side knows has one mark,
  // and the road ends beside it are joined across it by a span drawn like the road.
  const known=new Map(features.filter(f=>f.kind==='bridge').map(f=>[String(f.pos),f]));
  const crossings=data.cells.filter(c=>c.crossing==='bridge').map(c=>c.pos);
  for(const f of known.values())assert.ok(crossings.some(p=>String(p)===String(f.pos)),`${sid} ${f.id}: bridge on a crossing cell`);
  for(const pos of crossings){
    bridgesDrawn++;
    const feature=known.get(String(pos)),key=feature?feature.id:`crossing:${pos}`;
    keys.add(key);
    const g=group(layer,key);
    assert.ok(g,`${sid} ${key}: bridge mark drawn`);
    checkStatus(sid,key,g);
    assert.equal(attr(g.open,'data-state'),feature?.state||'intact');
    assert.match(g.body,/class="bridge-deck"/,`${sid} ${key}: its own mark`);
    assert.ok(g.body.includes('class="feature-label">'),`${sid} ${key}: label`);
    const ends=roadEnds.filter(h=>Math.abs(dist(center(h),center(pos))-SPACING)<eps);
    assert.ok(ends.length>=2,`${sid} ${key}: two road ends beside the bridge`);
    const span=g.body.match(/<path class="road-span-casing" d="([^"]+)" fill="none" stroke="([^"]+)" stroke-width="([^"]+)"/);
    assert.ok(span,`${sid} ${key}: the road continues across the bridge`);
    const line=points(span[1]);
    assert.equal(line.length,3);assert.ok(near(line[1],center(pos)),`${sid} ${key}: span crosses the bridge hex centre`);
    for(const end of [line[0],line[2]])assert.ok(ends.some(h=>near(center(h),end)),`${sid} ${key}: span meets a road end`);
    const roadCasing=layer.match(/<path class="road-casing" d="[^"]+" fill="none" stroke="([^"]+)" stroke-width="([^"]+)"/);
    assert.deepEqual([span[2],span[3]],[roadCasing[1],roadCasing[2]],`${sid} ${key}: span drawn like the road`);
    spans++;
    // A bridge known destroyed carries no road across and is drawn broken.
    const blown=feature?{...feature,state:'destroyed'}:null;
    if(blown){
      const broken=group(render([...features.filter(f=>f!==feature),blown],sid,data),key);
      assert.equal(attr(broken.open,'data-state'),'destroyed');
      assert.doesNotMatch(broken.body,/road-span/);assert.match(broken.body,/bridge-broken/);
    }
  }
  // Coverage: the sources table lists exactly the marks drawn (no stale or missing entries).
  assert.deepEqual([...keys].sort(),Object.keys(sourcesFor(sid)).sort(),`${sid}: sources table matches the drawn marks`);
  // Only the commander view is drawn: truth changed behind the side's back changes nothing.
  assert.equal(render(data.unseen,sid,data),layer,`${sid}: unseen gates, bridges and works stay hidden`);
  // The legend lists every mark with its status and basis.
  context.args=[features,{cells:data.cells,sources:sourcesFor(sid)}];
  const legend=vm.runInContext('BattleFeatures.legend(args[0],esc,args[1])',context);
  for(const key of keys){
    const s=sourcesFor(sid)[key];
    assert.ok(legend.includes(`data-feature="${esc(key)}"`)&&legend.includes(esc(s.source)),`${sid} ${key}: in the legend`);
  }
  if(keys.size)for(const status of new Set([...keys].map(k=>sourcesFor(sid)[k].status)))assert.ok(legend.includes(`legend-status-${status}`),`${sid}: legend key for ${status}`);
  summary.push(`${sid} ${roads} roads ${buildings} buildings ${crossings.length} bridges`+(roads?` (max ${stray.toFixed(1)} px off)`:""));
}
// Hougoumont: the compound yard, its walls on the engine's wall edges, and the gate in the
// state the side knows, open as briefed and shut when the report says so.
function checkCompound(sid,data,f,svg,layer,keys){
  for(const [label,features,walls] of [['briefed',data.features,data.walls],['reported closed',data.closed.features,data.closed.walls]]){
    const building=features.find(x=>x.id===f.id),drawn=render([building],sid,data);
    const wallKey=`${f.id}#walls`;keys.add(wallKey);
    const g=group(drawn,wallKey);
    assert.ok(g,`${sid} ${wallKey}: compound drawn (${label})`);
    if(label==='briefed'){assert.ok(inLayer(layer,g.body));checkStatus(sid,wallKey,g);}
    const yard=g.body.match(/<path class="compound-yard" d="([^"]+)"/);
    assert.ok(yard,`${sid}: compound yard`);
    assert.equal((yard[1].match(/M/g)||[]).length,building.compound.length,`${sid}: one yard ring per compound hex`);
    const wallPath=g.body.match(/<path class="compound-wall" d="([^"]+)"/)[1];
    const gatesDrawn=building.openings.map(o=>{const k=`${f.id}#${o.id}`;keys.add(k);return [o,group(drawn,k)];});
    // Every barrier drawn (wall segment or shut gate) sits on an edge the engine walls, and back.
    const barrier=[...segments(wallPath)];
    for(const [o,gate] of gatesDrawn){
      assert.ok(gate,`${sid} ${o.id}: gate drawn (${label})`);
      if(label==='briefed'){assert.ok(inLayer(layer,gate.body));checkStatus(sid,`${f.id}#${o.id}`,gate);}
      assert.equal(attr(gate.open,'data-state'),o.state,`${sid} ${o.id}: drawn in the state the side knows`);
      assert.ok(gate.body.includes(`class="feature-label">${esc(o.name)} · ${esc(o.state)}</text>`),`${sid} ${o.id}: labelled with its state`);
      const leaf=gate.body.match(/<path class="gate-(open|shut)" d="([^"]+)"/);
      assert.ok(leaf,`${sid} ${o.id}: gate mark`);
      assert.equal(leaf[1],['open','closing','forced'].includes(o.state)?'open':'shut');
      const edge=gate.body.match(/data-edge="([^"]+)"/)[1].split(' ').map(s=>s.split(',').map(Number));
      assert.ok(near([(edge[0][0]+edge[1][0])/2,(edge[0][1]+edge[1][1])/2],[(center(o.inside)[0]+center(o.outside)[0])/2,(center(o.inside)[1]+center(o.outside)[1])/2]),`${sid} ${o.id}: on the edge between its inside and outside hexes`);
      if(leaf[1]==='shut')barrier.push(edge);
    }
    const mids=barrier.map(([a,b])=>[(a[0]+b[0])/2,(a[1]+b[1])/2]);
    const engine=walls[f.id].map(([p,n])=>[(center(p)[0]+center(n)[0])/2,(center(p)[1]+center(n)[1])/2]);
    assert.equal(mids.length,engine.length,`${sid}: ${mids.length} drawn barrier edges, engine walls ${engine.length} (${label})`);
    for(const m of engine)assert.ok(mids.some(d=>near(d,m)),`${sid}: engine wall at ${m} drawn (${label})`);
    for(const [a,b] of barrier)assert.ok(Math.abs(dist(a,b)-R)<1e-3,`${sid}: a barrier is one hex edge long`);
  }
}
// bt-T16 (docs/research/80): no feature label meets another, and no counter covers one. The check reads the
// drawn SVG with its own, narrower text-width estimate (6 px a character, 7.8 for capitals), so it does not
// share the placement rule's margin. The counters are the real cards (unit-icons.js) of the scenario's start.
const PLAYABLE=['little-round-top','hougoumont-north-gate','concord-north-bridge','pegasus-bridge','hill-223-patrol'];
const unescape=s=>s.replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
function drawnLabels(layer){
  const out=[];
  for(const m of layer.matchAll(/<g class="feature-mark[^>]*data-feature="([^"]*)"([^>]*)>(.*?)<\/g>/g)){
    const t=m[3].match(/<text x="([-\d.]+)" y="([-\d.]+)"(?: text-anchor="(\w+)")? class="feature-label">([^<]*)<\/text>/);
    if(!t)continue;
    const move=m[2].match(/translate\(([-\d.]+),([-\d.]+)\)/),x=+t[1]+(move?+move[1]:0),y=+t[2]+(move?+move[2]:0),text=unescape(t[4]);
    const w=[...text].reduce((n,c)=>n+(/[A-Z%]/.test(c)?7.8:6),0),x0=t[3]==='middle'?x-w/2:t[3]==='end'?x-w:x;
    out.push({key:m[1],text,x0:x0-1,y0:y-10,x1:x0+w+1,y1:y+3});
  }
  return out;
}
const meet=(a,b)=>a.x0<b.x1&&b.x0<a.x1&&a.y0<b.y1&&b.y0<a.y1;
// bt-T23 (docs/research/80 §7): every label stays inside the 1080 x 840 scene the desk shows (static/app.js MAP_FRAME).
const FRAME={x0:0,y0:0,x1:1080,y1:840};
const within=(b,f)=>b.x0>=f.x0&&b.y0>=f.y0&&b.x1<=f.x1&&b.y1<=f.y1;
function countersOf(data){
  const entries=[...data.contacts.map(c=>({unit:{id:c.id},contact:true,enemy:true,point:center(c.pos),report:''})),
    ...data.units.map(u=>({unit:{id:u.id,unit_type:'infantry'},contact:false,enemy:false,point:center(u.pos),report:''}))];
  context.entries=entries;
  const html=vm.runInContext('UnitIcons.create({esc}).render(entries)',context);
  const cards=[...html.matchAll(/<g transform="translate\(([-\d.]+),([-\d.]+)\)"><rect class="counter-body" width="(\d+)" height="(\d+)"/g)]
    .map(m=>({x0:+m[1],y0:+m[2],x1:+m[1]+ +m[3],y1:+m[2]+ +m[4]}));
  const dots=[...html.matchAll(/<circle class="counter-anchor" cx="([-\d.]+)" cy="([-\d.]+)" r="(\d+)"/g)]
    .map(m=>({x0:+m[1]-m[3],y0:+m[2]-m[3],x1:+m[1]+ +m[3],y1:+m[2]+ +m[3]}));
  assert.equal(cards.length,entries.length,'one card parsed per counter');
  return {entries,cards,dots,obstacles:vm.runInContext('UnitIcons.create({esc}).obstacles(entries)',context)};
}
let labelsChecked=0;
for(const sid of PLAYABLE){
  const data=scenarios[sid];
  const counters=countersOf(data);
  const layer=render(data.features,sid,data,{obstacles:counters.obstacles,frame:FRAME});
  const labels=drawnLabels(layer);
  assert.ok(labels.length>0,`${sid}: labels drawn`);
  assert.doesNotMatch(layer,/data-label="hidden"/,`${sid}: no label is hidden at the scenario's start`);
  for(const l of labels)assert.ok(within(l,FRAME),`${sid}: "${l.text}" crosses the map frame ${JSON.stringify(l)}`);
  for(let i=0;i<labels.length;i++){
    for(let j=i+1;j<labels.length;j++)assert.ok(!meet(labels[i],labels[j]),`${sid}: "${labels[i].text}" meets "${labels[j].text}"`);
    for(const c of [...counters.cards,...counters.dots])assert.ok(!meet(labels[i],c),`${sid}: a counter covers "${labels[i].text}"`);
  }
  labelsChecked+=labels.length;
}
// The rule: lower priority number first, then key; the first candidate whose box is free; none free hides it.
{
  const place=(specs,obstacles)=>{
    context.args=[specs,obstacles];
    return JSON.parse(vm.runInContext('JSON.stringify([...BattleFeatures.placeLabels(args[0],args[1]).entries()])',context));
  };
  const spot=(x,y)=>({x,y,anchor:'start'});
  const a={key:'a',priority:1,text:'Alpha',candidates:[spot(10,20),spot(10,60)]};
  const b={key:'b',priority:0,text:'Bravo',candidates:[spot(10,20),spot(10,60)]};
  assert.deepEqual(place([a,b],[]),[['b',spot(10,20)],['a',spot(10,60)]],'the lower priority number takes the shared first place; the other moves on');
  assert.deepEqual(place([b,a],[]),place([a,b],[]),'the input order does not matter');
  const tie={key:'c',priority:1,text:'Charlie',candidates:[spot(10,20),spot(10,60)]};
  assert.deepEqual(place([tie,a],[]),[['a',spot(10,20)],['c',spot(10,60)]],'equal priority: the lower key goes first');
  const wall={x0:0,y0:0,x1:200,y1:30};
  assert.deepEqual(place([a],[wall]),[['a',spot(10,60)]],'an obstacle sends the label to its next place');
  assert.deepEqual(place([a],[wall,{x0:0,y0:40,x1:200,y1:90}]),[['a',null]],'no free place hides the label');
  assert.deepEqual(place([{...a,candidates:[spot(10,20)]},{...b,candidates:[spot(10,20)]}],[]),[['b',spot(10,20)],['a',null]],
    'of two labels that want one place the higher-numbered priority is hidden');
  // bt-T23: a place outside the frame is not taken; no place inside it hides the label; no frame, no test.
  const framed=(specs,frame)=>{
    context.args=[specs,[],frame];
    return JSON.parse(vm.runInContext('JSON.stringify([...BattleFeatures.placeLabels(args[0],args[1],args[2]).entries()])',context));
  };
  const edge={key:'e',priority:0,text:'Alpha',candidates:[spot(1060,20),{x:1060,y:20,anchor:'end'}]};
  assert.deepEqual(framed([edge]),[['e',spot(1060,20)]],'with no frame the first place is taken, as before');
  assert.deepEqual(framed([edge],FRAME),[['e',{x:1060,y:20,anchor:'end'}]],'the first place crosses the right edge; the flipped one is taken');
  assert.deepEqual(framed([{...edge,candidates:[spot(10,5),spot(-4,60)]}],FRAME),[['e',null]],'no place inside the frame hides the label');
  // The objective's title: Hill 223's shack is in column 0, where the centred title was cut at the left edge.
  const [x,y]=center([0,11]);
  const lines=[{text:'Command post at the shack',y:y-118,size:21},{text:'PATROL OBJECTIVE',y:y-97,size:10,spacing:1.4}];
  context.args=[lines,x,R,FRAME];
  const title=JSON.parse(vm.runInContext('JSON.stringify(BattleFeatures.titlePlace(...args))',context));
  assert.equal(title.anchor,'start','the shack title starts right of the left edge');
  for(const l of lines){
    context.args=[l.text,{...title,y:l.y},l.size,l.spacing];
    assert.ok(within(JSON.parse(vm.runInContext('JSON.stringify(BattleFeatures.labelBox(...args))',context)),FRAME),`Hill 223: "${l.text}" inside the frame`);
  }
  context.args=[[{text:'Little Round Top',y:300,size:21}],540,R,FRAME];
  assert.equal(vm.runInContext('JSON.stringify(BattleFeatures.titlePlace(...args))',context),JSON.stringify({x:540,anchor:'middle'}),'a title that fits stays centred');
}
assert.ok(summary.some(s=>/hougoumont.* [1-9] buildings/.test(s)));
assert.equal(compounds,1,'the Hougoumont compound is checked');
assert.ok(spans>=4,'Concord (two entries) and both Pegasus crossings carry the road');
console.log('Map features passed: '+summary.join('; ')+`; one continuous line over routed hexes, ${footprints} scaled footprints, ${compounds} compound on the engine's wall edges with the gate as known (open and closed), ${spans} bridges carrying the road, status on every mark and in the legend, unseen truth hidden, grid toggle styles hex outlines only.`);
