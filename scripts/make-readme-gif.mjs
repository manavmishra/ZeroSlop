#!/usr/bin/env node
// Build the full skill demo: 1080p film frames + GitHub GIF/WebP + poster/player.
// Build-only dependencies: playwright-core, sharp, @xterm/xterm. No live model calls.
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir,mkdtemp,stat} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {filmHTML,timeline,WIDTH,HEIGHT,DURATION,POSTER_TIME,CAPTIONS,MCP_URL} from '../growth/demo-film.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require('playwright-core'),sharp=require('sharp');
const ROOT=fileURLToPath(new URL('../',import.meta.url));
const xtermModule=require.resolve('@xterm/xterm',{paths:[process.env.ZERO_SLOP_MEDIA_DEPS??ROOT]});
const xtermJS=await readFile(xtermModule,'utf8');
const xtermCSS=await readFile(resolve(dirname(xtermModule),'../css/xterm.css'),'utf8');
const xtermVersion=JSON.parse(await readFile(resolve(dirname(xtermModule),'../package.json'),'utf8')).version;
const server=JSON.parse(await readFile(resolve(ROOT,'server.json'),'utf8'));
if(MCP_URL!==server.remotes[0].url)throw Error('Demo MCP endpoint differs from server.json.');
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
const html=filmHTML({logo,before,after,beforeScore,afterScore,flags,xtermJS,xtermCSS});
await writeFile(resolve(frames,'film.html'),html);
const evidence={kind:'Reconstructed installed-skill session rendered in a real xterm.js terminal',terminalRenderer:`@xterm/xterm ${xtermVersion}`,mcpURL:MCP_URL,durationMs:DURATION,source:'examples/launch-post.before.md',edit:'examples/launch-post.after.md',before,after,beforeScore,afterScore,flags,protectedDetail:'40%',beforeSha256:createHash('sha256').update(before).digest('hex'),afterSha256:createHash('sha256').update(after).digest('hex'),beforeOutput,afterOutput,fidelity,note:'Uses the saved repository example. This is not a recording of the hosted editor or a real-time capture. Host model outputs vary. Timing is edited for readability, not a latency measurement.'};
await writeFile(resolve(ROOT,'growth/demo-evidence.json'),JSON.stringify(evidence,null,2)+'\n');
await writeFile(resolve(frames,'captions.txt'),CAPTIONS.join('\n\n')+'\n');
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const saved=new Map(),gifFrames=[],gifDelay=[];
const base=resolve(ROOT,'assets/zero-slop-demo');
try{
  const page=await browser.newPage({viewport:{width:WIDTH,height:HEIGHT},deviceScaleFactor:1.5,reducedMotion:'no-preference'});
  await page.route('**/*',route=>route.abort());
  await page.setContent(html);await page.evaluate(()=>window.filmReady);
  const frame=async t=>{if(saved.has(t))return saved.get(t);await page.evaluate(t=>renderFrame(t),t);const png=await page.screenshot();const path=resolve(frames,`frame-${String(t).padStart(5,'0')}.png`);await writeFile(path,png);saved.set(t,{png,path});return {png,path};};
  const keyTimes=[0,2200,6000,11000,15000,18000,21500,POSTER_TIME,32000,35000];
  const inspections=[];
  for(const t of keyTimes){await frame(t);inspections.push({t,...await page.evaluate(()=>window.filmInspection())});}
  await writeFile(resolve(frames,'terminal-inspections.json'),JSON.stringify(inspections,null,2)+'\n');
  const visible=inspections.find(f=>f.t===POSTER_TIME).visibleLines.join(' ').replace(/\s+/g,' ');
  if(!visible.includes(after))throw Error('The poster must contain the complete readable edit.');
  if(!(await page.locator('.closing').innerText()).includes(MCP_URL))throw Error('Closing frame must include the exact MCP endpoint.');
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
  const overflow=await page.locator('.caption,.mcp-url,.xterm-screen').evaluateAll(els=>els.map(el=>({name:el.className,scroll:el.scrollHeight,height:el.clientHeight,width:el.scrollWidth,client:el.clientWidth})).filter(x=>x.scroll>x.height+1||x.width>x.client+1));
  if(overflow.length)throw Error(`Layout overflow: ${JSON.stringify(overflow)}`);
}finally{await browser.close();}
const player=`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Zero Slop | The skill in your terminal</title>
  <style>
    :root{color-scheme:light}*{box-sizing:border-box}
    body{margin:0;padding:32px 20px;background:#fff;color:#12100c;font:16px/1.6 system-ui,sans-serif}
    main{max-width:1100px;margin:auto}
    video{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#fff}
    h1{font-size:26px;font-weight:600;letter-spacing:-.6px}a{color:#a64c2c}
    p{max-width:75ch}summary{cursor:pointer}code{font-size:.94em;overflow-wrap:anywhere}
    .links{display:flex;gap:24px;flex-wrap:wrap}
    @media(prefers-reduced-motion:reduce){video{scroll-behavior:auto}}
  </style>
</head>
<body><main>
  <h1>Zero Slop: the skill in your terminal</h1>
  <video controls playsinline muted preload="metadata" poster="zero-slop-demo-poster.png">
    <source src="zero-slop-demo.mp4" type="video/mp4">
    Your browser cannot play this video. <a href="zero-slop-demo.mp4">Download the MP4</a>.
  </video>
  <p>A reconstructed skill session using the saved launch-post example and a real terminal renderer.
    Your AI assistant edits; Zero Slop’s local tools score the wording and compare details against the source.
    Hosted outputs can differ. Timing is edited for readability.</p>
  <div class="links">
    <a href="https://zero-slop.ai/try/">Try the free editor</a>
    <a href="https://zero-slop.ai/#mcp">MCP setup guide</a>
    <a href="https://github.com/manavmishra/ZeroSlop">Install the skill</a>
  </div>
  <p>Hosted MCP endpoint: <code>${MCP_URL}</code></p>
  <details><summary>Read the demo transcript</summary>
    <p>Install in your shell: <code>npx skills add manavmishra/ZeroSlop --global</code>.</p>
    <p>Restart your assistant. Then paste the draft after <code>/zero-slop</code> inside its session.
      This is an assistant request, not a shell executable.</p>
    <p><strong>Original:</strong> ${before}</p>
    <p>Four stock phrases are flagged. Writing score: ${beforeScore}/100; lower is better.</p>
    <p><strong>Edit:</strong> ${after}</p>
    <p>The writing score is ${afterScore}/100, with zero flagged phrases.
      The source’s 40% figure is retained. The checks do not establish whether that source claim is true.</p>
    <p>To use the optional hosted MCP, add <code>${MCP_URL}</code> to your MCP client.</p>
  </details>
</main></body></html>`;
await writeFile(`${base}.html`,player);
