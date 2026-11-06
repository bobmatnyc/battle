// Regression check for one-click, dialog-free reset. This is an isolated DOM harness,
// not a replacement for the recorded browser play-through.
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url);
// The views carry the same scenario_brief the server adds in BattleQueries.project.
const fixtureScript=`
import json
from battle.analysis import assess
from battle.bootstrap import build_scenarios
from battle.engine import view
from battle.presentation import present_view, scenario_brief
catalog = build_scenarios()
def shown(scenario_id):
    entry = catalog.resolve(scenario_id)
    v = view(catalog.create(scenario_id))
    shown_view = dict(v, voice_profile=present_view(v, entry)["voice_profile"])
    shown_view["scenario_brief"] = scenario_brief(entry, v["side"])
    shown_view["analysis"] = assess(v)
    return {"view": shown_view, "map": catalog.map(scenario_id)}
print(json.dumps({**shown("little-round-top"), "hougoumont": shown("hougoumont-north-gate")}))`;
const generated=spawnSync('python3',['-c',fixtureScript],{cwd:root,encoding:'utf8'});
assert.equal(generated.status,0);
const initial={...JSON.parse(generated.stdout).view,game_id:'test-initial',mode:'scripted',messages:[],clock:{running:false,inflight:false,speed:10,remaining_seconds:30,speeds:[0.5,1,2,5,10,30,60]}};
const elements=new Map();
const element=id=>{if(!elements.has(id))elements.set(id,{id,classList:{toggle(){},add(){},remove(){}},addEventListener(){},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},scrollIntoView(){},value:'',innerHTML:'',textContent:''});return elements.get(id);};
const requests=[];
const hougoumont=JSON.parse(generated.stdout).hougoumont;
const hougoumontView={...hougoumont.view,game_id:'test-hougoumont',mode:'scripted',messages:[],clock:initial.clock};
let served='little-round-top';  // Which scenario the mock server is playing.
const setCells=[];
const context=vm.createContext({document:{getElementById:element},window:{matchMedia:()=>({matches:false})},console,BattleMapView:{active:()=>false,update(){},init(){},setCells(cells){setCells.push(cells);}},setTimeout:()=>0,clearTimeout(){},
  confirm(){throw Error('Native dialogs must not be used');},
  fetch:async(path,options)=>{
    requests.push({path,options});
    if(path==='/api/new'&&options?.body)served=JSON.parse(options.body).scenario==='hougoumont-north-gate'?'hougoumont-north-gate':'little-round-top';
    const hg=served==='hougoumont-north-gate';
    const catalog={default:'little-round-top',scenarios:[{id:'little-round-top',title:'Little Round Top'},{id:'hougoumont-north-gate',title:'Hougoumont: the north gate'}]};
    return {ok:true,json:async()=>path==='/api/map'?{...(hg?hougoumont:JSON.parse(generated.stdout)).map,cells:[]}:path==='/api/scenarios'?catalog:hg?hougoumontView:path==='/api/new'?{...initial,game_id:'test-fresh'}:initial};}});
vm.runInContext(readFileSync(new URL('../static/cartography.js',import.meta.url),'utf8'),context);
for(const file of ['api-client.js','troop-analysis.js','scenario-picker.js','timeline.js','unit-icons.js'])vm.runInContext(readFileSync(new URL('../static/'+file,import.meta.url),'utf8'),context);
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
// Little Round Top labels under poc-11: the player's side comes from the view, not a literal.
const notice=element('rules-notice');notice.classList={...notice.classList,toggle(name,on){notice.hiddenState=on;}};
vm.runInContext('render()',context);
assert.equal(vm.runInContext('state.rules',context),'poc-11');
assert.equal(notice.hiddenState,true);
assert.match(element('map').innerHTML,/class="place-label">Little Round Top</);
assert.match(element('map').innerHTML,/SUMMIT OBJECTIVE/);
assert.match(element('map').innerHTML,/fill="#244f76" stroke="#f0e2b7"\/><text[^>]*>YOU</);
vm.runInContext("state.status='complete';state.winner='union';state.reason='The Union held out until the scenario deadline.';render()",context);
assert.match(element('outcome').innerHTML,/The line holds\..*The Union held out/);
vm.runInContext("state.winner='confederate';render()",context);
assert.match(element('outcome').innerHTML,/The summit is lost\./);
vm.runInContext("state.winner='draw';render()",context);
assert.match(element('outcome').innerHTML,/The battle ends in a draw\./);
vm.runInContext("state.rules='poc-8';render()",context);
assert.equal(notice.hiddenState,false);
vm.runInContext("Object.assign(state,{rules:'poc-11',status:'active',winner:null,reason:null});render()",context);
console.log('Side labels passed: Little Round Top map labels, player HQ, outcome headlines and earlier-rules notice.');
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

