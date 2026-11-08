import * as THREE from './vendor/three.module.js';

// Standalone presentation. Loads bundled model data only; no coordinator or hardware API.
const $ = s => document.querySelector(s);
const stages = [
 {t:0,name:'Underway',sub:'Deck watch active',title:'Ready to respond.',copy:'The vessel is underway. The swarm and rescue USV are ready to launch.'},
 {t:3,name:'Man overboard',sub:'Rapid separation',title:'The distance grows.',copy:'Accelerated scenario time shows the person drifting far from the vessel while the ship continues forward.'},
 {t:5,name:'Dispersed search',sub:'Wide UAV grid · slow local USV sweep',title:'Cover the ocean. Divide the work.',copy:'Five aircraft spread into separate offshore lane groups. The USV searches a small box near the launch point at a deliberately slow pace.'},
 {t:32,name:'Positive lock',sub:'Swarm converges · USV accelerates',title:'Found. Bring the response together.',copy:'A scripted sighting confirms the person. The swarm collapses into a compact observation formation; the USV accelerates directly toward the fix. The ship turns back.'},
 {t:36,name:'Closing distance',sub:'Continuous visual contact',title:'Watch the gap close.',copy:'The drones hold the person in view. The USV closes the remaining distance rapidly while the vessel stays clear of the final approach.'},
 {t:49,name:'Rendezvous',sub:'USV on scene · mission complete',title:'Help has arrived.',copy:'The USV reaches the person while the drones maintain observation. The simulation ends here; physical recovery is not depicted.'}
];
let endTime=49;
let story=null;
const storyFrame=()=>story?.frames[Math.min(endTime,Math.max(0,Math.floor(time)))];
// Cubic interpolation keeps velocity continuous between baked one-second samples.
const storyPoint=(key,i=null,at=time)=>{
 const n=Math.floor(at),u=at-n,points=[-1,0,1,2].map(k=>{const v=story.frames[Math.max(0,Math.min(endTime,n+k))][key];return i===null?v:v[i];});
 return [0,1].map(j=>{const [a,b,c,d]=points.map(p=>p[j]);return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u);});
};
const guides=[
 {t:0,title:'One alert. A coordinated response.',text:'Press Play once. Each phase card advances automatically after three seconds.'},
 {t:3,title:'The person is drifting away.',text:'Scenario time is accelerated to reveal a large separation. The vessel continues ahead; the offshore search area clears the ship.'},
 {t:8,title:'Spread out. Search separate lanes.',text:'Five UAVs fan out into distinct, drift-following back-and-forth lane groups. Scan cones activate only after reaching the search grid, clear of the ship.'},
 {t:18,title:'Two searches. Different speeds.',text:'The selected grid moves with the forecast drift. It scored best among 36 layouts under an assumed detection model. The USV sweeps slowly along the current near its launch point.'},
 {t:32,title:'Positive lock. Converge and intercept.',text:'The swarm contracts into a compact formation around the observed person. The uncertainty region tightens, the USV accelerates, and the ship turns back.'},
 {t:36,title:'Closing the rescue gap.',text:'Continuous aerial observation guides the faster USV approach. Watch the remaining-distance readout count down. There is no contact-loss sequence.'}
];
let seenGuides=new Set(),guideRemaining=0;
function hideGuide(){ $('#guide').hidden=true;guideRemaining=0; }
function showGuide(g){guideRemaining=3;$('#guide-label').textContent='NEXT IN 3s · AUTO PLAY';$('#guide-title').textContent=g.title;$('#guide-copy').textContent=g.text;$('#guide').hidden=false;updatePanel();}
$('#guide-next').onclick=()=>{hideGuide();playing=true;updatePanel();};
$('#guided').onchange=()=>{if(!$('#guided').checked)hideGuide();};


let time=0, playing=false, speed=1, lastFrame=performance.now(), lastStage=-1;
let reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const stageAt=t=>Math.max(0,stages.findLastIndex(s=>t>=s.t));
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x);};
const phaseFrac=(a,b)=>ease((time-a)/(b-a));
const format=t=>`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}`;
$('#steps').innerHTML=stages.map((s,i)=>`<button class="step" data-step="${i}" aria-label="Jump to ${s.name}"><span class="num">${String(i+1).padStart(2,'0')}</span><span>${s.name}<small>${s.sub}</small></span></button>`).join('');
document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>{{time=stages[+b.dataset.step].t;playing=false;hideGuide();seenGuides=new Set(guides.filter(g=>g.t<time));updatePanel();}});
$('#play').onclick=()=>{if(time>=endTime){time=0;seenGuides.clear();}playing=!playing;updatePanel();};
$('#reset').onclick=()=>{time=0;playing=false;hideGuide();seenGuides.clear();updatePanel();};
$('#scrubber').oninput=e=>{time=+e.target.value;playing=false;hideGuide();seenGuides=new Set(guides.filter(g=>g.t<time));updatePanel();};
$('#speed').onchange=e=>{speed=+e.target.value;};
document.addEventListener('keydown',e=>{if(e.code==='Space'&&!['INPUT','SELECT','BUTTON'].includes(document.activeElement.tagName)){e.preventDefault();$('#play').click();}});

