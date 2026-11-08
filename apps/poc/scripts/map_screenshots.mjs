// Map-feature screenshot harness (docs/research/72 §6). Offline, localhost only, no credentials.
// Starts an offline POC on a temporary SQLite file and a free port and a headless Chrome/Chromium
// with its own profile, then captures the command map for every player scenario (Little Round
// Top, Hougoumont, Concord, Pegasus Bridge, Hill 223) at the fit view and zoomed in, each with
// the hex grid on and off, plus the feature legend; and plays Concord (docs/research/74), Pegasus
// Bridge and Hill 223 (docs/research/75) on the desk to a result: header, the marks drawn, an
// order accepted, the outcome headline and reason. docs/research/75: no headless entry with
// drawn marks remains, so the read-only renders of docs/research/72 §6 are gone.
// Usage: node scripts/map_screenshots.mjs <output dir>
// Exit 0: passed. 1: failed. 3: BLOCKED, no runnable browser (never a pass).
// Fault injection: MAP_HARNESS_FAULT=throw|sigint (after the page opens), MAP_HARNESS_POC_READY
// (text the POC never prints), MAP_HARNESS_DEADLINE_MS. Every exit path stops the POC and the
// browser's process group, removes the profile and database directory, and verifies both are gone.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync} from 'node:fs';
import {createServer} from 'node:net';
import {homedir, tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
const POC=new URL('../',import.meta.url).pathname;
const BLOCKED=3;
const out=resolve(process.argv[2]||'');
if(!process.argv[2]){console.error('usage: node scripts/map_screenshots.mjs <output dir>');process.exit(2);}
mkdirSync(out,{recursive:true});
const FAULT=process.env.MAP_HARNESS_FAULT||'';
const READY=new RegExp(process.env.MAP_HARNESS_POC_READY||'Battle ready');
const DEADLINE_MS=Number(process.env.MAP_HARNESS_DEADLINE_MS||180000);
const CONCORD='concord-north-bridge';

function findBrowser(){
  if(process.env.BATTLE_BROWSER)return existsSync(process.env.BATTLE_BROWSER)?process.env.BATTLE_BROWSER:null;
  const found=['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/chromium','/usr/bin/chromium-browser','/usr/bin/google-chrome'];
  const pw=join(homedir(),'Library/Caches/ms-playwright');
  if(existsSync(pw))for(const d of readdirSync(pw).filter(d=>/^chromium-\d+$/.test(d)).sort().reverse())
    for(const sub of ['chrome-mac-arm64','chrome-mac'])found.push(join(pw,d,sub,'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'));
  return found.find(p=>existsSync(p))||null;
}
const freePort=()=>new Promise(done=>{const s=createServer();s.listen(0,'127.0.0.1',()=>{const {port}=s.address();s.close(()=>done(port));});});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
// No provider credentials reach the POC; --offline uses the scripted commander.
function cleanEnv(){const env={};for(const [k,v] of Object.entries(process.env))if(!/OPENROUTER|API_KEY|TOKEN|SECRET/i.test(k))env[k]=v;return env;}
function waitFor(child,pattern,ms,label){
  return new Promise((done,failed)=>{
    let log='';const timer=setTimeout(()=>failed(new Error(`${label} not ready in ${ms} ms:\n${log.slice(-400)}`)),ms);
    const read=b=>{log+=b;const m=pattern.exec(log);if(m){clearTimeout(timer);child.stdout?.off('data',read);child.stderr?.off('data',read);done(m);}};
    child.stdout?.on('data',read);child.stderr?.on('data',read);
    child.once('exit',code=>{clearTimeout(timer);failed(new Error(`${label} exited (${code}) before it was ready:\n${log.slice(-400)}`));});
  });
}
function alive(pid,group=false){try{process.kill(group?-pid:pid,0);return true;}catch(e){return e.code==='EPERM';}}
async function stop(child,group=false){
  if(!child?.pid)return;
  const send=sig=>{try{process.kill(group?-child.pid:child.pid,sig);}catch{}};
  if(child.exitCode===null&&child.signalCode===null){
    const exited=new Promise(r=>child.once('exit',r));
    send('SIGTERM');if(group)send('SIGCONT');
    await Promise.race([exited,sleep(2000)]);
  }
  send('SIGKILL');
  for(let i=0;i<30&&alive(child.pid,group);i++)await sleep(100);
}

// A minimal DevTools client over Node's WebSocket: one page session.
class Page{
  static async open(endpoint){
    const ws=new WebSocket(endpoint);
    await new Promise((ok,bad)=>{ws.addEventListener('open',ok,{once:true});ws.addEventListener('error',()=>bad(new Error('DevTools socket')),{once:true});});
    const page=new Page(ws);
    const {targetId}=await page.send('Target.createTarget',{url:'about:blank'});
    page.session=(await page.send('Target.attachToTarget',{targetId,flatten:true})).sessionId;
    return page;
  }
  constructor(ws){
    this.ws=ws;this.next=1;this.waiting=new Map();
    ws.addEventListener('message',e=>{const r=JSON.parse(e.data),w=this.waiting.get(r.id);if(!w)return;this.waiting.delete(r.id);r.error?w.bad(new Error(r.error.message)):w.ok(r.result||{});});
    const lost=()=>{for(const w of this.waiting.values())w.bad(new Error('DevTools connection closed'));this.waiting.clear();};
    ws.addEventListener('close',lost);ws.addEventListener('error',lost);
  }
  send(method,params={}){
    const id=this.next++;
    return new Promise((ok,bad)=>{this.waiting.set(id,{ok,bad});this.ws.send(JSON.stringify({id,method,params,...(this.session?{sessionId:this.session}:{})}));});
  }
  async eval(expression){
    const r=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(r.exceptionDetails)throw new Error('page error: '+(r.exceptionDetails.exception?.description||r.exceptionDetails.text));
    return r.result.value;
  }
  async until(what,expression,ms=20000){
    const end=Date.now()+ms;
    for(;;){const v=await this.eval(expression);if(v)return v;if(Date.now()>end)throw new Error('timed out waiting for '+what);await sleep(150);}
  }
  async shot(file,selector){
    const box=await this.eval(`(()=>{const b=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:b.x+scrollX,y:b.y+scrollY,width:b.width,height:b.height};})()`);
    const {data}=await this.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{...box,scale:1}});
    writeFileSync(join(out,file),Buffer.from(data,'base64'));
    return `${file} (${Math.round(box.width)}x${Math.round(box.height)} css px at 2x)`;
  }
  close(){this.ws.close();}
}

