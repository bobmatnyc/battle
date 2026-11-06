// Check that the display projection preserves engine geometry and accepts only terrain data.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
const generated=spawnSync('python3',['-c','import json; from battle.scenario import terrain; print(json.dumps(list(terrain().values())))'],{encoding:'utf8'});
assert.equal(generated.status,0);
const cells=JSON.parse(generated.stdout),before=JSON.stringify(cells);
const context=vm.createContext({});
for(const path of ['static/cartography.js','static/map-view.js'])vm.runInContext(readFileSync(path,'utf8'),context);
context.cells=cells;
const data=vm.runInContext('BattleMap.geojson(cells,BattleMapView.coordinate)',context);
assert.equal(data.features.filter(f=>f.properties.kind==='surface').length,504);
assert.ok(data.features.some(f=>f.properties.kind==='contour'));
for(const f of data.features){
  assert.ok(['surface','contour'].includes(f.properties.kind));
  if(f.geometry.type==='Polygon')assert.deepEqual(f.geometry.coordinates[0][0],f.geometry.coordinates[0].at(-1));
  assert.ok(!JSON.stringify(f).includes('unit'));
}
const [a,b]=vm.runInContext('[BattleMapView.coordinate([24,26]),BattleMapView.coordinate([24+Math.sqrt(3)*25.5,26])]',context);
const distance=(b[0]-a[0])*Math.PI/180*6378137;
assert.ok(Math.abs(distance-50)<1e-6);
assert.equal(JSON.stringify(cells),before);
console.log('Map geometry passed: 504 terrain cells, closed rings, contours, 50 m spacing, unchanged input.');

// Missing WebGL/library must restore the interactive SVG rather than leave a blank map.
const nodes=new Map();
function node(id){if(!nodes.has(id))nodes.set(id,{classList:{add(){},remove(){}},appendChild(){},removeAttribute(){},textContent:''});return nodes.get(id);}
context.document={getElementById:node};context.clearTimeout=()=>{};
let fallbackCount=0;context.fallback=()=>fallbackCount++;
vm.runInContext('BattleMapView.init(cells,fallback)',context);
assert.equal(fallbackCount,1);
assert.equal(vm.runInContext('BattleMapView.active()',context),false);
assert.match(node('map-renderer').textContent,/fallback/);
console.log('Missing renderer fallback passed: SVG restored and failure explicitly labelled.');
