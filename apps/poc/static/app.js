const $=id=>document.getElementById(id);
const api=BattleApi.create({fetch:(...args)=>fetch(...args)});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const unitIcons=UnitIcons.create({esc});
let state,mapData,selected=null,destination=null,busy=false,replay=false,liveState,history=[],hexes=true,terrain=false,toastTimer;
let godMode=false,godEventLimit=60,unitAction=null;
const stateUrl=()=>'/api/state'+(godMode?'?view=god':'');
let replayPlaying=false,replaySpeed=10,replayIndex=0,replayTimer,replayGeneration=0,viewEpoch=0;
const speeds=[0.5,1,2,5,10,30,60];
const center=p=>[(p[0]+.5*(p[1]&1))*Math.sqrt(3)*25.5+24,p[1]*38.25+26];
const elapsedSeconds=t=>t*state.seconds_per_turn;
const clock=t=>BattleTimeline.time(mapData.setting,elapsedSeconds(t),state.display_locale||'en-GB');
function renderTimeline(){
  const elapsed=elapsedSeconds(state.turn);
  const date=BattleTimeline.date(mapData.setting,elapsed,state.display_locale||'en-GB');
  $('clock').textContent=clock(state.turn);
  $('battle-date').textContent=date;
  $('battle-location').textContent=mapData.setting.location;
  $('replay-slider').setAttribute('aria-valuetext',`${date} · ${clock(state.turn)}`);
  if(replay)$('replay-label').textContent=`Recorded · ${date} · ${clock(state.turn)}`;
}
const troopAnalysis=TroopAnalysis.create({element:$,context:()=>({state,liveState,selected,busy,replay,godMode}),
  dispatch:instruction=>post('/api/standing-orders',{instruction}),toast,esc,clock});
