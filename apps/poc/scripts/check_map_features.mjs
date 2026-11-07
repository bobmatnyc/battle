// Check that every catalog scenario's roads and buildings render from the commander view
// the browser receives: one continuous line over the routed road hexes, a closed footprint
// per building, and a feature layer the hex-grid toggle cannot hide.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
const root=new URL('../',import.meta.url);
// The data path of GET /api/state: the commander view (RulesSimulation.view) through present_view.
const fixtureScript=`
import json
from battle.adapters.rules import RulesSimulation
from battle.bootstrap import build_headless_scenarios
from battle.presentation import present_view
from battle.scenario_entry import build_state
catalog = build_headless_scenarios()
out = {}
for sid in catalog.ids():
    entry = catalog.resolve(sid)
    out[sid] = present_view(RulesSimulation().view(build_state(entry)), entry)["map_features"]
print(json.dumps(out))`;
const generated=spawnSync('python3',['-c',fixtureScript],{cwd:root,encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const scenarios=JSON.parse(generated.stdout);
const context=vm.createContext({});
vm.runInContext(readFileSync(new URL('../static/map-features.js',import.meta.url),'utf8'),context);
const R=25.5,inner=R*Math.sqrt(3)/2,eps=1e-6;
const center=p=>[(p[0]+.5*(p[1]&1))*Math.sqrt(3)*R+24,p[1]*38.25+26];  // static/app.js center
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
context.center=center;context.esc=esc;
const render=features=>{context.features=features;return vm.runInContext('BattleFeatures.render(features,center,esc)',context);};
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
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
// Grid off adds only the no-grid class to #map; every rule it selects must style hex outlines alone.
const css=readFileSync(new URL('../static/style.css',import.meta.url),'utf8');
const gridRules=[...css.matchAll(/([^{}]*no-grid[^{}]*)\{([^}]*)\}/g)];
assert.ok(gridRules.length>0);
for(const [,selector,body] of gridRules){
  for(const one of selector.split(','))assert.match(one.trim(),/^#map\.no-grid \.hex$/,`grid toggle reaches ${one}`);
  assert.match(body.trim(),/^stroke-opacity:0;?$/);
}
assert.doesNotMatch(css,/battle-features/);  // No rule can hide the feature layer.
const summary=[];
for(const [sid,features] of Object.entries(scenarios)){
  const layer=render(features);
  let roads=0,buildings=0,stray=0;
  for(const f of features){
    const svg=render([f]);
    assert.ok(layer.includes(svg.slice(svg.indexOf('>')+1,-4)),`${sid} ${f.id}: drawn in the full layer`);
    if(f.kind==='road'){
      roads++;
      const ds=[...svg.matchAll(/<path d="([^"]+)"/g)].map(m=>m[1]);
      assert.equal(ds.length,2,`${sid} ${f.id}: casing and fill`);
      assert.equal(ds[0],ds[1]);
      assert.equal((ds[0].match(/M/g)||[]).length,1,`${sid} ${f.id}: one subpath, no gap`);
      const line=ds[0].split(/ ?[ML]/).filter(Boolean).map(s=>s.split(',').map(Number));
      assert.deepEqual(line,f.points.map(center));
      assert.ok(f.hexes.length>=2,`${sid} ${f.id}: routed hexes`);
      assert.deepEqual(line[0],center(f.hexes[0]));assert.deepEqual(line.at(-1),center(f.hexes.at(-1)));
      // Consecutive routed hexes touch (centres one hex apart), so the engine's road has no gap.
      for(let i=1;i<f.hexes.length;i++)assert.ok(Math.abs(dist(center(f.hexes[i-1]),center(f.hexes[i]))-Math.sqrt(3)*R)<eps,`${sid} ${f.id}: gap after ${f.hexes[i-1]}`);
      // The drawn line crosses every routed hex and never leaves them.
      for(const h of f.hexes){
        const near=Math.min(...line.slice(1).map((b,i)=>toSegment(center(h),line[i],b)));
        assert.ok(near<=inner+eps,`${sid} ${f.id}: line misses routed hex ${h} by ${near}`);
      }
      // A straight segment may clip the corner of a hex beside the routed chain; the
      // centreline stays within half the casing width, so the drawn road covers the chain.
      const casing=Number(svg.match(/stroke-width="([^"]+)"/)[1])/2;
      for(let i=1;i<line.length;i++){
        const n=Math.ceil(dist(line[i-1],line[i]));
        for(let k=0;k<=n;k++){
          const p=[line[i-1][0]+(line[i][0]-line[i-1][0])*k/n,line[i-1][1]+(line[i][1]-line[i-1][1])*k/n];
          const off=Math.min(...f.hexes.map(h=>outside(p,h)));
          stray=Math.max(stray,off);
          assert.ok(off<casing,`${sid} ${f.id}: line leaves the road hexes by ${off} px at ${p}`);
        }
      }
      assert.ok(svg.includes(`class="feature-label">${esc(f.name)}</text>`));
    }else if(f.kind==='building'){
      buildings++;
      const [x,y]=center(f.pos);
      const g=svg.match(/<g transform="translate\(([^,]+),([^)]+)\)"><rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"/);
      assert.ok(g,`${sid} ${f.id}: closed rect footprint`);
      assert.deepEqual([Number(g[1]),Number(g[2])],[x,y]);
      const [rx,ry,w,h]=g.slice(3).map(Number);
      assert.ok(w>0&&h>0);
      // The footprint lies inside its own hex, so neighbouring buildings never merge.
      for(const c of [[rx,ry],[rx+w,ry],[rx,ry+h],[rx+w,ry+h]])assert.ok(Math.hypot(...c)<inner,`${sid} ${f.id}: footprint leaves its hex`);
      assert.ok(svg.includes(`class="feature-label">${esc(f.name)}</text>`));
    }
  }
  summary.push(`${sid} ${roads} roads ${buildings} buildings`+(roads?` (max ${stray.toFixed(1)} px off)`:""));
}
assert.ok(summary.some(s=>/hougoumont.* [1-9] buildings/.test(s)));
console.log('Map features passed: '+summary.join('; ')+'; one continuous line over routed hexes, closed footprints, grid toggle styles hex outlines only.');