async function desk(page,port,sid,label,log){
  if(sid!=='little-round-top'){
    await page.eval(`(()=>{const s=document.getElementById('scenario-select');s.value=${JSON.stringify(sid)};s.onchange();document.getElementById('new-game').click();return true;})()`);
  }
  await page.until(`${sid} on the desk`,`(()=>{try{return state.scenario_brief.id===${JSON.stringify(sid)}&&!!document.querySelector('#map .battle-features')&&!/Loading/.test(document.getElementById('map-renderer').textContent);}catch{return false;}})()`,30000);
  const renderer=await page.eval(`document.getElementById('map-renderer').textContent`);
  log.push(`${label}: renderer "${renderer}"`);
  const layer=()=>page.eval(`document.querySelector('#map .battle-features').outerHTML`);
  const before=await layer();
  const shots=[];
  for(const zoomed of [false,true]){
    if(zoomed){
      if(await page.eval(`BattleMapView.active()`)){
        await page.eval(`document.getElementById('map-in').click(),true`);
        await page.until('2x zoom',`/^2\\.0/.test(document.getElementById('map-zoom').textContent)`);await sleep(400);
      }else log.push(`${label}: SVG fallback has no camera; the zoomed shots are the fit view`);
    }
    for(const grid of ['on','off']){
      const off=await page.eval(`document.getElementById('map').classList.contains('no-grid')`);
      if((grid==='off')!==off)await page.eval(`document.getElementById('hex-toggle').click(),true`);
      assert.equal(await page.eval(`document.getElementById('map').classList.contains('no-grid')`),grid==='off');
      assert.equal(await layer(),before,`${label}: the feature layer is unchanged with the grid ${grid}`);
      shots.push(await page.shot(`${label}-${zoomed?'zoom2x':'fit'}-grid-${grid}.png`,'#map-wrap'));
    }
  }
  if(await page.eval(`BattleMapView.active()`))await page.eval(`document.getElementById('map-fit').click(),true`);
  shots.push(await page.shot(`${label}-legend.png`,'#feature-legend-panel'));
  // The hex tooltips (native <title>, which no screenshot shows), for every hex under a mark.
  const tips=await page.eval(`[...document.querySelectorAll('#map polygon.hex title')].map(t=>t.textContent).filter(t=>/Sourced|Reconstructed|Illustrative|Reported/.test(t))`);
  writeFileSync(join(out,`${label}-hex-tooltips.txt`),tips.join('\n')+'\n');
  log.push(`${label}: ${tips.length} hex tooltips name a mark status (${label}-hex-tooltips.txt)`);
  return shots;
}