function updatePanel(){
  const idx=stageAt(time),s=stages[idx];
  document.querySelectorAll('.step').forEach((b,i)=>{b.classList.toggle('current',i===idx);b.classList.toggle('done',i<idx);b.setAttribute('aria-current',i===idx?'step':'false');});
  $('#step-number').textContent=`0${idx+1} / 06`;
  $('#brief-label').textContent=`0${idx+1} / ${s.name.toUpperCase()}`;
  $('#brief-title').textContent=s.title;$('#brief-copy').textContent=s.copy;
  $('#time').textContent=format(time);$('#scrubber').value=time;
  $('#play').textContent=playing?'Ⅱ Pause':time>=endTime?'↺ Replay mission':'▶ Play mission';
  $('#mission-state').textContent=s.name.toUpperCase();
  $('#contact-state').textContent=idx===0?'ON WATCH':idx<3?'SEARCHING':'POSITIVE LOCK';
  $('#surface-state').textContent=idx<2?'ON STANDBY':idx===2?'SLOW LOCAL SWEEP':time>=endTime?'ON SCENE':'RAPID INTERCEPT';
  const f=storyFrame();
  if(f){ $('#model-time').textContent=format(f.model_s);$('#fix-age').textContent=format(f.since_fix_s);$('#model-area').textContent=Math.round(f.area90).toLocaleString()+' m²';$('#environment').textContent='Wind 2.77 · current 0.167 m/s';$('#model-status').textContent=f.rough?'WAVE OCCLUSION · COMMS HEALTHY · REPLANNING':f.observed?'FRESH FIX → CONTRACT ESTIMATE → INTERCEPT':'WIND + CURRENT + LEEWAY → PROBABILITY → SEARCH'; }
  if(story)$('#model-source').textContent='Drift-following search · best of 36 candidates under assumed detection. '+story.forcing+' · '+story.forcing_time+' UTC · 800 PIW-1 particles. 50% / 90% ensemble regions; uncalibrated.';
  $('#area-hud').textContent=time<3?'STANDBY':$('#model-area').textContent;
  $('#clock-hud').textContent=`Model ${$('#model-time').textContent} · since fix ${$('#fix-age').textContent}`;
  if(f){const p=storyPoint('observation'),b=storyPoint('boat');$('#rescue-gap').textContent=time>=endTime?'USV ON SCENE':time>=32?`USV → PERSON  ${Math.round(Math.hypot(p[0]-b[0],p[1]-b[1]))} m`:'USV · SLOW SEARCH NEAR LAUNCH';}

  lastStage=idx;
}

