import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const slots={1:'Head',3:'Shoulders',5:'Chest',6:'Waist',7:'Legs',8:'Feet',9:'Wrists',10:'Hands',16:'Back',20:'Robe',21:'Main hand',22:'Off hand',13:'Weapon',17:'Two-handed weapon',14:'Shield',23:'Held in off hand'};
const sections={0:'Upper arm',1:'Lower arm',2:'Hands',3:'Upper torso',4:'Lower torso',5:'Upper leg',6:'Lower leg',7:'Foot'};
let data,mode='armor',selected,parts=[],activePart,request=0,model,renderer,controls,scene,camera,wireframe=false,frameDistance=4;
const loader=new GLTFLoader();
function dispose(object){if(!object)return;object.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of [o.material].flat()){m.map?.dispose();m.dispose();}}});}
function initViewer(){
  try{
    renderer=new THREE.WebGLRenderer({canvas:$('canvas'),antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(35,1,.01,500);controls=new OrbitControls(camera,$('canvas'));controls.enableDamping=true;controls.enablePan=false;controls.autoRotateSpeed=1;
    new ResizeObserver(resize).observe($('stage'));
    renderer.setAnimationLoop(()=>{if(document.hidden)return;controls.update();renderer.render(scene,camera);});
    $('canvas').addEventListener('webglcontextlost',e=>{e.preventDefault();$('status').hidden=false;$('status').textContent='The 3D context was interrupted. Reload the page to restore it.';});
  }catch(e){$('status').textContent='3D requires WebGL. You can still browse the set textures below.';}
}
function resize(){if(!renderer)return;const {width,height}=$('stage').getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();if(model)reset();}
function reset(){if(!camera)return;if(model)model.rotation.set(0,0,0);camera.position.set(frameDistance*.86,frameDistance*.25,frameDistance*.50);controls.target.set(0,0,0);controls.update();}
function hash(){return `#${mode==='armor'?'set':'creature'}-${selected.id}${mode==='armor'&&activePart?`-${activePart.itemID}-${activePart.sideIndex}`:''}`;}
async function showPart(index){
  const ticket=++request;activePart=parts[index];
  document.querySelectorAll('.controls button').forEach(b=>b.disabled=!activePart||!renderer);
  $('parts').querySelectorAll('button').forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
  if(!activePart){if(model){scene.remove(model);dispose(model);model=null;}$('status').hidden=false;$('status').textContent='This entry has texture sections only.';$('model-label').textContent='';$('piece-caption').textContent='';return;}
  history.replaceState(null,'',hash());
  $('piece-caption').textContent=activePart.caption;
  $('model-label').textContent=mode==='armor'?`${activePart.side} · ${activePart.side==='Head'?'Human male · ':''}Static preview`:'Client creature appearance · Static preview';
  if(!renderer)return;
  if(model){scene.remove(model);dispose(model);model=null;}
  $('status').hidden=false;$('status').textContent='Loading model…';
  try{
    const gltf=await loader.loadAsync(activePart.url);
    if(ticket!==request){dispose(gltf.scene);return;}
    model=gltf.scene;const box=new THREE.Box3().setFromObject(model),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
    model.position.sub(center);scene.add(model);
    const radius=size.length()/2;frameDistance=radius/Math.sin(THREE.MathUtils.degToRad(camera.fov*Math.min(1,camera.aspect)/2))*1.12;
    controls.minDistance=radius*.6;controls.maxDistance=frameDistance*4;camera.near=Math.max(.001,radius/100);camera.far=frameDistance*10;camera.updateProjectionMatrix();reset();
    model.traverse(o=>{if(o.isMesh)o.material.wireframe=wireframe;});$('status').hidden=true;
  }catch(e){if(ticket===request){$('status').hidden=false;$('status').textContent='This model could not be loaded. Select another piece or reload.';}}
}
function pick(entry,routeItem,routeSide){
  selected=entry;activePart=undefined;$('entry-title').textContent=entry.name;
  $('entry-kind').textContent=mode==='armor'?(entry.category==='tier1'?'New Tier 1':entry.category==='pvp'?'PvP armor':'Armor appearance'):'Creature appearance';
  $('entry-subtitle').textContent=mode==='armor'?[...new Set([entry.class,entry.role,`Set ${entry.id}`].filter(Boolean))].join(' · '):`Display ${entry.displayID} · Model ${entry.id}`;
  $('set-link').hidden=mode!=='armor';$('set-link').href=`content.html#set-${entry.id}`;$('creature-note').hidden=mode!=='creature';$('textures-section').hidden=mode!=='armor';
  parts=mode==='armor'?entry.pieces.flatMap(p=>p.parts.filter(part=>part.url).map((part,i)=>({...part,itemID:p.itemID,sideIndex:i,caption:`${p.name||slots[p.slot]||'Set piece'} · Item ${p.itemID} · ${part.triangles.toLocaleString('en-US')} triangles`}))).sort((a,b)=>(a.side==='Head'?-1:0)-(b.side==='Head'?-1:0)):[{...entry,caption:`${entry.triangles.toLocaleString('en-US')} triangles · ${entry.variantCount} display variant${entry.variantCount===1?'':'s'} in the client`}];
  $('parts').innerHTML=parts.map((p,i)=>`<button data-part="${i}" aria-pressed="false">${esc(mode==='armor'?p.side:'Creature model')}${parts.filter(q=>q.side===p.side).length>1?` · ${p.itemID}`:''}</button>`).join('');
  $('parts').querySelectorAll('button').forEach(b=>b.onclick=()=>showPart(Number(b.dataset.part)));
  $('textures').innerHTML=mode==='armor'?entry.pieces.map(p=>`<article class="piece"><div class="piece-head">${p.icon?`<img src="${p.icon}" alt="" loading="lazy">`:''}<div>${esc(p.name||slots[p.slot]||'Set piece')}<small>${esc(slots[p.slot]||'')} · Item ${p.itemID}</small></div></div><div class="swatches">${p.cloth.filter(t=>t.url).map(t=>`<figure><a href="${t.url}" target="_blank" rel="noreferrer"><img src="${t.url}" alt="${esc(sections[t.section]||'Body')} texture for item ${p.itemID}" loading="lazy"></a><figcaption>${esc(sections[t.section]||`Section ${t.section}`)}</figcaption></figure>`).join('')}</div>${p.parts.some(x=>x.url)?'<small>3D model available above</small>':''}</article>`).join(''):'';
  $('references').innerHTML=mode==='armor'?entry.pieces.map(p=>`<p>Item ${p.itemID} → Appearance ${p.appearanceID} → Display ${p.displayID}${p.parts.map(x=>`<br>Model ${x.fileDataID}: ${esc(x.path||x.internalName||'Unnamed file')}`).join('')}</p>`).join(''):`<p>CreatureModelData ${entry.id} → File ${entry.fileDataID}<br>CreatureDisplayInfo ${entry.displayID}<br>${esc(entry.path)}<br>Internal name: ${esc(entry.internalName)}</p>`;
  history.replaceState(null,'',hash());renderCatalog();
  const pi=parts.findIndex(p=>p.itemID===routeItem&&p.sideIndex===routeSide);showPart(pi<0?0:pi);
}
function filtered(){if(!data)return [];const q=$('search').value.trim().toLowerCase(),cat=$('category').value;return (mode==='armor'?data.sets:data.creatures.filter(c=>c.url)).filter(e=>{
  if(mode==='armor'&&cat!=='all'&&!(cat==='new'?e.status==='new':e.category===cat))return false;
  return !q||[e.name,e.class,e.role,e.id,e.internalName,...(e.pieces||[]).map(p=>`${p.itemID} ${p.name||''}`)].join(' ').toLowerCase().includes(q);
});}
function renderCatalog(){const entries=filtered();$('count').textContent=`${entries.length} ${mode==='armor'?'sets':'creature models'}`;
  $('catalog').innerHTML=entries.length?entries.map(e=>`<button data-id="${e.id}" aria-pressed="${selected?.id===e.id}">${e.pieces?.find(p=>p.icon)?.icon?`<img src="${e.pieces.find(p=>p.icon).icon}" alt="" loading="lazy">`:''}<span>${esc(e.name)}<small>${esc(mode==='armor'?e.role||e.class||`Set ${e.id}`:`Model ${e.id}`)}</small></span></button>`).join(''):'<p class="muted">No matching entries.</p>';
  $('catalog').querySelectorAll('button').forEach(b=>b.onclick=()=>pick(entries.find(e=>e.id===Number(b.dataset.id))));
}
function switchMode(next,entry){if(!data)return;mode=next;$('armor-tab').setAttribute('aria-pressed',String(mode==='armor'));$('creature-tab').setAttribute('aria-pressed',String(mode==='creature'));$('category').hidden=mode!=='armor';document.querySelector('label[for=category]').hidden=mode!=='armor';$('search').value='';selected=null;renderCatalog();const first=entry||filtered()[0];if(first)pick(first);}
function route(){const match=location.hash.match(/^#(set|creature)-(\d+)(?:-(\d+)-(\d+))?$/);if(!match)return false;const next=match[1]==='set'?'armor':'creature';const entry=(next==='armor'?data.sets:data.creatures).find(e=>e.id===Number(match[2]));if(!entry)return false;if(next==='armor')$('category').value=entry.category==='tier1'?'tier1':'all';switchMode(next,entry);if(match[3])pick(entry,Number(match[3]),Number(match[4]));return true;}
$('search').oninput=renderCatalog;$('category').onchange=()=>{renderCatalog();const entries=filtered();if(entries.length&&!entries.some(e=>e.id===selected?.id))pick(entries[0]);};
$('armor-tab').onclick=()=>switchMode('armor');$('creature-tab').onclick=()=>switchMode('creature');
$('rotate').onclick=()=>{if(!controls)return;controls.autoRotate=!controls.autoRotate;$('rotate').setAttribute('aria-pressed',String(controls.autoRotate));};
$('reset').onclick=reset;
function turn(amount){if(!model)return;model.rotation.y+=amount;}
$('turn-left').onclick=()=>turn(-Math.PI/8);$('turn-right').onclick=()=>turn(Math.PI/8);
function zoom(scale){if(!model)return;camera.position.multiplyScalar(scale);camera.position.setLength(THREE.MathUtils.clamp(camera.position.length(),controls.minDistance,controls.maxDistance));controls.update();}
$('zoom-in').onclick=()=>zoom(.8);$('zoom-out').onclick=()=>zoom(1.25);
$('canvas').onkeydown=e=>{if(['ArrowLeft','ArrowRight','+','-'].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft')turn(-Math.PI/8);if(e.key==='ArrowRight')turn(Math.PI/8);if(e.key==='+')zoom(.8);if(e.key==='-')zoom(1.25);}};
$('wireframe').onclick=()=>{wireframe=!wireframe;$('wireframe').setAttribute('aria-pressed',String(wireframe));model?.traverse(o=>{if(o.isMesh)o.material.wireframe=wireframe;});};
try{data=await fetch('models-data.json').then(r=>{if(!r.ok)throw new Error('Data unavailable');return r.json();});$('summary').textContent=`${data.summary.tierSets} Tier 1 sets · ${data.summary.sets} sets total · ${data.summary.creaturePreviews} creature previews`;initViewer();if(!route())switchMode('armor');addEventListener('hashchange',route);}catch(e){$('entry-title').textContent='Gallery unavailable';$('status').textContent='Could not load gallery data. Please reload the page.';}
