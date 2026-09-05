// Build-only, genuinely three-dimensional set. The readable face is a capture
// of the actual xterm renderer; physical materials are confined to the housing.
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {SVGLoader} from 'three/addons/loaders/SVGLoader.js';
import {presentationTime,studioMotion,ease} from './studio-timeline.mjs';

const {logo}=window.studioPayload;
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true,alpha:true});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(1280,720);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.12;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.VSMShadowMap;
// Composite fully shaded objects, not translucent individual mesh surfaces.
// Per-material fades expose back faces and darken overlapping extruded paths.
const output=document.createElement('canvas');
output.width=renderer.domElement.width;output.height=renderer.domElement.height;
const composite=output.getContext('2d',{alpha:false});
document.querySelector('#stage').appendChild(output);
const scene=new THREE.Scene();
renderer.setClearColor(0xffffff,0);
const camera=new THREE.PerspectiveCamera(34,1280/720,.1,100);
const pmrem=new THREE.PMREMGenerator(renderer);
const room=new RoomEnvironment();
scene.environment=pmrem.fromScene(room,.06).texture;
room.dispose();
scene.add(new THREE.HemisphereLight(0xffffff,0xc9c8c5,1.6));
const key=new THREE.DirectionalLight(0xffffff,3.1);
key.position.set(-5,9,8);key.castShadow=true;
key.shadow.mapSize.set(1024,1024);
Object.assign(key.shadow.camera,{left:-12,right:12,top:10,bottom:-10,near:.1,far:35});
key.shadow.bias=-.00015;key.shadow.normalBias=.025;key.shadow.radius=8;key.shadow.blurSamples=16;
scene.add(key);
const fill=new THREE.DirectionalLight(0xe6ebf0,1.1);fill.position.set(6,3,-5);scene.add(fill);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({color:0x8d8982,opacity:.12}));
floor.rotation.x=-Math.PI/2;floor.position.y=-3.05;floor.receiveShadow=true;scene.add(floor);

const housing=new THREE.Group();scene.add(housing);
const metal=new THREE.MeshPhysicalMaterial({color:0xb9bdc1,metalness:.85,roughness:.26,clearcoat:.12,clearcoatRoughness:.35});
const porcelain=new THREE.MeshPhysicalMaterial({color:0xf4f4f2,metalness:.08,roughness:.29,clearcoat:.2,clearcoatRoughness:.28});
const back=new THREE.Mesh(new RoundedBoxGeometry(11.95,5.29,.22,6,.12),metal);
back.castShadow=true;back.receiveShadow=true;housing.add(back);
const bezel=new THREE.Mesh(new RoundedBoxGeometry(11.88,5.22,.09,6,.1),porcelain);
bezel.position.z=.115;bezel.castShadow=true;housing.add(bezel);
const faceW=11.76,faceH=5.14;
const shape=new THREE.Shape();const r=.11;
shape.moveTo(-faceW/2+r,-faceH/2);
shape.lineTo(faceW/2-r,-faceH/2);shape.quadraticCurveTo(faceW/2,-faceH/2,faceW/2,-faceH/2+r);
shape.lineTo(faceW/2,faceH/2-r);shape.quadraticCurveTo(faceW/2,faceH/2,faceW/2-r,faceH/2);
shape.lineTo(-faceW/2+r,faceH/2);shape.quadraticCurveTo(-faceW/2,faceH/2,-faceW/2,faceH/2-r);
shape.lineTo(-faceW/2,-faceH/2+r);shape.quadraticCurveTo(-faceW/2,-faceH/2,-faceW/2+r,-faceH/2);
const faceGeo=new THREE.ShapeGeometry(shape,16);
const pos=faceGeo.attributes.position,uv=faceGeo.attributes.uv;
for(let i=0;i<pos.count;i++)uv.setXY(i,pos.getX(i)/faceW+.5,pos.getY(i)/faceH+.5);
const faceMaterial=new THREE.MeshBasicMaterial({color:0xffffff,toneMapped:false});
const face=new THREE.Mesh(faceGeo,faceMaterial);face.position.z=.169;housing.add(face);