// Direct POC reads and the clock speed, as the POC's own host (localhost only).
async function api(port,path,body){
  const r=await fetch(`http://127.0.0.1:${port}${path}`,body?{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}:{});
  const d=await r.json();
  if(!r.ok)throw new Error(`${path}: ${d.error||r.status}`);
  return d;
}

// docs/research/74: Concord through the desk's own controls, offline and scripted, to a result.
async function concordPlay(page,port,log){
  const head=await page.eval(`({clock:document.getElementById('clock').textContent,date:document.getElementById('battle-date').textContent,
    location:document.getElementById('battle-location').textContent,campaign:document.getElementById('campaign-line').textContent,
    header:[...document.querySelectorAll('.masthead,.field-heading')].map(n=>n.innerText).join(' ')})`);
  assert.deepEqual([head.clock,head.campaign],['09:25','CONCORD · 19 APRIL 1775']);
  assert.match(head.date,/Wednesday, (19 April|April 19,) 1775/);  // The browser's locale orders day and month.
  assert.match(head.location,/North Bridge · Concord, Massachusetts/);
  assert.doesNotMatch(head.header,/\bturn\b|revision/i,'no turn counter or revision label');
  log.push(`concord: header ${head.clock} · ${head.date} · ${head.location}; no turn or revision label`);
  const drawn=await page.eval(`({water:mapData.cells.filter(c=>c.terrain==='water').length,
    fill:BattleMap.render(mapData.cells,true,false).includes('#b9d3e3'),
    roads:[...document.querySelectorAll('#map [data-feature$="-road"] .road-casing')].map(n=>n.closest('[data-feature]').dataset.feature),
    bridge:!!document.querySelector('#map [data-feature="crossing:12,10"] .bridge-deck'),
    span:!!document.querySelector('#map [data-feature="crossing:12,10"] .road-span-fill')})`);
  assert.ok(drawn.water>0&&drawn.fill,'the river is water and the renderer fills it');
  assert.deepEqual(drawn.roads,['muster-road','town-road']);
  assert.ok(drawn.bridge&&drawn.span,'the North Bridge deck and its road span are drawn');
  log.push(`concord: ${drawn.water} water hexes filled #b9d3e3; roads ${drawn.roads.join(', ')}; North Bridge deck and span drawn`);
  // An order through the desk: the Acton company to the bridge approach.
  await page.eval(`(selectUnit('P1'),destination=[11,10],renderControls(),document.getElementById('send-order').click(),true)`);
  const order=await page.until('the P1 order on record',`fetch('/api/state').then(r=>r.json()).then(s=>s.orders.find(o=>o.unit_id==='P1'&&o.stance==='move'&&String(o.destination)==='11,10')||null)`);
  log.push(`concord: order accepted ${order.id} P1 move -> 11,10 (${order.status})`);
  shots.push(await page.shot('concord-order.png','body'));
  // Run the clock from the desk at 60x until the battle ends, then read the outcome headline.
  const live=await api(port,'/api/state');
  await api(port,'/api/clock',{game_id:live.game_id,command:'speed',speed:60});
  await page.until('the clock control',`!document.getElementById('clock-toggle').disabled`);
  await page.eval(`document.getElementById('clock-toggle').click(),true`);
  const outcome=await page.until('the Concord outcome',`state.status==='complete'&&!document.getElementById('outcome').classList.contains('hidden')?document.getElementById('outcome').innerText:null`,90000);
  const done=await api(port,'/api/state?view=god');
  const british=done.decisions.filter(d=>d.side==='british'&&d.role!=='staff');
  assert.ok(british.length>0&&british.every(d=>d.source==='scripted'&&d.policy==='scripted-concord-regulars-v1'),'the desk opponent played the regulars policy');
  const headline=outcome.split('\n')[0];
  assert.ok(['The bridge is carried.','The regulars hold the bridge.','The battle ends in a draw.'].includes(headline),headline);
  log.push(`concord: played to ${done.winner} at ${done.turn} intervals; headline "${headline}"; ${british.length} British decisions, all scripted-concord-regulars-v1; mode ${done.mode}`);
  shots.push(await page.shot('concord-outcome.png','body'));
}

