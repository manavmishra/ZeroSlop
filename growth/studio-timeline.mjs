// The studio presentation wraps the verified xterm replay without changing its text.
export const STUDIO_DURATION = 24000;
export const STUDIO_POSTER_TIME = 17700;
export const STUDIO_KEY_TIMES = [0,400,800,2200,4000,5000,8200,10000,11600,12400,15800,17700,20500,23000];
// Re-time the verified replay. Output holds stay readable; camera moves and
// command entry are compressed. This is an editorial cut, not a speed claim.
const CUT = [[0,0],[800,1200],[1000,1550],[2300,3250],[3600,5200],[3850,5450],[4650,6350],[5000,7200],[8600,12000],[8800,12200],[9400,12800],[9900,13400],[10400,14000],[11200,16400],[11600,17200],[11900,17600],[12300,18000],[13100,18700],[13400,19100],[15800,22000],[16400,23000],[17000,24000],[17600,25200],[19000,30000],[20200,31400],[24000,36000]];
function mapTime(t,inverse=false){
  const a=inverse?1:0,b=inverse?0:1;
  for(let i=1;i<CUT.length;i++)if(t<=CUT[i][a]){
    const start=CUT[i-1],end=CUT[i];
    return start[b]+(end[b]-start[b])*Math.max(0,(t-start[a])/(end[a]-start[a]));
  }
  return CUT.at(-1)[b];
}
export const presentationTime=t=>mapTime(t);
export function sourceTime(t) {
  const legacy=presentationTime(t);
  return legacy < 1200 ? 0 : legacy < 12000 ? Math.min(legacy - 1200, 6000) : legacy;
}
const moving = [[0,1200],[1200,2400],[7200,7600],[16400,17200],[17600,18000],[18700,19100],[30000,31400]];
export function studioTimeline(fps = 30) {
  const times = new Set([0,1200,2400,5200,7200,7600,12000,12200,12800,13400,14000,16400,17200,17600,18000,18700,19100,22000,23000,24000,25200,30000,31400]);
  for (const [start,end] of moving) for(let t=start;t<=end;t+=1000/fps) times.add(Math.round(t));
  for (const [start,end,len] of [[1550,3250,40],[5450,6350,10]]) {
    for(let i=0;i<=len;i++)times.add(Math.round(start+(end-start)*i/len));
  }
  const ordered=[...new Set([...times].map(t=>Math.round(mapTime(t,true))))].filter(t=>t<STUDIO_DURATION).sort((a,b)=>a-b);
  return ordered.map((t,i)=>({t,durationMs:(ordered[i+1]??STUDIO_DURATION)-t}));
}
export function studioHTML({bundle,logo,MCP_URL}) {
  const payload = JSON.stringify({logo,MCP_URL}).replaceAll('<','\\u003c');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Zero Slop studio film</title><style>
  *{box-sizing:border-box}html,body{margin:0;width:1280px;height:720px;overflow:hidden;background:#fff;color:#12100c;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;-webkit-font-smoothing:antialiased}
  #stage{position:absolute;inset:0}canvas{display:block;width:1280px;height:720px}
  .brand{position:absolute;left:54px;top:31px;display:flex;align-items:center;gap:12px;height:58px}
  .brand svg{width:56px;height:56px}.brand h1{margin:0;font-size:30px;font-weight:600;letter-spacing:-1px}
  .intro{position:absolute;left:93px;top:252px;transform-origin:left center}
  .intro h2{font-size:76px;font-weight:600;letter-spacing:-3.6px;line-height:1.04;margin:0 0 25px}
  .intro p{font-size:25px;line-height:1.4;letter-spacing:-.35px;margin:0;color:#68645e}
  .instruction{position:absolute;left:65px;top:653px;margin:0;font-size:19px;line-height:1.2;color:#68645e}
  .closing{position:absolute;left:82px;top:529px;right:75px;display:grid;grid-template-columns:1.72fr 1fr;gap:40px;opacity:0}
  .closing p{font-size:19px;margin:0 0 12px;color:#68645e}.closing a{font-size:32px;font-weight:520;letter-spacing:-.75px;color:#8c3f22;text-decoration:none;white-space:nowrap}
  .closing .secondary{border-left:1px solid #ddd9d3;padding-left:29px}.closing .secondary a{color:#12100c;font-size:28px}
  footer{position:absolute;left:65px;right:65px;bottom:14px;display:flex;justify-content:space-between;font-size:13px;line-height:1.2;color:#68645e}
  @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
  </style></head><body><main id="stage" aria-label="Three-dimensional studio presentation of a reconstructed Zero Slop skill session"></main>
  <header class="brand">${logo}<h1>Zero Slop in your terminal.</h1></header>
  <section class="intro"><h2>Zero Slop</h2><p>Find AI-sounding writing.<br>Keep the source intact.</p></section>
  <p class="instruction"></p>
  <section class="closing"><div><p>Optional hosted MCP</p><a href="${MCP_URL}">${MCP_URL}</a></div><div class="secondary"><p>Or try the free browser editor</p><a href="https://zero-slop.ai/try/">zero-slop.ai/try</a></div></section>
  <footer><span>Reconstructed skill session. Timing edited for readability.</span><span>zero-slop.ai</span></footer>
  <script>window.studioPayload=${payload};</script><script>${bundle.replaceAll('</script','<\\/script')}</script></body></html>`;
}
