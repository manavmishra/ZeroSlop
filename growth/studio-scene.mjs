// Build-only, genuinely three-dimensional set. The readable face is a capture
// of the actual xterm renderer; physical materials are confined to the housing.
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {SVGLoader} from 'three/addons/loaders/SVGLoader.js';
import {presentationTime} from './studio-timeline.mjs';

const {logo}=window.studioPayload;
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true,alpha:false});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(1280,720);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.12;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.VSMShadowMap;
document.querySelector('#stage').appendChild(renderer.domElement);
const scene=new THREE.Scene();
scene.background=new THREE.Color('#ffffff');
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
const ease=x=>{x=Math.max(0,Math.min(1,x));return x*x*x*(x*(x*6-15)+10);};
const lerp=THREE.MathUtils.lerp;
let currentImage='',texture;
async function updateFace(url){
  if(url===currentImage)return;
  const img=await new Promise((resolve,reject)=>{const el=new Image();el.onload=()=>resolve(el);el.onerror=reject;el.src=url;});
  const next=new THREE.Texture(img);next.colorSpace=THREE.SRGBColorSpace;next.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());next.needsUpdate=true;
  faceMaterial.map=next;faceMaterial.needsUpdate=true;if(texture)texture.dispose();texture=next;currentImage=url;
}
function compose(t){
  const intro=t<1200;
  const end=ease((t-30000)/1400);
  const settle=ease((t-1200)/1200);
  const inspectPush=t>=7200?ease((t-7200)/400):0;
  const editPush=t>=16400?ease((t-16400)/800):0;
  camera.position.set(0,.22,lerp(13.7,12.65,settle)-.1*inspectPush-.13*editPush);
  camera.lookAt(0,0,0);
  housing.visible=!intro;
  housing.rotation.set(lerp(-.08,-.006,settle)+.035*end,lerp(-.23,-.022,settle)-.28*end,lerp(.017,0,settle)-.025*end);
  housing.position.set(2.75*end,.07+.7*end,0);
  housing.scale.setScalar(1-.48*end);
  logoRoot.visible=intro||t>=30000;
  if(intro){
    const drift=ease(t/1200);
    camera.position.set(0,.32,12.6);camera.lookAt(0,0,0);
    logoRoot.position.set(3,.1,0);
    logoRoot.rotation.set(.1,lerp(-.28,-.13,drift),-.06);
    logoRoot.scale.setScalar(1.04+.03*drift);
  }else{
    logoRoot.position.set(-3.65,.65,.05);
    logoRoot.rotation.set(.08,-.15+.14*end,-.02);
    logoRoot.scale.setScalar(.58*end);
  }
  const brand=document.querySelector('.brand');brand.style.opacity=intro?'0':'1';
  const title=document.querySelector('.intro');title.style.opacity=intro?'1':'0';
  title.style.transform=`translateX(${intro?4*(1-ease(t/1200)):0}px)`;
  const instruction=document.querySelector('.instruction');
  instruction.style.opacity=intro?'0':String(1-end);
  instruction.textContent=t<5200?'Install once. Then restart your assistant.':t<12000?'Paste your draft after /zero-slop.':t<22000?'Your assistant edits. Local tools compare source details.':'Review the edit before you use it.';
  const closing=document.querySelector('.closing');closing.style.opacity=String(end);closing.style.transform=`translateY(${8*(1-end)}px)`;
  document.querySelector('footer').style.opacity=intro?'0':'1';
  renderer.render(scene,camera);
  scene.updateMatrixWorld(true);
  const corners=[[-faceW/2,-faceH/2],[faceW/2,-faceH/2],[faceW/2,faceH/2],[-faceW/2,faceH/2]].map(([x,y])=>{
    const point=face.localToWorld(new THREE.Vector3(x,y,0)).project(camera);
    return {x:(point.x+1)*640,y:(1-point.y)*360};
  });
  window.studioInspection={t,renderer:'Three.js',screenCorners:corners,screenVisible:housing.visible,webgl:renderer.getContext().getParameter(renderer.getContext().VERSION)};
}
window.renderStudio=async(t,url)=>{await updateFace(url);compose(presentationTime(t));await new Promise(resolve=>requestAnimationFrame(resolve));};
window.renderLogo=async()=>{
  document.querySelectorAll('.brand,.intro,.instruction,.closing,footer').forEach(el=>el.style.display='none');
  housing.visible=false;logoRoot.visible=true;
  renderer.setPixelRatio(1);renderer.setSize(1200,1200);
  camera.aspect=1;camera.updateProjectionMatrix();camera.position.set(0,.6,12.6);camera.lookAt(0,-.35,0);
  logoRoot.position.set(0,.05,0);logoRoot.rotation.set(.1,-.2,-.03);logoRoot.scale.setScalar(1.04);
  renderer.render(scene,camera);await new Promise(resolve=>requestAnimationFrame(resolve));
};
window.studioReady=Promise.all([document.fonts.ready,renderer.compileAsync(scene,camera)]).then(()=>compose(0));