// docs/research/75: Pegasus Bridge and Hill 223 through the desk's own controls, offline and
// scripted, to a result. Each spec names its header, its drawn marks, one order and its opponent.
const ERAS=[
  {sid:'pegasus-bridge',label:'pegasus',clock:'00:25',campaign:'NORMANDY · 6 JUNE 1944',
   date:/Tuesday, (6 June|June 6,) 1944/,location:/Caen Canal bridge · Bénouville, Normandy/,
   drawn:`({water:mapData.cells.filter(c=>c.terrain==='water').length,marsh:mapData.cells.filter(c=>c.terrain==='marsh').length,
     fill:BattleMap.render(mapData.cells,true,false).includes('#b9d3e3'),
     roads:[...document.querySelectorAll('#map [data-feature$="-road"] .road-casing')].map(n=>n.closest('[data-feature]').dataset.feature),
     canal:!!document.querySelector('#map [data-feature="canal-bridge"] .bridge-deck'),
     charges:!!document.querySelector('#map [data-feature="canal-bridge"] .bridge-charges'),
     label:document.querySelector('#map [data-feature="canal-bridge"] .feature-label')?.textContent,
     orne:!!document.querySelector('#map [data-feature="crossing:19,10"] .bridge-deck')})`,
   check(d){
     assert.ok(d.water>0&&d.fill&&d.marsh>0,'the canal and the Orne are water, the marsh between them is marsh');
     assert.deepEqual(d.roads.sort(),['benouville-road','bridges-road','ranville-road']);
     assert.ok(d.canal&&d.charges&&d.orne,'both bridges are drawn, the canal bridge with its charges');
     assert.equal(d.label,'Caen Canal bridge · charges');
     return `${d.water} water and ${d.marsh} marsh hexes; roads ${d.roads.join(', ')}; canal bridge "${d.label}" and the Orne bridge drawn`;
   },
   order:{unit:'D24',to:[9,10],why:'24 Platoon, with the sappers, onto the canal bridge'},
   note:'Note: on this entry the bridge is blown at 00:27:30 whatever you order, because the charge timings are authored, not sourced.',
   opponent:'german',policy:'scripted-pegasus-guard-v1'},
  {sid:'hill-223-patrol',label:'hill-223',clock:'06:45',campaign:'ARGONNE · 8 OCTOBER 1918',
   date:/Tuesday, (8 October|October 8,) 1918/,location:/Hill southwest of Hill 223 · Châtel-Chéhéry, Argonne/,
   drawn:`({woods:mapData.cells.filter(c=>c.terrain==='woods').length,
     trench:document.querySelector('#map [data-feature="old-trench"]')?.dataset.status,
     place:document.querySelector('#map .place-label')?.textContent})`,
   check(d){
     assert.ok(d.woods>0,'the ravine and the east-crest woods are woods');
     assert.equal(d.trench,'sourced');
     assert.equal(d.place,'Command post at the shack');
     return `${d.woods} woods hexes; old trench (${d.trench}); objective "${d.place}"`;
   },
   order:{unit:'A3',to:[16,6],why:'the right of the company line, by runner'},
   opponent:'german',policy:'scripted-hill-223-german-v1'},
];
async function eraPlay(page,port,log,era){
  const head=await page.eval(`({clock:document.getElementById('clock').textContent,date:document.getElementById('battle-date').textContent,
    location:document.getElementById('battle-location').textContent,campaign:document.getElementById('campaign-line').textContent,
    header:[...document.querySelectorAll('.masthead,.field-heading')].map(n=>n.innerText).join(' ')})`);
  assert.deepEqual([head.clock,head.campaign],[era.clock,era.campaign]);
  assert.match(head.date,era.date);  // The browser's locale orders day and month.
  assert.match(head.location,era.location);
  assert.doesNotMatch(head.header,/\bturn\b|revision/i,'no turn counter or revision label');
  log.push(`${era.label}: header ${head.clock} · ${head.date} · ${head.location}; no turn or revision label`);
  log.push(`${era.label}: ${era.check(await page.eval(era.drawn))}`);
  if(era.note){  // bt-D09 default: the brief's note is on the desk, and visible, before play.
    const seen=await page.eval(`(n=>({text:n.innerText,visible:n.checkVisibility()}))(document.getElementById('mission-text'))`);
    assert.ok(seen.visible&&seen.text.endsWith(era.note),`the ${era.label} brief shows its note: ${seen.text}`);
    log.push(`${era.label}: brief note visible before play: "${era.note}"`);
  }
  const {unit,to}=era.order;
  await page.eval(`(selectUnit(${JSON.stringify(unit)}),destination=${JSON.stringify(to)},renderControls(),document.getElementById('send-order').click(),true)`);
  const order=await page.until(`the ${unit} order on record`,`fetch('/api/state').then(r=>r.json()).then(s=>s.orders.find(o=>o.unit_id===${JSON.stringify(unit)}&&o.stance==='move'&&String(o.destination)===${JSON.stringify(String(to))})||null)`);
  log.push(`${era.label}: order accepted ${order.id} ${unit} move -> ${to} (${order.status}): ${era.order.why}`);
  shots.push(await page.shot(`${era.label}-order.png`,'body'));
  const live=await api(port,'/api/state');
  await api(port,'/api/clock',{game_id:live.game_id,command:'speed',speed:60});
  await page.until('the clock control',`!document.getElementById('clock-toggle').disabled`);
  await page.eval(`document.getElementById('clock-toggle').click(),true`);
  const outcome=await page.until(`the ${era.label} outcome`,`state.status==='complete'&&!document.getElementById('outcome').classList.contains('hidden')?document.getElementById('outcome').innerText:null`,120000);
  const done=await api(port,'/api/state?view=god');
  const theirs=done.decisions.filter(d=>d.side===era.opponent&&d.role!=='staff');
  assert.ok(theirs.length>0&&theirs.every(d=>d.source==='scripted'&&d.policy===era.policy),`the desk opponent played ${era.policy}`);
  const outcomes=done.scenario_brief.outcomes;
  const headline=outcome.split('\n')[0];
  assert.equal(headline,done.winner===done.side?outcomes.win:done.winner==='draw'?outcomes.draw:outcomes.loss);
  assert.ok(outcome.includes(done.reason),'the server reason is shown with the headline');
  log.push(`${era.label}: played to ${done.winner} at ${done.turn} intervals; headline "${headline}"; reason "${done.reason}"; ${theirs.length} ${era.opponent} decisions, all ${era.policy}; mode ${done.mode}`);
  shots.push(await page.shot(`${era.label}-outcome.png`,'body'));
}
let shots;

