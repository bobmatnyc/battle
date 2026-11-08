/* MapLibre owns rendering/camera only. Scene coordinates never enter simulation state. */
const BattleMapView = (() => {
  const metresPerPixel=50/(Math.sqrt(3)*25.5), radius=6378137;
  let fitZoom=15;
  let sceneCells, map, ready=false, failed=false, detail=false, resizeObserver, startupTimer, focus=null;
  // bt-T18 (docs/research/81 §3): the centre for a zoom-in, in scene pixels, given the current centre, the
  // new frame's half size and the focus {core, all}: boxes [x0,y0,x1,y1] of the objective with its label
  // (core) and of the objective with every point mark (all). Per axis: the least move that keeps `all` in
  // frame; if it is larger than the frame, the least move that keeps `core` in frame; if that is larger
  // too, the middle of `core`. Then the frame is kept on the 1080 x 840 scene. No focus: the current
  // centre (the zoom as before).
  function focusCentre(centre,half,focus){
    if(!focus)return centre;
    const fit=(c,h,lo,hi)=>hi-lo<=2*h?Math.min(Math.max(c,hi-h),lo+h):null;
    const axis=(i,size)=>{
      const c=centre[i],h=half[i],{core,all}=focus;
      const v=fit(c,h,all[i],all[i+2])??fit(c,h,core[i],core[i+2])??(core[i]+core[i+2])/2;
      return 2*h>=size?size/2:Math.min(Math.max(v,h),size-h);
    };
    return [axis(0,1080),axis(1,840)];
  }
  // One zoom step in about the focus; the fit view and the zoom-out step are unchanged.
  function zoomIn(){
    const zoom=Math.min(map.getZoom()+1,map.getMaxZoom()),k=Math.pow(2,zoom-map.getZoom());
    const a=map.project(coordinate([0,0])),b=map.project(coordinate([1080,840]));
    const sx=1080/(b.x-a.x),sy=840/(b.y-a.y),{clientWidth:w,clientHeight:h}=map.getContainer();
    const centre=focusCentre([(w/2-a.x)*sx,(h/2-a.y)*sy],[w/2*sx/k,h/2*sy/k],focus);
    map.easeTo({zoom,center:coordinate(centre),duration:180});
  }
  // bt-T23 (docs/research/80 §7): the part of the 1080 x 840 scene the map frame shows, in scene pixels
  // {x0,y0,x1,y1}, which no feature label may cross. The whole scene at the fit view and in the SVG fallback.
  function frame(){
    const scene={x0:0,y0:0,x1:1080,y1:840};
    if(!ready)return scene;
    const a=map.project(coordinate([0,0])),b=map.project(coordinate([1080,840])),{clientWidth:w,clientHeight:h}=map.getContainer();
    const sx=1080/(b.x-a.x),sy=840/(b.y-a.y);
    return {x0:Math.max(0,-a.x*sx),y0:Math.max(0,-a.y*sy),x1:Math.min(1080,(w-a.x)*sx),y1:Math.min(840,(h-a.y)*sy)};
  }
  const coordinate=([x,y])=>{
    const east=(x-540)*metresPerPixel,north=(420-y)*metresPerPixel;
    return [east/radius*180/Math.PI,(2*Math.atan(Math.exp(north/radius))-Math.PI/2)*180/Math.PI];
  };
  function syncOverlay(){
    if(!ready)return;
    const a=map.project(coordinate([0,0])),b=map.project(coordinate([1080,840]));
    const svg=document.getElementById('map');
    Object.assign(svg.style,{left:a.x+'px',top:a.y+'px',width:(b.x-a.x)+'px',height:(b.y-a.y)+'px'});
    const zoom=document.getElementById('map-zoom');
    const pixelsPerMetre=(b.x-a.x)/(1080*metresPerPixel);
    const distance=[10,20,50,100,200,500].filter(m=>m*pixelsPerMetre<=110).at(-1)||10;
    document.getElementById('live-scale-line').style.width=(distance*pixelsPerMetre)+'px';
    document.getElementById('live-scale-label').textContent=distance+' m';
    zoom.textContent=`${(Math.pow(2,map.getZoom()-fitZoom)).toFixed(1)}× view`;
  }
  function applyStyle(){
    if(!ready)return;
    map.setPaintProperty('relief','fill-opacity',detail?['interpolate',['linear'],['get','elevation'],145,0,190,.3]:0);
    map.setPaintProperty('contours','line-opacity',detail?.75:.38);
  }
  // A new scenario brings new terrain; MapLibre keeps the cells it was built with.
  function setCells(cells){
    sceneCells=cells;
    if(ready)map.getSource('scenario').setData(BattleMap.geojson(cells,coordinate));
  }
  function init(cells,onChange){
    sceneCells=cells;
    const badge=document.getElementById('map-renderer'),host=document.getElementById('vector-map'),svg=document.getElementById('map');
    function fallback(){
      if(failed)return;failed=true;ready=false;clearTimeout(startupTimer);
      if(resizeObserver)resizeObserver.disconnect();
      document.getElementById('map-wrap').appendChild(svg);svg.removeAttribute('style');
      if(map){map.remove();map=null;}
      document.getElementById('live-map-scale').classList.add('hidden');
      host.classList.add('hidden');document.getElementById('map-camera').classList.add('hidden');
      document.getElementById('map-wrap').classList.remove('vector-active');
      badge.textContent='SVG fallback · vector renderer unavailable';onChange();
    }
    try{
      if(typeof maplibregl==='undefined')return fallback();
      maplibregl.setWorkerUrl('/vendor/maplibre/maplibre-gl-csp-worker.js');
      maplibregl.setWorkerCount(1);
      badge.textContent='Loading MapLibre…';
      map=new maplibregl.Map({container:host,attributionControl:false,renderWorldCopies:false,
        dragRotate:false,pitchWithRotate:false,touchPitch:false,maxPitch:0,fadeDuration:0,
        center:coordinate([540,420]),zoom:15,minZoom:13,maxZoom:19,
        style:{version:8,sources:{scenario:{type:'geojson',data:BattleMap.geojson(cells,coordinate),maxzoom:20,tolerance:0,buffer:64}},layers:[
          {id:'background',type:'background',paint:{'background-color':'#e8f0df'}},
          {id:'terrain',type:'fill',source:'scenario',filter:['==',['get','kind'],'surface'],paint:{'fill-color':['match',['get','terrain'],'woods','#b9ddbc','rocky','#dce2dc','water','#b9d3e3','marsh','#d7e3cf','#e8f0df'],'fill-antialias':false}},
          {id:'relief',type:'fill',source:'scenario',filter:['==',['get','kind'],'surface'],paint:{'fill-color':'#6b8264','fill-opacity':0,'fill-antialias':false}},
          {id:'contours',type:'line',source:'scenario',filter:['==',['get','kind'],'contour'],paint:{'line-color':'#8ca58a','line-width':['case',['get','major'],1.6,1],'line-opacity':.38}}
        ]}});
      map.touchZoomRotate.disableRotation();
      const bounds=[coordinate([0,840]),coordinate([1080,0])];
      function fit(){map.fitBounds(bounds,{padding:10,duration:0});fitZoom=map.getZoom();syncOverlay();}
      map.on('error',fallback);
      map.on('load',()=>{
        if(failed)return;clearTimeout(startupTimer);ready=true;
        map.getSource('scenario').setData(BattleMap.geojson(sceneCells,coordinate));
        document.getElementById('map-wrap').classList.add('vector-active');
        map.getCanvasContainer().appendChild(svg);
        fit();map.setMinZoom(map.getZoom()-.5);map.setMaxZoom(map.getZoom()+2.5);
        map.setMaxBounds([coordinate([-540,1260]),coordinate([1620,-420])]);
        badge.textContent='MapLibre · local vector tiles';
        document.getElementById('live-map-scale').classList.remove('hidden');
        document.getElementById('map-camera').classList.remove('hidden');
        document.getElementById('map-in').onclick=zoomIn;
        document.getElementById('map-out').onclick=()=>map.zoomOut({duration:180});
        document.getElementById('map-fit').onclick=fit;
        map.on('move',syncOverlay);
        map.on('moveend',onChange);  // bt-T23: labels are placed again inside the new frame.
        map.on('resize',syncOverlay);
        resizeObserver=new ResizeObserver(()=>map.resize());resizeObserver.observe(host);
        applyStyle();onChange();syncOverlay();
      });
      startupTimer=setTimeout(fallback,12000);
    }catch{fallback();}
  }
  function update(elevation,box=null){focus=box;if(detail!==elevation){detail=elevation;applyStyle();}syncOverlay();}
  return {init,setCells,update,coordinate,focusCentre,frame,active:()=>ready};
})();
