#!/usr/bin/env node
// Build-only helper: capture exact xterm states for the Blender product film.
// It does not contact the network and does not run a model.
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url),{chromium}=require('playwright-core');
const ROOT=fileURLToPath(new URL('../',import.meta.url));
const DEPS=process.env.ZERO_SLOP_MEDIA_DEPS??'/tmp/zero-slop-terminal.k43Uzl';
const xtermModule=require.resolve('@xterm/xterm',{paths:[DEPS]});
const xtermJS=await readFile(xtermModule,'utf8');
const xtermCSS=await readFile(resolve(dirname(xtermModule),'../css/xterm.css'),'utf8');
const {filmHTML}=await import('../growth/demo-film.mjs');
const beforePath=resolve(ROOT,'examples/launch-post.before.md');
const afterPath=resolve(ROOT,'examples/launch-post.after.md');
const before=(await readFile(beforePath,'utf8')).trim(),after=(await readFile(afterPath,'utf8')).trim();
const run=(...args)=>execFileSync('python3',[resolve(ROOT,'scripts/slopscore.py'),...args],{encoding:'utf8'});
const score=raw=>Number(raw.match(/Writing score: ([\d.]+)/)[1]);
const beforeScore=score(run('--explain',beforePath)),afterScore=score(run('--explain',afterPath));
const flags=["We're thrilled to",'leveraged','cutting-edge','seamless'];
const logo=await readFile(resolve(ROOT,'assets/logo/studio/zero-slop-mark.svg'),'utf8');
const html=filmHTML({logo,before,after,beforeScore,afterScore,flags,xtermJS,xtermCSS});
const output=resolve(ROOT,'growth/blender-screens');await mkdir(output,{recursive:true});
const states=[
  ['install',0],['assistant',5000],['source',6000],['flags',14000],
  ['edit',17200],['checks',23000],
];
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
  const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:2});
  await page.route('**/*',route=>route.abort());await page.setContent(html);await page.evaluate(()=>window.filmReady);
  await page.addStyleTag({content:'.closing,.brand,.instruction,footer{visibility:hidden!important}.terminal-shell{transform:none!important}.xterm,.xterm *{outline:none!important;box-shadow:none!important}'});
  for(const [name,time] of states){
    await page.evaluate(time=>window.renderFrame(time),time);
    await page.locator('.terminal-shell').screenshot({path:resolve(output,`${name}.png`)});
  }
}finally{await browser.close();}
await writeFile(resolve(output,'manifest.json'),JSON.stringify({
  source:'examples/launch-post.before.md + examples/launch-post.after.md',
  renderer:'@xterm/xterm 6.0.0 capture reused as an opaque Blender screen plate',
  states:Object.fromEntries(states.map(([name,time])=>[name,{sourceTime:time,file:`growth/blender-screens/${name}.png`}])),
},null,2)+'\n');
console.log(`Wrote ${states.length} exact xterm screen plates to ${output}`);
