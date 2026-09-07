// Export the vector identity in the same physically based studio used by the film.
throw new Error(
  "This gold-logo studio renderer is retired. The current official logo is at " +
  "assets/logo/ and https://zero-slop.ai/brand/. The historical studio scene and " +
  "film direction remain archived unchanged."
);

import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {studioHTML} from './studio-timeline.mjs';
const require=createRequire(import.meta.url),ROOT=fileURLToPath(new URL('../',import.meta.url));
const {chromium}=require('playwright-core'),esbuild=require('esbuild');
const build=await esbuild.build({entryPoints:[resolve(ROOT,'growth/studio-scene.mjs')],bundle:true,write:false,platform:'browser',format:'iife',minify:true,nodePaths:[resolve(process.env.ZERO_SLOP_MEDIA_DEPS??ROOT,'node_modules')]});
const logo=await readFile(resolve(ROOT,'assets/logo/studio/zero-slop-mark.svg'),'utf8');
const html=studioHTML({bundle:build.outputFiles[0].text,logo,MCP_URL:'https://mcp.zero-slop.ai/mcp'});
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
  const page=await browser.newPage({viewport:{width:1200,height:1200},deviceScaleFactor:1});
  await page.route('**/*',route=>route.abort());await page.setContent(html);await page.evaluate(()=>window.studioReady);
  await page.evaluate(()=>window.renderLogo());
  const path=resolve(ROOT,'assets/logo/studio/zero-slop-mark-3d-1200.png');
  await page.locator('canvas').screenshot({path});console.log(path);
}finally{await browser.close();}