// Load baked model output; no server mutation or external service is involved.
try{const r=await fetch('./mission-drift.json');if(!r.ok)throw Error('Missing mission-drift.json');story=await r.json();endTime=story.duration;stages[5].t=endTime;$('#scrubber').max=endTime;$('#model-source').textContent=story.forcing+' · '+story.forcing_time+' UTC · 800 PIW-1 particles. 50% / 90% ensemble regions; uncalibrated.';initScene();}catch(e){$('#scene-error').hidden=false;$('#scene-error').textContent='3D rendering unavailable. Enable WebGL in a supported browser. '+e.message;}
function initScene(){
  const view=$('#viewport'),scene=new THREE.Scene();
  scene.background=new THREE.Color('#143143');scene.fog=new THREE.FogExp2('#143143',.0008);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(view.clientWidth,view.clientHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;view.appendChild(renderer.domElement);
  // A soft daylight environment gives glazing, painted metal and water reflected light.
  const skyCanvas=document.createElement('canvas');skyCanvas.width=1024;skyCanvas.height=512;
  const skyContext=skyCanvas.getContext('2d'),skyGradient=skyContext.createLinearGradient(0,0,0,512);
  skyGradient.addColorStop(0,'#557f9b');skyGradient.addColorStop(.45,'#c2d9e1');skyGradient.addColorStop(.52,'#e8e8d8');skyGradient.addColorStop(.6,'#597a86');skyGradient.addColorStop(1,'#203d4b');
  skyContext.fillStyle=skyGradient;skyContext.fillRect(0,0,1024,512);
  const sunGlow=skyContext.createRadialGradient(220,160,2,220,160,80);sunGlow.addColorStop(0,'rgba(255,247,219,1)');sunGlow.addColorStop(.15,'rgba(255,247,219,.7)');sunGlow.addColorStop(1,'rgba(255,247,219,0)');skyContext.fillStyle=sunGlow;skyContext.fillRect(0,0,1024,512);
  const skyTexture=new THREE.CanvasTexture(skyCanvas);skyTexture.mapping=THREE.EquirectangularReflectionMapping;skyTexture.colorSpace=THREE.SRGBColorSpace;
  const pmrem=new THREE.PMREMGenerator(renderer),environment=pmrem.fromEquirectangular(skyTexture);scene.environment=environment.texture;scene.environmentIntensity=.65;pmrem.dispose();skyTexture.dispose();
  const camera=new THREE.PerspectiveCamera(44,1,.1,1800),look=new THREE.Vector3(-20,0,8);
  let az=-1.85,el=.78,radius=235,drag=false,px=0,py=0;
  const presets={overview:[-1.85,.78,235,-20,8],deck:[1.2,.50,125,0,-6],rescue:[.7,.65,125,-30,-15]};
  let targetLook=look.clone(),cameraMode="overview";
  document.querySelectorAll('[data-camera]').forEach(b=>b.onclick=()=>{cameraMode=b.dataset.camera;[az,el,radius,targetLook.x,targetLook.z]=presets[b.dataset.camera];document.querySelectorAll('[data-camera]').forEach(x=>x.classList.toggle('selected',x===b));});
  view.addEventListener('pointerdown',e=>{drag=true;px=e.clientX;py=e.clientY;view.setPointerCapture(e.pointerId);});
  view.addEventListener('pointermove',e=>{if(!drag)return;az-=(e.clientX-px)*.006;el=clamp(el+(e.clientY-py)*.004,.15,1.3);px=e.clientX;py=e.clientY;});
  view.addEventListener('pointerup',()=>drag=false);view.addEventListener('pointercancel',()=>drag=false);
  view.addEventListener('wheel',e=>{e.preventDefault();radius=clamp(radius+e.deltaY*.08,55,320);},{passive:false});
  scene.add(new THREE.HemisphereLight('#adc8da','#062a37',2.4));const sun=new THREE.DirectionalLight('#ffdab2',3.1);sun.position.set(-80,120,-60);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-150,right:250,top:150,bottom:-150,near:1,far:500});sun.shadow.bias=-.001;scene.add(sun);
  const mat=(color,roughness=.65,metalness=.1)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
  const hullmat=mat('#4c6270'),deckmat=mat('#6c7f87'),white=mat('#d9e0d8'),dark=mat('#162a38'),orange=mat('#ff884b'),cyan=mat('#65dfd1');
  const glow=new THREE.MeshBasicMaterial({color:'#7ef7e0'}),warmGlow=new THREE.MeshBasicMaterial({color:'#ff9e65'});
  function mesh(g,m,parent,pos=[0,0,0]){const o=new THREE.Mesh(g,m);o.position.set(...pos);o.castShadow=!m.transparent;o.receiveShadow=true;parent.add(o);return o;}
  const box=(p,x,y,z,w,h,d,m)=>mesh(new THREE.BoxGeometry(w,h,d),m,p,[x,y,z]);
  function line(p,pts,color='#77b6bf',opacity=.6){const o=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(a=>new THREE.Vector3(...a))),new THREE.LineBasicMaterial({color,transparent:true,opacity,fog:false}));p.add(o);return o;}
  function ring(parent,r,color,y=.15){const o=mesh(new THREE.RingGeometry(r-.12,r+.12,100),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide,transparent:true,opacity:.6}),parent,[0,y,0]);o.rotation.x=-Math.PI/2;return o;}
  // Ocean surface, translucent grid and soft wave motion.
  const oceanG=new THREE.PlaneGeometry(2400,2400,240,240);oceanG.rotateX(-Math.PI/2);
  const ocean=mesh(oceanG,new THREE.MeshPhysicalMaterial({color:'#0b4655',roughness:.25,metalness:.05,clearcoat:1,clearcoatRoughness:.16,flatShading:false}),scene);
  ocean.castShadow=false;
  // Fine capillary normals complement the larger geometric swell.
  const normalCanvas=document.createElement('canvas');normalCanvas.width=normalCanvas.height=256;
  const nc=normalCanvas.getContext('2d'),pixels=nc.createImageData(256,256);
  for(let y=0;y<256;y++)for(let x=0;x<256;x++){const k=(y*256+x)*4;pixels.data[k]=128+22*Math.sin(x*.49+y*.19)+12*Math.cos(y*.74);pixels.data[k+1]=128+20*Math.cos(y*.39-x*.22);pixels.data[k+2]=245;pixels.data[k+3]=255;}
  nc.putImageData(pixels,0,0);const normalMap=new THREE.CanvasTexture(normalCanvas);normalMap.wrapS=normalMap.wrapT=THREE.RepeatWrapping;normalMap.repeat.set(195,195);ocean.material.normalMap=normalMap;ocean.material.normalScale.set(.6,.6);
  const positions=oceanG.attributes.position,base=positions.array.slice();
  const grid=new THREE.GridHelper(2000,100,'#2a7180','#1c596b');grid.position.y=-.45;grid.material.transparent=true;grid.material.opacity=.035;scene.add(grid);
  // Ship points along the x axis. Procedural hull includes a pointed bow.
  const ship=new THREE.Group();scene.add(ship);ship.position.set(-25,0,-10);
  const shape=new THREE.Shape();shape.moveTo(-45,-9);shape.lineTo(27,-9);shape.quadraticCurveTo(42,-8,49,0);shape.quadraticCurveTo(42,8,27,9);shape.lineTo(-45,9);shape.closePath();
  const hg=new THREE.ExtrudeGeometry(shape,{depth:6,bevelEnabled:true,bevelSize:1.1,bevelThickness:.5,bevelSegments:2,steps:1});hg.rotateX(-Math.PI/2);
  mesh(hg,hullmat,ship,[0,0,0]);
  box(ship,-4,6.3,0,78,.5,16.8,deckmat);box(ship,4,10,0,22,7,12,white);box(ship,7,14.4,0,14,2,10,white);box(ship,8,14.3,-5.1,12,1.2,.15,dark);box(ship,8,14.3,5.1,12,1.2,.15,dark);box(ship,15.1,14.3,0,.2,1.2,9,dark);
  box(ship,-8,13,0,6,6,6,dark);box(ship,-8,16.2,0,6.5,.4,6.5,deckmat);
  const mast=mesh(new THREE.CylinderGeometry(.22,.38,14,8),white,ship,[3,22,0]);box(ship,3,24,0,.5,.5,15,white);box(ship,3,28,0,6,.3,1,white);
  for(let x=-43;x<39;x+=4){for(const z of [-8.7,8.7])box(ship,x,7.1,z,.12,1.6,.12,white);}
  line(ship,[[-44,7.8,-8.7],[33,7.8,-8.7],[46,7.8,0],[33,7.8,8.7],[-44,7.8,8.7]],'#cad7d5',.6);
  for(let x=22;x<35;x+=4)box(ship,x,6.65,0,2,.12,.22,white);
  // Bridge glazing, hull apertures, deck fittings and radar hardware.
  const glass=new THREE.MeshPhysicalMaterial({color:'#173d4e',metalness:.55,roughness:.16,clearcoat:1});
  for(const side of [-1,1]){
    for(let x=-3;x<15;x+=3)box(ship,x,11.3,side*6.06,2,1.5,.12,glass);
    for(let x=-37;x<30;x+=5){const port=mesh(new THREE.CylinderGeometry(.42,.42,.16,20),glass,ship,[x,3.8,side*9.05]);port.rotation.x=Math.PI/2;}
    for(let x=-40;x<35;x+=8){box(ship,x,6.9,side*7,.6,.6,.6,dark);box(ship,x,7.25,side*7,1.3,.15,.3,hullmat);}
    line(ship,[[-44,7.25,side*8.7],[33,7.25,side*8.7]],'#d4e0df',.8);
    box(ship,0,.6,side*9.05,76,.65,.12,dark);
    const rescueRing=mesh(new THREE.TorusGeometry(.7,.18,10,24),orange,ship,[-4,10,side*6.2]);
    for(let x=-42;x<0;x+=3)line(ship,[[x,6.62,-8],[x,6.62,8]],'#42535b',.6);
  }
  mesh(new THREE.SphereGeometry(1.6,24,16),white,ship,[5,17,0]);
  box(ship,3,27.9,0,8,.65,.8,white);
  for(const z of [-3,3])mesh(new THREE.CylinderGeometry(.07,.07,5,8),dark,ship,[8,18,z]);
  for(let x=19;x<31;x+=3)box(ship,x,6.8,-3,1.8,.3,3.5,dark);
  const shipWake=new THREE.Group();scene.add(shipWake);
  for(let j=0;j<28;j++){const distance=j*3;line(shipWake,[[-distance,.35,-8-distance*.2],[-distance-2,.4,-5],[-distance,.35,8+distance*.2]],'#d2f1ee',.34*(1-j/28));}
  // Deck launch pads and five quadrotors.
  const dronePads=[[-35,-5],[-25,-5],[-35,5],[-25,5],[-15,-5]];
  const drones=[];
  dronePads.forEach(([x,z],i)=>{
    const pad=new THREE.Group();pad.position.set(x,6.7,z);ship.add(pad);ring(pad,2.5,'#7ad8c9',0);line(pad,[[-1,0,0],[1,0,0]],'#d0e5df');
    const d=new THREE.Group();scene.add(d);d.scale.setScalar(1.9);box(d,0,0,0,1.8,.6,1.1,dark);box(d,.4,-.45,0,.6,.5,.6,orange);
    const shell=mesh(new THREE.SphereGeometry(1,24,12),white,d,[0,.12,0]);shell.scale.set(1.1,.42,.72);
    const gimbal=mesh(new THREE.SphereGeometry(.43,20,12),dark,d,[.7,-.6,0]);
    const lens=mesh(new THREE.CylinderGeometry(.23,.23,.12,20),glass,d,[1.04,-.6,0]);lens.rotation.z=Math.PI/2;
    for(const z of [-.85,.85]){box(d,0,-.9,z,2,.1,.1,dark);for(const x of [-.65,.65])box(d,x,-.5,z,.1,.8,.1,dark);}
    const rotors=[];
    for(const xx of [-1,1])for(const zz of [-1,1]){
      const arm=box(d,xx*1.1,0,zz*1.1,3.2,.16,.18,deckmat);arm.rotation.y=-xx*zz*Math.PI/4;
      mesh(new THREE.CylinderGeometry(.22,.22,.5,8),dark,d,[xx*2.05,.2,zz*2.05]);
      const r=box(d,xx*2.05,.5,zz*2.05,2.5,.035,.18,dark);rotors.push(r);const blur=mesh(new THREE.CircleGeometry(1.25,24),new THREE.MeshBasicMaterial({color:'#bdcccf',transparent:true,opacity:.11,side:THREE.DoubleSide,depthWrite:false}),d,[xx*2.05,.51,zz*2.05]);blur.rotation.x=-Math.PI/2;
    }
    mesh(new THREE.SphereGeometry(.14,8,8),glow,d,[-.7,.15,.6]);
    const target=new THREE.Vector3(35+i*9,22+i*3,[-26,-6,19,43,65][i]);
    const scan=mesh(new THREE.ConeGeometry(12,35,32,1,true),new THREE.MeshBasicMaterial({color:'#72ead8',transparent:true,opacity:.055,side:THREE.DoubleSide,depthWrite:false}),scene);scan.visible=false;
    drones.push({d,rotors,start:new THREE.Vector3(x-25,7.3,z-10),target,scan});
  });
  // USV at the stern; USV and drone geometry represent the future product, not current hardware.
  const boat=new THREE.Group();scene.add(boat);
  for(const z of [-1.4,1.4]){const pontoon=mesh(new THREE.CapsuleGeometry(.72,6,8,20),hullmat,boat,[0,.6,z]);pontoon.rotation.z=Math.PI/2;box(boat,0,1.15,z,5,.12,.8,orange);}
  box(boat,-.2,2.5,0,2,.45,1.5,glass);
  mesh(new THREE.SphereGeometry(.35,16,12),white,boat,[-1,3,0]);
  for(const z of [-1.7,1.7])line(boat,[[-2,1.8,z],[2,1.8,z],[3,1.4,z]],'#d4e8e6',1);
  const rescueBuoy=mesh(new THREE.TorusGeometry(.7,.2,12,32),orange,boat,[-2.2,1.8,0]);rescueBuoy.rotation.x=Math.PI/2;

  box(boat,0,1.4,0,5,.4,3.2,white);box(boat,-.4,2,0,2.3,.9,1.7,orange);box(boat,-.6,3.1,0,.12,1.5,.12,white);mesh(new THREE.SphereGeometry(.2,12,8),glow,boat,[-.6,3.9,0]);
  const wake=new THREE.Group();scene.add(wake);for(let i=0;i<9;i++)line(wake,[[-i*2,.1,-1.4-i*.35],[-i*2-1,.1,0],[-i*2,.1,1.4+i*.35]],'#b4eee2',.22-i*.019);
  // Person in an orange flotation device.
  const person=new THREE.Group();scene.add(person);person.scale.setScalar(1.35);mesh(new THREE.SphereGeometry(.48,16,12),mat('#cfaa8c'),person,[0,1.0,0]);box(person,0,.35,0,.9,.8,.65,orange);
  const suit=mat('#243a4c'),skin=mat('#cfaa8c');
  for(const side of [-1,1]){
    const arm=mesh(new THREE.CapsuleGeometry(.15,.65,6,12),suit,person,[side*.62,.5,0]);arm.rotation.z=-side*.9;
    mesh(new THREE.SphereGeometry(.16,12,8),skin,person,[side*.9,.72,0]);
    const leg=mesh(new THREE.CapsuleGeometry(.18,.7,6,12),suit,person,[side*.25,-.45,.25]);leg.rotation.x=.45;
    box(person,side*.27,.44,.36,.12,.6,.04,white);
  }
  const lifering=mesh(new THREE.TorusGeometry(1,.22,10,32),orange,person,[0,.15,0]);lifering.rotation.x=Math.PI/2;
  const personRing=ring(scene,5,'#ff9b65');
  const targetLine=line(scene,[[0,0,0],[1,1,1]],'#8ffbe5',.8);
  const searchPaths=Array.from({length:5},()=>line(scene,[[0,0,0],[1,0,1]],'#70dfcd',.5));
  const route=line(scene,[[0,0,0],[1,0,1]],'#ffae69',1);
  searchPaths.forEach(p=>p.userData.width=.32);route.userData.width=.55;
  const droneSpots=drones.map(()=>ring(scene,7,'#72d9d2'));
  const boatStowed=new THREE.Vector3(-63,7,-10);
  const cloudGeometry=new THREE.BufferGeometry();
  cloudGeometry.setAttribute('position',new THREE.Float32BufferAttribute(new Float32Array(134*3),3));
  const cloud=new THREE.Points(cloudGeometry,new THREE.PointsMaterial({color:'#ffcf75',size:.75,transparent:true,opacity:.5,sizeAttenuation:true}));scene.add(cloud);
  function region(color,opacity){const m=mesh(new THREE.BufferGeometry(),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide,transparent:true,opacity,depthWrite:false,fog:false}),scene);return {fill:m,edge:line(scene,[[0,0,0],[1,0,1]],color,.85)};}
  const outer=region('#ffba38',.16),inner=region('#ffe09c',.25);
  outer.edge.userData.width=.3;inner.edge.userData.width=.2;
  const world=(p,y=2.2)=>new THREE.Vector3(2+p[0],y,3+p[1]);
  const currentDirection=new THREE.Vector3(story.current_enu[0],0,story.current_enu[1]).normalize();
  const currentArrow=new THREE.ArrowHelper(currentDirection,world([-100,-30],4),45,0x89d5ff,7,4);scene.add(currentArrow);
  const currentLabel=document.createElement('div');currentLabel.className='object-label';currentLabel.textContent='WATER CURRENT';currentLabel.style.borderColor='#89d5ff';$('.theatre').appendChild(currentLabel);
  function updateRegion(obj,points){
    if(points.length<3){obj.fill.visible=obj.edge.visible=false;return;}
    const center=points.reduce((p,q)=>[p[0]+q[0]/points.length,p[1]+q[1]/points.length],[0,0]);const vertices=[];
    for(let i=0;i<points.length;i++){for(const p of [center,points[i],points[(i+1)%points.length]]){const v=world(p,2.1);vertices.push(v.x,v.y,v.z);}}
    obj.fill.geometry.dispose();obj.fill.geometry=new THREE.BufferGeometry();obj.fill.geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
    updateLine(obj.edge,[...points,points[0]].map(p=>world(p,2.3)));
  }
  function updateLine(obj,points){
    obj.geometry.dispose();obj.geometry=new THREE.BufferGeometry().setFromPoints(points);
    if(obj.userData.width){
      let ribbon=obj.userData.ribbon;
      if(!ribbon){ribbon=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshBasicMaterial({color:obj.material.color,transparent:true,opacity:.8,side:THREE.DoubleSide,depthWrite:false,fog:false}));obj.add(ribbon);obj.userData.ribbon=ribbon;}
      const vertices=[],w=obj.userData.width;
      for(let i=1;i<points.length;i++){
        const a=points[i-1],b=points[i],dx=b.x-a.x,dz=b.z-a.z,len=Math.hypot(dx,dz)||1,nx=-dz/len*w,nz=dx/len*w;
        const q=[[a.x+nx,a.y,a.z+nz],[a.x-nx,a.y,a.z-nz],[b.x+nx,b.y,b.z+nz],[b.x-nx,b.y,b.z-nz]];
        for(const j of [0,1,2,1,3,2])vertices.push(...q[j]);
      }
      ribbon.geometry.dispose();ribbon.geometry=new THREE.BufferGeometry();ribbon.geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
    }
  }
  function contour(hull,center){
    return Array.from({length:96},(_,i)=>{
      const angle=i*Math.PI*2/96,dx=Math.cos(angle),dz=Math.sin(angle);let distance=0;
      for(let j=0;j<hull.length;j++){
        const a=hull[j],b=hull[(j+1)%hull.length],ex=b[0]-a[0],ez=b[1]-a[1];
        const ax=a[0]-center[0],az=a[1]-center[1],den=dx*ez-dz*ex;
        if(Math.abs(den)<1e-8)continue;
        const t=(ax*ez-az*ex)/den,v=(ax*dz-az*dx)/den;
        if(t>=0&&v>=0&&v<=1)distance=Math.max(distance,t);
      }
      return [center[0]+dx*distance,center[1]+dz*distance];
    });
  }
  const contours=story.frames.map(f=>({outer:contour(f.hull90,f.center),inner:contour(f.hull50,f.center)}));
  function displayEstimate(){
    const n=Math.min(endTime,Math.floor(time)),next=Math.min(endTime,n+1);
    let a=n,b=next,u=time-n;
    // Start at the pre-fix footprint at the lock instant; reveal posterior over 3s.
    for(const lock of [32]){
      if(time>=lock-1&&time<lock){a=b=lock-1;u=0;}
      if(time>=lock&&time<lock+3){a=lock-1;b=lock+3;u=ease((time-lock)/3);}
    }
    const blend=key=>contours[a][key].map((p,i)=>p.map((v,j)=>v+(contours[b][key][i][j]-v)*u));
    const area=story.frames[a].area90+(story.frames[b].area90-story.frames[a].area90)*u;
    return {outer:blend('outer'),inner:blend('inner'),area,a,b,u};
  }
  // Deterministic support-vessel return: turn on confirmed lock, then use sightings only.
  const shipFrames=[];
  for(let t=0;t<=endTime;t++){
    let x,z,heading;
    if(t<=32){x=-25+Math.max(0,t-3)*6;z=-10;heading=0;}
    else if(t<=48){const angle=Math.PI*ease((t-32)/16);x=149+30*Math.sin(angle);z=-10+30*(1-Math.cos(angle));heading=angle;}
    else{const prev=shipFrames[t-1],fix=story.frames[t].observation,dx=2+fix[0]-prev.x,dz=3+fix[1]-prev.z,distance=Math.hypot(dx,dz),step=Math.min(2.7,Math.max(0,distance-120));x=prev.x+dx/(distance||1)*step;z=prev.z+dz/(distance||1)*step;const desired=Math.atan2(dz,dx);heading=prev.heading+Math.atan2(Math.sin(desired-prev.heading),Math.cos(desired-prev.heading))*.12;}
    shipFrames.push({x,z,heading});
  }
  const droneLabels=drones.map((_,i)=>{const el=document.createElement('div');el.className='object-label drone-label';el.textContent='UAV '+(i+1);$('.theatre').appendChild(el);return el;});
  const vtmp=new THREE.Vector3();
  function label(el,obj,visible){
    if(!visible){el.style.display='none';return;}
    obj.getWorldPosition(vtmp);vtmp.y+=4;vtmp.project(camera);
    el.style.display=vtmp.z<1?'block':'none';const boatLabel=el.id==='boat-label';el.style.left=`${(vtmp.x*.5+.5)*view.clientWidth+(boatLabel?-70:12)}px`;el.style.top=`${(-vtmp.y*.5+.5)*view.clientHeight+(boatLabel?-20:10)}px`;
  }
  new ResizeObserver(()=>{const w=view.clientWidth,h=view.clientHeight;if(!w||!h)return;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);}).observe(view);
  function animate(now){
    requestAnimationFrame(animate);const dt=Math.min((now-lastFrame)/1000,.1);lastFrame=now;
    if(playing&&guideRemaining>0){guideRemaining=Math.max(0,guideRemaining-dt);$('#guide-label').textContent=`NEXT IN ${Math.ceil(guideRemaining)}s · AUTO PLAY`;if(guideRemaining===0)hideGuide();}
    else if(playing){const next=Math.min(endTime,time+dt*speed);const g=$('#guided').checked&&guides.find(g=>!seenGuides.has(g)&&g.t>=time&&g.t<=next);if(g){time=g.t;seenGuides.add(g);showGuide(g);}else time=next;if(time===endTime)playing=false;}
    const idx=stageAt(time);if(idx!==lastStage||playing)updatePanel();
    const motion=time;
    const f=storyFrame(),observed=f.observed;
    const rough=f.rough;
    const waveScale=rough?.85:.22;
    for(let i=0;i<positions.count;i++){const x=base[i*3],z=base[i*3+2];positions.array[i*3+1]=(Math.sin(x*.14+z*.08-motion*1.15)+.55*Math.cos(z*.25-x*.11-motion*.8)+.25*Math.sin(x*.5+z*.3-motion*1.8)) * waveScale;}
    positions.needsUpdate=true;oceanG.computeVertexNormals();normalMap.offset.set(motion*.002,motion*.001);
    const sf=shipFrames[Math.floor(time)],sn=shipFrames[Math.min(endTime,Math.floor(time)+1)],su=time-Math.floor(time);
    ship.position.set(sf.x+(sn.x-sf.x)*su,0,sf.z+(sn.z-sf.z)*su);ship.rotation.y=-(sf.heading+(sn.heading-sf.heading)*su);
    const stern=new THREE.Vector3(-45,0,0).applyAxisAngle(new THREE.Vector3(0,1,0),ship.rotation.y).add(ship.position);
    shipWake.position.copy(stern);shipWake.rotation.y=ship.rotation.y;shipWake.visible=time>=3;
    ship.rotation.x=Math.sin(motion*.45)*.006;ship.rotation.z=Math.sin(motion*.35)*.004;
    const fall=phaseFrac(2,3),truth=storyPoint('truth');
    person.position.copy(world(truth,.2));person.position.y=7.7*(1-fall)+.15;person.position.z=-1*(1-fall)+person.position.z*fall;
    person.rotation.z=fall<1?-fall*.8:Math.sin(motion)*.12;
    person.visible=time<3||observed||$('#truth').checked;
    $('#person-label').textContent=rough?'HIDDEN SCENARIO TRUTH · NO VISUAL FIX':observed?'POSITIVE VISUAL LOCK':'SIMULATED PERSON · SEARCHING';
    personRing.position.set(person.position.x,.7,person.position.z);personRing.visible=time>=3&&person.visible;
    const search=time>=5&&!observed;
    {
      const display=displayEstimate();
      updateRegion(outer,display.outer);
      updateRegion(inner,display.inner);
      const arr=cloudGeometry.attributes.position.array;
      const pa=story.frames[display.a].particles,pb=story.frames[display.b].particles;
      pa.forEach((p,i)=>{const v=world(p.map((v,j)=>v+(pb[i][j]-v)*display.u),2.4);arr[i*3]=v.x;arr[i*3+1]=v.y;arr[i*3+2]=v.z;});
      cloudGeometry.setDrawRange(0,pa.length);cloudGeometry.attributes.position.needsUpdate=true;cloudGeometry.computeBoundingSphere();
      searchPaths.forEach((path,i)=>{const next=story.frames[Math.min(endTime,Math.floor(time)+1)],u=time-Math.floor(time);updateLine(path,f.routes[i].map((p,j)=>world(p.map((v,k)=>v+(next.routes[i][j][k]-v)*u),2.8)));});
      updateLine(route,observed?[world(storyPoint('boat'),3),world(storyPoint('observation'),3)]:f.surface_route.map(p=>world(p,3)));
      if(time>=3){const area=Math.round(display.area).toLocaleString()+' m²';$('#model-area').textContent=area;$('#area-hud').textContent=area;}
    }
    const showProbability=$('#probability').checked&&time>=3;
    outer.fill.visible=outer.edge.visible=inner.fill.visible=inner.edge.visible=showProbability;
    cloud.visible=showProbability;
    searchPaths.forEach(path=>path.visible=search);
    route.visible=time>=5;
    drones.forEach(({d,rotors,start,scan},i)=>{
      const p=storyPoint('drones',i),pose=world(p,34+i*1.5);
      const lift=phaseFrac(5+i*.12,7+i*.12),onDeck=start.clone();onDeck.x+=ship.position.x+25;
      d.position.lerpVectors(onDeck,pose,lift);d.rotation.z=search?-.04:0;
      const ahead=storyPoint('drones',i,Math.min(endTime,time+.15)),behind=storyPoint('drones',i,Math.max(0,time-.15));
      const heading=-Math.atan2(ahead[1]-behind[1],ahead[0]-behind[0]);
      d.rotation.y+=Math.atan2(Math.sin(heading-d.rotation.y),Math.cos(heading-d.rotation.y))*(1-Math.exp(-dt*4));
      rotors.forEach(r=>r.rotation.y=motion*(time>=5?70:0));
      const clearOfShip=Math.hypot(d.position.x-ship.position.x,d.position.z-ship.position.z)>80;scan.visible=(f.scanning[i]||observed)&&clearOfShip;scan.material.opacity=.055;scan.position.set(d.position.x,d.position.y-17.5,d.position.z);
      droneSpots[i].visible=search&&f.scanning[i]&&clearOfShip;droneSpots[i].position.set(d.position.x,.8,d.position.z);
    });
    const boatPosition=world(storyPoint('boat'),.5),stowed=boatStowed.clone();stowed.x+=ship.position.x+25;
    boat.position.lerpVectors(stowed,boatPosition,phaseFrac(5,7));
    const ahead=storyPoint('boat',null,Math.min(endTime,time+.1)),behind=storyPoint('boat',null,Math.max(0,time-.1));
    const heading=-Math.atan2(ahead[1]-behind[1],ahead[0]-behind[0]);
    boat.rotation.y+=Math.atan2(Math.sin(heading-boat.rotation.y),Math.cos(heading-boat.rotation.y))*(1-Math.exp(-dt*5));boat.rotation.x=Math.sin(motion*1.2)*.025;
    wake.position.copy(boat.position);wake.rotation.y=boat.rotation.y;wake.visible=time>=7&&time<endTime;
    const active=drones[0].d.position;updateLine(targetLine,[active,world(storyPoint('observation'),1)]);targetLine.visible=observed&&time>=32;
    if(cameraMode==='overview'&&!drag){
      const spread=phaseFrac(3,18),close=phaseFrac(32,endTime);
      const center=world(storyPoint('center'),0);
      const points=f.routes.flat().map(p=>world(p));points.push(ship.position.clone().add(new THREE.Vector3(50,0,0)),ship.position.clone().add(new THREE.Vector3(-50,0,0)),boat.position);
      const bounds=new THREE.Box3().setFromPoints(points),mid=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
      targetLook.set((-20+(mid.x+20)*spread)*(1-close)+center.x*close,0,(8+(mid.z-8)*spread)*(1-close)+center.z*close);
      const fit=Math.max(650,Math.hypot(size.x,size.z)*1.45);
      radius=(235+(fit-235)*spread)*(1-close)+245*close;
    }
    if(cameraMode==='rescue')targetLook.copy(world(f.center,0));
    if(cameraMode==='deck')targetLook.copy(ship.position);
    look.lerp(targetLook,.07);camera.position.set(look.x+radius*Math.sin(az)*Math.cos(el),radius*Math.sin(el),look.z+radius*Math.cos(az)*Math.cos(el));camera.lookAt(look);
    currentArrow.visible=time>=5&&time<32;label(currentLabel,currentArrow,currentArrow.visible);
    drones.forEach(({d},i)=>label(droneLabels[i],d,time>=8&&!observed));
    label($('#person-label'),person,time>=3&&person.visible);label($('#boat-label'),boat,time>=5);
    renderer.render(scene,camera);
  }
  requestAnimationFrame(animate);
}
updatePanel();
