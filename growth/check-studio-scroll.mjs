#!/usr/bin/env node
// Build-only regression check for the real terminal texture in the silent film.
// No network or live model calls. Requires the same build tools as the renderer.
//
// ZERO_SLOP_MEDIA_DEPS=/tmp/zero-slop-media-deps \
//   node growth/check-studio-scroll.mjs [--output /tmp/new-scroll-check]
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {filmHTML,WIDTH,HEIGHT} from './demo-film.mjs';
import {sourceTime,STUDIO_DURATION} from './studio-timeline.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const require=createRequire(import.meta.url);
const dependencyPaths=[process.env.ZERO_SLOP_MEDIA_DEPS??ROOT,ROOT];
const {chromium}=require(require.resolve('playwright-core',{paths:dependencyPaths}));
const xtermModule=require.resolve('@xterm/xterm',{paths:dependencyPaths});
const args=process.argv.slice(2);
assert(args.length===0||(args.length===2&&args[0]==='--output'),
  'Usage: node growth/check-studio-scroll.mjs [--output DIR]');
const output=args.length?resolve(args[1]):await mkdtemp(`${tmpdir()}/zero-slop-scroll-check-`);
await mkdir(output,{recursive:true});
const before=(await readFile(resolve(ROOT,'examples/launch-post.before.md'),'utf8')).trim();
const after=(await readFile(resolve(ROOT,'examples/launch-post.after.md'),'utf8')).trim();
const html=filmHTML({
  logo:await readFile(resolve(ROOT,'assets/logo/studio/zero-slop-mark.svg'),'utf8'),
  before,after,beforeScore:99.3,afterScore:9.5,
  flags:["We're thrilled to",'leveraged','cutting-edge','seamless'],
  xtermJS:await readFile(xtermModule,'utf8'),
  xtermCSS:await readFile(resolve(dirname(xtermModule),'../css/xterm.css'),'utf8'),
});
const EVENTS=[9900,10400,11200,11600,15800,16400,17000,17600];
const SOURCE_EVENTS=[13400,14000,16400,17200,22000,23000,24000,25200];
const EVENT_RECORDS=EVENTS.map((at,index)=>({at,sourceTime:SOURCE_EVENTS[index]}));
const normalize=text=>text.replace(/\s+/g,' ').trim();
const browser=await chromium.launch({
  executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless:true,
});
try{
  const page=await browser.newPage({viewport:{width:WIDTH,height:HEIGHT},deviceScaleFactor:1.5});
  const blocked=[];
  await page.route('**/*',route=>{blocked.push(route.request().url());return route.abort();});
  await page.setContent(html);await page.evaluate(()=>window.filmReady);
  assert.equal(await page.locator('audio,video').count(),0,'The terminal source must contain no media playback');
  await page.addStyleTag({content:'.terminal-shell{transform:none!important;box-shadow:none!important}.xterm,.xterm *{outline:none!important;box-shadow:none!important;border:0!important}'});
  const render=async(t,scrollEvents)=>page.evaluate(
    ({mapped,t,scrollEvents})=>window.renderFrame(mapped,{presentationTime:t,scrollEvents}),
    {mapped:sourceTime(t),t,scrollEvents});
  const key=async(t,scrollEvents)=>page.evaluate(
    ({mapped,t,scrollEvents})=>window.filmFrameKey(mapped,{presentationTime:t,scrollEvents}),
    {mapped:sourceTime(t),t,scrollEvents});
  const capture=()=>page.locator('.terminal-shell').screenshot();
  const report=[];
  for(const event of EVENTS){
    const samples=[];
    for(const delta of [-1,0,55,110,165,220]){
      const t=event+delta,state=await render(t);
      assert.equal(state.cols,76,'Terminal column count changed');
      assert.equal(state.rows,14,'Visible viewport must remain 14 rows');
      assert.equal(state.renderRows,17,'Three physical guard rows are required');
      assert(state.scrollTopRows>=state.renderViewportY-1e-7,'Outgoing top rows are missing');
      assert(state.scrollTopRows+14<=state.renderViewportY+17+1e-7,'Incoming bottom rows are missing');
      assert(state.rowHeight>20&&state.rowHeight<40,'Invalid physical terminal cell height');
      const physical=await page.evaluate(()=>({
        clip:document.querySelector('#terminal').getBoundingClientRect().height,
        overflow:getComputedStyle(document.querySelector('#terminal')).overflow,
        lines:Array.from(document.querySelector('.xterm-rows').children,row=>row.textContent),
      }));
      assert.equal(physical.overflow,'hidden','Guard rows must be clipped');
      assert(Math.abs(physical.clip-state.rows*state.rowHeight)<.05,'Clip is not exactly 14 physical rows');
      assert.equal(physical.lines.length,state.renderRows,'Missing actual xterm guard-row DOM');
      for(const [index,line] of physical.lines.entries()){
        assert.equal(normalize(line),normalize(state.allLines[state.renderViewportY+index]??''),
          `Physical xterm row differs from its buffer at ${t} ms, row ${index}`);
      }
      samples.push({delta,top:state.scrollTopRows,target:state.scrollTargetRows,
        progress:state.scrollProgress,pixelOffset:state.pixelOffset,
        renderViewportY:state.renderViewportY,rowHeight:state.rowHeight,
        visibleLines:state.visibleLines});
      if(event===11200||event===17600){
        await writeFile(resolve(output,`scroll-${event}-${delta}.png`),await capture());
      }
    }
    assert(samples.every((sample,index)=>index===0||sample.top>=samples[index-1].top),
      `Scroll reverses at ${event} ms`);
    assert(Math.abs(samples[1].top-samples[0].top)<1e-6,`Scroll jumps at ${event} ms`);
    assert(samples[2].top>samples[1].top&&samples[4].top<samples[5].top,
      `Intermediate pixel motion is missing at ${event} ms`);
    assert.equal(samples[1].progress,0,'Scroll must begin at rest');
    assert.equal(samples[3].progress,.5,'Scroll midpoint must be deterministic');
    assert.equal(samples[5].progress,1,'Scroll must finish at rest');
    report.push({event,samples});
  }
  // Defaults, explicit numeric presentation events, and explicit event records
  // must resolve to the same source thresholds and produce the same texture.
  for(const [index,event] of EVENTS.entries()){
    const t=event+110,baseline=await key(t);
    assert.equal(await key(t,EVENTS),baseline,'Numeric presentation-event mapping changed');
    assert.equal(await key(t,EVENT_RECORDS),baseline,'Object event mapping changed');
    const defaultState=await render(t),numeric=await render(t,EVENTS),records=await render(t,EVENT_RECORDS);
    assert.equal(numeric.scrollTopRows,defaultState.scrollTopRows,'Numeric event render differs');
    assert.equal(records.scrollTopRows,defaultState.scrollTopRows,'Object event render differs');
    const legacy=await page.evaluate(source=>window.renderFrame(source+110),SOURCE_EVENTS[index]);
    assert.equal(legacy.scrollTopRows,defaultState.scrollTopRows,'Source-clock fallback mapping changed');
  }
  const randomTime=11310;
  await render(randomTime);const first=await capture();
  await render(STUDIO_DURATION-1000);await render(1000);await render(randomTime);
  assert(first.equals(await capture()),'Random-access re-render is not pixel-identical');
  assert.equal(await key(6000),await key(7000),'Static source hold does not share a canonical key');
  assert.notEqual(await key(11310),await key(11320),'Scrolling frames incorrectly share a canonical key');
  const draft=await render(6000);
  assert(normalize(draft.visibleLines.join(' ')).includes(before),'Complete source draft is absent');
  const final=await render(18800);
  assert(normalize(final.visibleLines.join(' ')).includes(after),'Complete edit is absent at the settled result');
  assert(final.visibleLines.includes('Source figure retained: 40%.'),'Protected source figure is absent');
  assert.equal(final.visibleLines.length,14,'Settled viewport must contain exactly 14 rows');
  assert.deepEqual(blocked,[],'The source attempted a network request');
  const summary={events:EVENTS.length,randomAccess:'pixel-identical',
    randomAccessSha256:createHash('sha256').update(first).digest('hex'),
    cacheKeys:'static reused; movement distinct',eventForms:'default, numeric, records, source-clock',
    networkRequests:0,rows:14,renderRows:17,rowHeight:final.rowHeight};
  await writeFile(resolve(output,'report.json'),JSON.stringify({summary,report,final},null,2)+'\n');
  console.log(`Studio terminal scroll checks passed: ${EVENTS.length} transitions, guard rows, cache keys, random access and complete edit.`);
  console.log(`Report and boundary screenshots: ${output}`);
}finally{await browser.close();}
