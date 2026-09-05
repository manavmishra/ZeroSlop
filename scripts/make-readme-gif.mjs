#!/usr/bin/env node
// Zero Cut: a typeset product film, not a screen recording or latency test.
// Usage: node scripts/make-readme-gif.mjs [assets/zero-slop-demo.gif]
// Build-only: playwright-core + sharp. Optional CHROME_PATH and NODE_PATH.
// Exports a GIF, optimized animated WebP, static poster and standalone player.

import { createRequire } from "node:module";
import { readFile, writeFile, mkdir, stat } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright-core");
const sharp = require("sharp");
const ROOT = fileURLToPath(new URL("../", import.meta.url));
const out = resolve(process.argv[2] ?? `${ROOT}/assets/zero-slop-demo.gif`);
if (!out.endsWith('.gif')) throw Error('Output must have a .gif extension');
const base = out.slice(0,-4);
const W = 1040, H = 560, DURATION = 8400;
// Direction: variance 6 / motion 6 / density 2. White is explicitly requested.
// Exact existing logo, one rust accent, no decorative UI or invented statistics.
const logo = await readFile(`${ROOT}/assets/logo/logo-mark.svg`, "utf8");
const source = "We're thrilled to announce that our team has leveraged cutting-edge machine learning to deliver a seamless onboarding experience, reducing setup time by 40%.";
const rewrite = "We used machine learning to reduce onboarding setup time by 40%.";
const flags = ["We're thrilled to", "leveraged", "cutting-edge", "seamless"];
const esc = text => text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
let marked=esc(source);
for(const [i,phrase] of flags.entries()) marked=marked.replace(esc(phrase),`<mark data-flag="${i}">${esc(phrase)}</mark>`);
const markup=`
  <header><div class="brand">${logo}<strong>Zero Slop</strong></div><span class="category">AI writing editor</span></header>
  <div class="story">
    <section class="hook scene"><p class="eyebrow">Cut the stock phrases.</p><p class="hook-line">We're thrilled to<span>…</span><i></i></p></section>
    <section class="before scene"><p class="label">The draft</p><p class="draft">${marked}</p></section>
    <section class="after scene"><p class="label">The edit</p><p class="rewrite">We used machine learning to<br>reduce onboarding setup time<br>by <strong>40%.</strong></p></section>
    <section class="action scene"><p class="action-title">Try it free.</p><p class="url">zero-slop.ai/try<span>↗</span></p><p class="action-note">No account needed.</p></section>
    <aside class="proof"><p class="score-label">Writing score</p><div class="scores"><p class="old-score">99.3</p><p class="new-score">9.5</p></div><p class="out-of">/100</p><p class="before-count">4 phrases flagged</p><p class="after-count">0 phrases flagged</p><p class="score-note">Lower is better</p></aside>
    <div class="fact"><strong>40%</strong><span>setup-time reduction</span><span class="retained">Retained in the edit</span></div>
    <i class="zero-cut" aria-hidden="true"></i>
  </div>
  <footer><span>Free, open-source Agent Skill</span><span class="foot-proof">Illustrated example. Measured scores.</span><span class="foot-cta">zero-slop.ai</span></footer>`;

