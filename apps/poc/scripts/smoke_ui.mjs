// Regression check for one-click, dialog-free reset. This is an isolated DOM harness,
// not a replacement for the recorded browser play-through.
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url);
const generated=spawnSync('python3',['-c','import json; from battle.scenario import create; from battle.engine import view; from battle.analysis import assess; from battle.adapters.rules import LittleRoundTopCatalog; v=view(create()); v["analysis"]=assess(v); print(json.dumps({"view":v,"map":LittleRoundTopCatalog().map()}))'],{cwd:root,encoding:'utf8'});
assert.equal(generated.status,0);
const initial={...JSON.parse(generated.stdout).view,game_id:'test-initial',mode:'scripted',messages:[],clock:{running:false,inflight:false,speed:10,remaining_seconds:30,speeds:[0.5,1,2,5,10,30,60]}};
const elements=new Map();
const element=id=>{if(!elements.has(id))elements.set(id,{id,classList:{toggle(){},add(){},remove(){}},addEventListener(){},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},scrollIntoView(){},value:'',innerHTML:'',textContent:''});return elements.get(id);};
const requests=[];
const context=vm.createContext({document:{getElementById:element},window:{matchMedia:()=>({matches:false})},console,BattleMapView:{active:()=>false,update(){},init(){}},setTimeout:()=>0,clearTimeout(){},
  confirm(){throw Error('Native dialogs must not be used');},
  fetch:async(path,options)=>{requests.push({path,options});return {ok:true,json:async()=>path==='/api/map'?{...JSON.parse(generated.stdout).map,cells:[]}:path==='/api/new'?{...initial,game_id:'test-fresh'}:initial};}});
vm.runInContext(readFileSync(new URL('../static/cartography.js',import.meta.url),'utf8'),context);
for(const file of ['api-client.js','troop-analysis.js','timeline.js','unit-icons.js'])vm.runInContext(readFileSync(new URL('../static/'+file,import.meta.url),'utf8'),context);
vm.runInContext(readFileSync(new URL('../static/app.js',import.meta.url),'utf8'),context);
await new Promise(resolve=>setImmediate(resolve));
assert.equal(element('clock').textContent,'16:30');
assert.match(element('battle-date').textContent,/2 July 1863/);
assert.match(element('battle-location').textContent,/Little Round Top.*Gettysburg/);
vm.runInContext('state.turn=4; renderTimeline()',context);
assert.equal(element('clock').textContent,'16:32');
vm.runInContext('state.turn=5; replay=true; renderTimeline()',context);
assert.match(element('replay-label').textContent,/Recorded.*16:32:30/);
assert.doesNotMatch(element('replay-label').textContent,/Revision|TURN/);
assert.equal(vm.runInContext("BattleTimeline.date({start_local:'1863-07-02T23:59:30'},30)",context),'Friday, 3 July 1863');
assert.equal(vm.runInContext("BattleTimeline.time({start_local:'1863-07-02T23:59:30'},30)",context),'00:00');
vm.runInContext('state.turn=0; replay=false',context);
console.log('Timeline passed: calendar, location, recorded timestamps and midnight rollover.');
assert.match(element('map').innerHTML,/skill 70 · energy 100 · morale 85/);
assert.match(element('unit-list').innerHTML,/Skill<b>70%/);
assert.match(element('unit-list').innerHTML,/Energy<b>100%/);
assert.match(element('map').innerHTML,/data-unit="U3"/);
assert.match(element('map').innerHTML,/INF \/ SC/);
const hiddenMetrics=vm.runInContext("UnitIcons.describe({id:'C1',composition:{type:'infantry'},strength_range:[24,48],skill:99,fatigue:1,morale:99},true)",context);
assert.equal(hiddenMetrics.strength,'24–48');
assert.equal(hiddenMetrics.skill,null);assert.equal(hiddenMetrics.energy,null);assert.equal(hiddenMetrics.morale,null);
assert.equal(vm.runInContext("UnitIcons.describe({fatigue:35}).energy",context),65);
vm.runInContext("state.units.push({...state.units[0],id:'UD1',name:'Detached formation',strength:20,initial:20,pos:[14,15]}); renderMap(); renderUnits()",context);
assert.match(element('map').innerHTML,/data-unit="UD1"/);
assert.match(element('map').innerHTML,/UD1 · infantry · 20 troops/);
vm.runInContext("state.units=state.units.filter(u=>u.id!=='UD1'); renderMap(); renderUnits()",context);
assert.doesNotMatch(element('map').innerHTML,/data-unit="UD1"/);
console.log('Unit counters passed: ratings, scout role, hidden enemy attributes and formation refresh.');

vm.runInContext("state={...state,clock:{...state.clock,speed:30}};liveState=state;renderControls()",context);
assert.equal(element('clock-speed').textContent,'30×');
await element('new-game').onclick();
assert.equal(requests.filter(r=>r.path==='/api/new').length,1);
assert.equal(element('clock-speed').textContent,'10×');  // The speed label follows the fresh server clock.
assert.match(element('toast').textContent,/Clock paused; previous battle archived/);
assert.equal(element('clock-toggle').disabled,false);
await element('clock-toggle').onclick();
assert.equal(requests.filter(r=>r.path==='/api/clock').length,1);
assert.equal(JSON.parse(requests.at(-1).options.body).command,'start');
await element('god-toggle').onclick();
assert.equal(element('god-toggle-state').textContent,'On');
await element('new-game').onclick();
assert.equal(requests.filter(r=>r.path==='/api/new').length,2);
assert.equal(element('god-toggle-state').textContent,'On');
await element('god-toggle').onclick();
assert.equal(element('god-toggle-state').textContent,'Off');
console.log('UI regression passed: one-click reset, retained God Mode selection, on/off toggle, clock start, no native dialog.');

