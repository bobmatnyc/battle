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
from battle.adapters.rules import RulesSimulation
from battle.services.queries import BattleQueries
from battle.comms import PROFILES
catalog = build_scenarios()
queries = BattleQueries(None, RulesSimulation(), None, assess=assess, present=present_view, scenarios=catalog)
opening = catalog.create("little-round-top")
# docs/research/65: what /api/replay returns for each view of the opening revision.
replays = {"union": queries.project(opening), "confederate": queries.project(opening, side="confederate"),
           "god": queries.project(opening, god=True)}
def shown(scenario_id):
    entry = catalog.resolve(scenario_id)
    v = view(catalog.create(scenario_id))
    shown_view = dict(v, voice_profile=present_view(v, entry)["voice_profile"])
    shown_view["scenario_brief"] = scenario_brief(entry, v["side"])
    shown_view["analysis"] = assess(v)
    return {"view": shown_view, "map": catalog.map(scenario_id)}
print(json.dumps({**shown("little-round-top"), "hougoumont": shown("hougoumont-north-gate"),
                  "concord": shown("concord-north-bridge"), "pegasus": shown("pegasus-bridge"),
                  "hill": shown("hill-223-patrol"), "replays": replays, "profiles": PROFILES,
                  # docs/research/75: the mock server lists the player catalog itself, in order.
                  "catalog": [{"id": i, "title": catalog.resolve(i).title} for i in catalog.ids()]}))`;
const generated=spawnSync('python3',['-c',fixtureScript],{cwd:root,encoding:'utf8'});
assert.equal(generated.status,0);
const initial={...JSON.parse(generated.stdout).view,game_id:'test-initial',mode:'scripted',messages:[],clock:{running:false,inflight:false,speed:10,remaining_seconds:30,speeds:[0.5,1,2,5,10,30,60]}};
const elements=new Map();
const element=id=>{if(!elements.has(id))elements.set(id,{id,classList:{toggle(){},add(){},remove(){}},addEventListener(){},setAttribute(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},scrollIntoView(){},value:'',innerHTML:'',textContent:''});return elements.get(id);};
const requests=[];
const hougoumont=JSON.parse(generated.stdout).hougoumont;
const concord=JSON.parse(generated.stdout).concord;  // docs/research/74
const replays=JSON.parse(generated.stdout).replays;
const replayed=path=>{const q=new URLSearchParams(path.split('?')[1]);return {...replays[q.get('view')==='god'?'god':q.get('side')||'union'],revision:+q.get('revision')};};
const hougoumontView={...hougoumont.view,game_id:'test-hougoumont',mode:'scripted',messages:[],clock:initial.clock};
const concordView={...concord.view,game_id:'test-concord',mode:'scripted',messages:[],clock:initial.clock};
// docs/research/75: Pegasus Bridge and Hill 223, served with their cells so water and woods are drawn.
const {pegasus,hill,catalog:playerCatalog}=JSON.parse(generated.stdout);
const pegasusView={...pegasus.view,game_id:'test-pegasus',mode:'scripted',messages:[],clock:initial.clock};
const hillView={...hill.view,game_id:'test-hill',mode:'scripted',messages:[],clock:initial.clock};
const WITH_CELLS={'concord-north-bridge':[concord.map,concordView],'pegasus-bridge':[pegasus.map,pegasusView],
  'hill-223-patrol':[hill.map,hillView]};
let served='little-round-top';  // Which scenario the mock server is playing.
let completed=false;  // docs/research/65: the opponent's replay unlocks only after the battle.
const liveInitial=()=>completed?{...initial,status:'complete',winner:'union',reason:'The Union held out until the scenario deadline.'}:initial;
const setCells=[];
const context=vm.createContext({document:{getElementById:element},window:{matchMedia:()=>({matches:false})},console,BattleMapView:{active:()=>false,update(){},init(){},frame:()=>({x0:0,y0:0,x1:1080,y1:840}),setCells(cells){setCells.push(cells);}},setTimeout:()=>0,clearTimeout(){},
  confirm(){throw Error('Native dialogs must not be used');},
  fetch:async(path,options)=>{
    requests.push({path,options});
    if(path==='/api/new'&&options?.body){const asked=JSON.parse(options.body).scenario;served=['hougoumont-north-gate',...Object.keys(WITH_CELLS)].includes(asked)?asked:'little-round-top';}
    const hg=served==='hougoumont-north-gate',cells=WITH_CELLS[served];
    const catalog={default:'little-round-top',scenarios:playerCatalog};
    if(path.startsWith('/api/history'))return {ok:true,json:async()=>[{revision:0,turn:0},{revision:1,turn:0}]};
    if(path.startsWith('/api/replay'))return {ok:true,json:async()=>replayed(path)};
    // Concord's, Pegasus's and Hill 223's maps keep their cells, so water, woods and bridges are drawn (docs/research/74, 75).
    return {ok:true,json:async()=>path==='/api/map'?(cells?cells[0]:{...(hg?hougoumont:JSON.parse(generated.stdout)).map,cells:[]}):path==='/api/scenarios'?catalog:cells?cells[1]:hg?hougoumontView:path==='/api/new'?{...initial,game_id:'test-fresh'}:liveInitial()};}});
vm.runInContext(readFileSync(new URL('../static/cartography.js',import.meta.url),'utf8'),context);
for(const file of ['api-client.js','order-wording.js','troop-analysis.js','scenario-picker.js','timeline.js','unit-icons.js','feature-sources.js','map-features.js'])vm.runInContext(readFileSync(new URL('../static/'+file,import.meta.url),'utf8'),context);
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
// Little Round Top labels under poc-13: the player's side comes from the view, not a literal.
const notice=element('rules-notice');notice.classList={...notice.classList,toggle(name,on){notice.hiddenState=on;}};
vm.runInContext('render()',context);
assert.equal(vm.runInContext('state.rules',context),'poc-13');
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
vm.runInContext("Object.assign(state,{rules:'poc-13',status:'active',winner:null,reason:null});render()",context);
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
// docs/research/72: footprints at the map's scale, and every mark's status in the legend.
assert.match(element('map').innerHTML,/<rect class="footprint"/);
assert.match(element('feature-legend').innerHTML,/data-feature="farmstead".*legend-status-illustrative/);
console.log('Map feature UI passed: roads, footprints and fortifications rendered with the shared SVG overlay; legend lists each status.');
// Grid off and on: the toggle sets only the no-grid class; the feature layer is drawn unchanged.
function featuresSurviveGridToggle(){
  const map=element('map'),classes=map.classList,toggles=[];
  map.classList={...classes,toggle(name,on){toggles.push([name,on]);}};
  const layer=vm.runInContext('renderFeatures()',context);  // The page's own call, with its scale and sources.
  assert.match(layer,/<path class="road-casing" d="M/);
  for(const gridOff of [true,false]){
    element('hex-toggle').onclick();
    assert.deepEqual(toggles.at(-1),['no-grid',gridOff]);
    assert.ok(map.innerHTML.includes(layer),`feature layer with the grid ${gridOff?'off':'on'}`);
  }
  map.classList=classes;
}
featuresSurviveGridToggle();
console.log('Grid toggle passed: Little Round Top roads and buildings drawn with the hex grid off and on.');

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
// bt-T11: a standing order may go to the command's own detachment, so voice is named with the courier.
assert.equal(element('standing-status').textContent,'Changing a selection is a draft. Dispatch sends it by voice or foot courier.');
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

// bt-T11: the send button, its tooltip, the map tip and the mission help line name the viewing side's own
// means, from command.profile only; an order to the command's own detachment stays a local order.
function wording(send,title,help){
  const own=vm.runInContext('state.command.unit_id',context);
  const other=vm.runInContext('state.units.find(u=>u.id!==state.command.unit_id).id',context);
  const observing=vm.runInContext('godMode',context);  // The map tip names the means in the commander view only.
  vm.runInContext(`godMode=false;selectUnit(${JSON.stringify(other)});destination=[0,0];renderControls();renderObserver()`,context);
  assert.equal(element('send-order').textContent,send,other);
  assert.equal(element('send-order').title,title,other);
  assert.equal(element('order-means').textContent,help);
  assert.ok(element('map-tip').textContent.endsWith(` · ${send.replace('Dispatch','dispatch').replace(' ↗','')}.`),element('map-tip').textContent);
  vm.runInContext(`selectUnit(${JSON.stringify(own)});destination=[0,0];renderControls()`,context);
  assert.equal(element('send-order').textContent,'Give local order ↗',own);
  assert.match(element('map-tip').textContent,/give a local order\.$/);
  vm.runInContext(`godMode=${observing};selected=null;destination=null;renderMap();renderControls()`,context);
}
wording('Dispatch by foot courier ↗','1863 · voice / foot courier: orders go by foot courier.','Movement orders travel by foot courier.');
// Every profile the engine defines, read from comms.PROFILES: the 1944, 1918 and Roman profiles never say runner alone.
const profiles=JSON.parse(generated.stdout).profiles;
const wordingOf=(fn,id)=>vm.runInContext(`BattleOrderWording.${fn}(${JSON.stringify(profiles[id])})`,context);
assert.deepEqual(Object.fromEntries(Object.keys(profiles).map(id=>[id,wordingOf('send',id)])),{
  'civil-war-courier-v1':'Dispatch by foot courier ↗','napoleonic-courier-v1':'Dispatch by foot runner ↗',
  'colonial-1775-voice-v1':'Dispatch by voice or runner ↗','wwii-1944-radio-v1':'Dispatch by radio, voice or runner ↗',
  'wwi-1918-voice-runner-v1':'Dispatch by voice or runner ↗','roman-republic-signal-v1':'Dispatch by voice or runner ↗',
  'roman-216-v1':'Dispatch by voice or mounted messenger ↗','carthage-216-v1':'Dispatch by voice or mounted messenger ↗'});
for(const id of ['wwii-1944-radio-v1','wwi-1918-voice-runner-v1','roman-republic-signal-v1','roman-216-v1'])
  for(const fn of ['send','tooltip','help','tip','standing'])
    assert.doesNotMatch(wordingOf(fn,id),/by runner\b/,`${id} ${fn}: ${wordingOf(fn,id)}`);
assert.equal(wordingOf('standing','roman-republic-signal-v1'),'Changing a selection is a draft. Dispatch sends it by voice or runner.');
// A view without a command profile is a legacy headquarters, whose orders went by runner.
assert.equal(vm.runInContext('BattleOrderWording.send(undefined)',context),'Dispatch by runner ↗');
console.log("Order wording passed: send button, tooltip, map tip, help line and standing-order note from the side's own command profile, for every profile.");

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

// docs/research/65: while the battle is active, Replay offers the player's side and God only.
const lastReplay=()=>requests.filter(r=>r.path.startsWith('/api/replay')).at(-1).path;
const chooseReplayView=async value=>{element('replay-view').value=value;await element('replay-view').onchange();};
const commandsBefore=requests.filter(r=>r.options?.method==='POST'&&r.path!=='/api/clock').length;
await element('history-toggle').onclick();
assert.equal(vm.runInContext('state.status',context),'active');
assert.match(element('replay-view').innerHTML,/value="union">Union commander.*value="god">God view/);
assert.doesNotMatch(element('replay-view').innerHTML,/confederate|Confederate/);
await element('live-view').onclick();
// A completed battle: Replay as the Union, then the Confederates, then God, then the Union again.
completed=true;
await element('history-toggle').onclick();
assert.equal(vm.runInContext('liveState.status',context),'complete');
assert.equal(vm.runInContext('replay',context),true);
assert.equal(lastReplay(),'/api/replay?game_id=test-initial&revision=0');  // The player's own view by default.
assert.match(element('replay-view').innerHTML,/value="union">Union commander.*value="confederate">Confederate commander.*value="god">God view/);
assert.equal(element('replay-view').value,'union');
await chooseReplayView('confederate');
assert.equal(lastReplay(),'/api/replay?game_id=test-initial&revision=0&side=confederate');
assert.equal(vm.runInContext('state.side',context),'confederate');
assert.equal(element('god-toggle-state').textContent,'Off');
assert.match(element('clock-status').textContent,/recorded Confederate commander view/);
assert.match(element('unit-list').innerHTML,/data-unit="C1"/);
assert.doesNotMatch(element('unit-list').innerHTML,/data-unit="U\d"/);  // No Union unit the Confederates have not seen.
assert.doesNotMatch(element('map').innerHTML,/data-unit="U\d"/);
assert.equal(element('mission-title').textContent,replays.confederate.scenario_brief.mission.title);
assert.equal(element('replay-view').value,'confederate');
await chooseReplayView('god');
assert.equal(lastReplay(),'/api/replay?game_id=test-initial&revision=0&view=god');
assert.equal(element('god-toggle-state').textContent,'On');
assert.match(element('unit-list').innerHTML,/data-unit="U1"/);assert.match(element('unit-list').innerHTML,/data-unit="C1"/);
await chooseReplayView('union');
assert.equal(lastReplay(),'/api/replay?game_id=test-initial&revision=0');
assert.equal(element('god-toggle-state').textContent,'Off');
assert.doesNotMatch(element('unit-list').innerHTML,/data-unit="C\d"/);
await chooseReplayView('confederate');
element('replay-slider').value='1';await element('replay-slider').oninput({target:element('replay-slider')});
assert.equal(lastReplay(),'/api/replay?game_id=test-initial&revision=1&side=confederate');  // Seeking keeps the view.
await element('live-view').onclick();
assert.equal(vm.runInContext('replay',context),false);
assert.equal(requests.at(-1).path,'/api/state');  // Live is the player's commander view again.
assert.equal(vm.runInContext('state.side',context),'union');
assert.equal(element('replay-view').innerHTML,'');
// Return to live from a God replay keeps God Mode on: the live desk opens in God view, as the switch shows.
await element('history-toggle').onclick();
await chooseReplayView('god');
await element('live-view').onclick();
assert.equal(vm.runInContext('replay',context),false);
assert.equal(requests.at(-1).path,'/api/state?view=god');
assert.equal(element('god-toggle-state').textContent,'On');
await element('god-toggle').onclick();
assert.equal(requests.at(-1).path,'/api/state');
assert.equal(element('god-toggle-state').textContent,'Off');
assert.equal(requests.filter(r=>r.options?.method==='POST'&&r.path!=='/api/clock').length,commandsBefore);  // Replay sent no command.
completed=false;vm.runInContext(`state=liveState=${JSON.stringify(initial)};render()`,context);
console.log('Replay sides passed: player and God only while active; after the battle Union, Confederate and God views by selector, seek keeps the view, live returns to the player, God replay returns to live God view, no commands or dialogs.');

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
// docs/research/72: the compound's walls and the north gate, open as briefed, and the gate's sourced status.
assert.match(element('map').innerHTML,/data-feature="hougoumont#walls".*class="compound-wall"/);
assert.match(element('map').innerHTML,/data-feature="hougoumont#north-gate" data-status="sourced" data-state="open"/);
assert.match(element('feature-legend').innerHTML,/data-feature="hougoumont#north-gate".*Closing the Gates at Hougoumont/);
featuresSurviveGridToggle();
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
wording('Dispatch by foot runner ↗','1815 · voice / foot runner: orders go by foot runner.','Movement orders travel by foot runner.');  // bt-T11
console.log('Hougoumont UI passed: selection by POST /api/new, terrain refresh, mission, side names, objective, outcomes, voice and no opponent mission in the page.');

// docs/research/74: Concord, the third player scenario, through the same picker and Reset.
assert.match(element('scenario-select').innerHTML,/value="concord-north-bridge"/);
element('scenario-select').value='concord-north-bridge';
element('scenario-select').onchange();
const concordMapRequests=requests.filter(r=>r.path==='/api/map').length;
await element('new-game').onclick();
assert.equal(JSON.parse(requests.filter(r=>r.path==='/api/new').at(-1).options.body).scenario,'concord-north-bridge');
assert.equal(requests.filter(r=>r.path==='/api/map').length,concordMapRequests+1);
assert.equal(vm.runInContext('state.game_id',context),'test-concord');
assert.equal(context.document.title,'battle · Concord North Bridge');
assert.equal(element('campaign-line').textContent,'CONCORD · 19 APRIL 1775');
assert.equal(element('clock').textContent,'09:25');
assert.match(element('battle-date').textContent,/19 April 1775/);
assert.match(element('battle-location').textContent,/North Bridge · Concord, Massachusetts/);
for(const id of ['clock','battle-date','battle-location','campaign-line','clock-status'])
  assert.doesNotMatch(element(id).textContent,/\bturn\b|revision/i,id);
assert.equal(element('mission-title').textContent,'Clear the bridge');
assert.match(element('mission-text').innerHTML,/do not fire unless first fired upon.*<strong>09:35<\/strong>/);
assert.equal(element('objective-key').textContent,'BRIDGE');
assert.match(element('map').innerHTML,/class="place-label">North Bridge</);
assert.match(element('map').innerHTML,/r="53"/);  // The bridge ring: hold-objective, radius 1.
assert.match(element('map').innerHTML,/#b9d3e3/);  // The river's water cells.
assert.match(element('map').innerHTML,/data-feature="muster-road"/);
assert.match(element('map').innerHTML,/data-feature="town-road"/);
assert.match(element('map').innerHTML,/data-feature="crossing:12,10"[^>]*data-status="reconstructed"/);
assert.match(element('feature-legend').innerHTML,/data-feature="crossing:12,10".*North Bridge/);
assert.equal(vm.runInContext('state.voice_profile',context),'colonial-1775-en-v1');
// The empty dispatch list names no address and no detachment count (Concord has four companies).
assert.doesNotMatch(element('dispatches').innerHTML,/General|Three detachments/);
assert.match(element('dispatches').innerHTML,/The command awaits your orders\./);
// An order from the desk: the Acton company to the bridge approach.
vm.runInContext("selectUnit('P1')",context);
await element('unit-order').onclick();element('unit-order-kind').value='move';await element('unit-order-kind').onchange();
vm.runInContext('destination=[11,10];renderControls()',context);
await element('unit-action-form').onsubmit({preventDefault(){}});
assert.deepEqual(JSON.parse(requests.filter(r=>r.path==='/api/orders').at(-1).options.body).orders,[{unit_id:'P1',stance:'move',destination:[11,10]}]);
// Report ages follow the view's seconds_per_turn, not a fixed 30 s.
vm.runInContext("state.seconds_per_turn=60;state.turn=3;state.units[0].observed_turn=1;state.contacts=[{id:'K1',side:'british',pos:[13,10],age:2,observed_turn:1,received_turn:1,confidence:'low',identification:{type:{observer_role:'line',observed_turn:1}}}];renderUnits();renderContacts();selectUnit('P1')",context);
assert.match(element('unit-list').innerHTML,/120s AGO/);
assert.match(element('unit-report-age').textContent,/120s old/);
assert.match(element('contact-list').innerHTML,/120s ago.*120s old/);
vm.runInContext("state.last_commander_source='scripted';renderControls()",context);
assert.match(element('ai-status').textContent,/plans every 180s/);  // Three intervals.
wording('Dispatch by voice or runner ↗','1775 · voice / runner: orders go by voice or runner, as distance allows.',
  'Movement orders travel by voice or runner.');  // bt-T11
vm.runInContext(`state=liveState=${JSON.stringify(concordView)};render()`,context);
vm.runInContext("Object.assign(state,{status:'complete',winner:'provincial',reason:'The Provincials held the bridge.'});render()",context);
assert.match(element('outcome').innerHTML,/The bridge is carried\..*The Provincials held the bridge/);
vm.runInContext("state.winner='british';render()",context);
assert.match(element('outcome').innerHTML,/The regulars hold the bridge\./);
console.log('Concord UI passed: picker and Reset, 19 April 1775 local header, brief, water, roads and the North Bridge drawn, an order sent, report ages from seconds_per_turn, outcome headlines.');

// docs/research/75: Pegasus Bridge and Hill 223, the fourth and fifth player scenarios, through the same
// picker and Reset: the local 1944 and 1918 header, the brief, the features drawn, an order, the headlines.
async function switchTo(id,gameId,title){
  assert.match(element('scenario-select').innerHTML,new RegExp(`value="${id}"`));
  element('scenario-select').value=id;
  element('scenario-select').onchange();
  const mapRequests=requests.filter(r=>r.path==='/api/map').length;
  await element('new-game').onclick();
  assert.equal(JSON.parse(requests.filter(r=>r.path==='/api/new').at(-1).options.body).scenario,id);
  assert.equal(requests.filter(r=>r.path==='/api/map').length,mapRequests+1);
  assert.equal(vm.runInContext('state.game_id',context),gameId);
  assert.equal(context.document.title,`battle · ${title}`);
  for(const field of ['clock','battle-date','battle-location','campaign-line','clock-status'])
    assert.doesNotMatch(element(field).textContent,/\bturn\b|revision/i,field);
}
async function orderFromDesk(unit,destination){
  vm.runInContext(`selectUnit(${JSON.stringify(unit)})`,context);
  await element('unit-order').onclick();element('unit-order-kind').value='move';await element('unit-order-kind').onchange();
  vm.runInContext(`destination=${JSON.stringify(destination)};renderControls()`,context);
  await element('unit-action-form').onsubmit({preventDefault(){}});
  assert.deepEqual(JSON.parse(requests.filter(r=>r.path==='/api/orders').at(-1).options.body).orders,[{unit_id:unit,stance:'move',destination}]);
}
const literal=text=>text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
function headlines(view,winner,loser,texts){
  vm.runInContext(`state=liveState=${JSON.stringify(view)};render()`,context);
  vm.runInContext(`Object.assign(state,{status:'complete',winner:${JSON.stringify(winner)},reason:'Reason from the server.'});render()`,context);
  assert.match(element('outcome').innerHTML,new RegExp(`${literal(texts.win)}.*Reason from the server`));
  vm.runInContext(`state.winner=${JSON.stringify(loser)};render()`,context);
  assert.match(element('outcome').innerHTML,new RegExp(literal(texts.loss)));
}

await switchTo('pegasus-bridge','test-pegasus','Pegasus Bridge');
assert.equal(element('campaign-line').textContent,'NORMANDY · 6 JUNE 1944');
assert.equal(element('clock').textContent,'00:25');
assert.match(element('battle-date').textContent,/6 June 1944/);
assert.match(element('battle-location').textContent,/Caen Canal bridge · Bénouville, Normandy/);
assert.equal(element('mission-title').textContent,'Seize the canal bridge');
assert.match(element('mission-text').innerHTML,/24 Platoon.*Neilson.*<strong>03:25<\/strong>.*Ham/);
// bt-D09 default: the brief tells the player before play that the bridge is blown at 00:27:30.
assert.match(element('mission-text').innerHTML,/Note: on this entry the bridge is blown at <strong>00:27:30<\/strong> whatever you order, because the charge timings are authored, not sourced\.$/);
assert.equal(element('objective-key').textContent,'BRIDGE');
assert.match(element('map').innerHTML,/class="place-label">Caen Canal bridge</);
assert.match(element('map').innerHTML,/#b9d3e3/);  // The canal and the Orne.
assert.match(element('map').innerHTML,/#d7e3cf/);  // The marsh between them.
// Both bridges: the canal bridge as known (wired with charges), the Orne bridge from its crossing cell.
assert.match(element('map').innerHTML,/data-feature="canal-bridge"[^>]*data-status="reconstructed"/);
assert.match(element('map').innerHTML,/class="bridge-charges"/);
assert.match(element('map').innerHTML,/Caen Canal bridge · charges/);
assert.match(element('map').innerHTML,/data-feature="crossing:19,10"[^>]*data-status="sourced"/);
for(const road of ['benouville-road','bridges-road','ranville-road'])assert.match(element('map').innerHTML,new RegExp(`data-feature="${road}"`));
assert.equal(vm.runInContext('state.voice_profile',context),'wwii-1944-en-v1');
await orderFromDesk('D24',[9,10]);  // 24 Platoon, with the sappers, onto the bridge.
wording('Dispatch by radio, voice or runner ↗','1944 · radio / voice / runner: orders go by radio, voice or runner, as distance allows.',
  'Movement orders travel by radio, voice or runner.');  // bt-T11
headlines(pegasusView,'british','german',pegasus.view.scenario_brief.outcomes);
console.log('Pegasus UI passed: picker and Reset, 6 June 1944 local header, brief, canal, marsh, roads, the canal bridge with its charges and the Orne bridge drawn, an order sent, outcome headlines.');

await switchTo('hill-223-patrol','test-hill','Hill 223');
assert.equal(element('campaign-line').textContent,'ARGONNE · 8 OCTOBER 1918');
assert.equal(element('clock').textContent,'06:45');
assert.match(element('battle-date').textContent,/8 October 1918/);
assert.match(element('battle-location').textContent,/Hill southwest of Hill 223 · Châtel-Chéhéry, Argonne/);
assert.equal(element('mission-title').textContent,'Bring the patrol back');
assert.match(element('mission-text').innerHTML,/Acting Sergeant Early.*runner.*5 men and one prisoner.*<strong>10:30<\/strong>/);
assert.equal(element('objective-key').textContent,'SHACK');
assert.match(element('map').innerHTML,/class="place-label">Command post at the shack</);
assert.match(element('map').innerHTML,/data-feature="old-trench"[^>]*data-status="sourced"/);
assert.equal(vm.runInContext('state.voice_profile',context),'wwi-1918-en-v1');
await orderFromDesk('A3',[16,6]);  // The right of the company line.
wording('Dispatch by voice or runner ↗','1918 · voice / runner: orders go by voice or runner, as distance allows.',
  'Movement orders travel by voice or runner.');  // bt-T11
headlines(hillView,'american','german',hill.view.scenario_brief.outcomes);
console.log('Hill 223 UI passed: picker and Reset, 8 October 1918 local header, brief, the shack objective and the old trench drawn, an order sent, outcome headlines.');