function toast(text){$('toast').textContent=text;$('toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),5500);}
const get=path=>api.get(path);
async function pauseLive(){
  state=await getPost('/api/clock',{command:'pause',game_id:state.game_id});liveState=state;
  while(state.clock.inflight){renderControls();await new Promise(r=>setTimeout(r,150));state=await get(stateUrl());liveState=state;}
}
async function post(path,body={}){
  if(busy||replay||(godMode&&['/api/orders','/api/chat','/api/formations','/api/recommendations','/api/standing-orders'].includes(path)))return;busy=true;viewEpoch++;renderControls();
  try{
    if(state.clock.running||state.clock.inflight)await pauseLive();
    state=await getPost(path,{...body,revision:state.revision,game_id:state.game_id});liveState=state;render();return state;
  }catch(e){toast(e.message);try{state=await get(stateUrl());liveState=state;render();}catch{}}
  finally{busy=false;renderControls();}
}
async function controlClock(command,speed){
  if(busy)return;busy=true;viewEpoch++;renderControls();
  try{state=await getPost('/api/clock',{command,speed,game_id:state.game_id});liveState=state;render();}
  catch(e){toast(e.message);}finally{busy=false;renderControls();}
}
async function getPost(path,body){const data=await api.post(path,body);return godMode?await get(stateUrl()):data;}
function polygons(){return mapData.cells.map(c=>{const[x,y]=center(c.pos),points=Array.from({length:6},(_,i)=>{const a=(60*i-30)*Math.PI/180;return `${x+25.5*Math.cos(a)},${y+25.5*Math.sin(a)}`;}).join(' ');const chosen=destination&&String(c.pos)===String(destination);return `<polygon class="hex ${chosen?'selected-hex':''}" data-c="${c.pos[0]}" data-r="${c.pos[1]}" points="${points}"><title>Hex ${c.pos.join(',')} · ${c.terrain} · ${c.elevation} m (authored)${(state.map_features||[]).filter(f=>f.pos&&String(f.pos)===String(c.pos)||f.hexes?.some(p=>String(p)===String(c.pos))).map(f=>' · '+esc(f.name)+(f.kind==='fortification'?' '+f.progress+'% · cover '+f.cover:'')).join('')}</title></polygon>`;}).join('');}
function renderFeatures(){
  let svg='<g class="battle-features" pointer-events="none">';
  for(const f of state.map_features||[]){
    if(f.kind==='road'){
      const path=f.points.map((p,i)=>(i?'L':'M')+center(p).join(',')).join(' '),[x,y]=center(f.points[1]);
      svg+=`<path d="${path}" fill="none" stroke="#ae997b" stroke-width="10" stroke-linejoin="round"/><path d="${path}" fill="none" stroke="#fff4d5" stroke-width="6" stroke-linejoin="round"/><text x="${x+12}" y="${y-14}" class="feature-label">${esc(f.name)}</text>`;
    }else{
      const[x,y]=center(f.pos);
      if(f.kind==='building')svg+=`<g transform="translate(${x},${y})"><rect x="-16" y="-11" width="32" height="22" rx="1" fill="#d8c7b0" stroke="#856f58" stroke-width="2"/><path d="M-16,0H16M0,-11V11" stroke="#aa9075" stroke-width="2"/><text x="0" y="-20" text-anchor="middle" class="feature-label">${esc(f.name)}</text></g>`;
      else if(f.kind==='fortification')svg+=`<g transform="translate(${x},${y+24})" opacity="${f.progress===100?1:.65}"><path d="M-22,8V0L-11,-6L0,0L11,-6L22,0V8" fill="none" stroke="#70563a" stroke-width="6"/><path d="M-22,8V0L-11,-6L0,0L11,-6L22,0V8" fill="none" stroke="#cab18b" stroke-width="2"/><text x="30" y="5" text-anchor="start" class="feature-label">${f.progress===100?'FIELDWORKS':esc(f.progress)+'% WORKS'}</text></g>`;
    }
  }
  return svg+'</g>';
}
function renderMap(){const[ox,oy]=center(state.objective);let shapes=BattleMap.render(mapData.cells,terrain,BattleMapView.active())+`<g>${polygons()}</g><g pointer-events="none" class="summit"><circle cx="${ox}" cy="${oy}" r="53" fill="#fff" fill-opacity=".25" stroke="#b19752" stroke-width="2" stroke-dasharray="5 5"/><circle cx="${ox}" cy="${oy}" r="15" fill="#fff" stroke="#b19752" stroke-width="2"/><path d="M${ox-4},${oy+8}v-17l11,4 -11,4" fill="none" stroke="#94772e" stroke-width="2"/><text x="${ox}" y="${oy-118}" class="place-label">Little Round Top</text><text x="${ox}" y="${oy-97}" class="place-subtitle">SUMMIT OBJECTIVE</text></g>`;
shapes+=renderFeatures();
for(const depot of state.supply_sites||[]){const[x,y]=center(depot.pos);shapes+=`<g pointer-events="none"><rect x="${x-12}" y="${y-12}" width="24" height="24" rx="3" fill="#fff5d5" stroke="#8f7134" stroke-width="2"/><path d="M${x-7},${y-7}l14,14m0,-14l-14,14" stroke="#8f7134"/><text x="${x}" y="${y+29}" text-anchor="middle" font-size="11" fill="#634e27">${godMode?esc(depot.side)+' · ':''}AMMUNITION</text></g>`;}
const selectedUnit=state.units.find(u=>u.id===selected);
if(selectedUnit){const target=destination||selectedUnit.target;if(target){const[a,b]=center(selectedUnit.pos),[c,d]=center(target);shapes+=`<path d="M${a},${b}L${c},${d}" stroke="#23445b" stroke-width="3" stroke-dasharray="7 5" pointer-events="none"/><circle cx="${c}" cy="${d}" r="10" fill="none" stroke="#23445b" stroke-width="3" pointer-events="none"/>`;}}
shapes+=unitIcons.render([
  ...state.contacts.map(c=>({unit:c,contact:true,enemy:true,selected:selected==='contact:'+c.id,
    point:center(c.pos),report:`Estimate · ${c.age*state.seconds_per_turn}s old · ${c.confidence||'unconfirmed'} confidence`})),
  ...state.units.map(u=>({unit:u,contact:false,enemy:u.side!==state.side,selected:selected===u.id,
    point:center(u.pos),report:godMode?'Exact observer state':`Reported ${clock(u.observed_turn)}`})),
]);
for(const r of state.recommendations||[]){
  if(r.status!=='delivered')continue;
  const u=state.units.find(u=>u.id===r.unit_id);if(!u)continue;
  const[x,y]=center(u.pos);shapes+=`<g class="advice-flag" data-advice-unit="${esc(u.id)}" tabindex="0" role="button" aria-label="Recommendation from ${esc(u.id)}" transform="translate(${x+21},${y-11})"><title>${esc(u.id)}: commander recommendation received. Select to review.</title><rect x="-5" y="-16" width="27" height="35" rx="4" fill="#3c3520" stroke="#f2cb61"/><path d="M1,13V-10H16L11,-4L16,2H1" fill="#f2cb61" stroke="#f2cb61" stroke-width="2"/></g>`;
}
const hqs=godMode?Object.entries(state.headquarters||{}):[[state.side,state.hq]];
for(const[side,pos] of hqs){const[hx,hy]=center(pos);const offset=state.command||state.commands?.[side]?-31:0;shapes+=`<g pointer-events="none"><rect x="${hx-18}" y="${hy-12+offset}" width="36" height="22" rx="3" fill="${side==='union'?'#244f76':'#873e36'}" stroke="#f0e2b7"/><text x="${hx}" y="${hy+3+offset}" text-anchor="middle" font-size="10" fill="#fff">${side==='union'?'YOU':'HQ'}</text></g>`;}
if(godMode){for(const packet of [...[...state.orders,...(state.standing_orders||[])].filter(o=>o.status==='en_route').map(o=>o.transport),...(state.reports||[]).map(r=>r.transport)].filter(Boolean)){const[x,y]=center(packet.pos),[a,b]=center(packet.address);shapes+=`<g pointer-events="none"><path d="M${x},${y}L${a},${b}" stroke="#856830" stroke-width="1.5" stroke-dasharray="3 5" opacity=".6"/><rect x="${x-4}" y="${y-3}" width="8" height="6" fill="#fff4cb" stroke="#856830"/></g>`;}}
$('map').innerHTML=shapes;$('map').classList.toggle('no-grid',!hexes);BattleMapView.update(terrain);
}
function renderUnits(){$('unit-list').innerHTML=state.units.map(u=>`<button class="unit-card ${u.side!==state.side?'enemy-card':''} ${u.id===selected?'selected':''}" data-unit="${u.id}" aria-pressed="${u.id===selected}"><div class="unit-top"><b>${u.id} · ${esc(u.status.toUpperCase())}${(state.recommendations||[]).some(r=>r.unit_id===u.id&&r.status==='delivered')?' · ⚑ ADVICE':''}</b><span>${godMode?"EXACT · "+u.side.toUpperCase():(state.turn-u.observed_turn)*30+"s AGO"}</span></div><span class="unit-strength">${u.strength}<small> / ${u.initial}</small></span><span class="unit-name">${esc(u.name)}${u.recon_role==="scout"?" · SCOUT":""}${u.id===state.command?.unit_id?" · YOUR HQ":godMode&&Object.values(state.commands||{}).some(c=>c.unit_id===u.id)?" · HQ":""}</span><div class="unit-action" title="${esc(u.local_reason||"Standing orders")}">${esc((u.stance==='dig_in'&&['hold','observe'].includes(u.local_action)?'digging in':u.local_action||'standing orders').replaceAll('_',' '))}${u.tactical_target?" → "+u.tactical_target.join(","):""}</div>${unitIcons.metrics(u)}<div class="unit-bottom"><span>${u.ammo} rounds</span></div></button>`).join('');}
function renderContacts(){
  $('contact-list').innerHTML=state.contacts.length?state.contacts.map(c=>{
    const strength=c.strength_range?`${c.strength_range[0]}–${c.strength_range[1]} troops`:'Strength unconfirmed';
    return `<article class="contact-card ${c.age>1?'aged-contact':''}"><div><strong>${esc(c.id)} · ${esc(c.composition?.type||'unidentified troops')}</strong><span>HEX ${c.pos.join(',')}</span></div><b>${strength}</b><p>Weapons: ${esc(c.composition?.weapons||'not established')}</p>${c.identification?.type?`<p>Identified by ${esc(c.identification.type.observer_role)} · ${(state.turn-c.identification.type.observed_turn)*30}s ago</p>`:''}<small>${esc(c.confidence||'low')} confidence · ${esc(c.observer_role||'field report')} · ${c.age*30}s old</small></article>`;
  }).join(''):'<p class="contact-empty">No delivered enemy sightings. Sustained observation improves estimates; scouting detachments identify formations more quickly.</p>';
}
function renderDispatches(){const ds=[...state.dispatches].sort((a,b)=>b.turn-a.turn);$('dispatch-count').textContent=ds.length;$('dispatches').innerHTML=ds.length?ds.map(d=>`<article class="dispatch"><time>${clock(d.turn)} · ${godMode?esc(d.side?.toUpperCase()||'')+' · ':''}${esc(d.kind.toUpperCase())}</time><p>${esc(d.display_text ?? d.text)}</p>${d.observed_turn!==d.turn?`<span class="age">Observed ${clock(d.observed_turn)} · delivered ${clock(d.turn)}</span>`:''}</article>`).join(''):godMode?'<div class="empty-state">No dispatches recorded at this time. Start the clock to observe both sides.</div>':'<div class="empty-state"><strong>General, the line awaits your orders.</strong>Three detachments stand ready. We await word of the enemy from the field.<br><br>Select a blue unit on the map or below it. Choose a destination hex and dispatch a runner, then start the clock.</div>';
}
function renderMessages(){const msgs=state.messages||[];$('messages').innerHTML=msgs.map(m=>`<div class="chat-message ${esc(m.role)}"><small>${m.role==='user'?'YOU':m.source==='openrouter'?'STAFF · OPENROUTER':'STAFF · LOCAL FALLBACK'} · ${clock(m.turn)}</small>${esc(m.content)}${m.proposals.length?`<div class="proposal-list">${m.proposals.map(o=>`${esc(o.unit_id)}: ${esc(o.stance)}${o.destination?' to hex '+esc(o.destination.join(',')):''}`).join('<br>')}</div><button data-proposal="${m.id}" ${replay||godMode?'disabled':''}>Dispatch ${m.proposals.length} proposed order${m.proposals.length===1?'':'s'} ↗</button>`:''}</div>`).join('');$('messages').scrollTop=$('messages').scrollHeight;}
function renderControls(){if(!state)return;renderUnitDetail();troopAnalysis.render();const u=state.units.find(u=>u.id===selected);const inactive=busy||replay||godMode||state.command?.operational===false||state.status!=='active';const c=state.clock||liveState?.clock||{},running=replay?replayPlaying:c.running,rate=replay?replaySpeed:c.speed;
$('clock-toggle').disabled=busy||(!replay&&state.status!=='active')||(!replay&&c.inflight&&!c.running);
$('clock-toggle').textContent=replay?(running?'Pause replay Ⅱ':'Play replay ▶'):(running?'Pause clock Ⅱ':'Start clock ▶');
$('clock-speed').textContent=`${rate}×${replay?' replay':''}`;
$('clock-slower').disabled=busy||rate===speeds[0];$('clock-faster').disabled=busy||rate===speeds.at(-1);
$('clock-status').textContent=replay?`${running?'Playing':'Paused'} · recorded ${godMode?'omniscient':'commander'} view`:c.error||
(c.inflight?(c.running?'Updating battlefield…':'Pausing clock…'):
state.status!=='active'?'Battle complete · replay available':`${c.running?'Running':'Paused'} · battlefield time${c.running?' · '+c.speed+'×':''}`);
$('send-order').disabled=Boolean(unitAction&&unitAction!=='move')||inactive||!u||!destination||['routed','lost'].includes(u.status);$('hold-order').disabled=inactive||!u||['routed','lost'].includes(u.status);$('new-game').disabled=busy;$('ai-mode').disabled=busy||replay;$('chat-send').disabled=busy||replay||godMode;$('chat-input').disabled=busy||replay||godMode;$('god-toggle').disabled=busy;
$('send-order').textContent=u&&u.id===state.command?.unit_id?'Give local order ↗':'Dispatch runner ↗';
$('order-summary').innerHTML='<span class="eyebrow">MOVEMENT ORDERS</span><strong>'+(!u?'Select a detachment to begin.':`${esc(u.name)}${destination?` → hex ${destination.join(',')}`:' · choose a destination hex'}`)+'</strong>';
$('map-tip').textContent=unitAction==='split'?'Split: choose an adjacent hex, then send instructions in the unit panel.':godMode?'God Mode · inspect all sides. Return to commander view to give orders.':replay?'Recorded commander view. Orders are disabled.':u?(destination?`${u.id} → ${destination.join(',')} · ${u.id===state.command?.unit_id?'give a local order':'dispatch a runner'}.`:`${u.id} selected. Choose a hex or hold position.`):'Select a blue unit, then choose a destination hex.';
$('ai-mode').value=state.mode||liveState?.mode||'scripted';$('ai-status').textContent=replay?'Recorded view · live commands paused':state.last_fallback_reason?`Local fallback used (${state.last_fallback_reason}). Battle continues.`:state.last_commander_source?`Last decision: ${state.last_commander_source==='openrouter'?'OpenRouter agent':'scripted commander'} · plans every 90s`:'First command decision arrives when the clock runs.';
}
function render(){$('rules-notice').classList.toggle('hidden',state.rules==='poc-8');renderObserver();renderContacts();renderTimeline();renderMap();renderUnits();renderDispatches();renderMessages();renderControls();$('outcome').classList.toggle('hidden',state.status==='active');if(state.status!=='active')$('outcome').innerHTML=`<strong>${state.winner==='union'?'The line holds.':state.winner==='confederate'?'The summit is lost.':'The battle ends in a draw.'}</strong><p>${esc(state.reason)}</p><a href="/api/export" target="_blank">Open complete event log & replay audit ↗</a>`;}
function renderObserver(){
  $('god-toggle').classList.toggle('active',godMode);$('god-toggle').setAttribute('aria-checked',godMode);$('god-toggle-state').textContent=godMode?'On':'Off';
  $('god-notice').classList.toggle('hidden',!godMode);$('god-inspector').classList.toggle('hidden',!godMode);
  $('enemy-intelligence').classList.toggle('hidden',godMode);$('enemy-key').textContent=godMode?'ENEMY · EXACT':'REPORTED ENEMY';
  const c=state.command;
  $('command-location').innerHTML=c?`<strong>You are with ${esc(c.unit_id)} · hex ${c.pos?.join(',')||'unknown'}</strong><span>${esc(c.profile.label)} · ${c.operational?'Headquarters moves with this detachment.':'COMMAND DISRUPTED · standing orders continue.'}</span>`:'<strong>Legacy headquarters</strong><span>Use Reset for an attached command unit.</span>';
  if(!godMode)return;
  const category=$('god-filter').value||'all';
  const matches=e=>category==='all'||(category==='combat'?/volley|casualties|unit_|movement|battle_ended/.test(e.kind):category==='communications'?/order_|report_|communication_/.test(e.kind):/decision|staff_consulted/.test(e.kind));
  const events=(state.events||[]).filter(matches).slice().reverse();
  $('god-count').textContent=`${(state.events||[]).length} RECORDED EVENTS`;
  $('god-events').innerHTML=events.slice(0,godEventLimit).map(e=>`<details class="god-event"><summary><time>${clock(e.turn)}</time><b>${esc(e.kind.replaceAll('_',' '))}</b><span>${esc(e.unit_id||e.side||e.order_id||'')} #${e.seq}</span></summary><pre>${esc(JSON.stringify(e,null,2))}</pre></details>`).join('')||'<p>No events at this time. Start the clock to observe the battle.</p>';
  $('god-older').disabled=godEventLimit>=events.length;$('god-older').textContent=`Show older events (${Math.min(events.length,godEventLimit)} / ${events.length})`;
  $('god-traffic').textContent=JSON.stringify({orders:state.orders,standing_orders:state.standing_orders,reports:state.reports,recommendations:state.recommendations},null,2);
  $('god-decisions').textContent=JSON.stringify(state.decisions||[],null,2);
  $('god-units').textContent=JSON.stringify(state.units,null,2);
}
$('god-filter').onchange=()=>{godEventLimit=60;renderObserver();};
$('god-older').onclick=()=>{godEventLimit+=60;renderObserver();};
$('god-toggle').onclick=async()=>{
  if(busy)return;busy=true;viewEpoch++;stopReplay();const previous=godMode;
  godMode=!godMode;selected=null;destination=null;unitAction=null;godEventLimit=60;renderControls();
  try{if(replay){if(!await loadReplay(replayIndex))throw Error('Could not change replay view.');}else{state=await get(stateUrl());liveState=state;render();}}
  catch(e){godMode=previous;toast(e.message);}finally{busy=false;renderControls();}
};
function combineCandidates(u){
  const cube=p=>{const x=p[0]-(p[1]-(p[1]&1))/2;return[x,-x-p[1],p[1]];};
  const adjacent=(a,b)=>Math.max(...cube(a).map((v,i)=>Math.abs(v-cube(b)[i])))===1;
  return state.units.filter(v=>v.id!==u.id&&v.side===state.side&&!['lost','routed','merged'].includes(v.status)&&v.id!==state.command?.unit_id&&v.strength+u.strength<=80&&adjacent(u.pos,v.pos)&&['unit_type','weapon_class','skill','recon_role','recon_skill'].every(k=>u[k]===v[k]));
}
function renderUnitDetail(){
  const contact=selected?.startsWith('contact:')?state.contacts.find(c=>'contact:'+c.id===selected):null;
  const u=contact||state.units.find(u=>u.id===selected),present=Boolean(u);
  $('unit-detail').classList.toggle('hidden',!present);$('mission-objective').classList.toggle('hidden',present);
  $('unit-analysis').disabled=!u||Boolean(contact)||godMode||u.side!==state.side;
  if(!u)return;
  const enemy=contact||u.side!==state.side,readOnly=busy||replay||godMode||enemy||state.status!=='active'||state.command?.operational===false||['routed','lost','merged'].includes(u.status);
  $('unit-title').textContent=contact?`${u.id} · enemy contact`:`${u.id} · ${u.name}`;
  $('unit-report-age').textContent=godMode?'Exact state · omniscient observer':`Observed ${clock(u.observed_turn)} · ${(state.turn-u.observed_turn)*30}s old${u.id===state.command?.unit_id?' · with your headquarters':''}`;
  $('unit-stats').innerHTML=contact?`<strong class="detail-strength">${u.strength_range?u.strength_range.join('–'):'Unknown'}<small> estimated troops</small></strong><p>${esc(u.composition?.type||'Unidentified')} · ${esc(u.composition?.weapons||'weapons unknown')}</p><p>${esc(u.confidence||'Unconfirmed')} confidence</p>`:`<strong class="detail-strength">${u.strength}<small> / ${u.initial} troops</small></strong><div class="detail-metrics"><span>Type<b>${esc(u.unit_type||"Unknown")}</b></span><span>Skill<b>${u.skill??"?"}%</b></span><span>Energy<b>${UnitIcons.describe(u).energy??"?"}%</b></span><span>Ammunition<b>${u.ammo}</b></span><span>Morale<b>${u.morale}%</b></span><span>Suppression<b>${u.suppression}%</b></span><span>Fatigue<b>${u.fatigue}%</b></span>${u.tools!==undefined?'<span>Entrenching tools<b>'+u.tools+'</b></span>':''}</div><p>${esc(u.weapon_class||'Weapons not reported')} · ${esc(u.recon_role||'line')} · ${esc(u.status)}</p>`;
  $('unit-mission').textContent=contact?'Enemy orders are unknown.':`Mission: ${(state.order_templates||[]).find(t=>t.id===u.stance)?.label||u.stance}${u.target?' → hex '+u.target.join(','):''} · order version ${u.order_version}`;
  const fieldwork=(state.map_features||[]).find(f=>f.kind==='fortification'&&String(f.pos)===String(u.pos));
  if(!contact&&fieldwork)$('unit-mission').textContent+=` · fieldworks ${fieldwork.progress}% · reported cover ${fieldwork.cover}`;
  $('unit-judgment').textContent=contact?'':(u.mission_result?u.mission_result.status.toUpperCase()+' · '+u.mission_result.reason+' ':'')+(u.local_reason||'Following standing orders.');
  const candidates=!enemy?combineCandidates(u):[];
  for(const id of ['unit-move','unit-order','unit-hold'])$(id).disabled=Boolean(readOnly);
  $('unit-split').disabled=Boolean(readOnly||!['poc-4','poc-5','poc-6','poc-7','poc-8'].includes(state.rules)||u.strength<24);
  $('unit-combine').disabled=Boolean(readOnly||!['poc-4','poc-5','poc-6','poc-7','poc-8'].includes(state.rules)||!candidates.length);
  $('unit-action-note').textContent=godMode?'Observer view. Turn off God Mode to issue orders.':replay?'Recorded view. Return to live to command.':enemy?'Enemy intelligence only; commands are unavailable.':state.status!=='active'?'Battle complete. Reset to command a fresh battle.':state.command?.operational===false?'Headquarters is disrupted; standing orders continue.':['routed','lost'].includes(u.status)?'Formation is reported unable to accept orders.':!['poc-4','poc-5','poc-6','poc-7','poc-8'].includes(state.rules)?'Reset to enable split and combine in a new battle.':!candidates.length?'Combine needs an adjacent friendly unit with matching weapons, training and role.':'Split/combine require sixty seconds of regrouping after instructions arrive. Local commanders can refuse during contact.';
  const oldPartner=$('unit-combine-target').value;
  const partnerOptions=candidates.map(v=>`<option value="${esc(v.id)}">${esc(v.id)} · ${v.strength} troops</option>`).join('');
  if($('unit-combine-target').innerHTML!==partnerOptions)$('unit-combine-target').innerHTML=partnerOptions;
  if(candidates.some(v=>v.id===oldPartner))$('unit-combine-target').value=oldPartner;
  $('unit-action-form').classList.toggle('hidden',!unitAction||Boolean(readOnly));
  $('unit-order-field').classList.toggle('hidden',unitAction!=='order');
  $('unit-split-field').classList.toggle('hidden',unitAction!=='split');
  $('unit-combine-field').classList.toggle('hidden',unitAction!=='combine');
  $('unit-split-count').max=Math.max(12,(u.strength||0)-12);
  $('unit-split-count').disabled=unitAction!=='split'||Boolean(readOnly);
  $('unit-combine-target').disabled=unitAction!=='combine'||Boolean(readOnly);
  $('unit-order-kind').disabled=unitAction!=='order'||Boolean(readOnly);
  const templates=state.order_templates||[{id:'hold',label:'Hold and defend',destination:'none',intent:'Hold the present ground.',effect:'Defend and report enemy contact.'},{id:'move',label:'Move to position',destination:'hex',intent:'Proceed to the appointed map reference.',effect:'Report on arrival.'}];
  const previousOrder=$('unit-order-kind').value;
  const orderOptions=templates.map(t=>`<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('');
  if($('unit-order-kind').innerHTML!==orderOptions){$('unit-order-kind').innerHTML=orderOptions;$('unit-order-kind').value=templates.some(t=>t.id===previousOrder)?previousOrder:'hold';}
  const template=templates.find(t=>t.id===$('unit-order-kind').value)||templates[0];
  const needsHex=unitAction==='move'||unitAction==='split'||(unitAction==='order'&&template.destination==='hex');
  $('unit-order-description').classList.toggle('hidden',unitAction!=='order');
  $('unit-order-description').innerHTML=`<strong>${esc(template.intent)}</strong><p>${esc(template.effect)}</p>${template.id==='resupply'?'<p>'+((state.supply_sites||[]).map(d=>esc(d.name)+' · hex '+d.pos.join(',')).join('<br>')||'No ammunition point in this battle.')+'</p>':''}`;
  $('unit-action-target').textContent=needsHex?(destination?'Selected hex '+destination.join(','):'Choose '+(unitAction==='split'?'an adjacent':'a destination')+' hex on the map.') :unitAction==='combine'?'The selected unit survives. Troops and ammunition join it.':unitAction==='order'?'Instructions take effect on receipt. Start the clock after sending.':'The commander will hold and defend the current position.';
  $('unit-action-submit').disabled=Boolean(readOnly||(needsHex&&!destination)||(unitAction==='combine'&&!candidates.length));
  $('unit-action-submit').textContent=unitAction==='split'?'Send split instructions':unitAction==='combine'?'Send combine instructions':'Send order';
  const advice=(state.recommendations||[]).filter(r=>r.unit_id===u.id&&r.status!=='en_route').slice(-2).reverse();
  $('unit-recommendations').innerHTML=advice.map(r=>`<article class="recommendation"><strong>⚑ Commander recommends ${(state.order_templates||[]).find(t=>t.id===r.proposal.stance)?.label||esc(r.proposal.stance)}</strong><p>${esc(r.text)}</p><small>Observed ${clock(r.created_turn)} · ${r.received_turn!==undefined?'received '+clock(r.received_turn):'not received'} · ${esc(r.status)}${r.expires_turn!==undefined?' · expires '+clock(r.expires_turn):''}${r.proposal.destination?' · hex '+r.proposal.destination.join(','):''}</small><p class="advice-evidence">At report: ${r.evidence.ammo} rounds · fatigue ${r.evidence.fatigue}% · morale ${r.evidence.morale}%</p><div class="unit-form-buttons"><button data-advice-id="${esc(r.id)}" data-response="dismiss" ${readOnly||['accepted','dismissed'].includes(r.status)?'disabled':''}>Dismiss</button><button data-advice-id="${esc(r.id)}" data-response="accept" ${readOnly||r.status!=='delivered'?'disabled':''}>Dispatch suggested order</button></div></article>`).join('');
  const ops=(state.formation_ops||[]).filter(o=>o.unit_id===u.id||o.partner_id===u.id);
  $('unit-operations').innerHTML=ops.slice(-3).map(o=>`<p>${esc(o.id)} · ${esc(o.kind)} · ${esc(o.status.replaceAll('_',' '))}${o.reason?'<br>'+esc(o.reason):''}</p>`).join('');
}
function chooseUnitAction(action){unitAction=action;destination=null;renderMap();renderControls();}
$('unit-close').onclick=()=>{selected=null;unitAction=null;destination=null;renderMap();renderUnits();renderControls();};
$('unit-move').onclick=()=>chooseUnitAction('move');
$('unit-order').onclick=()=>chooseUnitAction('order');
$('unit-hold').onclick=()=>$('hold-order').onclick();
$('unit-split').onclick=()=>chooseUnitAction('split');
$('unit-combine').onclick=()=>chooseUnitAction('combine');
$('unit-order-kind').onchange=()=>{destination=null;renderMap();renderControls();};
$('unit-action-cancel').onclick=()=>{unitAction=null;destination=null;renderMap();renderControls();};
$('unit-action-form').onsubmit=async e=>{
  e.preventDefault();if(!selected||busy||replay||godMode)return;
  let result;
  if(unitAction==='split'||unitAction==='combine'){
    const instruction={kind:unitAction,unit_id:selected,...(unitAction==='split'?{count:Number($('unit-split-count').value),destination}:{partner_id:$('unit-combine-target').value})};
    result=await post('/api/formations',{instruction});
  }else{
    const stance=unitAction==='move'?'move':$('unit-order-kind').value;
    result=await post('/api/orders',{orders:[{unit_id:selected,stance,destination:['move','retreat','recon'].includes(stance)?destination:null}]});
  }
  if(result){unitAction=null;destination=null;render();toast('Instructions dispatched. Start the clock to carry them out.');}
};
function selectUnit(id){selected=id;destination=null;unitAction=null;const u=state.units.find(u=>u.id===id);$('unit-split-count').value=u?Math.floor(u.strength/2):20;renderMap();renderUnits();renderControls();if(window.matchMedia('(max-width:760px)').matches)$('unit-detail').scrollIntoView({behavior:'smooth',block:'start'});}
$('unit-recommendations').onclick=async e=>{
  const button=e.target.closest('[data-advice-id]');if(!button||button.disabled)return;
  const result=await post('/api/recommendations',{recommendation_id:button.dataset.adviceId,response:button.dataset.response});
  if(result)toast(button.dataset.response==='accept'?'Suggested order dispatched. Start the clock for delivery.':'Recommendation dismissed. Standing orders continue.');
};
function inspectAdvice(uid){selectUnit(uid);$('unit-recommendations').scrollIntoView({behavior:'smooth',block:'nearest'});}
let mapPointerStart=null;
$('map').addEventListener('pointerdown',e=>{mapPointerStart=[e.clientX,e.clientY];});
$('map').addEventListener('click',e=>{if(mapPointerStart&&Math.hypot(e.clientX-mapPointerStart[0],e.clientY-mapPointerStart[1])>5)return;const advice=e.target.closest('[data-advice-unit]');if(advice){inspectAdvice(advice.dataset.adviceUnit);return;}const contact=e.target.closest('[data-contact]');if(contact){selectUnit('contact:'+contact.dataset.contact);return;}const marker=e.target.closest('[data-unit]');if(marker){selectUnit(marker.dataset.unit);return;}const hex=e.target.closest('[data-c]');if(hex&&selected&&!replay&&!godMode){destination=[+hex.dataset.c,+hex.dataset.r];renderMap();renderControls();}else if(hex&&!selected)toast(godMode?'Select a formation to inspect it.':'Select a blue unit first.');});
$('map').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){const advice=e.target.closest('[data-advice-unit]');if(advice){e.preventDefault();inspectAdvice(advice.dataset.adviceUnit);return;}const marker=e.target.closest('[data-unit]');if(marker){e.preventDefault();selectUnit(marker.dataset.unit);}else{const contact=e.target.closest('[data-contact]');if(contact){e.preventDefault();selectUnit('contact:'+contact.dataset.contact);}}}});
$('unit-list').addEventListener('click',e=>{const card=e.target.closest('[data-unit]');if(card)selectUnit(card.dataset.unit);});
$('send-order').onclick=async()=>{const result=await post('/api/orders',{orders:[{unit_id:selected,stance:'move',destination}]});if(result){destination=null;render();toast('Order issued. Start the clock to continue.');}};
$('hold-order').onclick=async()=>{const result=await post('/api/orders',{orders:[{unit_id:selected,stance:'hold',destination:null}]});if(result){destination=null;render();toast('Hold order dispatched.');}};
$('clock-toggle').onclick=async()=>{
  if(replay){if(replayPlaying)stopReplay();else{if(replayIndex>=history.length-1)await loadReplay(0);replayPlaying=true;scheduleReplay();}renderControls();}
  else await controlClock(state.clock.running?'pause':'start');
};
function changeSpeed(direction){
  const rate=replay?replaySpeed:state.clock.speed,next=speeds[Math.max(0,Math.min(speeds.length-1,speeds.indexOf(rate)+direction))];
  if(replay){replaySpeed=next;clearTimeout(replayTimer);if(replayPlaying)scheduleReplay();renderControls();}
  else controlClock('speed',next);
}
$('clock-slower').onclick=()=>changeSpeed(-1);$('clock-faster').onclick=()=>changeSpeed(1);
$('new-game').onclick=async()=>{
  if(busy)return;
  stopReplay();
  if(replay){replay=false;state=liveState;$('replay-bar').classList.add('hidden');}
  const r=await post('/api/new');
  if(r){selected=null;destination=null;unitAction=null;history=[];replayIndex=0;godEventLimit=60;render();toast('Battle reset to 16:30. Clock paused; previous battle archived.');}
};
$('ai-mode').onchange=()=>post('/api/mode',{mode:$('ai-mode').value});
$('hex-toggle').onclick=()=>{hexes=!hexes;$('hex-toggle').classList.toggle('active',hexes);$('hex-toggle').setAttribute('aria-pressed',hexes);renderMap();};
$('terrain-toggle').onclick=()=>{terrain=!terrain;$('terrain-toggle').classList.toggle('active',terrain);$('terrain-toggle').setAttribute('aria-pressed',terrain);renderMap();};
function tab(name){const chat=name==='chat';$('chat-panel').classList.toggle('hidden',!chat);$('dispatch-panel').classList.toggle('hidden',chat);for(const n of ['chat','dispatch']){$(n+'-tab').classList.toggle('active',n===name);$(n+'-tab').setAttribute('aria-selected',n===name);}if(chat)$('chat-input').focus();}
$('chat-tab').onclick=()=>tab('chat');$('dispatch-tab').onclick=()=>tab('dispatch');
$('chat-form').onsubmit=async e=>{e.preventDefault();const text=$('chat-input').value.trim();if(!text)return;const result=await post('/api/chat',{text});if(result)$('chat-input').value='';};
$('messages').onclick=async e=>{const button=e.target.closest('[data-proposal]');if(!button)return;const msg=(state.messages||[]).find(m=>m.id===+button.dataset.proposal);if(!msg)return;const result=await post('/api/orders',{orders:msg.proposals});if(result)toast('Proposed orders dispatched.');};
function stopReplay(){replayPlaying=false;clearTimeout(replayTimer);replayGeneration++;}
function scheduleReplay(){
  if(!replayPlaying||!replay)return;
  if(replayIndex>=history.length-1){stopReplay();renderControls();return;}
  const delay=Math.max(100,elapsedSeconds(history[replayIndex+1].turn-history[replayIndex].turn)*1000/replaySpeed);
  const generation=replayGeneration;
  replayTimer=setTimeout(async()=>{if(generation!==replayGeneration)return;await loadReplay(replayIndex+1);if(generation===replayGeneration)scheduleReplay();},delay);
}
$('history-toggle').onclick=async()=>{
  if(busy)return;if(replay)return;
  busy=true;viewEpoch++;renderControls();
  try{await pauseLive();history=await get('/api/history?game_id='+state.game_id);liveState=state;replay=true;replaySpeed=state.clock.speed;
    $('replay-bar').classList.remove('hidden');$('replay-slider').max=history.length-1;await loadReplay(0);
  }catch(e){toast(e.message);}finally{busy=false;renderControls();}
};
async function loadReplay(i){
  const generation=replayGeneration;
  try{const data=await get('/api/replay?game_id='+liveState.game_id+'&revision='+history[i].revision+(godMode?'&view=god':''));
    if(!replay||generation!==replayGeneration)return;
    replayIndex=i;state={...data,mode:liveState.mode,messages:[]};$('replay-slider').value=i;
    render();return true;
  }catch(e){stopReplay();toast(e.message);renderControls();return false;}
}
$('replay-slider').oninput=async e=>{stopReplay();await loadReplay(+e.target.value);};
$('live-view').onclick=async()=>{stopReplay();viewEpoch++;try{state=await get(stateUrl());liveState=state;replay=false;$('replay-bar').classList.add('hidden');render();}catch(e){toast(e.message);}};
async function poll(){
  const epoch=viewEpoch;
  try{if(!busy&&!replay){const fresh=await get(stateUrl());if(!busy&&!replay&&epoch===viewEpoch){const changed=!state||fresh.game_id!==state.game_id||fresh.revision!==state.revision;state=fresh;liveState=state;if(changed)render();else renderControls();}}}
  catch(e){if(!replay)toast('Clock connection interrupted. The server may still be running.');}
  finally{setTimeout(poll,500);}
}
(async()=>{try{[state,mapData]=await Promise.all([get(stateUrl()),get('/api/map')]);liveState=state;render();BattleMapView.init(mapData.cells,renderMap);setTimeout(poll,500);}catch(e){toast('Could not connect to the local simulation: '+e.message);}})();