vm.runInContext("selectUnit('U2')",context);
assert.match(element('unit-title').textContent,/U2/);
assert.match(element('unit-stats').innerHTML,/40/);
assert.equal(element('unit-split').disabled,false);
await element('unit-order').onclick();
element('unit-order-kind').value='hold';
await element('unit-action-form').onsubmit({preventDefault(){}});
const issued=requests.filter(r=>r.path==='/api/orders').at(-1);
assert.equal(JSON.parse(issued.options.body).orders[0].unit_id,'U2');
assert.equal(JSON.parse(issued.options.body).orders[0].stance,'hold');
await element('god-toggle').onclick();
vm.runInContext("selectUnit('U2')",context);
assert.equal(element('unit-order').disabled,true);
assert.equal(element('unit-split').disabled,true);
console.log('Unit panel passed: strength, selected-unit order routing and observer restrictions.');

await element('god-toggle').onclick();
vm.runInContext("selectUnit('U2')",context);
for(const [stance,target] of [['rest',null],['retreat',[1,2]],['resupply',null],['recon',[3,4]],['dig_in',null]]){
  await element('unit-order').onclick();element('unit-order-kind').value=stance;
  await element('unit-order-kind').onchange();
  if(target)vm.runInContext('destination='+JSON.stringify(target)+';renderControls()',context);
  assert.equal(element('unit-action-submit').disabled,false);
  assert.equal(element('send-order').disabled,true);
  await element('unit-action-form').onsubmit({preventDefault(){}});
  const order=JSON.parse(requests.filter(r=>r.path==='/api/orders').at(-1).options.body).orders[0];
  assert.deepEqual(order,{unit_id:'U2',stance,destination:target});
}
assert.match(element('unit-order-kind').innerHTML,/Reconnoiter/);
console.log('Order template UI passed: common catalog, destination requirements, correct payloads, no movement shortcut override.');

assert.match(element('map').innerHTML,/North farm lane/);assert.match(element('map').innerHTML,/Farmstead/);assert.match(element('map').innerHTML,/FIELDWORKS/);
console.log('Map feature UI passed: roads, buildings and fortifications rendered with the shared SVG overlay.');

vm.runInContext(`state.recommendations=[{id:'A1',unit_id:'U2',side:'union',status:'delivered',created_turn:1,received_turn:2,proposal:{unit_id:'U2',stance:'dig_in',destination:null},text:'General, improve this ground.',evidence:{ammo:1600,fatigue:0,morale:85}}];render();inspectAdvice('U2');`,context);
assert.match(element('map').innerHTML,/Recommendation from U2/);
assert.match(element('unit-list').innerHTML,/⚑ ADVICE/);
assert.match(element('unit-recommendations').innerHTML,/Dispatch suggested order/);
const respond=async response=>element('unit-recommendations').onclick({target:{closest:()=>({disabled:false,dataset:{adviceId:'A1',response}})}});
await respond('accept');
assert.equal(JSON.parse(requests.filter(r=>r.path==='/api/recommendations').at(-1).options.body).recommendation_id,'A1');
await respond('dismiss');
assert.equal(JSON.parse(requests.filter(r=>r.path==='/api/recommendations').at(-1).options.body).response,'dismiss');
await element('god-toggle').onclick();
const beforeAdviceRequests=requests.filter(r=>r.path==='/api/recommendations').length;
await respond('accept');
assert.equal(requests.filter(r=>r.path==='/api/recommendations').length,beforeAdviceRequests);
console.log('Recommendation UI passed: map/card flags, review panel, accept/dismiss payloads and observer guard.');

await element('god-toggle').onclick();
vm.runInContext("selectUnit('U3')",context);
await element('unit-analysis').onclick();
assert.equal(element('analysis-dialog').open,true);
assert.match(element('analysis-summary').innerHTML,/120/);
assert.equal(element('standing-unit').value,'U3');
assert.match(element('standing-recommendation').textContent,/Observe and screen/);
const beforeStanding=requests.filter(r=>r.path==='/api/standing-orders').length;
await element('standing-recommend').onclick();
assert.equal(element('standing-profile').value,'screen');
assert.equal(requests.filter(r=>r.path==='/api/standing-orders').length,beforeStanding);
await element('standing-form').onsubmit({preventDefault(){}});
assert.deepEqual(JSON.parse(requests.filter(r=>r.path==='/api/standing-orders').at(-1).options.body).instruction,{unit_id:'U3',profile_id:'screen'});
await element('god-toggle').onclick();
assert.equal(element('standing-send').disabled,true);
await element('standing-form').onsubmit({preventDefault(){}});
assert.equal(requests.filter(r=>r.path==='/api/standing-orders').length,beforeStanding+1);
await element('analysis-close').onclick();assert.equal(element('analysis-dialog').open,false);
console.log('Standing orders UI passed: prebattle assessment, per-unit recommendation draft, explicit dispatch and observer guard.');
