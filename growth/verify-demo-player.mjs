// Build-only browser QA: explicit playback, video decoding and silent delivery.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
const require=createRequire(import.meta.url),{chromium}=require('playwright-core');
const files={'/':['zero-slop-demo.html','text/html'],'/zero-slop-demo.mp4':['zero-slop-demo.mp4','video/mp4'],'/zero-slop-demo-poster.png':['zero-slop-demo-poster.png','image/png']};
const server=createServer(async(req,res)=>{const item=files[req.url];if(!item){res.writeHead(404);res.end();return;}try{const bytes=await readFile(new URL('../assets/'+item[0],import.meta.url));res.writeHead(200,{'Content-Type':item[1],'Content-Length':bytes.length});res.end(bytes);}catch{res.writeHead(500);res.end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH??'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
  const page=await browser.newPage({viewport:{width:1100,height:900}});
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(()=>document.querySelector('video').readyState>=1);
  const initial=await page.locator('video').evaluate(v=>({duration:v.duration,paused:v.paused,controls:v.controls,muted:v.muted,width:v.videoWidth,height:v.videoHeight,error:v.error}));
  if(Math.abs(initial.duration-15.15)>0.000001||!initial.paused||!initial.controls||initial.width!==900||initial.height!==580||initial.error)throw Error(JSON.stringify(initial));
  await page.locator('video').click();
  await page.evaluate(async()=>{const v=document.querySelector('video');v.currentTime=10;await v.play();});
  await page.waitForFunction(()=>document.querySelector('video').currentTime>12);
  const playback=await page.evaluate(()=>{
    const v=document.querySelector('video');v.pause();
    return {time:v.currentTime,decodedAudioBytes:v.webkitAudioDecodedByteCount,frames:v.getVideoPlaybackQuality().totalVideoFrames,error:v.error};
  });
  if(playback.error||playback.decodedAudioBytes!==0||playback.frames<1)throw Error(JSON.stringify(playback));
  console.log(JSON.stringify({initial,playback},null,2));
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