// Extrude the existing SVG paths, including its transformed signature slash.
const sculpture=new THREE.Group();
for(const path of new SVGLoader().parse(logo).paths){
  for(const part of SVGLoader.createShapes(path)){
    const hex=path.color.getHexString();
    const isGold=hex==='e2a500';
    const isRust=!isGold&&hex!=='12100c';
    const geometry=new THREE.ExtrudeGeometry(part,{depth:isGold?4.5:.65,bevelEnabled:true,bevelSegments:4,steps:1,bevelSize:isGold?.4:.09,bevelThickness:isGold?.35:.08,curveSegments:32});
    const material=new THREE.MeshPhysicalMaterial({color:isGold?0x9e6500:isRust?0x58220a:0x080706,metalness:isGold?.18:.22,roughness:isGold?.34:.33,clearcoat:.22,clearcoatRoughness:.27});
    const mesh=new THREE.Mesh(geometry,material);mesh.castShadow=true;mesh.receiveShadow=true;
    if(!isGold)mesh.position.z=isRust?5.45:4.9;
    sculpture.add(mesh);
  }
}
sculpture.scale.set(.08,-.08,.08);
const logoRoot=new THREE.Group();logoRoot.add(sculpture);scene.add(logoRoot);
const bounds=new THREE.Box3().setFromObject(sculpture),center=bounds.getCenter(new THREE.Vector3());
sculpture.position.sub(center);
let currentImage='',texture;
async function updateFace(url){
  if(url===currentImage)return;
  const img=await new Promise((resolve,reject)=>{const el=new Image();el.onload=()=>resolve(el);el.onerror=reject;el.src=url;});
  const next=new THREE.Texture(img);next.colorSpace=THREE.SRGBColorSpace;next.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());next.needsUpdate=true;
  faceMaterial.map=next;faceMaterial.needsUpdate=true;if(texture)texture.dispose();texture=next;currentImage=url;
}
function pose(group,state){
  group.position.set(state.x,state.y,state.z);
  group.rotation.set(state.rx,state.ry,state.rz);
  group.scale.setScalar(state.scale);
}
function renderLayers(housingOpacity,logoOpacity){
  composite.globalAlpha=1;composite.fillStyle='#ffffff';
  composite.fillRect(0,0,output.width,output.height);
  for(const [group,opacity] of [[housing,housingOpacity],[logoRoot,logoOpacity]]){
    if(opacity<=0)continue;
    housing.visible=group===housing;logoRoot.visible=group===logoRoot;
    renderer.render(scene,camera);
    composite.globalAlpha=opacity;composite.drawImage(renderer.domElement,0,0);
  }
  composite.globalAlpha=1;
}
function compose(t){
  const motion=studioMotion(t),legacy=presentationTime(t);
  camera.position.set(0,motion.camera.y,motion.camera.z);
  camera.lookAt(0,0,0);
  pose(housing,motion.housing);pose(logoRoot,motion.logo);
  const brand=document.querySelector('.brand');brand.style.opacity=String(motion.brandOpacity);
  const title=document.querySelector('.intro');title.style.opacity=String(motion.introOpacity);
  const instruction=document.querySelector('.instruction');
  let captionOpacity=1;
  for(const at of [3600,8600,15800]){
    if(t>=at-100&&t<at)captionOpacity=1-ease((t-at+100)/100);
    if(t>=at&&t<at+150)captionOpacity=ease((t-at)/150);
  }
  instruction.style.opacity=String(motion.instructionOpacity*captionOpacity);
  instruction.textContent=legacy<5200?'Install once. Then restart your assistant.':legacy<12000?'Paste your draft after /zero-slop.':legacy<22000?'Your assistant edits. Local tools compare source details.':'Review the edit before you use it.';
  const closing=document.querySelector('.closing');closing.style.opacity=String(motion.closingOpacity);closing.style.transform=`translateY(${motion.closingOffsetY}px)`;
  document.querySelector('footer').style.opacity=String(motion.brandOpacity);
  renderLayers(motion.housing.opacity,motion.logo.opacity);
  scene.updateMatrixWorld(true);
  const corners=[[-faceW/2,-faceH/2],[faceW/2,-faceH/2],[faceW/2,faceH/2],[-faceW/2,faceH/2]].map(([x,y])=>{
    const point=face.localToWorld(new THREE.Vector3(x,y,0)).project(camera);
    return {x:(point.x+1)*640,y:(1-point.y)*360};
  });
  window.studioInspection={t,renderer:'Three.js',screenCorners:corners,screenVisible:motion.housing.opacity>.99,housingOpacity:motion.housing.opacity,logoOpacity:motion.logo.opacity,motion,webgl:renderer.getContext().getParameter(renderer.getContext().VERSION)};
}
window.renderStudio=async(t,url)=>{await updateFace(url);compose(t);await new Promise(resolve=>requestAnimationFrame(resolve));};
window.renderLogo=async()=>{
  document.querySelectorAll('.brand,.intro,.instruction,.closing,footer').forEach(el=>el.style.display='none');
  housing.visible=false;logoRoot.visible=true;
  renderer.setPixelRatio(1);renderer.setSize(1200,1200);
  output.width=1200;output.height=1200;
  output.style.width='1200px';output.style.height='1200px';
  camera.aspect=1;camera.updateProjectionMatrix();camera.position.set(0,.6,12.6);camera.lookAt(0,-.35,0);
  logoRoot.position.set(0,.05,0);logoRoot.rotation.set(.1,-.2,-.03);logoRoot.scale.setScalar(1.04);
  renderLayers(0,1);await new Promise(resolve=>requestAnimationFrame(resolve));
};
window.studioReady=Promise.all([document.fonts.ready,renderer.compileAsync(scene,camera)]).then(()=>compose(0));
