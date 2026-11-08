/* Original vector cartography from the public scenario terrain; no imagery or tiles. */
const BattleMap = (() => {
  const palette = {open:'#e8f0df', woods:'#b9ddbc', rocky:'#dce2dc', water:'#b9d3e3', marsh:'#d7e3cf'};  // water, marsh: docs/research/72
  const xy = p => [(p[0]+.5*(p[1]&1))*Math.sqrt(3)*25.5+24,p[1]*38.25+26];
  const vertices = p => {const [x,y]=xy(p);return Array.from({length:6},(_,i)=>{const a=(60*i-30)*Math.PI/180;return [x+25.5*Math.cos(a),y+25.5*Math.sin(a)];});};
  let cachedCells, cachedDetail, cachedAnnotations, cachedSVG, contourCells, contourCache;
  function contoursFor(cells){
    if(cells===contourCells)return contourCache;
    const lookup=new Map(cells.map(c=>[c.pos.join(','),c]));
    const triangles=[];
    for(const a of cells){
      const [c,r]=a.pos,offset=r&1;
      for(const pair of [[[c+1,r],[c+offset,r+1]],[[c+offset-1,r+1],[c+offset,r+1]]]){
        const b=lookup.get(pair[0].join(',')),d=lookup.get(pair[1].join(','));
        if(b&&d)triangles.push([a,b,d]);
      }
    }
    const contours=[];
    if(cells.length){
      const low=Math.min(...cells.map(c=>c.elevation)),high=Math.max(...cells.map(c=>c.elevation));
      for(let level=Math.ceil(low/5)*5;level<high;level+=5){
        const segments=[];
        for(const tri of triangles){
          const hits=[];
          for(let i=0;i<3;i++){
            const a=tri[i],b=tri[(i+1)%3];
            if((a.elevation<level)===(b.elevation<level))continue;
            const t=(level-a.elevation)/(b.elevation-a.elevation),p=xy(a.pos),q=xy(b.pos);
            hits.push([p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t]);
          }
          if(hits.length===2)segments.push(hits);
        }
        if(segments.length)contours.push({level,segments});
      }
    }
    contourCells=cells;contourCache=contours;return contours;
  }
  function render(cells, detail=false, annotationsOnly=false) {
    if(cells===cachedCells&&detail===cachedDetail&&annotationsOnly===cachedAnnotations)return cachedSVG;
    const contours=contoursFor(cells);
    let svg='<g class="cartography" pointer-events="none">'+(annotationsOnly?'':'<rect width="1080" height="840" fill="#e8f0df"/>');
    if(!annotationsOnly)for(const cell of cells){
      const color=palette[cell.terrain]||palette.open;
      svg+=`<polygon points="${vertices(cell.pos).map(p=>p.join(',')).join(' ')}" fill="${color}" stroke="${color}" stroke-width="1"/>`;
      if(detail){const opacity=Math.max(0,Math.min(.3,(cell.elevation-145)/150));svg+=`<polygon points="${vertices(cell.pos).map(p=>p.join(',')).join(' ')}" fill="#6b8264" opacity="${opacity}"/>`;}
    }
    for(const {level,segments} of contours){
      const major=level%10===0;
      if(!annotationsOnly)svg+=`<path d="${segments.map(([a,b])=>`M${a.join(',')}L${b.join(',')}`).join('')}" fill="none" stroke="#8ca58a" stroke-width="${major?1.6:1}" opacity="${detail?.75:.38}" stroke-linecap="round"/>`;
      if(detail&&major){
        const [point]=segments[Math.floor(segments.length*.2)];
        svg+=`<text x="${point[0]}" y="${point[1]}" class="contour-label">${level} m</text>`;
      }
    }
    for(const cell of cells){
      const [c,r]=cell.pos,[x,y]=xy(cell.pos);
      if(c%3!==0||r%3!==0)continue;
      if(cell.terrain==='woods')svg+=`<g transform="translate(${x},${y})" opacity=".48"><path d="M0,-10L-6,1H-4L-8,7H8L4,1H6Z" fill="#78aa81"/><path d="M0,7V11" stroke="#6b9572" stroke-width="2"/></g>`;
      if(cell.terrain==='rocky')svg+=`<path d="M${x-7},${y+4}l5,-9 6,2 4,7z" fill="#bbc6bc" stroke="#9aa99d" stroke-width="1"/>`;
    }
    svg+='<text x="210" y="285" class="terrain-label">OPEN GROUND</text><text x="350" y="740" class="terrain-label woods-label">WOODLAND</text><text x="850" y="600" class="terrain-label">OPEN GROUND</text>';
    if(!annotationsOnly)svg+='<g transform="translate(830,756)" class="vector-scale"><path d="M0,0V6H88.33V0M44.16,2V6"/><text x="0" y="24">0</text><text x="88.33" y="24" text-anchor="end">100 m</text></g>';
    svg+='</g>';
    cachedCells=cells;cachedDetail=detail;cachedAnnotations=annotationsOnly;cachedSVG=svg;return svg;
  }
  function geojson(cells, coordinate){
    const features=cells.map((cell,i)=>{
      const ring=vertices(cell.pos).map(coordinate);ring.push(ring[0]);
      return {type:'Feature',id:i,properties:{kind:'surface',terrain:cell.terrain,elevation:cell.elevation},geometry:{type:'Polygon',coordinates:[ring]}};
    });
    for(const {level,segments} of contoursFor(cells))features.push({type:'Feature',properties:{kind:'contour',level,major:level%10===0},geometry:{type:'MultiLineString',coordinates:segments.map(segment=>segment.map(coordinate))}});
    return {type:'FeatureCollection',features};
  }
  return {render,geojson};
})();