const css=`
  :root{color-scheme:light;--ink:#12100c;--rust:#b0502c;--muted:#65635f;--line:#e9e7e4}
  *{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;-webkit-font-smoothing:antialiased}
  .viewport{width:100%;max-width:${W}px;margin:0 auto;overflow:hidden}#stage{position:relative;width:${W}px;height:${H}px;transform-origin:top left;overflow:hidden;background:#fff}
  header{height:110px;display:flex;align-items:center;justify-content:space-between;margin:0 48px;border-bottom:1px solid var(--line)}
  .brand{display:flex;gap:10px;align-items:center}.brand svg{width:60px;height:60px;display:block}.brand strong{font-size:29px;letter-spacing:-1.1px;font-weight:720}.category{font-size:16px;color:var(--muted)}
  .story{position:relative;height:370px;margin:0 56px}.scene{position:absolute;left:0;top:30px;width:708px;height:286px}.scene p{margin:0}.label{font-size:16px;color:var(--muted);font-weight:550;margin-bottom:20px!important}
  .hook{width:930px}.eyebrow{color:var(--muted);font-size:20px;margin-top:20px!important}.hook-line{position:relative;display:inline-block;margin-top:30px!important;font-size:80px;line-height:1.1;letter-spacing:-3.8px;font-weight:620}.hook-line span{color:var(--rust)}.hook-line i{position:absolute;left:-2px;right:-2px;top:57%;height:7px;background:var(--rust);border-radius:7px;transform-origin:left center}
  .draft{width:692px;padding-right:8px;font-size:31px;line-height:1.46;letter-spacing:-.85px;font-weight:430}
  mark{position:relative;color:inherit;background:transparent;border-radius:2px;box-decoration-break:clone;-webkit-box-decoration-break:clone}mark.on{background:#f8e9e2;color:#823c22;box-shadow:0 2px 0 var(--rust)}
  .rewrite{font-size:40px;line-height:1.36;letter-spacing:-1.45px;font-weight:550}.rewrite strong{color:var(--rust);font-weight:inherit}
  .proof{position:absolute;right:0;top:34px;width:184px;height:238px;border-left:1px solid var(--line);padding-left:27px}.proof p{margin:0}.score-label{font-size:15px;color:var(--muted)}.scores{position:relative;height:74px;margin-top:17px}.scores p{position:absolute;font-size:66px;line-height:1;letter-spacing:-4px;font-weight:650;font-variant-numeric:tabular-nums}.old-score{color:var(--rust)}.out-of{font-size:16px;color:var(--muted)}.before-count,.after-count{position:absolute;top:155px;font-size:15px;white-space:nowrap}.score-note{position:absolute;top:188px;font-size:13px;color:var(--muted)}
  .fact{position:absolute;left:0;top:307px;display:flex;gap:12px;align-items:center}.fact strong{font-size:26px;font-weight:650;letter-spacing:-.6px}.fact>span{font-size:16px;color:var(--muted)}.fact .retained{margin-left:14px;padding-left:18px;border-left:1px solid #d8d3cd;font-size:15px;color:var(--rust)}
  .zero-cut{position:absolute;left:0;top:205px;width:1000px;height:9px;background:var(--rust);border-radius:9px;transform-origin:left center}
  .action{top:36px}.action-title{font-size:82px;line-height:1.05;letter-spacing:-3.4px;font-weight:650}.url{display:inline-flex;gap:18px;align-items:center;margin-top:23px!important;font-size:36px;letter-spacing:-1.1px;color:var(--rust);font-weight:500}.url span{font-size:34px}.action-note{margin-top:22px!important;font-size:18px;color:var(--muted)}
  footer{height:80px;display:flex;align-items:center;justify-content:space-between;margin:0 56px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}.foot-cta{font-size:17px;color:var(--ink)}
  .before,.after,.action,.proof,.fact,.zero-cut,.new-score,.after-count,.retained{opacity:0}
  .controls{display:flex;flex-wrap:wrap;justify-content:center;gap:14px;align-items:center;padding:16px;font-size:13px;color:var(--muted)}button{background:#fff;color:var(--ink);border:1px solid #c9c5be;border-radius:6px;padding:7px 16px;font:inherit;cursor:pointer}button:focus-visible{outline:2px solid var(--rust);outline-offset:3px}.note{max-width:420px}
  @media(prefers-reduced-motion:reduce){.hook,.before,.action,.zero-cut,.old-score,.before-count{opacity:0!important}.after,.proof,.fact,.new-score,.after-count,.retained{opacity:1!important;transform:none!important}}
`;

// No intermediate scores are invented. Motion is only transform + opacity;
// static layouts and sparse hold frames keep both paint cost and GIF size low.
function renderFrame(t){
  const clamp=n=>Math.max(0,Math.min(1,n));
  const ease=n=>1-Math.pow(1-clamp(n),3);
  const fade=(start,dur)=>ease((t-start)/dur);
  const reset=fade(8120,280);
  const show=(selector,value,y=0)=>{for(const el of document.querySelectorAll(selector)){el.style.opacity=String(value);el.style.transform=`translateY(${y}px)`;}};
  const hook=(1-fade(980,160))*(1-reset)+reset;
  show('.hook',hook,-8*(1-hook));
  document.querySelector('.hook-line i').style.transform=`rotate(-8deg) scaleX(${fade(480,280)*(1-reset)})`;
  const before=fade(1140,200)*(1-fade(3420,160))*(1-reset);
  const after=fade(3580,240)*(1-fade(6060,180))*(1-reset);
  const action=fade(6240,280)*(1-fade(7940,180));
  show('.before',before,8*(1-fade(1140,200))-8*fade(3420,160));
  show('.after',after,12*(1-fade(3580,240))-8*fade(6060,180));
  show('.action',action,12*(1-fade(6240,280)));
  show('.proof',fade(1200,220)*(1-fade(7940,180)));
  const changed=t>=3660?1:0;
  show('.old-score,.before-count',1-changed);
  show('.new-score,.after-count',changed,8*(1-changed));
  show('.fact',fade(1200,220)*(1-fade(7940,180)));
  show('.retained',fade(3900,220));
  const cut=document.querySelector('.zero-cut');
  const cutIn=fade(3300,360),cutOut=fade(3650,210);
  cut.style.opacity=String(t>=3300&&t<3860?1-cutOut:0);
  cut.style.transform=`translate(${cutOut*1000}px,${-cutOut*140}px) rotate(-8deg) scaleX(${cutIn})`;
  const count=t>=2040?4:t>=1900?3:t>=1760?2:t>=1620?1:0;
  for(const mark of document.querySelectorAll('mark'))mark.classList.toggle('on',Number(mark.dataset.flag)<count&&t<8120);
}