// Scenario text comes from the game's brief. Little Round Top first: the copy the desk always showed.
await element('god-toggle').onclick();  // God Mode off again.
vm.runInContext(`state=liveState=${JSON.stringify(initial)};render()`,context);
assert.equal(element('mission-title').textContent,'Defend the summit');
assert.equal(element('mission-text').innerHTML,'Keep an effective formation in the summit hex or the six hexes around it (the dashed ring) until <strong>17:00</strong>. If Confederate troops hold that ground for 90 seconds with no effective Union formation there, the battle ends at once in their favor, even before 17:00.');
assert.equal(element('brief-kicker').textContent,'THE UNION LEFT FLANK');
assert.equal(element('brief-tagline').textContent,'Hold the high ground.');
assert.equal(element('brief-subhead').textContent,'You command the Union. The computer commands the Confederate advance.');
assert.equal(element('campaign-line').textContent,'GETTYSBURG · 2 JULY 1863');
assert.equal(element('conditions').textContent,'SUMMER · DRY · CLEAR');
assert.equal(element('objective-key').textContent,'SUMMIT');
assert.match(element('map').innerHTML,/r="53"/);  // The summit ring.
assert.equal(element('map-reference').href,'https://www.loc.gov/item/99447491/');
assert.equal(vm.runInContext('state.voice_profile',context),'civil-war-en-v1');
assert.match(element('scenario-select').innerHTML,/value="little-round-top".*value="hougoumont-north-gate"/);
console.log('Scenario text passed: Little Round Top mission, headings, objective and voice come from the brief unchanged.');

// New-game selection: pick Hougoumont, Reset, and the whole desk follows the new game.
element('scenario-select').value='hougoumont-north-gate';
element('scenario-select').onchange();
const mapRequestsBefore=requests.filter(r=>r.path==='/api/map').length;
await element('new-game').onclick();
assert.equal(JSON.parse(requests.filter(r=>r.path==='/api/new').at(-1).options.body).scenario,'hougoumont-north-gate');
assert.equal(requests.filter(r=>r.path==='/api/map').length,mapRequestsBefore+1);  // Terrain follows the scenario.
assert.equal(setCells.length,1);
assert.equal(vm.runInContext('state.game_id',context),'test-hougoumont');
assert.equal(context.document.title,'battle · Hougoumont: the north gate');
assert.equal(element('campaign-line').textContent,'WATERLOO · 18 JUNE 1815');
assert.equal(element('campaign-title').textContent,'Hougoumont: the north gate');
assert.equal(element('brief-kicker').textContent,'THE NORTH GATE');
assert.equal(element('brief-subhead').textContent,'You command the Allied garrison. The computer commands the French assault.');
assert.equal(element('mission-title').textContent,'Hold the farm');
assert.match(element('mission-text').innerHTML,/inside the walls of Hougoumont until <strong>11:50<\/strong>.*north gate open.*180 seconds/);
assert.equal(element('clock').textContent,'11:20');
assert.match(element('battle-date').textContent,/18 June 1815/);
assert.match(element('battle-location').textContent,/Hougoumont.*Waterloo/);
assert.equal(element('objective-key').textContent,'FARM');
assert.equal(element('map-reference').href,'');  // Authored layout: no historical map to link.
assert.match(element('map').innerHTML,/class="place-label">Hougoumont farm</);
assert.match(element('map').innerHTML,/COMPOUND OBJECTIVE/);
assert.doesNotMatch(element('map').innerHTML,/r="53"/);  // A compound is not a ring of hexes.
assert.match(element('map').innerHTML,/Hougoumont chateau and farm/);  // The building feature is drawn.
assert.equal(vm.runInContext('state.voice_profile',context),'napoleonic-en-v1');
assert.match(element('toast').textContent,/Battle reset to 11:20/);
assert.equal(element('scenario-select').value,'hougoumont-north-gate');
vm.runInContext("Object.assign(state,{status:'complete',winner:'allied',reason:'The Allied garrison held the farm until the scenario deadline.'});render()",context);
assert.match(element('outcome').innerHTML,/Hougoumont holds\..*Allied garrison held/);
vm.runInContext("state.winner='french';render()",context);
assert.match(element('outcome').innerHTML,/The farm is lost\./);
vm.runInContext("state.winner='draw';render()",context);
assert.match(element('outcome').innerHTML,/The battle ends in a draw\./);
// Only the player's mission reaches the page: nothing of the French mission, no Union or Confederate wording.
const frenchMission=/assault group west|pass men through/;
for(const [id,el] of elements){
  for(const text of [el.innerHTML,el.textContent]){
    assert.doesNotMatch(String(text),frenchMission,id);
    // The scenario list names every scenario by design; CSS class names are not text.
    // The hidden God Mode panels keep the last observer render from the Little Round Top run above.
    if(id!=='scenario-select'&&!id.startsWith('god-'))assert.doesNotMatch(String(text).replace(/class="[^"]*"/g,''),/Union|Confederate|Little Round Top|summit/i,id);
  }
}
console.log('Hougoumont UI passed: selection by POST /api/new, terrain refresh, mission, side names, objective, outcomes, voice and no opponent mission in the page.');
