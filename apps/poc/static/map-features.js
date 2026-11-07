/* Roads, buildings and fieldworks drawn from the commander's map_features (the
 * observer-visible features the engine routes, covers and sights with).
 * A separate module so scripts/check_map_features.mjs renders the same SVG. */
const BattleFeatures = (() => {
  // Why: the command map must show the features the engine moves and sees by.
  // What: one SVG group; a road is one path through its authored points, a
  // building a closed rect at its hex, a fortification a breastwork mark.
  // Independent of the hex-grid toggle. Test: scripts/check_map_features.mjs.
  function render(features, center, esc) {
    let svg='<g class="battle-features" pointer-events="none">';
    for(const f of features||[]){
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
  return {render};
})();