const playback=`
const stage=document.querySelector('#stage'),viewport=document.querySelector('.viewport');
function resize(){const scale=viewport.clientWidth/${W};stage.style.transform='scale('+scale+')';viewport.style.height=(${H}*scale)+'px';}
new ResizeObserver(resize).observe(viewport);resize();
const reduced=matchMedia('(prefers-reduced-motion: reduce)'),toggle=document.querySelector('#toggle');
let paused=false,started=performance.now(),elapsed=0,raf;
function tick(now){if(!paused&&!reduced.matches){elapsed=(now-started)%${DURATION};renderFrame(elapsed);raf=requestAnimationFrame(tick);}}
function sync(){cancelAnimationFrame(raf);if(reduced.matches){renderFrame(4800);toggle.disabled=true;toggle.textContent='Motion reduced';}else{toggle.disabled=false;toggle.textContent=paused?'Play':'Pause';if(!paused)raf=requestAnimationFrame(tick);}}
toggle.addEventListener('click',()=>{paused=!paused;started=performance.now()-elapsed;sync();});
document.querySelector('#replay').addEventListener('click',()=>{started=performance.now();elapsed=0;paused=false;sync();});
reduced.addEventListener('change',sync);document.addEventListener('visibilitychange',()=>{if(document.hidden)cancelAnimationFrame(raf);else{started=performance.now()-elapsed;sync();}});sync();
`;
const html=(controls=false)=>`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Slop - Zero Cut</title><style>${css}</style></head><body><div class="viewport"><div id="stage" role="img" aria-label="Zero Slop: four stock phrases removed, writing score 99.3 to 9.5, with the 40% result retained.">${markup}</div></div>${controls?'<div class="controls"><button id="toggle">Pause</button><button id="replay">Replay</button><span class="note">Illustrative sequence. Scores are measured; timing is not a speed test.</span></div>':''}<script>${renderFrame.toString()};renderFrame(0);${controls?playback:''}</script></body></html>`;

// 25 fps during the short transitions; long readable holds are single frames.
// Repeated frames are merged by the encoders. The player runs at display rate.
const points=new Set([0,480,760,980,1460,1620,1760,1900,2040,3300,3860,3900,4120,6060,6520,7940,8120,8400]);
for(const [start,end] of [[480,760],[980,1460],[3300,3860],[3900,4120],[6060,6520],[7940,8120],[8120,8400]])for(let t=start;t<end;t+=40)points.add(t);
const ticks=[...points].sort((a,b)=>a-b);
const timeline=ticks.slice(0,-1).map((t,i)=>({t,delay:ticks[i+1]-t}));
await mkdir(dirname(out),{recursive:true});
await writeFile(`${base}.html`,html(true));
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const buffers=[];
let poster;
try{
  const page=await browser.newPage({viewport:{width:W,height:H},deviceScaleFactor:1,reducedMotion:'no-preference'});
  await page.route('**/*',route=>route.abort());
  await page.setContent(html());await page.evaluate(()=>document.fonts.ready);
  for(const {t} of timeline){await page.evaluate(t=>renderFrame(t),t);const png=await page.screenshot({type:'png'});buffers.push(await sharp(png).removeAlpha().raw().toBuffer());}
  await page.evaluate(()=>renderFrame(4800));poster=await page.screenshot({type:'png'});
  const overflow=await page.locator('.scene,.draft,.rewrite,.brand,footer').evaluateAll(els=>els.map(el=>({name:el.className||el.tagName,scroll:el.scrollHeight,height:el.clientHeight,width:el.scrollWidth,client:el.clientWidth})).filter(el=>el.scroll>el.height||el.width>el.client));
  if(overflow.length)throw Error(`Layout overflow: ${JSON.stringify(overflow)}`);
}finally{await browser.close();}
const raw={width:W,height:H*buffers.length,channels:3,pageHeight:H},pixels=Buffer.concat(buffers),delay=timeline.map(f=>f.delay);
await sharp(poster).png({palette:true,colours:128,effort:10,dither:0}).toFile(`${base}-poster.png`);
await sharp(pixels,{raw}).gif({loop:0,delay,colours:96,dither:0,effort:10,interFrameMaxError:0,interPaletteMaxError:0}).toFile(out);
await sharp(pixels,{raw}).webp({loop:0,delay,quality:90,nearLossless:true,mixed:true,effort:6,minSize:true}).toFile(`${base}.webp`);
for(const file of [out,`${base}.webp`,`${base}-poster.png`]){const meta=await sharp(file,{animated:true}).metadata(),bytes=(await stat(file)).size;console.log(`${file}: ${meta.width}x${meta.pageHeight??meta.height}, ${meta.pages??1} frames, ${bytes} bytes`);if(file===out&&bytes>400000)throw Error('GIF exceeds 400 kB budget');if(meta.delay&&meta.delay.reduce((a,b)=>a+b,0)!==DURATION)throw Error('Encoded duration drift');}
console.log(`Loop ${DURATION}ms. Exact scores 99.3 -> 9.5. Zero playback dependencies or remote requests.`);
