/* MapLibre owns rendering/camera only. Scene coordinates never enter simulation state. */
const BattleMapView = (() => {
  const metresPerPixel=50/(Math.sqrt(3)*25.5), radius=6378137;
  let fitZoom=15;
  let map, ready=false, failed=false, detail=false, resizeObserver, startupTimer;
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
  function init(cells,onChange){
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
          {id:'terrain',type:'fill',source:'scenario',filter:['==',['get','kind'],'surface'],paint:{'fill-color':['match',['get','terrain'],'woods','#b9ddbc','rocky','#dce2dc','#e8f0df'],'fill-antialias':false}},
          {id:'relief',type:'fill',source:'scenario',filter:['==',['get','kind'],'surface'],paint:{'fill-color':'#6b8264','fill-opacity':0,'fill-antialias':false}},
          {id:'contours',type:'line',source:'scenario',filter:['==',['get','kind'],'contour'],paint:{'line-color':'#8ca58a','line-width':['case',['get','major'],1.6,1],'line-opacity':.38}}
        ]}});
      map.touchZoomRotate.disableRotation();
      const bounds=[coordinate([0,840]),coordinate([1080,0])];
      function fit(){map.fitBounds(bounds,{padding:10,duration:0});fitZoom=map.getZoom();syncOverlay();}
      map.on('error',fallback);
      map.on('load',()=>{
        if(failed)return;clearTimeout(startupTimer);ready=true;
        document.getElementById('map-wrap').classList.add('vector-active');
        map.getCanvasContainer().appendChild(svg);
        fit();map.setMinZoom(map.getZoom()-.5);map.setMaxZoom(map.getZoom()+2.5);
        map.setMaxBounds([coordinate([-540,1260]),coordinate([1620,-420])]);
        badge.textContent='MapLibre · local vector tiles';
        document.getElementById('live-map-scale').classList.remove('hidden');
        document.getElementById('map-camera').classList.remove('hidden');
        document.getElementById('map-in').onclick=()=>map.zoomIn({duration:180});
        document.getElementById('map-out').onclick=()=>map.zoomOut({duration:180});
        document.getElementById('map-fit').onclick=fit;
        map.on('move',syncOverlay);
        map.on('resize',syncOverlay);
        resizeObserver=new ResizeObserver(()=>map.resize());resizeObserver.observe(host);
        applyStyle();onChange();syncOverlay();
      });
      startupTimer=setTimeout(fallback,12000);
    }catch{fallback();}
  }
  function update(elevation){if(detail!==elevation){detail=elevation;applyStyle();}syncOverlay();}
  return {init,update,coordinate,active:()=>ready};
})();