async function run(held,log){
  const binary=findBrowser();
  if(!binary){console.error('HARNESS BLOCKED: no Chrome/Chromium found (set BATTLE_BROWSER). This is not a pass.');return BLOCKED;}
  const port=await freePort();
  log.push(`browser: ${binary}`,`POC port ${port}, database ${join(held.dir,'battle.sqlite')}`);
  held.poc=spawn('python3',['-m','battle','--offline','--port',String(port),'--db',join(held.dir,'battle.sqlite')],{cwd:POC,env:cleanEnv(),stdio:['ignore','pipe','pipe']});
  await waitFor(held.poc,READY,20000,'POC');
  if(held.closing)return 1;
  held.browser=spawn(binary,['--headless=new','--remote-debugging-port=0',`--user-data-dir=${held.profile}`,'--no-first-run','--no-default-browser-check',
    '--disable-extensions','--disable-sync','--disable-background-networking','--disable-component-update','--disable-default-apps','--window-size=1440,1100','about:blank'],
    {env:cleanEnv(),stdio:['ignore','ignore','pipe'],detached:true});
  let endpoint;
  try{endpoint=(await waitFor(held.browser,/DevTools listening on (ws:\/\/\S+)/,20000,'browser'))[1];}
  catch(e){console.error(`HARNESS BLOCKED: the browser did not start (${e.message.split('\n')[0]}). This is not a pass.`);return BLOCKED;}
  log.push(`POC pid ${held.poc.pid}, browser group ${held.browser.pid}`);
  held.page=await Page.open(endpoint);
  await held.page.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:2,mobile:false});
  if(FAULT==='throw')throw new Error('MAP_HARNESS_FAULT=throw: injected failure after the page opened');
  if(FAULT==='sigint'){process.kill(process.pid,'SIGINT');await sleep(10000);}
  shots=[];
  await held.page.send('Page.navigate',{url:`http://127.0.0.1:${port}/`});
  shots.push(...await desk(held.page,port,'little-round-top','little-round-top',log));
  shots.push(...await desk(held.page,port,'hougoumont-north-gate','hougoumont',log));
  shots.push(...await desk(held.page,port,CONCORD,'concord',log));
  await concordPlay(held.page,port,log);
  for(const era of ERAS){
    shots.push(...await desk(held.page,port,era.sid,era.label,log));
    await eraPlay(held.page,port,log,era);
  }
  // The picker offers exactly the player scenarios.
  const picker=await held.page.eval(`[...document.querySelectorAll('#scenario-select option')].map(o=>o.value)`);
  assert.deepEqual(picker,['little-round-top','hougoumont-north-gate',CONCORD,...ERAS.map(e=>e.sid)]);
  log.push(`player picker: ${picker.join(', ')}`);
  log.push('screenshots:',...shots.map(s=>'  '+s));
  return 0;
}

