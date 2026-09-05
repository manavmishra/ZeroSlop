#!/usr/bin/env node
// Build the full skill demo: 1080p film frames + GitHub GIF/WebP + poster/player.
// Build-only dependencies: playwright-core and sharp. No live model/network calls.
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir,mkdtemp,stat} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {filmHTML,timeline,WIDTH,HEIGHT,DURATION,POSTER_TIME,CAPTIONS} from '../growth/demo-film.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require('playwright-core'),sharp=require('sharp');
const ROOT=fileURLToPath(new URL('../',import.meta.url));
const args=process.argv.slice(2),preview=args.includes('--preview');
const frameArg=args.indexOf('--frames');
const frames=frameArg>=0?resolve(args[frameArg+1]):await mkdtemp(`${tmpdir()}/zero-slop-film-`);
await mkdir(frames,{recursive:true});
const beforePath=resolve(ROOT,'examples/launch-post.before.md'),afterPath=resolve(ROOT,'examples/launch-post.after.md');
const before=(await readFile(beforePath,'utf8')).trim(),after=(await readFile(afterPath,'utf8')).trim();
const run=(...args)=>execFileSync('python3',[resolve(ROOT,'scripts/slopscore.py'),...args],{encoding:'utf8'});
const beforeOutput=run('--explain',beforePath),afterOutput=run('--explain',afterPath),fidelity=run('--fidelity',beforePath,afterPath);
const score=raw=>Number(raw.match(/Writing score: ([\d.]+)/)[1]);
const beforeScore=score(beforeOutput),afterScore=score(afterOutput);
if(beforeScore!==99.3||afterScore!==9.5)throw Error('Example measurements changed; review the film before rebuilding.');
const flags=["We're thrilled to",'leveraged','cutting-edge','seamless'];
const logo=await readFile(resolve(ROOT,'assets/logo/logo-mark.svg'),'utf8');
const html=filmHTML({logo,before,after,beforeScore,afterScore,flags});
await writeFile(resolve(frames,'film.html'),html);
const evidence={kind:'Typeset demonstration of the installed Agent Skill using the saved repository example',durationMs:DURATION,source:'examples/launch-post.before.md',edit:'examples/launch-post.after.md',before,after,beforeScore,afterScore,flags,protectedDetail:'40%',beforeSha256:createHash('sha256').update(before).digest('hex'),afterSha256:createHash('sha256').update(after).digest('hex'),beforeOutput,afterOutput,fidelity,note:'This is not a recording of the hosted editor. Host model outputs vary. Timing is edited for readability, not a latency measurement.'};
await writeFile(resolve(ROOT,'growth/demo-evidence.json'),JSON.stringify(evidence,null,2)+'\n');
await writeFile(resolve(frames,'captions.txt'),CAPTIONS.join('\n\n')+'\n');
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const saved=new Map(),gifFrames=[],gifDelay=[];
const base=resolve(ROOT,'assets/zero-slop-demo');
try{
  const page=await browser.newPage({viewport:{width:WIDTH,height:HEIGHT},deviceScaleFactor:1.5,reducedMotion:'no-preference'});
  await page.route('**/*',route=>route.abort());
  await page.setContent(html);await page.evaluate(()=>document.fonts.ready);
  const frame=async t=>{if(saved.has(t))return saved.get(t);await page.evaluate(t=>renderFrame(t),t);const png=await page.screenshot();const path=resolve(frames,`frame-${String(t).padStart(5,'0')}.png`);await writeFile(path,png);saved.set(t,{png,path});return {png,path};};
  for(const t of [0,6000,15000,17600,21500,POSTER_TIME,32000])await frame(t);
  await sharp((await frame(POSTER_TIME)).png).resize(1280,720).png({palette:true,colours:128,dither:0,effort:10}).toFile(`${base}-poster.png`);
  if(preview){console.log(`Preview frames and source: ${frames}`);}else{
    const manifest=[];
    const filmTimeline=timeline();
    for(const [index,item] of filmTimeline.entries()){
      const {path}=await frame(item.t);manifest.push({file:path,durationMs:item.durationMs});
      if(index%40===0)console.log(`Rendered ${index}/${filmTimeline.length} unique film frames`);
    }
    await writeFile(resolve(frames,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
    // GIF delays are centiseconds. Merge boundaries closer than 20 ms, preserving time.
    const candidates=[...new Set(timeline(20).map(f=>Math.round(f.t/10)*10)),DURATION].sort((a,b)=>a-b);
    const gifTimes=[0];
    for(const t of candidates)if(t-gifTimes[gifTimes.length-1]>=20&&DURATION-t>=20)gifTimes.push(t);
    gifTimes.push(DURATION);
    for(let i=0;i<gifTimes.length-1;i++){
      const {png}=await frame(gifTimes[i]);
      gifFrames.push(await sharp(png).resize(960,540).removeAlpha().raw().toBuffer());
      gifDelay.push(gifTimes[i+1]-gifTimes[i]);
    }
    const raw={width:960,height:540*gifFrames.length,channels:3,pageHeight:540},pixels=Buffer.concat(gifFrames);
    await sharp(pixels,{raw}).gif({loop:0,delay:gifDelay,colours:96,dither:0,effort:10,interFrameMaxError:0}).toFile(`${base}.gif`);
    await sharp(pixels,{raw}).webp({loop:0,delay:gifDelay,quality:88,nearLossless:true,mixed:true,effort:6,minSize:true}).toFile(`${base}.webp`);
    for(const ext of ['gif','webp'])console.log(`${ext}: ${(await stat(`${base}.${ext}`)).size} bytes`);
    console.log(`MP4 input manifest: ${resolve(frames,'manifest.json')}`);
  }
  const overflow=await page.locator('.source,.edited,.original,.rewritten,.install code,.next,.end-links').evaluateAll(els=>els.map(el=>({name:el.className||el.tagName,scroll:el.scrollHeight,height:el.clientHeight,width:el.scrollWidth,client:el.clientWidth})).filter(x=>x.scroll>x.height+1||x.width>x.client+1));
  if(overflow.length)throw Error(`Layout overflow: ${JSON.stringify(overflow)}`);
}finally{await browser.close();}
const player=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Slop | The skill in use</title><style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;padding:32px 20px;background:#fff;color:#12100c;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto}video{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#fff}h1{font-size:26px;font-weight:600;letter-spacing:-.6px}a{color:#a64c2c}p{max-width:75ch}summary{cursor:pointer}code{font-size:.94em}.links{display:flex;gap:24px;flex-wrap:wrap}@media(prefers-reduced-motion:reduce){video{scroll-behavior:auto}}</style></head><body><main><h1>Zero Slop: the skill in use</h1><video controls playsinline muted preload="metadata" poster="zero-slop-demo-poster.png"><source src="zero-slop-demo.mp4" type="video/mp4">Your browser cannot play this video. <a href="zero-slop-demo.mp4">Download the MP4</a>.</video><p>A typeset demonstration using the saved launch-post example. Your AI assistant edits; Zero Slop’s local tools score the wording and check source details. The browser editor and MCP use a hosted editor, so their outputs can differ. Sequence edited for readability.</p><div class="links"><a href="https://zero-slop.ai/try/">Try the free editor</a><a href="https://zero-slop.ai/#mcp">Connect the hosted MCP</a><a href="https://github.com/manavmishra/ZeroSlop">Install the skill</a></div><details><summary>Read the demo transcript</summary><p>Install once in your terminal: <code>npx skills add manavmishra/ZeroSlop --global</code>.</p><p>In your AI assistant, paste the draft after <code>/zero-slop</code>.</p><p><strong>Original:</strong> ${before}</p><p>Four stock phrases are flagged. Writing score: ${beforeScore}/100; lower is better.</p><p><strong>Edit:</strong> ${after}</p><p>The writing score is ${afterScore}/100, with zero flagged phrases. The source’s 40% result is retained. The checks do not establish whether that source claim is true.</p></details></main></body></html>`;
await writeFile(`${base}.html`,player);