async function main(){
  const held={closing:false,dir:mkdtempSync(join(tmpdir(),'battle-map-harness.')),profile:mkdtempSync(join(tmpdir(),'battle-map-profile.'))};
  const log=[`output: ${out}`,`deadline: ${DEADLINE_MS} ms`];
  let cleaned;
  const cleanup=()=>cleaned??=(async()=>{
    held.closing=true;
    try{held.page?.close();}catch{}
    await stop(held.browser,true);await stop(held.poc);
    rmSync(held.profile,{recursive:true,force:true,maxRetries:3,retryDelay:100});
    rmSync(held.dir,{recursive:true,force:true,maxRetries:3,retryDelay:100});
    const report=[held.poc&&`POC pid ${held.poc.pid} ${alive(held.poc.pid)?'STILL RUNNING':'gone'}`,
      held.browser&&`browser group ${held.browser.pid} ${alive(held.browser.pid,true)?'STILL RUNNING':'gone'}`,
      `profile ${existsSync(held.profile)?'STILL PRESENT':'removed'}`,`database dir ${existsSync(held.dir)?'STILL PRESENT':'removed'}`].filter(Boolean);
    console.log('cleanup: '+report.join('; '));
    if(report.some(r=>/STILL/.test(r)))process.exitCode=1;
  })();
  // bt-T08 review: `on`, not `once`, so a second signal during cleanup's wait finds a listener and
  // cannot kill the harness before the browser group is stopped; SIGHUP (a closed terminal) too.
  // The first signal starts cleanup; later ones are ignored while it runs.
  let signalled=false;
  for(const sig of ['SIGINT','SIGTERM','SIGHUP'])process.on(sig,()=>{
    if(signalled)return;
    signalled=true;
    console.error(`HARNESS FAILED: ${sig} received`);
    void cleanup().finally(()=>process.exit(1));
  });
  // After SIGHUP the terminal may be gone; a failed write must not end the run before cleanup.
  for(const stream of [process.stdout,process.stderr])stream.on('error',()=>{});
  let code;
  try{
    let timer;
    const deadline=new Promise((_,bad)=>{timer=setTimeout(()=>bad(new Error(`harness passed its ${DEADLINE_MS} ms deadline`)),DEADLINE_MS);});
    code=await Promise.race([run(held,log),deadline]).finally(()=>clearTimeout(timer));
    console.log(log.join('\n'));
    if(code===0)console.log('HARNESS PASSED: desk screenshots with the grid on and off, legends and tooltips for every player scenario; Concord, Pegasus Bridge and Hill 223 played to a result.');
  }catch(e){
    console.log(log.join('\n'));
    console.error(`HARNESS FAILED: ${e.stack||e}`);code=1;
  }finally{await cleanup();}
  return process.exitCode||code;
}
const code=await main();
process.exitCode=code;
setTimeout(()=>process.exit(code),3000).unref();
